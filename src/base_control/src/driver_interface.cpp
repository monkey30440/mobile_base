#include "base_control/driver_interface.hpp"

#include <chrono>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

namespace base_control
{

namespace
{

// 連續 FC06 之間隔；RS-485 半雙工，避免碰撞
constexpr auto kFc06Gap = std::chrono::milliseconds(20);
constexpr auto kAlmRstPulse = std::chrono::milliseconds(200);

const std::unordered_map<uint16_t, const char *> kMotorStatusMap{
  {0, "STOP"},
  {2, "RUN"},
  {3, "EBRAKE"},
  {4, "FREE"},
  {5, "FAULT"},
  {6, "WAIT/INHIBIT"},
  {7, "MOVING(SERVO ON)"},
  {8, "SLIGHT-POS-KEEPING"},
  {9, "STO"},
};

}  // namespace

std::string motor_status_text(uint16_t status)
{
  const auto it = kMotorStatusMap.find(status);
  if (it != kMotorStatusMap.end()) {
    return it->second;
  }
  return "UNKNOWN(" + std::to_string(status) + ")";
}

uint16_t net_in_word(bool servo_en, bool free, bool fwd, bool rev, bool alm_rst)
{
  uint16_t word = 0;
  if (servo_en) {word |= static_cast<uint16_t>(1U << kBitServoEn);}
  if (free) {word |= static_cast<uint16_t>(1U << kBitFree);}
  if (fwd) {word |= static_cast<uint16_t>(1U << kBitFwd);}
  if (rev) {word |= static_cast<uint16_t>(1U << kBitRev);}
  if (alm_rst) {word |= static_cast<uint16_t>(1U << kBitAlmRst);}
  return word;
}

DriverInterface::DriverInterface(Md2Transport & transport, int right_id, int left_id)
: transport_(transport), right_id_(right_id), left_id_(left_id)
{
}

int DriverInterface::counts_per_motor_rev() const
{
  if (counts_per_motor_rev_ <= 0) {
    throw DriverConfigError("counts_per_motor_rev 尚未確定，請先呼叫 validate_configuration()");
  }
  return counts_per_motor_rev_;
}

int DriverInterface::validate_configuration()
{
  struct Entry
  {
    const char * label;
    int driver_id;
  };
  const Entry entries[] = {{"右輪", right_id_}, {"左輪", left_id_}};

  int resolution = 0;
  for (const auto & entry : entries) {
    const uint16_t format = transport_.read_register(entry.driver_id, kAddrPositionFormat);
    if (format != kPositionFormatTurnsPulse) {
      throw DriverConfigError(
              std::string(entry.label) + "（ID " + std::to_string(entry.driver_id) +
              "）位置命令格式 02-14 = " + std::to_string(format) +
              "，本專案要求 0（Index(turns) + pulse）。請將驅動器回復出廠預設。");
    }

    const uint16_t value = transport_.read_register(entry.driver_id, kAddrEncoderResolution);
    if (value == 0) {
      throw DriverConfigError(
              std::string(entry.label) + "（ID " + std::to_string(entry.driver_id) +
              "）編碼器解析度 01-06 = 0，不合法");
    }
    if (resolution == 0) {
      resolution = value;
    } else if (resolution != value) {
      throw DriverConfigError(
              "左右輪編碼器解析度不一致：" + std::to_string(resolution) +
              " vs " + std::to_string(value));
    }
  }

  counts_per_motor_rev_ = resolution * kQuadratureFactor;
  return counts_per_motor_rev_;
}

void DriverInterface::enable()
{
  write_net_in_both(net_in_word(/*servo_en=*/true));
}

void DriverInterface::disable(int retries)
{
  write_net_in_both(net_in_word(/*servo_en=*/false), /*best_effort=*/true, retries);
}

void DriverInterface::set_free()
{
  write_net_in_both(net_in_word(/*servo_en=*/false, /*free=*/true));
}

void DriverInterface::alarm_reset()
{
  write_net_in_both(net_in_word(false, false, false, false, /*alm_rst=*/true));
  std::this_thread::sleep_for(kAlmRstPulse);
  write_net_in_both(net_in_word(/*servo_en=*/false));
}

void DriverInterface::apply_motion_profile(
  uint16_t linear_acc_ms, uint16_t linear_dec_ms,
  uint16_t s_curve_acc_ms, uint16_t s_curve_dec_ms)
{
  write_register_both(kAddrLinearAccMs, linear_acc_ms);
  write_register_both(kAddrLinearDecMs, linear_dec_ms);
  write_register_both(kAddrScurveAccMs, s_curve_acc_ms);
  write_register_both(kAddrScurveDecMs, s_curve_dec_ms);
}

DualFeedback DriverInterface::command(int16_t right_rpm, int16_t left_rpm)
{
  return exchange(kMdLiteJg, right_rpm, left_rpm);
}

DualFeedback DriverInterface::stop()
{
  return exchange(kMdLiteIstop, 0, 0);
}

void DriverInterface::reset_position_tracking()
{
  right_turns_ = TurnsTracker{};
  left_turns_ = TurnsTracker{};
}

DualFeedback DriverInterface::exchange(uint16_t cmd, int16_t right_rpm, int16_t left_rpm)
{
  const Md2Feedback raw = transport_.read_write(cmd, right_rpm, cmd, left_rpm);

  DualFeedback feedback;
  feedback.right = decode(right_turns_, raw.right);
  feedback.left = decode(left_turns_, raw.left);
  feedback.comm_s = raw.comm_s;
  return feedback;
}

MotorFeedback DriverInterface::decode(TurnsTracker & tracker, const DriverRaw & raw) const
{
  const int64_t turns = accumulate_turns(tracker, raw.pos_turns);

  MotorFeedback feedback;
  feedback.status = raw.status;
  feedback.alarm = raw.alarm;
  feedback.rpm = raw.rpm;
  feedback.position_counts =
    turns * static_cast<int64_t>(counts_per_motor_rev()) + static_cast<int64_t>(raw.pos_pulse);
  return feedback;
}

int64_t DriverInterface::accumulate_turns(TurnsTracker & tracker, int16_t raw_turns)
{
  if (tracker.last_raw.has_value()) {
    const int64_t delta = static_cast<int64_t>(raw_turns) - static_cast<int64_t>(*tracker.last_raw);
    if (delta < -kTurnsHalfRange) {
      tracker.offset += kTurnsRange;   // 正向繞回
    } else if (delta > kTurnsHalfRange) {
      tracker.offset -= kTurnsRange;   // 反向繞回
    }
  }
  tracker.last_raw = raw_turns;
  return static_cast<int64_t>(raw_turns) + tracker.offset;
}

void DriverInterface::write_net_in_both(uint16_t word, bool best_effort, int retries)
{
  write_register_both(kAddrNetIn, word, best_effort, retries);
}

void DriverInterface::write_register_both(
  int address, uint16_t value, bool best_effort, int retries)
{
  std::vector<std::string> failures;

  for (const int driver_id : {right_id_, left_id_}) {
    std::string last_error;
    bool ok = false;

    for (int attempt = 0; attempt <= retries; ++attempt) {
      try {
        transport_.write_register(driver_id, address, value);
        ok = true;
        break;
      } catch (const Md2Error & exc) {
        last_error = exc.what();
        // 失敗多因匯流排殘留資料造成不同步，重試前先排空
        if (attempt < retries) {
          transport_.drain();
        }
      }
    }
    std::this_thread::sleep_for(kFc06Gap);

    if (!ok) {
      if (!best_effort) {
        throw Md2Error(last_error);
      }
      failures.push_back("ID " + std::to_string(driver_id) + ": " + last_error);
    }
  }

  if (!failures.empty()) {
    std::string message;
    for (size_t i = 0; i < failures.size(); ++i) {
      if (i != 0) {message += "; ";}
      message += failures[i];
    }
    throw Md2Error(message);
  }
}

}  // namespace base_control

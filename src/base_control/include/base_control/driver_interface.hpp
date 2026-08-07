// SUB-001 Base Control — Driver Interface
//
// DEXMART M1 驅動器語意層：暫存器語意、組態驗證、激磁控制、警報處理，
// 並將原始回授解碼為馬達端工程量（RPM、單調連續之累計 counts）。
//
// 不負責：Modbus 封包（md2_transport）、車體運動學（diff_drive_controller）。

#ifndef BASE_CONTROL__DRIVER_INTERFACE_HPP_
#define BASE_CONTROL__DRIVER_INTERFACE_HPP_

#include <cstdint>
#include <optional>
#include <stdexcept>
#include <string>

#include "base_control/md2_transport.hpp"

namespace base_control
{

// ── 暫存器位址 ──────────────────────────────────────────────────────────────
inline constexpr int kAddrAlarmNo = 0x0003;
inline constexpr int kAddrEncoderResolution = 0x0105;  // 01-06 單相 pulse/rev
inline constexpr int kAddrPositionFormat = 0x020D;     // 02-14 位置命令格式
inline constexpr int kAddrNetIn = 0x1400;
inline constexpr int kAddrLinearAccMs = 0x4000;        // 04-01
inline constexpr int kAddrScurveAccMs = 0x4004;
inline constexpr int kAddrLinearDecMs = 0x4008;        // 04-09
inline constexpr int kAddrScurveDecMs = 0x400C;
inline constexpr int kAddrMotorStatus = 0x4600;

// ── NET-IN bit mapping ──────────────────────────────────────────────────────
inline constexpr int kBitFwd = 0;
inline constexpr int kBitRev = 1;
inline constexpr int kBitAlmRst = 3;
inline constexpr int kBitD0 = 4;
inline constexpr int kBitD1 = 5;
inline constexpr int kBitFree = 6;
inline constexpr int kBitServoEn = 7;

// ── Multi-Drive Lite 指令 ───────────────────────────────────────────────────
inline constexpr uint16_t kMdLiteIstop = 0x0000;
inline constexpr uint16_t kMdLiteJg = 0x0001;
inline constexpr uint16_t kMdLiteFree = 0x0005;
inline constexpr uint16_t kMdLiteSvon = 0x0006;
inline constexpr uint16_t kMdLiteBrake = 0x0009;

/// 02-14 位置命令格式：0 = Index(turns) + pulse（本專案採用之出廠預設）
inline constexpr uint16_t kPositionFormatTurnsPulse = 0;

/// 增量式編碼器四倍頻
inline constexpr int kQuadratureFactor = 4;

/// turns 為 signed 16-bit；05-03 = 2 關閉 Overflow 保護時靜默繞回，須由軟體累加。
inline constexpr int64_t kTurnsRange = 0x10000;
inline constexpr int64_t kTurnsHalfRange = kTurnsRange / 2;

class DriverConfigError : public std::runtime_error
{
public:
  explicit DriverConfigError(const std::string & what) : std::runtime_error(what) {}
};

std::string motor_status_text(uint16_t status);

/// 單一驅動器之馬達端回授。
struct MotorFeedback
{
  uint16_t status = 0;
  uint16_t alarm = 0;
  int16_t rpm = 0;                ///< 馬達端 RPM
  int64_t position_counts = 0;    ///< 馬達端累計 counts，單調連續

  bool has_alarm() const { return alarm != 0; }
};

struct DualFeedback
{
  MotorFeedback right;
  MotorFeedback left;
  double comm_s = 0.0;
};

uint16_t net_in_word(
  bool servo_en = false, bool free = false, bool fwd = false,
  bool rev = false, bool alm_rst = false);

/// 左右輪驅動器控制與狀態讀取。
class DriverInterface
{
public:
  DriverInterface(Md2Transport & transport, int right_id, int left_id);

  int right_id() const { return right_id_; }
  int left_id() const { return left_id_; }

  /// 每馬達轉之 counts，由 01-06 推導；須先呼叫 validate_configuration()。
  int counts_per_motor_rev() const;

  /// 驗證驅動器組態並推導每轉 counts。
  ///
  /// 本專案要求 02-14 = 0。驅動器端不做持久化設定，讀到其他值代表驅動器
  /// 曾被更改或更換，直接視為錯誤而非靜默容忍，避免無聲之里程誤差。
  int validate_configuration();

  void enable();

  /// SERVO-EN OFF。安全關鍵：逐顆獨立嘗試並重試，單顆失敗不影響另一顆。
  void disable(int retries = 2);

  void set_free();
  void alarm_reset();

  void apply_motion_profile(
    uint16_t linear_acc_ms, uint16_t linear_dec_ms,
    uint16_t s_curve_acc_ms, uint16_t s_curve_dec_ms);

  /// 下達雙輪馬達端轉速命令並讀回回授。
  DualFeedback command(int16_t right_rpm, int16_t left_rpm);

  /// 立即停止，維持激磁。
  DualFeedback stop();

  /// 清除 turns 繞回追蹤狀態；重新連線或啟用時應呼叫。
  void reset_position_tracking();

private:
  struct TurnsTracker
  {
    std::optional<int16_t> last_raw;
    int64_t offset = 0;
  };

  DualFeedback exchange(uint16_t cmd, int16_t right_rpm, int16_t left_rpm);
  MotorFeedback decode(TurnsTracker & tracker, const DriverRaw & raw) const;

  /// 將 signed 16-bit turns 還原為連續累計圈數。
  ///
  /// 以「原始值 + 累計補償量」而非逐次累加差值計算，
  /// 使偶發異常讀值僅造成單次尖峰，不會永久污染位置。
  static int64_t accumulate_turns(TurnsTracker & tracker, int16_t raw_turns);

  void write_net_in_both(uint16_t word, bool best_effort = false, int retries = 0);
  void write_register_both(int address, uint16_t value, bool best_effort = false, int retries = 0);

  Md2Transport & transport_;
  int right_id_;
  int left_id_;
  int counts_per_motor_rev_ = 0;
  TurnsTracker right_turns_;
  TurnsTracker left_turns_;
};

}  // namespace base_control

#endif  // BASE_CONTROL__DRIVER_INTERFACE_HPP_

#include "base_control/base_control_hardware.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <string>
#include <vector>

#include "hardware_interface/types/hardware_interface_type_values.hpp"
#include "pluginlib/class_list_macros.hpp"

namespace base_control
{

namespace
{

constexpr double kTwoPi = 2.0 * M_PI;
constexpr double kRpmToRadS = kTwoPi / 60.0;

/// 連續通訊失敗達此次數即回報錯誤，交由 controller_manager 處置。
constexpr int kMaxConsecutiveFaults = 5;

template<typename T>
bool read_param(
  const std::unordered_map<std::string, std::string> & params,
  const std::string & key, T & target, const rclcpp::Logger & logger)
{
  const auto it = params.find(key);
  if (it == params.end()) {
    return true;  // 未提供則沿用預設值
  }
  try {
    if constexpr (std::is_same_v<T, std::string>) {
      target = it->second;
    } else if constexpr (std::is_floating_point_v<T>) {
      target = static_cast<T>(std::stod(it->second));
    } else {
      target = static_cast<T>(std::stol(it->second));
    }
  } catch (const std::exception & exc) {
    RCLCPP_ERROR(logger, "參數 %s 值 '%s' 無法解析：%s", key.c_str(), it->second.c_str(), exc.what());
    return false;
  }
  return true;
}

int normalize_sign(int value)
{
  return value >= 0 ? 1 : -1;
}

}  // namespace

// ── 生命週期 ─────────────────────────────────────────────────────────────────

hardware_interface::CallbackReturn BaseControlHardware::on_init(
  const hardware_interface::HardwareComponentInterfaceParams & params)
{
  if (SystemInterface::on_init(params) != CallbackReturn::SUCCESS) {
    return CallbackReturn::ERROR;
  }
  if (!load_params() || !resolve_joints()) {
    return CallbackReturn::ERROR;
  }

  // 使用框架提供之節點，不另建節點與執行緒
  diagnostics_pub_ = get_node()->create_publisher<diagnostic_msgs::msg::DiagnosticArray>(
    "/driver/status", rclcpp::QoS(10));
  last_diagnostics_time_ = rclcpp::Time(0, 0, RCL_ROS_TIME);

  RCLCPP_INFO(
    get_logger(), "base_control 初始化：%s @ %d，右輪 ID %d、左輪 ID %d",
    params_.serial_port.c_str(), params_.serial_baud,
    params_.right_driver_id, params_.left_driver_id);
  return CallbackReturn::SUCCESS;
}

hardware_interface::CallbackReturn BaseControlHardware::on_configure(
  const rclcpp_lifecycle::State & /*previous_state*/)
{
  try {
    transport_.open(
      params_.serial_port, params_.serial_baud, 'N', 8, 1, params_.serial_timeout_s);
    driver_ = std::make_unique<DriverInterface>(
      transport_, params_.right_driver_id, params_.left_driver_id);

    const int counts_per_motor_rev = driver_->validate_configuration();
    counts_per_wheel_rev_ = static_cast<double>(counts_per_motor_rev) * params_.gear_ratio;
    RCLCPP_INFO(
      get_logger(), "驅動器組態確認，每馬達轉 %d counts，每輪轉 %.0f counts",
      counts_per_motor_rev, counts_per_wheel_rev_);

    driver_->apply_motion_profile(
      params_.linear_acc_ms, params_.linear_dec_ms,
      params_.s_curve_acc_ms, params_.s_curve_dec_ms);
  } catch (const std::exception & exc) {
    RCLCPP_ERROR(get_logger(), "on_configure 失敗：%s", exc.what());
    transport_.close();
    driver_.reset();
    return CallbackReturn::ERROR;
  }
  return CallbackReturn::SUCCESS;
}

hardware_interface::CallbackReturn BaseControlHardware::on_activate(
  const rclcpp_lifecycle::State & /*previous_state*/)
{
  try {
    driver_->reset_position_tracking();
    driver_->enable();

    // 先以 speed=0 取得初始位置，避免第一次 read() 無資料
    feedback_ = driver_->stop();
    feedback_valid_ = true;
    consecutive_faults_ = 0;

    set_command(left_joint_ + "/velocity", 0.0);
    set_command(right_joint_ + "/velocity", 0.0);
  } catch (const std::exception & exc) {
    RCLCPP_ERROR(get_logger(), "on_activate 失敗：%s", exc.what());
    return CallbackReturn::ERROR;
  }
  RCLCPP_INFO(get_logger(), "驅動器已激磁");
  return CallbackReturn::SUCCESS;
}

hardware_interface::CallbackReturn BaseControlHardware::on_deactivate(
  const rclcpp_lifecycle::State & /*previous_state*/)
{
  if (!driver_) {
    return CallbackReturn::SUCCESS;
  }

  // 中斷可能發生於交易途中，殘留回應會使後續請求失去同步
  transport_.drain();

  try {
    driver_->stop();
  } catch (const std::exception & exc) {
    RCLCPP_ERROR(get_logger(), "停止命令失敗：%s", exc.what());
    transport_.drain();
  }

  try {
    driver_->disable();
    RCLCPP_INFO(get_logger(), "驅動器已停止並解除激磁");
  } catch (const std::exception & exc) {
    RCLCPP_ERROR(get_logger(), "解除激磁失敗：%s", exc.what());
    return CallbackReturn::ERROR;
  }

  feedback_valid_ = false;
  return CallbackReturn::SUCCESS;
}

hardware_interface::CallbackReturn BaseControlHardware::on_cleanup(
  const rclcpp_lifecycle::State & /*previous_state*/)
{
  driver_.reset();
  transport_.close();
  return CallbackReturn::SUCCESS;
}

hardware_interface::CallbackReturn BaseControlHardware::on_shutdown(
  const rclcpp_lifecycle::State & previous_state)
{
  return on_cleanup(previous_state);
}

// ── 控制迴圈 ─────────────────────────────────────────────────────────────────

hardware_interface::return_type BaseControlHardware::read(
  const rclcpp::Time & time, const rclcpp::Duration & /*period*/)
{
  if (!driver_) {
    return hardware_interface::return_type::ERROR;
  }

  // FC17h 為讀寫合一，交易置於 read() 使回授時間戳與本週期一致，
  // 避免里程積分產生一個週期之時間誤差。命令取自上一次 write()。
  int16_t left_rpm = 0;
  int16_t right_rpm = 0;
  to_motor_rpm(
    get_command<double>(left_joint_ + "/velocity"),
    get_command<double>(right_joint_ + "/velocity"),
    left_rpm, right_rpm);

  try {
    feedback_ = driver_->command(right_rpm, left_rpm);
    feedback_valid_ = true;
    consecutive_faults_ = 0;
  } catch (const std::exception & exc) {
    ++consecutive_faults_;
    RCLCPP_WARN(
      get_logger(), "通訊失敗（%d/%d）：%s",
      consecutive_faults_, kMaxConsecutiveFaults, exc.what());
    transport_.drain();
    if (consecutive_faults_ >= kMaxConsecutiveFaults) {
      RCLCPP_ERROR(get_logger(), "連續通訊失敗達上限，回報硬體錯誤");
      return hardware_interface::return_type::ERROR;
    }
    return hardware_interface::return_type::OK;  // 暫態失敗沿用前次狀態
  }

  const auto to_wheel_rad = [this](int64_t counts, int sign) {
      return static_cast<double>(counts) / counts_per_wheel_rev_ * kTwoPi * sign;
    };
  const auto to_wheel_rad_s = [this](int16_t motor_rpm, int sign) {
      return motor_rpm * kRpmToRadS / params_.gear_ratio * sign;
    };

  set_state(
    left_joint_ + "/position",
    to_wheel_rad(feedback_.left.position_counts, params_.left_feedback_sign));
  set_state(
    right_joint_ + "/position",
    to_wheel_rad(feedback_.right.position_counts, params_.right_feedback_sign));
  set_state(
    left_joint_ + "/velocity",
    to_wheel_rad_s(feedback_.left.rpm, params_.left_feedback_sign));
  set_state(
    right_joint_ + "/velocity",
    to_wheel_rad_s(feedback_.right.rpm, params_.right_feedback_sign));

  publish_diagnostics(time);

  if (feedback_.left.has_alarm() || feedback_.right.has_alarm()) {
    RCLCPP_ERROR_THROTTLE(
      get_logger(), *get_clock(), 1000,
      "驅動器警報 right=%u left=%u", feedback_.right.alarm, feedback_.left.alarm);
    return hardware_interface::return_type::ERROR;
  }
  return hardware_interface::return_type::OK;
}

hardware_interface::return_type BaseControlHardware::write(
  const rclcpp::Time & /*time*/, const rclcpp::Duration & /*period*/)
{
  // 命令於下一次 read() 之 FC17h 交易一併送出，此處不進行匯流排存取。
  return hardware_interface::return_type::OK;
}

// ── 換算 ─────────────────────────────────────────────────────────────────────

void BaseControlHardware::to_motor_rpm(
  double left_wheel_rad_s, double right_wheel_rad_s,
  int16_t & left_motor_rpm, int16_t & right_motor_rpm) const
{
  if (!std::isfinite(left_wheel_rad_s)) {left_wheel_rad_s = 0.0;}
  if (!std::isfinite(right_wheel_rad_s)) {right_wheel_rad_s = 0.0;}

  double left = left_wheel_rad_s * params_.gear_ratio / kRpmToRadS;
  double right = right_wheel_rad_s * params_.gear_ratio / kRpmToRadS;

  // 超過上限時兩輪等比縮放，保持 v/omega 比值，避免獨立截斷改變行進方向
  const double peak = std::max(std::abs(left), std::abs(right));
  const double limit = static_cast<double>(params_.max_motor_rpm);
  if (peak > limit) {
    const double scale = limit / peak;
    left *= scale;
    right *= scale;
  }

  // 低於最小有效轉速時驅動器控制不穩定，抬升至下限。
  // 兩輪各自套用，故極低速轉彎時 v/omega 比值會失真；此限制源自驅動器特性。
  const auto apply_deadband = [this](double rpm) {
      const double minimum = static_cast<double>(params_.min_effective_motor_rpm);
      if (rpm == 0.0 || minimum == 0.0) {
        return rpm;
      }
      if (std::abs(rpm) < minimum) {
        return std::copysign(minimum, rpm);
      }
      return rpm;
    };

  left_motor_rpm = static_cast<int16_t>(
    std::lround(apply_deadband(left) * params_.left_motor_sign));
  right_motor_rpm = static_cast<int16_t>(
    std::lround(apply_deadband(right) * params_.right_motor_sign));
}

// ── 參數與 joint ─────────────────────────────────────────────────────────────

bool BaseControlHardware::load_params()
{
  const auto & p = info_.hardware_parameters;
  const auto logger = get_logger();
  bool ok = true;

  ok &= read_param(p, "serial_port", params_.serial_port, logger);
  ok &= read_param(p, "serial_baud", params_.serial_baud, logger);
  ok &= read_param(p, "serial_timeout_s", params_.serial_timeout_s, logger);
  ok &= read_param(p, "right_driver_id", params_.right_driver_id, logger);
  ok &= read_param(p, "left_driver_id", params_.left_driver_id, logger);
  ok &= read_param(p, "gear_ratio", params_.gear_ratio, logger);
  ok &= read_param(p, "max_motor_rpm", params_.max_motor_rpm, logger);
  ok &= read_param(p, "min_effective_motor_rpm", params_.min_effective_motor_rpm, logger);
  ok &= read_param(p, "right_motor_sign", params_.right_motor_sign, logger);
  ok &= read_param(p, "left_motor_sign", params_.left_motor_sign, logger);
  ok &= read_param(p, "right_feedback_sign", params_.right_feedback_sign, logger);
  ok &= read_param(p, "left_feedback_sign", params_.left_feedback_sign, logger);
  ok &= read_param(p, "linear_acc_ms", params_.linear_acc_ms, logger);
  ok &= read_param(p, "linear_dec_ms", params_.linear_dec_ms, logger);
  ok &= read_param(p, "s_curve_acc_ms", params_.s_curve_acc_ms, logger);
  ok &= read_param(p, "s_curve_dec_ms", params_.s_curve_dec_ms, logger);
  ok &= read_param(p, "diagnostics_period_s", params_.diagnostics_period_s, logger);
  if (!ok) {
    return false;
  }

  params_.right_motor_sign = normalize_sign(params_.right_motor_sign);
  params_.left_motor_sign = normalize_sign(params_.left_motor_sign);
  params_.right_feedback_sign = normalize_sign(params_.right_feedback_sign);
  params_.left_feedback_sign = normalize_sign(params_.left_feedback_sign);

  if (params_.gear_ratio <= 0.0) {
    RCLCPP_ERROR(logger, "gear_ratio 必須 > 0");
    return false;
  }
  if (params_.max_motor_rpm <= 0) {
    RCLCPP_ERROR(logger, "max_motor_rpm 必須 > 0");
    return false;
  }
  if (params_.min_effective_motor_rpm < 0 ||
    params_.min_effective_motor_rpm > params_.max_motor_rpm)
  {
    RCLCPP_ERROR(logger, "min_effective_motor_rpm 須介於 0 與 max_motor_rpm 之間");
    return false;
  }
  if (params_.right_driver_id == params_.left_driver_id) {
    RCLCPP_ERROR(logger, "right_driver_id 與 left_driver_id 不得相同");
    return false;
  }
  return true;
}

bool BaseControlHardware::resolve_joints()
{
  if (info_.joints.size() != 2) {
    RCLCPP_ERROR(
      get_logger(), "須宣告恰好 2 個 joint，實際 %zu 個", info_.joints.size());
    return false;
  }

  for (const auto & joint : info_.joints) {
    const bool has_velocity_command =
      std::any_of(
      joint.command_interfaces.begin(), joint.command_interfaces.end(),
      [](const auto & i) {return i.name == hardware_interface::HW_IF_VELOCITY;});
    const bool has_position_state =
      std::any_of(
      joint.state_interfaces.begin(), joint.state_interfaces.end(),
      [](const auto & i) {return i.name == hardware_interface::HW_IF_POSITION;});
    const bool has_velocity_state =
      std::any_of(
      joint.state_interfaces.begin(), joint.state_interfaces.end(),
      [](const auto & i) {return i.name == hardware_interface::HW_IF_VELOCITY;});

    if (!has_velocity_command || !has_position_state || !has_velocity_state) {
      RCLCPP_ERROR(
        get_logger(),
        "joint '%s' 須具備 velocity command 與 position/velocity state interface",
        joint.name.c_str());
      return false;
    }

    if (joint.name.find("_L") != std::string::npos) {
      left_joint_ = joint.name;
    } else if (joint.name.find("_R") != std::string::npos) {
      right_joint_ = joint.name;
    }
  }

  if (left_joint_.empty() || right_joint_.empty()) {
    RCLCPP_ERROR(
      get_logger(),
      "無法由 joint 名稱判別左右輪，名稱須包含 '_L' 或 '_R'（實際：%s、%s）",
      info_.joints[0].name.c_str(), info_.joints[1].name.c_str());
    return false;
  }
  return true;
}

// ── 診斷 ─────────────────────────────────────────────────────────────────────

void BaseControlHardware::publish_diagnostics(const rclcpp::Time & time)
{
  if (!diagnostics_pub_ || !feedback_valid_) {
    return;
  }
  if (last_diagnostics_time_.nanoseconds() != 0 &&
    (time - last_diagnostics_time_).seconds() < params_.diagnostics_period_s)
  {
    return;
  }
  last_diagnostics_time_ = time;

  const auto driver_status =
    [](const std::string & name, int driver_id, const MotorFeedback & motor) {
      diagnostic_msgs::msg::DiagnosticStatus status;
      status.name = "base_control: " + name;
      status.hardware_id = "M1 driver id=" + std::to_string(driver_id);
      if (motor.has_alarm()) {
        status.level = diagnostic_msgs::msg::DiagnosticStatus::ERROR;
        status.message = "警報 " + std::to_string(motor.alarm);
      } else {
        status.level = diagnostic_msgs::msg::DiagnosticStatus::OK;
        status.message = motor_status_text(motor.status);
      }
      const auto kv = [](const std::string & key, const std::string & value) {
          diagnostic_msgs::msg::KeyValue item;
          item.key = key;
          item.value = value;
          return item;
        };
      status.values = {
        kv("motor_status", std::to_string(motor.status)),
        kv("motor_status_text", motor_status_text(motor.status)),
        kv("alarm", std::to_string(motor.alarm)),
        kv("motor_rpm", std::to_string(motor.rpm)),
        kv("position_counts", std::to_string(motor.position_counts)),
      };
      return status;
    };

  diagnostic_msgs::msg::DiagnosticStatus comm;
  comm.name = "base_control: communication";
  comm.hardware_id = params_.serial_port;
  comm.level = consecutive_faults_ > 0
    ? diagnostic_msgs::msg::DiagnosticStatus::WARN
    : diagnostic_msgs::msg::DiagnosticStatus::OK;
  comm.message = consecutive_faults_ > 0
    ? "連續失敗 " + std::to_string(consecutive_faults_) + " 次"
    : "正常";
  {
    diagnostic_msgs::msg::KeyValue transaction;
    transaction.key = "transaction_ms";
    transaction.value = std::to_string(feedback_.comm_s * 1000.0);
    diagnostic_msgs::msg::KeyValue faults;
    faults.key = "consecutive_faults";
    faults.value = std::to_string(consecutive_faults_);
    comm.values = {transaction, faults};
  }

  diagnostic_msgs::msg::DiagnosticArray array;
  array.header.stamp = time;
  array.status = {
    driver_status("right_wheel_driver", params_.right_driver_id, feedback_.right),
    driver_status("left_wheel_driver", params_.left_driver_id, feedback_.left),
    comm,
  };
  diagnostics_pub_->publish(array);
}

}  // namespace base_control

PLUGINLIB_EXPORT_CLASS(
  base_control::BaseControlHardware, hardware_interface::SystemInterface)

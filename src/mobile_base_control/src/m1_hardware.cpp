// Copyright 2026 mobile_base contributors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include "mobile_base_control/m1_hardware.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <limits>
#include <memory>
#include <string>
#include <thread>
#include <utility>
#include <vector>

#include "pluginlib/class_list_macros.hpp"
#include "rclcpp/rclcpp.hpp"

namespace mobile_base_control
{

namespace
{
constexpr double PI = 3.14159265358979323846;
constexpr double RAD_S_TO_RPM = 60.0 / (2.0 * PI);
constexpr double RPM_TO_RAD_S = (2.0 * PI) / 60.0;
}  // namespace

M1Hardware::M1Hardware()
: driver_(std::make_shared<M1Driver>())
{
}

M1Hardware::M1Hardware(std::shared_ptr<M1Driver> driver)
: driver_(std::move(driver))
{
  if (!driver_) {
    driver_ = std::make_shared<M1Driver>();
  }
}

M1Hardware::~M1Hardware()
{
  if (driver_ && driver_->is_connected()) {
    driver_->stop(config_.right_driver_id, config_.left_driver_id);
    driver_->disable(config_.right_driver_id, config_.left_driver_id);
    driver_->disconnect();
  }
}

void M1Hardware::set_driver_for_testing(std::shared_ptr<M1Driver> driver) noexcept
{
  driver_ = std::move(driver);
}

int16_t M1Hardware::wheel_rad_s_to_motor_rpm(
  double wheel_rad_s,
  double gear_ratio,
  int motor_sign,
  double max_motor_rpm) noexcept
{
  if (std::isnan(wheel_rad_s) || std::isinf(wheel_rad_s) || gear_ratio <= 0.0) {
    return 0;
  }
  const double rpm_unclamped = wheel_rad_s * gear_ratio * RAD_S_TO_RPM *
    static_cast<double>(motor_sign);
  const double abs_max = std::min(std::abs(max_motor_rpm), 32767.0);
  const double rpm_clamped = std::clamp(rpm_unclamped, -abs_max, abs_max);
  return static_cast<int16_t>(std::lround(rpm_clamped));
}

double M1Hardware::motor_rpm_to_wheel_rad_s(
  int16_t actual_rpm,
  double gear_ratio,
  int motor_sign) noexcept
{
  if (gear_ratio <= 0.0) {
    return 0.0;
  }
  return (static_cast<double>(actual_rpm) * static_cast<double>(motor_sign) / gear_ratio) *
         RPM_TO_RAD_S;
}

double M1Hardware::motor_steps_to_wheel_rad(
  int64_t accumulated_steps,
  double motor_steps_per_rev,
  double gear_ratio,
  int motor_sign) noexcept
{
  const double steps_per_wheel_rev = motor_steps_per_rev * gear_ratio;
  if (steps_per_wheel_rev <= 0.0) {
    return 0.0;
  }
  return (static_cast<double>(accumulated_steps) / steps_per_wheel_rev) * (2.0 * PI) *
         static_cast<double>(motor_sign);
}

hardware_interface::CallbackReturn M1Hardware::parse_parameters()
{
  const auto & params = info_.hardware_parameters;

  if (params.find("serial_port") != params.end()) {
    config_.serial_port = params.at("serial_port");
  } else if (params.find("device") != params.end()) {
    config_.serial_port = params.at("device");
  }

  if (params.find("baud_rate") != params.end()) {
    config_.baud_rate = std::stoi(params.at("baud_rate"));
  } else if (params.find("baud") != params.end()) {
    config_.baud_rate = std::stoi(params.at("baud"));
  }

  if (params.find("response_timeout_ms") != params.end()) {
    try {
      const int64_t val = std::stoll(params.at("response_timeout_ms"));
      if (val <= 0) {
        RCLCPP_FATAL(
          get_logger(),
          "response_timeout_ms must be positive, got %lld",
          static_cast<long long>(val));  // NOLINT(runtime/int)
        return hardware_interface::CallbackReturn::ERROR;
      }
      config_.timeout_ms = static_cast<uint32_t>(val);
    } catch (const std::exception & e) {
      RCLCPP_FATAL(
        get_logger(),
        "Invalid response_timeout_ms parameter '%s': %s",
        params.at("response_timeout_ms").c_str(), e.what());
      return hardware_interface::CallbackReturn::ERROR;
    }
  } else if (params.find("timeout_ms") != params.end()) {
    try {
      const int64_t val = std::stoll(params.at("timeout_ms"));
      if (val <= 0) {
        RCLCPP_FATAL(
          get_logger(),
          "timeout_ms must be positive, got %lld",
          static_cast<long long>(val));  // NOLINT(runtime/int)
        return hardware_interface::CallbackReturn::ERROR;
      }
      config_.timeout_ms = static_cast<uint32_t>(val);
    } catch (const std::exception & e) {
      RCLCPP_FATAL(
        get_logger(),
        "Invalid timeout_ms parameter '%s': %s",
        params.at("timeout_ms").c_str(), e.what());
      return hardware_interface::CallbackReturn::ERROR;
    }
  } else {
    RCLCPP_FATAL(
      get_logger(),
      "Missing required parameter 'response_timeout_ms' (or 'timeout_ms') in URDF/hardware "
      "configuration. No production default is assumed (final production timeout pending "
      "real-hardware latency measurement).");
    return hardware_interface::CallbackReturn::ERROR;
  }

  if (params.find("left_driver_id") != params.end()) {
    config_.left_driver_id = std::stoi(params.at("left_driver_id"));
  }
  if (params.find("right_driver_id") != params.end()) {
    config_.right_driver_id = std::stoi(params.at("right_driver_id"));
  }

  if (params.find("gear_ratio") != params.end()) {
    config_.gear_ratio = std::stod(params.at("gear_ratio"));
  }

  if (params.find("left_wheel_sign") != params.end()) {
    config_.left_wheel_sign = std::stoi(params.at("left_wheel_sign"));
  } else if (params.find("left_sign") != params.end()) {
    config_.left_wheel_sign = std::stoi(params.at("left_sign"));
  }

  if (params.find("right_wheel_sign") != params.end()) {
    config_.right_wheel_sign = std::stoi(params.at("right_wheel_sign"));
  } else if (params.find("right_sign") != params.end()) {
    config_.right_wheel_sign = std::stoi(params.at("right_sign"));
  }

  if (params.find("motor_steps_per_rev") != params.end()) {
    config_.motor_steps_per_rev = std::stod(params.at("motor_steps_per_rev"));
  } else if (params.find("encoder_cpr") != params.end()) {
    config_.motor_steps_per_rev = std::stod(params.at("encoder_cpr"));
  }

  if (params.find("max_motor_rpm") != params.end()) {
    config_.max_motor_rpm = std::stod(params.at("max_motor_rpm"));
  }

  if (params.find("left_wheel_name") != params.end()) {
    config_.left_wheel_name = params.at("left_wheel_name");
  }
  if (params.find("right_wheel_name") != params.end()) {
    config_.right_wheel_name = params.at("right_wheel_name");
  }

  // Validate hardware info joints if provided
  if (!info_.joints.empty()) {
    if (info_.joints.size() != 2) {
      RCLCPP_FATAL(
        get_logger(),
        "M1Hardware expects exactly 2 joints, but got %zu",
        info_.joints.size());
      return hardware_interface::CallbackReturn::ERROR;
    }
    for (size_t i = 0; i < info_.joints.size(); ++i) {
      const auto & joint = info_.joints[i];
      if (joint.command_interfaces.empty() ||
        joint.command_interfaces[0].name != hardware_interface::HW_IF_VELOCITY)
      {
        RCLCPP_FATAL(
          get_logger(),
          "Joint '%s' missing required '%s' command interface",
          joint.name.c_str(), hardware_interface::HW_IF_VELOCITY);
        return hardware_interface::CallbackReturn::ERROR;
      }
      bool has_pos = false;
      bool has_vel = false;
      for (const auto & si : joint.state_interfaces) {
        if (si.name == hardware_interface::HW_IF_POSITION) {
          has_pos = true;
        }
        if (si.name == hardware_interface::HW_IF_VELOCITY) {
          has_vel = true;
        }
      }
      if (!has_pos || !has_vel) {
        RCLCPP_FATAL(
          get_logger(),
          "Joint '%s' missing required position or velocity state interfaces",
          joint.name.c_str());
        return hardware_interface::CallbackReturn::ERROR;
      }
    }
    // Update joint names from parsed info if not explicitly overridden
    if (params.find("left_wheel_name") == params.end() &&
      params.find("right_wheel_name") == params.end())
    {
      config_.left_wheel_name = info_.joints[0].name;
      config_.right_wheel_name = info_.joints[1].name;
    }
  }

  if (config_.gear_ratio <= 0.0) {
    RCLCPP_FATAL(get_logger(), "gear_ratio must be positive, got %f", config_.gear_ratio);
    return hardware_interface::CallbackReturn::ERROR;
  }
  if (config_.left_wheel_sign != 1 && config_.left_wheel_sign != -1) {
    RCLCPP_FATAL(
      get_logger(), "left_wheel_sign must be +1 or -1, got %d",
      config_.left_wheel_sign);
    return hardware_interface::CallbackReturn::ERROR;
  }
  if (config_.right_wheel_sign != 1 && config_.right_wheel_sign != -1) {
    RCLCPP_FATAL(
      get_logger(), "right_wheel_sign must be +1 or -1, got %d",
      config_.right_wheel_sign);
    return hardware_interface::CallbackReturn::ERROR;
  }
  if (config_.motor_steps_per_rev <= 0.0) {
    RCLCPP_FATAL(
      get_logger(), "motor_steps_per_rev must be positive, got %f",
      config_.motor_steps_per_rev);
    return hardware_interface::CallbackReturn::ERROR;
  }

  return hardware_interface::CallbackReturn::SUCCESS;
}

hardware_interface::CallbackReturn M1Hardware::on_init(
  const hardware_interface::HardwareComponentInterfaceParams & params)
{
  if (hardware_interface::SystemInterface::on_init(params) !=
    hardware_interface::CallbackReturn::SUCCESS)
  {
    return hardware_interface::CallbackReturn::ERROR;
  }

  if (parse_parameters() != hardware_interface::CallbackReturn::SUCCESS) {
    return hardware_interface::CallbackReturn::ERROR;
  }

  RCLCPP_INFO(
    get_logger(),
    "M1Hardware initialized: Left='%s' (ID %d, sign %+d), Right='%s' (ID %d, sign %+d), "
    "gear_ratio=%.2f, port='%s'@%d, timeout=%u ms",
    config_.left_wheel_name.c_str(), config_.left_driver_id, config_.left_wheel_sign,
    config_.right_wheel_name.c_str(), config_.right_driver_id, config_.right_wheel_sign,
    config_.gear_ratio, config_.serial_port.c_str(), config_.baud_rate, config_.timeout_ms);

  return hardware_interface::CallbackReturn::SUCCESS;
}

hardware_interface::CallbackReturn M1Hardware::on_configure(
  const rclcpp_lifecycle::State & /*previous_state*/)
{
  RCLCPP_INFO(get_logger(), "Configuring M1Hardware on port '%s'...", config_.serial_port.c_str());

  if (!driver_) {
    driver_ = std::make_shared<M1Driver>();
  }

  if (!driver_->is_connected()) {
    auto conn_res = driver_->connect(
      config_.serial_port,
      config_.baud_rate,
      config_.timeout_ms);
    if (!conn_res.ok) {
      RCLCPP_ERROR(
        get_logger(),
        "Failed to connect to M1 serial port '%s': error %s",
        config_.serial_port.c_str(),
        error_code_to_string(conn_res.error));
      return hardware_interface::CallbackReturn::FAILURE;
    }
  }

  RCLCPP_INFO(get_logger(), "M1Hardware configured and connected successfully.");
  return hardware_interface::CallbackReturn::SUCCESS;
}

std::vector<hardware_interface::StateInterface> M1Hardware::export_state_interfaces()
{
  std::vector<hardware_interface::StateInterface> state_interfaces;

  // Left wheel state interfaces [0]
  state_interfaces.emplace_back(
    config_.left_wheel_name,
    hardware_interface::HW_IF_POSITION,
    &hw_positions_[0]);
  state_interfaces.emplace_back(
    config_.left_wheel_name,
    hardware_interface::HW_IF_VELOCITY,
    &hw_velocities_[0]);

  // Right wheel state interfaces [1]
  state_interfaces.emplace_back(
    config_.right_wheel_name,
    hardware_interface::HW_IF_POSITION,
    &hw_positions_[1]);
  state_interfaces.emplace_back(
    config_.right_wheel_name,
    hardware_interface::HW_IF_VELOCITY,
    &hw_velocities_[1]);

  return state_interfaces;
}

std::vector<hardware_interface::CommandInterface> M1Hardware::export_command_interfaces()
{
  std::vector<hardware_interface::CommandInterface> command_interfaces;

  // Left wheel command interface [0]
  command_interfaces.emplace_back(
    config_.left_wheel_name,
    hardware_interface::HW_IF_VELOCITY,
    &hw_commands_[0]);

  // Right wheel command interface [1]
  command_interfaces.emplace_back(
    config_.right_wheel_name,
    hardware_interface::HW_IF_VELOCITY,
    &hw_commands_[1]);

  return command_interfaces;
}

hardware_interface::CallbackReturn M1Hardware::on_activate(
  const rclcpp_lifecycle::State & /*previous_state*/)
{
  RCLCPP_INFO(get_logger(), "Activating M1Hardware (engaging Servo-On)...");

  // 1. Reset commands and position origins
  hw_commands_[0] = 0.0;
  hw_commands_[1] = 0.0;
  hw_positions_[0] = 0.0;
  hw_positions_[1] = 0.0;
  hw_velocities_[0] = 0.0;
  hw_velocities_[1] = 0.0;

  left_position_tracker_.reset();
  right_position_tracker_.reset();

  if (!driver_ || !driver_->is_connected()) {
    RCLCPP_ERROR(get_logger(), "Cannot activate: driver is not connected");
    return hardware_interface::CallbackReturn::ERROR;
  }

  // 2. Pre-activation check: read current state (with bounded retry for transient bus settling)
  Result<ExchangeResult> pre_res = Result<ExchangeResult>::failure(ErrorCode::RECEIVE_FAILED);
  for (int attempt = 0; attempt < 3; ++attempt) {
    pre_res = driver_->read_state(config_.right_driver_id, config_.left_driver_id);
    if (pre_res.ok) {
      break;
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(20));
  }
  if (!pre_res.ok) {
    RCLCPP_ERROR(
      get_logger(),
      "Activation pre-check read_state failed: error %s",
      error_code_to_string(pre_res.error));
    return hardware_interface::CallbackReturn::ERROR;
  }
  if (pre_res.value.states[0].alarm != 0 || pre_res.value.states[1].alarm != 0) {
    RCLCPP_ERROR(
      get_logger(),
      "Activation aborted: active alarm detected (Right alarm=%u, Left alarm=%u)",
      pre_res.value.states[0].alarm,
      pre_res.value.states[1].alarm);
    return hardware_interface::CallbackReturn::ERROR;
  }

  // 3. Send SVON enable command (with bounded retry for transient bus settling)
  bool enable_ok = false;
  for (int attempt = 0; attempt < 3; ++attempt) {
    auto enable_res = driver_->enable(config_.right_driver_id, config_.left_driver_id);
    if (enable_res.ok) {
      enable_ok = true;
      break;
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(20));
  }
  if (!enable_ok) {
    RCLCPP_ERROR(get_logger(), "Activation enable command failed after 3 attempts");
    return hardware_interface::CallbackReturn::ERROR;
  }

  // 4. Bounded polling until drives leave WAIT/INHIBIT (status == 6) and reach active state
  bool activated = false;
  ExchangeResult active_state{};

  for (int attempt = 0; attempt < config_.activate_poll_max_attempts; ++attempt) {
    std::this_thread::sleep_for(std::chrono::milliseconds(config_.activate_poll_interval_ms));
    auto poll_res = driver_->read_state(config_.right_driver_id, config_.left_driver_id);
    if (!poll_res.ok) {
      RCLCPP_WARN(
        get_logger(),
        "Activation poll attempt %d failed: %s",
        attempt + 1,
        error_code_to_string(poll_res.error));
      continue;
    }

    const auto & st_right = poll_res.value.states[0];
    const auto & st_left = poll_res.value.states[1];

    if (st_right.alarm != 0 || st_left.alarm != 0) {
      RCLCPP_ERROR(
        get_logger(),
        "Alarm raised during activation poll: Right alarm=%u, Left alarm=%u",
        st_right.alarm, st_left.alarm);
      driver_->disable(config_.right_driver_id, config_.left_driver_id);
      return hardware_interface::CallbackReturn::ERROR;
    }

    // Check if status transitioned away from WAIT/INHIBIT (6) to active
    if (st_right.status != 6 && st_left.status != 6) {
      active_state = poll_res.value;
      activated = true;
      break;
    }
  }

  if (!activated) {
    RCLCPP_ERROR(
      get_logger(),
      "Activation timed out waiting for drivers to enter active state; sending disable cleanup");
    driver_->disable(config_.right_driver_id, config_.left_driver_id);
    return hardware_interface::CallbackReturn::ERROR;
  }

  // Initialize position trackers with the baseline active sample
  right_position_tracker_.update(active_state.states[0].position_steps);
  left_position_tracker_.update(active_state.states[1].position_steps);

  latest_motor_state_ = active_state;
  has_valid_state_ = true;
  is_active_ = true;

  RCLCPP_INFO(get_logger(), "M1Hardware activated successfully.");
  return hardware_interface::CallbackReturn::SUCCESS;
}

hardware_interface::CallbackReturn M1Hardware::on_deactivate(
  const rclcpp_lifecycle::State & /*previous_state*/)
{
  RCLCPP_INFO(get_logger(), "Deactivating M1Hardware (executing stop and disable sequence)...");

  hw_commands_[0] = 0.0;
  hw_commands_[1] = 0.0;
  is_active_ = false;

  if (driver_ && driver_->is_connected()) {
    // 1. Stop primitive (JG 0)
    auto stop_res = driver_->stop(config_.right_driver_id, config_.left_driver_id);
    if (!stop_res.ok) {
      RCLCPP_WARN(
        get_logger(),
        "Stop command during deactivation failed (%s), continuing best-effort cleanup",
        error_code_to_string(stop_res.error));
    }

    // 2. Bounded zero-RPM confirmation delay
    std::this_thread::sleep_for(std::chrono::milliseconds(config_.stop_poll_interval_ms));

    // 3. Disable primitive (SVOFF)
    auto disable_res = driver_->disable(config_.right_driver_id, config_.left_driver_id);
    if (!disable_res.ok) {
      RCLCPP_WARN(
        get_logger(),
        "Disable command during deactivation failed (%s), continuing best-effort cleanup",
        error_code_to_string(disable_res.error));
    }
  }

  has_valid_state_ = false;
  RCLCPP_INFO(get_logger(), "M1Hardware deactivated successfully.");
  return hardware_interface::CallbackReturn::SUCCESS;
}

hardware_interface::CallbackReturn M1Hardware::on_cleanup(
  const rclcpp_lifecycle::State & /*previous_state*/)
{
  RCLCPP_INFO(get_logger(), "Cleaning up M1Hardware...");
  is_active_ = false;
  has_valid_state_ = false;
  if (driver_ && driver_->is_connected()) {
    driver_->disconnect();
  }
  return hardware_interface::CallbackReturn::SUCCESS;
}

hardware_interface::CallbackReturn M1Hardware::on_shutdown(
  const rclcpp_lifecycle::State & /*previous_state*/)
{
  RCLCPP_INFO(get_logger(), "Shutting down M1Hardware...");
  is_active_ = false;
  has_valid_state_ = false;
  if (driver_ && driver_->is_connected()) {
    driver_->stop(config_.right_driver_id, config_.left_driver_id);
    driver_->disable(config_.right_driver_id, config_.left_driver_id);
    driver_->disconnect();
  }
  return hardware_interface::CallbackReturn::SUCCESS;
}

hardware_interface::CallbackReturn M1Hardware::on_error(
  const rclcpp_lifecycle::State & /*previous_state*/)
{
  RCLCPP_ERROR(
    get_logger(),
    "M1Hardware entered ERROR state, executing best-effort safety cleanup");
  is_active_ = false;
  has_valid_state_ = false;
  if (driver_ && driver_->is_connected()) {
    driver_->stop(config_.right_driver_id, config_.left_driver_id);
    driver_->disable(config_.right_driver_id, config_.left_driver_id);
    driver_->disconnect();
  }
  return hardware_interface::CallbackReturn::SUCCESS;
}

hardware_interface::return_type M1Hardware::read(
  const rclcpp::Time & /*time*/,
  const rclcpp::Duration & /*period*/)
{
  if (!is_active_ || !has_valid_state_) {
    RCLCPP_ERROR(
      get_logger(),
      "read() called without valid cached motor state or while component is inactive");
    return hardware_interface::return_type::ERROR;
  }

  const auto & st_right = latest_motor_state_.states[0];
  const auto & st_left = latest_motor_state_.states[1];

  // Device health policy: check for active drive alarms
  if (st_right.alarm != 0 || st_left.alarm != 0) {
    RCLCPP_ERROR(
      get_logger(),
      "Drive alarm detected during read(): Right ID%d alarm=%u, Left ID%d alarm=%u",
      config_.right_driver_id, st_right.alarm,
      config_.left_driver_id, st_left.alarm);
    return hardware_interface::return_type::ERROR;
  }

  // Update position accumulators with raw steps
  left_position_tracker_.update(st_left.position_steps);
  right_position_tracker_.update(st_right.position_steps);

  // Convert accumulated steps -> Continuous wheel position [rad]
  hw_positions_[0] = motor_steps_to_wheel_rad(
    left_position_tracker_.accumulated_steps,
    config_.motor_steps_per_rev,
    config_.gear_ratio,
    config_.left_wheel_sign);

  hw_positions_[1] = motor_steps_to_wheel_rad(
    right_position_tracker_.accumulated_steps,
    config_.motor_steps_per_rev,
    config_.gear_ratio,
    config_.right_wheel_sign);

  // Convert actual RPM -> Wheel angular velocity [rad/s]
  hw_velocities_[0] = motor_rpm_to_wheel_rad_s(
    st_left.actual_rpm,
    config_.gear_ratio,
    config_.left_wheel_sign);

  hw_velocities_[1] = motor_rpm_to_wheel_rad_s(
    st_right.actual_rpm,
    config_.gear_ratio,
    config_.right_wheel_sign);

  return hardware_interface::return_type::OK;
}

hardware_interface::return_type M1Hardware::write(
  const rclcpp::Time & /*time*/,
  const rclcpp::Duration & /*period*/)
{
  if (!is_active_) {
    RCLCPP_ERROR(get_logger(), "write() called on inactive hardware component");
    return hardware_interface::return_type::ERROR;
  }

  // 1. Defensive command validation
  if (std::isnan(hw_commands_[0]) || std::isinf(hw_commands_[0]) ||
    std::isnan(hw_commands_[1]) || std::isinf(hw_commands_[1]))
  {
    RCLCPP_ERROR(
      get_logger(),
      "Invalid command received: Left=%f rad/s, Right=%f rad/s",
      hw_commands_[0], hw_commands_[1]);
    hw_commands_[0] = 0.0;
    hw_commands_[1] = 0.0;
    return hardware_interface::return_type::ERROR;
  }

  // 2. Convert wheel velocity [rad/s] -> Motor RPM
  const int16_t left_rpm = wheel_rad_s_to_motor_rpm(
    hw_commands_[0],
    config_.gear_ratio,
    config_.left_wheel_sign,
    config_.max_motor_rpm);

  const int16_t right_rpm = wheel_rad_s_to_motor_rpm(
    hw_commands_[1],
    config_.gear_ratio,
    config_.right_wheel_sign,
    config_.max_motor_rpm);

  // 3. Construct MotorCommand structs (Driver A = Right / ID1, Driver B = Left / ID2)
  const MotorCommand cmd_right{config_.right_driver_id, right_rpm};
  const MotorCommand cmd_left{config_.left_driver_id, left_rpm};

  if (!driver_ || !driver_->is_connected()) {
    RCLCPP_ERROR(get_logger(), "write() failed: driver is not connected");
    return hardware_interface::return_type::ERROR;
  }

  // 4. Perform single Multi-drive 2.0 FC17 exchange transaction (Model A2)
  auto exchange_res = driver_->exchange(cmd_right, cmd_left);
  if (!exchange_res.ok) {
    RCLCPP_ERROR(
      get_logger(),
      "M1Driver exchange failed during write(): error %s (Right ID %d target=%d RPM, "
      "Left ID %d target=%d RPM)",
      error_code_to_string(exchange_res.error),
      config_.right_driver_id, right_rpm,
      config_.left_driver_id, left_rpm);
    return hardware_interface::return_type::ERROR;
  }

  // 5. Update cached latest motor state
  latest_motor_state_ = exchange_res.value;
  has_valid_state_ = true;

  // 6. Device health check on returned state
  if (latest_motor_state_.states[0].alarm != 0 || latest_motor_state_.states[1].alarm != 0) {
    RCLCPP_ERROR(
      get_logger(),
      "Drive alarm returned in write() exchange: Right ID%d alarm=%u, Left ID%d alarm=%u",
      config_.right_driver_id, latest_motor_state_.states[0].alarm,
      config_.left_driver_id, latest_motor_state_.states[1].alarm);
    return hardware_interface::return_type::ERROR;
  }

  return hardware_interface::return_type::OK;
}

}  // namespace mobile_base_control

PLUGINLIB_EXPORT_CLASS(
  mobile_base_control::M1Hardware,
  hardware_interface::SystemInterface)

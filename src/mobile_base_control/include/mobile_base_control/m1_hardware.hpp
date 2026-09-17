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

#ifndef MOBILE_BASE_CONTROL__M1_HARDWARE_HPP_
#define MOBILE_BASE_CONTROL__M1_HARDWARE_HPP_

#include <array>
#include <cmath>
#include <cstdint>
#include <memory>
#include <limits>
#include <optional>
#include <string>
#include <vector>

#include "hardware_interface/handle.hpp"
#include "hardware_interface/hardware_info.hpp"
#include "hardware_interface/system_interface.hpp"
#include "hardware_interface/types/hardware_interface_return_values.hpp"
#include "hardware_interface/types/hardware_interface_type_values.hpp"
#include "rclcpp/macros.hpp"
#include "rclcpp_lifecycle/state.hpp"

#include "mobile_base_control/m1_driver.hpp"

namespace mobile_base_control
{

/// Structure to track continuous relative motor position using Dexmart M1 Format-0 feedback.
struct PositionTracker
{
  bool initialized{false};
  Format0PositionSample previous_sample{};
  int64_t accumulated_feedback_units{0};

  void reset() noexcept
  {
    initialized = false;
    previous_sample = Format0PositionSample{};
    accumulated_feedback_units = 0;
  }

  void initialize(const Format0PositionSample & sample) noexcept
  {
    previous_sample = sample;
    accumulated_feedback_units = 0;
    initialized = true;
  }

  bool update(const Format0PositionSample & current, uint32_t radix) noexcept
  {
    if (!initialized || radix == 0) {
      return false;
    }

    int32_t index_delta =
      static_cast<int32_t>(current.index) - static_cast<int32_t>(previous_sample.index);

    if (index_delta > 32767) {
      index_delta -= 65536;
    } else if (index_delta < -32768) {
      index_delta += 65536;
    }

    const int64_t delta =
      static_cast<int64_t>(index_delta) * static_cast<int64_t>(radix) +
      static_cast<int64_t>(current.pos) -
      static_cast<int64_t>(previous_sample.pos);

    accumulated_feedback_units += delta;
    previous_sample = current;
    return true;
  }
};

/// Hardware parameters for M1Hardware configuration.
struct M1HardwareConfig
{
  std::string serial_port{"/dev/ttyUSB0"};
  int baud_rate{230400};
  uint32_t timeout_ms{0};  // REQUIRED parameter from URDF/caller; no production default

  int left_driver_id{static_cast<int>(DriveId::Left)};    // ID 2
  int right_driver_id{static_cast<int>(DriveId::Right)};  // ID 1

  double gear_ratio{20.0};
  int left_wheel_sign{1};    // +1 forward
  int right_wheel_sign{-1};  // -1 forward (native sign inversion)

  double max_motor_rpm{3000.0};         // Operational motor clamp

  std::string left_wheel_name{"driving_wheel_joint_L"};
  std::string right_wheel_name{"driving_wheel_joint_R"};

  // Activation and stop polling parameters
  int activate_poll_max_attempts{10};
  int activate_poll_interval_ms{20};
  int stop_poll_max_attempts{5};
  int stop_poll_interval_ms{20};
};

class M1Hardware : public hardware_interface::SystemInterface
{
public:
  RCLCPP_SMART_PTR_DEFINITIONS(M1Hardware)

  M1Hardware();
  explicit M1Hardware(std::shared_ptr<M1Driver> driver);
  ~M1Hardware() override;

  // ros2_control SystemInterface lifecycle callbacks
  hardware_interface::CallbackReturn on_init(
    const hardware_interface::HardwareComponentInterfaceParams & params) override;

  hardware_interface::CallbackReturn on_configure(
    const rclcpp_lifecycle::State & previous_state) override;

  hardware_interface::CallbackReturn on_activate(
    const rclcpp_lifecycle::State & previous_state) override;

  hardware_interface::CallbackReturn on_deactivate(
    const rclcpp_lifecycle::State & previous_state) override;

  hardware_interface::CallbackReturn on_cleanup(
    const rclcpp_lifecycle::State & previous_state) override;

  hardware_interface::CallbackReturn on_shutdown(
    const rclcpp_lifecycle::State & previous_state) override;

  hardware_interface::CallbackReturn on_error(
    const rclcpp_lifecycle::State & previous_state) override;

  // Command and State Interface Exports
  std::vector<hardware_interface::StateInterface> export_state_interfaces() override;
  std::vector<hardware_interface::CommandInterface> export_command_interfaces() override;

  // Real-time control loop read / write (Model A2)
  hardware_interface::return_type read(
    const rclcpp::Time & time,
    const rclcpp::Duration & period) override;

  hardware_interface::return_type write(
    const rclcpp::Time & time,
    const rclcpp::Duration & period) override;

  // Utility / Conversion functions (Pure and unit-testable)
  static int16_t wheel_rad_s_to_motor_rpm(
    double wheel_rad_s,
    double gear_ratio,
    int motor_sign,
    double max_motor_rpm) noexcept;

  static double motor_rpm_to_wheel_rad_s(
    int16_t actual_rpm,
    double gear_ratio,
    int motor_sign) noexcept;

  static double feedback_units_to_wheel_rad(
    int64_t accumulated_feedback_units,
    uint32_t feedback_units_per_rev,
    double gear_ratio,
    int motor_sign) noexcept;

  static double motor_steps_to_wheel_rad(
    int64_t accumulated_steps,
    double position_steps_per_rev,
    double gear_ratio,
    int motor_sign) noexcept
  {
    if (position_steps_per_rev <= 0.0) {
      return std::numeric_limits<double>::quiet_NaN();
    }
    return feedback_units_to_wheel_rad(
      accumulated_steps,
      static_cast<uint32_t>(std::lround(position_steps_per_rev)),
      gear_ratio,
      motor_sign);
  }

  // Named semantic constant: 4 quadrature counts per single-phase pulse.
  // Verified on current physical hardware:
  // 2500 single-phase pulses/rev -> 10000 feedback units/rev.
  // Note: Vendor documentation does not state a universal rule that every M1 model/firmware
  // always uses encoder_resolution * 4 as feedback units/rev; this relationship is supported
  // by current physical hardware verification and protocol observations.
  static constexpr int64_t kQuadratureCountsPerPulse = 4;

  // Configuration accessor & testing injection seam
  const M1HardwareConfig & get_config() const noexcept {return config_;}
  // Snapshot order: Right, Left. Empty until BOTH configuration reads succeed.
  const std::optional<std::array<M1DeviceConfig, 2>> & get_device_configs() const noexcept
  {
    return device_configs_;
  }
  const std::optional<uint32_t> & get_runtime_radix() const noexcept
  {
    return runtime_radix_;
  }
  const PositionTracker & get_left_position_tracker() const noexcept
  {
    return left_position_tracker_;
  }
  const PositionTracker & get_right_position_tracker() const noexcept
  {
    return right_position_tracker_;
  }
  void set_driver_for_testing(std::shared_ptr<M1Driver> driver) noexcept;

private:
  hardware_interface::CallbackReturn parse_parameters();

  // Internal configuration
  M1HardwareConfig config_;
  std::shared_ptr<M1Driver> driver_;
  std::optional<std::array<M1DeviceConfig, 2>> device_configs_;
  std::optional<uint32_t> runtime_radix_{std::nullopt};

  // Command storage: [0]=Left, [1]=Right
  double hw_commands_[2]{0.0, 0.0};

  // State storage: [0]=Left, [1]=Right
  double hw_positions_[2]{
    std::numeric_limits<double>::quiet_NaN(), std::numeric_limits<double>::quiet_NaN()};
  double hw_velocities_[2]{
    std::numeric_limits<double>::quiet_NaN(), std::numeric_limits<double>::quiet_NaN()};

  // Position trackers for left and right motors
  PositionTracker left_position_tracker_;
  PositionTracker right_position_tracker_;

  // Cached latest motor states (Model A2)
  ExchangeResult latest_motor_state_{};
  bool has_valid_state_{false};
  bool is_active_{false};
};

}  // namespace mobile_base_control

#endif  // MOBILE_BASE_CONTROL__M1_HARDWARE_HPP_

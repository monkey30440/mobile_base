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

/// Structure to track continuous relative motor position across int32 rollover.
struct PositionTracker
{
  bool initialized{false};
  int32_t previous_raw{0};
  int64_t accumulated_steps{0};

  void reset() noexcept
  {
    initialized = false;
    previous_raw = 0;
    accumulated_steps = 0;
  }

  void update(int32_t current_raw) noexcept
  {
    if (!initialized) {
      previous_raw = current_raw;
      accumulated_steps = 0;
      initialized = true;
      return;
    }
    // 2's complement difference accurately handles rollover between -2^31 and 2^31-1
    const int32_t delta = static_cast<int32_t>(
      static_cast<uint32_t>(current_raw) - static_cast<uint32_t>(previous_raw));
    accumulated_steps += static_cast<int64_t>(delta);
    previous_raw = current_raw;
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

  double motor_steps_per_rev{10000.0};  // 2500 CPR * 4 quadrature in format 1
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

  static double motor_steps_to_wheel_rad(
    int64_t accumulated_steps,
    double motor_steps_per_rev,
    double gear_ratio,
    int motor_sign) noexcept;

  // Configuration accessor & testing injection seam
  const M1HardwareConfig & get_config() const noexcept {return config_;}
  void set_driver_for_testing(std::shared_ptr<M1Driver> driver) noexcept;

private:
  hardware_interface::CallbackReturn parse_parameters();

  // Internal configuration
  M1HardwareConfig config_;
  std::shared_ptr<M1Driver> driver_;

  // Command storage: [0]=Left, [1]=Right
  double hw_commands_[2]{0.0, 0.0};

  // State storage: [0]=Left, [1]=Right
  double hw_positions_[2]{0.0, 0.0};
  double hw_velocities_[2]{0.0, 0.0};

  // Position trackers for left and right motors
  PositionTracker left_position_tracker_;
  PositionTracker right_position_tracker_;

  // Cached latest motor states (Model A2)
  ExchangeResult latest_motor_state_{};
  bool has_valid_state_{false};
};

}  // namespace mobile_base_control

#endif  // MOBILE_BASE_CONTROL__M1_HARDWARE_HPP_

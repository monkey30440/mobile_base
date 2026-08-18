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

#include <gtest/gtest.h>
#include <cmath>
#include <limits>
#include <memory>
#include <string>
#include <vector>

#include "hardware_interface/hardware_info.hpp"
#include "hardware_interface/resource_manager.hpp"
#include "hardware_interface/system_interface.hpp"
#include "hardware_interface/types/hardware_interface_return_values.hpp"
#include "hardware_interface/types/hardware_interface_type_values.hpp"
#include "pluginlib/class_loader.hpp"
#include "rclcpp_lifecycle/state.hpp"

#include "mobile_base_control/m1_driver.hpp"
#include "mobile_base_control/m1_hardware.hpp"

using mobile_base_control::M1Hardware;
using mobile_base_control::M1HardwareConfig;
using mobile_base_control::M1Driver;
using mobile_base_control::PositionTracker;
using mobile_base_control::Result;
using mobile_base_control::ErrorCode;
using mobile_base_control::ExchangeResult;
using mobile_base_control::MotorState;
using mobile_base_control::MotorCommand;
using hardware_interface::CallbackReturn;
using hardware_interface::return_type;

namespace
{
constexpr double PI = 3.14159265358979323846;

hardware_interface::HardwareComponentInterfaceParams create_test_params(
  const std::string & port = "mock",
  int baud = 230400,
  uint32_t timeout_ms = 100)
{
  hardware_interface::HardwareInfo info;
  info.name = "M1HardwareTest";
  info.type = "system";
  info.hardware_plugin_name = "mobile_base_control/M1Hardware";

  info.hardware_parameters["serial_port"] = port;
  info.hardware_parameters["baud_rate"] = std::to_string(baud);
  info.hardware_parameters["timeout_ms"] = std::to_string(timeout_ms);
  info.hardware_parameters["left_driver_id"] = "2";
  info.hardware_parameters["right_driver_id"] = "1";
  info.hardware_parameters["gear_ratio"] = "20.0";
  info.hardware_parameters["left_wheel_sign"] = "1";
  info.hardware_parameters["right_wheel_sign"] = "-1";
  info.hardware_parameters["motor_steps_per_rev"] = "10000.0";
  info.hardware_parameters["max_motor_rpm"] = "3000.0";
  info.hardware_parameters["left_wheel_name"] = "driving_wheel_joint_L";
  info.hardware_parameters["right_wheel_name"] = "driving_wheel_joint_R";

  // Joint 0: Left
  hardware_interface::ComponentInfo joint_l;
  joint_l.name = "driving_wheel_joint_L";
  hardware_interface::InterfaceInfo cmd_vel_l;
  cmd_vel_l.name = hardware_interface::HW_IF_VELOCITY;
  joint_l.command_interfaces.push_back(cmd_vel_l);
  hardware_interface::InterfaceInfo state_pos_l;
  state_pos_l.name = hardware_interface::HW_IF_POSITION;
  hardware_interface::InterfaceInfo state_vel_l;
  state_vel_l.name = hardware_interface::HW_IF_VELOCITY;
  joint_l.state_interfaces.push_back(state_pos_l);
  joint_l.state_interfaces.push_back(state_vel_l);
  info.joints.push_back(joint_l);

  // Joint 1: Right
  hardware_interface::ComponentInfo joint_r;
  joint_r.name = "driving_wheel_joint_R";
  hardware_interface::InterfaceInfo cmd_vel_r;
  cmd_vel_r.name = hardware_interface::HW_IF_VELOCITY;
  joint_r.command_interfaces.push_back(cmd_vel_r);
  hardware_interface::InterfaceInfo state_pos_r;
  state_pos_r.name = hardware_interface::HW_IF_POSITION;
  hardware_interface::InterfaceInfo state_vel_r;
  state_vel_r.name = hardware_interface::HW_IF_VELOCITY;
  joint_r.state_interfaces.push_back(state_pos_r);
  joint_r.state_interfaces.push_back(state_vel_r);
  info.joints.push_back(joint_r);

  hardware_interface::HardwareComponentInterfaceParams params;
  params.hardware_info = info;
  return params;
}

}  // namespace

// =========================================================================
// 1. Conversion Math Tests
// =========================================================================

TEST(M1HardwareConversionTest, WheelRadSToMotorRpm)
{
  const double gear = 20.0;
  const double max_rpm = 3000.0;

  // 1.0 rad/s on left wheel (+1 sign) -> 1.0 * 20 * 60 / (2*pi) ~= 190.9859 -> 191 RPM
  EXPECT_EQ(M1Hardware::wheel_rad_s_to_motor_rpm(1.0, gear, 1, max_rpm), 191);

  // 1.0 rad/s on right wheel (-1 sign) -> -191 RPM
  EXPECT_EQ(M1Hardware::wheel_rad_s_to_motor_rpm(1.0, gear, -1, max_rpm), -191);

  // -1.0 rad/s on left wheel (+1 sign) -> -191 RPM
  EXPECT_EQ(M1Hardware::wheel_rad_s_to_motor_rpm(-1.0, gear, 1, max_rpm), -191);

  // -1.0 rad/s on right wheel (-1 sign) -> +191 RPM
  EXPECT_EQ(M1Hardware::wheel_rad_s_to_motor_rpm(-1.0, gear, -1, max_rpm), 191);

  // Zero command -> 0 RPM
  EXPECT_EQ(M1Hardware::wheel_rad_s_to_motor_rpm(0.0, gear, 1, max_rpm), 0);
  EXPECT_EQ(M1Hardware::wheel_rad_s_to_motor_rpm(0.0, gear, -1, max_rpm), 0);

  // Clamping test: excessive rad/s -> clamped to max_rpm
  EXPECT_EQ(M1Hardware::wheel_rad_s_to_motor_rpm(100.0, gear, 1, max_rpm), 3000);
  EXPECT_EQ(M1Hardware::wheel_rad_s_to_motor_rpm(-100.0, gear, 1, max_rpm), -3000);

  // Defensive NaN and Inf
  EXPECT_EQ(
    M1Hardware::wheel_rad_s_to_motor_rpm(
      std::numeric_limits<double>::quiet_NaN(), gear, 1, max_rpm), 0);
  EXPECT_EQ(
    M1Hardware::wheel_rad_s_to_motor_rpm(
      std::numeric_limits<double>::infinity(), gear, 1, max_rpm), 0);
}

TEST(M1HardwareConversionTest, MotorRpmToWheelRadS)
{
  const double gear = 20.0;

  // 191 RPM on left (+1 sign) -> 191 * (2*pi/60) / 20 ~= 1.00007 rad/s
  double rad_s_left = M1Hardware::motor_rpm_to_wheel_rad_s(191, gear, 1);
  EXPECT_NEAR(rad_s_left, 1.0, 0.005);

  // -191 RPM on right (-1 sign) -> (-191 * -1) * (2*pi/60) / 20 ~= 1.00007 rad/s
  double rad_s_right = M1Hardware::motor_rpm_to_wheel_rad_s(-191, gear, -1);
  EXPECT_NEAR(rad_s_right, 1.0, 0.005);

  // Zero RPM -> 0 rad/s
  EXPECT_DOUBLE_EQ(M1Hardware::motor_rpm_to_wheel_rad_s(0, gear, 1), 0.0);
}

TEST(M1HardwareConversionTest, MotorStepsToWheelRad)
{
  const double steps_per_rev = 10000.0;
  const double gear = 20.0;
  // 1 wheel revolution = 200,000 motor steps = 2*PI radians

  // Left wheel (+1 sign)
  EXPECT_NEAR(
    M1Hardware::motor_steps_to_wheel_rad(200000, steps_per_rev, gear, 1),
    2.0 * PI, 1e-6);
  EXPECT_NEAR(
    M1Hardware::motor_steps_to_wheel_rad(-200000, steps_per_rev, gear, 1),
    -2.0 * PI, 1e-6);

  // Right wheel (-1 sign: positive wheel motion corresponds to negative motor steps)
  EXPECT_NEAR(
    M1Hardware::motor_steps_to_wheel_rad(-200000, steps_per_rev, gear, -1),
    2.0 * PI, 1e-6);
  EXPECT_NEAR(
    M1Hardware::motor_steps_to_wheel_rad(200000, steps_per_rev, gear, -1),
    -2.0 * PI, 1e-6);

  // Zero steps
  EXPECT_DOUBLE_EQ(M1Hardware::motor_steps_to_wheel_rad(0, steps_per_rev, gear, 1), 0.0);
}

// =========================================================================
// 2. PositionTracker & Rollover Tests
// =========================================================================

TEST(PositionTrackerTest, InitialSampleSetsOrigin)
{
  PositionTracker tracker;
  EXPECT_FALSE(tracker.initialized);
  EXPECT_EQ(tracker.accumulated_steps, 0);

  tracker.update(12345);
  EXPECT_TRUE(tracker.initialized);
  EXPECT_EQ(tracker.previous_raw, 12345);
  EXPECT_EQ(tracker.accumulated_steps, 0);
}

TEST(PositionTrackerTest, PositiveAndNegativeDeltas)
{
  PositionTracker tracker;
  tracker.update(1000);

  tracker.update(1500);
  EXPECT_EQ(tracker.accumulated_steps, 500);

  tracker.update(1200);
  EXPECT_EQ(tracker.accumulated_steps, 200);

  tracker.update(200);
  EXPECT_EQ(tracker.accumulated_steps, -800);
}

TEST(PositionTrackerTest, Signed32BitPositiveRollover)
{
  PositionTracker tracker;
  // Start near +2^31 - 1 (0x7FFFFFF0 = 2,147,483,632)
  int32_t near_max = 2147483632;
  tracker.update(near_max);

  // Advance by +30 steps across int32 overflow to -2,147,483,634 (0x8000000E)
  int32_t wrapped_positive = static_cast<int32_t>(static_cast<uint32_t>(near_max) + 30);
  tracker.update(wrapped_positive);

  EXPECT_EQ(tracker.accumulated_steps, 30);

  // Advance another +50 steps
  int32_t next_pos = static_cast<int32_t>(static_cast<uint32_t>(wrapped_positive) + 50);
  tracker.update(next_pos);

  EXPECT_EQ(tracker.accumulated_steps, 80);
}

TEST(PositionTrackerTest, Signed32BitNegativeRollover)
{
  PositionTracker tracker;
  // Start near -2^31 (0x8000000E = -2,147,483,634)
  int32_t near_min = -2147483634;
  tracker.update(near_min);

  // Move backwards by -30 steps across int32 underflow
  int32_t wrapped_negative = static_cast<int32_t>(static_cast<uint32_t>(near_min) - 30);
  tracker.update(wrapped_negative);

  EXPECT_EQ(tracker.accumulated_steps, -30);
}

TEST(PositionTrackerTest, ResetClearsOrigin)
{
  PositionTracker tracker;
  tracker.update(5000);
  tracker.update(5500);
  EXPECT_EQ(tracker.accumulated_steps, 500);

  tracker.reset();
  EXPECT_FALSE(tracker.initialized);
  EXPECT_EQ(tracker.accumulated_steps, 0);

  tracker.update(8000);
  EXPECT_EQ(tracker.accumulated_steps, 0);
  tracker.update(8100);
  EXPECT_EQ(tracker.accumulated_steps, 100);
}

// =========================================================================
// 3. M1Hardware Lifecycle & Mock Execution Tests
// =========================================================================

TEST(M1HardwareLifecycleTest, InitParameterParsing)
{
  M1Hardware hw;
  auto params = create_test_params("mock", 230400, 100);
  EXPECT_EQ(hw.on_init(params), CallbackReturn::SUCCESS);

  const auto & cfg = hw.get_config();
  EXPECT_EQ(cfg.serial_port, "mock");
  EXPECT_EQ(cfg.baud_rate, 230400);
  EXPECT_EQ(cfg.timeout_ms, 100u);
  EXPECT_EQ(cfg.left_driver_id, 2);
  EXPECT_EQ(cfg.right_driver_id, 1);
  EXPECT_DOUBLE_EQ(cfg.gear_ratio, 20.0);
  EXPECT_EQ(cfg.left_wheel_sign, 1);
  EXPECT_EQ(cfg.right_wheel_sign, -1);
}

TEST(M1HardwareLifecycleTest, ExportInterfaces)
{
  M1Hardware hw;
  auto params = create_test_params("mock");
  ASSERT_EQ(hw.on_init(params), CallbackReturn::SUCCESS);

  auto state_ifaces = hw.export_state_interfaces();
  ASSERT_EQ(state_ifaces.size(), 4u);
  EXPECT_EQ(state_ifaces[0].get_prefix_name(), "driving_wheel_joint_L");
  EXPECT_EQ(state_ifaces[0].get_interface_name(), hardware_interface::HW_IF_POSITION);
  EXPECT_EQ(state_ifaces[1].get_prefix_name(), "driving_wheel_joint_L");
  EXPECT_EQ(state_ifaces[1].get_interface_name(), hardware_interface::HW_IF_VELOCITY);
  EXPECT_EQ(state_ifaces[2].get_prefix_name(), "driving_wheel_joint_R");
  EXPECT_EQ(state_ifaces[2].get_interface_name(), hardware_interface::HW_IF_POSITION);
  EXPECT_EQ(state_ifaces[3].get_prefix_name(), "driving_wheel_joint_R");
  EXPECT_EQ(state_ifaces[3].get_interface_name(), hardware_interface::HW_IF_VELOCITY);

  auto cmd_ifaces = hw.export_command_interfaces();
  ASSERT_EQ(cmd_ifaces.size(), 2u);
  EXPECT_EQ(cmd_ifaces[0].get_prefix_name(), "driving_wheel_joint_L");
  EXPECT_EQ(cmd_ifaces[0].get_interface_name(), hardware_interface::HW_IF_VELOCITY);
  EXPECT_EQ(cmd_ifaces[1].get_prefix_name(), "driving_wheel_joint_R");
  EXPECT_EQ(cmd_ifaces[1].get_interface_name(), hardware_interface::HW_IF_VELOCITY);
}

TEST(M1HardwareLifecycleTest, FullLifecycleMockSuccess)
{
  M1Hardware hw;
  auto params = create_test_params("mock");
  ASSERT_EQ(hw.on_init(params), CallbackReturn::SUCCESS);

  rclcpp_lifecycle::State unconfigured(
    lifecycle_msgs::msg::State::PRIMARY_STATE_UNCONFIGURED, "unconfigured");
  rclcpp_lifecycle::State inactive(
    lifecycle_msgs::msg::State::PRIMARY_STATE_INACTIVE, "inactive");
  rclcpp_lifecycle::State active(
    lifecycle_msgs::msg::State::PRIMARY_STATE_ACTIVE, "active");

  // 1. Configure
  EXPECT_EQ(hw.on_configure(unconfigured), CallbackReturn::SUCCESS);

  // 2. Activate
  EXPECT_EQ(hw.on_activate(inactive), CallbackReturn::SUCCESS);

  // 3. Read in ACTIVE
  rclcpp::Time now(0, 0, RCL_ROS_TIME);
  rclcpp::Duration dt(0, 20000000);  // 20 ms
  EXPECT_EQ(hw.read(now, dt), return_type::OK);

  // 4. Write zero command in ACTIVE
  auto cmd_ifaces = hw.export_command_interfaces();
  EXPECT_TRUE(cmd_ifaces[0].set_value(0.0));
  EXPECT_TRUE(cmd_ifaces[1].set_value(0.0));
  EXPECT_EQ(hw.write(now, dt), return_type::OK);

  // 5. Deactivate
  EXPECT_EQ(hw.on_deactivate(active), CallbackReturn::SUCCESS);

  // 6. Cleanup
  EXPECT_EQ(hw.on_cleanup(inactive), CallbackReturn::SUCCESS);
}

TEST(M1HardwareLifecycleTest, WriteAndReadFeedbackLoop)
{
  M1Hardware hw;
  auto params = create_test_params("mock");
  ASSERT_EQ(hw.on_init(params), CallbackReturn::SUCCESS);

  rclcpp_lifecycle::State unconfigured(
    lifecycle_msgs::msg::State::PRIMARY_STATE_UNCONFIGURED, "unconfigured");
  rclcpp_lifecycle::State inactive(
    lifecycle_msgs::msg::State::PRIMARY_STATE_INACTIVE, "inactive");

  ASSERT_EQ(hw.on_configure(unconfigured), CallbackReturn::SUCCESS);
  ASSERT_EQ(hw.on_activate(inactive), CallbackReturn::SUCCESS);

  auto cmd_ifaces = hw.export_command_interfaces();
  auto state_ifaces = hw.export_state_interfaces();

  // Command: Left = 1.0 rad/s, Right = 1.0 rad/s
  // Left: +1 sign -> 191 RPM
  // Right: -1 sign -> -191 RPM
  EXPECT_TRUE(cmd_ifaces[0].set_value(1.0));
  EXPECT_TRUE(cmd_ifaces[1].set_value(1.0));

  rclcpp::Time now(0, 0, RCL_ROS_TIME);
  rclcpp::Duration dt(0, 20000000);
  EXPECT_EQ(hw.write(now, dt), return_type::OK);

  // Read back feedback (Mock driver echoes back commanded target_rpm as actual_rpm)
  EXPECT_EQ(hw.read(now, dt), return_type::OK);

  // State interfaces:
  // state_ifaces[1]: Left velocity -> should be ~1.0 rad/s
  // state_ifaces[3]: Right velocity -> should be ~1.0 rad/s
  auto left_vel_opt = state_ifaces[1].get_optional<double>();
  auto right_vel_opt = state_ifaces[3].get_optional<double>();
  ASSERT_TRUE(left_vel_opt.has_value());
  ASSERT_TRUE(right_vel_opt.has_value());
  EXPECT_NEAR(left_vel_opt.value(), 1.0, 0.01);
  EXPECT_NEAR(right_vel_opt.value(), 1.0, 0.01);

  // Cleanup
  rclcpp_lifecycle::State active(
    lifecycle_msgs::msg::State::PRIMARY_STATE_ACTIVE, "active");
  EXPECT_EQ(hw.on_deactivate(active), CallbackReturn::SUCCESS);
}

TEST(M1HardwareLifecycleTest, InvalidCommandRejection)
{
  M1Hardware hw;
  auto params = create_test_params("mock");
  ASSERT_EQ(hw.on_init(params), CallbackReturn::SUCCESS);

  rclcpp_lifecycle::State unconfigured(
    lifecycle_msgs::msg::State::PRIMARY_STATE_UNCONFIGURED, "unconfigured");
  rclcpp_lifecycle::State inactive(
    lifecycle_msgs::msg::State::PRIMARY_STATE_INACTIVE, "inactive");

  ASSERT_EQ(hw.on_configure(unconfigured), CallbackReturn::SUCCESS);
  ASSERT_EQ(hw.on_activate(inactive), CallbackReturn::SUCCESS);

  auto cmd_ifaces = hw.export_command_interfaces();
  // Set NaN command
  EXPECT_TRUE(cmd_ifaces[0].set_value(std::numeric_limits<double>::quiet_NaN()));
  EXPECT_TRUE(cmd_ifaces[1].set_value(1.0));

  rclcpp::Time now(0, 0, RCL_ROS_TIME);
  rclcpp::Duration dt(0, 20000000);
  EXPECT_EQ(hw.write(now, dt), return_type::ERROR);

  rclcpp_lifecycle::State active(
    lifecycle_msgs::msg::State::PRIMARY_STATE_ACTIVE, "active");
  EXPECT_EQ(hw.on_deactivate(active), CallbackReturn::SUCCESS);
}

TEST(M1HardwareLifecycleTest, ReadWithoutValidStateFails)
{
  M1Hardware hw;
  auto params = create_test_params("mock");
  ASSERT_EQ(hw.on_init(params), CallbackReturn::SUCCESS);

  // Before activate, read() should return ERROR because no valid state is cached
  rclcpp::Time now(0, 0, RCL_ROS_TIME);
  rclcpp::Duration dt(0, 20000000);
  EXPECT_EQ(hw.read(now, dt), return_type::ERROR);
}

TEST(M1HardwareLifecycleTest, PluginLoaderDiscovery)
{
  // Verify that pluginlib can discover and instantiate M1Hardware via XML definition
  pluginlib::ClassLoader<hardware_interface::SystemInterface> loader(
    "hardware_interface", "hardware_interface::SystemInterface");

  std::vector<std::string> classes = loader.getDeclaredClasses();
  bool found = false;
  for (const auto & cls : classes) {
    if (cls == "mobile_base_control/M1Hardware") {
      found = true;
      break;
    }
  }
  EXPECT_TRUE(found) << "mobile_base_control/M1Hardware was not found in declared classes";

  if (found) {
    std::shared_ptr<hardware_interface::SystemInterface> instance =
      loader.createSharedInstance("mobile_base_control/M1Hardware");
    EXPECT_NE(instance, nullptr);
  }
}

TEST(M1HardwareIntegrationTest, ResourceManagerURDFLoading)
{
  const std::string urdf =
    R"xml(<?xml version="1.0"?>
<robot name="mobile_base_test">
  <link name="base_link"/>
  <link name="left_wheel"/>
  <link name="right_wheel"/>
  <joint name="driving_wheel_joint_L" type="continuous">
    <parent link="base_link"/>
    <child link="left_wheel"/>
  </joint>
  <joint name="driving_wheel_joint_R" type="continuous">
    <parent link="base_link"/>
    <child link="right_wheel"/>
  </joint>
  <ros2_control name="M1Hardware" type="system">
    <hardware>
      <plugin>mobile_base_control/M1Hardware</plugin>
      <param name="serial_port">mock</param>
      <param name="baud_rate">230400</param>
      <param name="timeout_ms">100</param>
      <param name="left_driver_id">2</param>
      <param name="right_driver_id">1</param>
      <param name="gear_ratio">20.0</param>
      <param name="left_wheel_sign">1</param>
      <param name="right_wheel_sign">-1</param>
      <param name="motor_steps_per_rev">10000.0</param>
      <param name="max_motor_rpm">3000.0</param>
    </hardware>
    <joint name="driving_wheel_joint_L">
      <command_interface name="velocity"/>
      <state_interface name="position"/>
      <state_interface name="velocity"/>
    </joint>
    <joint name="driving_wheel_joint_R">
      <command_interface name="velocity"/>
      <state_interface name="position"/>
      <state_interface name="velocity"/>
    </joint>
  </ros2_control>
</robot>)xml";

  auto clock = std::make_shared<rclcpp::Clock>(RCL_ROS_TIME);
  auto logger = rclcpp::get_logger("resource_manager_test");

  EXPECT_NO_THROW({
    hardware_interface::ResourceManager rm(urdf, clock, logger, true);
    EXPECT_TRUE(rm.are_components_initialized());

    // State interfaces should be available after activate_all = true
    EXPECT_TRUE(rm.state_interface_is_available("driving_wheel_joint_L/position"));
    EXPECT_TRUE(rm.state_interface_is_available("driving_wheel_joint_L/velocity"));
    EXPECT_TRUE(rm.state_interface_is_available("driving_wheel_joint_R/position"));
    EXPECT_TRUE(rm.state_interface_is_available("driving_wheel_joint_R/velocity"));

    // Command interfaces should be available after activate_all = true
    EXPECT_TRUE(rm.command_interface_is_available("driving_wheel_joint_L/velocity"));
    EXPECT_TRUE(rm.command_interface_is_available("driving_wheel_joint_R/velocity"));
  });
}

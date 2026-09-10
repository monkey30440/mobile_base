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

#include "controller_interface/controller_interface_base.hpp"
#include "diff_drive_controller/diff_drive_controller.hpp"
#include "geometry_msgs/msg/twist_stamped.hpp"
#include "hardware_interface/hardware_info.hpp"
#include "hardware_interface/component_parser.hpp"
#include "hardware_interface/resource_manager.hpp"
#include "hardware_interface/system_interface.hpp"
#include "hardware_interface/types/hardware_interface_return_values.hpp"
#include "hardware_interface/types/hardware_interface_type_values.hpp"
#include "pluginlib/class_loader.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_lifecycle/state.hpp"

#include "mobile_base_control/m1_driver.hpp"
#include "mobile_base_control/m1_hardware.hpp"

using mobile_base_control::M1Hardware;
using mobile_base_control::M1HardwareConfig;
using mobile_base_control::M1Driver;
using mobile_base_control::PositionTracker;
using mobile_base_control::Format0PositionSample;
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

// Test driver fixture returning confirmed M1 configuration registers only.
class FixtureM1Driver : public M1Driver
{
public:
  size_t config_reads{0};

  Result<mobile_base_control::M1DeviceConfig> read_device_config(int id) override
  {
    ++config_reads;
    mobile_base_control::M1DeviceConfig config;
    config.driver_id = id;
    config.encoder_resolution_pulses_per_rev = 2500;
    config.position_command_format = 0;
    return Result<mobile_base_control::M1DeviceConfig>::success(config);
  }
};

void import_fixture_hardware(
  hardware_interface::ResourceManager & rm, const std::string & urdf,
  const std::shared_ptr<rclcpp::Clock> & clock)
{
  hardware_interface::HardwareComponentParams params;
  params.hardware_info = hardware_interface::parse_control_resources_from_urdf(urdf).at(0);
  params.clock = clock;
  auto hw = std::make_unique<M1Hardware>(std::make_shared<FixtureM1Driver>());
  rm.import_component(std::move(hw), params);
  rclcpp_lifecycle::State active(lifecycle_msgs::msg::State::PRIMARY_STATE_ACTIVE, "active");
  ASSERT_EQ(rm.set_component_state("M1Hardware", active), return_type::OK);
}

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

TEST(M1HardwareConversionTest, FeedbackUnitsToWheelRad)
{
  const uint32_t radix = 10000;
  const double gear = 20.0;
  // Fixture: 1 wheel revolution = 10,000 * 20 = 200,000 feedback units = 2*PI radians

  // Left wheel (+1 sign)
  EXPECT_NEAR(
    M1Hardware::feedback_units_to_wheel_rad(200000, radix, gear, 1),
    2.0 * PI, 1e-6);
  EXPECT_NEAR(
    M1Hardware::feedback_units_to_wheel_rad(-200000, radix, gear, 1),
    -2.0 * PI, 1e-6);

  // Right wheel (-1 sign: positive wheel motion corresponds to negative motor feedback units)
  EXPECT_NEAR(
    M1Hardware::feedback_units_to_wheel_rad(-200000, radix, gear, -1),
    2.0 * PI, 1e-6);
  EXPECT_NEAR(
    M1Hardware::feedback_units_to_wheel_rad(200000, radix, gear, -1),
    -2.0 * PI, 1e-6);

  // Zero units
  EXPECT_DOUBLE_EQ(M1Hardware::feedback_units_to_wheel_rad(0, radix, gear, 1), 0.0);

  // Invalid parameters
  EXPECT_TRUE(std::isnan(M1Hardware::feedback_units_to_wheel_rad(100, 0, gear, 1)));
  EXPECT_TRUE(std::isnan(M1Hardware::feedback_units_to_wheel_rad(100, radix, 0.0, 1)));
  EXPECT_TRUE(std::isnan(M1Hardware::feedback_units_to_wheel_rad(100, radix, -1.0, 1)));
  EXPECT_TRUE(std::isnan(M1Hardware::feedback_units_to_wheel_rad(100, radix, gear, 0)));

  // Forwarding helper motor_steps_to_wheel_rad
  EXPECT_NEAR(
    M1Hardware::motor_steps_to_wheel_rad(200000, 10000.0, gear, 1),
    2.0 * PI, 1e-6);
}

// =========================================================================
// 2. PositionTracker & Format-0 Decoding Tests
// =========================================================================

TEST(PositionTrackerTest, InitialSampleSetsOrigin)
{
  PositionTracker tracker;
  EXPECT_FALSE(tracker.initialized);
  EXPECT_EQ(tracker.accumulated_feedback_units, 0);

  tracker.initialize(Format0PositionSample{123, 4567});
  EXPECT_TRUE(tracker.initialized);
  EXPECT_EQ(tracker.previous_sample.index, 123);
  EXPECT_EQ(tracker.previous_sample.pos, 4567);
  EXPECT_EQ(tracker.accumulated_feedback_units, 0);
}

TEST(PositionTrackerTest, Format0BoundaryTransitions)
{
  PositionTracker tracker;
  const uint32_t radix = 10000;

  tracker.initialize(Format0PositionSample{0, 0});
  EXPECT_EQ(tracker.accumulated_feedback_units, 0);

  // Intra-revolution forward step
  tracker.update(Format0PositionSample{0, 9999}, radix);
  EXPECT_EQ(tracker.accumulated_feedback_units, 9999);

  // Boundary transition across radix: (0, 9999) -> (1, 0)
  tracker.update(Format0PositionSample{1, 0}, radix);
  EXPECT_EQ(tracker.accumulated_feedback_units, 10000);

  // Advance several revolutions to (5, 9999)
  tracker.update(Format0PositionSample{5, 9999}, radix);
  EXPECT_EQ(tracker.accumulated_feedback_units, 59999);

  // Boundary transition: (5, 9999) -> (6, 0) (+1 unit)
  tracker.update(Format0PositionSample{6, 0}, radix);
  EXPECT_EQ(tracker.accumulated_feedback_units, 60000);

  // Reverse boundary transition: (6, 0) -> (5, 9999) (-1 unit)
  tracker.update(Format0PositionSample{5, 9999}, radix);
  EXPECT_EQ(tracker.accumulated_feedback_units, 59999);

  // Return to origin (0, 0)
  tracker.update(Format0PositionSample{0, 0}, radix);
  EXPECT_EQ(tracker.accumulated_feedback_units, 0);

  // Negative boundary transition: (0, 0) -> (-1, 9999) (-1 unit)
  tracker.update(Format0PositionSample{-1, 9999}, radix);
  EXPECT_EQ(tracker.accumulated_feedback_units, -1);

  // Negative step: (-1, 9999) -> (-1, 9998) (-1 unit)
  tracker.update(Format0PositionSample{-1, 9998}, radix);
  EXPECT_EQ(tracker.accumulated_feedback_units, -2);
}

TEST(PositionTrackerTest, Signed16BitIndexRollover)
{
  PositionTracker tracker;
  const uint32_t radix = 10000;

  // Initialize near positive maximum int16 index
  tracker.initialize(Format0PositionSample{32767, 9999});

  // Advance forward across int16 rollover to (-32768, 0)
  tracker.update(Format0PositionSample{-32768, 0}, radix);
  EXPECT_EQ(tracker.accumulated_feedback_units, 1);

  // Advance further
  tracker.update(Format0PositionSample{-32768, 50}, radix);
  EXPECT_EQ(tracker.accumulated_feedback_units, 51);

  // Reverse backward across int16 underflow to (32767, 9999)
  tracker.update(Format0PositionSample{-32768, 0}, radix);
  EXPECT_EQ(tracker.accumulated_feedback_units, 1);
  tracker.update(Format0PositionSample{32767, 9999}, radix);
  EXPECT_EQ(tracker.accumulated_feedback_units, 0);
}

TEST(PositionTrackerTest, RealHardwareObservedTransitions)
{
  const uint32_t radix = 10000;

  // Right driver physically captured baseline and motion:
  // Before: Index=0, Pos=1
  // After:  Index=-20, Pos=909
  // Expected delta = -20 * 10000 + (909 - 1) = -200000 + 908 = -199092 units
  PositionTracker right_tracker;
  right_tracker.initialize(Format0PositionSample{0, 1});
  right_tracker.update(Format0PositionSample{-20, 909}, radix);
  EXPECT_EQ(right_tracker.accumulated_feedback_units, -199092);

  // Left driver physically captured baseline and motion:
  // Before: Index=-1, Pos=9998
  // After:  Index=20, Pos=422
  // Expected delta = (20 - (-1)) * 10000 + (422 - 9998) = 210000 - 9576 = +200424 units
  PositionTracker left_tracker;
  left_tracker.initialize(Format0PositionSample{-1, 9998});
  left_tracker.update(Format0PositionSample{20, 422}, radix);
  EXPECT_EQ(left_tracker.accumulated_feedback_units, 200424);
}

TEST(PositionTrackerTest, ResetClearsOrigin)
{
  PositionTracker tracker;
  const uint32_t radix = 10000;

  tracker.initialize(Format0PositionSample{5, 500});
  tracker.update(Format0PositionSample{5, 600}, radix);
  EXPECT_EQ(tracker.accumulated_feedback_units, 100);

  tracker.reset();
  EXPECT_FALSE(tracker.initialized);
  EXPECT_EQ(tracker.accumulated_feedback_units, 0);
  EXPECT_EQ(tracker.previous_sample, (Format0PositionSample{0, 0}));

  tracker.initialize(Format0PositionSample{8, 8000});
  EXPECT_TRUE(tracker.initialized);
  EXPECT_EQ(tracker.accumulated_feedback_units, 0);
  tracker.update(Format0PositionSample{8, 8100}, radix);
  EXPECT_EQ(tracker.accumulated_feedback_units, 100);
}

// =========================================================================
// 3. M1Hardware Lifecycle & Mock Execution Tests
// =========================================================================

TEST(M1HardwareLifecycleTest, InitParameterParsing)
{
  M1Hardware hw(std::make_shared<FixtureM1Driver>());
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

TEST(M1HardwareLifecycleTest, MissingTimeoutParameterFails)
{
  M1Hardware hw(std::make_shared<FixtureM1Driver>());
  auto params = create_test_params("mock", 230400, 100);
  params.hardware_info.hardware_parameters.erase("timeout_ms");
  params.hardware_info.hardware_parameters.erase("response_timeout_ms");
  EXPECT_EQ(hw.on_init(params), CallbackReturn::ERROR);
}

TEST(M1HardwareLifecycleTest, DoesNotRequireRosOwnedPositionScale)
{
  M1Hardware hw(std::make_shared<FixtureM1Driver>());
  auto params = create_test_params("mock", 230400, 100);
  params.hardware_info.hardware_parameters.erase("motor_steps_per_rev");

  EXPECT_EQ(hw.on_init(params), CallbackReturn::SUCCESS);
}

TEST(M1HardwareLifecycleTest, ReadsConfigurationAndDerivesRadix)
{
  auto driver = std::make_shared<M1Driver>();
  std::vector<std::vector<uint8_t>> requests;
  driver->set_transact_override(
    [&requests](const std::vector<uint8_t> & req) {
      requests.push_back(req);
      if (req.size() == 6 && req[1] == 0x03 && (req[0] == 1 || req[0] == 2)) {
        const uint16_t value = req[2] == 0x3D ? 2500 : 0;
        return Result<std::vector<uint8_t>>::success(
          {req[0], 0x03, 0x02, static_cast<uint8_t>(value >> 8),
            static_cast<uint8_t>(value & 0xFF)});
      }
      return Result<std::vector<uint8_t>>::failure(ErrorCode::INVALID_RESPONSE);
    });
  M1Hardware hw(driver);
  ASSERT_EQ(hw.on_init(create_test_params()), CallbackReturn::SUCCESS);
  rclcpp_lifecycle::State state;
  ASSERT_EQ(hw.on_configure(state), CallbackReturn::SUCCESS);
  const std::vector<std::vector<uint8_t>> expected{
    {1, 3, 0x3D, 5, 0, 1}, {1, 3, 0x3E, 0x0D, 0, 1},
    {2, 3, 0x3D, 5, 0, 1}, {2, 3, 0x3E, 0x0D, 0, 1}};
  EXPECT_EQ(requests, expected);  // Exactly the 4 configuration reads, no SVON or motion.
  ASSERT_TRUE(hw.get_device_configs());
  EXPECT_EQ((*hw.get_device_configs())[0].encoder_resolution_pulses_per_rev, 2500u);
  EXPECT_EQ((*hw.get_device_configs())[0].position_command_format, 0u);
  EXPECT_EQ((*hw.get_device_configs())[1].encoder_resolution_pulses_per_rev, 2500u);
  EXPECT_EQ((*hw.get_device_configs())[1].position_command_format, 0u);
  ASSERT_TRUE(hw.get_runtime_radix().has_value());
  EXPECT_EQ(*hw.get_runtime_radix(), 10000u);
  for (auto & interface : hw.export_state_interfaces()) {
    EXPECT_TRUE(std::isnan(interface.get_optional<double>().value()));
  }
  EXPECT_EQ(hw.write(rclcpp::Time(0), rclcpp::Duration(0, 20000000)), return_type::ERROR);
}

TEST(M1HardwareLifecycleTest, RejectsLegacyRosScale)
{
  M1Hardware hw;
  auto params = create_test_params();
  params.hardware_info.hardware_parameters["motor_steps_per_rev"] = "2500";
  EXPECT_EQ(hw.on_init(params), CallbackReturn::ERROR);
}

TEST(M1HardwareLifecycleTest, ConfigurationFailureDoesNotPublishPartialOrStaleSnapshot)
{
  for (size_t failing_read : {1u, 2u, 3u, 4u}) {
    auto driver = std::make_shared<M1Driver>();
    size_t calls = 0;
    bool fail = false;
    driver->set_transact_override([&](const std::vector<uint8_t> & req) {
        if (++calls == failing_read && fail) {
          return Result<std::vector<uint8_t>>::failure(ErrorCode::TIMEOUT);
        }
        const uint16_t value = req[2] == 0x3D ? 2500 : 0;
        return Result<std::vector<uint8_t>>::success(
          {req[0], 3, 2, static_cast<uint8_t>(value >> 8),
            static_cast<uint8_t>(value & 0xFF)});
      });
    M1Hardware hw(driver);
    ASSERT_EQ(hw.on_init(create_test_params()), CallbackReturn::SUCCESS);
    rclcpp_lifecycle::State state;
    ASSERT_EQ(hw.on_configure(state), CallbackReturn::SUCCESS);
    ASSERT_TRUE(hw.get_device_configs());
    ASSERT_TRUE(hw.get_runtime_radix());
    fail = true;
    calls = 0;
    EXPECT_EQ(hw.on_configure(state), CallbackReturn::FAILURE);
    EXPECT_FALSE(hw.get_device_configs());
    EXPECT_FALSE(hw.get_runtime_radix());
    EXPECT_FALSE(driver->is_connected());
    EXPECT_EQ(calls, failing_read);
    EXPECT_EQ(hw.on_activate(state), CallbackReturn::FAILURE);
    EXPECT_EQ(calls, failing_read);
    fail = false;
    EXPECT_EQ(hw.on_configure(state), CallbackReturn::SUCCESS);  // Reconnect/re-read.
    EXPECT_TRUE(hw.get_device_configs());
    EXPECT_TRUE(hw.get_runtime_radix());
    driver->disconnect();  // Captured stack values outlive all possible transactions.
  }
}

TEST(M1HardwareLifecycleTest, CleanupInvalidatesConfiguration)
{
  M1Hardware hw(std::make_shared<FixtureM1Driver>());
  ASSERT_EQ(hw.on_init(create_test_params()), CallbackReturn::SUCCESS);
  rclcpp_lifecycle::State state;
  ASSERT_EQ(hw.on_configure(state), CallbackReturn::SUCCESS);
  ASSERT_TRUE(hw.get_device_configs());
  ASSERT_TRUE(hw.get_runtime_radix());
  EXPECT_EQ(hw.on_cleanup(state), CallbackReturn::SUCCESS);
  EXPECT_FALSE(hw.get_device_configs());
  EXPECT_FALSE(hw.get_runtime_radix());
  EXPECT_EQ(hw.on_activate(state), CallbackReturn::FAILURE);
}

TEST(M1HardwareLifecycleTest, ConfigurationRejectsZeroEncoderResolution)
{
  auto driver = std::make_shared<M1Driver>();
  driver->set_transact_override([](const std::vector<uint8_t> & req) {
      if (req.size() == 6 && req[1] == 0x03) {
        const uint16_t value = 0;
        return Result<std::vector<uint8_t>>::success(
          {req[0], 0x03, 0x02, static_cast<uint8_t>(value >> 8),
            static_cast<uint8_t>(value & 0xFF)});
      }
      return Result<std::vector<uint8_t>>::failure(ErrorCode::INVALID_RESPONSE);
    });
  M1Hardware hw(driver);
  ASSERT_EQ(hw.on_init(create_test_params()), CallbackReturn::SUCCESS);
  rclcpp_lifecycle::State state;
  EXPECT_EQ(hw.on_configure(state), CallbackReturn::FAILURE);
  EXPECT_FALSE(hw.get_device_configs().has_value());
  EXPECT_FALSE(hw.get_runtime_radix().has_value());
}

TEST(M1HardwareLifecycleTest, ConfigurationRejectsUnsupportedFormat)
{
  auto driver = std::make_shared<M1Driver>();
  driver->set_transact_override([](const std::vector<uint8_t> & req) {
      if (req.size() == 6 && req[1] == 0x03) {
        const uint16_t value = (req[2] == 0x3D) ? 2500 : 1;
        return Result<std::vector<uint8_t>>::success(
          {req[0], 0x03, 0x02, static_cast<uint8_t>(value >> 8),
            static_cast<uint8_t>(value & 0xFF)});
      }
      return Result<std::vector<uint8_t>>::failure(ErrorCode::INVALID_RESPONSE);
    });
  M1Hardware hw(driver);
  ASSERT_EQ(hw.on_init(create_test_params()), CallbackReturn::SUCCESS);
  rclcpp_lifecycle::State state;
  EXPECT_EQ(hw.on_configure(state), CallbackReturn::FAILURE);
  EXPECT_FALSE(hw.get_device_configs().has_value());
  EXPECT_FALSE(hw.get_runtime_radix().has_value());
}

TEST(M1HardwareLifecycleTest, ConfigurationRejectsPairResolutionMismatch)
{
  auto driver = std::make_shared<M1Driver>();
  driver->set_transact_override([](const std::vector<uint8_t> & req) {
      if (req.size() == 6 && req[1] == 0x03) {
        uint16_t value = 0;
        if (req[2] == 0x3D) {
          value = (req[0] == 1) ? 2500 : 2000;
        }
        return Result<std::vector<uint8_t>>::success(
          {req[0], 0x03, 0x02, static_cast<uint8_t>(value >> 8),
            static_cast<uint8_t>(value & 0xFF)});
      }
      return Result<std::vector<uint8_t>>::failure(ErrorCode::INVALID_RESPONSE);
    });
  M1Hardware hw(driver);
  ASSERT_EQ(hw.on_init(create_test_params()), CallbackReturn::SUCCESS);
  rclcpp_lifecycle::State state;
  EXPECT_EQ(hw.on_configure(state), CallbackReturn::FAILURE);
  EXPECT_FALSE(hw.get_device_configs().has_value());
  EXPECT_FALSE(hw.get_runtime_radix().has_value());
}

TEST(M1HardwareLifecycleTest, ActivationBlockedWithoutConfiguration)
{
  auto driver = std::make_shared<FixtureM1Driver>();
  size_t transactions = 0;
  driver->set_transact_override([&transactions](const std::vector<uint8_t> &) {
      ++transactions;
      return Result<std::vector<uint8_t>>::failure(ErrorCode::INVALID_RESPONSE);
    });
  M1Hardware hw(driver);
  ASSERT_EQ(hw.on_init(create_test_params()), CallbackReturn::SUCCESS);
  rclcpp_lifecycle::State state;
  EXPECT_EQ(hw.on_activate(state), CallbackReturn::FAILURE);
  EXPECT_EQ(transactions, 0u);
}

TEST(M1HardwareLifecycleTest, ActivationEstablishesServoOffBaselineBeforeEnable)
{
  auto driver = std::make_shared<FixtureM1Driver>();
  std::vector<std::string> sequence;
  driver->set_transact_override([&sequence](const std::vector<uint8_t> & req) {
      if (req.size() >= 2 && req[1] == 0x03) {
        sequence.push_back("read_state");
        std::vector<uint8_t> rsp(35, 0);
        rsp[0] = 0x65;
        rsp[1] = 0x03;
        rsp[2] = 32;
        // Driver 1 (Right): index=0, pos=100
        rsp[13] = 0x00; rsp[14] = 0x00;
        rsp[15] = 0x00; rsp[16] = 100;
        // Driver 2 (Left): index=-1, pos=500
        rsp[29] = 0xFF; rsp[30] = 0xFF;
        rsp[31] = 0x01; rsp[32] = 0xF4;
        return Result<std::vector<uint8_t>>::success(rsp);
      }
      if (req.size() >= 2 && req[1] == 0x17) {
        sequence.push_back("enable");
        std::vector<uint8_t> rsp(35, 0);
        rsp[0] = 0x65;
        rsp[1] = 0x17;
        rsp[2] = 32;
        return Result<std::vector<uint8_t>>::success(rsp);
      }
      return Result<std::vector<uint8_t>>::failure(ErrorCode::INVALID_RESPONSE);
    });

  M1Hardware hw(driver);
  ASSERT_EQ(hw.on_init(create_test_params()), CallbackReturn::SUCCESS);
  rclcpp_lifecycle::State state;
  ASSERT_EQ(hw.on_configure(state), CallbackReturn::SUCCESS);
  ASSERT_EQ(hw.on_activate(state), CallbackReturn::SUCCESS);

  ASSERT_GE(sequence.size(), 2u);
  EXPECT_EQ(sequence[0], "read_state");
  EXPECT_EQ(sequence[1], "enable");

  const auto right_tracker = hw.get_right_position_tracker();
  const auto left_tracker = hw.get_left_position_tracker();
  EXPECT_TRUE(right_tracker.initialized);
  EXPECT_EQ(right_tracker.previous_sample.index, 0);
  EXPECT_EQ(right_tracker.previous_sample.pos, 100);
  EXPECT_EQ(right_tracker.accumulated_feedback_units, 0);

  EXPECT_TRUE(left_tracker.initialized);
  EXPECT_EQ(left_tracker.previous_sample.index, -1);
  EXPECT_EQ(left_tracker.previous_sample.pos, 500);
  EXPECT_EQ(left_tracker.accumulated_feedback_units, 0);
}

TEST(M1HardwareLifecycleTest, ActivationAbortsBeforeEnableOnPreCheckFailure)
{
  auto driver = std::make_shared<FixtureM1Driver>();
  bool enable_called = false;
  driver->set_transact_override([&enable_called](const std::vector<uint8_t> & req) {
      if (req.size() >= 2 && req[1] == 0x03) {
        return Result<std::vector<uint8_t>>::failure(ErrorCode::TIMEOUT);
      }
      if (req.size() >= 2 && req[1] == 0x17) {
        enable_called = true;
      }
      return Result<std::vector<uint8_t>>::failure(ErrorCode::INVALID_RESPONSE);
    });

  M1Hardware hw(driver);
  ASSERT_EQ(hw.on_init(create_test_params()), CallbackReturn::SUCCESS);
  rclcpp_lifecycle::State state;
  ASSERT_EQ(hw.on_configure(state), CallbackReturn::SUCCESS);
  EXPECT_EQ(hw.on_activate(state), CallbackReturn::ERROR);
  EXPECT_FALSE(enable_called);
}

TEST(M1HardwareLifecycleTest, ActivationAbortsBeforeEnableOnPreCheckAlarm)
{
  auto driver = std::make_shared<FixtureM1Driver>();
  bool enable_called = false;
  driver->set_transact_override([&enable_called](const std::vector<uint8_t> & req) {
      if (req.size() >= 2 && req[1] == 0x03) {
        std::vector<uint8_t> rsp(35, 0);
        rsp[0] = 0x65;
        rsp[1] = 0x03;
        rsp[2] = 32;
        rsp[6] = 0x01;  // Alarm on Right drive
        return Result<std::vector<uint8_t>>::success(rsp);
      }
      if (req.size() >= 2 && req[1] == 0x17) {
        enable_called = true;
      }
      return Result<std::vector<uint8_t>>::failure(ErrorCode::INVALID_RESPONSE);
    });

  M1Hardware hw(driver);
  ASSERT_EQ(hw.on_init(create_test_params()), CallbackReturn::SUCCESS);
  rclcpp_lifecycle::State state;
  ASSERT_EQ(hw.on_configure(state), CallbackReturn::SUCCESS);
  EXPECT_EQ(hw.on_activate(state), CallbackReturn::ERROR);
  EXPECT_FALSE(enable_called);
}

TEST(M1HardwareLifecycleTest, StaleStateProtectionInReadAndWrite)
{
  auto driver = std::make_shared<FixtureM1Driver>();
  M1Hardware hw(driver);
  ASSERT_EQ(hw.on_init(create_test_params()), CallbackReturn::SUCCESS);
  rclcpp_lifecycle::State state;
  ASSERT_EQ(hw.on_configure(state), CallbackReturn::SUCCESS);
  ASSERT_EQ(hw.on_activate(state), CallbackReturn::SUCCESS);

  const rclcpp::Time now(0);
  const rclcpp::Duration dt(0, 20000000);

  // First read consumes cached active_state from on_activate
  EXPECT_EQ(hw.read(now, dt), return_type::OK);

  // Second consecutive read fails to prevent reusing stale feedback
  EXPECT_EQ(hw.read(now, dt), return_type::ERROR);

  // Write replenishes valid cached state
  EXPECT_EQ(hw.write(now, dt), return_type::OK);
  EXPECT_EQ(hw.read(now, dt), return_type::OK);
  EXPECT_EQ(hw.read(now, dt), return_type::ERROR);

  // Write failure clears valid cached state
  driver->set_transact_override([](const std::vector<uint8_t> &) {
      return Result<std::vector<uint8_t>>::failure(ErrorCode::TIMEOUT);
    });
  EXPECT_EQ(hw.write(now, dt), return_type::ERROR);
  EXPECT_EQ(hw.read(now, dt), return_type::ERROR);

  // Write returning alarm clears valid cached state
  driver->set_transact_override([](const std::vector<uint8_t> &) {
      std::vector<uint8_t> rsp(35, 0);
      rsp[0] = 0x65;
      rsp[1] = 0x17;
      rsp[2] = 32;
      rsp[6] = 0x01;  // Right drive alarm
      return Result<std::vector<uint8_t>>::success(rsp);
    });
  EXPECT_EQ(hw.write(now, dt), return_type::ERROR);
  EXPECT_EQ(hw.read(now, dt), return_type::ERROR);
}

TEST(M1HardwareLifecycleTest, ControlLoopPositionAndVelocityConversion)
{
  auto driver = std::make_shared<FixtureM1Driver>();
  M1Hardware hw(driver);
  ASSERT_EQ(hw.on_init(create_test_params()), CallbackReturn::SUCCESS);
  rclcpp_lifecycle::State state;
  ASSERT_EQ(hw.on_configure(state), CallbackReturn::SUCCESS);
  ASSERT_EQ(hw.on_activate(state), CallbackReturn::SUCCESS);
  const rclcpp::Time now(0);
  const rclcpp::Duration dt(0, 20000000);
  ASSERT_EQ(hw.read(now, dt), return_type::OK);
  driver->set_transact_override([](const std::vector<uint8_t> & req) {
      EXPECT_EQ(req[0], 0x65);
      EXPECT_EQ(req[1], 0x17);
      std::vector<uint8_t> response(35, 0);
      response[0] = 0x65;
      response[1] = 0x17;
      response[2] = 32;
      // Right (ID 1, sign -1): Index = -1, Pos = 0 -> -10000 units -> +pi/10 rad wheel displacement
      response[13] = 0xFF;
      response[14] = 0xFF;
      response[15] = 0x00;
      response[16] = 0x00;
      // Left (ID 2, sign +1): Index = 1, Pos = 0 -> +10000 units -> +pi/10 rad wheel displacement
      response[29] = 0x00;
      response[30] = 0x01;
      response[31] = 0x00;
      response[32] = 0x00;
      return Result<std::vector<uint8_t>>::success(response);
    });
  ASSERT_EQ(hw.write(now, dt), return_type::OK);
  ASSERT_EQ(hw.read(now, dt), return_type::OK);
  const auto interfaces = hw.export_state_interfaces();
  EXPECT_NEAR(interfaces[0].get_optional<double>().value(), PI / 10.0, 1e-9);
  EXPECT_NEAR(interfaces[2].get_optional<double>().value(), PI / 10.0, 1e-9);
  EXPECT_EQ(driver->config_reads, 2u);
}

TEST(M1HardwareLifecycleTest, InvalidTimeoutParameterFails)
{
  M1Hardware hw(std::make_shared<FixtureM1Driver>());
  // Zero timeout
  auto params_zero = create_test_params("mock", 230400, 100);
  params_zero.hardware_info.hardware_parameters["response_timeout_ms"] = "0";
  params_zero.hardware_info.hardware_parameters.erase("timeout_ms");
  EXPECT_EQ(hw.on_init(params_zero), CallbackReturn::ERROR);

  // Negative timeout
  auto params_neg = create_test_params("mock", 230400, 100);
  params_neg.hardware_info.hardware_parameters["response_timeout_ms"] = "-50";
  params_neg.hardware_info.hardware_parameters.erase("timeout_ms");
  EXPECT_EQ(hw.on_init(params_neg), CallbackReturn::ERROR);

  // Non-numeric timeout
  auto params_str = create_test_params("mock", 230400, 100);
  params_str.hardware_info.hardware_parameters["response_timeout_ms"] = "invalid_timeout";
  params_str.hardware_info.hardware_parameters.erase("timeout_ms");
  EXPECT_EQ(hw.on_init(params_str), CallbackReturn::ERROR);
}

TEST(M1HardwareLifecycleTest, ExplicitResponseTimeoutAliasPasses)
{
  M1Hardware hw(std::make_shared<FixtureM1Driver>());
  auto params = create_test_params("mock", 230400, 100);
  params.hardware_info.hardware_parameters.erase("timeout_ms");
  params.hardware_info.hardware_parameters["response_timeout_ms"] = "100";
  EXPECT_EQ(hw.on_init(params), CallbackReturn::SUCCESS);
  EXPECT_EQ(hw.get_config().timeout_ms, 100u);
}

TEST(M1HardwareLifecycleTest, ExportInterfaces)
{
  M1Hardware hw(std::make_shared<FixtureM1Driver>());
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
  M1Hardware hw(std::make_shared<FixtureM1Driver>());
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
  M1Hardware hw(std::make_shared<FixtureM1Driver>());
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
  M1Hardware hw(std::make_shared<FixtureM1Driver>());
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
  M1Hardware hw(std::make_shared<FixtureM1Driver>());
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
    hardware_interface::ResourceManager rm(urdf, clock, logger, false);
    EXPECT_TRUE(rm.are_components_initialized());

    // The plugin loads without a ROS scale. Unconfigured hardware is unavailable.
    EXPECT_TRUE(rm.state_interface_exists("driving_wheel_joint_L/position"));
    EXPECT_TRUE(rm.state_interface_exists("driving_wheel_joint_R/position"));
    EXPECT_FALSE(rm.command_interface_is_available("driving_wheel_joint_L/velocity"));
    EXPECT_FALSE(rm.command_interface_is_available("driving_wheel_joint_R/velocity"));
  });
}

// =========================================================================
// 4. DiffDriveController + M1Hardware Integration Tests (IMP-008 Baseline)
// =========================================================================

class DiffDriveIntegrationTest : public ::testing::Test
{
protected:
  static void SetUpTestSuite()
  {
    if (!rclcpp::ok()) {
      rclcpp::init(0, nullptr);
    }
  }

  static const char * get_test_urdf()
  {
    return
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
      <param name="response_timeout_ms">100</param>
      <param name="left_driver_id">2</param>
      <param name="right_driver_id">1</param>
      <param name="gear_ratio">20.0</param>
      <param name="left_wheel_sign">1</param>
      <param name="right_wheel_sign">-1</param>
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
  }

  std::shared_ptr<diff_drive_controller::DiffDriveController> create_and_configure_controller(
    double wheel_separation = 0.555, double wheel_radius = 0.08)
  {
    auto controller = std::make_shared<diff_drive_controller::DiffDriveController>();
    rclcpp::NodeOptions node_options;
    node_options.parameter_overrides({
      {"left_wheel_names", std::vector<std::string>{"driving_wheel_joint_L"}},
      {"right_wheel_names", std::vector<std::string>{"driving_wheel_joint_R"}},
      {"wheel_separation", wheel_separation},
      {"wheel_radius", wheel_radius},
      {"use_stamped_vel", false},
      {"open_loop", false},
      {"publish_rate", 50.0},
    });

    const auto init_ret = controller->init("diff_drive_controller", "", 50, "", node_options);
    if (init_ret != controller_interface::return_type::OK) {
      return nullptr;
    }
    const auto & state = controller->configure();
    if (state.id() != lifecycle_msgs::msg::State::PRIMARY_STATE_INACTIVE) {
      return nullptr;
    }
    return controller;
  }
};

TEST_F(DiffDriveIntegrationTest, ControllerPluginDiscovery)
{
  pluginlib::ClassLoader<controller_interface::ChainableControllerInterface> loader(
    "controller_interface", "controller_interface::ChainableControllerInterface");

  std::vector<std::string> classes = loader.getDeclaredClasses();
  bool found = false;
  for (const auto & cls : classes) {
    if (cls == "diff_drive_controller/DiffDriveController") {
      found = true;
      break;
    }
  }
  EXPECT_TRUE(found) <<
    "diff_drive_controller/DiffDriveController was not found in declared classes";
}

TEST_F(DiffDriveIntegrationTest, FullIntegrationLifecycle)
{
  auto clock = std::make_shared<rclcpp::Clock>(RCL_ROS_TIME);
  auto logger = rclcpp::get_logger("diff_drive_test");

  hardware_interface::ResourceManager rm(clock, logger);
  import_fixture_hardware(rm, get_test_urdf(), clock);
  ASSERT_TRUE(rm.command_interface_is_available("driving_wheel_joint_L/velocity"));

  auto controller = create_and_configure_controller();
  ASSERT_NE(controller, nullptr);

  std::vector<hardware_interface::LoanedCommandInterface> loaned_commands;
  loaned_commands.emplace_back(rm.claim_command_interface("driving_wheel_joint_L/velocity"));
  loaned_commands.emplace_back(rm.claim_command_interface("driving_wheel_joint_R/velocity"));

  std::vector<hardware_interface::LoanedStateInterface> loaned_states;
  loaned_states.emplace_back(rm.claim_state_interface("driving_wheel_joint_L/position"));
  loaned_states.emplace_back(rm.claim_state_interface("driving_wheel_joint_L/velocity"));
  loaned_states.emplace_back(rm.claim_state_interface("driving_wheel_joint_R/position"));
  loaned_states.emplace_back(rm.claim_state_interface("driving_wheel_joint_R/velocity"));

  controller->assign_interfaces(std::move(loaned_commands), std::move(loaned_states));

  const auto & active_state = controller->get_node()->activate();
  EXPECT_EQ(active_state.id(), lifecycle_msgs::msg::State::PRIMARY_STATE_ACTIVE);

  const auto & inactive_state = controller->get_node()->deactivate();
  EXPECT_EQ(inactive_state.id(), lifecycle_msgs::msg::State::PRIMARY_STATE_INACTIVE);
}

TEST_F(DiffDriveIntegrationTest, LinearForwardCommandPath)
{
  auto clock = std::make_shared<rclcpp::Clock>(RCL_ROS_TIME);
  auto logger = rclcpp::get_logger("diff_drive_test");

  hardware_interface::ResourceManager rm(clock, logger);
  import_fixture_hardware(rm, get_test_urdf(), clock);
  ASSERT_TRUE(rm.command_interface_is_available("driving_wheel_joint_L/velocity"));

  auto controller = create_and_configure_controller(0.555, 0.08);
  ASSERT_NE(controller, nullptr);

  std::vector<hardware_interface::LoanedCommandInterface> loaned_commands;
  loaned_commands.emplace_back(rm.claim_command_interface("driving_wheel_joint_L/velocity"));
  loaned_commands.emplace_back(rm.claim_command_interface("driving_wheel_joint_R/velocity"));

  std::vector<hardware_interface::LoanedStateInterface> loaned_states;
  loaned_states.emplace_back(rm.claim_state_interface("driving_wheel_joint_L/position"));
  loaned_states.emplace_back(rm.claim_state_interface("driving_wheel_joint_L/velocity"));
  loaned_states.emplace_back(rm.claim_state_interface("driving_wheel_joint_R/position"));
  loaned_states.emplace_back(rm.claim_state_interface("driving_wheel_joint_R/velocity"));

  controller->assign_interfaces(std::move(loaned_commands), std::move(loaned_states));
  ASSERT_EQ(controller->get_node()->activate().id(),
    lifecycle_msgs::msg::State::PRIMARY_STATE_ACTIVE);

  // Claim reference interfaces: [0] = linear velocity, [1] = angular velocity
  auto ref_ifaces = controller->export_reference_interfaces();
  ASSERT_EQ(ref_ifaces.size(), 2u);

  // Request v = 0.4 m/s forward, omega = 0.0 rad/s
  EXPECT_TRUE(ref_ifaces[0]->set_value(0.4));
  EXPECT_TRUE(ref_ifaces[1]->set_value(0.0));

  rclcpp::Time now(1, 0, RCL_ROS_TIME);
  rclcpp::Duration dt(0, 20000000);  // 20 ms cycle (50 Hz)

  EXPECT_EQ(
    controller->update_and_write_commands(now, dt),
    controller_interface::return_type::OK);

  // Write through hardware interface to verify motor conversion and FC17 transaction
  EXPECT_EQ(rm.write(now, dt).result, return_type::OK);

  // Verify feedback is non-null and correctly read on next cycle:
  // Expected wheel velocity: omega = v / r = 0.4 / 0.08 = 5.0 rad/s
  EXPECT_EQ(rm.read(now, dt).result, return_type::OK);
  auto left_vel_state = rm.claim_state_interface("driving_wheel_joint_L/velocity");
  auto right_vel_state = rm.claim_state_interface("driving_wheel_joint_R/velocity");
  EXPECT_NEAR(left_vel_state.get_optional<double>().value_or(0.0), 5.0, 0.01);
  EXPECT_NEAR(right_vel_state.get_optional<double>().value_or(0.0), 5.0, 0.01);
}

TEST_F(DiffDriveIntegrationTest, AngularRotationCommandPath)
{
  auto clock = std::make_shared<rclcpp::Clock>(RCL_ROS_TIME);
  auto logger = rclcpp::get_logger("diff_drive_test");

  hardware_interface::ResourceManager rm(clock, logger);
  import_fixture_hardware(rm, get_test_urdf(), clock);
  ASSERT_TRUE(rm.command_interface_is_available("driving_wheel_joint_L/velocity"));

  auto controller = create_and_configure_controller(0.555, 0.08);
  ASSERT_NE(controller, nullptr);

  std::vector<hardware_interface::LoanedCommandInterface> loaned_commands;
  loaned_commands.emplace_back(rm.claim_command_interface("driving_wheel_joint_L/velocity"));
  loaned_commands.emplace_back(rm.claim_command_interface("driving_wheel_joint_R/velocity"));

  std::vector<hardware_interface::LoanedStateInterface> loaned_states;
  loaned_states.emplace_back(rm.claim_state_interface("driving_wheel_joint_L/position"));
  loaned_states.emplace_back(rm.claim_state_interface("driving_wheel_joint_L/velocity"));
  loaned_states.emplace_back(rm.claim_state_interface("driving_wheel_joint_R/position"));
  loaned_states.emplace_back(rm.claim_state_interface("driving_wheel_joint_R/velocity"));

  controller->assign_interfaces(std::move(loaned_commands), std::move(loaned_states));
  ASSERT_EQ(controller->get_node()->activate().id(),
    lifecycle_msgs::msg::State::PRIMARY_STATE_ACTIVE);

  auto ref_ifaces = controller->export_reference_interfaces();
  ASSERT_EQ(ref_ifaces.size(), 2u);

  // Request pure yaw rotation: v = 0.0 m/s, omega = +1.0 rad/s (counter-clockwise)
  EXPECT_TRUE(ref_ifaces[0]->set_value(0.0));
  EXPECT_TRUE(ref_ifaces[1]->set_value(1.0));

  rclcpp::Time now(1, 0, RCL_ROS_TIME);
  rclcpp::Duration dt(0, 20000000);  // 20 ms

  EXPECT_EQ(
    controller->update_and_write_commands(now, dt),
    controller_interface::return_type::OK);

  // Kinematics:
  // v_L = -omega * (d / 2) = -1.0 * 0.2775 = -0.2775 m/s -> omega_L = -3.46875 rad/s
  // v_R = +omega * (d / 2) = +1.0 * 0.2775 = +0.2775 m/s -> omega_R = +3.46875 rad/s
  // Motor target RPMs:
  // Left Motor (sign +1): -3.46875 * 20 * 60 / (2*pi) = -662 RPM
  // Right Motor (sign -1): -(+3.46875) * 20 * 60 / (2*pi) = -662 RPM
  // Both motors spin in negative direction for physical base CCW rotation!
  EXPECT_EQ(rm.write(now, dt).result, return_type::OK);
  EXPECT_EQ(rm.read(now, dt).result, return_type::OK);

  auto left_vel_state = rm.claim_state_interface("driving_wheel_joint_L/velocity");
  auto right_vel_state = rm.claim_state_interface("driving_wheel_joint_R/velocity");
  EXPECT_NEAR(left_vel_state.get_optional<double>().value_or(0.0), -3.46875, 0.01);
  EXPECT_NEAR(right_vel_state.get_optional<double>().value_or(0.0), +3.46875, 0.01);
}

TEST_F(DiffDriveIntegrationTest, ZeroCommandPath)
{
  auto clock = std::make_shared<rclcpp::Clock>(RCL_ROS_TIME);
  auto logger = rclcpp::get_logger("diff_drive_test");

  hardware_interface::ResourceManager rm(clock, logger);
  import_fixture_hardware(rm, get_test_urdf(), clock);
  ASSERT_TRUE(rm.command_interface_is_available("driving_wheel_joint_L/velocity"));

  auto controller = create_and_configure_controller(0.555, 0.08);
  ASSERT_NE(controller, nullptr);

  std::vector<hardware_interface::LoanedCommandInterface> loaned_commands;
  loaned_commands.emplace_back(rm.claim_command_interface("driving_wheel_joint_L/velocity"));
  loaned_commands.emplace_back(rm.claim_command_interface("driving_wheel_joint_R/velocity"));

  std::vector<hardware_interface::LoanedStateInterface> loaned_states;
  loaned_states.emplace_back(rm.claim_state_interface("driving_wheel_joint_L/position"));
  loaned_states.emplace_back(rm.claim_state_interface("driving_wheel_joint_L/velocity"));
  loaned_states.emplace_back(rm.claim_state_interface("driving_wheel_joint_R/position"));
  loaned_states.emplace_back(rm.claim_state_interface("driving_wheel_joint_R/velocity"));

  controller->assign_interfaces(std::move(loaned_commands), std::move(loaned_states));
  ASSERT_EQ(controller->get_node()->activate().id(),
    lifecycle_msgs::msg::State::PRIMARY_STATE_ACTIVE);

  auto ref_ifaces = controller->export_reference_interfaces();
  ASSERT_EQ(ref_ifaces.size(), 2u);

  // Request zero velocity: v = 0.0, omega = 0.0
  EXPECT_TRUE(ref_ifaces[0]->set_value(0.0));
  EXPECT_TRUE(ref_ifaces[1]->set_value(0.0));

  rclcpp::Time now(1, 0, RCL_ROS_TIME);
  rclcpp::Duration dt(0, 20000000);

  EXPECT_EQ(
    controller->update_and_write_commands(now, dt),
    controller_interface::return_type::OK);

  EXPECT_EQ(rm.write(now, dt).result, return_type::OK);
  EXPECT_EQ(rm.read(now, dt).result, return_type::OK);

  auto left_vel_state = rm.claim_state_interface("driving_wheel_joint_L/velocity");
  auto right_vel_state = rm.claim_state_interface("driving_wheel_joint_R/velocity");
  EXPECT_DOUBLE_EQ(left_vel_state.get_optional<double>().value_or(1.0), 0.0);
  EXPECT_DOUBLE_EQ(right_vel_state.get_optional<double>().value_or(1.0), 0.0);
}

TEST_F(DiffDriveIntegrationTest, FeedbackPathPositionProgression)
{
  auto clock = std::make_shared<rclcpp::Clock>(RCL_ROS_TIME);
  auto logger = rclcpp::get_logger("diff_drive_test");

  hardware_interface::ResourceManager rm(clock, logger);
  import_fixture_hardware(rm, get_test_urdf(), clock);
  ASSERT_TRUE(rm.command_interface_is_available("driving_wheel_joint_L/velocity"));

  auto controller = create_and_configure_controller(0.555, 0.08);
  ASSERT_NE(controller, nullptr);

  std::vector<hardware_interface::LoanedCommandInterface> loaned_commands;
  loaned_commands.emplace_back(rm.claim_command_interface("driving_wheel_joint_L/velocity"));
  loaned_commands.emplace_back(rm.claim_command_interface("driving_wheel_joint_R/velocity"));

  std::vector<hardware_interface::LoanedStateInterface> loaned_states;
  loaned_states.emplace_back(rm.claim_state_interface("driving_wheel_joint_L/position"));
  loaned_states.emplace_back(rm.claim_state_interface("driving_wheel_joint_L/velocity"));
  loaned_states.emplace_back(rm.claim_state_interface("driving_wheel_joint_R/position"));
  loaned_states.emplace_back(rm.claim_state_interface("driving_wheel_joint_R/velocity"));

  controller->assign_interfaces(std::move(loaned_commands), std::move(loaned_states));
  ASSERT_EQ(controller->get_node()->activate().id(),
    lifecycle_msgs::msg::State::PRIMARY_STATE_ACTIVE);

  auto ref_ifaces = controller->export_reference_interfaces();
  EXPECT_TRUE(ref_ifaces[0]->set_value(0.4));
  EXPECT_TRUE(ref_ifaces[1]->set_value(0.0));

  rclcpp::Time now(1, 0, RCL_ROS_TIME);
  rclcpp::Duration dt(0, 20000000);  // 20 ms

  // Execute 5 consecutive control cycles and verify smooth position tracking without NaN
  double prev_left_pos = 0.0;
  double prev_right_pos = 0.0;
  for (int step = 0; step < 5; ++step) {
    now = now + dt;
    EXPECT_EQ(
      controller->update_and_write_commands(now, dt),
      controller_interface::return_type::OK);
    EXPECT_EQ(rm.write(now, dt).result, return_type::OK);
    EXPECT_EQ(rm.read(now, dt).result, return_type::OK);

    auto left_pos = rm.claim_state_interface("driving_wheel_joint_L/position");
    auto right_pos = rm.claim_state_interface("driving_wheel_joint_R/position");
    const double curr_left = left_pos.get_optional<double>().value_or(0.0);
    const double curr_right = right_pos.get_optional<double>().value_or(0.0);

    EXPECT_FALSE(std::isnan(curr_left));
    EXPECT_FALSE(std::isnan(curr_right));
    EXPECT_GE(curr_left, prev_left_pos);
    EXPECT_GE(curr_right, prev_right_pos);
    prev_left_pos = curr_left;
    prev_right_pos = curr_right;
  }
}

TEST_F(DiffDriveIntegrationTest, CommandSubstitutionProhibitionPolicy)
{
  M1Hardware hw(std::make_shared<FixtureM1Driver>());
  auto params = create_test_params("mock", 230400, 100);
  ASSERT_EQ(hw.on_init(params), CallbackReturn::SUCCESS);

  rclcpp_lifecycle::State unconfigured(
    lifecycle_msgs::msg::State::PRIMARY_STATE_UNCONFIGURED, "unconfigured");
  rclcpp_lifecycle::State inactive(
    lifecycle_msgs::msg::State::PRIMARY_STATE_INACTIVE, "inactive");
  ASSERT_EQ(hw.on_configure(unconfigured), CallbackReturn::SUCCESS);
  ASSERT_EQ(hw.on_activate(inactive), CallbackReturn::SUCCESS);

  auto cmd_ifaces = hw.export_command_interfaces();

  // Test 1: NaN command must be rejected with return_type::ERROR, never substituted with motion
  EXPECT_TRUE(cmd_ifaces[0].set_value(std::numeric_limits<double>::quiet_NaN()));
  EXPECT_TRUE(cmd_ifaces[1].set_value(0.5));
  rclcpp::Time now(1, 0, RCL_ROS_TIME);
  rclcpp::Duration dt(0, 20000000);
  EXPECT_EQ(hw.write(now, dt), return_type::ERROR);

  // Test 2: Inf command must be rejected with return_type::ERROR, never substituted with motion
  EXPECT_TRUE(cmd_ifaces[0].set_value(std::numeric_limits<double>::infinity()));
  EXPECT_TRUE(cmd_ifaces[1].set_value(0.5));
  EXPECT_EQ(hw.write(now, dt), return_type::ERROR);

  // Clean shutdown
  rclcpp_lifecycle::State active(
    lifecycle_msgs::msg::State::PRIMARY_STATE_ACTIVE, "active");
  EXPECT_EQ(hw.on_deactivate(active), CallbackReturn::SUCCESS);
}

TEST_F(DiffDriveIntegrationTest, SafeStopChainOnDeactivate)
{
  M1Hardware hw(std::make_shared<FixtureM1Driver>());
  auto params = create_test_params("mock", 230400, 100);
  ASSERT_EQ(hw.on_init(params), CallbackReturn::SUCCESS);

  rclcpp_lifecycle::State unconfigured(
    lifecycle_msgs::msg::State::PRIMARY_STATE_UNCONFIGURED, "unconfigured");
  rclcpp_lifecycle::State inactive(
    lifecycle_msgs::msg::State::PRIMARY_STATE_INACTIVE, "inactive");
  ASSERT_EQ(hw.on_configure(unconfigured), CallbackReturn::SUCCESS);
  ASSERT_EQ(hw.on_activate(inactive), CallbackReturn::SUCCESS);

  // Verify hardware is active and commands can be written
  auto cmd_ifaces = hw.export_command_interfaces();
  EXPECT_TRUE(cmd_ifaces[0].set_value(1.0));
  EXPECT_TRUE(cmd_ifaces[1].set_value(1.0));
  rclcpp::Time now(1, 0, RCL_ROS_TIME);
  rclcpp::Duration dt(0, 20000000);
  EXPECT_EQ(hw.write(now, dt), return_type::OK);

  // Trigger deactivation sequence (stop -> disable -> disconnect)
  rclcpp_lifecycle::State active(
    lifecycle_msgs::msg::State::PRIMARY_STATE_ACTIVE, "active");
  EXPECT_EQ(hw.on_deactivate(active), CallbackReturn::SUCCESS);

  // After deactivation, read/write should fail without activation
  EXPECT_EQ(hw.read(now, dt), return_type::ERROR);
  EXPECT_EQ(hw.write(now, dt), return_type::ERROR);
}

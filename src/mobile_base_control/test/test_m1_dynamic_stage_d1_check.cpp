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
#include <sstream>
#include <string>
#include <vector>

#include "mobile_base_control/m1_dynamic_stage_d1_check.hpp"
#include "mobile_base_control/m1_hardware.hpp"

namespace mobile_base_control
{

TEST(DynamicStageD1Test, DryRunCausesZeroTransportCalls)
{
  DynamicStageD1Options opts;
  opts.dry_run = true;
  opts.execute = false;
  opts.left_wheel_cmd_rad_s = 0.5;

  std::ostringstream out;
  std::ostringstream err;

  int ret = run_dynamic_stage_d1_check(opts, nullptr, out, err);
  EXPECT_EQ(ret, 0);
  EXPECT_TRUE(err.str().empty());
  EXPECT_NE(out.str().find("[DRY RUN MODE]"), std::string::npos);
  EXPECT_NE(out.str().find("Target Wheel          : LEFT WHEEL ONLY"), std::string::npos);
  EXPECT_NE(out.str().find("Right Wheel Target    : 0.0 rad/s"), std::string::npos);
}

TEST(DynamicStageD1Test, ProhibitedCliParametersRejected)
{
  std::vector<std::string> prohibited_args = {
    "--rpm", "--right", "--right-vel", "--both", "--reverse", "--linear", "--angular", "--cmd_vel"
  };

  for (const auto & bad_arg : prohibited_args) {
    std::vector<const char *> argv = {"stage_d1_check", bad_arg.c_str()};
    EXPECT_THROW(
      parse_stage_d1_command_line(static_cast<int>(argv.size()), const_cast<char **>(argv.data())),
      std::invalid_argument) << "Failed to reject prohibited CLI argument: " << bad_arg;
  }
}

TEST(DynamicStageD1Test, LeftWheelVelocityBoundsValidation)
{
  DynamicStageD1Options opts;

  // Zero command rejected
  opts.left_wheel_cmd_rad_s = 0.0;
  auto res = validate_stage_d1_options(opts);
  EXPECT_FALSE(res.valid);

  // Negative command rejected
  opts.left_wheel_cmd_rad_s = -0.5;
  res = validate_stage_d1_options(opts);
  EXPECT_FALSE(res.valid);

  // NaN rejected
  opts.left_wheel_cmd_rad_s = std::numeric_limits<double>::quiet_NaN();
  res = validate_stage_d1_options(opts);
  EXPECT_FALSE(res.valid);

  // Exceeds harness sanity clamping limit (> 1.5 rad/s) rejected
  opts.left_wheel_cmd_rad_s = 2.0;
  res = validate_stage_d1_options(opts);
  EXPECT_FALSE(res.valid);

  // Valid provisional speed (0.5 rad/s) accepted
  opts.left_wheel_cmd_rad_s = 0.5;
  res = validate_stage_d1_options(opts);
  EXPECT_TRUE(res.valid);

  // Valid limit speed (1.5 rad/s) accepted
  opts.left_wheel_cmd_rad_s = 1.5;
  res = validate_stage_d1_options(opts);
  EXPECT_TRUE(res.valid);
}

TEST(DynamicStageD1Test, CycleCountBoundsValidation)
{
  DynamicStageD1Options opts;
  opts.left_wheel_cmd_rad_s = 0.5;

  // Active cycles too low (< 10)
  opts.active_cycles = 5;
  auto res = validate_stage_d1_options(opts);
  EXPECT_FALSE(res.valid);

  // Active cycles too high (> 150)
  opts.active_cycles = 200;
  res = validate_stage_d1_options(opts);
  EXPECT_FALSE(res.valid);

  // Warmup cycles too high (> 30)
  opts.active_cycles = 60;
  opts.warmup_cycles = 50;
  res = validate_stage_d1_options(opts);
  EXPECT_FALSE(res.valid);

  // Valid configuration
  opts.warmup_cycles = 10;
  opts.active_cycles = 60;
  opts.cooldown_cycles = 10;
  res = validate_stage_d1_options(opts);
  EXPECT_TRUE(res.valid);
}

TEST(DynamicStageD1Test, MathematicalSignAndGearConversion)
{
  const double gear_ratio = 20.0;
  const int8_t left_sign = +1;
  const int8_t right_sign = -1;
  const double max_rpm = 3000.0;

  // 1. Left wheel 0.5 rad/s -> ~95 RPM
  const double left_cmd_0_5 = 0.5;
  const int16_t left_rpm_0_5 = M1Hardware::wheel_rad_s_to_motor_rpm(
    left_cmd_0_5, gear_ratio, left_sign, max_rpm);
  EXPECT_EQ(left_rpm_0_5, 95);  // round(0.5 * 20 * 60 / 2pi) = 95

  // 2. Left wheel 1.0 rad/s -> ~191 RPM
  const double left_cmd_1_0 = 1.0;
  const int16_t left_rpm_1_0 = M1Hardware::wheel_rad_s_to_motor_rpm(
    left_cmd_1_0, gear_ratio, left_sign, max_rpm);
  EXPECT_EQ(left_rpm_1_0, 191);  // round(1.0 * 20 * 60 / 2pi) = 191

  // 3. Right wheel command strictly 0.0 -> strictly 0 RPM
  const double right_cmd_0_0 = 0.0;
  const int16_t right_rpm_0_0 = M1Hardware::wheel_rad_s_to_motor_rpm(
    right_cmd_0_0, gear_ratio, right_sign, max_rpm);
  EXPECT_EQ(right_rpm_0_0, 0);

  // 4. Actual RPM 95 -> ~0.4974 rad/s
  const double left_actual_vel = M1Hardware::motor_rpm_to_wheel_rad_s(
    left_rpm_0_5, gear_ratio, left_sign);
  EXPECT_NEAR(left_actual_vel, 0.4974, 1e-3);

  // 5. Position steps conversion (10000 steps/rev * 20 gear = 200000 steps/wheel rev)
  PositionTracker tracker;
  tracker.update(0);
  tracker.update(200000);  // 1 full wheel revolution
  const double wheel_rad = (static_cast<double>(tracker.accumulated_steps) / (10000.0 * 20.0)) *
    (2.0 * M_PI) * static_cast<double>(left_sign);
  EXPECT_NEAR(wheel_rad, 2.0 * M_PI, 1e-5);
}

TEST(DynamicStageD1Test, URDFStructureAndParams)
{
  DynamicStageD1Options opts;
  opts.device = "/dev/ttyUSB0";
  opts.baud = 230400;
  opts.timeout_ms = 50;
  opts.driver_a = 1;
  opts.driver_b = 2;

  std::string urdf = build_stage_d1_urdf(opts);
  EXPECT_NE(urdf.find("mobile_base_control/M1Hardware"), std::string::npos);
  EXPECT_NE(urdf.find("<param name=\"serial_port\">/dev/ttyUSB0</param>"), std::string::npos);
  EXPECT_NE(urdf.find("<param name=\"baud_rate\">230400</param>"), std::string::npos);
  EXPECT_NE(urdf.find("<param name=\"response_timeout_ms\">50</param>"), std::string::npos);
  EXPECT_NE(urdf.find("<param name=\"left_driver_id\">2</param>"), std::string::npos);
  EXPECT_NE(urdf.find("<param name=\"right_driver_id\">1</param>"), std::string::npos);
  EXPECT_NE(urdf.find("driving_wheel_joint_L"), std::string::npos);
  EXPECT_NE(urdf.find("driving_wheel_joint_R"), std::string::npos);
}

}  // namespace mobile_base_control

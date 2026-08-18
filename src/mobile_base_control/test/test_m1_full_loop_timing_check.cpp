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
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include "mobile_base_control/m1_full_loop_timing_check.hpp"
#include "mobile_base_control/m1_hardware.hpp"

using mobile_base_control::FullLoopTimingOptions;
using mobile_base_control::M1Hardware;
using mobile_base_control::parse_full_loop_command_line;
using mobile_base_control::run_full_loop_timing_check;
using mobile_base_control::validate_full_loop_options;

TEST(FullLoopTimingCheckTest, DryRunCausesZeroTransportCalls)
{
  FullLoopTimingOptions opts;
  opts.dry_run = true;
  opts.execute = false;
  opts.target_rate_hz = 30.0;
  opts.warmup_cycles = 20;
  opts.measured_cycles = 1000;

  std::ostringstream out, err;
  int ret = run_full_loop_timing_check(opts, nullptr, out, err);

  EXPECT_EQ(ret, 0);
  EXPECT_NE(out.str().find("IMP-008 Full ros2_control Loop Timing Check (DRY-RUN)"),
    std::string::npos);
  EXPECT_NE(out.str().find("Target Loop Rate   : 30 Hz (Period = 33.333 ms)"), std::string::npos);
  EXPECT_NE(out.str().find("Expected Writes    : 1023 control writes"), std::string::npos);
  EXPECT_NE(out.str().find("ALL COMMANDS HARD-BOUND TO ZERO VELOCITY"), std::string::npos);
}

TEST(FullLoopTimingCheckTest, NonZeroMotionParametersRejectedAtCli)
{
  const char * argv_rpm[] = {"m1_full_loop_timing_check", "--rpm", "100"};
  EXPECT_THROW(parse_full_loop_command_line(3, const_cast<char **>(argv_rpm)),
    std::invalid_argument);

  const char * argv_vel[] = {"m1_full_loop_timing_check", "--velocity", "1.0"};
  EXPECT_THROW(parse_full_loop_command_line(3, const_cast<char **>(argv_vel)),
    std::invalid_argument);

  const char * argv_speed[] = {"m1_full_loop_timing_check", "--speed", "50"};
  EXPECT_THROW(parse_full_loop_command_line(3, const_cast<char **>(argv_speed)),
    std::invalid_argument);

  const char * argv_lin[] = {"m1_full_loop_timing_check", "--linear", "0.2"};
  EXPECT_THROW(parse_full_loop_command_line(3, const_cast<char **>(argv_lin)),
    std::invalid_argument);

  const char * argv_ang[] = {"m1_full_loop_timing_check", "--angular", "0.5"};
  EXPECT_THROW(parse_full_loop_command_line(3, const_cast<char **>(argv_ang)),
    std::invalid_argument);

  const char * argv_cmd[] = {"m1_full_loop_timing_check", "--cmd_vel", "0.1"};
  EXPECT_THROW(parse_full_loop_command_line(3, const_cast<char **>(argv_cmd)),
    std::invalid_argument);
}

TEST(FullLoopTimingCheckTest, BoundedOptionValidation)
{
  FullLoopTimingOptions opts;
  opts.warmup_cycles = 101;  // > 100
  auto val = validate_full_loop_options(opts);
  EXPECT_FALSE(val.valid);

  opts.warmup_cycles = 20;
  opts.measured_cycles = 2001;  // > 2000
  val = validate_full_loop_options(opts);
  EXPECT_FALSE(val.valid);

  opts.measured_cycles = 1000;
  opts.target_rate_hz = 0.0;  // Invalid rate
  val = validate_full_loop_options(opts);
  EXPECT_FALSE(val.valid);

  opts.target_rate_hz = 105.0;  // > 100 Hz
  val = validate_full_loop_options(opts);
  EXPECT_FALSE(val.valid);

  opts.target_rate_hz = 30.0;
  opts.driver_a = 1;
  opts.driver_b = 1;  // Same ID
  val = validate_full_loop_options(opts);
  EXPECT_FALSE(val.valid);

  opts.driver_b = 2;
  opts.timeout_ms = 0;  // Invalid timeout
  val = validate_full_loop_options(opts);
  EXPECT_FALSE(val.valid);
}

TEST(FullLoopTimingCheckTest, ZeroCommandInvariantGuaranteesZeroRpm)
{
  // Architectural proof: 0.0 rad/s input to M1Hardware conversions strictly yields 0 RPM
  EXPECT_EQ(M1Hardware::wheel_rad_s_to_motor_rpm(0.0, 20.0, 1, 3000.0), 0);
  EXPECT_EQ(M1Hardware::wheel_rad_s_to_motor_rpm(0.0, 20.0, -1, 3000.0), 0);
  EXPECT_EQ(M1Hardware::wheel_rad_s_to_motor_rpm(-0.0, 20.0, 1, 3000.0), 0);

  // NaN and Inf are also safely clamped to 0
  EXPECT_EQ(M1Hardware::wheel_rad_s_to_motor_rpm(std::numeric_limits<double>::quiet_NaN(), 20.0, 1,
    3000.0), 0);
  EXPECT_EQ(M1Hardware::wheel_rad_s_to_motor_rpm(std::numeric_limits<double>::infinity(), 20.0, 1,
    3000.0), 0);
}

TEST(FullLoopTimingCheckTest, UrdfGenerationStructure)
{
  FullLoopTimingOptions opts;
  opts.device = "/dev/ttyUSB0";
  opts.baud = 230400;
  opts.timeout_ms = 50;
  opts.driver_a = 1;
  opts.driver_b = 2;

  std::string urdf = mobile_base_control::build_full_loop_urdf(opts);

  EXPECT_NE(urdf.find("mobile_base_control/M1Hardware"), std::string::npos);
  EXPECT_NE(urdf.find("<param name=\"serial_port\">/dev/ttyUSB0</param>"), std::string::npos);
  EXPECT_NE(urdf.find("<param name=\"baud_rate\">230400</param>"), std::string::npos);
  EXPECT_NE(urdf.find("<param name=\"response_timeout_ms\">50</param>"), std::string::npos);
  EXPECT_NE(urdf.find("<param name=\"left_driver_id\">2</param>"), std::string::npos);
  EXPECT_NE(urdf.find("<param name=\"right_driver_id\">1</param>"), std::string::npos);
}

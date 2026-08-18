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

#ifndef MOBILE_BASE_CONTROL__M1_FULL_LOOP_TIMING_CHECK_HPP_
#define MOBILE_BASE_CONTROL__M1_FULL_LOOP_TIMING_CHECK_HPP_

#include <cstddef>
#include <cstdint>
#include <iosfwd>
#include <memory>
#include <string>
#include <vector>

#include "mobile_base_control/m1_driver.hpp"
#include "mobile_base_control/m1_hardware.hpp"
#include "mobile_base_control/m1_latency_stats.hpp"

namespace mobile_base_control
{

constexpr size_t FULL_LOOP_MAX_WARMUP_CYCLES = 100;
constexpr size_t FULL_LOOP_MAX_MEASURED_CYCLES = 2000;

struct FullLoopCycleSample
{
  size_t seq{0};
  double cycle_duration_us{0.0};       // Total cycle duration: read start to write end
  double period_interval_us{0.0};      // Actual interval between cycle k start and cycle k-1 start
  double read_duration_us{0.0};        // M1Hardware::read() duration
  double controller_duration_us{0.0};  // diff_drive_controller::update() duration
  double write_duration_us{0.0};       // M1Hardware::write() (FC17 transaction) duration
  bool deadline_missed{false};         // cycle_duration_us > target_period_us
  bool ok{false};
  int16_t driver1_rpm{0};
  int16_t driver2_rpm{0};
  uint16_t driver1_alarm{0};
  uint16_t driver2_alarm{0};
  double left_wheel_cmd_rad_s{0.0};
  double right_wheel_cmd_rad_s{0.0};
};

struct FullLoopTimingOptions
{
  std::string device{"/dev/ttyUSB0"};
  int baud{230400};
  int timeout_ms{50};
  int driver_a{1};  // Right
  int driver_b{2};  // Left
  double target_rate_hz{30.0};
  size_t warmup_cycles{20};
  size_t measured_cycles{1000};
  std::string raw_output_path{""};
  bool dry_run{true};
  bool execute{false};
};

struct FullLoopValidationResult
{
  bool valid{false};
  std::string error_message{""};
};

FullLoopValidationResult validate_full_loop_options(
  const FullLoopTimingOptions & options) noexcept;

FullLoopTimingOptions parse_full_loop_command_line(int argc, char ** argv);

std::string build_full_loop_urdf(const FullLoopTimingOptions & opts);

int run_full_loop_timing_check(
  const FullLoopTimingOptions & options,
  std::shared_ptr<M1Driver> mock_driver,
  std::ostream & out,
  std::ostream & err);

}  // namespace mobile_base_control

#endif  // MOBILE_BASE_CONTROL__M1_FULL_LOOP_TIMING_CHECK_HPP_

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

#ifndef MOBILE_BASE_CONTROL__M1_DYNAMIC_STAGE_D2_CHECK_HPP_
#define MOBILE_BASE_CONTROL__M1_DYNAMIC_STAGE_D2_CHECK_HPP_

#include <cstdint>
#include <iosfwd>
#include <memory>
#include <string>
#include <vector>

#include "mobile_base_control/m1_driver.hpp"
#include "mobile_base_control/m1_hardware.hpp"

namespace mobile_base_control
{

// Harness-internal CLI sanity limits for Stage D2 (not upstream safety bound)
constexpr double STAGE_D2_MAX_RIGHT_WHEEL_VEL_RAD_S = 1.5;  // Clamping limit (~286 motor RPM)
constexpr size_t STAGE_D2_MAX_WARMUP_CYCLES = 30;           // max 1.0 s @ 30 Hz
constexpr size_t STAGE_D2_MAX_ACTIVE_CYCLES = 150;          // max 5.0 s @ 30 Hz
constexpr size_t STAGE_D2_MAX_COOLDOWN_CYCLES = 30;         // max 1.0 s @ 30 Hz

struct DynamicStageD2Sample
{
  size_t seq{0};
  std::string phase{""};               // "warmup", "active", "cooldown"
  double cycle_duration_us{0.0};
  double left_cmd_rad_s{0.0};          // Strictly 0.0
  double right_cmd_rad_s{0.0};
  int16_t left_target_rpm{0};          // Strictly 0
  int16_t right_target_rpm{0};
  int16_t left_actual_rpm{0};
  int16_t right_actual_rpm{0};
  double left_wheel_vel_rad_s{0.0};
  double right_wheel_vel_rad_s{0.0};
  int32_t left_raw_steps{0};
  int32_t right_raw_steps{0};
  double left_wheel_pos_rad{0.0};
  double right_wheel_pos_rad{0.0};
  uint8_t driver1_status{0};
  uint8_t driver2_status{0};
  uint8_t driver1_alarm{0};
  uint8_t driver2_alarm{0};
  bool ok{false};
};

struct DynamicStageD2Options
{
  std::string device{"/dev/ttyUSB0"};
  int baud{230400};
  int timeout_ms{50};
  int driver_a{1};                     // Right Wheel (ID 1)
  int driver_b{2};                     // Left Wheel (ID 2)
  double target_rate_hz{30.0};
  double right_wheel_cmd_rad_s{0.5};   // Provisional Stage D2 command (rad/s)
  size_t warmup_cycles{10};
  size_t active_cycles{60};            // 60 cycles @ 30 Hz = 2.0 s
  size_t cooldown_cycles{10};
  std::string raw_output_path{""};
  bool dry_run{true};                  // Default to dry-run
  bool execute{false};                 // Requires explicit --execute
};

struct DynamicStageD2ValidationResult
{
  bool valid{false};
  std::string error_message{""};
};

DynamicStageD2ValidationResult validate_stage_d2_options(
  const DynamicStageD2Options & options) noexcept;

DynamicStageD2Options parse_stage_d2_command_line(int argc, char ** argv);

std::string build_stage_d2_urdf(const DynamicStageD2Options & opts);

int run_dynamic_stage_d2_check(
  const DynamicStageD2Options & options,
  std::shared_ptr<M1Driver> mock_driver,
  std::ostream & out,
  std::ostream & err);

}  // namespace mobile_base_control

#endif  // MOBILE_BASE_CONTROL__M1_DYNAMIC_STAGE_D2_CHECK_HPP_

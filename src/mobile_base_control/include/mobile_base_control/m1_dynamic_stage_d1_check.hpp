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

#ifndef MOBILE_BASE_CONTROL__M1_DYNAMIC_STAGE_D1_CHECK_HPP_
#define MOBILE_BASE_CONTROL__M1_DYNAMIC_STAGE_D1_CHECK_HPP_

#include <cstddef>
#include <cstdint>
#include <iosfwd>
#include <memory>
#include <string>
#include <vector>

#include "mobile_base_control/m1_driver.hpp"
#include "mobile_base_control/m1_hardware.hpp"

namespace mobile_base_control
{

// Architectural safety limits for Level 4 Stage D1 (Left-Wheel Only)
constexpr double STAGE_D1_MAX_LEFT_WHEEL_VEL_RAD_S = 1.5;  // ~286 motor RPM (~0.12 m/s linear)
constexpr size_t STAGE_D1_MAX_WARMUP_CYCLES = 30;           // max 1.0 s @ 30 Hz
constexpr size_t STAGE_D1_MAX_ACTIVE_CYCLES = 150;          // max 5.0 s @ 30 Hz
constexpr size_t STAGE_D1_MAX_COOLDOWN_CYCLES = 30;         // max 1.0 s @ 30 Hz

struct DynamicStageD1Sample
{
  size_t seq{0};
  std::string phase{""};               // "warmup", "active", "cooldown"
  double cycle_duration_us{0.0};
  double left_cmd_rad_s{0.0};
  double right_cmd_rad_s{0.0};         // Strictly 0.0
  int16_t left_target_rpm{0};
  int16_t right_target_rpm{0};         // Strictly 0
  int16_t left_actual_rpm{0};
  int16_t right_actual_rpm{0};
  int32_t left_pos_steps{0};
  int32_t right_pos_steps{0};
  double left_wheel_pos_rad{0.0};
  double right_wheel_pos_rad{0.0};
  double left_wheel_vel_rad_s{0.0};
  double right_wheel_vel_rad_s{0.0};
  uint16_t driver1_alarm{0};
  uint16_t driver2_alarm{0};
  uint16_t driver1_status{0};
  uint16_t driver2_status{0};
  bool ok{false};
};

struct DynamicStageD1Options
{
  std::string device{"/dev/ttyUSB0"};
  int baud{230400};
  int timeout_ms{50};                  // PROVISIONAL TEST CONDITION
  int driver_a{1};                     // Right (ID 1)
  int driver_b{2};                     // Left (ID 2)
  double target_rate_hz{30.0};
  double left_wheel_cmd_rad_s{0.5};    // Default provisional 0.5 rad/s (~95 motor RPM)
  size_t warmup_cycles{10};            // 10 cycles @ 30 Hz (~0.33 s)
  size_t active_cycles{60};            // 60 cycles @ 30 Hz (~2.0 s)
  size_t cooldown_cycles{10};          // 10 cycles @ 30 Hz (~0.33 s)
  std::string raw_output_path{""};
  bool dry_run{true};
  bool execute{false};
};

struct DynamicStageD1ValidationResult
{
  bool valid{false};
  std::string error_message{""};
};

DynamicStageD1ValidationResult validate_stage_d1_options(
  const DynamicStageD1Options & options) noexcept;

DynamicStageD1Options parse_stage_d1_command_line(int argc, char ** argv);

std::string build_stage_d1_urdf(const DynamicStageD1Options & opts);

int run_dynamic_stage_d1_check(
  const DynamicStageD1Options & options,
  std::shared_ptr<M1Driver> mock_driver,
  std::ostream & out,
  std::ostream & err);

}  // namespace mobile_base_control

#endif  // MOBILE_BASE_CONTROL__M1_DYNAMIC_STAGE_D1_CHECK_HPP_

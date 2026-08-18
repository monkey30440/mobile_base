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

#ifndef MOBILE_BASE_CONTROL__M1_FC17_LATENCY_CHECK_HPP_
#define MOBILE_BASE_CONTROL__M1_FC17_LATENCY_CHECK_HPP_

#include <cstdint>
#include <iosfwd>
#include <string>
#include <vector>

#include "mobile_base_control/m1_driver.hpp"
#include "mobile_base_control/m1_latency_stats.hpp"

namespace mobile_base_control
{

constexpr size_t FC17_MAX_WARMUP_SAMPLES = 100;
constexpr size_t FC17_MAX_MEASURED_SAMPLES = 2000;

struct Fc17LatencyCheckOptions
{
  std::string device{"/dev/ttyUSB0"};
  int baud{230400};
  uint32_t timeout_ms{50};  // PROVISIONAL LEVEL-3 TEST CONDITION; NOT PRODUCTION DEFAULT
  int driver_a{1};          // Right
  int driver_b{2};          // Left
  size_t warmup_samples{5};
  size_t measured_samples{20};
  int delay_ms{0};
  bool dry_run{false};
  bool execute{false};
  std::string raw_output_file{""};
};

struct Fc17ValidationResult
{
  bool valid{false};
  std::string error_message;
};

Fc17LatencyCheckOptions parse_fc17_latency_command_line(int argc, char ** argv);
Fc17ValidationResult validate_fc17_latency_options(const Fc17LatencyCheckOptions & opts);

int run_fc17_latency_check(
  const Fc17LatencyCheckOptions & opts,
  M1Driver & driver,
  std::ostream & out,
  std::ostream & err);

}  // namespace mobile_base_control

#endif  // MOBILE_BASE_CONTROL__M1_FC17_LATENCY_CHECK_HPP_

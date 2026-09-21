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

#ifndef MOBILE_BASE_CONTROL__M1_DIAGNOSTICS_HPP_
#define MOBILE_BASE_CONTROL__M1_DIAGNOSTICS_HPP_

#include <chrono>
#include <cstdint>
#include <optional>

#include "diagnostic_msgs/msg/diagnostic_status.hpp"
#include "mobile_base_control/m1_driver.hpp"

namespace mobile_base_control
{

using M1DiagnosticClock = std::chrono::steady_clock;
inline constexpr std::chrono::milliseconds kM1MotorStateFreshnessTimeout{200};

struct M1DiagnosticObservation
{
  bool communication_observed{false};
  ErrorCode communication{ErrorCode::NONE};
  int right_driver_id{0};
  std::optional<uint16_t> right_alarm;
  int left_driver_id{0};
  std::optional<uint16_t> left_alarm;
  std::optional<M1DiagnosticClock::time_point> motor_state_time;
};

diagnostic_msgs::msg::DiagnosticStatus make_m1_diagnostic_status(
  const M1DiagnosticObservation & observation,
  M1DiagnosticClock::time_point now);

}  // namespace mobile_base_control

#endif  // MOBILE_BASE_CONTROL__M1_DIAGNOSTICS_HPP_

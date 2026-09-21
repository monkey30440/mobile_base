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

#include "mobile_base_control/m1_diagnostics.hpp"

#include <string>
#include <utility>

#include "diagnostic_msgs/msg/key_value.hpp"

namespace mobile_base_control
{

namespace
{

void add_value(
  diagnostic_msgs::msg::DiagnosticStatus & status,
  const std::string & key,
  const std::string & value)
{
  diagnostic_msgs::msg::KeyValue entry;
  entry.key = key;
  entry.value = value;
  status.values.push_back(std::move(entry));
}

std::string alarm_to_string(const std::optional<uint16_t> & alarm)
{
  return alarm ? std::to_string(*alarm) : "unknown";
}

const char * communication_message(ErrorCode error) noexcept
{
  switch (error) {
    case ErrorCode::TIMEOUT:
      return "Communication timeout";
    case ErrorCode::NOT_CONNECTED:
      return "Not connected";
    case ErrorCode::SEND_FAILED:
      return "Communication send failed";
    default:
      return "Communication failed";
  }
}

}  // namespace

diagnostic_msgs::msg::DiagnosticStatus make_m1_diagnostic_status(
  const M1DiagnosticObservation & observation,
  M1DiagnosticClock::time_point now)
{
  diagnostic_msgs::msg::DiagnosticStatus status;
  status.name = "Drive System";
  status.hardware_id = "m1";
  const bool motor_state_unavailable =
    !observation.right_alarm || !observation.left_alarm ||
    !observation.motor_state_time ||
    now - *observation.motor_state_time > kM1MotorStateFreshnessTimeout;

  if (!observation.communication_observed) {
    status.level = diagnostic_msgs::msg::DiagnosticStatus::STALE;
    status.message = "Communication status unknown";
  } else if (observation.communication != ErrorCode::NONE) {
    status.level = diagnostic_msgs::msg::DiagnosticStatus::ERROR;
    status.message = communication_message(observation.communication);
  } else if (motor_state_unavailable) {
    status.level = diagnostic_msgs::msg::DiagnosticStatus::STALE;
    status.message = "Motor state unavailable";
  } else if (*observation.right_alarm != 0 && *observation.left_alarm != 0) {
    status.level = diagnostic_msgs::msg::DiagnosticStatus::ERROR;
    status.message = "Multiple drive alarms";
  } else if (*observation.right_alarm != 0) {
    status.level = diagnostic_msgs::msg::DiagnosticStatus::ERROR;
    status.message = "Right drive alarm";
  } else if (*observation.left_alarm != 0) {
    status.level = diagnostic_msgs::msg::DiagnosticStatus::ERROR;
    status.message = "Left drive alarm";
  } else {
    status.level = diagnostic_msgs::msg::DiagnosticStatus::OK;
    status.message = "Operating normally";
  }

  add_value(
    status, "communication",
    !observation.communication_observed ? "UNKNOWN" :
    observation.communication == ErrorCode::NONE ? "OK" :
    error_code_to_string(observation.communication));
  add_value(status, "right_driver_id", std::to_string(observation.right_driver_id));
  add_value(status, "right_alarm", alarm_to_string(observation.right_alarm));
  add_value(status, "left_driver_id", std::to_string(observation.left_driver_id));
  add_value(status, "left_alarm", alarm_to_string(observation.left_alarm));
  return status;
}

}  // namespace mobile_base_control

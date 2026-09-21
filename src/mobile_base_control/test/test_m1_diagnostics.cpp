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

#include <chrono>
#include <optional>
#include <string>
#include <vector>

#include "diagnostic_msgs/msg/diagnostic_status.hpp"
#include "mobile_base_control/m1_diagnostics.hpp"

using diagnostic_msgs::msg::DiagnosticStatus;
using mobile_base_control::ErrorCode;
using mobile_base_control::M1DiagnosticObservation;
using mobile_base_control::error_code_to_string;
using mobile_base_control::make_m1_diagnostic_status;

namespace
{

using SteadyClock = std::chrono::steady_clock;
const auto kNow = SteadyClock::time_point(std::chrono::seconds(10));

std::string value_for(const DiagnosticStatus & status, const std::string & key)
{
  for (const auto & value : status.values) {
    if (value.key == key) {
      return value.value;
    }
  }
  return {};
}

M1DiagnosticObservation healthy_observation(
  SteadyClock::time_point state_time = kNow)
{
  M1DiagnosticObservation observation;
  observation.communication_observed = true;
  observation.communication = ErrorCode::NONE;
  observation.right_driver_id = 1;
  observation.right_alarm = 0;
  observation.left_driver_id = 2;
  observation.left_alarm = 0;
  observation.motor_state_time = state_time;
  return observation;
}

TEST(M1DiagnosticsTest, ReportsUnobservedCommunicationAsStale)
{
  M1DiagnosticObservation observation;
  observation.right_driver_id = 1;
  observation.left_driver_id = 2;

  const auto status = make_m1_diagnostic_status(observation, kNow);

  EXPECT_EQ(status.level, DiagnosticStatus::STALE);
  EXPECT_EQ(value_for(status, "communication"), "UNKNOWN");
}

TEST(M1DiagnosticsTest, ReportsExactIdentityAndHealthyContract)
{
  const auto status = make_m1_diagnostic_status(healthy_observation(), kNow);

  EXPECT_EQ(status.name, "Drive System");
  EXPECT_EQ(status.hardware_id, "m1");
  EXPECT_EQ(status.level, DiagnosticStatus::OK);
  EXPECT_EQ(status.message, "Operating normally");
  ASSERT_EQ(status.values.size(), 5U);
  EXPECT_EQ(value_for(status, "communication"), "OK");
  EXPECT_EQ(value_for(status, "right_driver_id"), "1");
  EXPECT_EQ(value_for(status, "right_alarm"), "0");
  EXPECT_EQ(value_for(status, "left_driver_id"), "2");
  EXPECT_EQ(value_for(status, "left_alarm"), "0");
}

TEST(M1DiagnosticsTest, ReportsCommunicationFailuresBeforeAlarms)
{
  struct Case
  {
    ErrorCode error;
    const char * communication;
    const char * message;
  };
  const std::vector<Case> cases{
    {ErrorCode::TIMEOUT, "TIMEOUT", "Communication timeout"},
    {ErrorCode::RECEIVE_FAILED, "RECEIVE_FAILED", "Communication failed"},
    {ErrorCode::NOT_CONNECTED, "NOT_CONNECTED", "Not connected"},
    {ErrorCode::SEND_FAILED, "SEND_FAILED", "Communication send failed"},
  };

  for (const auto & test_case : cases) {
    auto observation = healthy_observation();
    observation.communication = test_case.error;
    observation.right_alarm = 10;
    observation.left_alarm = 20;
    observation.motor_state_time = kNow - std::chrono::seconds(1);
    const auto status = make_m1_diagnostic_status(observation, kNow);
    EXPECT_EQ(status.level, DiagnosticStatus::ERROR);
    EXPECT_EQ(status.message, test_case.message);
    EXPECT_EQ(value_for(status, "communication"), test_case.communication);
  }
}

TEST(M1DiagnosticsTest, PreservesEveryDriverCommunicationErrorName)
{
  const std::vector<ErrorCode> errors{
    ErrorCode::CONTEXT_CREATE_FAILED,
    ErrorCode::CONFIG_FAILED,
    ErrorCode::CONNECT_FAILED,
    ErrorCode::ALREADY_CONNECTED,
    ErrorCode::NOT_CONNECTED,
    ErrorCode::SEND_FAILED,
    ErrorCode::TIMEOUT,
    ErrorCode::RECEIVE_FAILED,
    ErrorCode::BAD_FUNCTION,
    ErrorCode::BAD_LENGTH,
    ErrorCode::INVALID_RESPONSE,
    ErrorCode::MODBUS_EXCEPTION,
    ErrorCode::INVALID_ARGUMENT,
  };

  for (const auto error : errors) {
    auto observation = healthy_observation();
    observation.communication = error;
    const auto status = make_m1_diagnostic_status(observation, kNow);
    EXPECT_EQ(value_for(status, "communication"), error_code_to_string(error));
  }
}

TEST(M1DiagnosticsTest, ReportsRightLeftAndMultipleDriveAlarms)
{
  struct Case
  {
    uint16_t right_alarm;
    uint16_t left_alarm;
    const char * message;
  };
  const std::vector<Case> cases{
    {7, 0, "Right drive alarm"},
    {0, 8, "Left drive alarm"},
    {7, 8, "Multiple drive alarms"},
  };

  for (const auto & test_case : cases) {
    auto observation = healthy_observation();
    observation.right_alarm = test_case.right_alarm;
    observation.left_alarm = test_case.left_alarm;
    const auto status = make_m1_diagnostic_status(observation, kNow);
    EXPECT_EQ(status.level, DiagnosticStatus::ERROR);
    EXPECT_EQ(status.message, test_case.message);
  }
}

TEST(M1DiagnosticsTest, ReportsUnknownAlarmsBeforeFirstMotorState)
{
  M1DiagnosticObservation observation;
  observation.communication_observed = true;
  observation.communication = ErrorCode::NONE;
  observation.right_driver_id = 1;
  observation.left_driver_id = 2;

  const auto status = make_m1_diagnostic_status(observation, kNow);

  EXPECT_EQ(status.level, DiagnosticStatus::STALE);
  EXPECT_EQ(status.message, "Motor state unavailable");
  EXPECT_EQ(value_for(status, "communication"), "OK");
  EXPECT_EQ(value_for(status, "right_alarm"), "unknown");
  EXPECT_EQ(value_for(status, "left_alarm"), "unknown");
}

TEST(M1DiagnosticsTest, ReportsCommunicationFailureWithoutMotorStateAsError)
{
  M1DiagnosticObservation observation;
  observation.communication_observed = true;
  observation.communication = ErrorCode::TIMEOUT;
  observation.right_driver_id = 1;
  observation.left_driver_id = 2;

  const auto status = make_m1_diagnostic_status(observation, kNow);

  EXPECT_EQ(status.level, DiagnosticStatus::ERROR);
  EXPECT_EQ(status.message, "Communication timeout");
  EXPECT_EQ(value_for(status, "communication"), "TIMEOUT");
}

TEST(M1DiagnosticsTest, TreatsExactlyFreshnessTimeoutAsFresh)
{
  const auto observation = healthy_observation(kNow - std::chrono::milliseconds(200));

  const auto status = make_m1_diagnostic_status(observation, kNow);

  EXPECT_EQ(status.level, DiagnosticStatus::OK);
}

TEST(M1DiagnosticsTest, ReportsMotorStateOlderThanFreshnessTimeoutAsStale)
{
  const auto observation = healthy_observation(kNow - std::chrono::milliseconds(201));

  const auto status = make_m1_diagnostic_status(observation, kNow);

  EXPECT_EQ(status.level, DiagnosticStatus::STALE);
  EXPECT_EQ(status.message, "Motor state unavailable");
}

}  // namespace

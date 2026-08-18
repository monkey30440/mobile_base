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

#include <array>
#include <sstream>
#include <string>
#include <vector>

#include "mobile_base_control/m1_control_check.hpp"

using mobile_base_control::ControlCheckOptions;
using mobile_base_control::ControlOp;
using mobile_base_control::ErrorCode;
using mobile_base_control::M1Driver;
using mobile_base_control::Result;
using mobile_base_control::parse_command_line;
using mobile_base_control::run_control_check;
using mobile_base_control::validate_options;

namespace
{
std::vector<uint8_t> create_dummy_md2_response(
  uint8_t fc,
  uint16_t s1_status, uint16_t s1_alarm, int16_t s1_rpm, int32_t s1_pos,
  uint16_t s2_status, uint16_t s2_alarm, int16_t s2_rpm, int32_t s2_pos)
{
  std::vector<uint8_t> rsp;
  rsp.push_back(0x65);
  rsp.push_back(fc);
  rsp.push_back(32);  // 2 drivers * 16 bytes = 32

  auto append_driver = [&](uint16_t st, uint16_t al, int16_t rpm, int32_t pos) {
      uint16_t pos_hi = static_cast<uint16_t>((static_cast<uint32_t>(pos) >> 16) & 0xFFFF);
      uint16_t pos_lo = static_cast<uint16_t>(static_cast<uint32_t>(pos) & 0xFFFF);
      uint16_t urpm = static_cast<uint16_t>(rpm);

      // Word 0: Status
      rsp.push_back(static_cast<uint8_t>((st >> 8) & 0xFF));
      rsp.push_back(static_cast<uint8_t>(st & 0xFF));
      // Word 1: Alarm
      rsp.push_back(static_cast<uint8_t>((al >> 8) & 0xFF));
      rsp.push_back(static_cast<uint8_t>(al & 0xFF));
      // Word 2: RPM
      rsp.push_back(static_cast<uint8_t>((urpm >> 8) & 0xFF));
      rsp.push_back(static_cast<uint8_t>(urpm & 0xFF));
      // Word 3: Bus Voltage (e.g. 2400 -> 24.00V)
      rsp.push_back(0x09);
      rsp.push_back(0x60);
      // Word 4: Current (e.g. 150 -> 1.50A)
      rsp.push_back(0x00);
      rsp.push_back(0x96);
      // Word 5: Pos HI
      rsp.push_back(static_cast<uint8_t>((pos_hi >> 8) & 0xFF));
      rsp.push_back(static_cast<uint8_t>(pos_hi & 0xFF));
      // Word 6: Pos LO
      rsp.push_back(static_cast<uint8_t>((pos_lo >> 8) & 0xFF));
      rsp.push_back(static_cast<uint8_t>(pos_lo & 0xFF));
      // Word 7: Error Check
      rsp.push_back(0x00);
      rsp.push_back(0x00);
    };

  append_driver(s1_status, s1_alarm, s1_rpm, s1_pos);
  append_driver(s2_status, s2_alarm, s2_rpm, s2_pos);
  return rsp;
}
}  // namespace

TEST(M1ControlCheckTest, OptionValidationMissingOp)
{
  ControlCheckOptions opts;
  opts.dry_run = true;
  auto res = validate_options(opts);
  EXPECT_FALSE(res.valid);
  EXPECT_NE(res.error_message.find("No operation specified"), std::string::npos);
}

TEST(M1ControlCheckTest, OptionValidationInvalidDriverIDs)
{
  ControlCheckOptions opts;
  opts.op = ControlOp::READ_STATE;
  opts.dry_run = true;

  opts.driver_a = 1;
  opts.driver_b = 1;  // Duplicate
  EXPECT_FALSE(validate_options(opts).valid);

  opts.driver_a = 0;  // Out of range
  opts.driver_b = 2;
  EXPECT_FALSE(validate_options(opts).valid);

  opts.driver_a = 1;
  opts.driver_b = 9;  // Out of range
  EXPECT_FALSE(validate_options(opts).valid);
}

TEST(M1ControlCheckTest, OptionValidationExchangeRequiresExplicitRpmAndDuration)
{
  ControlCheckOptions opts;
  opts.op = ControlOp::EXCHANGE;
  opts.dry_run = true;

  // Missing both
  auto res1 = validate_options(opts);
  EXPECT_FALSE(res1.valid);
  EXPECT_NE(res1.error_message.find("--rpm"), std::string::npos);

  // Missing duration
  opts.rpm = 50;
  auto res2 = validate_options(opts);
  EXPECT_FALSE(res2.valid);
  EXPECT_NE(res2.error_message.find("--duration-ms"), std::string::npos);

  // Duration is 0
  opts.duration_ms = 0;
  auto res3 = validate_options(opts);
  EXPECT_FALSE(res3.valid);
  EXPECT_NE(res3.error_message.find("--duration-ms"), std::string::npos);

  // Valid
  opts.duration_ms = 1000;
  EXPECT_TRUE(validate_options(opts).valid);
}

TEST(M1ControlCheckTest, OptionValidationSafetyConfirmationRequiredForRealExec)
{
  ControlCheckOptions opts;
  opts.op = ControlOp::ENABLE;
  opts.dry_run = false;
  opts.execute = false;

  // Real execution without --execute flag must be rejected
  auto res = validate_options(opts);
  EXPECT_FALSE(res.valid);
  EXPECT_NE(res.error_message.find("--execute"), std::string::npos);

  // With --execute flag, validation passes
  opts.execute = true;
  EXPECT_TRUE(validate_options(opts).valid);
}

TEST(M1ControlCheckTest, CommandLineParsing)
{
  std::vector<std::string> args = {
    "m1_control_check",
    "--op", "exchange",
    "--rpm", "60",
    "--duration-ms", "500",
    "--device", "/dev/ttyUSB1",
    "--baud", "115200",
    "--timeout-ms", "80",
    "--driver-a", "2",
    "--driver-b", "1",
    "--dry-run"
  };

  std::vector<char *> argv;
  for (auto & s : args) {
    argv.push_back(&s[0]);
  }

  auto opts = parse_command_line(static_cast<int>(argv.size()), argv.data());
  EXPECT_EQ(opts.op, ControlOp::EXCHANGE);
  ASSERT_TRUE(opts.rpm.has_value());
  EXPECT_EQ(opts.rpm.value(), 60);
  ASSERT_TRUE(opts.duration_ms.has_value());
  EXPECT_EQ(opts.duration_ms.value(), 500u);
  EXPECT_EQ(opts.device, "/dev/ttyUSB1");
  EXPECT_EQ(opts.baud, 115200);
  EXPECT_EQ(opts.timeout_ms, 80u);
  EXPECT_EQ(opts.driver_a, 2);
  EXPECT_EQ(opts.driver_b, 1);
  EXPECT_TRUE(opts.dry_run);
  EXPECT_FALSE(opts.execute);
}

TEST(M1ControlCheckTest, DryRunNeverCallsDriver)
{
  ControlCheckOptions opts;
  opts.op = ControlOp::EXCHANGE;
  opts.rpm = 50;
  opts.duration_ms = 1000;
  opts.dry_run = true;

  M1Driver driver;
  bool transact_called = false;
  driver.set_transact_override(
    [&transact_called](const std::vector<uint8_t> &) -> Result<std::vector<uint8_t>> {
      transact_called = true;
      return Result<std::vector<uint8_t>>::failure(ErrorCode::SEND_FAILED);
    });

  std::stringstream out;
  std::stringstream err;
  int ret = run_control_check(opts, driver, out, err);

  EXPECT_EQ(ret, 0);
  EXPECT_FALSE(transact_called);
  EXPECT_FALSE(driver.is_connected());

  const std::string out_str = out.str();
  EXPECT_NE(out_str.find("DRY RUN (NO HARDWARE WRITES EXECUTED)"), std::string::npos);
  EXPECT_NE(out_str.find("Target RPM      : 50 RPM"), std::string::npos);
  EXPECT_NE(out_str.find("Duration        : 1000 ms"), std::string::npos);
  EXPECT_NE(out_str.find("PASS: Dry-run preview generated successfully."), std::string::npos);
}

TEST(M1ControlCheckTest, PreviewContentForOperations)
{
  M1Driver driver;

  // Test Enable Preview
  {
    ControlCheckOptions opts;
    opts.op = ControlOp::ENABLE;
    opts.dry_run = true;
    std::stringstream out;
    std::stringstream err;
    int ret = run_control_check(opts, driver, out, err);
    EXPECT_EQ(ret, 0);
    EXPECT_NE(out.str().find("SVON 0x0006"), std::string::npos);
  }

  // Test Stop Preview
  {
    ControlCheckOptions opts;
    opts.op = ControlOp::STOP;
    opts.dry_run = true;
    std::stringstream out;
    std::stringstream err;
    int ret = run_control_check(opts, driver, out, err);
    EXPECT_EQ(ret, 0);
    EXPECT_NE(out.str().find("JG 0x0001 with 0 RPM"), std::string::npos);
  }

  // Test Disable Preview
  {
    ControlCheckOptions opts;
    opts.op = ControlOp::DISABLE;
    opts.dry_run = true;
    std::stringstream out;
    std::stringstream err;
    int ret = run_control_check(opts, driver, out, err);
    EXPECT_EQ(ret, 0);
    EXPECT_NE(out.str().find("SVOFF 0x0007"), std::string::npos);
  }
}

TEST(M1ControlCheckTest, MockExecutionFailureImmediatelyAborts)
{
  ControlCheckOptions opts;
  opts.op = ControlOp::ENABLE;
  opts.dry_run = false;
  opts.execute = true;

  M1Driver driver;
  // Inject connection override via transact failure
  driver.set_transact_override(
    [](const std::vector<uint8_t> &) -> Result<std::vector<uint8_t>> {
      return Result<std::vector<uint8_t>>::failure(ErrorCode::TIMEOUT);
    });

  // Note: driver.connect to a real port won't be called if we mock driver transact
  // But driver.connect will fail on non-existent port unless we test mock run
  opts.device = "/dev/non_existent_serial_port";
  std::stringstream out;
  std::stringstream err;
  int ret = run_control_check(opts, driver, out, err);

  // Connection failure returns code 2
  EXPECT_EQ(ret, 2);
  EXPECT_NE(err.str().find("FAIL: Connection failed"), std::string::npos);
}

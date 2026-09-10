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
#include <modbus/modbus.h>

#include <algorithm>
#include <cerrno>
#include <sstream>
#include <string>
#include <vector>

#include "mobile_base_control/m1_driver.hpp"
#include "mobile_base_control/m1_unicast_read_check.hpp"

using mobile_base_control::ErrorCode;
using mobile_base_control::M1Driver;
using mobile_base_control::Result;
using mobile_base_control::UnicastReadOptions;
using mobile_base_control::parse_unicast_read_args;
using mobile_base_control::run_unicast_read_check;
using mobile_base_control::validate_unicast_read_options;

namespace
{
// Interpose only in this test executable. Exercise the real M1Driver connection
// and transaction paths without opening any serial device or replacing transact().
struct ModbusCapture
{
  int context_token{0};
  bool connected{false};
  bool fail_connect{false};
  size_t timeout_request{0};
  int receive_error{ETIMEDOUT};
  int slave{0};
  std::vector<std::string> events;
  std::vector<std::vector<uint8_t>> requests;
};

ModbusCapture capture;

modbus_t * captured_context()
{
  return reinterpret_cast<modbus_t *>(&capture.context_token);
}

UnicastReadOptions parse_test_args(std::vector<std::string> args)
{
  std::vector<char *> argv;
  for (auto & arg : args) {
    argv.push_back(arg.data());
  }
  return parse_unicast_read_args(static_cast<int>(argv.size()), argv.data());
}

class M1UnicastSequenceTest : public ::testing::Test
{
protected:
  void SetUp() override
  {
    capture = ModbusCapture{};
  }
};
}  // namespace

extern "C"
{
modbus_t * modbus_new_rtu(const char * device, int baud, char parity, int bits, int stop_bits)
{
  EXPECT_STREQ(device, "test-only-serial");
  EXPECT_EQ(baud, 230400);
  EXPECT_EQ(parity, 'N');
  EXPECT_EQ(bits, 8);
  EXPECT_EQ(stop_bits, 1);
  capture.events.push_back("new");
  return captured_context();
}

int modbus_set_response_timeout(modbus_t * ctx, uint32_t sec, uint32_t usec)
{
  EXPECT_EQ(ctx, captured_context());
  EXPECT_EQ(sec, 0u);
  EXPECT_EQ(usec, 50000u);
  capture.events.push_back("timeout");
  return 0;
}

int modbus_connect(modbus_t * ctx)
{
  EXPECT_EQ(ctx, captured_context());
  EXPECT_FALSE(capture.connected);
  capture.events.push_back("connect");
  capture.connected = !capture.fail_connect;
  return capture.fail_connect ? -1 : 0;
}

int modbus_flush(modbus_t * ctx)
{
  EXPECT_EQ(ctx, captured_context());
  EXPECT_TRUE(capture.connected);
  capture.events.push_back("flush");
  return 0;
}

int modbus_set_slave(modbus_t * ctx, int slave)
{
  EXPECT_EQ(ctx, captured_context());
  EXPECT_TRUE(capture.connected);
  capture.slave = slave;
  capture.events.push_back("slave");
  return 0;
}

int modbus_send_raw_request(modbus_t * ctx, const uint8_t * req, int length)
{
  EXPECT_EQ(ctx, captured_context());
  EXPECT_TRUE(capture.connected);
  EXPECT_EQ(length, 6);
  if (length != 6) {
    errno = EINVAL;
    return -1;
  }
  EXPECT_EQ(req[0], capture.slave);
  EXPECT_EQ(req[1], 0x03);
  EXPECT_EQ(req[4], 0x00);
  EXPECT_EQ(req[5], 0x01);
  capture.requests.emplace_back(req, req + length);
  capture.events.push_back("send");
  return length + 2;
}

int modbus_receive_confirmation(modbus_t * ctx, uint8_t * rsp)
{
  EXPECT_EQ(ctx, captured_context());
  EXPECT_TRUE(capture.connected);
  capture.events.push_back("receive");
  if (capture.requests.size() == capture.timeout_request) {
    errno = capture.receive_error;
    return -1;
  }
  const auto & req = capture.requests.back();
  const uint16_t value = req[2] == 0x3D && req[3] == 0x05 ? 2500 : 0;
  // libmodbus has already checked the CRC when it returns a confirmation.
  const std::vector<uint8_t> response = {
    req[0], 0x03, 0x02, static_cast<uint8_t>(value >> 8),
    static_cast<uint8_t>(value & 0xFF), 0, 0};
  std::copy(response.begin(), response.end(), rsp);
  return static_cast<int>(response.size());
}

void modbus_close(modbus_t * ctx)
{
  EXPECT_EQ(ctx, captured_context());
  EXPECT_TRUE(capture.connected);
  capture.connected = false;
  capture.events.push_back("close");
}

void modbus_free(modbus_t * ctx)
{
  EXPECT_EQ(ctx, captured_context());
  EXPECT_FALSE(capture.connected);
  capture.events.push_back("free");
}
}  // extern "C"

TEST(M1UnicastReadCheckTest, ParseCommandLineArguments)
{
  std::vector<std::string> args = {
    "m1_unicast_read_check",
    "--device", "/dev/ttyUSB1",
    "--baud", "115200",
    "--timeout-ms", "100",
    "--driver-id", "2",
    "--register", "0x3D05"
  };
  std::vector<char *> argv;
  for (auto & a : args) {
    argv.push_back(a.data());
  }

  auto opts = parse_unicast_read_args(static_cast<int>(argv.size()), argv.data());
  EXPECT_EQ(opts.device, "/dev/ttyUSB1");
  EXPECT_EQ(opts.baud, 115200);
  EXPECT_EQ(opts.timeout_ms, 100u);
  EXPECT_EQ(opts.driver_id, 2);
  EXPECT_EQ(opts.reg, 0x3D05);
  EXPECT_TRUE(opts.register_specified);

  auto val = validate_unicast_read_options(opts);
  EXPECT_TRUE(val.valid);
}

TEST(M1UnicastReadCheckTest, HelpOptionPrintsUsage)
{
  std::vector<std::string> args = {"m1_unicast_read_check", "--help"};
  std::vector<char *> argv;
  for (auto & a : args) {
    argv.push_back(a.data());
  }

  auto opts = parse_unicast_read_args(static_cast<int>(argv.size()), argv.data());
  EXPECT_TRUE(opts.help);

  M1Driver driver;
  std::ostringstream out;
  std::ostringstream err;
  const int ret = run_unicast_read_check(opts, driver, out, err);
  EXPECT_EQ(ret, 0);
  EXPECT_NE(out.str().find("Usage: m1_unicast_read_check"), std::string::npos);
  EXPECT_TRUE(err.str().empty());
}

TEST(M1UnicastReadCheckTest, ParseDecimalRegister)
{
  std::vector<std::string> args = {
    "m1_unicast_read_check",
    "--driver-id", "1",
    "--register", "15885"  // 0x3E0D
  };
  std::vector<char *> argv;
  for (auto & a : args) {
    argv.push_back(a.data());
  }

  auto opts = parse_unicast_read_args(static_cast<int>(argv.size()), argv.data());
  EXPECT_EQ(opts.reg, 0x3E0D);
  EXPECT_TRUE(opts.register_specified);
}

TEST(M1UnicastReadCheckTest, ValidationRejectsInvalidInputs)
{
  UnicastReadOptions opts;
  opts.register_specified = false;
  EXPECT_FALSE(validate_unicast_read_options(opts).valid);

  opts.register_specified = true;
  opts.driver_id = 0;
  EXPECT_FALSE(validate_unicast_read_options(opts).valid);

  opts.driver_id = 248;
  EXPECT_FALSE(validate_unicast_read_options(opts).valid);

  opts.driver_id = 2;
  opts.device = "";
  EXPECT_FALSE(validate_unicast_read_options(opts).valid);

  opts.device = "/dev/ttyUSB0";
  opts.baud = 0;
  EXPECT_FALSE(validate_unicast_read_options(opts).valid);

  opts.baud = 230400;
  opts.timeout_ms = 0;
  EXPECT_FALSE(validate_unicast_read_options(opts).valid);

  opts.timeout_ms = 50;
  EXPECT_TRUE(validate_unicast_read_options(opts).valid);
}

TEST(M1UnicastReadCheckTest, SuccessfulExecutionPreservesWireFrameAndReportsValue)
{
  M1Driver driver;
  size_t call_count = 0;
  std::vector<std::vector<uint8_t>> captured_requests;

  driver.set_transact_override([&](const std::vector<uint8_t> & req) {
      ++call_count;
      captured_requests.push_back(req);
      // Slave 2, FC 03, 2 bytes, value = 2500 (0x09C4)
      return Result<std::vector<uint8_t>>::success({2, 0x03, 0x02, 0x09, 0xC4});
    });

  UnicastReadOptions opts;
  opts.device = "mock";
  opts.driver_id = 2;
  opts.reg = 0x3D05;
  opts.register_specified = true;

  std::ostringstream out;
  std::ostringstream err;
  const int ret = run_unicast_read_check(opts, driver, out, err);

  EXPECT_EQ(ret, 0);
  EXPECT_EQ(call_count, 1u);  // Requirement 1 & 7: Exactly one request sent, no second transaction
  ASSERT_EQ(captured_requests.size(), 1u);

  const auto & adu = captured_requests[0];
  ASSERT_GE(adu.size(), 6u);
  EXPECT_EQ(adu[0], 2);       // Requirement 2: Requested slave ID preserved
  EXPECT_EQ(adu[1], 0x03);    // Requirement 4: FC03 is used
  EXPECT_EQ(adu[2], 0x3D);    // Requirement 3: Requested register high byte
  EXPECT_EQ(adu[3], 0x05);    // Requirement 3: Requested register low byte
  EXPECT_EQ(adu[4], 0x00);    // 1 register requested
  EXPECT_EQ(adu[5], 0x01);

  // Requirement 6: Success value is reported
  EXPECT_NE(out.str().find("SUCCESS: ID 2 register 0x3D05 = 2500"), std::string::npos);
  EXPECT_TRUE(err.str().empty());
  EXPECT_FALSE(driver.is_connected());  // Disconnected cleanly
}

TEST(M1UnicastReadCheckTest, TimeoutReportedWithoutSecondTransaction)
{
  M1Driver driver;
  size_t call_count = 0;
  std::vector<std::vector<uint8_t>> captured_requests;

  driver.set_transact_override([&](const std::vector<uint8_t> & req) {
      ++call_count;
      captured_requests.push_back(req);
      return Result<std::vector<uint8_t>>::failure(ErrorCode::TIMEOUT);
    });

  UnicastReadOptions opts;
  opts.device = "mock";
  opts.driver_id = 2;
  opts.reg = 0x3D05;
  opts.register_specified = true;

  std::ostringstream out;
  std::ostringstream err;
  const int ret = run_unicast_read_check(opts, driver, out, err);

  EXPECT_NE(ret, 0);
  EXPECT_EQ(call_count, 1u);  // Requirement 1 & 7: Exactly one request, no retry
  ASSERT_EQ(captured_requests.size(), 1u);
  EXPECT_EQ(captured_requests[0][0], 2);
  EXPECT_EQ(captured_requests[0][1], 0x03);
  EXPECT_EQ(captured_requests[0][2], 0x3D);
  EXPECT_EQ(captured_requests[0][3], 0x05);

  EXPECT_NE(err.str().find("TIMEOUT"), std::string::npos);  // Requirement 5: Timeout is reported
  EXPECT_NE(err.str().find("ID 2 register 0x3D05"), std::string::npos);
  EXPECT_TRUE(out.str().empty());
  EXPECT_FALSE(driver.is_connected());
}

TEST(M1UnicastReadCheckTest, Driver1RegisterRead)
{
  M1Driver driver;
  size_t call_count = 0;
  std::vector<std::vector<uint8_t>> captured_requests;

  driver.set_transact_override([&](const std::vector<uint8_t> & req) {
      ++call_count;
      captured_requests.push_back(req);
      // Slave 1, FC 03, 2 bytes, value = 0 (0x0000)
      return Result<std::vector<uint8_t>>::success({1, 0x03, 0x02, 0x00, 0x00});
    });

  UnicastReadOptions opts;
  opts.device = "mock";
  opts.driver_id = 1;
  opts.reg = 0x3E0D;
  opts.register_specified = true;

  std::ostringstream out;
  std::ostringstream err;
  const int ret = run_unicast_read_check(opts, driver, out, err);

  EXPECT_EQ(ret, 0);
  EXPECT_EQ(call_count, 1u);
  ASSERT_EQ(captured_requests.size(), 1u);
  EXPECT_EQ(captured_requests[0][0], 1);
  EXPECT_EQ(captured_requests[0][1], 0x03);
  EXPECT_EQ(captured_requests[0][2], 0x3E);
  EXPECT_EQ(captured_requests[0][3], 0x0D);

  EXPECT_NE(out.str().find("SUCCESS: ID 1 register 0x3E0D = 0"), std::string::npos);
  EXPECT_FALSE(driver.is_connected());
}

namespace
{
struct SequenceCase
{
  std::string name;
  std::vector<std::string> reads;
  std::vector<std::vector<uint8_t>> requests;
};

class OrderedReadTest : public M1UnicastSequenceTest,
  public ::testing::WithParamInterface<SequenceCase> {};
}  // namespace

TEST_P(OrderedReadTest, PreservesEveryRequestOnOneConnection)
{
  const auto & scenario = GetParam();
  std::vector<std::string> args = {
    "m1_unicast_read_check", "--device", "test-only-serial",
    "--baud", "230400", "--timeout-ms", "50"};
  for (const auto & read : scenario.reads) {
    args.insert(args.end(), {"--read", read});
  }
  const auto opts = parse_test_args(args);
  std::ostringstream out;
  std::ostringstream err;
  {
    M1Driver driver;
    EXPECT_EQ(run_unicast_read_check(opts, driver, out, err), 0);
    EXPECT_FALSE(driver.is_connected());
  }
  EXPECT_EQ(capture.requests, scenario.requests);
  std::vector<std::string> events = {"new", "timeout", "connect", "flush"};
  for (size_t i = 0; i < scenario.requests.size(); ++i) {
    events.insert(events.end(), {"slave", "flush", "send", "receive"});
  }
  events.insert(events.end(), {"close", "free"});
  // Includes destruction: one allocation/open/close/free; no reconnect or retry.
  EXPECT_EQ(capture.events, events);
  EXPECT_TRUE(err.str().empty());
}

INSTANTIATE_TEST_SUITE_P(
  DiagnosticMatrix, OrderedReadTest,
  ::testing::Values(
    SequenceCase{"S1", {"1:0x3D05", "2:0x3D05"},
      {{1, 3, 0x3D, 0x05, 0, 1}, {2, 3, 0x3D, 0x05, 0, 1}}},
    SequenceCase{"S2", {"2:0x3D05", "2:0x3E0D"},
      {{2, 3, 0x3D, 0x05, 0, 1}, {2, 3, 0x3E, 0x0D, 0, 1}}},
    SequenceCase{"S3", {"1:0x3D05", "1:0x3E0D", "2:0x3D05"},
      {{1, 3, 0x3D, 0x05, 0, 1}, {1, 3, 0x3E, 0x0D, 0, 1}, {2, 3, 0x3D, 0x05, 0, 1}}},
    SequenceCase{"S4", {"2:0x3D05", "1:0x3D05"},
      {{2, 3, 0x3D, 0x05, 0, 1}, {1, 3, 0x3D, 0x05, 0, 1}}},
    SequenceCase{"S5", {"1:0x3E0D", "2:0x3D05"},
      {{1, 3, 0x3E, 0x0D, 0, 1}, {2, 3, 0x3D, 0x05, 0, 1}}},
    SequenceCase{"RepeatedRead", {"1:15621", "1:15621"},
      {{1, 3, 0x3D, 0x05, 0, 1}, {1, 3, 0x3D, 0x05, 0, 1}}}),
  [](const ::testing::TestParamInfo<SequenceCase> & info) {return info.param.name;});

TEST_F(M1UnicastSequenceTest, ReportsEachValueInOrder)
{
  const auto opts = parse_test_args({
    "m1_unicast_read_check", "--device", "test-only-serial",
    "--read", "1:0x3D05", "--read", "1:0x3E0D", "--read", "2:0x3D05"});
  M1Driver driver;
  std::ostringstream out;
  std::ostringstream err;
  ASSERT_EQ(run_unicast_read_check(opts, driver, out, err), 0);
  const auto first = out.str().find("READ 1: ID 1 register 0x3D05 SUCCESS = 2500");
  const auto second = out.str().find("READ 2: ID 1 register 0x3E0D SUCCESS = 0");
  const auto third = out.str().find("READ 3: ID 2 register 0x3D05 SUCCESS = 2500");
  ASSERT_NE(first, std::string::npos);
  ASSERT_NE(second, std::string::npos);
  ASSERT_NE(third, std::string::npos);
  EXPECT_LT(first, second);
  EXPECT_LT(second, third);
  EXPECT_TRUE(err.str().empty());
}

TEST_F(M1UnicastSequenceTest, StopsAtEachPossibleTimeoutWithoutRetryOrLaterTransmission)
{
  const auto opts = parse_test_args({
    "m1_unicast_read_check", "--device", "test-only-serial",
    "--read", "1:0x3D05", "--read", "1:0x3E0D",
    "--read", "2:0x3D05", "--read", "2:0x3E0D"});
  const std::vector<std::vector<uint8_t>> expected = {
    {1, 3, 0x3D, 0x05, 0, 1}, {1, 3, 0x3E, 0x0D, 0, 1},
    {2, 3, 0x3D, 0x05, 0, 1}, {2, 3, 0x3E, 0x0D, 0, 1}};
  const std::vector<std::string> labels = {
    "READ 1: ID 1 register 0x3D05", "READ 2: ID 1 register 0x3E0D",
    "READ 3: ID 2 register 0x3D05", "READ 4: ID 2 register 0x3E0D"};
  for (size_t failing = 1; failing <= expected.size(); ++failing) {
    SCOPED_TRACE(failing);
    capture = ModbusCapture{};
    capture.timeout_request = failing;
    std::ostringstream out;
    std::ostringstream err;
    {
      M1Driver driver;
      EXPECT_EQ(run_unicast_read_check(opts, driver, out, err), 3);
      EXPECT_FALSE(driver.is_connected());
    }
    EXPECT_EQ(
      capture.requests,
      (std::vector<std::vector<uint8_t>>(expected.begin(), expected.begin() + failing)));
    EXPECT_EQ(std::count(capture.events.begin(), capture.events.end(), "connect"), 1);
    EXPECT_EQ(std::count(capture.events.begin(), capture.events.end(), "close"), 1);
    EXPECT_EQ(std::count(capture.events.begin(), capture.events.end(), "free"), 1);
    EXPECT_EQ(std::count(capture.events.begin(), capture.events.end(), "receive"), failing);
    EXPECT_NE(out.str().find(labels[failing - 1] + " TIMEOUT"), std::string::npos);
    for (size_t i = failing; i < expected.size(); ++i) {
      EXPECT_NE(out.str().find(labels[i] + " NOT EXECUTED"), std::string::npos);
    }
  }
}

TEST_F(M1UnicastSequenceTest, StopsOnNonTimeoutFailure)
{
  capture.timeout_request = 1;
  capture.receive_error = EIO;
  const auto opts = parse_test_args({
    "m1_unicast_read_check", "--device", "test-only-serial",
    "--read", "1:0x3D05", "--read", "2:0x3D05"});
  M1Driver driver;
  std::ostringstream out;
  std::ostringstream err;
  EXPECT_EQ(run_unicast_read_check(opts, driver, out, err), 3);
  EXPECT_EQ(capture.requests.size(), 1u);
  EXPECT_NE(out.str().find("READ 1: ID 1 register 0x3D05 RECEIVE_FAILED"), std::string::npos);
  EXPECT_NE(out.str().find("READ 2: ID 2 register 0x3D05 NOT EXECUTED"), std::string::npos);
  EXPECT_FALSE(driver.is_connected());
}

TEST_F(M1UnicastSequenceTest, ConnectFailureNeverTransmitsOrRetries)
{
  capture.fail_connect = true;
  const auto opts = parse_test_args({
    "m1_unicast_read_check", "--device", "test-only-serial", "--read", "1:0x3D05"});
  M1Driver driver;
  std::ostringstream out;
  std::ostringstream err;
  EXPECT_EQ(run_unicast_read_check(opts, driver, out, err), 2);
  EXPECT_TRUE(capture.requests.empty());
  EXPECT_EQ(capture.events, (std::vector<std::string>{"new", "timeout", "connect", "free"}));
  EXPECT_NE(err.str().find("CONNECT_FAILED"), std::string::npos);
}

TEST_F(M1UnicastSequenceTest, LegacySingleReadRetainsOutputAndOneLifecycle)
{
  const auto opts = parse_test_args({
    "m1_unicast_read_check", "--device", "test-only-serial",
    "--driver-id", "2", "--register", "0x3D05"});
  std::ostringstream out;
  std::ostringstream err;
  {
    M1Driver driver;
    EXPECT_EQ(run_unicast_read_check(opts, driver, out, err), 0);
  }
  EXPECT_EQ(capture.requests, (std::vector<std::vector<uint8_t>>{{2, 3, 0x3D, 0x05, 0, 1}}));
  EXPECT_EQ(
    capture.events, (std::vector<std::string>{
    "new", "timeout", "connect", "flush", "slave", "flush", "send", "receive", "close", "free"}));
  EXPECT_NE(out.str().find("SUCCESS: ID 2 register 0x3D05 = 2500"), std::string::npos);
  EXPECT_TRUE(err.str().empty());
}

TEST_F(M1UnicastSequenceTest, RejectsMixedCliFormsBeforeConnecting)
{
  for (const auto & legacy : std::vector<std::vector<std::string>>{
    {"--driver-id", "1"}, {"--register", "0x3D05"},
    {"--driver-id", "1", "--register", "0x3D05"}})
  {
    std::vector<std::string> args = {
      "m1_unicast_read_check", "--device", "test-only-serial", "--read", "2:0x3D05"};
    args.insert(args.end(), legacy.begin(), legacy.end());
    const auto opts = parse_test_args(args);
    M1Driver driver;
    std::ostringstream out;
    std::ostringstream err;
    EXPECT_EQ(run_unicast_read_check(opts, driver, out, err), 1);
    EXPECT_NE(err.str().find("INVALID_ARGUMENT"), std::string::npos);
  }
  EXPECT_TRUE(capture.events.empty());
}

TEST_F(M1UnicastSequenceTest, RejectsInvalidSequenceEntriesBeforeAnyConnection)
{
  for (const auto & read : {
    "", "1", "1:", ":0x3D05", "1:0x3D05:2", "0:0x3D05", "248:0x3D05",
    "-1:0x3D05", "1:-1", "1:65536", "1:0x10000", "1:0x3D05junk",
    "1junk:0x3D05", "1:99999999999999999999999999"})
  {
    SCOPED_TRACE(read);
    const auto opts = parse_test_args({
      "m1_unicast_read_check", "--device", "test-only-serial",
      "--read", "1:0x3D05", "--read", read});
    M1Driver driver;
    std::ostringstream out;
    std::ostringstream err;
    EXPECT_EQ(run_unicast_read_check(opts, driver, out, err), 1);
    EXPECT_NE(err.str().find("INVALID_ARGUMENT"), std::string::npos);
  }
  EXPECT_TRUE(capture.events.empty());
}

TEST_F(M1UnicastSequenceTest, RejectsMissingReadAndUnknownFlagsBeforeConnecting)
{
  for (const auto & tail : std::vector<std::vector<std::string>>{
    {"--read"}, {"--reads", "2:0x3D05"}, {"--read", "--help"}})
  {
    std::vector<std::string> args = {
      "m1_unicast_read_check", "--device", "test-only-serial", "--read", "1:0x3D05"};
    args.insert(args.end(), tail.begin(), tail.end());
    const auto opts = parse_test_args(args);
    M1Driver driver;
    std::ostringstream out;
    std::ostringstream err;
    EXPECT_EQ(run_unicast_read_check(opts, driver, out, err), 1);
    EXPECT_NE(err.str().find("INVALID_ARGUMENT"), std::string::npos);
  }
  EXPECT_TRUE(capture.events.empty());
}

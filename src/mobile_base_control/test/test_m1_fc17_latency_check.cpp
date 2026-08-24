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
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#include "mobile_base_control/m1_driver.hpp"
#include "mobile_base_control/m1_fc17_latency_check.hpp"

using mobile_base_control::ErrorCode;
using mobile_base_control::Fc17LatencyCheckOptions;
using mobile_base_control::M1Driver;
using mobile_base_control::Result;
using mobile_base_control::parse_fc17_latency_command_line;
using mobile_base_control::run_fc17_latency_check;
using mobile_base_control::validate_fc17_latency_options;

namespace
{

std::vector<uint8_t> make_mock_md2_response(
  uint8_t fc,
  uint16_t d1_status, uint16_t d1_alarm, int16_t d1_rpm,
  uint16_t d2_status, uint16_t d2_alarm, int16_t d2_rpm)
{
  std::vector<uint8_t> rsp = {
    0x65, fc, 0x20,  // Group addr (0x65), FC, byte count = 32
    // Driver 1 (16 bytes)
    static_cast<uint8_t>(d1_status >> 8), static_cast<uint8_t>(d1_status & 0xFF),
    static_cast<uint8_t>(d1_alarm >> 8), static_cast<uint8_t>(d1_alarm & 0xFF),
    static_cast<uint8_t>(static_cast<uint16_t>(d1_rpm) >> 8), static_cast<uint8_t>(d1_rpm & 0xFF),
    0x13, 0x88,  // Bus voltage (50.00 V)
    0x00, 0x00,  // Current (0.00 A)
    0x00, 0x00, 0x00, 0x00,  // Pos
    0x00, 0x00,  // Error check
    // Driver 2 (16 bytes)
    static_cast<uint8_t>(d2_status >> 8), static_cast<uint8_t>(d2_status & 0xFF),
    static_cast<uint8_t>(d2_alarm >> 8), static_cast<uint8_t>(d2_alarm & 0xFF),
    static_cast<uint8_t>(static_cast<uint16_t>(d2_rpm) >> 8), static_cast<uint8_t>(d2_rpm & 0xFF),
    0x13, 0x88,  // Bus voltage
    0x00, 0x00,  // Current
    0x00, 0x00, 0x00, 0x00,  // Pos
    0x00, 0x00   // Error check
  };
  return rsp;
}

}  // namespace

TEST(Fc17LatencyCheckTest, DryRunCausesZeroTransportCalls)
{
  Fc17LatencyCheckOptions opts;
  opts.dry_run = true;
  opts.execute = false;

  M1Driver driver;
  size_t call_count = 0;
  driver.set_transact_override(
    [&call_count](const std::vector<uint8_t> &) -> Result<std::vector<uint8_t>> {
      ++call_count;
      return Result<std::vector<uint8_t>>::failure(ErrorCode::NOT_CONNECTED);
    });

  std::ostringstream out, err;
  int ret = run_fc17_latency_check(opts, driver, out, err);

  EXPECT_EQ(ret, 0);
  EXPECT_EQ(call_count, 0u);
  EXPECT_NE(out.str().find("DRY-RUN"), std::string::npos);
  EXPECT_NE(out.str().find("BOTH MOTOR TARGETS HARD-BOUND TO 0 RPM"), std::string::npos);
}

TEST(Fc17LatencyCheckTest, NonZeroMotionParametersRejectedAtCli)
{
  const char * argv_rpm[] = {"m1_fc17_latency_check", "--rpm", "100"};
  EXPECT_THROW(parse_fc17_latency_command_line(3, const_cast<char **>(argv_rpm)),
    std::invalid_argument);

  const char * argv_vel[] = {"m1_fc17_latency_check", "--velocity", "1.0"};
  EXPECT_THROW(parse_fc17_latency_command_line(3, const_cast<char **>(argv_vel)),
    std::invalid_argument);

  const char * argv_speed[] = {"m1_fc17_latency_check", "--speed", "50"};
  EXPECT_THROW(parse_fc17_latency_command_line(3, const_cast<char **>(argv_speed)),
    std::invalid_argument);

  const char * argv_lin[] = {"m1_fc17_latency_check", "--linear", "0.2"};
  EXPECT_THROW(parse_fc17_latency_command_line(3, const_cast<char **>(argv_lin)),
    std::invalid_argument);

  const char * argv_ang[] = {"m1_fc17_latency_check", "--angular", "0.5"};
  EXPECT_THROW(parse_fc17_latency_command_line(3, const_cast<char **>(argv_ang)),
    std::invalid_argument);
}

TEST(Fc17LatencyCheckTest, BoundedOptionValidation)
{
  Fc17LatencyCheckOptions opts;
  opts.warmup_samples = 101;  // > 100
  auto val = validate_fc17_latency_options(opts);
  EXPECT_FALSE(val.valid);

  opts.warmup_samples = 5;
  opts.measured_samples = 2001;  // > 2000
  val = validate_fc17_latency_options(opts);
  EXPECT_FALSE(val.valid);

  opts.measured_samples = 20;
  opts.driver_a = 1;
  opts.driver_b = 1;  // Same ID
  val = validate_fc17_latency_options(opts);
  EXPECT_FALSE(val.valid);

  opts.driver_b = 2;
  opts.timeout_ms = 0;  // Invalid timeout
  val = validate_fc17_latency_options(opts);
  EXPECT_FALSE(val.valid);
}

TEST(Fc17LatencyCheckTest, ExchangeZeroAlwaysBuildsJg0Payload)
{
  M1Driver driver;
  std::vector<uint8_t> captured_req;

  driver.set_transact_override(
    [&captured_req](const std::vector<uint8_t> & req) -> Result<std::vector<uint8_t>> {
      captured_req = req;
      return Result<std::vector<uint8_t>>::success(
        make_mock_md2_response(0x17, 0, 0, 0, 0, 0, 0));
    });

  auto res = driver.exchange_zero(1, 2);
  ASSERT_TRUE(res.ok);
  ASSERT_GE(captured_req.size(), 19u);

  // Check FC17 format:
  // [0] = 0x65 (Group Addr), [1] = 0x17 (FC17)
  // [2,3] = Read Addr (0xF003), [4,5] = Read Count (0x0010 = 16 words)
  // [6,7] = Write Addr (0xF003), [8,9] = Write Count (0x0004 = 4 words)
  // [10] = Write Byte Count (0x08 = 8 bytes)
  // Driver 1: [11,12] = Command Word (0x0006 for JG), [13,14] = Speed (0x0000 for 0 RPM)
  // Driver 2: [15,16] = Command Word (0x0006 for JG), [17,18] = Speed (0x0000 for 0 RPM)
  EXPECT_EQ(captured_req[0], 0x65);
  EXPECT_EQ(captured_req[1], 0x17);
  EXPECT_EQ(captured_req[2], 0xF0);
  EXPECT_EQ(captured_req[3], 0x03);
  EXPECT_EQ(captured_req[4], 0x00);
  EXPECT_EQ(captured_req[5], 0x10);

  EXPECT_EQ(captured_req[6], 0xF8);
  EXPECT_EQ(captured_req[7], 0x03);
  EXPECT_EQ(captured_req[8], 0x00);
  EXPECT_EQ(captured_req[9], 0x04);
  EXPECT_EQ(captured_req[10], 0x08);

  EXPECT_EQ(captured_req[11], 0x00);
  EXPECT_EQ(captured_req[12], 0x01);  // CMD_JG (0x0001)
  EXPECT_EQ(captured_req[13], 0x00);
  EXPECT_EQ(captured_req[14], 0x00);  // 0 RPM

  EXPECT_EQ(captured_req[15], 0x00);
  EXPECT_EQ(captured_req[16], 0x01);  // CMD_JG (0x0001)
  EXPECT_EQ(captured_req[17], 0x00);
  EXPECT_EQ(captured_req[18], 0x00);  // 0 RPM
}

TEST(Fc17LatencyCheckTest, FullMockMeasurementLifecycle)
{
  Fc17LatencyCheckOptions opts;
  opts.device = "mock";
  opts.execute = true;
  opts.dry_run = false;
  opts.warmup_samples = 2;
  opts.measured_samples = 5;

  M1Driver driver;
  bool is_enabled = false;

  driver.set_transact_override(
    [&is_enabled](const std::vector<uint8_t> & req) -> Result<std::vector<uint8_t>> {
      if (req.size() < 2) {
        return Result<std::vector<uint8_t>>::failure(ErrorCode::BAD_LENGTH);
      }
      uint8_t fc = req[1];
      if (fc == 0x03) {
        uint16_t status = is_enabled ? 0 : 6;
        return Result<std::vector<uint8_t>>::success(
          make_mock_md2_response(0x03, status, 0, 0, status, 0, 0));
      } else if (fc == 0x17) {
        if (req.size() < 13) {
          return Result<std::vector<uint8_t>>::failure(ErrorCode::BAD_LENGTH);
        }
        uint16_t cmd = (req[11] << 8) | req[12];
        if (cmd == 0x0006) {  // CMD_SVON
          is_enabled = true;
          return Result<std::vector<uint8_t>>::success(
            make_mock_md2_response(0x17, 0, 0, 0, 0, 0, 0));
        } else if (cmd == 0x0007) {  // CMD_SVOFF
          is_enabled = false;
          return Result<std::vector<uint8_t>>::success(
            make_mock_md2_response(0x17, 6, 0, 0, 6, 0, 0));
        } else if (cmd == 0x0001) {  // CMD_JG
          return Result<std::vector<uint8_t>>::success(
            make_mock_md2_response(0x17, 0, 0, 0, 0, 0, 0));
        }
      }
      return Result<std::vector<uint8_t>>::failure(ErrorCode::BAD_FUNCTION);
    });

  std::ostringstream out, err;
  int ret = run_fc17_latency_check(opts, driver, out, err);

  EXPECT_EQ(ret, 0);
  EXPECT_NE(out.str().find("FC17 ZERO-SPEED LATENCY MEASUREMENT RESULTS"), std::string::npos);
  EXPECT_NE(out.str().find("Total Samples     : 5"), std::string::npos);
  EXPECT_NE(out.str().find("Successful Samples: 5"), std::string::npos);
}

TEST(Fc17LatencyCheckTest, RawOutputUsesDetailedTimingSchemaAndMarksMockPhasesUnavailable)
{
  Fc17LatencyCheckOptions opts;
  opts.device = "mock";
  opts.execute = true;
  opts.warmup_samples = 0;
  opts.measured_samples = 1;
  opts.raw_output_file = "/tmp/mobile_base_fc17_detailed_timing_test.csv";
  std::remove(opts.raw_output_file.c_str());

  M1Driver driver;
  std::ostringstream out, err;
  ASSERT_EQ(run_fc17_latency_check(opts, driver, out, err), 0) << err.str();

  std::ifstream csv(opts.raw_output_file);
  ASSERT_TRUE(csv.is_open());
  std::string header;
  std::string row;
  ASSERT_TRUE(static_cast<bool>(std::getline(csv, header)));
  ASSERT_TRUE(static_cast<bool>(std::getline(csv, row)));

  EXPECT_EQ(
    header,
    "seq,tx_syscall_us,wait_first_rx_us,rx_duration_us,total_us,ok,error,"
    "driver1_alarm,driver1_rpm,driver2_alarm,driver2_rpm");
  EXPECT_EQ(row.rfind("1,-1.00,-1.00,-1.00,", 0), 0u);

  std::remove(opts.raw_output_file.c_str());
}

TEST(Fc17LatencyCheckTest, NonZeroObservedRpmAbortsAndExecutesCleanup)
{
  Fc17LatencyCheckOptions opts;
  opts.device = "mock";
  opts.execute = true;
  opts.dry_run = false;
  opts.warmup_samples = 0;
  opts.measured_samples = 5;

  M1Driver driver;
  size_t jg_calls = 0;
  bool is_enabled = false;
  bool disable_called = false;

  driver.set_transact_override(
    [&](const std::vector<uint8_t> & req) -> Result<std::vector<uint8_t>> {
      uint8_t fc = req[1];
      if (fc == 0x03) {
        uint16_t status = is_enabled ? 0 : 6;
        return Result<std::vector<uint8_t>>::success(
          make_mock_md2_response(0x03, status, 0, 0, status, 0, 0));
      } else if (fc == 0x17) {
        if (req.size() < 13) {
          return Result<std::vector<uint8_t>>::failure(ErrorCode::BAD_LENGTH);
        }
        uint16_t cmd = (req[11] << 8) | req[12];
        if (cmd == 0x0006) {  // CMD_SVON
          is_enabled = true;
          return Result<std::vector<uint8_t>>::success(
            make_mock_md2_response(0x17, 0, 0, 0, 0, 0, 0));
        } else if (cmd == 0x0007) {  // CMD_SVOFF
          disable_called = true;
          is_enabled = false;
          return Result<std::vector<uint8_t>>::success(
            make_mock_md2_response(0x17, 6, 0, 0, 6, 0, 0));
        } else if (cmd == 0x0001) {  // CMD_JG
          ++jg_calls;
          if (jg_calls >= 2) {
            // Anomaly: unexpected non-zero RPM!
            return Result<std::vector<uint8_t>>::success(
              make_mock_md2_response(0x17, 0, 0, 50, 0, 0, 50));
          }
          return Result<std::vector<uint8_t>>::success(
            make_mock_md2_response(0x17, 0, 0, 0, 0, 0, 0));
        }
      }
      return Result<std::vector<uint8_t>>::failure(ErrorCode::BAD_FUNCTION);
    });

  std::ostringstream out, err;
  int ret = run_fc17_latency_check(opts, driver, out, err);

  EXPECT_EQ(ret, 10);
  EXPECT_TRUE(disable_called);
  EXPECT_NE(err.str().find("PRIMARY MEASUREMENT FAILED"), std::string::npos);
  EXPECT_NE(err.str().find("best-effort cleanup is NOT an independent safety guarantee"),
    std::string::npos);
}

TEST(Fc17LatencyCheckTest, ActiveAlarmAbortsAndExecutesCleanup)
{
  Fc17LatencyCheckOptions opts;
  opts.device = "mock";
  opts.execute = true;
  opts.dry_run = false;
  opts.warmup_samples = 0;
  opts.measured_samples = 5;
  opts.raw_output_file = "/tmp/mobile_base_fc17_abort_timing_test.csv";
  std::remove(opts.raw_output_file.c_str());

  M1Driver driver;
  size_t jg_calls = 0;
  bool is_enabled = false;
  bool disable_called = false;

  driver.set_transact_override(
    [&](const std::vector<uint8_t> & req) -> Result<std::vector<uint8_t>> {
      uint8_t fc = req[1];
      if (fc == 0x03) {
        uint16_t status = is_enabled ? 0 : 6;
        return Result<std::vector<uint8_t>>::success(
          make_mock_md2_response(0x03, status, 0, 0, status, 0, 0));
      } else if (fc == 0x17) {
        if (req.size() < 13) {
          return Result<std::vector<uint8_t>>::failure(ErrorCode::BAD_LENGTH);
        }
        uint16_t cmd = (req[11] << 8) | req[12];
        if (cmd == 0x0006) {  // CMD_SVON
          is_enabled = true;
          return Result<std::vector<uint8_t>>::success(
            make_mock_md2_response(0x17, 0, 0, 0, 0, 0, 0));
        } else if (cmd == 0x0007) {  // CMD_SVOFF
          disable_called = true;
          is_enabled = false;
          return Result<std::vector<uint8_t>>::success(
            make_mock_md2_response(0x17, 6, 0, 0, 6, 0, 0));
        } else if (cmd == 0x0001) {  // CMD_JG
          ++jg_calls;
          if (jg_calls >= 2) {
            // Anomaly: alarm triggered!
            return Result<std::vector<uint8_t>>::success(
              make_mock_md2_response(0x17, 0, 1, 0, 0, 1, 0));
          }
          return Result<std::vector<uint8_t>>::success(
            make_mock_md2_response(0x17, 0, 0, 0, 0, 0, 0));
        }
      }
      return Result<std::vector<uint8_t>>::failure(ErrorCode::BAD_FUNCTION);
    });

  std::ostringstream out, err;
  int ret = run_fc17_latency_check(opts, driver, out, err);

  EXPECT_EQ(ret, 10);
  EXPECT_TRUE(disable_called);
  EXPECT_NE(err.str().find("PRIMARY MEASUREMENT FAILED"), std::string::npos);

  std::ifstream csv(opts.raw_output_file);
  ASSERT_TRUE(csv.is_open());
  std::string header;
  std::string row;
  EXPECT_TRUE(static_cast<bool>(std::getline(csv, header)));
  EXPECT_TRUE(static_cast<bool>(std::getline(csv, row)));
  EXPECT_NE(row.find(",1,0,"), std::string::npos);
  std::remove(opts.raw_output_file.c_str());
}

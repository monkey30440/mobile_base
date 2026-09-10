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

#include <pty.h>
#include <unistd.h>

#include <array>
#include <chrono>
#include <string>
#include <thread>
#include <utility>
#include <vector>

#include "mobile_base_control/m1_driver.hpp"

using mobile_base_control::ErrorCode;
using mobile_base_control::M1Driver;
using mobile_base_control::M1ConfigField;
using mobile_base_control::MotorCommand;
using mobile_base_control::Result;

TEST(M1DriverTest, ErrorCodeStrings)
{
  EXPECT_STREQ(mobile_base_control::error_code_to_string(ErrorCode::NONE), "NONE");
  EXPECT_STREQ(
    mobile_base_control::error_code_to_string(ErrorCode::CONTEXT_CREATE_FAILED),
    "CONTEXT_CREATE_FAILED");
  EXPECT_STREQ(
    mobile_base_control::error_code_to_string(ErrorCode::CONNECT_FAILED), "CONNECT_FAILED");
  EXPECT_STREQ(
    mobile_base_control::error_code_to_string(ErrorCode::ALREADY_CONNECTED), "ALREADY_CONNECTED");
  EXPECT_STREQ(
    mobile_base_control::error_code_to_string(ErrorCode::NOT_CONNECTED), "NOT_CONNECTED");
  EXPECT_STREQ(mobile_base_control::error_code_to_string(ErrorCode::TIMEOUT), "TIMEOUT");
  EXPECT_STREQ(
    mobile_base_control::error_code_to_string(ErrorCode::BAD_FUNCTION), "BAD_FUNCTION");
  EXPECT_STREQ(mobile_base_control::error_code_to_string(ErrorCode::BAD_LENGTH), "BAD_LENGTH");
  EXPECT_STREQ(
    mobile_base_control::error_code_to_string(ErrorCode::INVALID_RESPONSE), "INVALID_RESPONSE");
  EXPECT_STREQ(
    mobile_base_control::error_code_to_string(ErrorCode::MODBUS_EXCEPTION), "MODBUS_EXCEPTION");
  EXPECT_STREQ(
    mobile_base_control::error_code_to_string(ErrorCode::INVALID_ARGUMENT), "INVALID_ARGUMENT");
}

TEST(M1DriverTest, BitmaskCalculation)
{
  auto res1 = mobile_base_control::detail::build_driver_bitmask({1});
  ASSERT_TRUE(res1.ok);
  EXPECT_EQ(res1.value, 0x0001);

  auto res2 = mobile_base_control::detail::build_driver_bitmask({1, 2});
  ASSERT_TRUE(res2.ok);
  EXPECT_EQ(res2.value, 0x0003);

  auto res3 = mobile_base_control::detail::build_driver_bitmask({1, 3, 5});
  ASSERT_TRUE(res3.ok);
  EXPECT_EQ(res3.value, (1 << 0) | (1 << 2) | (1 << 4));

  // Invalid IDs
  EXPECT_FALSE(mobile_base_control::detail::build_driver_bitmask({}).ok);
  EXPECT_FALSE(mobile_base_control::detail::build_driver_bitmask({0}).ok);
  EXPECT_FALSE(mobile_base_control::detail::build_driver_bitmask({9}).ok);
  EXPECT_FALSE(mobile_base_control::detail::build_driver_bitmask({1, 1}).ok);  // duplicate
  EXPECT_FALSE(mobile_base_control::detail::build_driver_bitmask(
      {1, 2, 3, 4, 5, 6, 7, 8, 1}).ok);
}

TEST(M1DriverTest, SignedConversions)
{
  // 16-bit
  EXPECT_EQ(mobile_base_control::detail::decode_s16(0x0000), 0);
  EXPECT_EQ(mobile_base_control::detail::decode_s16(0x0050), 80);
  EXPECT_EQ(mobile_base_control::detail::decode_s16(0xFFB0), -80);
  EXPECT_EQ(mobile_base_control::detail::decode_s16(0x7FFF), 32767);
  EXPECT_EQ(mobile_base_control::detail::decode_s16(0x8000), -32768);
}

TEST(M1DriverTest, Format0PositionDecoding)
{
  using mobile_base_control::detail::decode_format0_position;

  // high = 0x0000, low = 0x0001 -> index = 0, pos = 1
  auto s1 = decode_format0_position(0x0000, 0x0001);
  EXPECT_EQ(s1.index, 0);
  EXPECT_EQ(s1.pos, 1);

  // high = 0xFFFF, low = 9998 -> index = -1, pos = 9998 (not packed signed32 -55538)
  auto s2 = decode_format0_position(0xFFFF, 9998);
  EXPECT_EQ(s2.index, -1);
  EXPECT_EQ(s2.pos, 9998);

  // Normal boundary values
  auto s3 = decode_format0_position(0x0005, 9999);
  EXPECT_EQ(s3.index, 5);
  EXPECT_EQ(s3.pos, 9999);

  auto s4 = decode_format0_position(0x0006, 0);
  EXPECT_EQ(s4.index, 6);
  EXPECT_EQ(s4.pos, 0);

  // Extremes of signed 16-bit Index
  auto s5 = decode_format0_position(0x7FFF, 9999);
  EXPECT_EQ(s5.index, 32767);
  EXPECT_EQ(s5.pos, 9999);

  auto s6 = decode_format0_position(0x8000, 0);
  EXPECT_EQ(s6.index, -32768);
  EXPECT_EQ(s6.pos, 0);
}

TEST(M1DriverTest, BuildFC03Request)
{
  auto req = mobile_base_control::detail::build_fc03_request({1, 2});
  ASSERT_TRUE(req.ok);
  // Expected: Group=0x65, FC=0x03, Addr=0xF003, Count=16 (0x0010)
  std::vector<uint8_t> expected = {0x65, 0x03, 0xF0, 0x03, 0x00, 0x10};
  EXPECT_EQ(req.value, expected);

  // Invalid IDs
  EXPECT_FALSE(mobile_base_control::detail::build_fc03_request({}).ok);
  EXPECT_FALSE(mobile_base_control::detail::build_fc03_request({0, 2}).ok);
}

TEST(M1DriverTest, BuildFC17Request)
{
  std::vector<int> ids = {1, 2};
  std::vector<std::pair<uint16_t, uint16_t>> cmds = {
    {0x0001, 0x0050},   // ID1: JG +80 RPM
    {0x0001, 0xFFB0}    // ID2: JG -80 RPM
  };

  auto req = mobile_base_control::detail::build_fc17_request(ids, cmds);
  ASSERT_TRUE(req.ok);

  // Expected Header: Group=0x65, FC=0x17, ReadAddr=0xF003, ReadCount=16 (0x0010),
  // WriteAddr=0xF803, WriteCount=4 (0x0004), WriteBytes=8 (0x08)
  // Followed by words: 0x0001, 0x0050, 0x0001, 0xFFB0
  std::vector<uint8_t> expected = {
    0x65, 0x17,
    0xF0, 0x03,
    0x00, 0x10,
    0xF8, 0x03,
    0x00, 0x04,
    0x08,
    0x00, 0x01, 0x00, 0x50,
    0x00, 0x01, 0xFF, 0xB0
  };
  EXPECT_EQ(req.value, expected);

  // Mismatch command size
  EXPECT_FALSE(mobile_base_control::detail::build_fc17_request(
      {1, 2}, {{0x0001, 0x0000}}).ok);
}

namespace
{
std::vector<uint8_t> create_dummy_md2_response(
  uint8_t fc,
  uint16_t s1_status, uint16_t s1_alarm, int16_t s1_rpm, int16_t s1_index, uint16_t s1_pos,
  uint16_t s2_status, uint16_t s2_alarm, int16_t s2_rpm, int16_t s2_index, uint16_t s2_pos)
{
  std::vector<uint8_t> rsp;
  rsp.push_back(0x65);
  rsp.push_back(fc);
  rsp.push_back(32);  // 2 drivers * 16 bytes = 32

  auto append_driver = [&](uint16_t st, uint16_t al, int16_t rpm, int16_t index, uint16_t pos) {
      uint16_t u_index = static_cast<uint16_t>(index);
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
      // Word 5: Pos HI (Index)
      rsp.push_back(static_cast<uint8_t>((u_index >> 8) & 0xFF));
      rsp.push_back(static_cast<uint8_t>(u_index & 0xFF));
      // Word 6: Pos LO (Step/Pos)
      rsp.push_back(static_cast<uint8_t>((pos >> 8) & 0xFF));
      rsp.push_back(static_cast<uint8_t>(pos & 0xFF));
      // Word 7: Error Check
      rsp.push_back(0x00);
      rsp.push_back(0x00);
    };

  append_driver(s1_status, s1_alarm, s1_rpm, s1_index, s1_pos);
  append_driver(s2_status, s2_alarm, s2_rpm, s2_index, s2_pos);

  return rsp;
}

uint16_t modbus_crc(const std::vector<uint8_t> & bytes)
{
  uint16_t crc = 0xFFFF;
  for (const uint8_t byte : bytes) {
    crc ^= byte;
    for (int bit = 0; bit < 8; ++bit) {
      crc = (crc & 1) != 0 ? static_cast<uint16_t>((crc >> 1) ^ 0xA001) :
        static_cast<uint16_t>(crc >> 1);
    }
  }
  return crc;
}
}  // namespace

TEST(M1DriverTest, ParseMultiDriveResponse)
{
  // Right: Index=0, Pos=1; Left: Index=-1, Pos=9998
  auto valid_rsp = create_dummy_md2_response(
    0x03, 0, 0, 80, 0, 1, 6, 0, -80, -1, 9998);
  auto parse_res = mobile_base_control::detail::parse_multidrive_response(
    0x03, {1, 2}, valid_rsp.data(), valid_rsp.size());
  ASSERT_TRUE(parse_res.ok);

  const auto & states = parse_res.value.states;
  EXPECT_EQ(states[0].driver_id, 1);
  EXPECT_EQ(states[0].status, 0);
  EXPECT_EQ(states[0].alarm, 0);
  EXPECT_EQ(states[0].actual_rpm, 80);
  EXPECT_EQ(states[0].bus_voltage_raw, 2400);
  EXPECT_EQ(states[0].current_raw, 150);
  EXPECT_EQ(states[0].position_sample.index, 0);
  EXPECT_EQ(states[0].position_sample.pos, 1);

  EXPECT_EQ(states[1].driver_id, 2);
  EXPECT_EQ(states[1].status, 6);
  EXPECT_EQ(states[1].alarm, 0);
  EXPECT_EQ(states[1].actual_rpm, -80);
  EXPECT_EQ(states[1].position_sample.index, -1);
  EXPECT_EQ(states[1].position_sample.pos, 9998);

  // Exception response: [0x65, 0x83, 0x02]
  std::vector<uint8_t> exc_rsp = {0x65, 0x83, 0x02};
  auto exc_res = mobile_base_control::detail::parse_multidrive_response(
    0x03, {1, 2}, exc_rsp.data(), exc_rsp.size());
  EXPECT_FALSE(exc_res.ok);
  EXPECT_EQ(exc_res.error, ErrorCode::MODBUS_EXCEPTION);

  // Wrong FC
  auto bad_fc_res = mobile_base_control::detail::parse_multidrive_response(
    0x17, {1, 2}, valid_rsp.data(), valid_rsp.size());
  EXPECT_FALSE(bad_fc_res.ok);
  EXPECT_EQ(bad_fc_res.error, ErrorCode::BAD_FUNCTION);

  // Wrong Group ID
  auto bad_group_rsp = valid_rsp;
  bad_group_rsp[0] = 0x01;
  auto bad_group_res = mobile_base_control::detail::parse_multidrive_response(
    0x03, {1, 2}, bad_group_rsp.data(), bad_group_rsp.size());
  EXPECT_FALSE(bad_group_res.ok);
  EXPECT_EQ(bad_group_res.error, ErrorCode::INVALID_RESPONSE);

  // Truncated length
  auto trunc_res = mobile_base_control::detail::parse_multidrive_response(
    0x03, {1, 2}, valid_rsp.data(), 20);
  EXPECT_FALSE(trunc_res.ok);
  EXPECT_EQ(trunc_res.error, ErrorCode::BAD_LENGTH);
}

TEST(M1DriverTest, MockTransactOperations)
{
  M1Driver driver;
  EXPECT_FALSE(driver.is_connected());

  // Test read_state: Right index=0 pos=500, Left index=-1 pos=9500
  driver.set_transact_override(
    [](const std::vector<uint8_t> & req) -> Result<std::vector<uint8_t>> {
      EXPECT_EQ(req[0], 0x65);
      EXPECT_EQ(req[1], 0x03);
      return Result<std::vector<uint8_t>>::success(
        create_dummy_md2_response(0x03, 0, 0, 0, 0, 500, 0, 0, 0, -1, 9500));
    });

  auto state_res = driver.read_state(1, 2);
  ASSERT_TRUE(state_res.ok);
  EXPECT_EQ(state_res.value.states[0].position_sample.index, 0);
  EXPECT_EQ(state_res.value.states[0].position_sample.pos, 500);
  EXPECT_EQ(state_res.value.states[1].position_sample.index, -1);
  EXPECT_EQ(state_res.value.states[1].position_sample.pos, 9500);

  // Test enable (SVON)
  driver.set_transact_override(
    [](const std::vector<uint8_t> & req) -> Result<std::vector<uint8_t>> {
      EXPECT_EQ(req[0], 0x65);
      EXPECT_EQ(req[1], 0x17);
      // Command words SVON = 0x0006
      EXPECT_EQ(req[11], 0x00);
      EXPECT_EQ(req[12], 0x06);
      return Result<std::vector<uint8_t>>::success(
        create_dummy_md2_response(0x17, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0));
    });

  auto enable_res = driver.enable(1, 2);
  ASSERT_TRUE(enable_res.ok);

  // Test exchange (JG RPM)
  driver.set_transact_override(
    [](const std::vector<uint8_t> & req) -> Result<std::vector<uint8_t>> {
      EXPECT_EQ(req[0], 0x65);
      EXPECT_EQ(req[1], 0x17);
      // ID1 target: +50 RPM
      EXPECT_EQ(req[11], 0x00);
      EXPECT_EQ(req[12], 0x01);  // CMD_JG
      EXPECT_EQ(req[13], 0x00);
      EXPECT_EQ(req[14], 0x32);  // 50
      // ID2 target: -50 RPM
      EXPECT_EQ(req[15], 0x00);
      EXPECT_EQ(req[16], 0x01);  // CMD_JG
      EXPECT_EQ(req[17], 0xFF);
      EXPECT_EQ(req[18], 0xCE);  // -50
      return Result<std::vector<uint8_t>>::success(
        create_dummy_md2_response(0x17, 7, 0, 50, 0, 1000, 7, 0, -50, -1, 9000));
    });

  MotorCommand cmd1{1, 50};
  MotorCommand cmd2{2, -50};
  auto ex_res = driver.exchange(cmd1, cmd2);
  ASSERT_TRUE(ex_res.ok);
  EXPECT_EQ(ex_res.value.states[0].actual_rpm, 50);
  EXPECT_EQ(ex_res.value.states[1].actual_rpm, -50);

  // Test stop (JG 0)
  driver.set_transact_override(
    [](const std::vector<uint8_t> & req) -> Result<std::vector<uint8_t>> {
      EXPECT_EQ(req[0], 0x65);
      EXPECT_EQ(req[1], 0x17);
      EXPECT_EQ(req[11], 0x00);
      EXPECT_EQ(req[12], 0x01);  // CMD_JG
      EXPECT_EQ(req[13], 0x00);
      EXPECT_EQ(req[14], 0x00);  // 0
      return Result<std::vector<uint8_t>>::success(
        create_dummy_md2_response(0x17, 0, 0, 0, 0, 1050, 0, 0, 0, -1, 8950));
    });

  auto stop_res = driver.stop(1, 2);
  ASSERT_TRUE(stop_res.ok);

  // Test disable (SVOFF)
  driver.set_transact_override(
    [](const std::vector<uint8_t> & req) -> Result<std::vector<uint8_t>> {
      EXPECT_EQ(req[0], 0x65);
      EXPECT_EQ(req[1], 0x17);
      EXPECT_EQ(req[11], 0x00);
      EXPECT_EQ(req[12], 0x07);  // CMD_SVOFF
      return Result<std::vector<uint8_t>>::success(
        create_dummy_md2_response(0x17, 6, 0, 0, 0, 1050, 6, 0, 0, -1, 8950));
    });

  auto dis_res = driver.disable(1, 2);
  ASSERT_TRUE(dis_res.ok);

  // Test read_register
  driver.set_transact_override(
    [](const std::vector<uint8_t> & req) -> Result<std::vector<uint8_t>> {
      EXPECT_EQ(req[0], 1);  // ID 1
      EXPECT_EQ(req[1], 0x03);  // FC03
      EXPECT_EQ(req[2], 0x02);
      EXPECT_EQ(req[3], 0x0D);  // Reg 0x020D (02-14)
      return Result<std::vector<uint8_t>>::success({0x01, 0x03, 0x02, 0x00, 0x01});
    });

  auto reg_res = driver.read_register(1, 0x020D);
  ASSERT_TRUE(reg_res.ok);
  EXPECT_EQ(reg_res.value, 1);

  // Test write_register
  driver.set_transact_override(
    [](const std::vector<uint8_t> & req) -> Result<std::vector<uint8_t>> {
      EXPECT_EQ(req[0], 2);  // ID 2
      EXPECT_EQ(req[1], 0x06);  // FC06
      EXPECT_EQ(req[2], 0x09);
      EXPECT_EQ(req[3], 0x19);  // Reg 0x0919 (09-26)
      EXPECT_EQ(req[4], 0x00);
      EXPECT_EQ(req[5], 0x00);  // Val 0
      return Result<std::vector<uint8_t>>::success({0x02, 0x06, 0x09, 0x19, 0x00, 0x00});
    });

  auto wreg_res = driver.write_register(2, 0x0919, 0);
  ASSERT_TRUE(wreg_res.ok);
}

TEST(M1DriverTest, ReadsM1ConfigurationWithoutInferringFeedbackScale)
{
  M1Driver driver;
  for (int id : {1, 2}) {
    size_t calls = 0;
    driver.set_transact_override(
      [id, &calls](const std::vector<uint8_t> & req) {
        const std::vector<uint8_t> expected = calls++ == 0 ?
        std::vector<uint8_t>{static_cast<uint8_t>(id), 3, 0x3D, 5, 0, 1} :
        std::vector<uint8_t>{static_cast<uint8_t>(id), 3, 0x3E, 0x0D, 0, 1};
        EXPECT_EQ(req, expected);
        return Result<std::vector<uint8_t>>::success(
          {static_cast<uint8_t>(id), 3, 2,
            static_cast<uint8_t>(calls == 1 ? 0x09 : 0),
            static_cast<uint8_t>(calls == 1 ? 0xC4 : 0)});
      });
    const auto config = driver.read_device_config(id);
    ASSERT_TRUE(config.ok);
    EXPECT_EQ(config.value.driver_id, id);
    EXPECT_EQ(config.value.encoder_resolution_pulses_per_rev, 2500);
    EXPECT_EQ(config.value.position_command_format, 0);
    EXPECT_EQ(calls, 2u);
  }
}

TEST(M1DriverTest, ConfigurationReadIdentifiesEncoderRegisterFailure)
{
  M1Driver driver;
  size_t calls = 0;
  std::vector<std::vector<uint8_t>> captured_requests;
  driver.set_transact_override([&](const std::vector<uint8_t> & req) {
      ++calls;
      captured_requests.push_back(req);
      return Result<std::vector<uint8_t>>::failure(ErrorCode::TIMEOUT);
    });

  const auto config = driver.read_device_config(2);
  EXPECT_FALSE(config.ok);
  EXPECT_EQ(config.error, ErrorCode::TIMEOUT);
  EXPECT_EQ(config.failed_driver_id, 2);
  EXPECT_EQ(config.failed_field, M1ConfigField::ENCODER_RESOLUTION);
  EXPECT_EQ(config.failed_register(), 0x3D05);
  EXPECT_STREQ(config.failed_context(), "encoder resolution");
  EXPECT_EQ(calls, 1u);
  ASSERT_EQ(captured_requests.size(), 1u);
  EXPECT_EQ(captured_requests[0], (std::vector<uint8_t>{2, 0x03, 0x3D, 0x05, 0x00, 0x01}));
}

TEST(M1DriverTest, ConfigurationReadIdentifiesFormatRegisterFailure)
{
  M1Driver driver;
  size_t calls = 0;
  std::vector<std::vector<uint8_t>> captured_requests;
  driver.set_transact_override([&](const std::vector<uint8_t> & req) {
      ++calls;
      captured_requests.push_back(req);
      if (calls == 1) {
        return Result<std::vector<uint8_t>>::success({2, 0x03, 0x02, 0x09, 0xC4});
      }
      return Result<std::vector<uint8_t>>::failure(ErrorCode::TIMEOUT);
    });

  const auto config = driver.read_device_config(2);
  EXPECT_FALSE(config.ok);
  EXPECT_EQ(config.error, ErrorCode::TIMEOUT);
  EXPECT_EQ(config.failed_driver_id, 2);
  EXPECT_EQ(config.failed_field, M1ConfigField::POSITION_FORMAT);
  EXPECT_EQ(config.failed_register(), 0x3E0D);
  EXPECT_STREQ(config.failed_context(), "position command format");
  EXPECT_EQ(calls, 2u);
  ASSERT_EQ(captured_requests.size(), 2u);
  EXPECT_EQ(captured_requests[0], (std::vector<uint8_t>{2, 0x03, 0x3D, 0x05, 0x00, 0x01}));
  EXPECT_EQ(captured_requests[1], (std::vector<uint8_t>{2, 0x03, 0x3E, 0x0D, 0x00, 0x01}));
}

TEST(M1DriverTest, ConfigurationReadSuccessPreservesInvariantsAndClearsDiagnosticFields)
{
  M1Driver driver;
  size_t calls = 0;
  std::vector<std::vector<uint8_t>> captured_requests;
  driver.set_transact_override([&](const std::vector<uint8_t> & req) {
      ++calls;
      captured_requests.push_back(req);
      if (calls == 1) {
        return Result<std::vector<uint8_t>>::success({1, 0x03, 0x02, 0x09, 0xC4});
      }
      return Result<std::vector<uint8_t>>::success({1, 0x03, 0x02, 0x00, 0x00});
    });

  const auto config = driver.read_device_config(1);
  ASSERT_TRUE(config.ok);
  EXPECT_EQ(config.error, ErrorCode::NONE);
  EXPECT_EQ(config.value.driver_id, 1);
  EXPECT_EQ(config.value.encoder_resolution_pulses_per_rev, 2500);
  EXPECT_EQ(config.value.position_command_format, 0);
  EXPECT_EQ(config.failed_driver_id, 0);
  EXPECT_EQ(config.failed_field, M1ConfigField::NONE);
  EXPECT_EQ(config.failed_register(), 0);
  EXPECT_STREQ(config.failed_context(), "");
  EXPECT_EQ(calls, 2u);
  ASSERT_EQ(captured_requests.size(), 2u);
  EXPECT_EQ(captured_requests[0], (std::vector<uint8_t>{1, 0x03, 0x3D, 0x05, 0x00, 0x01}));
  EXPECT_EQ(captured_requests[1], (std::vector<uint8_t>{1, 0x03, 0x3E, 0x0D, 0x00, 0x01}));
}

TEST(M1DriverTest, ConfigurationReadPropagatesEitherRegisterFailure)
{
  for (size_t failing_read : {1u, 2u}) {
    for (auto error : {ErrorCode::TIMEOUT, ErrorCode::RECEIVE_FAILED}) {
      M1Driver driver;
      size_t calls = 0;
      driver.set_transact_override(
        [&](const std::vector<uint8_t> &) {
          if (++calls == failing_read) {
            return Result<std::vector<uint8_t>>::failure(error);
          }
          return Result<std::vector<uint8_t>>::success({1, 3, 2, 9, 0xC4});
        });
      const auto config = driver.read_device_config(1);
      EXPECT_FALSE(config.ok);
      EXPECT_EQ(config.error, error);
      EXPECT_EQ(calls, failing_read);
      EXPECT_EQ(config.value.driver_id, 0);  // No partial snapshot escapes.
    }
  }
}

TEST(M1DriverTest, ConfigurationReadRejectsMalformedResponses)
{
  const std::vector<std::vector<uint8_t>> responses{
    {1, 0x83, 2}, {2, 3, 2, 9, 0xC4}, {1, 4, 2, 9, 0xC4},
    {1, 3, 2, 9}, {1, 3, 4, 0, 0, 0, 0}};
  for (const auto & response : responses) {
    M1Driver driver;
    driver.set_transact_override([&](const std::vector<uint8_t> &) {
        return Result<std::vector<uint8_t>>::success(response);
      });
    EXPECT_FALSE(driver.read_device_config(1).ok);
  }
}

TEST(M1DriverTest, ConfigurationReadsPreserveOtherValuesWithoutInventingAScale)
{
  for (uint16_t encoder : {0, 1024, 65535}) {
    M1Driver driver;
    driver.set_transact_override([encoder](const std::vector<uint8_t> & req) {
        const uint16_t value = req[2] == 0x3D ? encoder : 1;
        return Result<std::vector<uint8_t>>::success(
          {req[0], 3, 2, static_cast<uint8_t>(value >> 8), static_cast<uint8_t>(value & 0xFF)});
      });
    const auto config = driver.read_device_config(2);
    ASSERT_TRUE(config.ok);
    EXPECT_EQ(config.value.encoder_resolution_pulses_per_rev, encoder);
    EXPECT_EQ(config.value.position_command_format, 1);
  }
  M1Driver driver;
  driver.set_transact_override([](const std::vector<uint8_t> & req) {
      return Result<std::vector<uint8_t>>::success({req[0], 3, 2, 0, 1});
    });
  const auto config1 = driver.read_device_config(1);
  ASSERT_TRUE(config1.ok);
  EXPECT_EQ(config1.value.position_command_format, 1);
  EXPECT_FALSE(driver.read_device_config(0).ok);
  EXPECT_FALSE(driver.read_device_config(248).ok);
}

TEST(M1DriverTest, NegativeHandling)
{
  M1Driver driver;

  // Timeout injection
  driver.set_transact_override(
    [](const std::vector<uint8_t> &) -> Result<std::vector<uint8_t>> {
      return Result<std::vector<uint8_t>>::failure(ErrorCode::TIMEOUT);
    });
  auto timeout_res = driver.read_state(1, 2);
  EXPECT_FALSE(timeout_res.ok);
  EXPECT_EQ(timeout_res.error, ErrorCode::TIMEOUT);

  // Send failed injection
  driver.set_transact_override(
    [](const std::vector<uint8_t> &) -> Result<std::vector<uint8_t>> {
      return Result<std::vector<uint8_t>>::failure(ErrorCode::SEND_FAILED);
    });
  auto send_fail_res = driver.enable(1, 2);
  EXPECT_FALSE(send_fail_res.ok);
  EXPECT_EQ(send_fail_res.error, ErrorCode::SEND_FAILED);

  // Invalid arguments
  EXPECT_FALSE(driver.read_state(1, 1).ok);
  EXPECT_FALSE(driver.read_state(0, 2).ok);
  EXPECT_FALSE(driver.read_state(1, 9).ok);
  EXPECT_FALSE(driver.read_register(0, 0x0000).ok);
  EXPECT_FALSE(driver.read_register(250, 0x0000).ok);
  EXPECT_FALSE(driver.write_register(0, 0x0000, 0).ok);
}

TEST(M1DriverTest, ConnectFailureHandling)
{
  M1Driver driver;
  // Connecting to a non-existent device path should fail cleanly
  auto res = driver.connect("/dev/non_existent_serial_device_m1", 230400, 50);
  EXPECT_FALSE(res.ok);
  EXPECT_EQ(res.error, ErrorCode::CONNECT_FAILED);
  EXPECT_FALSE(driver.is_connected());
}

TEST(M1DriverTest, DetailedTimingObservesLibmodbusWriteAndFirstReadOnPseudoTty)
{
  int master_fd = -1;
  int slave_fd = -1;
  char slave_name[128]{};
  ASSERT_EQ(openpty(&master_fd, &slave_fd, slave_name, nullptr, nullptr), 0);
  close(slave_fd);

  M1Driver driver;
  ASSERT_TRUE(driver.connect(slave_name, 230400, 100).ok);

  std::thread responder([master_fd]() {
      std::array<uint8_t, 64> request{};
      size_t received = 0;
      while (received < 21) {
        const ssize_t count = ::read(
          master_fd, request.data() + received, request.size() - received);
        ASSERT_GT(count, 0);
        received += static_cast<size_t>(count);
      }
      std::this_thread::sleep_for(std::chrono::milliseconds(2));
      auto response = create_dummy_md2_response(
        0x17, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0);
      const uint16_t crc = modbus_crc(response);
      response.push_back(static_cast<uint8_t>(crc & 0xFF));
      response.push_back(static_cast<uint8_t>(crc >> 8));
      ASSERT_EQ(::write(master_fd, response.data(), response.size()),
        static_cast<ssize_t>(response.size()));
    });

  driver.begin_detailed_timing_capture(1);
  const auto result = driver.exchange_zero(1, 2);
  const auto timings = driver.end_detailed_timing_capture();
  responder.join();
  close(master_fd);

  ASSERT_TRUE(result.ok) << mobile_base_control::error_code_to_string(result.error);
  ASSERT_EQ(timings.size(), 1u);
  EXPECT_GE(timings[0].tx_syscall_us, 0.0);
  EXPECT_GE(timings[0].wait_first_rx_us, 0.0);
  EXPECT_GE(timings[0].rx_duration_us, 0.0);
  EXPECT_GE(timings[0].total_us, timings[0].wait_first_rx_us);
  EXPECT_TRUE(timings[0].transport_ok);
}

TEST(M1DriverTest, DetailedTimingLeavesRxDurationUnavailableAfterPartialResponseTimeout)
{
  int master_fd = -1;
  int slave_fd = -1;
  char slave_name[128]{};
  ASSERT_EQ(openpty(&master_fd, &slave_fd, slave_name, nullptr, nullptr), 0);
  close(slave_fd);

  M1Driver driver;
  ASSERT_TRUE(driver.connect(slave_name, 230400, 20).ok);
  std::thread responder([master_fd]() {
      std::array<uint8_t, 21> request{};
      size_t received = 0;
      while (received < request.size()) {
        const ssize_t count = ::read(
          master_fd, request.data() + received, request.size() - received);
        ASSERT_GT(count, 0);
        received += static_cast<size_t>(count);
      }
      const uint8_t partial_response = 0x65;
      ASSERT_EQ(::write(master_fd, &partial_response, 1), 1);
    });

  driver.begin_detailed_timing_capture(1);
  const auto result = driver.exchange_zero(1, 2);
  const auto timings = driver.end_detailed_timing_capture();
  responder.join();
  close(master_fd);

  EXPECT_FALSE(result.ok);
  ASSERT_EQ(timings.size(), 1u);
  EXPECT_GE(timings[0].wait_first_rx_us, 0.0);
  EXPECT_EQ(timings[0].rx_duration_us, -1.0);
  EXPECT_FALSE(timings[0].transport_ok);
}

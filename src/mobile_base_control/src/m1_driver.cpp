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

#include "mobile_base_control/m1_driver.hpp"

#include <modbus/modbus.h>
#include <modbus/modbus-rtu.h>

#include <cerrno>
#include <cstring>
#include <algorithm>
#include <memory>
#include <string>
#include <utility>
#include <vector>

namespace mobile_base_control
{

namespace
{
constexpr uint8_t GROUP_ID = 0x65;
constexpr uint8_t FC_READ_HOLDING = 0x03;
constexpr uint8_t FC_WRITE_SINGLE = 0x06;
constexpr uint8_t FC_READ_WRITE_MULTIPLE = 0x17;

constexpr uint16_t CMD_JG = 0x0001;
constexpr uint16_t CMD_SVON = 0x0006;
constexpr uint16_t CMD_SVOFF = 0x0007;

constexpr uint16_t MD2_READ_BASE = 0xF000;
constexpr uint16_t MD2_WRITE_BASE = 0xF800;
constexpr size_t MD2_WORDS_PER_DRIVER = 8;
constexpr size_t MD2_BYTES_PER_DRIVER = 16;
}  // namespace

const char * error_code_to_string(ErrorCode code) noexcept
{
  switch (code) {
    case ErrorCode::NONE:
      return "NONE";
    case ErrorCode::CONTEXT_CREATE_FAILED:
      return "CONTEXT_CREATE_FAILED";
    case ErrorCode::CONFIG_FAILED:
      return "CONFIG_FAILED";
    case ErrorCode::CONNECT_FAILED:
      return "CONNECT_FAILED";
    case ErrorCode::ALREADY_CONNECTED:
      return "ALREADY_CONNECTED";
    case ErrorCode::NOT_CONNECTED:
      return "NOT_CONNECTED";
    case ErrorCode::SEND_FAILED:
      return "SEND_FAILED";
    case ErrorCode::TIMEOUT:
      return "TIMEOUT";
    case ErrorCode::RECEIVE_FAILED:
      return "RECEIVE_FAILED";
    case ErrorCode::BAD_FUNCTION:
      return "BAD_FUNCTION";
    case ErrorCode::BAD_LENGTH:
      return "BAD_LENGTH";
    case ErrorCode::INVALID_RESPONSE:
      return "INVALID_RESPONSE";
    case ErrorCode::MODBUS_EXCEPTION:
      return "MODBUS_EXCEPTION";
    case ErrorCode::INVALID_ARGUMENT:
      return "INVALID_ARGUMENT";
    default:
      return "UNKNOWN_ERROR";
  }
}

namespace detail
{

Result<uint16_t> build_driver_bitmask(const std::vector<int> & ids)
{
  if (ids.empty() || ids.size() > 8) {
    return Result<uint16_t>::failure(ErrorCode::INVALID_ARGUMENT);
  }

  uint16_t mask = 0;
  for (const int sid : ids) {
    if (sid < 1 || sid > 8) {
      return Result<uint16_t>::failure(ErrorCode::INVALID_ARGUMENT);
    }
    const uint16_t bit = static_cast<uint16_t>(1 << (sid - 1));
    if ((mask & bit) != 0) {
      // Duplicate ID
      return Result<uint16_t>::failure(ErrorCode::INVALID_ARGUMENT);
    }
    mask |= bit;
  }

  return Result<uint16_t>::success(mask);
}

Result<std::vector<uint8_t>> build_fc03_request(const std::vector<int> & ids)
{
  auto mask_res = build_driver_bitmask(ids);
  if (!mask_res.ok) {
    return Result<std::vector<uint8_t>>::failure(mask_res.error);
  }

  const uint16_t address = MD2_READ_BASE | mask_res.value;
  const uint16_t count = static_cast<uint16_t>(ids.size() * MD2_WORDS_PER_DRIVER);

  std::vector<uint8_t> req(6);
  req[0] = GROUP_ID;
  req[1] = FC_READ_HOLDING;
  req[2] = static_cast<uint8_t>((address >> 8) & 0xFF);
  req[3] = static_cast<uint8_t>(address & 0xFF);
  req[4] = static_cast<uint8_t>((count >> 8) & 0xFF);
  req[5] = static_cast<uint8_t>(count & 0xFF);

  return Result<std::vector<uint8_t>>::success(std::move(req));
}

Result<std::vector<uint8_t>> build_fc17_request(
  const std::vector<int> & ordered_ids,
  const std::vector<std::pair<uint16_t, uint16_t>> & commands)
{
  if (ordered_ids.empty() || ordered_ids.size() != commands.size()) {
    return Result<std::vector<uint8_t>>::failure(ErrorCode::INVALID_ARGUMENT);
  }

  auto mask_res = build_driver_bitmask(ordered_ids);
  if (!mask_res.ok) {
    return Result<std::vector<uint8_t>>::failure(mask_res.error);
  }

  const uint16_t read_address = MD2_READ_BASE | mask_res.value;
  const uint16_t read_count = static_cast<uint16_t>(ordered_ids.size() * MD2_WORDS_PER_DRIVER);
  const uint16_t write_address = MD2_WRITE_BASE | mask_res.value;
  const uint16_t write_count = static_cast<uint16_t>(ordered_ids.size() * 2);
  const uint8_t write_byte_count = static_cast<uint8_t>(ordered_ids.size() * 4);

  const size_t total_pdu_len = 11 + (ordered_ids.size() * 4);
  std::vector<uint8_t> req;
  req.reserve(total_pdu_len);

  req.push_back(GROUP_ID);
  req.push_back(FC_READ_WRITE_MULTIPLE);
  req.push_back(static_cast<uint8_t>((read_address >> 8) & 0xFF));
  req.push_back(static_cast<uint8_t>(read_address & 0xFF));
  req.push_back(static_cast<uint8_t>((read_count >> 8) & 0xFF));
  req.push_back(static_cast<uint8_t>(read_count & 0xFF));
  req.push_back(static_cast<uint8_t>((write_address >> 8) & 0xFF));
  req.push_back(static_cast<uint8_t>(write_address & 0xFF));
  req.push_back(static_cast<uint8_t>((write_count >> 8) & 0xFF));
  req.push_back(static_cast<uint8_t>(write_count & 0xFF));
  req.push_back(write_byte_count);

  for (const auto & cmd_pair : commands) {
    req.push_back(static_cast<uint8_t>((cmd_pair.first >> 8) & 0xFF));
    req.push_back(static_cast<uint8_t>(cmd_pair.first & 0xFF));
    req.push_back(static_cast<uint8_t>((cmd_pair.second >> 8) & 0xFF));
    req.push_back(static_cast<uint8_t>(cmd_pair.second & 0xFF));
  }

  return Result<std::vector<uint8_t>>::success(std::move(req));
}

Result<ExchangeResult> parse_multidrive_response(
  uint8_t expected_fc,
  const std::vector<int> & ordered_ids,
  const uint8_t * rsp_bytes,
  size_t rsp_len)
{
  if (!rsp_bytes || rsp_len < 3) {
    return Result<ExchangeResult>::failure(ErrorCode::BAD_LENGTH);
  }

  if ((rsp_bytes[1] & 0x80) != 0) {
    return Result<ExchangeResult>::failure(ErrorCode::MODBUS_EXCEPTION);
  }

  if (rsp_bytes[0] != GROUP_ID) {
    return Result<ExchangeResult>::failure(ErrorCode::INVALID_RESPONSE);
  }

  if (rsp_bytes[1] != expected_fc) {
    return Result<ExchangeResult>::failure(ErrorCode::BAD_FUNCTION);
  }

  const uint8_t byte_count = rsp_bytes[2];
  const size_t expected_byte_count = ordered_ids.size() * MD2_BYTES_PER_DRIVER;
  if (byte_count != expected_byte_count) {
    return Result<ExchangeResult>::failure(ErrorCode::BAD_LENGTH);
  }

  if (rsp_len < 3 + expected_byte_count) {
    return Result<ExchangeResult>::failure(ErrorCode::BAD_LENGTH);
  }

  ExchangeResult result{};
  const uint8_t * data_ptr = rsp_bytes + 3;

  for (size_t i = 0; i < ordered_ids.size() && i < 2; ++i) {
    const size_t driver_offset = i * MD2_BYTES_PER_DRIVER;
    const uint8_t * d = data_ptr + driver_offset;

    std::array<uint16_t, MD2_WORDS_PER_DRIVER> w{};
    for (size_t j = 0; j < MD2_WORDS_PER_DRIVER; ++j) {
      w[j] = static_cast<uint16_t>((d[2 * j] << 8) | d[2 * j + 1]);
    }

    MotorState state{};
    state.driver_id = ordered_ids[i];
    state.status = w[0];
    state.alarm = w[1];
    state.actual_rpm = decode_s16(w[2]);
    state.bus_voltage_raw = w[3];
    state.current_raw = w[4];
    state.position_steps = decode_s32(w[5], w[6]);
    state.error_check = w[7];

    result.states[i] = state;
  }

  return Result<ExchangeResult>::success(std::move(result));
}

}  // namespace detail

struct M1Driver::Impl
{
  modbus_t * ctx{nullptr};
  TransactFn transact_override;
};

M1Driver::M1Driver()
: impl_(std::make_unique<Impl>())
{
}

M1Driver::~M1Driver()
{
  disconnect();
}

M1Driver::M1Driver(M1Driver && other) noexcept = default;
M1Driver & M1Driver::operator=(M1Driver && other) noexcept = default;

bool M1Driver::is_connected() const noexcept
{
  return impl_ != nullptr && impl_->ctx != nullptr;
}

void M1Driver::set_transact_override(TransactFn fn)
{
  if (impl_) {
    impl_->transact_override = std::move(fn);
  }
}

Result<void> M1Driver::connect(
  const std::string & device,
  int baud,
  uint32_t timeout_ms,
  char parity,
  int data_bits,
  int stop_bits)
{
  if (!impl_) {
    return Result<void>::failure(ErrorCode::CONTEXT_CREATE_FAILED);
  }

  if (impl_->ctx != nullptr) {
    return Result<void>::failure(ErrorCode::ALREADY_CONNECTED);
  }

  modbus_t * ctx = modbus_new_rtu(
    device.c_str(), baud, parity, data_bits, stop_bits);
  if (!ctx) {
    return Result<void>::failure(ErrorCode::CONTEXT_CREATE_FAILED);
  }

  const uint32_t sec = timeout_ms / 1000;
  const uint32_t usec = (timeout_ms % 1000) * 1000;
  if (modbus_set_response_timeout(ctx, sec, usec) == -1) {
    modbus_free(ctx);
    return Result<void>::failure(ErrorCode::CONFIG_FAILED);
  }

  if (modbus_connect(ctx) == -1) {
    modbus_free(ctx);
    return Result<void>::failure(ErrorCode::CONNECT_FAILED);
  }

  impl_->ctx = ctx;
  return Result<void>::success();
}

Result<void> M1Driver::disconnect()
{
  if (impl_ && impl_->ctx != nullptr) {
    modbus_close(impl_->ctx);
    modbus_free(impl_->ctx);
    impl_->ctx = nullptr;
  }
  return Result<void>::success();
}

Result<std::vector<uint8_t>> M1Driver::transact(const std::vector<uint8_t> & request_without_crc)
{
  if (!impl_) {
    return Result<std::vector<uint8_t>>::failure(ErrorCode::NOT_CONNECTED);
  }

  if (impl_->transact_override) {
    return impl_->transact_override(request_without_crc);
  }

  if (impl_->ctx == nullptr) {
    return Result<std::vector<uint8_t>>::failure(ErrorCode::NOT_CONNECTED);
  }

  if (request_without_crc.empty()) {
    return Result<std::vector<uint8_t>>::failure(ErrorCode::INVALID_ARGUMENT);
  }

  // In libmodbus RTU, setting the expected slave ID allows confirmation matching
  modbus_set_slave(impl_->ctx, request_without_crc[0]);
  modbus_flush(impl_->ctx);

  const int send_ret = modbus_send_raw_request(
    impl_->ctx,
    request_without_crc.data(),
    static_cast<int>(request_without_crc.size()));

  if (send_ret == -1) {
    if (errno == ETIMEDOUT) {
      return Result<std::vector<uint8_t>>::failure(ErrorCode::TIMEOUT);
    }
    return Result<std::vector<uint8_t>>::failure(ErrorCode::SEND_FAILED);
  }

  uint8_t rsp[MODBUS_RTU_MAX_ADU_LENGTH];
  const int recv_ret = modbus_receive_confirmation(impl_->ctx, rsp);

  if (recv_ret == -1) {
    if (errno == ETIMEDOUT) {
      return Result<std::vector<uint8_t>>::failure(ErrorCode::TIMEOUT);
    }
    return Result<std::vector<uint8_t>>::failure(ErrorCode::RECEIVE_FAILED);
  }

  return Result<std::vector<uint8_t>>::success(
    std::vector<uint8_t>(rsp, rsp + recv_ret));
}

Result<ExchangeResult> M1Driver::read_state(int driver_a, int driver_b)
{
  if (driver_a == driver_b || driver_a < 1 || driver_a > 8 || driver_b < 1 || driver_b > 8) {
    return Result<ExchangeResult>::failure(ErrorCode::INVALID_ARGUMENT);
  }

  std::vector<int> ids = {std::min(driver_a, driver_b), std::max(driver_a, driver_b)};

  auto req_res = detail::build_fc03_request(ids);
  if (!req_res.ok) {
    return Result<ExchangeResult>::failure(req_res.error);
  }

  auto tx_res = transact(req_res.value);
  if (!tx_res.ok) {
    return Result<ExchangeResult>::failure(tx_res.error);
  }

  return detail::parse_multidrive_response(
    FC_READ_HOLDING, ids, tx_res.value.data(), tx_res.value.size());
}

Result<ExchangeResult> M1Driver::enable(int driver_a, int driver_b)
{
  if (driver_a == driver_b || driver_a < 1 || driver_a > 8 || driver_b < 1 || driver_b > 8) {
    return Result<ExchangeResult>::failure(ErrorCode::INVALID_ARGUMENT);
  }

  std::vector<int> ids = {std::min(driver_a, driver_b), std::max(driver_a, driver_b)};
  std::vector<std::pair<uint16_t, uint16_t>> commands = {
    {CMD_SVON, 0x0000},
    {CMD_SVON, 0x0000}
  };

  auto req_res = detail::build_fc17_request(ids, commands);
  if (!req_res.ok) {
    return Result<ExchangeResult>::failure(req_res.error);
  }

  auto tx_res = transact(req_res.value);
  if (!tx_res.ok) {
    return Result<ExchangeResult>::failure(tx_res.error);
  }

  return detail::parse_multidrive_response(
    FC_READ_WRITE_MULTIPLE, ids, tx_res.value.data(), tx_res.value.size());
}

Result<ExchangeResult> M1Driver::exchange(
  const MotorCommand & command_a,
  const MotorCommand & command_b)
{
  if (command_a.driver_id == command_b.driver_id ||
    command_a.driver_id < 1 || command_a.driver_id > 8 ||
    command_b.driver_id < 1 || command_b.driver_id > 8)
  {
    return Result<ExchangeResult>::failure(ErrorCode::INVALID_ARGUMENT);
  }

  std::vector<int> ids;
  std::vector<std::pair<uint16_t, uint16_t>> commands;

  if (command_a.driver_id < command_b.driver_id) {
    ids = {command_a.driver_id, command_b.driver_id};
    commands = {
      {CMD_JG, static_cast<uint16_t>(command_a.target_rpm)},
      {CMD_JG, static_cast<uint16_t>(command_b.target_rpm)}
    };
  } else {
    ids = {command_b.driver_id, command_a.driver_id};
    commands = {
      {CMD_JG, static_cast<uint16_t>(command_b.target_rpm)},
      {CMD_JG, static_cast<uint16_t>(command_a.target_rpm)}
    };
  }

  auto req_res = detail::build_fc17_request(ids, commands);
  if (!req_res.ok) {
    return Result<ExchangeResult>::failure(req_res.error);
  }

  auto tx_res = transact(req_res.value);
  if (!tx_res.ok) {
    return Result<ExchangeResult>::failure(tx_res.error);
  }

  return detail::parse_multidrive_response(
    FC_READ_WRITE_MULTIPLE, ids, tx_res.value.data(), tx_res.value.size());
}

Result<ExchangeResult> M1Driver::stop(int driver_a, int driver_b)
{
  if (driver_a == driver_b || driver_a < 1 || driver_a > 8 || driver_b < 1 || driver_b > 8) {
    return Result<ExchangeResult>::failure(ErrorCode::INVALID_ARGUMENT);
  }

  std::vector<int> ids = {std::min(driver_a, driver_b), std::max(driver_a, driver_b)};
  std::vector<std::pair<uint16_t, uint16_t>> commands = {
    {CMD_JG, 0x0000},
    {CMD_JG, 0x0000}
  };

  auto req_res = detail::build_fc17_request(ids, commands);
  if (!req_res.ok) {
    return Result<ExchangeResult>::failure(req_res.error);
  }

  auto tx_res = transact(req_res.value);
  if (!tx_res.ok) {
    return Result<ExchangeResult>::failure(tx_res.error);
  }

  return detail::parse_multidrive_response(
    FC_READ_WRITE_MULTIPLE, ids, tx_res.value.data(), tx_res.value.size());
}

Result<ExchangeResult> M1Driver::disable(int driver_a, int driver_b)
{
  if (driver_a == driver_b || driver_a < 1 || driver_a > 8 || driver_b < 1 || driver_b > 8) {
    return Result<ExchangeResult>::failure(ErrorCode::INVALID_ARGUMENT);
  }

  std::vector<int> ids = {std::min(driver_a, driver_b), std::max(driver_a, driver_b)};
  std::vector<std::pair<uint16_t, uint16_t>> commands = {
    {CMD_SVOFF, 0x0000},
    {CMD_SVOFF, 0x0000}
  };

  auto req_res = detail::build_fc17_request(ids, commands);
  if (!req_res.ok) {
    return Result<ExchangeResult>::failure(req_res.error);
  }

  auto tx_res = transact(req_res.value);
  if (!tx_res.ok) {
    return Result<ExchangeResult>::failure(tx_res.error);
  }

  return detail::parse_multidrive_response(
    FC_READ_WRITE_MULTIPLE, ids, tx_res.value.data(), tx_res.value.size());
}

Result<uint16_t> M1Driver::read_register(int driver_id, uint16_t address)
{
  if (driver_id < 1 || driver_id > 247) {
    return Result<uint16_t>::failure(ErrorCode::INVALID_ARGUMENT);
  }

  std::vector<uint8_t> req(6);
  req[0] = static_cast<uint8_t>(driver_id);
  req[1] = FC_READ_HOLDING;
  req[2] = static_cast<uint8_t>((address >> 8) & 0xFF);
  req[3] = static_cast<uint8_t>(address & 0xFF);
  req[4] = 0x00;
  req[5] = 0x01;  // read 1 word

  auto tx_res = transact(req);
  if (!tx_res.ok) {
    return Result<uint16_t>::failure(tx_res.error);
  }

  const auto & rsp = tx_res.value;
  if (rsp.size() < 3) {
    return Result<uint16_t>::failure(ErrorCode::BAD_LENGTH);
  }

  if ((rsp[1] & 0x80) != 0) {
    return Result<uint16_t>::failure(ErrorCode::MODBUS_EXCEPTION);
  }

  if (rsp[0] != static_cast<uint8_t>(driver_id)) {
    return Result<uint16_t>::failure(ErrorCode::INVALID_RESPONSE);
  }

  if (rsp[1] != FC_READ_HOLDING) {
    return Result<uint16_t>::failure(ErrorCode::BAD_FUNCTION);
  }

  if (rsp[2] != 2 || rsp.size() < 5) {
    return Result<uint16_t>::failure(ErrorCode::BAD_LENGTH);
  }

  const uint16_t val = static_cast<uint16_t>((rsp[3] << 8) | rsp[4]);
  return Result<uint16_t>::success(val);
}

Result<void> M1Driver::write_register(int driver_id, uint16_t address, uint16_t value)
{
  if (driver_id < 1 || driver_id > 247) {
    return Result<void>::failure(ErrorCode::INVALID_ARGUMENT);
  }

  std::vector<uint8_t> req(6);
  req[0] = static_cast<uint8_t>(driver_id);
  req[1] = FC_WRITE_SINGLE;
  req[2] = static_cast<uint8_t>((address >> 8) & 0xFF);
  req[3] = static_cast<uint8_t>(address & 0xFF);
  req[4] = static_cast<uint8_t>((value >> 8) & 0xFF);
  req[5] = static_cast<uint8_t>(value & 0xFF);

  auto tx_res = transact(req);
  if (!tx_res.ok) {
    return Result<void>::failure(tx_res.error);
  }

  const auto & rsp = tx_res.value;
  if (rsp.size() < 6) {
    return Result<void>::failure(ErrorCode::BAD_LENGTH);
  }

  if ((rsp[1] & 0x80) != 0) {
    return Result<void>::failure(ErrorCode::MODBUS_EXCEPTION);
  }

  if (rsp[0] != static_cast<uint8_t>(driver_id)) {
    return Result<void>::failure(ErrorCode::INVALID_RESPONSE);
  }

  if (rsp[1] != FC_WRITE_SINGLE) {
    return Result<void>::failure(ErrorCode::BAD_FUNCTION);
  }

  return Result<void>::success();
}

}  // namespace mobile_base_control

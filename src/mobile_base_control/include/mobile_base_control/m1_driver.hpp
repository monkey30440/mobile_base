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

#ifndef MOBILE_BASE_CONTROL__M1_DRIVER_HPP_
#define MOBILE_BASE_CONTROL__M1_DRIVER_HPP_

#include <array>
#include <cstdint>
#include <functional>
#include <memory>
#include <string>
#include <utility>
#include <vector>

namespace mobile_base_control
{

enum class ErrorCode
{
  NONE = 0,

  CONTEXT_CREATE_FAILED,
  CONFIG_FAILED,
  CONNECT_FAILED,
  ALREADY_CONNECTED,

  NOT_CONNECTED,
  SEND_FAILED,
  TIMEOUT,
  RECEIVE_FAILED,

  BAD_FUNCTION,
  BAD_LENGTH,
  INVALID_RESPONSE,
  MODBUS_EXCEPTION,
  INVALID_ARGUMENT,
};

const char * error_code_to_string(ErrorCode code) noexcept;

template<typename T>
struct Result
{
  bool ok{false};
  ErrorCode error{ErrorCode::NONE};
  T value{};

  static Result<T> success(T val = T{})
  {
    return Result<T>{true, ErrorCode::NONE, std::move(val)};
  }

  static Result<T> failure(ErrorCode err)
  {
    return Result<T>{false, err, T{}};
  }
};

template<>
struct Result<void>
{
  bool ok{false};
  ErrorCode error{ErrorCode::NONE};

  static Result<void> success()
  {
    return Result<void>{true, ErrorCode::NONE};
  }

  static Result<void> failure(ErrorCode err)
  {
    return Result<void>{false, err};
  }
};

struct MotorCommand
{
  int driver_id{0};
  int16_t target_rpm{0};
};

struct MotorState
{
  int driver_id{0};
  int16_t actual_rpm{0};
  int32_t position_steps{0};
  uint16_t status{0};
  uint16_t alarm{0};
  uint16_t bus_voltage_raw{0};  // unit: 0.01 V
  uint16_t current_raw{0};      // unit: 0.01 A
  uint16_t error_check{0};
};

struct ExchangeResult
{
  std::array<MotorState, 2> states{};
};

enum class DriveId : int
{
  Right = 1,
  Left = 2
};

namespace detail
{
inline int16_t decode_s16(uint16_t val) noexcept
{
  return static_cast<int16_t>(val);
}

inline int32_t decode_s32(uint16_t hi, uint16_t lo) noexcept
{
  const uint32_t u = (static_cast<uint32_t>(hi) << 16) | static_cast<uint32_t>(lo);
  return static_cast<int32_t>(u);
}

Result<uint16_t> build_driver_bitmask(const std::vector<int> & ids);
Result<std::vector<uint8_t>> build_fc03_request(const std::vector<int> & ids);
Result<std::vector<uint8_t>> build_fc17_request(
  const std::vector<int> & ordered_ids,
  const std::vector<std::pair<uint16_t, uint16_t>> & commands);
Result<ExchangeResult> parse_multidrive_response(
  uint8_t expected_fc,
  const std::vector<int> & ordered_ids,
  const uint8_t * rsp_bytes,
  size_t rsp_len);
}  // namespace detail

using TransactFn = std::function<Result<std::vector<uint8_t>>(const std::vector<uint8_t> &)>;

class M1Driver
{
public:
  M1Driver();
  virtual ~M1Driver();

  M1Driver(const M1Driver &) = delete;
  M1Driver & operator=(const M1Driver &) = delete;
  M1Driver(M1Driver && other) noexcept;
  M1Driver & operator=(M1Driver && other) noexcept;

  bool is_connected() const noexcept;

  Result<void> connect(
    const std::string & device,
    int baud,
    uint32_t timeout_ms,
    char parity = 'N',
    int data_bits = 8,
    int stop_bits = 1);

  Result<void> disconnect();

  Result<ExchangeResult> read_state(
    int driver_a = static_cast<int>(DriveId::Right),
    int driver_b = static_cast<int>(DriveId::Left));

  Result<ExchangeResult> enable(
    int driver_a = static_cast<int>(DriveId::Right),
    int driver_b = static_cast<int>(DriveId::Left));

  Result<ExchangeResult> exchange(
    const MotorCommand & command_a,
    const MotorCommand & command_b);

  Result<ExchangeResult> stop(
    int driver_a = static_cast<int>(DriveId::Right),
    int driver_b = static_cast<int>(DriveId::Left));

  Result<ExchangeResult> disable(
    int driver_a = static_cast<int>(DriveId::Right),
    int driver_b = static_cast<int>(DriveId::Left));

  // Single-register Standard Modbus operations (for configuration & diagnostic)
  Result<uint16_t> read_register(
    int driver_id,
    uint16_t address);

  Result<void> write_register(
    int driver_id,
    uint16_t address,
    uint16_t value);

  // Hook for testing without physical hardware
  void set_transact_override(TransactFn fn);

protected:
  virtual Result<std::vector<uint8_t>> transact(const std::vector<uint8_t> & request_without_crc);

private:
  struct Impl;
  std::unique_ptr<Impl> impl_;
};

}  // namespace mobile_base_control

#endif  // MOBILE_BASE_CONTROL__M1_DRIVER_HPP_

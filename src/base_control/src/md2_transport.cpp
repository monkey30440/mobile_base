#include "base_control/md2_transport.hpp"

#include <modbus/modbus.h>

#include <array>
#include <cerrno>
#include <chrono>
#include <cstring>
#include <string>

namespace base_control
{

namespace
{

std::string modbus_error(const std::string & context)
{
  return context + "：" + modbus_strerror(errno);
}

int16_t to_s16(uint16_t value)
{
  return static_cast<int16_t>(value);
}

}  // namespace

Md2Transport::~Md2Transport()
{
  close();
}

void Md2Transport::open(
  const std::string & port, int baud, char parity,
  int data_bits, int stop_bits, double response_timeout_s)
{
  if (ctx_ != nullptr) {
    throw Md2Error("序列埠已開啟，請先 close()");
  }

  ctx_ = modbus_new_rtu(port.c_str(), baud, parity, data_bits, stop_bits);
  if (ctx_ == nullptr) {
    throw Md2Error(modbus_error("建立 Modbus RTU context 失敗"));
  }

  if (modbus_connect(ctx_) == -1) {
    const std::string message = modbus_error("開啟序列埠 " + port + " 失敗");
    modbus_free(ctx_);
    ctx_ = nullptr;
    throw Md2Error(message);
  }

  const auto seconds = static_cast<uint32_t>(response_timeout_s);
  const auto micros =
    static_cast<uint32_t>((response_timeout_s - static_cast<double>(seconds)) * 1e6);
  modbus_set_response_timeout(ctx_, seconds, micros);
}

void Md2Transport::close()
{
  if (ctx_ == nullptr) {
    return;
  }
  modbus_close(ctx_);
  modbus_free(ctx_);
  ctx_ = nullptr;
}

void Md2Transport::drain()
{
  if (ctx_ != nullptr) {
    modbus_flush(ctx_);
  }
}

void Md2Transport::ensure_open() const
{
  if (ctx_ == nullptr) {
    throw Md2Error("序列埠尚未開啟");
  }
}

uint16_t Md2Transport::read_register(int driver_id, int address)
{
  ensure_open();
  if (modbus_set_slave(ctx_, driver_id) == -1) {
    throw Md2Error(modbus_error("設定 Driver ID " + std::to_string(driver_id) + " 失敗"));
  }

  uint16_t value = 0;
  if (modbus_read_registers(ctx_, address, 1, &value) == -1) {
    throw Md2Error(
      modbus_error(
        "讀取 Driver " + std::to_string(driver_id) +
        " 暫存器 0x" + std::to_string(address) + " 失敗"));
  }
  return value;
}

void Md2Transport::write_register(int driver_id, int address, uint16_t value)
{
  ensure_open();
  if (modbus_set_slave(ctx_, driver_id) == -1) {
    throw Md2Error(modbus_error("設定 Driver ID " + std::to_string(driver_id) + " 失敗"));
  }

  if (modbus_write_register(ctx_, address, value) == -1) {
    throw Md2Error(
      modbus_error(
        "寫入 Driver " + std::to_string(driver_id) +
        " 暫存器 0x" + std::to_string(address) + " 失敗"));
  }
}

Md2Feedback Md2Transport::read_write(
  uint16_t right_cmd, int16_t right_rpm,
  uint16_t left_cmd, int16_t left_rpm)
{
  ensure_open();
  if (modbus_set_slave(ctx_, kMd2GroupId) == -1) {
    throw Md2Error(modbus_error("設定群組位址失敗"));
  }

  // driver-major：[ID1_cmd][ID1_rpm][ID2_cmd][ID2_rpm]
  const std::array<uint16_t, kWriteCount> write_data{
    right_cmd,
    static_cast<uint16_t>(right_rpm),
    left_cmd,
    static_cast<uint16_t>(left_rpm),
  };
  std::array<uint16_t, kReadCount> read_data{};

  const auto start = std::chrono::steady_clock::now();
  const int rc = modbus_write_and_read_registers(
    ctx_,
    kWriteAddr, kWriteCount, write_data.data(),
    kReadAddr, kReadCount, read_data.data());
  const auto elapsed = std::chrono::steady_clock::now() - start;

  if (rc == -1) {
    throw Md2Error(modbus_error("FC17h 交易失敗"));
  }

  Md2Feedback feedback;
  feedback.comm_s = std::chrono::duration<double>(elapsed).count();

  const auto extract = [&read_data](int slot) {
      const int base = slot * kItemsPerDriver;
      DriverRaw raw;
      raw.status = read_data[base + kIdxStatus];
      raw.alarm = read_data[base + kIdxAlarm];
      raw.rpm = to_s16(read_data[base + kIdxRpm]);
      raw.pos_turns = to_s16(read_data[base + kIdxPosTurns]);
      raw.pos_pulse = read_data[base + kIdxPosPulse];
      return raw;
    };

  feedback.right = extract(0);
  feedback.left = extract(1);
  return feedback;
}

}  // namespace base_control

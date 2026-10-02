#pragma once
#include <cmath>
#include <array>
#include <vector>
#include <cstdint>
#include <stdexcept>
#include <string>
namespace mobile_base_m1 {
struct Scale { double motor_revolutions_per_wheel; double direction; double feedback_rpm_per_count; };
inline void validate(const Scale &s) {
 if (!std::isfinite(s.motor_revolutions_per_wheel) || s.motor_revolutions_per_wheel <= 0 ||
     (s.direction != 1 && s.direction != -1) || !std::isfinite(s.feedback_rpm_per_count) || s.feedback_rpm_per_count <= 0)
   throw std::invalid_argument("invalid configured wheel scale");
}
inline int16_t command_rpm(double wheel_radians_per_second, const Scale &s) {
 validate(s);
 const auto rpm = wheel_radians_per_second * 60 / (2 * std::acos(-1)) * s.motor_revolutions_per_wheel * s.direction;
 if (!std::isfinite(rpm) || std::abs(rpm) > 32767) throw std::invalid_argument("command outside signed RPM range");
 if (rpm != 0 && std::abs(rpm) < 60) throw std::invalid_argument("M1 JG clamps nonzero speed below 60 RPM; request rejected");
 return static_cast<int16_t>(std::lround(rpm));
}
inline double feedback_velocity(uint16_t raw, const Scale &s) {
 validate(s);
 const auto rpm = raw > 32767 ? static_cast<int32_t>(raw) - 65536 : raw;
 return rpm * s.feedback_rpm_per_count * (2 * std::acos(-1)) / 60 / s.motor_revolutions_per_wheel * s.direction;
}
inline double checked_feedback(uint16_t status, uint16_t alarm, uint16_t raw, const Scale &s) {
 if (alarm != 0 || (status != 0 && status != 2 && status != 6)) throw std::runtime_error("drive not ready: status=" + std::to_string(status) + " alarm=" + std::to_string(alarm));
 return feedback_velocity(raw, s);
}
// Observed on the user-authorized target: each Error_Check is the Modbus
// CRC16 of the cumulative response prefix, encoded as a big-endian register.
// The standard final frame CRC remains libmodbus's transport responsibility.
inline uint16_t prefix_crc(const std::vector<uint8_t> &data) {
 uint16_t value=0xffff;
 for(auto byte:data) {
  value ^= byte;
  for(int bit=0;bit<8;++bit) value=(value>>1)^((value&1)?0xa001:0);
 }
 return value;
}
inline void validate_error_checks(const std::array<uint16_t,8> &words) {
 std::vector<uint8_t> prefix{0x65,0x03,0x10};
 for(size_t i=0;i<words.size();++i) {
  if((i==3 || i==7) && words[i]!=prefix_crc(prefix))
   throw std::runtime_error("per-drive Error_Check prefix CRC mismatch at drive slot " + std::to_string(i/4));
  prefix.push_back(static_cast<uint8_t>(words[i]>>8));
  prefix.push_back(static_cast<uint8_t>(words[i]&0xff));
 }
}
}

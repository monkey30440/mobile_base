#pragma once
#include <cmath>
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
 if (alarm != 0 || (status != 0 && status != 2)) throw std::runtime_error("drive not ready: status=" + std::to_string(status) + " alarm=" + std::to_string(alarm));
 return feedback_velocity(raw, s);
}
}

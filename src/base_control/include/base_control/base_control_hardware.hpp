// SUB-001 Base Control — ros2_control hardware_interface 插件。
//
// 向 controller_manager 匯出左右輪之輪端 state / command interfaces，
// 內部完成馬達端與輪端之換算及方向修正。
//
// 規格見 docs/05_subsystem.md § SUB-001 Base Control。

#ifndef BASE_CONTROL__BASE_CONTROL_HARDWARE_HPP_
#define BASE_CONTROL__BASE_CONTROL_HARDWARE_HPP_

#include <memory>
#include <string>

#include "diagnostic_msgs/msg/diagnostic_array.hpp"
#include "hardware_interface/system_interface.hpp"
#include "hardware_interface/types/hardware_component_interface_params.hpp"
#include "hardware_interface/types/hardware_interface_return_values.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_lifecycle/state.hpp"

#include "base_control/driver_interface.hpp"
#include "base_control/md2_transport.hpp"

namespace base_control
{

class BaseControlHardware : public hardware_interface::SystemInterface
{
public:
  using CallbackReturn = hardware_interface::CallbackReturn;

  CallbackReturn on_init(
    const hardware_interface::HardwareComponentInterfaceParams & params) override;
  CallbackReturn on_configure(const rclcpp_lifecycle::State & previous_state) override;
  CallbackReturn on_activate(const rclcpp_lifecycle::State & previous_state) override;
  CallbackReturn on_deactivate(const rclcpp_lifecycle::State & previous_state) override;
  CallbackReturn on_cleanup(const rclcpp_lifecycle::State & previous_state) override;
  CallbackReturn on_shutdown(const rclcpp_lifecycle::State & previous_state) override;

  hardware_interface::return_type read(
    const rclcpp::Time & time, const rclcpp::Duration & period) override;
  hardware_interface::return_type write(
    const rclcpp::Time & time, const rclcpp::Duration & period) override;

private:
  struct Params
  {
    std::string serial_port = "/dev/ttyUSB0";
    int serial_baud = 230400;
    double serial_timeout_s = 0.1;
    int right_driver_id = 1;
    int left_driver_id = 2;
    double gear_ratio = 20.0;
    int max_motor_rpm = 4000;
    int min_effective_motor_rpm = 60;
    int right_motor_sign = -1;
    int left_motor_sign = 1;
    int right_feedback_sign = -1;
    int left_feedback_sign = 1;
    uint16_t linear_acc_ms = 100;
    uint16_t linear_dec_ms = 100;
    uint16_t s_curve_acc_ms = 1;
    uint16_t s_curve_dec_ms = 1;
    double diagnostics_period_s = 0.2;
  };

  bool load_params();
  bool resolve_joints();
  void publish_diagnostics(const rclcpp::Time & time);

  /// 輪端 rad/s → 馬達端 RPM，含方向修正、上限等比縮放與最小有效轉速。
  void to_motor_rpm(
    double left_wheel_rad_s, double right_wheel_rad_s,
    int16_t & left_motor_rpm, int16_t & right_motor_rpm) const;

  Params params_;
  std::string left_joint_;
  std::string right_joint_;

  Md2Transport transport_;
  std::unique_ptr<DriverInterface> driver_;

  double counts_per_wheel_rev_ = 0.0;
  DualFeedback feedback_;
  bool feedback_valid_ = false;
  int consecutive_faults_ = 0;

  rclcpp::Publisher<diagnostic_msgs::msg::DiagnosticArray>::SharedPtr diagnostics_pub_;
  rclcpp::Time last_diagnostics_time_;
};

}  // namespace base_control

#endif  // BASE_CONTROL__BASE_CONTROL_HARDWARE_HPP_

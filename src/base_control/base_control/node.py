"""SUB-001 Base Control ROS 2 節點。

訂閱 `/cmd_vel`，以差速運動學換算後透過 Multi-drive 2.0 控制左右輪驅動器，
並發布 `/wheel_states`（輪端回授）與 `/driver/status`（驅動器診斷）。

不負責 Wheel Odometry 計算，由 SUB-004 訂閱 `/wheel_states` 完成。
"""

from __future__ import annotations

import sys

import rclpy
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from geometry_msgs.msg import Twist
from rclpy.node import Node
from sensor_msgs.msg import JointState

from .driver_interface import DriverConfigError, DriverInterface
from .kinematics import DifferentialKinematics
from .md2_transport import Md2Error, Md2Transport
from .params import declare_parameters, load_parameters

# 連續通訊失敗達此次數即進入故障狀態並停止送出運動命令
_MAX_CONSECUTIVE_FAULTS = 5


class BaseControlNode(Node):

    def __init__(self) -> None:
        super().__init__('base_control_node')

        declare_parameters(self)
        self._params = load_parameters(self)

        self._transport: Md2Transport | None = None
        self._driver: DriverInterface | None = None
        self._kinematics: DifferentialKinematics | None = None

        self._target_linear = 0.0
        self._target_angular = 0.0
        self._last_cmd_time = self.get_clock().now()
        self._consecutive_faults = 0
        self._faulted = False

        self._joint_pub = self.create_publisher(JointState, 'wheel_states', 10)
        self._diag_pub = self.create_publisher(DiagnosticArray, 'driver/status', 10)
        self._cmd_sub = self.create_subscription(
            Twist, 'cmd_vel', self._on_cmd_vel, 10
        )

        self._connect()

        self._timer = self.create_timer(
            self._params.control.loop_period_s, self._on_timer
        )
        self.get_logger().info(
            f'base_control 啟動，控制週期 {self._params.control.loop_period_s * 1000:.0f} ms'
        )

    # ── 啟動 ─────────────────────────────────────────────────────────────────

    def _connect(self) -> None:
        serial_params = self._params.serial
        driver_params = self._params.driver

        self._transport = Md2Transport(
            port=serial_params.port,
            baud=serial_params.baud,
            timeout_s=serial_params.timeout_s,
            bytesize=serial_params.bytesize,
            parity=serial_params.parity,
            stopbits=serial_params.stopbits,
        )
        self._driver = DriverInterface(
            self._transport,
            right_id=driver_params.right_id,
            left_id=driver_params.left_id,
        )

        counts_per_motor_rev = self._driver.validate_configuration()
        self.get_logger().info(
            f'驅動器組態確認，每馬達轉 {counts_per_motor_rev} counts'
        )

        geometry = self._params.build_geometry(counts_per_motor_rev)
        self._kinematics = DifferentialKinematics(geometry)

        self._driver.apply_motion_profile(
            linear_acc_ms=driver_params.linear_acc_ms,
            linear_dec_ms=driver_params.linear_dec_ms,
            s_curve_acc_ms=driver_params.s_curve_acc_ms,
            s_curve_dec_ms=driver_params.s_curve_dec_ms,
        )
        self._driver.enable()
        self.get_logger().info('驅動器已激磁')

    # ── 訂閱 ─────────────────────────────────────────────────────────────────

    def _on_cmd_vel(self, msg: Twist) -> None:
        self._target_linear = msg.linear.x
        self._target_angular = msg.angular.z
        self._last_cmd_time = self.get_clock().now()

    def _cmd_vel_expired(self) -> bool:
        elapsed = (self.get_clock().now() - self._last_cmd_time).nanoseconds * 1e-9
        return elapsed > self._params.control.cmd_vel_timeout_s

    # ── 控制迴圈 ─────────────────────────────────────────────────────────────

    def _on_timer(self) -> None:
        if self._driver is None or self._kinematics is None:
            return

        # 命令逾時或已進入故障狀態時一律送出停止，避免失控
        if self._faulted or self._cmd_vel_expired():
            command = None
        else:
            command = self._kinematics.to_wheel_command(
                self._target_linear, self._target_angular
            )

        try:
            if command is None:
                feedback = self._driver.stop()
            else:
                feedback = self._driver.command(
                    right_rpm=command.right_motor_rpm,
                    left_rpm=command.left_motor_rpm,
                )
        except Md2Error as exc:
            self._on_comm_error(exc)
            return

        self._consecutive_faults = 0

        state = self._kinematics.to_wheel_state(
            right_motor_rpm=feedback.right.rpm,
            left_motor_rpm=feedback.left.rpm,
            right_motor_counts=feedback.right.position_counts,
            left_motor_counts=feedback.left.position_counts,
        )
        stamp = self.get_clock().now().to_msg()
        self._publish_wheel_states(stamp, state)
        self._publish_diagnostics(stamp, feedback)

        if feedback.right.has_alarm or feedback.left.has_alarm:
            self._enter_fault(
                f'驅動器警報 right={feedback.right.alarm} left={feedback.left.alarm}'
            )

    def _on_comm_error(self, exc: Md2Error) -> None:
        self._consecutive_faults += 1
        self.get_logger().warn(
            f'通訊失敗（{self._consecutive_faults}/{_MAX_CONSECUTIVE_FAULTS}）：{exc}'
        )
        if self._consecutive_faults >= _MAX_CONSECUTIVE_FAULTS and not self._faulted:
            self._enter_fault('連續通訊失敗，停止送出運動命令')

    def _enter_fault(self, reason: str) -> None:
        if self._faulted:
            return
        self._faulted = True
        self.get_logger().error(f'進入故障狀態：{reason}')

    # ── 發布 ─────────────────────────────────────────────────────────────────

    def _publish_wheel_states(self, stamp, state) -> None:
        control = self._params.control
        msg = JointState()
        msg.header.stamp = stamp
        msg.header.frame_id = control.frame_id
        msg.name = [control.left_joint_name, control.right_joint_name]
        msg.position = [state.left_position_rad, state.right_position_rad]
        msg.velocity = [state.left_velocity_rad_s, state.right_velocity_rad_s]
        self._joint_pub.publish(msg)

    def _publish_diagnostics(self, stamp, feedback) -> None:
        right_id, left_id = self._driver.driver_ids
        array = DiagnosticArray()
        array.header.stamp = stamp
        array.status = [
            self._driver_status('right_wheel_driver', right_id, feedback.right),
            self._driver_status('left_wheel_driver', left_id, feedback.left),
            self._comm_status(feedback.comm_s),
        ]
        self._diag_pub.publish(array)

    def _driver_status(self, name: str, driver_id: int, motor) -> DiagnosticStatus:
        status = DiagnosticStatus()
        status.name = f'base_control: {name}'
        status.hardware_id = f'M1 driver id={driver_id}'
        if motor.has_alarm:
            status.level = DiagnosticStatus.ERROR
            status.message = f'警報 {motor.alarm}'
        else:
            status.level = DiagnosticStatus.OK
            status.message = motor.status_text
        status.values = [
            KeyValue(key='motor_status', value=str(motor.status)),
            KeyValue(key='motor_status_text', value=motor.status_text),
            KeyValue(key='alarm', value=str(motor.alarm)),
            KeyValue(key='motor_rpm', value=str(motor.rpm)),
            KeyValue(key='position_counts', value=str(motor.position_counts)),
        ]
        return status

    def _comm_status(self, comm_s: float) -> DiagnosticStatus:
        status = DiagnosticStatus()
        status.name = 'base_control: communication'
        status.hardware_id = self._params.serial.port
        if self._faulted:
            status.level = DiagnosticStatus.ERROR
            status.message = '故障狀態'
        elif self._consecutive_faults > 0:
            status.level = DiagnosticStatus.WARN
            status.message = f'連續失敗 {self._consecutive_faults} 次'
        else:
            status.level = DiagnosticStatus.OK
            status.message = '正常'
        status.values = [
            KeyValue(key='transaction_ms', value=f'{comm_s * 1000:.2f}'),
            KeyValue(key='consecutive_faults', value=str(self._consecutive_faults)),
            KeyValue(key='cmd_vel_expired', value=str(self._cmd_vel_expired())),
        ]
        return status

    # ── 關閉 ─────────────────────────────────────────────────────────────────

    def shutdown(self) -> None:
        """停止運動、解除激磁並關閉序列埠。"""
        if self._driver is not None:
            try:
                self._driver.stop()
                self._driver.disable()
                self.get_logger().info('驅動器已停止並解除激磁')
            except Md2Error as exc:
                self.get_logger().error(f'關閉期間通訊失敗：{exc}')
        if self._transport is not None:
            self._transport.close()


def main(args=None) -> int:
    rclpy.init(args=args)
    node = None
    try:
        node = BaseControlNode()
        rclpy.spin(node)
    except (DriverConfigError, Md2Error) as exc:
        print(f'base_control 啟動失敗：{exc}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.shutdown()
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())

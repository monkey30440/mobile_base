#!/usr/bin/env python3
# Copyright 2026 Antigravity Team.
# Verification script for IMP-015 / SYS-034: teleop_twist_keyboard interface validation.

import os
import pty
import signal
import subprocess
import sys
import time

import geometry_msgs.msg
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy


class TeleopVerifier(Node):
    def __init__(self):
        super().__init__('teleop_verifier')
        self.received_msgs = []
        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )
        self.sub = self.create_subscription(
            geometry_msgs.msg.TwistStamped,
            '/diff_drive_controller/cmd_vel',
            self.msg_callback,
            qos
        )

    def msg_callback(self, msg):
        self.received_msgs.append((time.time(), msg))


def main():
    print("=" * 70)
    print("IMP-015 / SYS-034 Teleop Twist Keyboard Interface Verification")
    print("=" * 70)

    rclpy.init()
    node = TeleopVerifier()

    cmd = [
        "ros2", "run", "teleop_twist_keyboard", "teleop_twist_keyboard",
        "--ros-args",
        "-p", "stamped:=true",
        "-r", "cmd_vel:=/diff_drive_controller/cmd_vel"
    ]

    print(f"[1] Spawning teleop_twist_keyboard CLI with PTY: {' '.join(cmd)}")
    master_fd, slave_fd = pty.openpty()

    proc = subprocess.Popen(
        cmd,
        stdin=slave_fd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        close_fds=True
    )
    os.close(slave_fd)

    # Allow node to start and create publisher
    time.sleep(1.5)
    rclpy.spin_once(node, timeout_sec=0.2)

    try:
        # Test 1: Send 'i' (forward motion)
        print("\n[2] Testing Forward Command (key: 'i')...")
        os.write(master_fd, b'i')
        
        # Spin to receive message
        t_start = time.time()
        while len(node.received_msgs) == 0 and time.time() - t_start < 2.0:
            rclpy.spin_once(node, timeout_sec=0.05)

        assert len(node.received_msgs) >= 1, "FAIL: No TwistStamped message received after 'i'"
        _, msg_i = node.received_msgs[-1]
        print(f"    Received TwistStamped on /diff_drive_controller/cmd_vel:")
        print(f"      header.stamp: sec={msg_i.header.stamp.sec}, nanosec={msg_i.header.stamp.nanosec}")
        print(f"      header.frame_id: '{msg_i.header.frame_id}'")
        print(f"      twist.linear.x: {msg_i.twist.linear.x}")
        print(f"      twist.angular.z: {msg_i.twist.angular.z}")
        assert msg_i.header.frame_id == "", f"Expected frame_id '', got '{msg_i.header.frame_id}'"
        assert abs(msg_i.twist.linear.x - 0.5) < 1e-4, f"Expected linear.x 0.5, got {msg_i.twist.linear.x}"
        assert abs(msg_i.twist.angular.z - 0.0) < 1e-4, f"Expected angular.z 0.0, got {msg_i.twist.angular.z}"
        print("    [PASS] Forward command matches exact TwistStamped contract.")

        # Test 2: Send 'j' (turn left / CCW angular motion)
        print("\n[3] Testing Turn Left Command (key: 'j')...")
        count_before = len(node.received_msgs)
        os.write(master_fd, b'j')
        
        t_start = time.time()
        while len(node.received_msgs) == count_before and time.time() - t_start < 2.0:
            rclpy.spin_once(node, timeout_sec=0.05)

        assert len(node.received_msgs) > count_before, "FAIL: No message received after 'j'"
        _, msg_j = node.received_msgs[-1]
        print(f"    Received TwistStamped on /diff_drive_controller/cmd_vel:")
        print(f"      twist.linear.x: {msg_j.twist.linear.x}")
        print(f"      twist.angular.z: {msg_j.twist.angular.z}")
        assert abs(msg_j.twist.linear.x - 0.0) < 1e-4, f"Expected linear.x 0.0, got {msg_j.twist.linear.x}"
        assert abs(msg_j.twist.angular.z - 1.0) < 1e-4, f"Expected angular.z 1.0, got {msg_j.twist.angular.z}"
        print("    [PASS] Angular turn command matches exact TwistStamped contract.")

        # Test 3: Send 'k' (manual active stop)
        print("\n[4] Testing Manual Active Stop Command (key: 'k')...")
        count_before = len(node.received_msgs)
        os.write(master_fd, b'k')
        
        t_start = time.time()
        while len(node.received_msgs) == count_before and time.time() - t_start < 2.0:
            rclpy.spin_once(node, timeout_sec=0.05)

        assert len(node.received_msgs) > count_before, "FAIL: No message received after 'k'"
        _, msg_k = node.received_msgs[-1]
        print(f"    Received TwistStamped on /diff_drive_controller/cmd_vel:")
        print(f"      twist.linear.x: {msg_k.twist.linear.x}")
        print(f"      twist.angular.z: {msg_k.twist.angular.z}")
        assert abs(msg_k.twist.linear.x - 0.0) < 1e-4, f"Expected zero linear.x, got {msg_k.twist.linear.x}"
        assert abs(msg_k.twist.angular.z - 0.0) < 1e-4, f"Expected zero angular.z, got {msg_k.twist.angular.z}"
        print("    [PASS] Active stop command successfully published zero velocity.")

        # Test 4: Idle timeout behavior (no input sent for 1.0s -> no new messages published)
        print("\n[5] Testing Idle Behavior (no input for 1.0s)...")
        count_before = len(node.received_msgs)
        time.sleep(1.0)
        rclpy.spin_once(node, timeout_sec=0.1)
        count_after = len(node.received_msgs)
        print(f"    Messages received during 1.0s idle: {count_after - count_before}")
        assert count_after == count_before, "FAIL: Unexpected messages published during keyboard idle"
        print("    [PASS] Teleop node blocked waiting for input; no stale messages repeated.")
        print("    -> Downstream diff_drive_controller cmd_vel_timeout (0.5s) will safely trigger zero-reference.")

        # Test 5: Clean shutdown (CTRL-C / '\x03')
        print("\n[6] Testing Clean Shutdown (CTRL-C / '\\x03')...")
        count_before = len(node.received_msgs)
        os.write(master_fd, b'\x03')
        
        t_start = time.time()
        while len(node.received_msgs) == count_before and time.time() - t_start < 2.0:
            rclpy.spin_once(node, timeout_sec=0.05)

        proc.wait(timeout=3.0)
        assert len(node.received_msgs) > count_before, "FAIL: No cleanup message received on CTRL-C"
        _, msg_sigint = node.received_msgs[-1]
        print(f"    Received final cleanup TwistStamped on /diff_drive_controller/cmd_vel:")
        print(f"      twist.linear.x: {msg_sigint.twist.linear.x}")
        print(f"      twist.angular.z: {msg_sigint.twist.angular.z}")
        assert abs(msg_sigint.twist.linear.x - 0.0) < 1e-4
        assert abs(msg_sigint.twist.angular.z - 0.0) < 1e-4
        print("    [PASS] Clean shutdown successfully published zero velocity.")

    finally:
        try:
            os.close(master_fd)
        except OSError:
            pass
        if proc.poll() is None:
            proc.terminate()
            proc.wait()
        node.destroy_node()
        rclpy.shutdown()

    print("\n" + "=" * 70)
    print("ALL IMP-015 / SYS-034 TELEOP INTERFACE TESTS PASSED (100% SUCCESS)")
    print("=" * 70)


if __name__ == '__main__':
    main()

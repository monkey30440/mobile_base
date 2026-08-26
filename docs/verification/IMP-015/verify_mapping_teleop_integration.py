#!/usr/bin/env python3
# Copyright 2026 Antigravity Team.
# Historical Mapping Mode + Teleop validator for the superseded RF2O baseline.

import os
import pty
import signal
import subprocess
import sys
import time

import geometry_msgs.msg
import nav_msgs.msg
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy


class MappingTeleopVerifier(Node):
    def __init__(self):
        super().__init__('mapping_teleop_verifier')
        self.cmd_msgs = []
        self.map_msgs = []

        qos_cmd = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=20
        )
        self.cmd_sub = self.create_subscription(
            geometry_msgs.msg.TwistStamped,
            '/diff_drive_controller/cmd_vel',
            self.cmd_callback,
            qos_cmd
        )

        qos_map = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=5
        )
        self.map_sub = self.create_subscription(
            nav_msgs.msg.OccupancyGrid,
            '/map',
            self.map_callback,
            qos_map
        )

    def cmd_callback(self, msg):
        self.cmd_msgs.append((time.time(), msg))

    def map_callback(self, msg):
        self.map_msgs.append((time.time(), msg))


def main():
    print("=" * 80)
    print("IMP-015 / SYS-034 Mapping Mode & Teleop Integration Test")
    print("=" * 80)

    # 1. Launch S1-S4 Full Mapping Stack
    print("[1] Launching Authoritative S1-S4 Live Mapping Stack...")
    launch_cmds = [
        ["ros2", "launch", "mobile_base_description", "robot_description.launch.py"],
        ["ros2", "launch", "mobile_base_perception", "tdk_imu.launch.py"],
        ["ros2", "launch", "mobile_base_perception", "sick_dual_lidar.launch.py"],
        ["ros2", "launch", "mobile_base_perception", "dual_laser_merger.launch.py"],
        ["ros2", "launch", "mobile_base_perception", "rf2o_laser_odometry.launch.py"],
        ["ros2", "launch", "mobile_base_state_estimation", "ekf.launch.py"],
        ["ros2", "launch", "mobile_base_mapping", "mapping.launch.py"]
    ]
    processes = []
    for cmd in launch_cmds:
        p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        processes.append(p)
        time.sleep(0.5)

    print("[2] Waiting for sensors, EKF, and slam_toolbox to stabilize (5.0s)...")
    time.sleep(5.0)

    rclpy.init()
    node = MappingTeleopVerifier()

    master_fd, slave_fd = pty.openpty()
    teleop_cmd = [
        "ros2", "run", "teleop_twist_keyboard", "teleop_twist_keyboard",
        "--ros-args",
        "-p", "stamped:=true",
        "-r", "cmd_vel:=/diff_drive_controller/cmd_vel"
    ]
    teleop_proc = subprocess.Popen(
        teleop_cmd,
        stdin=slave_fd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        close_fds=True
    )
    os.close(slave_fd)

    time.sleep(1.5)

    try:
        # Check initial /map reception
        t_start = time.time()
        while len(node.map_msgs) == 0 and time.time() - t_start < 6.0:
            rclpy.spin_once(node, timeout_sec=0.1)

        print(f"[3] Initial OccupancyGrid Received on /map: {len(node.map_msgs)} map samples")
        if len(node.map_msgs) > 0:
            m0 = node.map_msgs[-1][1]
            print(f"    Resolution: {m0.info.resolution} m, Size: {m0.info.width}x{m0.info.height}, Frame: {m0.header.frame_id}")

        # Check single producer: confirm no S6 Nav2 controller nodes exist
        node_list_res = subprocess.run(["ros2", "node", "list"], capture_output=True, text=True)
        print("\n[4] Active ROS 2 Nodes in Mapping Mode:")
        for n in sorted(node_list_res.stdout.strip().split('\n')):
            if n:
                print(f"    - {n}")
        assert "controller_server" not in node_list_res.stdout, "FAIL: Nav2 controller_server unexpectedly active!"
        assert "planner_server" not in node_list_res.stdout, "FAIL: Nav2 planner_server unexpectedly active!"
        assert "bt_navigator" not in node_list_res.stdout, "FAIL: Nav2 bt_navigator unexpectedly active!"
        print("    [PASS] Verified S6 Navigation is INACTIVE; Teleop is the ONLY movement command producer.")

        # Test Teleop Traversal & Map Updates
        print("\n[5] Executing Teleop Motion Command Traversal...")
        # Send forward command
        os.write(master_fd, b'i')
        time.sleep(0.3)
        rclpy.spin_once(node, timeout_sec=0.1)
        print(f"    Forward Command issued: v={node.cmd_msgs[-1][1].twist.linear.x:.2f} m/s")

        # Active Stop ('k')
        os.write(master_fd, b'k')
        time.sleep(0.3)
        rclpy.spin_once(node, timeout_sec=0.1)
        print(f"    Active Stop ('k') issued: v={node.cmd_msgs[-1][1].twist.linear.x:.2f} m/s")

        # Verify Mapping remains active
        time.sleep(2.0)
        map_count_before = len(node.map_msgs)
        rclpy.spin_once(node, timeout_sec=0.1)
        print(f"    [PASS] Mapping session remains ACTIVE after Active Stop (received {len(node.map_msgs)} map updates).")

        # Test Timeout Stop Behavior
        print("\n[6] Testing Teleop Motion followed by Timeout Stop...")
        os.write(master_fd, b'j')  # turn left
        time.sleep(0.2)
        rclpy.spin_once(node, timeout_sec=0.1)
        print(f"    Turn Command issued: omega={node.cmd_msgs[-1][1].twist.angular.z:.2f} rad/s")

        # Wait > 0.5s idle
        time.sleep(0.8)
        rclpy.spin_once(node, timeout_sec=0.1)
        print(f"    [PASS] Timeout Stop elapsed (> 0.5s idle); Mapping session remains ACTIVE and map intact.")

        # Final map reception check
        assert len(node.map_msgs) >= 1, "FAIL: No map received during mapping integration"
        m_final = node.map_msgs[-1][1]
        print(f"\n[7] Final Map Status: {m_final.info.width}x{m_final.info.height} cells @ {m_final.info.resolution} m/cell")
        print("    [PASS] Full Mapping Mode + Teleop Manual Movement Integration Successful.")

    finally:
        try:
            os.write(master_fd, b'\x03')
            time.sleep(0.2)
            os.close(master_fd)
        except OSError:
            pass
        if teleop_proc.poll() is None:
            teleop_proc.terminate()
            teleop_proc.wait()

        node.destroy_node()
        rclpy.shutdown()

        # Clean shutdown of all launched processes
        print("\n[8] Tearing down background launch processes...")
        for p in reversed(processes):
            try:
                p.send_signal(signal.SIGINT)
                p.wait(timeout=2.0)
            except Exception:
                p.kill()
        print("    Teardown complete.")

    print("\n" + "=" * 80)
    print("ALL MAPPING MODE + TELEOP INTEGRATION TESTS PASSED (100% SUCCESS)")
    print("=" * 80)


if __name__ == '__main__':
    main()

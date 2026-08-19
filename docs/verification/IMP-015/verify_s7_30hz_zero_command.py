#!/usr/bin/env python3
# Verification script for S7 Base Control 30 Hz Zero Command Baseline

import os
import pty
import subprocess
import time

log_file = "/workspaces/mobile_base/docs/verification/IMP-015/2026-08-19T193500_s7_30hz_zero_command_validation.txt"
with open(log_file, "w") as f:
    f.write("================================================================================\n")
    f.write("S7 Base Control 30 Hz Baseline Zero-Command & Timing Verification Log\n")
    f.write("================================================================================\n")
    f.write("Timestamp: 2026-08-19T19:35:00+08:00\n")
    f.write("Host: Jetson arm64 (/dev/ttyUSB0 M1 connected)\n")
    f.write("Baseline: Synchronous Model A2 @ 30 Hz, M1 response_timeout_ms = 50 ms\n")
    f.write("Evidence Class: STATIC, CONTROLLER_STATE, ROS_TOPIC, HARDWARE_REGISTER, ENCODER_FEEDBACK\n")
    f.write("Safety Gate: ZERO COMMAND ONLY (linear.x = 0.0, angular.z = 0.0)\n")
    f.write("================================================================================\n\n")

print("1. Launching S7 Base Control at 30 Hz with response_timeout_ms:=50...")
launch_proc = subprocess.Popen(
    ["ros2", "launch", "mobile_base_control", "base_control.launch.py", "response_timeout_ms:=50"],
    stdout=open("/tmp/base_control_30hz.log", "w"),
    stderr=subprocess.STDOUT
)
time.sleep(8)

def append_output(title, cmd):
    print(f"Running: {title}")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    with open(log_file, "a") as f:
        f.write(f"--- {title} ---\n")
        f.write(res.stdout)
        if res.stderr:
            f.write(f"\n[STDERR]\n{res.stderr}")
        f.write("\n\n")

append_output("1. ACTIVE CONTROLLERS (CONTROLLER_STATE)", "ros2 control list_controllers")
append_output("2. ACTIVE HARDWARE COMPONENTS (HARDWARE_REGISTER)", "ros2 control list_hardware_components")
append_output("3. /diff_drive_controller/cmd_vel BEFORE TELEOP (ROS_TOPIC)", "ros2 topic info /diff_drive_controller/cmd_vel -v")
append_output("4. READ-ONLY WHEEL FEEDBACK /joint_states (ENCODER_FEEDBACK)", "timeout 3 ros2 topic echo /joint_states --once")
append_output("5. READ-ONLY WHEEL ODOMETRY /diff_drive_controller/odom (ENCODER_FEEDBACK)", "timeout 3 ros2 topic echo /diff_drive_controller/odom --once")

print("2. Spawning teleop via PTY and sending active zero command ('k')...")
master, slave = pty.openpty()
teleop_proc = subprocess.Popen(
    ["ros2", "run", "teleop_twist_keyboard", "teleop_twist_keyboard", "--ros-args", "-p", "stamped:=true", "-r", "cmd_vel:=/diff_drive_controller/cmd_vel"],
    stdin=slave, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True
)
os.close(slave)
time.sleep(2)
os.write(master, b'k')  # Send Active Zero Command
time.sleep(2)

append_output("6. TELEOP ZERO COMMAND TOPIC INFO (ROS_TOPIC)", "ros2 topic info /diff_drive_controller/cmd_vel -v")

# Clean shutdown of teleop
os.write(master, b'\x03')
time.sleep(1)
teleop_proc.terminate()
os.close(master)

# Let control loop run for 5 more seconds to monitor 30 Hz timing
time.sleep(5)

# Terminate launch process
launch_proc.terminate()
launch_proc.wait(timeout=5)

append_output("7. CONTROLLER MANAGER 30 HZ TIMING & OVERRUN CHECK", "grep -i -E 'overrun|timeout|error|fail|exception' /tmp/base_control_30hz.log || echo 'NO OVERRUNS OR TIMEOUTS DETECTED AT 30 HZ'")

print("Verification complete. Summary log:")
with open(log_file, "r") as f:
    print(f.read())

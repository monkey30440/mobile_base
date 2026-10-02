# M1 wheel hardware

This package fills the confirmed M1-specific device gap from spec #32 / decision #22 / ticket #35. Native `ros2_control` and `diff_drive_controller` own differential kinematics, wheel odometry, velocity limits and command timeout. The adapter only exchanges Modbus Multi-drive2.0 wheel commands and valid velocity feedback. It publishes no TF and integrates no wheel position. `robot_localization` remains the single odom→base_footprint owner.

## Required target profile

Copy `config/target.template.yaml` to an operator-owned target file and fill **every** unresolved fact. The only supplied hardware path is the operator-confirmed `/dev/fihRobotBaseMotor`; firmware, IDs, mode, PDO mapping, serial configuration, gear ratios, direction and scales remain unresolved. Wheel geometry, speed limits, controller rate and response/command timeouts need applicable calibration/operating evidence. The template fails closed before device connection. Test fixture values are software inputs and are never deployment defaults.

`gear_ratio` means motor revolutions per wheel revolution; `direction` is +1 or -1 mapping positive wheel radians to positive/CW motor RPM. `feedback_rpm_per_count` converts signed16 current-speed feedback to motor RPM. The minimal adapter supports verified speed mode, Multi-drive2.0, PDO mapping0 or1, two distinct IDs1–8, and status STOP0/RUN2 with no alarm. It does not enable a drive, reset faults, change firmware parameters, release STO or manipulate brakes. Operators must establish the verified drive mode and hardware conditions separately.

The communication manual revision1.1 (2025-02-03), pages37–42, specifies FC03 reads at index0 (status/alarm/current speed) and FC10 writes at index8 (Multi-drive Lite command/data), addressed by the drive ID bitmask. The standard Modbus transport/CRC/error handling comes from libmodbus. Page33 specifies signed16 JG RPM and clamps a nonzero command below60RPM to60RPM. Such commands are rejected and request best-effort zero on both drives; otherwise the adapter could move faster than requested. A verified target with adequate gearing/command range is required; this limitation is not hidden by another kinematics engine.

## Start and Teleop

Build with the repository container workflow, then:

```bash
ros2 launch mobile_base_m1 m1.launch.py hardware_config:=/absolute/target.yaml model_file:=/absolute/mobile_base.urdf
ros2 control list_controllers
ros2 topic echo /base_controller/odom
ros2 topic echo /diagnostics
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -p stamped:=true -r cmd_vel:=/base_controller/cmd_vel
```

`model_file` is the geometry-only deployment URDF containing `left_wheel_joint` / `right_wheel_joint`. This launch inserts the device control fragment and starts the single native robot_state_publisher; a containing bringup must not start another model TF owner. Controller feedback uses velocity, `open_loop=false`, and `enable_odom_tf=false`. Native `/base_controller/cmd_vel` is stamped Twist; `/base_controller/odom` remains the wheel-feedback odometry source. Limits and controller timeout come from the explicit profile.

Before Teleop, cancel Navigation and wait for its native terminal result. Before Navigation, end the Teleop process (Ctrl-C). Do not interpret zero speed, lack of messages, command timeout, controller inactive or zero acknowledgement as session completion or evidence that the physical robot stopped. Use the operator's actual hardware stop procedure and independent observation. Shutdown/deactivation/error handling sends best-effort zero; a disconnected link cannot guarantee delivery.

## Diagnose

Use `/diagnostics`, native controller logs and `ros2 control list_hardware_components`. Per-wheel status includes drive ID, configured firmware, motor status, alarm code, feedback validity and the basic cause. Communication/CRC/short-response/timeouts and alarm/inhibited/unknown statuses invalidate both feedback interfaces; previous data are never substituted as current valid measurements. The controller manager receives ERROR so it can deactivate affected controllers. Fault reset/servo/brake/STO recovery is a deliberate operator hardware procedure, not automatic adapter behavior.

If launch rejects a target fact, complete it from authoritative evidence. If serial connection fails, check the actual container device mapping, path permissions and serial settings. If current-speed/status reads fail, verify Multi-drive2.0 mode, IDs/bitmask and applicable firmware/manual revision. If a command is rejected, check documented minimum RPM, configured gear/direction and speed limits. Do not resume until the cause and hardware conditions are understood.

## Evidence boundary

The software suite uses a pseudo-terminal Modbus peer at the external serial boundary and public ROS topics with the real native controller; fixture geometry, IDs, RPM and timeouts are controlled inputs. Bounded protocol tests verify signed scale/direction, the documented minimum-speed rejection, and fault/inhibited feedback invalidity. These do not validate real firmware compatibility, encoder feedback, wheel direction, displacement, stopping or calibrated odometry.

**REQUIRES HARDWARE VALIDATION:** verified target startup, valid wheel feedback, motion direction/displacement, alarms/disconnection, timeout/shutdown stop, and Teleop handover. **REQUIRES CALIBRATION:** effective wheel radius/separation, gearing/scales/polarity, limits/timeouts and downstream odometry performance. Actual test versions/results are recorded in the implementation evidence; software completion is not hardware acceptance.

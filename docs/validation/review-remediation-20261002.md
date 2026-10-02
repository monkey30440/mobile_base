# Review remediation — software only, 2026-10-02

Based on integration `b9a002f1b8bd049c7a481802e3d27c03bc5f2c8c`. This followup fixes configuration validation and a reproduced two-drive fault-preservation defect. It changes no drive parameters, production limits, archived historical evidence, hardware/platform acceptance or calibration conclusions. No host devices were mapped or opened during these checks.

- IMU baud0 RED changed the external PTY attributes to B0 (hangup). GREEN requires a positive supported integer before opening the port; the public ROS test observes a configuration diagnostic and unchanged PTY attributes. Existing115200 packet/topic behavior remains passing.
- M1 update_rate0.5 RED started native processes and failed to exit within the bounded test; conversion to int0 was accepted by launch. GREEN rejects fractional/bool/zero/negative rates before constructing native parameters. Four public launch cases report the configuration reason and observe no request at the external serial peer. Existing valid30Hz native workflows remain passing. An additional targeted copy of the same public native command/feedback/timeout test, with only the fixture update rate changed to20Hz, also passes.
- A CRC-valid response containing left STO9 and right alarm13 RED caused the first wheel's validity check to throw before recording the other fault. Later healthy peer replies allowed native shutdown to send SVOFF7, whose documented effect may implicitly clear alarms. GREEN records both drives and latches all faults atomically before per-wheel conversion. The same public shutdown test observes no SVOFF even after subsequent healthy replies. Existing alarm-during-enable preservation also passes.

Separate `MultiDriveCommand` and `DriveStatus` enums distinguish ServoOn6 from Inhibited6. One CRC-validated snapshot function is shared by normal reads and fresh no-alarm cleanup checks; usable-feedback status rules remain shared and unchanged. This adds no automatic reset/re-enable, fallback, runtime observer or custom kinematics.

Validation used `mobile-base-v1-production-check:jazzy`, image SHA256`307cf16d1581c1078d21e67c1d8c9aab21eeca61641e1c9a23b90c34d0b83e46`, with an isolated worktree and no device mapping:

```bash
source /opt/ros/jazzy/setup.bash
colcon build --packages-select mobile_base_imu mobile_base_m1
source install/setup.bash
colcon test --packages-select mobile_base_imu mobile_base_m1 --event-handlers console_direct+
colcon test-result --verbose
```

Full affected-package regression PASS: IMU7 pytest cases (5 packet,2 public ROS); M1 4 gtest +23 public ROS/launch pytest cases. Colcon aggregate36,0 errors,0 failures,0 skipped (includes2 CTest suite entries);34 distinct cases. Unchanged unrelated packages were not rerun. Hardware motion, physical stopping after faults/link loss/isolated timeout, unidentified firmware, production timing/limits, coordinate integration and calibration remain outside this software evidence.

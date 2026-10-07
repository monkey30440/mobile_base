# Independent component launches — 2026-10-07

Operator confirmed manually starting each owning package. Spec32 and tickets35/36/37/38 were reconciled before runtime edits. This supersedes earlier sensor_model and Control-owned RSP component entries; prior hardware/GUI evidence remains historical, without claiming the new manual workflow physically accepted.

Description alone starts native RSP and publishes geometry/model TF. Optional explicit hardware_config adds the existing M1 ros2_control declaration, relocated from Control's launch; it opens no device. Control starts native controller_manager/spawners and subscribes to the Description robot_description; model_file now belongs to Description alone. Perception starts IMU/LiDAR separately; sensor_model and its Description dependency are removed. No protocol/driver implementation, mounting pose, wheel-state interface, odometry ownership or model geometry changed.

This follows [Jazzy Controller Manager's native topic input](https://control.ros.org/jazzy/doc/ros2_control/controller_manager/doc/userdoc.html) and [Jazzy migration guidance](https://control.ros.org/jazzy/doc/ros2_control/doc/migration.html). No custom description publisher or obsolete description parameter input is added.

Use the same explicit hardware profile for Description and Control, starting Description with that profile before Control. Geometry-only Description remains usable for passive model/sensor checks. Model selection does not open hardware; Control activation may Servo ON at zero command and retains existing lifecycle/stop limitations. No automatic comparison of two profile files or hot reload is claimed; mismatched/invalid setup requires deliberately ending and restarting the selected configuration. This is component verification, not product Bringup/readiness or calibrated deployment acceptance.

## Software evidence

ARM64 production-check image SHA256307cf16d1581c1078d21e67c1d8c9aab21eeca61641e1c9a23b90c34d0b83e46; native controller_manager4.48.0, RSP3.3.4, xacro2.1.1, SICK3.9.0. Network-none container, no physical devices mapped, read-only source. Fresh four-package build/install in `/tmp/independent-final` prevents removed-launch overlay leftovers; sensor_model is absent from clean install. Syntax/package XML/diff checks passed.

At the agreed installed-launch/public ROS seam, the separate Description/Control test first failed with2 robot_description publishers, then passed with1 publisher and native control feedback. It verifies the sole model remains after independently stopping Control. Another case loads the actual installed model with a pseudo-terminal hardware profile and observes the native description without any Modbus request or controller startup. Existing measured wheel JointState/TF, timeout, lifecycle, fault/recovery and native timing tests now launch Description separately; no fake joint state is added.

Final full suite: Control33 public ROS cases +4 C++ cases; Description1; Perception20; existing Bringup dataset/native-EKF10. **68 actual cases +3 CTest wrappers =71 counts;0errors,0failures,0skipped.** No new physical tests were performed. Real stop, target compatibility, independent manual GUI workflow and calibration remain separately applicable acceptance work.

Two-axis review retained user-approved f591f4e basis, scoped current delta against d74194b: Spec0 actionable findings. Standards found one small documentation ambiguity about model versus hardware validation; corrected,0 remaining findings. No issue closed or dependencies removed.

[Raw TDD/full-suite XML, build/test logs, issue-body snapshots, environment and source hashes](artifacts/independent-component-launches-20261007.tar.gz).

# M1 software evidence — 2026-10-02

Scope: ticket #35 / spec #32 minimal M1 adapter and native controller workflow. An isolated `docker run --rm --runtime runc --user 1000:1000 -v /tmp/mobile-base-35:/workspace mobile-base-v1-test:jazzy` used only a pseudo-terminal peer. No host serial device was opened or motor physically commanded by these checks.

Commands: `colcon build --packages-select mobile_base_m1 --cmake-clean-cache`, then `source install/setup.bash`, `colcon test --packages-select mobile_base_m1`, `colcon test-result --verbose`. Final result: no errors/failures/skips; 3 gtest cases and 4 public ROS/launch pytest cases (colcon's aggregate reports 9 because CTest suite entries are counted as well).

Observed public behavior:

- Real native diff_drive_controller receives stamped 0.1 m/s and external peer observes signed (+95, -95) motor RPM using explicit software fixture ratio 10 and opposite wheel polarity. Independently supplied ±120 RPM feedback produces 0.125663706 m/s wheel odometry, zero angular speed, and per-wheel valid diagnostics. Native 0.3 s command timeout produces zero requests.
- Injected status FAULT 5 / alarm 13 reports ERROR with left wheel source/drive ID 1 and alarm context, invalidates feedback and requests both wheels zero.
- Silent peer produces bounded read-timeout ERROR with feedback_valid=false, retains source identity, and observes best-effort zero requests; zero acknowledgement/physical stopping is not inferred.
- Unresolved deployment template exits launch with a missing-target-fact reason before hardware startup.

RED→GREEN conversion slices: missing conversion API→worked literal 600 RPM conversion; sub-60 RPM initially accepted→documented rejection; missing checked-feedback API→alarm/inhibited rejection. Public native ROS RED caught typed command initialization (int 0 incompatible with velocity double), corrected to 0.0. ROS test awaits native rolling velocity estimation after startup rather than declaring its initial transient invalid. Extra fault/timeout cases cover already implemented invalidity behavior at the higher public seam.

Actual installed versions in successful test image (arm64): hardware_interface/controller_manager 4.48.0; diff_drive_controller 4.42.1; diagnostic_updater 4.2.7; libmodbus 3.1.10; FastCDR 2.2.8; FastDDS/fastrtps 2.14.6; rmw_fastrtps_cpp 8.4.4. These are actual dependency resolutions, not the prior research snapshot's requested 4.48.1. Initial image mixed older FastCDR 2.2.5 with newly installed pal_statistics_msgs and failed with an undefined serialize(unsigned) symbol; root aligned native DDS dependencies before the passing workflow runs. Compatible target/production image must retain applicable versions.

**UNRESOLVED:** actual M1 firmware/IDs/serial settings/mode/PDO mapping/gearing/direction/scales/limits and operating timeouts; only `/dev/fihRobotBaseMotor` is operator-confirmed. Deployment is intentionally blocked on those facts. **REQUIRES HARDWARE VALIDATION:** actual compatible startup/feedback/drive alarms/RS485 loss, direction/displacement, timeout/shutdown physical stop and Operator Teleop handover. **REQUIRES CALIBRATION:** effective wheel radius/separation, scales/polarity and odometry performance. The fixture's numerical profile is not target evidence, and this ticket does not claim full hardware acceptance.

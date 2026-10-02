# V1 research: hardware platform and native local-motion boundaries

Research ticket [#19](https://github.com/monkey30440/mobile_base/issues/19), map [#18](https://github.com/monkey30440/mobile_base/issues/18). Checked 2026-10-02. This is research evidence, **not an architecture selection, specification, hardware acceptance or cleared map**.

## Authority and investigative scope

User-confirmed facts: Ubuntu 24.04, ROS 2 Jazzy, current stable compatible packages; AGX Orin; robot authority `RWF_V2.0_QA_release.xml`; M1 via USB–RS485/Modbus/Multi-drive 2.0; IIM-42652 via USB; picoScan150 via Ethernet. Five workflows and cancel-navigation-before-Teleop are as recorded in [map #18](https://github.com/monkey30440/mobile_base/issues/18). Those facts are requirements, not independently observed device configuration.

Repository inspected at `6f127f7288b9455463b692406f0a8ce471a574d7`: tracked filenames, vendor manuals, and allowed IMU documentary reference only. No existing spec, old map, ADR, project model, or other project implementation was used. No runtime code changed. `git ls-files '*RWF*' '*.xml'` and filename inventory found **no original RWF XML**: geometry, wheel topology, joint names, axes, footprint and sensor extrinsics remain UNRESOLVED. Existing project models were deliberately not substituted.

Vendor evidence retained in that commit:

- [M1 communication manual](https://github.com/monkey30440/mobile_base/blob/6f127f7288b9455463b692406f0a8ce471a574d7/src/mobile_base_control/docs/M1-COMM_UM-01-S0686.pdf): internal document SS-01-S0647, rev 1.1, 2025-02-03; SHA256 `6be696b136570a9871b6bf8dc6acbc836c43fab290ea8ba5e88c3c0f282d677a`.
- [M1 user manual](https://github.com/monkey30440/mobile_base/blob/6f127f7288b9455463b692406f0a8ce471a574d7/src/mobile_base_control/docs/M1-UserManual_UM-01-S0701.pdf): SHA256 `599d8142711fa92f2cd105827ef8c711b22d727b0161332059537962fe01769b`.
- [TDK DS-000440 rev 1.3](https://github.com/monkey30440/mobile_base/blob/6f127f7288b9455463b692406f0a8ce471a574d7/src/tdk_ros2_imu/docs/ds-000440-iim-42652-datasheet.pdf): SHA256 `88aedb9e2604f8adb6421a057ee4922b484b3464ca4c0ea3edaf5fa48f782615`; manufacturer [product entry](https://www.invensense.tdk.com/en-us/products/motion-tracking/6-axis/iim-42652).

GitNexus discovery bound `mobile_base`, `/home/zzz/mobile_base`; index timestamp 2026-10-01T01:41:44.810Z, commit `00c3319630216dfbc3ce349e0e5c12d22661c91c`, reported six commits behind. No IMU implementation symbols were explored through that stale index; **dependency impact could not be determined**. Documentary IMU reference was sufficient here; no runtime modification or unsupported dependency inference occurred.

## Platform and stable release evidence

CONFIRMED: NVIDIA's current [downloads and notes](https://developer.nvidia.com/embedded/jetpack/downloads) list JetPack **7.2.1**, Jetson Linux **39.2.1**, dated **2026-08-11**, Orin Family hardware, kernel 6.8 and L4T Ubuntu 24.04. [JetPack overview](https://developer.nvidia.com/embedded/jetpack) also explicitly includes Orin and Ubuntu 24.04. Thus “AGX Orin necessarily requires Ubuntu 22.04” is no longer supported by retrieved upstream evidence. Carrier/module SKU, boot storage and installed BSP are unobserved; specific platform flashing, USB/Ethernet operation and workload performance REQUIRES HARDWARE VALIDATION. This is a feasible supported platform candidate, not a deployment decision.

CONFIRMED: Jazzy deb documentation source targets Noble 24.04 and provides arm64 status resources ([ROS documentation source, Jazzy branch](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Installation/Ubuntu-Install-Debs.rst)). Documentation HTML was access-denied, so primary source was read instead.

Release snapshot: [rosdistro Jazzy distribution at immutable commit `9cca73049e6c6b941fa8fca3a33229acaededdfe`](https://github.com/ros/rosdistro/blob/9cca73049e6c6b941fa8fca3a33229acaededdfe/jazzy/distribution.yaml), committed 2026-10-01T21:37:31Z, records:

| Package family | Jazzy release metadata |
|---|---|
| ros2_control | 4.48.1-1 |
| ros2_controllers | 4.42.1-1 |
| robot_localization | 3.8.3-1 |
| robot_state_publisher | 3.3.4-1 |
| teleop_twist_keyboard | 2.4.1-1 |
| twist_mux | 4.5.0-1 |
| sick_scan_xd | 3.9.0-1 |

These are Jazzy release metadata, not proof of the exact apt binaries installed on the target or simultaneous build-farm availability. Global GitHub latest-release is misleading across ROS distributions: robot_localization API latest-release reported 3.5.1 while Jazzy release metadata is 3.8.3-1. SICK [release 3.9.0](https://github.com/SICKAG/sick_scan_xd/releases/tag/3.9.0), published 2026-03-17, agrees with Jazzy metadata. Nav2/slam_toolbox evidence belongs to the other map research tickets.

## Requirement → native boundary → gap

| Confirmed workflow need / capability responsibility | Native evidence and completeness | Gap and minimal candidate boundary; no selection |
|---|---|---|
| Mapping, Localization, Navigation and Teleop need a trustworthy physical model and frames | robot_state_publisher consumes URDF and joint state and publishes fixed/moving transforms ([Jazzy upstream](https://github.com/ros/robot_state_publisher/tree/3.3.4)). Native model publication exists. | Original URDF missing: platform geometry/topology UNRESOLVED. Data/configuration is required before determining whether differential kinematics applies; no custom model engine established. |
| Physical commands and feedback must cross M1 USB–RS485 boundary | ros2_control supplies lifecycle/resource/controller management and hardware plugin contracts; its read/write boundary requires the actual hardware component ([Jazzy getting started](https://control.ros.org/jazzy/doc/getting_started/getting_started.html)). A generic framework is not an M1 adapter. | CONFIRMED protocol-to-ROS responsibility remains outside generic controllers. No compatible public M1 plugin was identified in manufacturer/GitHub searches; universal absence is UNRESOLVED. Minimal candidate, if no reusable adapter exists, is device transport/protocol, command and feedback conversion, errors and lifecycle integration only. |
| Body velocity, local odometry and stale-command handling | diff_drive_controller supplies wheel velocity outputs, position/velocity-feedback odometry, optional odom TF, velocity/acceleration/jerk limits and command timeout ([Jazzy documentation](https://control.ros.org/jazzy/doc/ros2_controllers/diff_drive_controller/doc/userdoc.html)). | Native kinematics are conditionally complete for a confirmed differential base. Motor sign, gear ratio, wheel geometry, available feedback and stop behavior still need authority/validation. A second project kinematics/odometry implementation has no confirmed justification. |
| Continuous pose estimate for moving into map and navigating | robot_localization supports wheel/IMU fusion, planar mode, sensor timeout and selectable TF publication ([3.8.3 state-estimation documentation](https://github.com/cra-ros-pkg/robot_localization/blob/3.8.3/doc/state_estimation_nodes.rst)). | Native estimator candidate is available; choosing inputs, covariance and the sole odom→base TF owner remains a decision. It does not establish map localization or physical accuracy. |
| Operator movement after cancellation, including before localization | teleop_twist_keyboard 2.4.1 supports remapping and stamped output ([release README](https://github.com/ros2/teleop_twist_keyboard/blob/2.4.1/README.md)); twist_mux 4.5.0 supports stamped/unstamped output plus configured priorities, timeouts and locks ([source](https://github.com/ros-teleop/twist_mux/blob/4.5.0/src/twist_mux.cpp)). | Native command generation/arbitration exist. Arbitration does not itself verify NavigateToPose terminal cancellation or physical stop. Handoff ownership/procedure needs a decision; no custom arbiter justified by present evidence. |
| Laser input for Mapping/Localization/obstacle sensing | SICK 3.9.0 explicitly supplies picoScan150 ROS2 launch, Ethernet addresses and LaserScan fullframe/segment handling ([release README](https://github.com/SICKAG/sick_scan_xd/blob/3.9.0/README.md), [picoScan launch](https://github.com/SICKAG/sick_scan_xd/blob/3.9.0/launch/sick_picoscan.launch)). | Native driver coverage CONFIRMED; exact firmware/network, scan topic, echo configuration, timestamp and TF/extrinsics need configuration plus hardware validation. No project LiDAR decoder confirmed necessary. |
| IMU input and component-level failure information | TDK silicon provides I3C/I2C/SPI, not USB (DS-000440 pp.1,23,51). Allowed HandBoard guide documents STM32 virtual COM, 59-byte little-endian packet, AA55 header, XOR checksum, g/dps and power-on-relative yaw ([reference guide](https://github.com/monkey30440/mobile_base/blob/6f127f7288b9455463b692406f0a8ce471a574d7/src/tdk_ros2_imu/HandBoard_IMU_V1_Quick_Guide.md)). | CONFIRMED silicon datasheet alone cannot define this USB product. Minimal bridge-to-Imu conversion responsibility is documented by allowed reference; exact board/firmware identity and rates UNRESOLVED. Reuse/adaptation of allowed driver is a future decision, not independently revalidated here. |

## M1 protocol findings and limits

CONFIRMED from M1 communication manual §6, pp.37–44: Multi-drive 2.0 uses Modbus FC **03h**, **10h**, **17h**, supporting 1–8 drivers. Address high byte contains `0xF` and data index; low byte is driver-ID bitmap. Read mapping exposes motor state, alarm, RPM, bus voltage, current, high/low position or Hall count and IO. Write mapping depends on **09-26**, and includes Multi-drive command/data and digital RPM/acceleration/deceleration/torque. The FC17 example uses **ID 0x65**, two driver contributions and a final CRC; first contribution carries header/byte count, later contributions append data and internal Error_Check. A standard Modbus library alone does not define this vendor mapping or feedback meaning. [Manual](https://github.com/monkey30440/mobile_base/blob/6f127f7288b9455463b692406f0a8ce471a574d7/src/mobile_base_control/docs/M1-COMM_UM-01-S0686.pdf).

§2 p.2 specifies RS485 timeout parameter **05-17** and RTU inter-frame timing. User manual protection table identifies code 21 as CAN/RS485 communication timeout. Actual firmware support, drive IDs, baud/parity, mode, mapping, count units/rollover, USB adapter identity, wiring/termination and behavior on command silence, cable removal or process crash are **REQUIRES HARDWARE VALIDATION**, not inferred from these tables. Wheel radius/separation, reduction and slip compensation are **REQUIRES CALIBRATION**. Never equate ROS command timeout with a verified motor-level stop. [Communication manual](https://github.com/monkey30440/mobile_base/blob/6f127f7288b9455463b692406f0a8ce471a574d7/src/mobile_base_control/docs/M1-COMM_UM-01-S0686.pdf), [user manual](https://github.com/monkey30440/mobile_base/blob/6f127f7288b9455463b692406f0a8ce471a574d7/src/mobile_base_control/docs/M1-UserManual_UM-01-S0701.pdf).

## Physical and documentary follow-up

UNRESOLVED: obtain original RWF XML and motor/gearing installation data; identify carrier/module/BSP and IMU board firmware; establish whether a reusable M1 adapter fully covers Multi-drive 2.0. These can affect architecture and must not be relabeled calibration merely to clear the map.

REQUIRES HARDWARE VALIDATION: actual target boot and device enumeration; drive protocol/feedback/stop fault paths; SICK scan continuity/time/frame correctness; USB IMU units, packet resynchronization, disconnect/reconnect, update rate and drift; complete cancel-to-Teleop physical handoff. User says allowed IMU implementation passed verification; no specific acceptance records were supplied/read, so that is user-provided reference evidence, not new validation.

REQUIRES CALIBRATION: authoritative/measured sensor extrinsics, wheel radius/separation and scale, IMU biases/covariance/installation axes, estimator noise and drift. HandBoard guide explicitly states no magnetometer and power-on-relative yaw drift; this cannot be treated as absolute map heading ([allowed README](https://github.com/monkey30440/mobile_base/blob/6f127f7288b9455463b692406f0a8ce471a574d7/src/tdk_ros2_imu/README.md)).

No software runtime test or hardware/calibration operation was run: this note establishes documentary native boundaries, not configured-system acceptance. Static upstream source inspection supports stamped command compatibility; exact target binaries/performance remain unverified. Next decision tickets may settle platform deployment, authoritative model recovery, M1 adapter reuse/gap ownership, local-estimation/TF ownership, sensor integration and cancellation handoff. This research does not choose their outcomes.

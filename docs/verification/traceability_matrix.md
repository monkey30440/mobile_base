# System Requirement Traceability Matrix

## 1. Purpose & Authority Boundaries

This document serves as the **canonical Requirement Traceability Matrix (RTM)** for the `mobile_base` repository, establishing bidirectional traceability between normative system requirements, responsible subsystems, production implementation artifacts, verification methods, execution evidence references, and verification statuses.

> [!IMPORTANT]
> **Authority Boundaries:**
> * **Normative Requirements:** Defined exclusively in [`03_REQUIREMENTS.md`](../03_REQUIREMENTS.md). This matrix reflects those requirements without weakening, modifying, or creating normative criteria.
> * **Architectural Allocation:** Subsystem boundaries (S1–S7) follow [`04_SYSTEMS.md`](../04_SYSTEMS.md).
> * **Implementation Reality:** Production source code (`src/*`), launch files, parameter YAMLs, URDF models, and Behavior Tree definitions represent as-built ground truth.
> * **Evidence Classification:** All cited evidence artifacts resolve to [`evidence_index.md`](evidence_index.md).
> * **Historical Evidence Boundary:** Historical execution records (e.g., test suite pass records at commit `8ab06d9` or physical runs in `IMP-007`–`015`) reflect execution at their respective historical baselines and are classified as `HISTORICALLY VERIFIED`. No runtime tests were executed during documentation convergence; historical evidence is not converted into a live `CURRENT VERIFIED` claim on `HEAD`.

---

## 2. Verification Status Semantics

Every requirement is assigned exactly one of the six approved verification statuses:

| Verification Status | Definition & Application Criteria |
|---|---|
| **`CURRENT VERIFIED`** | Verification executed, observed, and confirmed on the active `HEAD` working tree baseline. |
| **`HISTORICALLY VERIFIED`** | Verified through physical hardware runs, telemetry logs, or automated test executions at a documented historical commit baseline; evidence is cataloged in [`evidence_index.md`](evidence_index.md) and directly demonstrates normative acceptance criteria. |
| **`IMPLEMENTED / NOT RE-VERIFIED`** | Implementation exists in production source code, launch files, or configurations, but lacks fresh or dedicated runtime re-verification on `HEAD`. |
| **`PARTIAL`** | Implementation or verification is partially complete, or contains a documented and bounded operational limitation (e.g., unidirectional success with progress timeout on return path). |
| **`GAP`** | Requirement ID allocation gap (unallocated/retired numbering gap — not an implementation or functionality defect in the system). |
| **`UNKNOWN / INSUFFICIENT EVIDENCE`** | Available evidence is insufficient or inconclusive to establish verification compliance. |

---

## 3. Requirement Traceability Matrix (SYS-001 ~ SYS-034)

The following table explicitly accounts for every requirement ID from `SYS-001` through `SYS-034`:

| Requirement ID | Requirement Name & Scope | Subsystem | Implementation Source Path(s) | Verification Method | Execution Evidence Reference | Verification Status |
|---|---|---|---|---|---|---|
| **SYS-001** | 建立地圖<br>(Mapping Initialization & 2D Grid Creation) | **S4 Mapping** | [`slam_toolbox.yaml`](../../src/mobile_base_mapping/config/slam_toolbox.yaml)<br>[`mapping.launch.py`](../../src/mobile_base_mapping/launch/mapping.launch.py)<br>[`mobile_base.launch.py`](../../src/mobile_base_bringup/launch/mobile_base.launch.py) | Hardware Procedure & Runtime Observation | [`EVID-E03`](evidence_index.md#5-docsevidence-artifact-index), [`EVID-E05`](evidence_index.md#5-docsevidence-artifact-index), [`RAW-014-02`](evidence_index.md#imp-014-s4-mapping-mapio-integration-3-files), [`RAW-015-13`](evidence_index.md#imp-015-s7-manual-teleop-base-control-physical-motion-22-files) | **HISTORICALLY VERIFIED** |
| **SYS-002** | 儲存地圖<br>(Map Package Persistence) | **S4 Mapping** | [`save_map.sh`](../../src/mobile_base_bringup/scripts/save_map.sh)<br>[`mapping.launch.py`](../../src/mobile_base_mapping/launch/mapping.launch.py) | Hardware Procedure & Integration Script Execution | [`RAW-014-03`](evidence_index.md#imp-014-s4-mapping-mapio-integration-3-files), [`EVID-E03`](evidence_index.md#5-docsevidence-artifact-index) | **HISTORICALLY VERIFIED** |
| **SYS-003** | LiDAR 感知<br>(Dual LiDAR Scan Acquisition) | **S2 Perception** | [`sick_dual_lidar.launch.py`](../../src/mobile_base_perception/launch/sick_dual_lidar.launch.py)<br>[`package.xml`](../../src/mobile_base_perception/package.xml) | Hardware Telemetry Inspection & Dual Sensor Acquisition | [`EVID-E06`](evidence_index.md#5-docsevidence-artifact-index), [`EVID-E14`](evidence_index.md#5-docsevidence-artifact-index), [`RAW-010-02`](evidence_index.md#imp-010-s2-dual-lidar-acquisition-2-files), [`RAW-010-01`](evidence_index.md#imp-010-s2-dual-lidar-acquisition-2-files) | **HISTORICALLY VERIFIED** |
| **SYS-004** | IMU 感知<br>(6-DoF IMU Telemetry Acquisition) | **S2 Perception** | [`tdk_imu_node.py`](../../src/tdk_ros2_imu/tdk_ros2_imu/tdk_imu_node.py)<br>[`protocol.py`](../../src/tdk_ros2_imu/tdk_ros2_imu/protocol.py)<br>[`tdk_imu.launch.py`](../../src/mobile_base_perception/launch/tdk_imu.launch.py)<br>[`tdk_imu.yaml`](../../src/mobile_base_perception/config/tdk_imu.yaml) | Hardware Preflight & Dynamic Telemetry Inspection | [`EVID-E06`](evidence_index.md#5-docsevidence-artifact-index), [`RAW-011-02`](evidence_index.md#imp-011-s2-tdk-imu-runtime-integration-4-files), [`RAW-011-03`](evidence_index.md#imp-011-s2-tdk-imu-runtime-integration-4-files), [`RAW-011-04`](evidence_index.md#imp-011-s2-tdk-imu-runtime-integration-4-files), [`RAW-011-01`](evidence_index.md#imp-011-s2-tdk-imu-runtime-integration-4-files) | **HISTORICALLY VERIFIED** |
| **SYS-005** | 系統里程<br>(Kinematic-ICP & EKF Odometry Fusion) | **S3 State Estimation** | [`LidarOdometryServer.cpp`](../../src/kinematic_icp/ros/src/kinematic_icp_ros/server/LidarOdometryServer.cpp)<br>[`kinematic_icp_ros.yaml`](../../src/kinematic_icp/ros/config/kinematic_icp_ros.yaml)<br>[`ekf.yaml`](../../src/mobile_base_state_estimation/config/ekf.yaml)<br>[`ekf.launch.py`](../../src/mobile_base_state_estimation/launch/ekf.launch.py) | Hardware Execution & Sensor Fusion Characterization | [`EVID-E05`](evidence_index.md#5-docsevidence-artifact-index), [`EVID-E07`](evidence_index.md#5-docsevidence-artifact-index), [`EVID-E08`](evidence_index.md#5-docsevidence-artifact-index), [`RAW-013-02`](evidence_index.md#imp-013-s3-state-estimation-ekf-integration-2-files) | **HISTORICALLY VERIFIED** |
| **SYS-006** | 持續更新地圖<br>(Continuous Occupancy Grid Update) | **S4 Mapping** | [`slam_toolbox.yaml`](../../src/mobile_base_mapping/config/slam_toolbox.yaml)<br>[`mapping.launch.py`](../../src/mobile_base_mapping/launch/mapping.launch.py) | Hardware Ground Motion & Dynamic Mapping Observation | [`RAW-015-13`](evidence_index.md#imp-015-s7-manual-teleop-base-control-physical-motion-22-files), [`EVID-E03`](evidence_index.md#5-docsevidence-artifact-index), [`EVID-E05`](evidence_index.md#5-docsevidence-artifact-index) | **HISTORICALLY VERIFIED** |
| **SYS-007** | 載入地圖<br>(Map Package Loading & Ready State) | **S5 Localization** | [`navigation.launch.py`](../../src/mobile_base_navigation/launch/navigation.launch.py)<br>[`site_resolution.py`](../../src/mobile_base_bringup/launch/site_resolution.py)<br>[`nav2_params.yaml`](../../src/mobile_base_navigation/config/nav2_params.yaml) | Hardware Execution & Site Resolution Inspection | [`EVID-E03`](evidence_index.md#5-docsevidence-artifact-index), [`EVID-E11`](evidence_index.md#5-docsevidence-artifact-index), [`RAW-014-03`](evidence_index.md#imp-014-s4-mapping-mapio-integration-3-files) | **HISTORICALLY VERIFIED** |
| **SYS-008** | Navigation Target<br>(Target Type Discrimination) | **S6 Navigation** | [`target_admission.cpp`](../../src/mobile_base_navigation/src/target_admission.cpp)<br>[`target_admission.hpp`](../../src/mobile_base_navigation/include/mobile_base_navigation/target_admission.hpp)<br>[`navigate_to_station_app.cpp`](../../src/mobile_base_navigation/src/navigate_to_station_app.cpp)<br>[`navigate_to_station_main.cpp`](../../src/mobile_base_navigation/src/navigate_to_station_main.cpp) | Automated Unit Test (Goal Pose & Station) & Hardware Acceptance Run (Station) | [`EVID-E11`](evidence_index.md#5-docsevidence-artifact-index), [`EVID-E03`](evidence_index.md#5-docsevidence-artifact-index) | **HISTORICALLY VERIFIED** |
| **SYS-009** | Goal Pose Normalization<br>(CLI Pose Parameter Normalization) | **S6 Navigation** | [`target_admission.cpp`](../../src/mobile_base_navigation/src/target_admission.cpp)<br>[`target_admission.hpp`](../../src/mobile_base_navigation/include/mobile_base_navigation/target_admission.hpp) | Automated Unit Test & Test Fixture Verification | [`EVID-E03`](evidence_index.md#5-docsevidence-artifact-index), [`EVID-E16`](evidence_index.md#5-docsevidence-artifact-index) | **HISTORICALLY VERIFIED** |
| **SYS-010** | 地圖定位<br>(AMCL Global Localization & map→odom TF) | **S5 Localization** | [`amcl_params.yaml`](../../src/mobile_base_localization/config/amcl_params.yaml)<br>[`localization.launch.py`](../../src/mobile_base_localization/launch/localization.launch.py)<br>[`navigation.launch.py`](../../src/mobile_base_navigation/launch/navigation.launch.py) | Hardware Execution & Autonomous Navigation Run | [`EVID-E11`](evidence_index.md#5-docsevidence-artifact-index), [`EVID-E03`](evidence_index.md#5-docsevidence-artifact-index) | **HISTORICALLY VERIFIED** |
| **SYS-011** | 路徑規劃<br>(Nav2 Global Path Planning) | **S6 Navigation** | [`nav2_params.yaml`](../../src/mobile_base_navigation/config/nav2_params.yaml)<br>[`route_assisted_nav.xml`](../../src/mobile_base_navigation/behavior_trees/route_assisted_nav.xml) | Hardware Execution & Autonomous Navigation Run | [`EVID-E11`](evidence_index.md#5-docsevidence-artifact-index), [`EVID-E03`](evidence_index.md#5-docsevidence-artifact-index) | **HISTORICALLY VERIFIED** |
| **SYS-012** | Unallocated Requirement ID<br>(Omitted in Baseline) | **Unallocated** | *None (Requirement ID allocation gap — not an implementation/functionality gap)* | Static Documentation & Requirements Inspection | [`EVID-E17`](evidence_index.md#5-docsevidence-artifact-index) | **GAP** |
| **SYS-013** | Route-preferred Strategy<br>(Route-assisted Navigation Preference) | **S6 Navigation** | [`nav2_params.yaml`](../../src/mobile_base_navigation/config/nav2_params.yaml)<br>[`route_assisted_nav.xml`](../../src/mobile_base_navigation/behavior_trees/route_assisted_nav.xml)<br>[`site_resolution.py`](../../src/mobile_base_bringup/launch/site_resolution.py) | Automated BT Runtime Test & Hardware Autonomous Run | [`EVID-E11`](evidence_index.md#5-docsevidence-artifact-index), [`EVID-E03`](evidence_index.md#5-docsevidence-artifact-index) | **HISTORICALLY VERIFIED** |
| **SYS-014** | 障礙物避讓<br>(Costmap Obstacle Avoidance & Collision Stop) | **S6 Navigation** | [`nav2_params.yaml`](../../src/mobile_base_navigation/config/nav2_params.yaml)<br>[`route_assisted_nav.xml`](../../src/mobile_base_navigation/behavior_trees/route_assisted_nav.xml) | Hardware Static Safety Test & Multi-Source Costmap Verification | [`EVID-E11`](evidence_index.md#5-docsevidence-artifact-index), [`EVID-E14`](evidence_index.md#5-docsevidence-artifact-index), [`EVID-E03`](evidence_index.md#5-docsevidence-artifact-index) | **HISTORICALLY VERIFIED** |
| **SYS-015** | 路徑追蹤<br>(FollowPath Controller & Progress Check) | **S6 Navigation** | [`nav2_params.yaml`](../../src/mobile_base_navigation/config/nav2_params.yaml)<br>[`route_assisted_nav.xml`](../../src/mobile_base_navigation/behavior_trees/route_assisted_nav.xml) | Hardware Autonomous Navigation & Progress Checker Telemetry | [`EVID-E11`](evidence_index.md#5-docsevidence-artifact-index), [`EVID-E03`](evidence_index.md#5-docsevidence-artifact-index) | **PARTIAL** |
| **SYS-016** | 到站判定<br>(StoppedGoalChecker Acceptance) | **S6 Navigation** | [`nav2_params.yaml`](../../src/mobile_base_navigation/config/nav2_params.yaml) | Hardware Autonomous Navigation Acceptance Run | [`EVID-E11`](evidence_index.md#5-docsevidence-artifact-index), [`EVID-E09`](evidence_index.md#5-docsevidence-artifact-index) | **HISTORICALLY VERIFIED** |
| **SYS-017** | 導航結果<br>(Standard Navigation Result Reporting) | **S6 Navigation** | [`navigate_to_station_app.cpp`](../../src/mobile_base_navigation/src/navigate_to_station_app.cpp)<br>[`navigate_to_station_app.hpp`](../../src/mobile_base_navigation/src/navigate_to_station_app.hpp) | Automated Unit Test & Hardware Execution | [`EVID-E11`](evidence_index.md#5-docsevidence-artifact-index), [`EVID-E03`](evidence_index.md#5-docsevidence-artifact-index) | **HISTORICALLY VERIFIED** |
| **SYS-018** | First Mile<br>(First Mile Stage Orchestration) | **S6 Navigation** | [`route_assisted_nav.xml`](../../src/mobile_base_navigation/behavior_trees/route_assisted_nav.xml)<br>[`nav2_params.yaml`](../../src/mobile_base_navigation/config/nav2_params.yaml) | Automated Behavior Tree Test & Hardware Autonomous Run | [`EVID-E11`](evidence_index.md#5-docsevidence-artifact-index), [`EVID-E03`](evidence_index.md#5-docsevidence-artifact-index) | **HISTORICALLY VERIFIED** |
| **SYS-019** | On Route Navigation<br>(On Route Stage Orchestration) | **S6 Navigation** | [`route_assisted_nav.xml`](../../src/mobile_base_navigation/behavior_trees/route_assisted_nav.xml)<br>[`nav2_params.yaml`](../../src/mobile_base_navigation/config/nav2_params.yaml) | Automated Behavior Tree Test & Hardware Autonomous Run | [`EVID-E11`](evidence_index.md#5-docsevidence-artifact-index), [`EVID-E03`](evidence_index.md#5-docsevidence-artifact-index) | **HISTORICALLY VERIFIED** |
| **SYS-020** | Last Mile<br>(Last Mile Stage Orchestration) | **S6 Navigation** | [`route_assisted_nav.xml`](../../src/mobile_base_navigation/behavior_trees/route_assisted_nav.xml)<br>[`nav2_params.yaml`](../../src/mobile_base_navigation/config/nav2_params.yaml) | Automated Behavior Tree Test & Hardware Autonomous Run | [`EVID-E11`](evidence_index.md#5-docsevidence-artifact-index), [`EVID-E03`](evidence_index.md#5-docsevidence-artifact-index) | **HISTORICALLY VERIFIED** |
| **SYS-021** | Reserved Fallback Boundary<br>(Free-space Fallback Disallowance) | **S6 Navigation** | [`route_assisted_nav.xml`](../../src/mobile_base_navigation/behavior_trees/route_assisted_nav.xml) | Automated Behavior Tree Logic Test & Config Inspection | [`EVID-E03`](evidence_index.md#5-docsevidence-artifact-index) | **HISTORICALLY VERIFIED** |
| **SYS-022** | 底盤運動控制<br>(Differential Drive Closed-Loop Control) | **S7 Base Control** | [`base_control_params.yaml`](../../src/mobile_base_control/config/base_control_params.yaml)<br>[`base_control.launch.py`](../../src/mobile_base_control/launch/base_control.launch.py)<br>[`m1_hardware.cpp`](../../src/mobile_base_control/src/m1_hardware.cpp)<br>[`m1_driver.cpp`](../../src/mobile_base_control/src/m1_driver.cpp) | Hardware Telemetry & Ground Motion Testing | [`EVID-E07`](evidence_index.md#5-docsevidence-artifact-index), [`EVID-E08`](evidence_index.md#5-docsevidence-artifact-index), [`RAW-008-11`](evidence_index.md#imp-008-s7-m1hardware-ros2_control-integration-18-files), [`RAW-015-13`](evidence_index.md#imp-015-s7-manual-teleop-base-control-physical-motion-22-files), [`RAW-015-14`](evidence_index.md#imp-015-s7-manual-teleop-base-control-physical-motion-22-files), [`RAW-015-15`](evidence_index.md#imp-015-s7-manual-teleop-base-control-physical-motion-22-files) | **HISTORICALLY VERIFIED** |
| **SYS-023** | 機器人描述<br>(Kinematic Geometry & Static TF Tree) | **S1 Robot Description** | [`robot_state_publisher.yaml`](../../src/mobile_base_description/config/robot_state_publisher.yaml)<br>[`robot_description.launch.py`](../../src/mobile_base_description/launch/robot_description.launch.py)<br>[`test_urdf_syntax.py`](../../src/mobile_base_description/test/test_urdf_syntax.py) | Static Inspection & URDF Syntax Automated Tests | [`EVID-E06`](evidence_index.md#5-docsevidence-artifact-index), [`RAW-009-01`](evidence_index.md#imp-009-s1-robot-description-geometry-3-files), [`RAW-009-02`](evidence_index.md#imp-009-s1-robot-description-geometry-3-files), [`RAW-009-03`](evidence_index.md#imp-009-s1-robot-description-geometry-3-files) | **HISTORICALLY VERIFIED** |
| **SYS-024** | Map Package Read-back<br>(MapIO Deserialization Verification) | **S4 Mapping** | [`save_map.sh`](../../src/mobile_base_bringup/scripts/save_map.sh)<br>[`test_map_io_readback.cpp`](../../src/mobile_base_mapping/test/test_map_io_readback.cpp)<br>[`validate_map_readback.cpp`](../../src/mobile_base_mapping/test/validate_map_readback.cpp) | Hardware Execution & Automated Read-back Verification | [`RAW-014-03`](evidence_index.md#imp-014-s4-mapping-mapio-integration-3-files), [`RAW-014-01`](evidence_index.md#imp-014-s4-mapping-mapio-integration-3-files), [`EVID-E03`](evidence_index.md#5-docsevidence-artifact-index) | **HISTORICALLY VERIFIED** |
| **SYS-025** | 導航取消<br>(Action Goal Cancellation Response) | **S6 Navigation** | [`navigate_to_station_app.cpp`](../../src/mobile_base_navigation/src/navigate_to_station_app.cpp)<br>[`route_assisted_nav.xml`](../../src/mobile_base_navigation/behavior_trees/route_assisted_nav.xml) | Automated Action Client Integration Test | [`EVID-E03`](evidence_index.md#5-docsevidence-artifact-index), [`EVID-E16`](evidence_index.md#5-docsevidence-artifact-index) | **HISTORICALLY VERIFIED** |
| **SYS-026** | 底盤故障處理<br>(Hardware Interface ERROR Propagation) | **S7 Base Control** | [`m1_hardware.cpp`](../../src/mobile_base_control/src/m1_hardware.cpp)<br>[`m1_driver.cpp`](../../src/mobile_base_control/src/m1_driver.cpp)<br>[`test_m1_hardware.cpp`](../../src/mobile_base_control/test/test_m1_hardware.cpp) | Automated Unit Test & Hardware Interface Inspection | [`RAW-008-01`](evidence_index.md#imp-008-s7-m1hardware-ros2_control-integration-18-files), [`RAW-007-03`](evidence_index.md#imp-007-s7-m1driver-transport-vertical-slice-13-files), [`EVID-E03`](evidence_index.md#5-docsevidence-artifact-index) | **HISTORICALLY VERIFIED** |
| **SYS-027** | 運動命令逾時<br>(Command Timeout & Stale Velocity Stop) | **S7 Base Control** | [`base_control_params.yaml`](../../src/mobile_base_control/config/base_control_params.yaml)<br>[`base_control.launch.py`](../../src/mobile_base_control/launch/base_control.launch.py) | Hardware Ground Execution & Timing Telemetry Analysis | [`RAW-015-16`](evidence_index.md#imp-015-s7-manual-teleop-base-control-physical-motion-22-files), [`RAW-015-05`](evidence_index.md#imp-015-s7-manual-teleop-base-control-physical-motion-22-files), [`EVID-E03`](evidence_index.md#5-docsevidence-artifact-index) | **HISTORICALLY VERIFIED** |
| **SYS-028** | 底盤運動限制<br>(Velocity & Acceleration Clamping) | **S7 Base Control** | [`base_control_params.yaml`](../../src/mobile_base_control/config/base_control_params.yaml) | Config Inspection & Hardware Controlled Motion Telemetry | [`EVID-E08`](evidence_index.md#5-docsevidence-artifact-index), [`RAW-008-04`](evidence_index.md#imp-008-s7-m1hardware-ros2_control-integration-18-files), [`RAW-015-10`](evidence_index.md#imp-015-s7-manual-teleop-base-control-physical-motion-22-files), [`RAW-015-11`](evidence_index.md#imp-015-s7-manual-teleop-base-control-physical-motion-22-files) | **HISTORICALLY VERIFIED** |
| **SYS-029** | 底盤狀態回授<br>(Measured Encoder Feedback Validation) | **S7 Base Control** | [`m1_hardware.cpp`](../../src/mobile_base_control/src/m1_hardware.cpp)<br>[`m1_driver.cpp`](../../src/mobile_base_control/src/m1_driver.cpp) | Hardware Dynamic Telemetry & Raw CSV Dataset Inspection | [`RAW-008-11`](evidence_index.md#imp-008-s7-m1hardware-ros2_control-integration-18-files), [`RAW-008-14`](evidence_index.md#imp-008-s7-m1hardware-ros2_control-integration-18-files), [`RAW-008-17`](evidence_index.md#imp-008-s7-m1hardware-ros2_control-integration-18-files), [`RAW-008-10`](evidence_index.md#imp-008-s7-m1hardware-ros2_control-integration-18-files), [`EVID-E06`](evidence_index.md#5-docsevidence-artifact-index) | **HISTORICALLY VERIFIED** |
| **SYS-030** | 底盤安全啟停<br>(Safe Enable, Stop, & Disable Sequencing) | **S7 Base Control** | [`m1_hardware.cpp`](../../src/mobile_base_control/src/m1_hardware.cpp)<br>[`m1_driver.cpp`](../../src/mobile_base_control/src/m1_driver.cpp) | Hardware Execution & Sequence Verification | [`RAW-007-11`](evidence_index.md#imp-007-s7-m1driver-transport-vertical-slice-13-files), [`RAW-007-12`](evidence_index.md#imp-007-s7-m1driver-transport-vertical-slice-13-files), [`RAW-007-13`](evidence_index.md#imp-007-s7-m1driver-transport-vertical-slice-13-files), [`RAW-015-08`](evidence_index.md#imp-015-s7-manual-teleop-base-control-physical-motion-22-files), [`RAW-015-09`](evidence_index.md#imp-015-s7-manual-teleop-base-control-physical-motion-22-files) | **HISTORICALLY VERIFIED** |
| **SYS-031** | Unallocated Requirement ID<br>(Omitted in Baseline) | **Unallocated** | *None (Requirement ID allocation gap — not an implementation/functionality gap)* | Static Documentation & Requirements Inspection | [`EVID-E17`](evidence_index.md#5-docsevidence-artifact-index) | **GAP** |
| **SYS-032** | Station Target Resolution<br>(Station Catalog Lookup & Pose Resolution) | **S6 Navigation** | [`target_admission.cpp`](../../src/mobile_base_navigation/src/target_admission.cpp)<br>[`navigate_to_station_app.cpp`](../../src/mobile_base_navigation/src/navigate_to_station_app.cpp)<br>[`target_admission.hpp`](../../src/mobile_base_navigation/include/mobile_base_navigation/target_admission.hpp) | Automated Unit Test & Hardware Resolution Execution | [`EVID-E11`](evidence_index.md#5-docsevidence-artifact-index), [`EVID-E03`](evidence_index.md#5-docsevidence-artifact-index) | **HISTORICALLY VERIFIED** |
| **SYS-033** | Canonical Goal Validation<br>(Pose Finiteness, Quaternion & Frame Validation) | **S6 Navigation** | [`target_admission.cpp`](../../src/mobile_base_navigation/src/target_admission.cpp)<br>[`target_admission.hpp`](../../src/mobile_base_navigation/include/mobile_base_navigation/target_admission.hpp) | Automated Unit Test & Parameter Validation Suite | [`EVID-E03`](evidence_index.md#5-docsevidence-artifact-index) | **HISTORICALLY VERIFIED** |
| **SYS-034** | 手動移動控制<br>(Mapping Mode Teleop Velocity Input) | **S7 Base Control** | [`base_control_params.yaml`](../../src/mobile_base_control/config/base_control_params.yaml)<br>[`mapping.launch.py`](../../src/mobile_base_bringup/launch/mapping.launch.py)<br>[`base_control.launch.py`](../../src/mobile_base_control/launch/base_control.launch.py) | Hardware Ground Execution & Teleoperation Integration Test | [`RAW-015-13`](evidence_index.md#imp-015-s7-manual-teleop-base-control-physical-motion-22-files), [`RAW-015-01`](evidence_index.md#imp-015-s7-manual-teleop-base-control-physical-motion-22-files), [`RAW-015-03`](evidence_index.md#imp-015-s7-manual-teleop-base-control-physical-motion-22-files), [`EVID-E03`](evidence_index.md#5-docsevidence-artifact-index) | **HISTORICALLY VERIFIED** |

---

## 4. Subsystem Allocation Breakdown

The 34 requirement IDs are allocated across the system architecture as follows:

| Subsystem ID | Subsystem Name | Allocated Requirements | Total Count |
|---|---|---|---|
| **S1** | **Robot Description** | SYS-023 | 1 |
| **S2** | **Perception** | SYS-003, SYS-004 | 2 |
| **S3** | **State Estimation** | SYS-005 | 1 |
| **S4** | **Mapping** | SYS-001, SYS-002, SYS-006, SYS-024 | 4 |
| **S5** | **Localization** | SYS-007, SYS-010 | 2 |
| **S6** | **Navigation** | SYS-008, SYS-009, SYS-011, SYS-013, SYS-014, SYS-015, SYS-016, SYS-017, SYS-018, SYS-019, SYS-020, SYS-021, SYS-025, SYS-032, SYS-033 | 15 |
| **S7** | **Base Control** | SYS-022, SYS-026, SYS-027, SYS-028, SYS-029, SYS-030, SYS-034 | 7 |
| **Unallocated** | *Requirement ID Allocation Gaps (Not functional gaps)* | SYS-012, SYS-031 | 2 |
| **Total** | | | **34** |

---

## 5. Verification Status Distribution & Metrics

```text
┌────────────────────────────────────────────────────────┐
│        SYS Requirement Verification Status Summary     │
├────────────────────────────────────────┬───────────────┤
│ Status Classification                  │ Count (Total) │
├────────────────────────────────────────┼───────────────┤
│ CURRENT VERIFIED                       │       0       │
│ HISTORICALLY VERIFIED                  │      31       │
│ IMPLEMENTED / NOT RE-VERIFIED          │       0       │
│ PARTIAL                                │       1       │
│ GAP (Requirement ID Allocation Gap)    │       2       │
│ UNKNOWN / INSUFFICIENT EVIDENCE        │       0       │
├────────────────────────────────────────┼───────────────┤
│ Total SYS Requirement IDs Accounted    │      34       │
└────────────────────────────────────────┴───────────────┘
```

* **Normatively Defined Requirements in Baseline:** 32 requirements (SYS-001~011, SYS-013~030, SYS-032~034).
* **Historically Verified Rate:** $31 / 32 = 96.9\%$ of normatively defined requirements have authoritative historical verification evidence.
* **Partial Verification Rate:** $1 / 32 = 3.1\%$ (SYS-015 due to Known Limitation B).
* **Requirement ID Allocation Gaps:** 2 IDs (SYS-012, SYS-031) are requirement ID allocation gaps that were unallocated/omitted from [`03_REQUIREMENTS.md`](../03_REQUIREMENTS.md). They do not represent functional defects or missing capabilities in the system.

---

## 6. Non-Standard Status Detailed Analysis

### 6.1 PARTIAL Status: SYS-015 (Path Tracking)
* **Requirement:** 系統應透過 Navigation2 `FollowPath` 控制 AMR 追蹤目前 active navigation stage 的有效路徑，並使用設定的 controller 與 progress checker 判定能否繼續追蹤。
* **Observed Verification Evidence:**
  - Forward navigation from Station A $\rightarrow$ Station B succeeded on physical AMR ([`phase_r5_resume_final_acceptance_report.txt`](../evidence/phase_r5_resume_final_acceptance_report.txt), `NAV_SUCCEEDED`, position error 0.045 m $\le 0.25$ m tolerance).
  - Return navigation from Station B $\rightarrow$ Station A encountered a progress checker timeout (`error_code=105`) at coordinate $y = -0.175\,\text{m}$ (0.42 m remaining to Station A).
* **Rationale for PARTIAL Classification:**
  The path tracking functionality is fully implemented and historically verified in the forward direction. The progress failure abort/stop mechanism was also verified on physical hardware when the timeout occurred. However, because return-path tracking was interrupted before reaching the destination, full bidirectional path tracking verification to destination remains incomplete (**Known Limitation B**). Per the Authority Model and Migration Plan, this bounded behavior does not block the MVP baseline, but prohibits a full `HISTORICALLY VERIFIED` claim for the complete bidirectional path traversal.

### 6.2 GAP Status: SYS-012 (Requirement ID Allocation Gap)
* **Requirement:** Not defined in [`03_REQUIREMENTS.md`](../03_REQUIREMENTS.md).
* **Context:** Audited in [`v0.1.0_as_built_as_verified_baseline.txt`](../evidence/v0.1.0_as_built_as_verified_baseline.txt) (line 567); the requirement numbering sequence skipped `SYS-012`.
* **Rationale for GAP Classification:** Maintained as an explicit row to satisfy full 34-item matrix accounting. This is strictly a **Requirement ID allocation gap** and does not represent an implementation, software, or functional gap in `mobile_base`.

### 6.3 GAP Status: SYS-031 (Requirement ID Allocation Gap)
* **Requirement:** Not defined in [`03_REQUIREMENTS.md`](../03_REQUIREMENTS.md).
* **Context:** Audited in [`v0.1.0_as_built_as_verified_baseline.txt`](../evidence/v0.1.0_as_built_as_verified_baseline.txt) (line 567); historically referenced in exploratory research notes but omitted from the normative baseline.
* **Rationale for GAP Classification:** Maintained as an explicit row to satisfy full 34-item matrix accounting. This is strictly a **Requirement ID allocation gap** and does not represent an implementation, software, or functional gap in `mobile_base`.

---

## 7. Integrity & Maintenance Rules

1. **Bidirectional Linkage:** Every defined requirement must map to at least one implementation file and at least one evidence entry in [`evidence_index.md`](evidence_index.md).
2. **No Fabricated Evidence:** Cells in this matrix must cite committed, physical artifacts. Narrative claims without artifact backing are prohibited.
3. **No Unqualified HEAD Claims:** Verification claims on current `HEAD` require live test execution under active CI or real hardware testing. Historical evidence remains labeled `HISTORICALLY VERIFIED`.
4. **Change Management:** Any modification to requirement definitions in [`03_REQUIREMENTS.md`](../03_REQUIREMENTS.md) or architectural responsibilities in [`04_SYSTEMS.md`](../04_SYSTEMS.md) requires a synchronized update to this matrix.

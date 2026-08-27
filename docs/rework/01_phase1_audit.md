# Phase 1 Accepted Audit Baseline

## 1. Scope and Method

* **Audit Mode:** Phase 1 and Phase 1B were conducted as strict READ-ONLY repository audits on branch `main` at baseline commit `e1e0397`.
* **Evidence Priority:**
  1. Production source code, launch files, parameter YAMLs, URDF/Xacro, and Behavior Tree definitions.
  2. Executable automated test implementations (`src/*/test/`).
  3. Committed runtime and hardware verification evidence (`docs/verification/`, `docs/evidence/`).
  4. Current normative requirements and design documentation (`docs/01_use_cases.md` ~ `docs/03_requirements.md`, `docs/05_architecture.md`).
  5. Historical handoff notes, research documents, and superseded implementation narratives (`docs/handoff/`, `docs/research/`, `docs/04_reuse_assessment.md`, `docs/07_implementation.md`).
* **Audit Boundaries:** The audit inspected the complete repository without modifying source files, rewriting documentation, deleting evidence, changing configurations, re-running physical hardware tests, or creating Git commits.

---

## 2. Confirmed As-Built Facts

### Base Control
* Chassis motion control is implemented via `mobile_base_control` integrating `M1Hardware` (`hardware_interface::SystemInterface`) and `M1Driver` over RS-485 Modbus RTU.
* `ros2_control` executes `joint_state_broadcaster` and `diff_drive_controller` (controlling `driving_wheel_joint_L` and `driving_wheel_joint_R`).
* `diff_drive_controller` provides wheel odometry (`/diff_drive_controller/odom`, TF publication disabled: `enable_odom_tf: false`) and accepts the final velocity command (`/diff_drive_controller/cmd_vel`, `geometry_msgs/msg/TwistStamped`).
* Detailed communication, kinematic limits, and safety watchdog parameters are defined in [`base_control_params.yaml`](file:///home/zzz/mobile_base/src/mobile_base_control/config/base_control_params.yaml).
* *Supporting Paths:* [`src/mobile_base_control/src/m1_hardware.cpp`](file:///home/zzz/mobile_base/src/mobile_base_control/src/m1_hardware.cpp), [`src/mobile_base_control/src/m1_driver.cpp`](file:///home/zzz/mobile_base/src/mobile_base_control/src/m1_driver.cpp), [`src/mobile_base_control/config/base_control_params.yaml`](file:///home/zzz/mobile_base/src/mobile_base_control/config/base_control_params.yaml), [`src/mobile_base_control/launch/base_control.launch.py`](file:///home/zzz/mobile_base/src/mobile_base_control/launch/base_control.launch.py).

### Perception
* Dual SICK picoScan150 2D LiDARs operate independently via `sick_scan_xd`: Front-Left publishes `/scan_front`, Rear-Right publishes `/scan_rear`.
* TDK IIM-42652 6-DoF IMU operates via `tdk_ros2_imu` publishing raw IMU telemetry to `/imu/data_raw`.
* `dual_laser_merger` and the unified `/scan` topic were decommissioned; downstream consumers subscribe directly to raw scan topics.
* *Supporting Paths:* [`src/mobile_base_perception/launch/sick_dual_lidar.launch.py`](file:///home/zzz/mobile_base/src/mobile_base_perception/launch/sick_dual_lidar.launch.py), [`src/mobile_base_perception/launch/tdk_imu.launch.py`](file:///home/zzz/mobile_base/src/mobile_base_perception/launch/tdk_imu.launch.py), [`src/mobile_base_perception/config/tdk_imu.yaml`](file:///home/zzz/mobile_base/src/mobile_base_perception/config/tdk_imu.yaml), [`src/tdk_ros2_imu/tdk_ros2_imu/tdk_imu_node.py`](file:///home/zzz/mobile_base/src/tdk_ros2_imu/tdk_ros2_imu/tdk_imu_node.py).

### State Estimation
* `kinematic_icp_ros` consumes `/scan_front` and wheel odometry prior buffer `/diff_drive_controller/odom`, publishing planar laser odometry to `/lidar_odometry` (`publish_odom_tf: false`).
* `robot_localization` EKF (`ekf_filter_node`) fuses planar pose $(x, y, \text{yaw})$ from `/lidar_odometry` and angular velocity yaw rate from `/imu/data_raw`.
* EKF is the SOLE dynamic publisher and authority of the `odom -> base_footprint` TF transform.
* *Supporting Paths:* [`src/kinematic_icp/ros/config/kinematic_icp_ros.yaml`](file:///home/zzz/mobile_base/src/kinematic_icp/ros/config/kinematic_icp_ros.yaml), [`src/mobile_base_state_estimation/config/ekf.yaml`](file:///home/zzz/mobile_base/src/mobile_base_state_estimation/config/ekf.yaml), [`src/mobile_base_state_estimation/launch/ekf.launch.py`](file:///home/zzz/mobile_base/src/mobile_base_state_estimation/launch/ekf.launch.py).

### Mapping
* Mapping mode runs `async_slam_toolbox_node` consuming `/scan_front` and dynamic TF `odom -> base_footprint`.
* `slam_toolbox` is the SOLE authority for `map -> odom` TF in Mapping Mode (`transform_publish_period: 0.05`).
* Manual teleoperation during mapping uses external `teleop_twist_keyboard` publishing `TwistStamped` to `/diff_drive_controller/cmd_vel`.
* Map saving uses `scripts/save_map.sh` (wrapping Nav2 `map_saver_cli`) exporting timestamped `.pgm` and `.yaml`, validated by `validate_map_readback`.
* *Supporting Paths:* [`src/mobile_base_mapping/config/slam_toolbox.yaml`](file:///home/zzz/mobile_base/src/mobile_base_mapping/config/slam_toolbox.yaml), [`src/mobile_base_bringup/launch/mapping.launch.py`](file:///home/zzz/mobile_base/src/mobile_base_bringup/launch/mapping.launch.py), [`src/mobile_base_bringup/scripts/save_map.sh`](file:///home/zzz/mobile_base/src/mobile_base_bringup/scripts/save_map.sh).

### Localization
* Navigation mode launches `map_server` loading `maps/<site>/map.yaml` and publishing `/map`.
* `amcl` consumes `/scan_front`, `/map`, and `/initialpose`, publishing `/amcl_pose`.
* `amcl` is the SOLE authority for `map -> odom` TF in Navigation Mode (`tf_broadcast: true`).
* *Supporting Paths:* [`src/mobile_base_localization/config/amcl_params.yaml`](file:///home/zzz/mobile_base/src/mobile_base_localization/config/amcl_params.yaml), [`src/mobile_base_localization/launch/localization.launch.py`](file:///home/zzz/mobile_base/src/mobile_base_localization/launch/localization.launch.py).

### Navigation
* Managed by Nav2 lifecycle manager (`lifecycle_manager_navigation`).
* `route_server` loads `maps/<site>/route_graph.geojson` and provides topological routing (`ComputeRoute`).
* `bt_navigator` executes the 3-Stage Behavior Tree (`route_assisted_nav.xml`: First Mile -> Route Graph -> Last Mile).
* `planner_server` (Navfn `GridBased`) computes First Mile and Last Mile connecting paths.
* `controller_server` (MPPI `FollowPath` + `stopped_goal_checker`) tracks active stage paths and outputs `/cmd_vel_nav` (`TwistStamped`).
* Nav2 `local_costmap` and `global_costmap` directly consume independent observation sources `scan_front` and `scan_rear`.
* `collision_monitor` intercepts `/cmd_vel_nav`, monitors `scan_front` and `scan_rear` against configured slowdown and stop polygons, and outputs `/cmd_vel` remapped to `/diff_drive_controller/cmd_vel`.
* Detailed controller tuning, costmap layers, and polygon definitions are maintained in [`nav2_params.yaml`](file:///home/zzz/mobile_base/src/mobile_base_navigation/config/nav2_params.yaml).
* *Supporting Paths:* [`src/mobile_base_navigation/config/nav2_params.yaml`](file:///home/zzz/mobile_base/src/mobile_base_navigation/config/nav2_params.yaml), [`src/mobile_base_navigation/behavior_trees/route_assisted_nav.xml`](file:///home/zzz/mobile_base/src/mobile_base_navigation/behavior_trees/route_assisted_nav.xml), [`src/mobile_base_navigation/launch/navigation.launch.py`](file:///home/zzz/mobile_base/src/mobile_base_navigation/launch/navigation.launch.py).

### Station Navigation
* Implemented as a standalone C++ CLI application `navigate_to_station` (`ros2 run mobile_base_navigation navigate_to_station --station <id> --catalog <path>`).
* Uses `TargetAdmission` library to parse `stations.yaml`, resolves Station ID to exact `geometry_msgs/msg/PoseStamped`, normalizes yaw, and validates coordinates and quaternion finiteness.
* Submits native `nav2_msgs/action/NavigateToPose` goals directly to Nav2 `bt_navigator`.
* No custom ROS Action Server or `mobile_base_msgs` package exists in the repository.
* *Supporting Paths:* [`src/mobile_base_navigation/src/navigate_to_station_app.cpp`](file:///home/zzz/mobile_base/src/mobile_base_navigation/src/navigate_to_station_app.cpp), [`src/mobile_base_navigation/src/target_admission.cpp`](file:///home/zzz/mobile_base/src/mobile_base_navigation/src/target_admission.cpp), [`maps/test_site/stations.yaml`](file:///home/zzz/mobile_base/maps/test_site/stations.yaml).

---

## 3. Confirmed Documentation Problems

* **Stale Root Entrypoint (`docs/README.md`):** Still claims CAP-001 and CAP-002 are "未開始" (unstarted), references deleted files (`compose.hardware.yaml`, `docs/implementation/`), and points to renamed `07_backlog.md`.
* **Outdated Subsystem Design (`docs/06_subsystem.md`):** Contains obsolete specifications including a nonexistent `mobile_base_msgs/action/NavigateToStation` action server, outdated goal checker tolerances (e.g. 0.15 m vs 0.25 m), outdated catalog YAML schema (`version`/`namespace`), and direct diff-drive command publication bypassing Collision Monitor.
* **Monolithic Implementation Narrative (`docs/07_implementation.md`):** Combines process rules, implementation notes, superseded RF2O evaluations, and references to 6 test filenames that never existed in Git history (`test_route_server.cpp`, `test_diff_drive_controller.cpp`, etc.).
* **Duplication Across Documents:** Architecture summaries, TF ownership rules, M1 protocol details, and requirement matrices are duplicated across 03, 04, 05, 06, 07, bringup guides, and design baselines.
* **Misleading Historical Context:** 32 research notes (`docs/research/`) and 5 session handoff transcripts (`docs/handoff/`) contain time-bound instructions (e.g. "ignore navigation docs") that mislead AI agents and human readers.

---

## 4. Confirmed Evidence State

* **Strong / Primary Historical Runtime Evidence:**
  * Raw CSVs, timing logs, and hardware motion measurements in `docs/verification/IMP-007` ~ `IMP-015`.
  * Phase runtime reports in `docs/evidence/` that directly support current as-built behavior: `phase_r1_runtime_closure_report.txt`, `phase_r2_hardware_static_preflight_report.txt`, `phase_r3_controlled_motion_characterization_report.txt`, `phase_r3_5_forward_motion_yaw_sanity_report.txt`, `phase_r5_resume_final_acceptance_report.txt`, `scan_decoupling_report.txt`, `launch_entry_optimization_report.txt`.
* **Supporting Evidence:**
  * Committed automated test source implementations under `src/*/test/`.
  * Test-site assets under `maps/test_site/` (`map.yaml`, `stations.yaml`, `route_graph.geojson`).
* **Secondary / Narrative Evidence:**
  * Narrative claims in `07_implementation.md` for later items (IMP-016 ~ IMP-027) where dedicated raw log files were not committed to `docs/verification/`.
* **Historical / Obsolete:**
  * Research notes (`docs/research/`, 32 files) and session handoffs (`docs/handoff/`, 5 files).
  * Superseded candidate evaluations (RF2O, `dual_laser_merger`) in `04_reuse_assessment.md`.
  * Obsolete filter reports (`phase_cm_f1_collision_scan_self_filter_report.txt`).
  * Empty directories containing only `.gitkeep` (`docs/verification/IMP-016` ~ `IMP-027`).
* **Qualification on Test Count:**
  * `515 tests PASS` is a **historically recorded test result** in `launch_entry_optimization_report.txt` (commit `8ab06d9`). In accordance with read-only audit rules, test suites were not re-run during Phase 1/1B, and this figure is not a current live-run verification claim.

---

## 5. Known Limitation

* **Symptom:** During return navigation (Station B -> Station A), Nav2 controller progress timeout (`error_code=105`) occurred at $y = -0.175\,\text{m}$ (0.42 m from Station A) as recorded in `phase_r5_resume_final_acceptance_report.txt`.
* **Root Cause:** `undetermined` (no speculative causes shall be asserted without fresh hardware execution and bag logs).
* **Classification:** `B — Known limitation`.

---

## 6. MVP Closure Status

* **Status:** `A-class MVP blocker: None found during Phase 1 audit.`
* **Supporting Rationale:**
  1. *Implementation exists:* Complete 7-subsystem pipeline is implemented in code, launch files, parameter configurations, URDF, and Behavior Trees.
  2. *Automated test sources exist:* Unit and integration test suites exist across all 10 packages in `src/`.
  3. *Historical mapping runtime evidence exists:* End-to-end mapping, SLAM, TF broadcasting, and map saving/readback are documented in Phase R1 and launch optimization reports.
  4. *Historical Station A -> B navigation evidence exists:* `NAV_SUCCEEDED` (exit code 0, position error 0.045 m $\le 0.25$ m tolerance, zero final velocity) is documented in Phase R5 report.
  5. *Historical Unknown Station rejection evidence exists:* `RESOLUTION_FAILED` (exit code 3, zero motion command) is documented in Phase R5 report.

---

## 7. Open / Deferred Decisions

The following decisions are intentionally deferred to subsequent documentation convergence phases:
* Exact target archive directory layout (`docs/archive/` structure).
* Final disposition of empty directories `docs/verification/IMP-016` ~ `IMP-027`.
* `07_implementation.md` rewrite vs archive + replace strategy.
* Final placement of `src/mobile_base_bringup/MAPPING.md` and `NAVIGATION.md` (retain in package vs consolidate in `docs/`).
* Exact target documentation filenames and cross-document link mapping.
* Evidence file relocation or consolidation.
* *Status:* `Deferred to later phases.`

---

## 8. Phase 1 Exit Condition

* Phase 1 and Phase 1B successfully established the accepted as-built reality, verified evidence boundaries, and cataloged documentation discrepancies.
* No A-class blocker was identified; navigation and MPPI debugging remain closed.
* The repository baseline is confirmed ready to proceed to Phase 2 documentation convergence.

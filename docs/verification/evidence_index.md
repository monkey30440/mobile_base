# Verification Evidence Index

## 1. Purpose

This document serves as the **canonical catalog and classification index** for all committed verification artifacts, runtime logs, telemetry datasets, hardware test records, and investigative reports within the `mobile_base` repository.

> [!IMPORTANT]
> **Authority and Verification Boundaries:**
> * This document is an **evidence catalog and classification index**, not a normative requirement authority. Normative system requirements remain defined in [`03_REQUIREMENTS.md`](file:///home/jim/mobile_base/docs/03_REQUIREMENTS.md).
> * This document is not an as-built configuration source; active runtime parameters and topics reside in source code and configuration YAMLs.
> * Historical records (e.g., test suite pass logs or hardware acceptance runs) reflect execution at their respective historical baseline commits. They do **not** constitute a live test claim on the current `HEAD` commit (`8f8ea23`). No automated or physical tests were re-executed during the creation of this index.
> * Raw evidence artifacts are immutable historical records; they are cataloged and classified in place without modification, relocation, or deletion.

---

## 2. Evidence Status Semantics

Every artifact in this index is individually evaluated and assigned one of the following authoritative status classifications:

| Status Classification | Definition & Usage Boundary |
|---|---|
| **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Historical execution record generated on physical hardware or runtime environments that directly supports the current as-built architecture and accepted MVP baseline. Remains valid historical proof, but does not imply that the current `HEAD` has been re-executed. |
| **HISTORICAL** | Valid historical baseline, preflight, unit/integration test, or construction record reflecting a specific development milestone. Retained for traceability, but should not be cited as direct verification of current `HEAD` without qualification. |
| **SUPERSEDED** | Valid historical artifact whose verified component, data path, or algorithm has been formally replaced or decommissioned by subsequent architectural refactoring (e.g., RF2O laser odometry, merged `/scan` topic, intermediate collision scan filter). |
| **INVESTIGATION-ONLY** | Investigative study, architectural trade-off analysis, read-only repository audit, prompt template, or deployment guide. Provides design context and rationale, but does not constitute runtime verification proof. |
| **OBSOLETE / INVALID** | Artifact whose technical premise is invalid or completely inapplicable to the system. Used with extreme caution; older valid records remain `HISTORICAL` rather than `OBSOLETE`. |
| **EMPTY PLACEHOLDER** | Directory placeholder (`.gitkeep`) with no committed raw verification artifacts. Does not constitute evidence. |

---

## 3. Evidence Collection Boundaries

Verification evidence in the `mobile_base` repository is organized across three primary boundaries:

1. **Phase & Architecture Evidence Reports ([`docs/evidence/`](file:///home/jim/mobile_base/docs/evidence/)):** 11 structured technical reports covering runtime closures, hardware preflight, controlled motion characterization, scan decoupling, launch entry optimization, and baseline investigations.
2. **Raw Implementation Artifacts ([`docs/verification/`](file:///home/jim/mobile_base/docs/verification/)):** 69 raw execution logs, telemetry CSV datasets, and validation scripts under [`IMP-007`](file:///home/jim/mobile_base/docs/verification/IMP-007/) through [`IMP-015`](file:///home/jim/mobile_base/docs/verification/IMP-015/).
3. **Historical Automated-Test Records:** Repository records documenting the expansion and pass status of the automated test suite across milestones (425 → 508 → 505 → 515 tests).
4. **Historical Pre-IMP Logs (`docs/m1_bringup_validation/logs/manual/`):** Low-level Modbus register exploration logs collected prior to the formal IMP verification convention.

All evidence files remain strictly in their current filesystem locations. No files are renamed, moved, or deleted in this batch.

---

## 4. High-Value Runtime Evidence Summary

The following key runtime verification findings are documented in the indexed artifacts:

* **M1 Motor Control & Physical Motion:**
  - RS-485 Modbus RTU communication at 230400 bps, 30 Hz control loop timing, and raw latency measurements (< 10 ms cycle) are proven with raw CSV datasets in [`IMP-008`](file:///home/jim/mobile_base/docs/verification/IMP-008/) ([`2026-08-18T135214_m1_full_loop_30hz_raw.csv`](file:///home/jim/mobile_base/docs/verification/IMP-008/2026-08-18T135214_m1_full_loop_30hz_raw.csv)) and [`IMP-007`](file:///home/jim/mobile_base/docs/verification/IMP-007/).
  - Real hardware preflight, exact hardware device identities (FTDI FT232R serial `BG03E9MD`, STM32 IMU serial `2063328E4842`, SICK LiDARs `192.168.0.1`/`192.168.0.2`), and controlled motion characterization are established in [`phase_r2_hardware_static_preflight_report.txt`](file:///home/jim/mobile_base/docs/evidence/phase_r2_hardware_static_preflight_report.txt) and [`phase_r3_controlled_motion_characterization_report.txt`](file:///home/jim/mobile_base/docs/evidence/phase_r3_controlled_motion_characterization_report.txt).
  - Forward-motion kinematic sign convention and yaw stability are validated in [`phase_r3_5_forward_motion_yaw_sanity_report.txt`](file:///home/jim/mobile_base/docs/evidence/phase_r3_5_forward_motion_yaw_sanity_report.txt).
  - Real-ground forward displacement, reverse motion, CCW rotation, and stale-command timeout stops (SYS-027) are validated on physical hardware in [`IMP-015`](file:///home/jim/mobile_base/docs/verification/IMP-015/) ([`2026-08-20T094000_hw_stage_g1_ground_forward_active_stop_mapping.txt`](file:///home/jim/mobile_base/docs/verification/IMP-015/2026-08-20T094000_hw_stage_g1_ground_forward_active_stop_mapping.txt) ~ [`2026-08-20T102000_hw_stage_g4_ground_timeout_stop.txt`](file:///home/jim/mobile_base/docs/verification/IMP-015/2026-08-20T102000_hw_stage_g4_ground_timeout_stop.txt)).
* **Dual SICK LiDAR & TDK IMU Acquisition:**
  - Dual SICK picoScan150 independent UDP acquisition (`/scan_front`, `/scan_rear`) is verified in [`IMP-010`](file:///home/jim/mobile_base/docs/verification/IMP-010/) ([`2026-08-18T173400_hw_s2_lidar_dual_acquisition.txt`](file:///home/jim/mobile_base/docs/verification/IMP-010/2026-08-18T173400_hw_s2_lidar_dual_acquisition.txt)).
  - TDK IIM-42652 IMU passive identity, static acquisition, and dynamic angular velocity response (`/imu/data_raw`) are verified in [`IMP-011`](file:///home/jim/mobile_base/docs/verification/IMP-011/) ([`2026-08-19T140200_hw_stage_i3_dynamic_validation.txt`](file:///home/jim/mobile_base/docs/verification/IMP-011/2026-08-19T140200_hw_stage_i3_dynamic_validation.txt)).
* **Kinematic-ICP & EKF State Estimation:**
  - Kinematic-ICP promotion as canonical laser odometry (`/lidar_odometry`), WheelOdometryBuffer contracts, and EKF dynamic TF authority (`odom -> base_footprint`) are verified in [`phase_r1_runtime_closure_report.txt`](file:///home/jim/mobile_base/docs/evidence/phase_r1_runtime_closure_report.txt) and [`IMP-013`](file:///home/jim/mobile_base/docs/verification/IMP-013/) ([`2026-08-19T162000_hw_stage_e2_stationary_ekf.txt`](file:///home/jim/mobile_base/docs/verification/IMP-013/2026-08-19T162000_hw_stage_e2_stationary_ekf.txt)).
* **Mapping & MapIO:**
  - SLAM Toolbox mapping, map saving (`scripts/save_map.sh`), and MapIO read-back round trip validation are verified in [`IMP-014`](file:///home/jim/mobile_base/docs/verification/IMP-014/) ([`2026-08-19T180500_hw_stage_m3_map_save_readback.txt`](file:///home/jim/mobile_base/docs/verification/IMP-014/2026-08-19T180500_hw_stage_m3_map_save_readback.txt)) and [`IMP-015`](file:///home/jim/mobile_base/docs/verification/IMP-015/) Stage G1.
* **Scan Decoupling Architecture:**
  - Removal of `dual_laser_merger` and direct consumption of independent scans (`/scan_front` for SLAM/Kinematic-ICP/AMCL; `scan_front` + `scan_rear` for Costmaps and Collision Monitor) is verified across 505 test items in [`scan_decoupling_report.txt`](file:///home/jim/mobile_base/docs/evidence/scan_decoupling_report.txt).
* **Canonical Public Bringup:**
  - Unified launch entrypoint (`ros2 launch mobile_base_bringup mobile_base.launch.py`) with automatic site resolution is validated on physical hardware and across 515 test items in [`launch_entry_optimization_report.txt`](file:///home/jim/mobile_base/docs/evidence/launch_entry_optimization_report.txt).
* **Autonomous Station Navigation & Acceptance:**
  - Physical execution on real AMR documented in [`phase_r5_resume_final_acceptance_report.txt`](file:///home/jim/mobile_base/docs/evidence/phase_r5_resume_final_acceptance_report.txt):
    * **Static PolygonStop Safety Test:** PASS (0 points inside stop polygon, no false triggers, stationary safety verified).
    * **Station A → Station B (H1):** `NAV_SUCCEEDED` (exit code 0, position error 0.045 m $\le 0.25$ m tolerance, zero final velocity).
    * **Unknown Station Rejection (H3):** `RESOLUTION_FAILED` (exit code 3, zero motion dispatched).
    * **Known Limitation (Station B → Station A Return Navigation, H2):** Progress timeout (`error_code=105`) occurred at $y = -0.175\,\text{m}$ (0.42 m from Station A). Root cause remains undetermined.

---

## 5. `docs/evidence/` Artifact Index

The following table catalogs all 11 surviving files in [`docs/evidence/`](file:///home/jim/mobile_base/docs/evidence/):

| ID | Path | Classification | Evidence Type | Scope | Date / Commit | Current Use | Limitations |
|---|---|---|---|---|---|---|---|
| **EVID-E03** | [`launch_entry_optimization_report.txt`](file:///home/jim/mobile_base/docs/evidence/launch_entry_optimization_report.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Hardware Execution & Verification Report | Canonical public bringup entry (`mobile_base.launch.py`), site resolution (`site_resolution.py`), test suite (515 tests PASS recorded), real AMR bringup | 2026-08-27<br>`8ab06d9` | Authoritative proof for single-entry launch architecture, site resolution, and 515-test historical suite run | Reflects execution at commit `8ab06d9`; does not constitute a live test claim on current `HEAD` |
| **EVID-E05** | [`phase_r1_runtime_closure_report.txt`](file:///home/jim/mobile_base/docs/evidence/phase_r1_runtime_closure_report.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Software Runtime & Test Closure Report | Kinematic-ICP promotion as canonical laser odometry (`/lidar_odometry`), WheelOdometryBuffer unit tests, dynamic TF `odom -> base_footprint` under EKF, 508 test items executed | 2026-08-26<br>`f0de34e` | Primary evidence for Kinematic-ICP integration, WheelOdometryBuffer contracts, and EKF dynamic TF ownership | Software runtime and simulated playback execution; hardware motion verified in Phase R2/R3 |
| **EVID-E06** | [`phase_r2_hardware_static_preflight_report.txt`](file:///home/jim/mobile_base/docs/evidence/phase_r2_hardware_static_preflight_report.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Hardware Static Preflight Report | Physical hardware identity checks (M1 FTDI FT232R serial `BG03E9MD`, TDK IMU STM32 VCP serial `2063328E4842`, SICK front `192.168.0.1`, rear `192.168.0.2`), static sensor acquisition, static TF tree | 2026-08-26<br>`f0de34e` | Authoritative hardware identity and static connectivity preflight baseline for physical AMR | Stationary preflight only; does not prove dynamic closed-loop navigation |
| **EVID-E07** | [`phase_r3_5_forward_motion_yaw_sanity_report.txt`](file:///home/jim/mobile_base/docs/evidence/phase_r3_5_forward_motion_yaw_sanity_report.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Hardware Motion Verification Report | Forward-motion yaw sanity under physical teleoperation (10 cm forward pulses), verifying kinematic sign convention, wheel odometry, and yaw stability | 2026-08-26<br>`f0de34e` | Proves positive forward motion produces positive displacement without yaw divergence on physical AMR | Short pulse motions (10 cm); does not evaluate high-speed or prolonged trajectory tracking |
| **EVID-E08** | [`phase_r3_controlled_motion_characterization_report.txt`](file:///home/jim/mobile_base/docs/evidence/phase_r3_controlled_motion_characterization_report.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Hardware Motion Characterization Report | Controlled motion characterization, linear/angular velocity scaling, EKF sensor fusion under motion, dynamic state estimation | 2026-08-26<br>`f0de34e` | Validates dynamic EKF state estimation performance and motion response under real physical driving conditions | Manual motion profile evaluation; does not cover autonomous path planning |
| **EVID-E09** | [`phase_r4_navigation_acceptance_freeze_report.txt`](file:///home/jim/mobile_base/docs/evidence/phase_r4_navigation_acceptance_freeze_report.txt) | **HISTORICAL** | Acceptance Decision & Readiness Report | Navigation acceptance test site setup freeze (Station A: [0,0,0], Station B: [1,0,0], tolerance policy: xy 0.25 m, yaw 30 deg) | 2026-08-26<br>`f0de34e` | Records acceptance criteria baseline and Station coordinate freeze prior to autonomous execution | Read-only evaluation report; no autonomous motion commands dispatched during Phase R4 |
| **EVID-E10** | [`phase_r5_f2_controller_spawner_ordering_fix_report.txt`](file:///home/jim/mobile_base/docs/evidence/phase_r5_f2_controller_spawner_ordering_fix_report.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Defect Resolution & Test Report | Resolution and automated test coverage (`test_base_control_spawner_ordering_contract`) ensuring `joint_state_broadcaster` spawns prior to `diff_drive_controller` in `base_control.launch.py` | 2026-08-26<br>`f0de34e` | Guarantees deterministic lifecycle startup order for ros2_control controller spawners | Covers controller spawner sequencing only |
| **EVID-E11** | [`phase_r5_resume_final_acceptance_report.txt`](file:///home/jim/mobile_base/docs/evidence/phase_r5_resume_final_acceptance_report.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Hardware Acceptance Execution Report | Real AMR physical execution of autonomous Station navigation (Static PolygonStop PASS, Station A → B PASS, Station B → A Progress Timeout, Unknown Station Rejection PASS) | 2026-08-26<br>`f0de34e` | Primary real-hardware navigation evidence proving Station A → B navigation, Unknown Station rejection, and documenting Known Limitation B | Documents unidirectional A → B success; does not prove bidirectional navigation; B → A root cause undetermined |
| **EVID-E14** | [`scan_decoupling_report.txt`](file:///home/jim/mobile_base/docs/evidence/scan_decoupling_report.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Architecture Refactoring & Verification Report | Decommissioning `dual_laser_merger` and merged `/scan`. Reconfiguring SLAM/Kinematic-ICP to `/scan_front`, and Costmaps/Collision Monitor to independent `scan_front` and `scan_rear`. 505 tests PASS | 2026-08-27<br>`4ed33f2` | Authoritative baseline specification and verification for current dual-scan decoupled architecture | Software and composition verification; dynamic physical obstacle deceleration across both LiDARs remains a candidate for future field verification |
| **EVID-E16** | [`station_id_navigation_implementation_ready_design.txt`](file:///home/jim/mobile_base/docs/evidence/station_id_navigation_implementation_ready_design.txt) | **INVESTIGATION-ONLY** | Design Specification Note | Detailed implementation design for `navigate_to_station` C++ application prior to implementation | 2026-08-26<br>`f0de34e` | Historical design spec for the `navigate_to_station` CLI | Pre-implementation design document |
| **EVID-E17** | [`v0.1.0_as_built_as_verified_baseline.txt`](file:///home/jim/mobile_base/docs/evidence/v0.1.0_as_built_as_verified_baseline.txt) | **INVESTIGATION-ONLY** | Baseline Audit Report | Comprehensive audit of v0.1.0 codebase at commit `9028a58`, analyzing package dependencies, TF trees, and initial gap identification | 2026-08-26<br>`f0de34e` | Baseline audit reference documenting early v0.1.0 system state | Audited at commit `9028a58`; precedes Kinematic-ICP promotion and scan decoupling |

---

## 6. `docs/verification/` Raw Artifact Index

This section indexes all 69 committed raw execution artifacts, telemetry CSVs, and verification scripts across [`IMP-007`](file:///home/jim/mobile_base/docs/verification/IMP-007/) through [`IMP-015`](file:///home/jim/mobile_base/docs/verification/IMP-015/).

### IMP-007 — S7 M1Driver Transport Vertical Slice (13 files)

* **Directory Path:** [`docs/verification/IMP-007/`](file:///home/jim/mobile_base/docs/verification/IMP-007/)
* **Target Package / Scope:** `mobile_base_control` (`M1Driver` Modbus RTU driver)

| ID | Path | Classification | Evidence Type | Timestamp / Commit | Supports | Limitations |
|---|---|---|---|---|---|---|
| **RAW-007-01** | [`2026-08-18T114546_build_m1_driver.txt`](file:///home/jim/mobile_base/docs/verification/IMP-007/2026-08-18T114546_build_m1_driver.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Build Log | 2026-08-18T11:45:46 / `233ae66` | Clean compilation of `mobile_base_control` | Build-only verification |
| **RAW-007-02** | [`2026-08-18T114548_unit_m1_driver.txt`](file:///home/jim/mobile_base/docs/verification/IMP-007/2026-08-18T114548_unit_m1_driver.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Unit Test Log | 2026-08-18T11:45:48 / `233ae66` | M1Driver frame formatting, CRC calculation, and response parsing (11 tests pass) | Unit test against mock transport |
| **RAW-007-03** | [`2026-08-18T114551_neg_m1_driver_timeout.txt`](file:///home/jim/mobile_base/docs/verification/IMP-007/2026-08-18T114551_neg_m1_driver_timeout.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Negative Unit Test Log | 2026-08-18T11:45:51 / `233ae66` | Timeout exception and error recovery behavior on serial timeout | Unit test environment |
| **RAW-007-04** | [`2026-08-18T114553_hw_m1_l2_read_only.txt`](file:///home/jim/mobile_base/docs/verification/IMP-007/2026-08-18T114553_hw_m1_l2_read_only.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Hardware Preflight Log | 2026-08-18T11:45:53 / `233ae66` | Read-only communication with physical M1 drivers over `/dev/ttyUSB0` at 230400 bps | Read-only state query; no motion commanded |
| **RAW-007-05** | [`2026-08-18T115855_build_m1_driver.txt`](file:///home/jim/mobile_base/docs/verification/IMP-007/2026-08-18T115855_build_m1_driver.txt) | **HISTORICAL** | Build Log | 2026-08-18T11:58:55 / `0903cb6` | Rebuild verification during iterative development | Intermediate development run |
| **RAW-007-06** | [`2026-08-18T115857_unit_m1_driver.txt`](file:///home/jim/mobile_base/docs/verification/IMP-007/2026-08-18T115857_unit_m1_driver.txt) | **HISTORICAL** | Unit Test Log | 2026-08-18T11:58:57 / `0903cb6` | M1Driver unit test rerun | Intermediate development run |
| **RAW-007-07** | [`2026-08-18T120241_build_m1_driver.txt`](file:///home/jim/mobile_base/docs/verification/IMP-007/2026-08-18T120241_build_m1_driver.txt) | **HISTORICAL** | Build Log | 2026-08-18T12:02:41 / `cbe51a8` | Rebuild verification | Intermediate development run |
| **RAW-007-08** | [`2026-08-18T120243_unit_m1_control_check.txt`](file:///home/jim/mobile_base/docs/verification/IMP-007/2026-08-18T120243_unit_m1_control_check.txt) | **HISTORICAL** | Unit Test Log | 2026-08-18T12:02:43 / `cbe51a8` | Control check unit test | Intermediate development run |
| **RAW-007-09** | [`2026-08-18T120638_build_m1_driver.txt`](file:///home/jim/mobile_base/docs/verification/IMP-007/2026-08-18T120638_build_m1_driver.txt) | **HISTORICAL** | Build Log | 2026-08-18T12:06:38 / `6006093` | Rebuild verification | Intermediate development run |
| **RAW-007-10** | [`2026-08-18T120640_unit_m1_control_check.txt`](file:///home/jim/mobile_base/docs/verification/IMP-007/2026-08-18T120640_unit_m1_control_check.txt) | **HISTORICAL** | Unit Test Log | 2026-08-18T12:06:40 / `6006093` | Control check unit test | Intermediate development run |
| **RAW-007-11** | [`2026-08-18T121549_hw_m1_l3_enable.txt`](file:///home/jim/mobile_base/docs/verification/IMP-007/2026-08-18T121549_hw_m1_l3_enable.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Hardware Execution Log | 2026-08-18T12:15:49 / `6006093` | Physical servo enable command execution on M1 hardware | Single-action enable verification |
| **RAW-007-12** | [`2026-08-18T121725_hw_m1_l3_disable.txt`](file:///home/jim/mobile_base/docs/verification/IMP-007/2026-08-18T121725_hw_m1_l3_disable.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Hardware Execution Log | 2026-08-18T12:17:25 / `6006093` | Physical servo disable command execution on M1 hardware | Single-action disable verification |
| **RAW-007-13** | [`2026-08-18T122035_hw_m1_l3_stop.txt`](file:///home/jim/mobile_base/docs/verification/IMP-007/2026-08-18T122035_hw_m1_l3_stop.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Hardware Execution Log | 2026-08-18T12:20:35 / `6006093` | Physical emergency stop command execution on M1 hardware | Single-action stop verification |

---

### IMP-008 — S7 M1Hardware ros2_control Integration (18 files)

* **Directory Path:** [`docs/verification/IMP-008/`](file:///home/jim/mobile_base/docs/verification/IMP-008/)
* **Target Package / Scope:** `mobile_base_control` (`M1Hardware` SystemInterface and `diff_drive_controller`)

| ID | Path | Classification | Evidence Type | Timestamp / Commit | Supports | Limitations |
|---|---|---|---|---|---|---|
| **RAW-008-01** | [`2026-08-18T125000_build_test_m1_hardware.txt`](file:///home/jim/mobile_base/docs/verification/IMP-008/2026-08-18T125000_build_test_m1_hardware.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Unit Test Log | 2026-08-18T12:50:00 / `838d722` | M1Hardware lifecycle states, command/state interfaces, and 27 unit tests | Mock hardware interface unit tests |
| **RAW-008-02** | [`2026-08-18T125000_plugin_discovery.txt`](file:///home/jim/mobile_base/docs/verification/IMP-008/2026-08-18T125000_plugin_discovery.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Plugin Inspection Log | 2026-08-18T12:50:00 / `838d722` | ros2_control pluginlib discovery of `mobile_base_control/M1Hardware` | Discovery-only verification |
| **RAW-008-03** | [`2026-08-18T125500_build_test_m1_hardware_timeout_erratum.txt`](file:///home/jim/mobile_base/docs/verification/IMP-008/2026-08-18T125500_build_test_m1_hardware_timeout_erratum.txt) | **HISTORICAL** | Unit Test Log | 2026-08-18T12:55:00 / `dbb4e0d` | Erratum verification for timeout parameter handling | Intermediate regression test |
| **RAW-008-04** | [`2026-08-18T130500_diff_drive_controller_integration.txt`](file:///home/jim/mobile_base/docs/verification/IMP-008/2026-08-18T130500_diff_drive_controller_integration.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Integration Test Log | 2026-08-18T13:05:00 / `6a1ff2e` | Controller Manager loading and activating `diff_drive_controller` and `joint_state_broadcaster` | Simulation/test environment |
| **RAW-008-05** | [`2026-08-18T131000_hw_m1_l2_latency.txt`](file:///home/jim/mobile_base/docs/verification/IMP-008/2026-08-18T131000_hw_m1_l2_latency.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Hardware Telemetry Log | 2026-08-18T13:10:00 / `febe60e` | Modbus RTU L2 round-trip latency characterization (< 5 ms typical) | Summary log; raw data in companion CSV |
| **RAW-008-06** | [`2026-08-18T131000_m1_l2_latency_raw.csv`](file:///home/jim/mobile_base/docs/verification/IMP-008/2026-08-18T131000_m1_l2_latency_raw.csv) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Raw Telemetry CSV | 2026-08-18T13:10:00 / `febe60e` | 500 samples of Modbus RTU L2 response times and driver status | Raw measurement dataset |
| **RAW-008-07** | [`2026-08-18T131500_sw_m1_fc17_latency_prep.txt`](file:///home/jim/mobile_base/docs/verification/IMP-008/2026-08-18T131500_sw_m1_fc17_latency_prep.txt) | **HISTORICAL** | Test Prep Log | 2026-08-18T13:15:00 / `febe60e` | Software prep for Modbus FC17 combined read/write evaluation | Test preparation record |
| **RAW-008-08** | [`2026-08-18T132420_m1_fc17_stage_a_raw.csv`](file:///home/jim/mobile_base/docs/verification/IMP-008/2026-08-18T132420_m1_fc17_stage_a_raw.csv) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Raw Telemetry CSV | 2026-08-18T13:24:20 / `febe60e` | Raw latency dataset for Modbus FC17 Stage A timing | Raw measurement dataset |
| **RAW-008-09** | [`2026-08-18T133000_m1_fc17_stage_b_raw.csv`](file:///home/jim/mobile_base/docs/verification/IMP-008/2026-08-18T133000_m1_fc17_stage_b_raw.csv) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Raw Telemetry CSV | 2026-08-18T13:30:00 / `febe60e` | Raw latency dataset for Modbus FC17 Stage B timing | Raw measurement dataset |
| **RAW-008-10** | [`2026-08-18T135214_hw_m1_full_loop_30hz.txt`](file:///home/jim/mobile_base/docs/verification/IMP-008/2026-08-18T135214_hw_m1_full_loop_30hz.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Hardware Telemetry Log | 2026-08-18T13:52:14 / `febe60e` | 30 Hz full control loop timing verification (0 deadline misses across 1000 cycles) | Summary log; raw data in companion CSV |
| **RAW-008-11** | [`2026-08-18T135214_m1_full_loop_30hz_raw.csv`](file:///home/jim/mobile_base/docs/verification/IMP-008/2026-08-18T135214_m1_full_loop_30hz_raw.csv) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Raw Telemetry CSV | 2026-08-18T13:52:14 / `febe60e` | 1000 samples of 30 Hz control cycle execution, read, controller, and write times | Raw measurement dataset |
| **RAW-008-12** | [`2026-08-18T141700_unit_m1_dynamic_feedback_stage_d1_prep.txt`](file:///home/jim/mobile_base/docs/verification/IMP-008/2026-08-18T141700_unit_m1_dynamic_feedback_stage_d1_prep.txt) | **HISTORICAL** | Test Prep Log | 2026-08-18T14:17:00 / `febe60e` | Test harness prep for Stage D1 dynamic feedback validation | Test preparation record |
| **RAW-008-13** | [`2026-08-18T142710_hw_m1_dynamic_stage_d1.txt`](file:///home/jim/mobile_base/docs/verification/IMP-008/2026-08-18T142710_hw_m1_dynamic_stage_d1.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Hardware Execution Log | 2026-08-18T14:27:10 / `febe60e` | Stage D1 physical hardware motion and encoder feedback validation | Summary log; raw data in companion CSV |
| **RAW-008-14** | [`2026-08-18T142710_m1_dynamic_stage_d1_raw.csv`](file:///home/jim/mobile_base/docs/verification/IMP-008/2026-08-18T142710_m1_dynamic_stage_d1_raw.csv) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Raw Telemetry CSV | 2026-08-18T14:27:10 / `febe60e` | Raw wheel position and velocity telemetry during Stage D1 dynamic motion | Raw measurement dataset |
| **RAW-008-15** | [`2026-08-18T143245_unit_m1_dynamic_feedback_stage_d2_prep.txt`](file:///home/jim/mobile_base/docs/verification/IMP-008/2026-08-18T143245_unit_m1_dynamic_feedback_stage_d2_prep.txt) | **HISTORICAL** | Test Prep Log | 2026-08-18T14:32:45 / `febe60e` | Test harness prep for Stage D2 dynamic feedback validation | Test preparation record |
| **RAW-008-16** | [`2026-08-18T143440_hw_m1_dynamic_stage_d2.txt`](file:///home/jim/mobile_base/docs/verification/IMP-008/2026-08-18T143440_hw_m1_dynamic_stage_d2.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Hardware Execution Log | 2026-08-18T14:34:40 / `febe60e` | Stage D2 physical hardware motion and encoder feedback validation | Summary log; raw data in companion CSV |
| **RAW-008-17** | [`2026-08-18T143440_m1_dynamic_stage_d2_raw.csv`](file:///home/jim/mobile_base/docs/verification/IMP-008/2026-08-18T143440_m1_dynamic_stage_d2_raw.csv) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Raw Telemetry CSV | 2026-08-18T14:34:40 / `febe60e` | Raw wheel position and velocity telemetry during Stage D2 dynamic motion | Raw measurement dataset |
| **RAW-008-18** | [`2026-08-18T144340_closure_m1_hardware_ros2_control.txt`](file:///home/jim/mobile_base/docs/verification/IMP-008/2026-08-18T144340_closure_m1_hardware_ros2_control.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Verification Closure Summary | 2026-08-18T14:43:40 / `febe60e` | Overall verification closure record for IMP-008 ros2_control integration | Summary record |

---

### IMP-009 — S1 Robot Description & Geometry (3 files)

* **Directory Path:** [`docs/verification/IMP-009/`](file:///home/jim/mobile_base/docs/verification/IMP-009/)
* **Target Package / Scope:** `mobile_base_description` (URDF/Xacro, joint limits, wheel geometry)

| ID | Path | Classification | Evidence Type | Timestamp / Commit | Supports | Limitations |
|---|---|---|---|---|---|---|
| **RAW-009-01** | [`2026-08-18T151212_unit_s1_robot_description.txt`](file:///home/jim/mobile_base/docs/verification/IMP-009/2026-08-18T151212_unit_s1_robot_description.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Unit Test Log | 2026-08-18T15:12:12 / `2ae71fa` | URDF/Xacro parsing, link inertia, collision geometries, 8 unit tests pass | Static model check |
| **RAW-009-02** | [`2026-08-18T152206_erratum_semantic_audit.txt`](file:///home/jim/mobile_base/docs/verification/IMP-009/2026-08-18T152206_erratum_semantic_audit.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Semantic Audit Log | 2026-08-18T15:22:06 / `2ae71fa` | REP-103/105 coordinate frame conventions (`base_footprint`, `base_link`, `laser_front_link`, `laser_rear_link`, `imu_link`) | Semantic/spec check |
| **RAW-009-03** | [`2026-08-18T155716_physical_geometry_sanity.txt`](file:///home/jim/mobile_base/docs/verification/IMP-009/2026-08-18T155716_physical_geometry_sanity.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Geometry Sanity Log | 2026-08-18T15:57:16 / `2ae71fa` | Physical robot geometry, wheel separation (0.420 m), wheel radius (0.075 m), LiDAR positions | Static verification |

---

### IMP-010 — S2 Dual LiDAR Acquisition (2 files)

* **Directory Path:** [`docs/verification/IMP-010/`](file:///home/jim/mobile_base/docs/verification/IMP-010/)
* **Target Package / Scope:** `mobile_base_perception` (`sick_scan_xd` dual SICK picoScan150)

| ID | Path | Classification | Evidence Type | Timestamp / Commit | Supports | Limitations |
|---|---|---|---|---|---|---|
| **RAW-010-01** | [`2026-08-18T170342_unit_s2_lidar_acquisition.txt`](file:///home/jim/mobile_base/docs/verification/IMP-010/2026-08-18T170342_unit_s2_lidar_acquisition.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Unit Test Log | 2026-08-18T17:03:42 / `2ae71fa` | SICK LiDAR launch syntax and argument verification | Syntax and launch-level test |
| **RAW-010-02** | [`2026-08-18T173400_hw_s2_lidar_dual_acquisition.txt`](file:///home/jim/mobile_base/docs/verification/IMP-010/2026-08-18T173400_hw_s2_lidar_dual_acquisition.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Hardware Execution Log | 2026-08-18T17:34:00 / `2ae71fa` | Real hardware UDP acquisition of dual SICK picoScan150 (`/scan_front` at `192.168.0.1`, `/scan_rear` at `192.168.0.2` @ 20 Hz) | Stationary sensor acquisition |

---

### IMP-011 — S2 TDK IMU Runtime Integration (4 files)

* **Directory Path:** [`docs/verification/IMP-011/`](file:///home/jim/mobile_base/docs/verification/IMP-011/)
* **Target Package / Scope:** `tdk_ros2_imu` / `mobile_base_perception` (TDK IIM-42652 6-DoF IMU)

| ID | Path | Classification | Evidence Type | Timestamp / Commit | Supports | Limitations |
|---|---|---|---|---|---|---|
| **RAW-011-01** | [`2026-08-19T134600_sw_s2_imu_runtime_integration.txt`](file:///home/jim/mobile_base/docs/verification/IMP-011/2026-08-19T134600_sw_s2_imu_runtime_integration.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Unit Test Log | 2026-08-19T13:46:00 / `2ae71fa` | `tdk_ros2_imu` software build and unit tests (16 pytest pass) | Software-level unit testing |
| **RAW-011-02** | [`2026-08-19T134830_hw_stage_i1_passive_identity.txt`](file:///home/jim/mobile_base/docs/verification/IMP-011/2026-08-19T134830_hw_stage_i1_passive_identity.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Hardware Preflight Log | 2026-08-19T13:48:30 / `2ae71fa` | USB CDC ACM device discovery on `/dev/ttyACM0` (STM32 VCP serial `2063328E4842`) | Device presence preflight |
| **RAW-011-03** | [`2026-08-19T135330_hw_stage_i2_static_acquisition.txt`](file:///home/jim/mobile_base/docs/verification/IMP-011/2026-08-19T135330_hw_stage_i2_static_acquisition.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Hardware Execution Log | 2026-08-19T13:53:30 / `2ae71fa` | Static IMU telemetry acquisition on `/imu/data_raw` (gravity vector ~9.8 m/s², zero angular velocity) | Stationary sensor telemetry |
| **RAW-011-04** | [`2026-08-19T140200_hw_stage_i3_dynamic_validation.txt`](file:///home/jim/mobile_base/docs/verification/IMP-011/2026-08-19T140200_hw_stage_i3_dynamic_validation.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Hardware Execution Log | 2026-08-19T14:02:00 / `2ae71fa` | Dynamic manual rotation validation proving correct yaw rate sign and magnitude response | Manual physical excitation |

---

### IMP-012 — Historical RF2O Laser Odometry (2 files)

* **Directory Path:** [`docs/verification/IMP-012/`](file:///home/jim/mobile_base/docs/verification/IMP-012/)
* **Target Package / Scope:** Historical RF2O 2D Laser Odometry (Superseded)

| ID | Path | Classification | Evidence Type | Timestamp / Commit | Supports | Limitations |
|---|---|---|---|---|---|---|
| **RAW-012-01** | [`2026-08-19T153600_sw_s2_rf2o_selected_scan.txt`](file:///home/jim/mobile_base/docs/verification/IMP-012/2026-08-19T153600_sw_s2_rf2o_selected_scan.txt) | **SUPERSEDED** | Software Integration Log | 2026-08-19T15:36:00 / `2ae71fa` | Historical RF2O software configuration and scan topic subscription | Superseded by Kinematic-ICP in Phase R1 ([`phase_r1_runtime_closure_report.txt`](file:///home/jim/mobile_base/docs/evidence/phase_r1_runtime_closure_report.txt)) |
| **RAW-012-02** | [`2026-08-19T154200_hw_stage_r2_stationary_runtime.txt`](file:///home/jim/mobile_base/docs/verification/IMP-012/2026-08-19T154200_hw_stage_r2_stationary_runtime.txt) | **SUPERSEDED** | Hardware Execution Log | 2026-08-19T15:42:00 / `2ae71fa` | Historical RF2O stationary runtime execution on hardware | Superseded by Kinematic-ICP in Phase R1 ([`phase_r1_runtime_closure_report.txt`](file:///home/jim/mobile_base/docs/evidence/phase_r1_runtime_closure_report.txt)) |

---

### IMP-013 — S3 State Estimation & EKF Integration (2 files)

* **Directory Path:** [`docs/verification/IMP-013/`](file:///home/jim/mobile_base/docs/verification/IMP-013/)
* **Target Package / Scope:** `mobile_base_state_estimation` (`robot_localization` `ekf_filter_node`)

| ID | Path | Classification | Evidence Type | Timestamp / Commit | Supports | Limitations |
|---|---|---|---|---|---|---|
| **RAW-013-01** | [`2026-08-19T161500_sw_s3_state_estimation.txt`](file:///home/jim/mobile_base/docs/verification/IMP-013/2026-08-19T161500_sw_s3_state_estimation.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Software Unit/Syntax Log | 2026-08-19T16:15:00 / `2ae71fa` | EKF launch syntax, parameter schema validation, and package build | Software syntax check |
| **RAW-013-02** | [`2026-08-19T162000_hw_stage_e2_stationary_ekf.txt`](file:///home/jim/mobile_base/docs/verification/IMP-013/2026-08-19T162000_hw_stage_e2_stationary_ekf.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Hardware Execution Log | 2026-08-19T16:20:00 / `2ae71fa` | Hardware stationary EKF fusion (fusing laser odom and IMU yaw rate to publish sole dynamic TF `odom -> base_footprint` @ 30 Hz) | Stationary baseline; dynamic motion verified in Phase R3 |

---

### IMP-014 — S4 Mapping & MapIO Integration (3 files)

* **Directory Path:** [`docs/verification/IMP-014/`](file:///home/jim/mobile_base/docs/verification/IMP-014/)
* **Target Package / Scope:** `mobile_base_mapping` (`async_slam_toolbox_node` & MapIO)

| ID | Path | Classification | Evidence Type | Timestamp / Commit | Supports | Limitations |
|---|---|---|---|---|---|---|
| **RAW-014-01** | [`2026-08-19T163000_sw_s4_mapping_mapio.txt`](file:///home/jim/mobile_base/docs/verification/IMP-014/2026-08-19T163000_sw_s4_mapping_mapio.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Software Unit Test Log | 2026-08-19T16:30:00 / `2ae71fa` | SLAM Toolbox config syntax, MapIO readback unit tests (4 tests pass) | Unit test against mock map file |
| **RAW-014-02** | [`2026-08-19T163500_hw_stage_m2_stationary_mapping.txt`](file:///home/jim/mobile_base/docs/verification/IMP-014/2026-08-19T163500_hw_stage_m2_stationary_mapping.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Hardware Execution Log | 2026-08-19T16:35:00 / `2ae71fa` | Real-hardware stationary SLAM initialization and dynamic TF `map -> odom` publication by SLAM Toolbox | Stationary sensor mapping; dynamic mapping in IMP-015 Stage G1 |
| **RAW-014-03** | [`2026-08-19T180500_hw_stage_m3_map_save_readback.txt`](file:///home/jim/mobile_base/docs/verification/IMP-014/2026-08-19T180500_hw_stage_m3_map_save_readback.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Hardware Execution Log | 2026-08-19T18:05:00 / `2ae71fa` | Live map saving (`save_map.sh`), metadata validation, and Nav2 map server read-back round trip | Static map file validation |

---

### IMP-015 — S7 Manual Teleop & Base Control Physical Motion (22 files)

* **Directory Path:** [`docs/verification/IMP-015/`](file:///home/jim/mobile_base/docs/verification/IMP-015/)
* **Target Package / Scope:** `mobile_base_control`, `mobile_base_bringup`, manual teleoperation, safety stopping, on-ground physical motion

| ID | Path | Classification | Evidence Type | Timestamp / Commit | Supports | Limitations |
|---|---|---|---|---|---|---|
| **RAW-015-01** | [`2026-08-19T190500_sw_teleop_interface_validation.txt`](file:///home/jim/mobile_base/docs/verification/IMP-015/2026-08-19T190500_sw_teleop_interface_validation.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Software Interface Test Log | 2026-08-19T19:05:00 / `d3c5e7f` | `teleop_twist_keyboard` stamped message publication to `/diff_drive_controller/cmd_vel` | Software interface test |
| **RAW-015-02** | [`2026-08-19T190500_sw_teleop_package_static_check.txt`](file:///home/jim/mobile_base/docs/verification/IMP-015/2026-08-19T190500_sw_teleop_package_static_check.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Package Dependency Check | 2026-08-19T19:05:00 / `d3c5e7f` | Verified Debian package installation of `ros-jazzy-teleop-twist-keyboard` | Static environment inspection |
| **RAW-015-03** | [`2026-08-19T190700_hw_teleop_hardware_suite.txt`](file:///home/jim/mobile_base/docs/verification/IMP-015/2026-08-19T190700_hw_teleop_hardware_suite.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Hardware Safety Preflight Log | 2026-08-19T19:07:00 / `d3c5e7f` | Level 4 Hardware Safety Preflight on physical AMR | Preflight check prior to motion |
| **RAW-015-04** | [`2026-08-19T190800_hw_mapping_teleop_integration.txt`](file:///home/jim/mobile_base/docs/verification/IMP-015/2026-08-19T190800_hw_mapping_teleop_integration.txt) | **HISTORICAL** | Integration Test Log | 2026-08-19T19:08:00 / `d3c5e7f` | Integrated live mapping stack with teleop command dispatch | Contains references to early RF2O mapping baseline |
| **RAW-015-05** | [`2026-08-19T191200_sys027_timeout_and_stopping_analysis.txt`](file:///home/jim/mobile_base/docs/verification/IMP-015/2026-08-19T191200_sys027_timeout_and_stopping_analysis.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Timing Analysis Report | 2026-08-19T19:12:00 / `d3c5e7f` | Timing analysis of command timeout ($t \le 0.5$ s) and stopping distance constraints | Analytical timing specification |
| **RAW-015-06** | [`2026-08-19T191500_evidence_integrity_audit.txt`](file:///home/jim/mobile_base/docs/verification/IMP-015/2026-08-19T191500_evidence_integrity_audit.txt) | **INVESTIGATION-ONLY** | Integrity Audit Record | 2026-08-19T19:15:00 / `d3c5e7f` | Audit record identifying lack of physical observation and mandating Level 4 physical tests | Audit process record |
| **RAW-015-07** | [`2026-08-19T192500_s7_control_chain_static_inspection.txt`](file:///home/jim/mobile_base/docs/verification/IMP-015/2026-08-19T192500_s7_control_chain_static_inspection.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Hardware State Inspection Log | 2026-08-19T19:25:00 / `d3c5e7f` | Static inspection of S7 Base Control hardware registers and controller state | Static state verification |
| **RAW-015-08** | [`2026-08-19T192600_s7_e2e_zero_command_validation.txt`](file:///home/jim/mobile_base/docs/verification/IMP-015/2026-08-19T192600_s7_e2e_zero_command_validation.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Hardware Execution Log | 2026-08-19T19:26:00 / `d3c5e7f` | E2E control path zero-command safety validation on real hardware | Zero-motion validation |
| **RAW-015-09** | [`2026-08-19T193500_s7_30hz_zero_command_validation.txt`](file:///home/jim/mobile_base/docs/verification/IMP-015/2026-08-19T193500_s7_30hz_zero_command_validation.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Hardware Timing Log | 2026-08-19T19:35:00 / `bd039ba` | 30 Hz baseline zero-command timing verification log on real hardware | Zero-motion timing verification |
| **RAW-015-10** | [`2026-08-19T194000_hw_wheels_off_ground_physical_motion.txt`](file:///home/jim/mobile_base/docs/verification/IMP-015/2026-08-19T194000_hw_wheels_off_ground_physical_motion.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Hardware Motion Log | 2026-08-19T19:40:00 / `d3c5e7f` | Elevated AMR wheels-off-ground physical motion test (forward, reverse, rotation) | Wheels off ground (elevated chassis) |
| **RAW-015-11** | [`2026-08-19T194500_hw_wheels_off_ground_comprehensive_suite.txt`](file:///home/jim/mobile_base/docs/verification/IMP-015/2026-08-19T194500_hw_wheels_off_ground_comprehensive_suite.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Hardware Motion Log | 2026-08-19T19:45:00 / `d3c5e7f` | Comprehensive wheels-off-ground verification suite covering all motion profiles | Wheels off ground (elevated chassis) |
| **RAW-015-12** | [`2026-08-19T204500_fastcdr_abi_and_runtime_closure.txt`](file:///home/jim/mobile_base/docs/verification/IMP-015/2026-08-19T204500_fastcdr_abi_and_runtime_closure.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Defect Resolution Log | 2026-08-19T20:45:00 / `bd039ba` | Fast-CDR ABI mismatch resolution and runtime stack closure in Docker environment | Environment configuration fix |
| **RAW-015-13** | [`2026-08-20T094000_hw_stage_g1_ground_forward_active_stop_mapping.txt`](file:///home/jim/mobile_base/docs/verification/IMP-015/2026-08-20T094000_hw_stage_g1_ground_forward_active_stop_mapping.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Hardware Ground Motion Log | 2026-08-20T09:40:00 / `5f95d27` | Real-ground forward displacement (+0.10 m/s ~1.5s), active stop, and dynamic SLAM mapping on flat ground | Low-speed forward trajectory (~0.15 m total motion) |
| **RAW-015-14** | [`2026-08-20T100500_hw_stage_g2_ground_reverse.txt`](file:///home/jim/mobile_base/docs/verification/IMP-015/2026-08-20T100500_hw_stage_g2_ground_reverse.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Hardware Ground Motion Log | 2026-08-20T10:05:00 / `5f95d27` | Real-ground reverse motion (-0.10 m/s ~1.0s) and active stop on flat ground | Low-speed reverse motion |
| **RAW-015-15** | [`2026-08-20T101500_hw_stage_g3_ground_ccw_rotation.txt`](file:///home/jim/mobile_base/docs/verification/IMP-015/2026-08-20T101500_hw_stage_g3_ground_ccw_rotation.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Hardware Ground Motion Log | 2026-08-20T10:15:00 / `5f95d27` | Real-ground CCW rotation (+0.15 rad/s ~1.0s) and active stop on flat ground | Pure in-place rotational motion |
| **RAW-015-16** | [`2026-08-20T102000_hw_stage_g4_ground_timeout_stop.txt`](file:///home/jim/mobile_base/docs/verification/IMP-015/2026-08-20T102000_hw_stage_g4_ground_timeout_stop.txt) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Hardware Ground Motion Log | 2026-08-20T10:20:00 / `5f95d27` | Real-ground stale-command timeout stop test on flat ground (command stopped; physical robot stopped in 0.5 s) | Low-speed forward timeout |
| **RAW-015-17** | [`validate_teleop_hardware_suite.py`](file:///home/jim/mobile_base/docs/verification/IMP-015/validate_teleop_hardware_suite.py) | **HISTORICAL** | Verification Test Script | `d3c5e7f` | Executable verification script for Level 4 Hardware Verification Suite | Verification script |
| **RAW-015-18** | [`verify_mapping_teleop_integration.py`](file:///home/jim/mobile_base/docs/verification/IMP-015/verify_mapping_teleop_integration.py) | **SUPERSEDED** | Verification Test Script | `543fa41` | Historical mapping and teleop integration validator for the superseded RF2O baseline | Superseded by Kinematic-ICP mapping pipeline |
| **RAW-015-19** | [`verify_s7_30hz_zero_command.py`](file:///home/jim/mobile_base/docs/verification/IMP-015/verify_s7_30hz_zero_command.py) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Verification Test Script | `bd039ba` | Executable test script verifying S7 Base Control 30 Hz zero-command baseline | Verification script |
| **RAW-015-20** | [`verify_teleop_interface.py`](file:///home/jim/mobile_base/docs/verification/IMP-015/verify_teleop_interface.py) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Verification Test Script | `d3c5e7f` | Executable test script validating `teleop_twist_keyboard` command publishing | Verification script |
| **RAW-015-21** | [`verify_wheels_off_ground_full_suite.py`](file:///home/jim/mobile_base/docs/verification/IMP-015/verify_wheels_off_ground_full_suite.py) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Verification Test Script | `d3c5e7f` | Executable test script for comprehensive wheels-off-ground verification suite | Verification script |
| **RAW-015-22** | [`verify_wheels_off_ground_motion.py`](file:///home/jim/mobile_base/docs/verification/IMP-015/verify_wheels_off_ground_motion.py) | **CURRENT-SUPPORTING HISTORICAL RUNTIME** | Verification Test Script | `d3c5e7f` | Executable test script for wheels-off-ground physical motion test | Verification script |

---

## 7. Empty Verification Placeholders

The following directories in `docs/verification/` contain only a `.gitkeep` placeholder file and have no committed raw execution artifacts:

| Directory Path | Classification | Physical Disposition | Rationale / Status |
|---|---|---|---|
| `IMP-016/` | **EMPTY PLACEHOLDER** | Deferred — Migration Gate 3 | S6 Target Admission thin gaps verified at system level in Phase R5 report and unit test suites |
| `IMP-017/` | **EMPTY PLACEHOLDER** | Deferred — Migration Gate 3 | S6 Route-assisted Navigation execution verified at system level in Phase R5 report |
| `IMP-018/` | **EMPTY PLACEHOLDER** | Deferred — Migration Gate 3 | TF and frame authority closure verified in `test_tf_authority.py` and Phase R1 report |
| `IMP-019/` | **EMPTY PLACEHOLDER** | Deferred — Migration Gate 3 | Perception data-flow closure verified in `test_perception_dataflow.py` and Scan Decoupling report |
| `IMP-020/` | **EMPTY PLACEHOLDER** | Deferred — Migration Gate 3 | Motion-command and physical-stop closure verified in `test_motion_command_stop_chain.py` and Phase R5 report |
| `IMP-021/` | **EMPTY PLACEHOLDER** | Deferred — Migration Gate 3 | Feedback and odometry closure verified in `test_feedback_odometry_chain.py` and Phase R1 report |
| `IMP-022/` | **EMPTY PLACEHOLDER** | Deferred — Migration Gate 3 | Operational-mode and lifecycle closure verified in Phase R1~R5 reports |
| `IMP-023/` | **EMPTY PLACEHOLDER** | Deferred — Migration Gate 3 | UC-001 Mapping end-to-end acceptance verified in Phase R1 and Launch Entry Optimization reports |
| `IMP-024/` | **EMPTY PLACEHOLDER** | Deferred — Migration Gate 3 | UC-002 Navigation end-to-end acceptance verified in Phase R5 report |
| `IMP-025/` | **EMPTY PLACEHOLDER** | Deferred — Migration Gate 3 | Requirement and custom-gap traceability audit addressed via Migration Batch 2 |
| `IMP-026/` | **EMPTY PLACEHOLDER** | Deferred — Migration Gate 3 | Reproducibility and clean-environment audit documented in Phase R1~R5 reports |
| `IMP-027/` | **EMPTY PLACEHOLDER** | Deferred — Migration Gate 3 | v0.1 Feature Freeze review documented in Phase 1 audit and baseline documentation |

> [!NOTE]
> Empty placeholder directories `IMP-016` through `IMP-027` were retired after verification confirmed that they contained no evidence artifacts.

---

## 8. Historical Automated-Test Records

The repository's automated test suite expanded over successive development phases. The following test execution records are preserved in committed reports:

| Milestone / Context | Historically Recorded Count | Result | Supporting Report Source | Baseline Commit / Context | Superseded by Later Run? |
|---|---|---|---|---|---|
| **v0.1.0 Feature Freeze Baseline** | **425 test items** | `PASS` (0 failures, 0 errors) | [`v0.1.0_as_built_as_verified_baseline.txt`](file:///home/jim/mobile_base/docs/evidence/v0.1.0_as_built_as_verified_baseline.txt) | `9028a58` (Initial v0.1.0 test suite across 10 packages before Kinematic-ICP promotion) | Yes — Superseded by 508-test run |
| **Kinematic-ICP Software Runtime Closure** | **508 test items** | `PASS` (0 failures, 0 errors, 41 skipped cppcheck) | [`phase_r1_runtime_closure_report.txt`](file:///home/jim/mobile_base/docs/evidence/phase_r1_runtime_closure_report.txt) | `543fa41` / `f0de34e` (Added Kinematic-ICP ROS wrapper & WheelOdometryBuffer unit tests) | Yes — Superseded by 505-test scan decoupling run |
| **Scan Decoupling Architecture** | **505 test items** | `PASS` (0 failures, 0 errors, 41 skipped cppcheck) | [`scan_decoupling_report.txt`](file:///home/jim/mobile_base/docs/evidence/scan_decoupling_report.txt) | `4ed33f2` (Retired merger/filter tests; added decoupled scan dependency tests) | Yes — Superseded by 515-test launch optimization run |
| **Launch Entry Optimization** | **515 test items** | `PASS` (0 failures, 0 errors, 41 skipped cppcheck) | [`launch_entry_optimization_report.txt`](file:///home/jim/mobile_base/docs/evidence/launch_entry_optimization_report.txt) | `8ab06d9` (Added canonical bringup & site resolution tests across all 10 packages) | **Latest Historical Record** |

> [!IMPORTANT]
> **Test Count Claim Boundary:**
> `515 tests PASS` is a **historically recorded test execution result** at commit `8ab06d9`. This index records historical evidence; no test suites were re-run during documentation convergence. This figure must **not** be stated as a live-run assertion for current `HEAD` without fresh execution.

---

## 9. Superseded Evidence Relationships

The following table summarizes evidence artifacts whose underlying architecture, node implementations, or data flows have been superseded by newer verified generations:

```text
┌─────────────────────────────────────────────────────────┐
│              Historical Architecture Flow               │
├─────────────────────────────────────────────────────────┤
│ 1. RF2O Laser Odometry (IMP-012)                        │
│    ──► Superseded by Kinematic-ICP (Phase R1 Report)    │
│                                                         │
│ 2. Merged Scan / dual_laser_merger                      │
│    ──► Superseded by Direct Scan Decoupling             │
│                                                         │
│ 3. Dedicated collision_scan_filter Node (CM-F1)         │
│    ──► Superseded by Direct Dual-Scan Collision Monitor │
│                                                         │
│ 4. Custom NavigateToStation ROS Action Spec             │
│    ──► Superseded by navigate_to_station CLI (Model B)  │
└─────────────────────────────────────────────────────────┘
```

| Historical / Superseded Artifact | Superseding Implementation / Evidence | Technical Rationale for Supersession |
|---|---|---|
| [`docs/verification/IMP-012/`](file:///home/jim/mobile_base/docs/verification/IMP-012/) (RF2O Odometry logs)<br>[`verify_mapping_teleop_integration.py`](file:///home/jim/mobile_base/docs/verification/IMP-015/verify_mapping_teleop_integration.py) | [`phase_r1_runtime_closure_report.txt`](file:///home/jim/mobile_base/docs/evidence/phase_r1_runtime_closure_report.txt)<br>[`kinematic_icp_ros.yaml`](file:///home/jim/mobile_base/src/kinematic_icp/ros/config/kinematic_icp_ros.yaml) | RF2O suffered high CPU load and odometry drift during fast rotation. Kinematic-ICP fuses wheel odometry prior buffers with scan matching, providing superior planar laser odometry. |
| References to `dual_laser_merger` & `/scan` | [`scan_decoupling_report.txt`](file:///home/jim/mobile_base/docs/evidence/scan_decoupling_report.txt)<br>[`nav2_params.yaml`](file:///home/jim/mobile_base/src/mobile_base_navigation/config/nav2_params.yaml) | Intermediate scan merger introduced latency and dropped rear points. Replaced by direct multi-source consumption in Nav2 Costmaps and Collision Monitor. |
| Historical CM-F1 collision scan self-filter attempt (`laser_filters`) | [`scan_decoupling_report.txt`](file:///home/jim/mobile_base/docs/evidence/scan_decoupling_report.txt)<br>[`nav2_params.yaml`](file:///home/jim/mobile_base/src/mobile_base_navigation/config/nav2_params.yaml) | The intermediate box-filter node was decommissioned when Collision Monitor polygon configurations were adjusted to directly consume raw scans without self-chassis triggering. |
| Obsolete `mobile_base_msgs/action/NavigateToStation` action server design in old specs | [`station_id_navigation_implementation_ready_design.txt`](file:///home/jim/mobile_base/docs/evidence/station_id_navigation_implementation_ready_design.txt)<br>[`navigate_to_station_app.cpp`](file:///home/jim/mobile_base/src/mobile_base_navigation/src/navigate_to_station_app.cpp) | Action server added redundant state machine overhead. Replaced by thin C++ client wrapper resolving Station ID and submitting native Nav2 `NavigateToPose` goals. |

---

## 10. Evidence Gaps / Re-Verification Candidates

The following items are identified as **re-verification candidates** where committed evidence reflects historical baselines or where physical test coverage is bounded:

| Candidate Area | Description of Evidence Gap | Classification | Target Resolution Scope |
|---|---|---|---|
| **Automated Test Suite Re-run** | Automated test suite (515 tests) has not been re-executed during the documentation convergence process. | `Re-verification candidate` | Re-run test suite during formal release validation or upon any future source code modification. |
| **Dynamic Multi-Angle Obstacle Deceleration / Stop** | Phase R5 report verified static `PolygonStop` on real hardware; dynamic multi-angle obstacle intrusions during active motion have software coverage but lack dedicated physical AMR telemetry logs. | `Re-verification candidate` | Execute dynamic obstacle intrusion tests during post-MVP field validation. |
| **Station B → A Return Navigation Progress Timeout Diagnosis** | Historical Phase R5 run recorded Nav2 controller progress timeout (`error_code=105`) at $y = -0.175$ m (0.42 m from Station A). Root cause is undetermined in committed evidence. | `Re-verification candidate` (Known Limitation B) | Perform on-robot hardware execution with diagnostic rosbag recording to characterize root cause (deferred from documentation convergence). |
| **Discrete Raw Logs for IMP-016 ~ IMP-027** | High-level checklist items (IMP-016 ~ IMP-027) were validated via system-level integration reports (Phase R1~R5, launch optimization) rather than discrete raw files in per-item folders. | `Re-verification candidate` (Covered at system level) | Reconciled via Migration Batch 2 (Traceability Matrix); physical placeholder directories scheduled for Gate 3 retirement. |

> [!NOTE]
> None of the above candidates constitute an A-class MVP functional blocker. System implementation, automated test implementations, and historical hardware acceptance evidence are fully established.

---

## 11. Index Integrity Rules

The maintenance of this evidence index is governed by the following strict integrity rules:

1. **Raw Evidence Immutability:** Raw evidence files (`.txt`, `.csv`, `.ref.txt`) are never modified, edited, or fabricated to match documentation changes.
2. **Historical Context Binding:** Every evidence artifact remains permanently bound to the Git commit hash, hardware configuration, and execution timestamp at which it was generated.
3. **Controlled Classification Updates:** An artifact's status classification (e.g., from `CURRENT-SUPPORTING HISTORICAL RUNTIME` to `SUPERSEDED`) may only be changed through an approved documentation migration batch or decision gate with documented architectural justification.
4. **Live Verification Independence:** Claiming that a requirement is currently verified on `HEAD` requires a new, timestamped verification execution record; historical records alone cannot be converted into live-test claims.
5. **Path Stability:** Evidence file paths in `docs/evidence/` and `docs/verification/` remain stable and persistent to preserve historical Git traceability.
6. **No Report Override of Raw Logs:** Narrative summary reports do not automatically override or replace raw telemetry data logs without explicit technical erratum documentation.

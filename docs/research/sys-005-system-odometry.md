> [!WARNING]
> **HISTORICAL / NON-AUTHORITATIVE**
>
> This document is retained for historical traceability only. It does not define the current system architecture, requirements, operational procedure, or verification authority. Use `docs/README.md` to locate the current canonical documentation.

# SYS-005 System Odometry — Reuse Research

## Question and scope

Assess the proposed composition:

```text
wheel odometry + RF2O odometry + IMU
                  ↓
       robot_localization EKF
                  ↓
 authoritative system odometry + odom -> base_footprint
```

The initial research question also considered an all-three-required, no-degraded contract. That constraint was subsequently superseded: the approved requirement now permits `robot_localization` native remaining-input fusion and prediction behavior. This note records both the investigated limitation and the final baseline decision.

## Direct conclusion

- `robot_localization` supports multiple `nav_msgs/msg/Odometry` inputs plus `sensor_msgs/msg/Imu`, planar filtering, configurable measurement fields, and publication of the `odom -> base_footprint` transform.
- The checked RF2O implementation does **not** natively subscribe to two `LaserScan` topics. One node instance has one `laser_scan_topic`, one subscription, one `last_scan`, and estimates motion between consecutive scans from that one stream.
- Two RF2O instances and one RF2O instance consuming a merged scan are technically different candidates. Neither is selected here.
- The proposed fusion is reusable in principle, but the current inputs are not ready for trustworthy fusion without resolving covariance and validity contracts.
- After measurement timeout, `robot_localization` continues prediction and output. This did not cover the initially considered all-three-required rule, but it does cover the subsequently approved native-behavior requirement.

## Exact versions and revisions checked

| Component | Version / revision | Scope checked |
|---|---|---|
| RF2O local reference | package `0.1.0`, commit `b38c68e46387b98845ecbfeb6660292f967a00d3` | subscription, timestamps, frames, covariance, TF publication |
| `robot_localization` for ROS 2 Jazzy | released `3.8.3` | Jazzy package availability and supported multi-input fusion |
| `robot_localization` local reference | tag `3.10.1`, commit `7dfb6aa97b2082185d2fac3420888ae8474bfc1a` | source-level timeout behavior; newer than the Jazzy release, so it is supporting evidence rather than exact-Jazzy closure |
| wheel odometry local reference | commit `f05d8cbb43a812e39c0b038c56baee8ada699b2c` | message timestamp, frames, and covariance population |

The target Jazzy image must still confirm its installed `robot_localization` package version. The ROS Index reports Jazzy `3.8.3`; the local source snapshot is not the exact Jazzy revision.

## Can RF2O consume two LaserScan topics?

No, not in the checked implementation.

Source evidence:

- The node declares one string parameter, `laser_scan_topic`.
- It creates exactly one `LaserScan` subscription.
- Its callback stores one `last_scan` and one `current_scan_time`.
- The RF2O algorithm compares the current scan with the previous scan from that same stream.

Relevant source: [RF2O node at the checked commit](https://github.com/MAPIRlab/rf2o_laser_odometry/blob/b38c68e46387b98845ecbfeb6660292f967a00d3/src/CLaserOdometry2DNode.cpp).

### Candidate A — two RF2O instances

Each instance consumes one independent LaserScan and publishes a separate odometry estimate. This produces **two RF2O odometry inputs**, not one RF2O estimate based jointly on both LiDARs. It also introduces correlation, covariance, initialization, frame, and disagreement-handling questions for the EKF.

### Candidate B — one RF2O instance with merged scan

RF2O consumes one composite LaserScan created upstream. This makes RF2O unaware of the two original sources and depends on a merge solution with verified TF, time synchronization, angular resampling, overlap/occlusion handling, latency, and failure semantics.

The two candidates are not equivalent. At research time no candidate was selected; a subsequent approved decision chose merged-scan input and `dual_laser_merger` 0.3.1.

## Three-input fusion readiness

### Frame compatibility

| Input | Current evidence | Gap |
|---|---|---|
| Wheel odometry | publishes `header.frame_id = odom` and `child_frame_id = base frame` | exact names and TF ownership must match the canonical `odom` and `base_footprint`; its own odom TF must be disabled when EKF is authoritative |
| RF2O odometry | configurable `odom_frame_id` and `base_frame_id`; obtains the static laser-to-base transform from TF | set `publish_tf=false`; prove scan frame TF and canonical base frame; note that the lookup uses latest TF (`TimePointZero`), not the scan timestamp |
| IMU | configurable IMU frame | prove mounting TF, ENU/REP-103 axis semantics, and which measurement fields are fused |
| EKF output | `world_frame=odom`, `odom_frame=odom`, `base_link_frame=base_footprint`, `publish_tf=true` is the intended ownership pattern | exact configuration and unique-publisher runtime evidence required |

`robot_localization` explicitly supports continuous wheel/visual-style odometry and IMU inputs, and supports multiple numbered odometry inputs. See the [official state-estimation documentation](https://docs.ros.org/en/jazzy/p/robot_localization/) and [ROS Index Jazzy package record](https://index.ros.org/p/robot_localization/).

### Timestamp compatibility

| Input | Current evidence | Gap |
|---|---|---|
| Wheel odometry | stamps the message with controller host time at publication | determine measurement age relative to the wheel feedback acquisition; publication time may hide transport/control-loop latency |
| RF2O odometry | output stamp is the stamp of the last LaserScan used | good provenance, but both LiDAR driver timestamp semantics and scan latency still require verification |
| IMU | previously assessed driver uses host publication time rather than sensor acquisition time | quantify serial and scheduling latency and align it with the other inputs |

The EKF processes stamped inputs and transforms measurements at their timestamps. Therefore, a common ROS clock alone is insufficient: acquisition-time semantics and bounded latency must also be demonstrated.

### Covariance compatibility

Current covariance data is not sufficient for a defensible three-source EKF configuration:

- RF2O constructs `nav_msgs/msg/Odometry` but does not populate pose or twist covariance; all values remain zero.
- The wheel odometry implementation only sets `twist.covariance[0] = 0.01`; pose covariance and angular-velocity covariance remain zero.
- The assessed IMU driver publishes zero covariance, which means uncertainty is unknown at the ROS message-contract level.
- The checked EKF source replaces very small selected covariance entries with `1e-9`; this prevents a numerical singularity but does **not** create a physically justified sensor uncertainty model.

Before fusion, each selected measurement fragment needs a justified covariance or a documented decision not to fuse that fragment. In particular, two pose-producing odometry sources can compete or oscillate if their uncertainty is understated.

### Input timeout and native degraded behavior

The mature EKF behaves as follows:

- `sensor_timeout` means the filter performs prediction without correction and continues producing output after measurements stop.
- It accepts an arbitrary number of configured inputs, but it does not provide an output contract meaning "wheel + RF2O + IMU are all currently valid."
- RF2O warns while waiting for scans, but its odometry message has no explicit validity field.
- Topic presence, node activity, and a continuing EKF output therefore cannot establish system-odometry validity.

The approved SYS-005 now adopts this native behavior: a missing or rejected source does not by itself invalidate system odometry. Remaining valid measurements may continue correction, and timeout may lead to prediction-only output. The project must still verify configuration, covariance, drift, and downstream suitability; it does not require a separate all-input validity gate.

## Coverage and gaps

### Against the current SYS-005 wording

`SYS-005` only requires planar odometry usable by localization, mapping, and navigation. The mature composition is a plausible candidate, but project-level coverage remains `Needs Verification` until frames, timestamps, covariances, field selection, unique TF ownership, and downstream integration are proven.

### Against the approved native-behavior contract

| Item | Assessment |
|---|---|
| Multi-source EKF capability | `Fully Covered` at mature-package capability level |
| Single authoritative `odom -> base_footprint` | `Fully Covered` by configuration, provided all other odometry TF publishers are disabled |
| RF2O consuming two raw LaserScans directly | `Not Covered` by the checked RF2O implementation |
| Trustworthy input covariance | `Not Covered` by current project messages/configuration |
| Remaining-input fusion and timeout prediction | `Fully Covered` at mature-package capability level |
| Overall approved system behavior | `Fully Covered` at mature-package capability level |

Gap classification:

- `Configuration Gap`: EKF fields, planar mode, frames, TF publication, timeouts, queues, differential/relative use, and rejection thresholds.
- `Evidence Gap`: timing, TF-at-stamp, sensor quality, convergence, integration, and real-hardware behavior.
- `Configuration / Evidence Gap`: `dual_laser_merger` 0.3.1 is selected, while synchronization, TF, QoS, resampling, overlap／occlusion, output parameters, latency, dropout, and failure semantics still require closure.

## Subsequent approved baseline decisions

The final approved SYS-005 requires wheel odometry, RF2O odometry, and IMU as configured estimation sources, while permitting `robot_localization` to continue with remaining valid measurements or prediction when inputs are abnormal or timed out. The user selected a merged `LaserScan` as the RF2O input and ROS 2 Jazzy `dual_laser_merger` 0.3.1 as the merge package. Its configuration and failure semantics remain unresolved.

## MVP change candidate

`None`. The remaining work is exact `dual_laser_merger`／EKF configuration and verification, not a custom all-input validity gate.

## Evidence references

- [RF2O official repository](https://github.com/MAPIRlab/rf2o_laser_odometry)
- [RF2O node source at assessed commit](https://github.com/MAPIRlab/rf2o_laser_odometry/blob/b38c68e46387b98845ecbfeb6660292f967a00d3/src/CLaserOdometry2DNode.cpp)
- [robot_localization ROS Index entry for Jazzy](https://index.ros.org/p/robot_localization/)
- [robot_localization official repository](https://github.com/cra-ros-pkg/robot_localization)
- Local evidence: `ref/rf2o_laser_odometry`, `ref/robot_localization`, `ref/base_motor_controller`, and the previously assessed `ref/tdk_ros2_imu`
> **Superseded candidate assessment:** this research record documents the earlier RF2O selection investigation. Current production architecture uses `/scan_front` + `/diff_drive_controller/odom` → Kinematic-ICP → `/lidar_odometry` → EKF + IMU yaw rate. RF2O is not an active or fallback architecture.

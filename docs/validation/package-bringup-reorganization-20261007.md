# Package responsibilities and installed Bringup verification — 2026-10-07

Authority: [spec32](https://github.com/monkey30440/mobile_base/issues/32), confirmed
package/entry revision and existing35/36/37/38 tickets. User confirmed the spelling
mobile_base_control and authorized implementation after reconciliation.

## Delivery

- mobile_base_perception replaces IMU/LiDAR packages: identical USB packet/node
  behavior and native dual SICK launch; installed Python module/resources renamed.
- mobile_base_control replaces M1: C++ namespace/header/plugin registration renamed;
  device protocol, measured position, fault latch and stop semantics unchanged.
  Native xacro expands the selected geometry. Explicit optional native controller
  covariance diagonals pass from the profile; no calibration/default is invented.
- mobile_base_bringup provides installed model/control/IMU/LiDAR/sensor-model,
  local_base and base entrypoints. Control-containing entries reuse one RSP;
  EKF alone owns odom→base_footprint. base includes both native LiDAR sources and
  optional native Foxglove. No motion publisher or new runtime owner is added.
- Public control/LiDAR workflow tests move to Bringup; necessary bounded protocol,
  IMU adapter and model tests remain with their responsibilities. Operator docs
  use Bringup and distinguish local verification from full product readiness.

Fresh package discovery/build resolves exactly Control, Perception, Description
and Bringup from the new install prefix. No compatibility aliases are added for
old package names. Use a clean build/install prefix and do not source stale overlays.

## Software evidence: PASS

No physical device mappings; network none; ARM64 production-check image and actual
versions recorded in the archive. Synthetic OS serial peers exercise installed
native nodes, not internal mocks. Real robot movement, sensor traffic, GUI assets,
physical stopping or calibration were not executed/accepted by this checkpoint.

Control4 C++ cases, Perception13 cases, Description1 case and Bringup47 cases:
**65 actual cases passed; colcon reports67 including2 CTest wrappers**. The first
all-package invocation failed6 Bringup cases:5 stale test-profile paths after
moving tests and1 recovery sequencing assumption. Native logs showed fault
injection before JSB readiness; native CLI rejects unconfigured→active. Tests
now wait for finite JointState, use installed Control profiles and query public
controller state for deliberate configure→activate. Those6 cases passed, then
all47 Bringup cases passed with the unchanged other3 packages' fresh results.

Final review strengthened the missing-filter case: all3 local/base cases share
complete valid peer profiles; only filter is removed. The motor profile really
points to the peer and IMU has a separate PTY. Zero requests/Servo ON meaningfully
checks pre-start failure. After this tests-only fixture change, those3 affected
cases passed again; unchanged other cases are not claimed newly rerun. The full
suite's prior local test and the final tested version are separately retained.

Integration observes finite measured wheel positions, root-to-wheel/IMU/LiDAR TF,
unique RSP/static/model and EKF output, disabled controller odom TF, native
covariance values, source identities/QoS and no command publisher. Passive LiDAR
graph checks accept source composition, not scan content or device shutdown.

Foxglove3.5.0 returned HTTP101 with the native SDK subprotocol. The initial legacy-only
request received400; no bridge patch was needed. The official SDK handshake
requires its advertised subprotocol ([primary source](https://docs.rs/foxglove/latest/src/foxglove/websocket/handshake.rs.html)).
This connection check is not Operator Foxglove visual acceptance. Native SICK
SIGINT cleanup limitations remain from earlier evidence; software PASS does not
claim graceful real-device shutdown.

## Review and handoff

Approved code-review basis f591f4e; this refactor reviewed relative to f8b5bc9 as
well as retained cumulative scope. Spec:0 actionable findings. Standards: the
missing-filter test gap was fixed and re-reviewed;0 remaining actionable findings.
One nonblocking P3 judgment remains: network argument signatures repeat across
three launch compositions. Explicit public signatures are retained for MVP;
no custom runtime/helper framework is added solely to hide a short fact list.

Original requirements, topics/frames, measured-wheel/nominal-seat semantics and
native owners remain. No issue is closed and no dependency is removed. Actual
Operator/hardware verification must next use these installed Bringup entries;
prior raw evidence retains its historical package names and scope. Formal target
facts, remaining35/36/37/38 acceptance, calibration and full V1 readiness remain open.

[Evidence archive](artifacts/package-bringup-reorganization-20261007.tar.gz) contains
fresh build/results, versions/isolation/prefixes, native scene logs, source snapshots,
intermediate failures and SHA256 manifest. Temporary helper scripts/old launch copies
are not the product verification entry.

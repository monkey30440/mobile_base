# Phased verification correction — 2026-10-07

Authority: Operator confirmation and [spec32](https://github.com/monkey30440/mobile_base/issues/32), section “Confirmed package responsibilities and phased verification”. Related tickets35/36/37/38/39/41/45/46 were reconciled before code edits; states and dependency edges remain unchanged.

Keep `mobile_base_perception` (IMU and native dual LiDAR) and `mobile_base_control` (renamed M1 adapter). Withdraw only the premature component/local_base/base Bringup wrappers introduced in dc3f6ee. Control public workflow tests return to Control; LiDAR public workflow tests return to Perception. The existing sensor/model component entry returns to Perception and includes native Description and dual-LiDAR launch. Preexisting Bringup dataset/native local-estimation partials remain, without claiming complete product readiness.

Development order: core35/36/37 acceptance →38 model/wheel/IMU/native-EKF integration →39/41 Mapping/Navigation product composition. Existing Wayfinder decisions and applicable hardware evidence remain; this correction is not new hardware or calibration acceptance. Control/IMU runtime implementation matches f8b5bc9 after the approved package-name substitution. Control's geometry-only explicit model contract is restored; the premature xacro/covariance convenience changes are withdrawn with the composition that introduced them.

## Software verification

Fresh build/install in `/tmp/stage`, ARM64 production-check image `sha256:307cf16d1581c1078d21e67c1d8c9aab21eeca61641e1c9a23b90c34d0b83e46`. Container network disabled, repository read-only, no physical devices mapped. Build all four affected packages, then run colcon tests sequentially against this fresh overlay.

- Control:31 public ROS/native controller cases and4 protocol C++ cases.
- Perception:13 packet/adapter cases and3 native public LiDAR workflow cases.
- Description:1 model extraction case.
- Bringup:10 existing dataset/native-EKF cases.

62 actual cases, plus3 CTest wrapper counts: **65 tests,0 errors,0 failures,0 skipped**. Python syntax/package XML and `git diff --check` passed. The first final result command tried writing its default log under the read-only workspace; rerunning only the result reader with explicit temporary log directory succeeded. This was a result-tool path error, not a test failure.

[Raw build/test logs, result XML, corrected issue-body snapshots and source hashes](artifacts/phased-verification-correction-20261007.tar.gz) retain the evidence. Prior [reorganization results](package-bringup-reorganization-20261007.md) remain historical software evidence, superseded as current entrypoints. The unexecuted temporary unified manual helper was invalidated.

## Review and remaining work

Two-axis review retains user-approved basis f591f4e and examines this selective correction against dc3f6ee: Standards0 actionable findings; Spec0 actionable findings. Core native responsibilities, real position/fault behavior and TF ownership remain intact.

No motor commands, sensor startup or physical tests occurred. Actual target compatibility, source-specific fault/recovery/shutdown acceptance and calibration retain their previous incomplete scopes. No issue closed or dependency removed. Continue core component acceptance before further integration/product Bringup delivery.

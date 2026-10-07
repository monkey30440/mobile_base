# V1 flow resumption — 2026-10-07

The operator authorized preservation commit/push, limited spec reconciliation,
and continuation of the original plan. This supersedes the initial pause in
v1-flow-recovery-20261007.md without discarding that historical snapshot.

## Preservation

Retained corrections and reviewed evidence were committed as 8377380 on
integration/v1-spec-32 and pushed to origin. User-owned untracked motor reference
data was not included. Four affected pytest cases passed via native colcon;
six aggregate entries include CTest wrappers, with no errors/failures/skips.
Independent Standards: zero actionable findings. Spec: zero runtime deviations,
with two reconciliation items, addressed below.

## Limited specification reconciliation

The existing V1 Specification was edited in place. Original supplied URDF hash
b49ef5cc66217ff5fb527a4d10a1d63b5f941dbd024bb30bb6704442c39e08fc is historical
authority. Operator-corrected deployment URDF hash
f6447d72716a11f4e5ee9d447b58d81256746af91604acb85b6ab56540e0f425 is tied to
8377380. Native sensor and TF owners remain unchanged. Source joints express
mounting poses once, native scan children are identity, and the obsolete extra
CAD-frame/optical-child approaches are superseded.

Testing retains the approved public ROS topics/TF/robot_description workflow
seam and operator Foxglove observation. Static visual acceptance is confirmed;
precise calibration, dynamic wheel/IMU direction and scale, real EKF integration,
long-duration/reconnect/shutdown acceptance remain distinct and incomplete.
No new product feature or custom runtime gap was found, so the cleared Wayfinder
architecture is retained. No replacement specification or architecture map was
created.

## Original tickets and frontier

Approved ticket sizes and native blocking dependencies were retained. The thirteen
existing implementation tickets had textual Parent links but no native sub-issue
attachment to their specification. Those existing approved relationships were
attached and verified; no new ticket was created or split, and no blocker was
removed. Closed dataset and development-container tickets stay closed; incomplete
device, estimation and downstream workflow tickets stay open.

Device frontier: Teleop/wheel feedback, USB IMU, dual LiDAR. The next original
slice being resumed is Teleop/wheel feedback, assigned before continuation.
Read-only preparation confirms the device symlinks exist, reviews target and
commissioning profiles, and checks applicability of earlier evidence. No serial
port was opened and no motor was enabled or commanded during this resumption.

Wheel feedback gaps: actual firmware identity and production limits/timing are
unresolved; effective geometry and physical displacement need calibration.
Earlier raised 0.1 m/s forward-and-stop evidence is retained. The 0.03 m/s
no-visible-motion/reporting discrepancy remains unresolved, and timeout-only or
communication-loss stopping was not established by the combined zero/off trial.
The checked-in commissioning profile remains 0.03 m/s and 150 motor RPM, while
the historical 0.1 m/s trial used a separately bounded profile. Do not silently
claim that profile is deployed or that target YAML can activate: target facts
remain null and must be resolved. Pose changes do not change M1 control behavior.

Next physical test requires fresh operator presence/raised-or-ground state;
the question was sent and dependent motion is pending its reply. Finish device
acceptance before the model/real-estimation integration ticket, then Mapping,
Navigation Bringup and the remaining original workflow slices in native dependency
order. Stationary sensor/model success does not unblock the complete estimation
slice or justify skipping its device gates.

Canonical tracker: https://github.com/monkey30440/mobile_base/issues/32

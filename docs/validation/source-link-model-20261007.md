# Source-link model correction — 2026-10-07

The operator confirmed the base mesh appearance is corrected and rejected added
base_lidar_cad_link_FL/BR frames. The supplied reference URDF was re-inspected:
base_lidar_joint_FL/BR and their visual/inertial origins all have zero RPY.
The URDF does not define native scan optical axes. Its CAD link axes therefore
must not be asserted to be sensor device axes merely from the link names.

The build-time extraction now preserves the original sensor links, joints,
meshes and inertials. Only existing native `_1` scan child frames express the
selected optical orientation. No extra CAD frames, scan rewriting or additional
runtime publisher are used. Nominal optical RPY remains roll pi, pitch zero,
yaw -pi/4 (FL) and -3pi/4 (BR), with source mount translations. This profile
requires physical off-axis alignment verification and measured calibration.
The original CAD frames remain unrotated by design; the scan frames have +Z down.

The installed-model test first failed on the rejected extra CAD links, then
passed after removal. Four affected software cases passed, including native
RSP TF publication, unchanged CAD visual/inertial origins, formal scan child
transforms and native driver launch configuration. A focused geometry assertion
was added and passed. Native sensor startup is asynchronous: the first 10-second
observation was too early for BR initialization and failed with zero BR scans;
this is recorded rather than treated as a successful hardware run.

Foxglove manual verification: reconnect ws://localhost:8765 to clear cached old
static frames; use fixed/display frame base_footprint and Scene Mesh up-axis
Z-up. Enable robot_description and both formal scans. The native scan frame IDs
must be base_lidar_link_FL_1 and base_lidar_link_BR_1. Inspect their +Z axes down
and physical target alignment. Base appearance is operator-confirmed; revised
optical alignment is still pending operator acceptance. No motors were operated.

A subsequent steady-state 10-second capture recorded 249 scans per side:
FL 24.999 Hz, maximum gap 43.83 ms; BR 25.002 Hz, maximum gap 44.32 ms.
Both native frame IDs are correct, each scan topic has one publisher, the model
contains no extra CAD links, scan +Z points down, and one RSP owns static TF.
The intervening capture exceeded the 250 ms gap gate; its exact transient cause
was not isolated. These bounded captures demonstrate the revised model and a
stable observation window, not long-duration transport acceptance.

A repeat capture with the original 250 ms maximum-gap assertion restored passed.
Independent Standards and Spec reviews of this correction relative to a06071a
reported zero actionable findings. Revised optical alignment still requires the
operator's manual Foxglove acceptance; no full-V1 or production-calibration
completion is claimed.

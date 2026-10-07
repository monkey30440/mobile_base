# Inverted LiDAR mounting and Foxglove mesh orientation

2026-10-07 follow-up to the single-echo/model stage. Operator confirmed both
formal scans stable, but rejected mounting orientation and model appearance.
Both LiDARs are physically inverted, tops facing downward. The requested whole-
model +90-degree adjustment concerns `/robot_description` appearance only.
The initial yaw-only stage is **not accepted physical mounting evidence**.

## Separate causes and responsibilities

1. **Physical TF error:** yaw-only configuration leaves device +Z up. A single
   forward/rear point cannot disambiguate upright yaw from inverted opposite yaw.
   With roll=pi, prior native bearings support nominal FL yaw=-45 degrees and
   BR yaw=-135 degrees, pitch0. These remain nominal, pending an off-axis target
   check and precise extrinsic calibration. An XY LaserScan with z0 does not
   reveal inversion by vertical point displacement; its Y/azimuth handedness
   and transformed Z axis do change. The official supplied SICK manual,
   section3.5.5 and annex “Upside down mounting [Design-in]” printedp86,
   explicitly states scan rotation stays counterclockwise in device coordinates
   regardless of installation. Data must stay native; RSP supplies mounting TF.
2. **Mesh display:** source STL wheel bounds are approximately x=.15993,
   y=.05,z=.15993m for a drive wheel, consistent with its source Y joint axis
   and Z-up geometry. Installed Foxglove3.3.0 defaults meshUpAxis to y_up and
   conditionally applies rotateX(pi/2) to STL/OBJ models. This matches the
   reported visual-only orientation discrepancy, but the current saved UI
   setting and corrected rendering still require operator confirmation.
   Set **3D Scene → Mesh up-axis → Z-up**, not base TF or URDF visual rotation.
   [Official URDF guidance](https://foxglove.dev/blog/adding-urdfs-to-foxglove-studios-3d-panel)
   and [3D panel settings](https://docs.foxglove.dev/docs/visualization/panels/3d).

## Implemented model contract

Original source sensor links/meshes/inertials use explicit CAD names
`base_lidar_cad_link_FL/BR` with their original transforms. Device-oriented
children `base_lidar_link_FL/BR` carry explicit mounting RPY. Native single-echo
scan children `base_lidar_link_FL_1/BR_1` are identity relative to the respective
device frame. Both mounting and scan +Z therefore point downward; CAD meshes
remain at their source geometry without an artificial additional rotation.
All transforms belong to native RSP; no added runtime TF publisher or scan rewrite.

The model/sensor launch now requires all six RPY arguments. Current profile:

```text
fl_scan_roll:=3.141592653589793 fl_scan_pitch:=0 fl_scan_yaw:=-0.7853981633974483
br_scan_roll:=3.141592653589793 br_scan_pitch:=0 br_scan_yaw:=-2.356194490192345
```

Base, IMU, all other geometry and motor behavior are unchanged. No wheel or
suspension states are fabricated. The normal model footprint root has +Z up;
the inverted LiDAR frames have +Z down, which is an expected physical relationship.

## Verification

The public native RSP test first failed on the old mounting identity quaternion,
then passes for both mounting/scan orientations and unchanged CAD transforms.
It accepts quaternion double-cover (q/-q are equivalent), verifies device +Z
maps to base -Z, and retains installed meshes/joint types/single TF ownership.
The full affected model/LiDAR suite contains4 passing pytest cases.

Bounded stationary hardware observer verifies both formal scan topics retain
single native frames, >1000 valid points per sample, approximately25Hz, one
publisher per topic, one model TF owner, model description, and downward +Z for
both mounting/scan frames. Expanded model and capture are retained in
`artifacts/inverted-model-20261007.tar.gz`. This is orientation wiring evidence,
not a physical off-axis target acceptance or calibrated extrinsic measurement.

## Manual gate still required

Reconnect Foxglove; base_footprint fixed/display frame; set Scene Mesh up-axis
Z-up. Show model, both formal scans, and TF axes with scan decay0. Verify whole
model appearance, mounting and scan blue +Z arrows downward, stable scans and
physical target positions. Then use a known off-axis target (e.g. move it toward
AMR left from a forward/rear reference) to distinguish angular handedness and
nominal yaw. Exact targets/coordinates must be reported before acceptance.
Mesh display correction and physical mounting acceptance are separate results.

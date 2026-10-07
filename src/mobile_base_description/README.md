# mobile_base_description

Build-time extraction of the supplied RWF_V2.0_QA_release.urdf base subtree.
The repository's reference platform folder is required at build time; installed
URDF and base meshes are self-contained and use package URIs. Upper-body geometry
is excluded. Source geometry, inertials and movable joints are retained.
BASE_FOOTPRINT is normalized/rerooted as base_footprint; wheel joint names map to
the canonical left_wheel_joint/right_wheel_joint used by M1.

Native robot_state_publisher is the sole model TF owner. Original sensor CAD
links are named base_lidar_cad_link_FL/BR and retain source meshes/inertials.
Their device-oriented children base_lidar_link_FL/BR carry explicit mounting RPY;
the native scan `_1` children are identity. This separates baked CAD geometry
from actual device axes without distorting meshes or rewriting scan data. The two native single-
echo optical frames are base_lidar_link_FL_1 and base_lidar_link_BR_1. Launch
requires explicitly selected optical roll/pitch/yaw (radians) relative to CAD axes.
The integrated observation uses nominal roll=180 degrees, pitch=0 and yaw=-45/-135 degrees: the
operator confirmed both sensors inverted, and coarse bearings constrain yaw; these are not calibrated production extrinsics. Optical
origin translation follows the CAD mount pending measured calibration. CAD
translations and other fixed sensor geometry are unchanged.

No joint_state_publisher or fabricated wheel/suspension/caster states are started.
Movable branches require real appropriate joint feedback; absence of that feedback
is not a complete dynamic-model acceptance. All sensor/base_footprint paths are
fixed and can be verified without motor operation. odom->base_footprint remains
robot_localization's responsibility; this model-only launch does not fabricate it.
Do not simultaneously start M1's standalone RSP: final bringup must compose a
single RSP with the control fragment/profile, rather than two competing owners.

```bash
ros2 launch mobile_base_description description.launch.py \
  fl_scan_roll:=3.141592653589793 fl_scan_pitch:=0 fl_scan_yaw:=-0.7853981633974483 \
  br_scan_roll:=3.141592653589793 br_scan_pitch:=0 br_scan_yaw:=-2.356194490192345
```

Foxglove 3D Scene → Mesh up-axis must be Z-up for the supplied STL geometry.
The default Y-up introduces a display-only mesh rotation; do not compensate
by rotating base TF or changing authoritative visual origins.

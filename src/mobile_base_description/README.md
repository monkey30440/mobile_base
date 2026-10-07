# mobile_base_description

Build-time extraction of the supplied RWF_V2.0_QA_release.urdf base subtree.
The repository's reference platform folder is required at build time; installed
URDF and base meshes are self-contained and use package URIs. Upper-body geometry
is excluded. Source geometry, inertials and movable joints are retained.
BASE_FOOTPRINT is normalized/rerooted as base_footprint; wheel joint names map to
the canonical left_wheel_joint/right_wheel_joint used by M1.

Native robot_state_publisher is the sole model TF owner. The two native single-
echo optical frames are base_lidar_link_FL_1 and base_lidar_link_BR_1. Launch
requires explicitly selected optical yaw (radians) relative to the CAD mount.
The integrated observation uses nominal +45/+135 degrees supported by operator
coarse measurements; these are not calibrated production extrinsics. Optical
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
  fl_scan_yaw:=0.7853981633974483 br_scan_yaw:=2.356194490192345
```

# mobile_base_description

Build-time extraction of the supplied RWF_V2.0_QA_release.urdf base subtree.
The repository's reference platform folder is required at build time; installed
URDF and base meshes are self-contained and use package URIs. Upper-body geometry
is excluded. Source geometry, inertials and movable joints are retained.
BASE_FOOTPRINT is normalized/rerooted as base_footprint; wheel joint names map to
the canonical left_wheel_joint/right_wheel_joint used by M1.

Native robot_state_publisher is the sole model TF owner. The supplied URDF
now defines the operator-confirmed mounting poses directly on
base_lidar_joint_FL/BR: roll=180 degrees, pitch=0, yaw=+45 degrees (FL)
and -135 degrees (BR). base_imu_joint has yaw=+90 degrees, roll/pitch=0,
with its source translation retained. The native base_lidar_link_FL_1/BR_1 scan children
are identity transforms, so mounting rotation is applied exactly once.
No extra CAD links or scan rewriting are used. Visual and inertial origins
remain unchanged; meshes rotate with their source links. Translations retain
the source mount positions pending precise extrinsic calibration.

No joint_state_publisher or fabricated wheel/suspension/caster states are started.
Movable branches require real appropriate joint feedback; absence of that feedback
is not a complete dynamic-model acceptance. All sensor/base_footprint paths are
fixed and can be verified without motor operation. odom->base_footprint remains
robot_localization's responsibility; this model-only launch does not fabricate it.
Do not simultaneously start M1's standalone RSP: final bringup must compose a
single RSP with the control fragment/profile, rather than two competing owners.

```bash
ros2 launch mobile_base_description description.launch.py
```

Foxglove 3D Scene → Mesh up-axis must be Z-up for the supplied STL geometry.
The default Y-up introduces a display-only mesh rotation; do not compensate
by rotating base TF or changing authoritative visual origins.

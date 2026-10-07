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
Use the installed Description entry for model-only verification.
Control now starts no RSP and can be launched independently after Description.
Perception starts its sensors separately; the former sensor_model entry was removed.

```bash
ros2 launch mobile_base_description description.launch.py
```

Foxglove 3D Scene → Mesh up-axis must be Z-up for the supplied STL geometry.
The default Y-up introduces a display-only mesh rotation; do not compensate
by rotating base TF or changing authoritative visual origins.

## Nominal drive-seat posture

V1 spec32 reconciliation (2026-10-07) uses the original design origins at zero
displacement for `driving_slide_joint_L/R`. The build-time deployment model
expresses only these two as fixed joints; source URDF and origin geometry remain
unchanged. Native RSP publishes the nominal base-to-drive-seat transforms. This
is not measured suspension travel, and no fake JointState or extra TF publisher
is introduced. Wheel rotation remains continuous and comes from real M1 position
feedback. Other passive caster/suspension joints are not implicitly fixed or
declared hardware-verified by this choice.

## Independent Control verification

For model/Perception-only checks, the default geometry-only launch above is enough.
For Control, start Description with the same explicit M1 profile that Control will
use, then launch Control in a second terminal:

```bash
ros2 launch mobile_base_description description.launch.py hardware_config:=/absolute/hardware.yaml
ros2 launch mobile_base_control m1.launch.py hardware_config:=/absolute/hardware.yaml
```

Description adds the existing M1 ros2_control declaration to the published URDF.
It reads configuration only: no device open, controller manager, Servo ON or
sensor startup occurs here. Native RSP remains the sole model publisher; Control
consumes its transient-local robot_description. Optional model_file overrides
geometry for a documented fixture/revision; the default is the installed model.
The override must be geometry-only and contain canonical wheel joints when a
hardware profile is supplied. Relative paths resolve from the caller directory,
with ~ expansion. YAML/parser errors and missing, empty, nonmapping or null-valued hardware
mappings fail model launch. Required hardware parameter completeness and physical
parameter validation remain Control/plugin responsibility.

Use one RSP and one profile per session. Loading a profile into Description is
not hardware acceptance. End/restart the selected configuration to change it;
there is no project-owned model/profile synchronization or hot reload.

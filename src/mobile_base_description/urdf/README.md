# URDF Assets

This directory contains the robot's private URDF/Xacro assets.

## Repository Policy

URDF/Xacro assets are intentionally excluded from the public repository
and may only be present in private or deployment environments.

Both states are valid:

- **Public checkout:** this directory may contain only this README.
- **Private/deployment checkout:** the actual URDF/Xacro assets may also be present.

The absence of private URDF/Xacro assets in a public checkout does not
indicate an incomplete repository or missing implementation.

When the assets are present, they are the authoritative robot-description
source and may be inspected or used normally.

When the assets are absent, do not fabricate, reconstruct, or infer their
contents. If a task specifically requires the private robot description,
report that the task cannot be fully verified without those assets.
# Mesh Assets

This directory contains the robot's private mesh assets.

## Repository Policy

Mesh assets are intentionally excluded from the public repository
and may only be present in private or deployment environments.

Both states are valid:

- **Public checkout:** this directory may contain only this README.
- **Private/deployment checkout:** the actual mesh assets may also be present.

The absence of private mesh assets in a public checkout does not
indicate an incomplete repository or missing implementation.

When the assets are present, they may be inspected or used normally.

When the assets are absent, do not fabricate, reconstruct, or infer their
contents. If a task specifically requires the private mesh geometry,
report that the task cannot be fully verified without those assets.
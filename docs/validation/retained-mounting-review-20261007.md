# Retained mounting corrections — pre-push review

Fixed point: f591f4e8ccbffb60aac8616d45c2a12d3558b143, previously approved by
operator. Reviewed its commit range through c3ff2ea and pending working-tree
corrections. Current operator-confirmed mounting result supersedes earlier
nominal or extra-CAD-frame approaches.

## Standards

Hard violations: 0. Actionable bugs: 0. New baseline smells: 0.
Removed optical arguments and identity scan children apply mounting rotations
once. Source sensor translations, visual/inertial origins and endpoints remain
consistent. The existing hardcoded footprint inversion maintainability concern
is unchanged and nonblocking.

## Spec

Actionable runtime deviations: 0. Scope-creep findings: 0.
Two reconciliation items: preserve original authority and record corrected model
revision/hash in the specification; replace stale LiDAR nominal yaw in its ticket.
Stationary operator-confirmed model/TF/scan results do not complete actual EKF,
dynamic-joint feedback, calibration, native shutdown/reconnect or full V1.

## Verification

Affected packages mobile_base_description and mobile_base_lidar completed native
colcon tests: four pytest cases passed; colcon counts six with two CTest wrappers.
No hardware motion or driver restart was performed by this review/test pass.
Test-result initially attempted a log in the read-only workspace and failed;
rerunning only reporting with /tmp log-base produced zero errors/failures/skips.

The earlier recovery archive is a timestamped snapshot before this commit, not
a replacement for current git history. The user subsequently authorized commit,
push, limited spec reconciliation and continuation of the original plan.

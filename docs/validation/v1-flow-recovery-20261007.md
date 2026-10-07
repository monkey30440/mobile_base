# V1 flow recovery — 2026-10-07

Implementation and hardware progression are paused at the operator's request.
Existing implementation is retained; no code rollback, clean or restart is part
of this recovery. The operator explicitly allows the current verified results
as reference evidence for this recovery, overriding the former default ban on
using unapproved project implementations as architecture references for this scope.
This does not authorize wholesale reuse of unverified implementation.

## Confirmed current result

Operator explicitly confirmed all coordinate frames and point clouds correct
in the integrated Foxglove observation. Current supplied-model joint poses:
FL roll pi/pitch zero/yaw +pi/4; BR roll pi/pitch zero/yaw -3pi/4;
IMU roll/pitch zero/yaw +pi/2. Native scan children are identity, formal native
LAST scan frames are base_lidar_link_FL_1 and base_lidar_link_BR_1.
No extra CAD frames or scan rewriting. Foxglove uses Z-up mesh interpretation.
The integrated test starts one native RSP. Both formal scans were operator-confirmed.

This is stationary model/TF/scan visual acceptance. It does not confirm precise
calibration, ground odometry direction/scale, actual EKF integration, dynamic
joint feedback, long-run/reconnect/power-cycle behavior or complete V1 readiness.
The archived source, SHA256 and working-tree patch identify the observed state;
HEAD alone does not: the most recent corrections remain uncommitted.

## Process assessment

Existing LiDAR and model/estimation implementation tickets cover the work.
However the latest mounting facts, deleted optical launch arguments, manual
acceptance and superseded CAD-link approaches have not been consistently
reconciled with the tracker/spec, review and commit checkpoints. Model work was
performed while its full estimation-ticket blockers remained open; isolated
model checks do not satisfy those blockers or complete that ticket.
Do not treat the previous recommendation to proceed to ground EKF tests as
completion of those prerequisites.

## Return stage and bounded next work

Return to specification/evidence reconciliation before implementation planning.
The cleared Wayfinder architecture still supports native sick_scan_xd, native
RSP and robot_localization. No evidence currently requires changing those owners
or creating a new architecture map. If a real responsibility/capability gap is
found, reopen the relevant Wayfinder decision before changing the solution.

Prepare a limited specification update: replace obsolete CAD-axis wording with
current operator-confirmed mounting facts, retain native identity scan children,
record original authority vs corrected deployment-model revision hashes, and
separate stationary acceptance from remaining calibration/motion acceptance.
Do not prescribe exact mounting angles as universal V1 product requirements.

Then use /to-tickets to review only affected existing slices/dependencies with
the operator: separate independently verifiable model/static-sensor integration
from wheel/IMU-dependent estimation if needed. Do not remove genuine estimation
blockers simply to mark progress. Reuse scoped applicable evidence and reconcile
review/commit checkpoints before /implement resumes on the approved frontier.
No new tickets, dependency rewrites, ticket closures, runtime modifications,
commits or motion tests were performed by this recovery.

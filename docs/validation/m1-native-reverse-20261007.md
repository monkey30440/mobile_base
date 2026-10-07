# Raised reverse commissioning — 2026-10-07

Original-plan continuation: Teleop/wheel feedback ticket, after preservation and
spec reconciliation. Operator freshly confirmed the AMR remains raised and they
are onsite to observe. Source 301aaa6 on integration/v1-spec-32. No source runtime
code changed during this test; the temporary observer/publisher extends the
previous archived forward commissioning workflow.

## Preconditions and corrected container access

An exclusive FC03-only guard checks both drive status/alarm/current RPM and target
RPM, final Modbus CRC and per-drive prefix checks. Initial and final states are
both inhibited6, alarm0, currentRPM0, targetRPM0.

The first attempt failed native hardware configure before any reverse command:
UID1000 had only GID1000 while the mapped serial device is root:dialout, mode660,
GID20. Native configure cannot open it. The post-failure FC03 readback remained
inhibited/zero. The replacement temporary container adds actual device GID20;
identical native hardware then configured and activated successfully. No chmod,
root-user workaround, drive parameter edit or project runtime patch was used.
Persistent hardware bringup must map the actual device and grant its host group;
the minimal development Compose without those settings is not a hardware runner.

## Bounded native test

Dedicated container, network none, ROS domain210, only the motor device mapped;
no IMU/EKF or LiDAR process was started there. Geometry was expanded from the
operator-verified installed model; this launch owns its one native RSP and native
controller with enable_odom_tf=false. Separate domain176 sensor view remains intact.
The reused commissioning profile bounds native linear speed to0.1m/s and both
motor caps to300RPM, ratio20:1/radius0.08m/separation0.555m. These are explicitly
commissioning settings, not validated production operating limits.

Before hardware activation, independent script review required complete unique
finite wheel feedback, post-zero fresh feedback, and protected launch cleanup.
Six invalid-feedback fixtures were rejected and a valid negative pair accepted,
without hardware access. The revised scripts had no remaining review finding.

The native observer verifies per-source health/freshness, initial zero, actual
public hardware caps and native controller speed limit before READY. Twenty
negative commands request -0.1m/s, angular0. Measured first-negative to explicit
zero duration:2.000187274s; this is observed timing, not a hard real-time guarantee.
Explicit zero, native timeout settling, fresh zero wheel feedback, successful
native deactivation and final inhibited/zero readback completed. No physical
bus-disconnection test was performed.

Normalized feedback ranges: left[-1.277581012,0]rad/s, right[-1.256637061,0]rad/s.
Native wheel odometry minimum linear.x=-0.100866102m/s. These are reported
feedback/derived odometry, not independent physical scale measurements.

## Physical acceptance and limits

The operator reported not noticing the two-second run; physical direction/stop
acceptance for that case is unconfirmed. They requested a separate10-second
repeat at the same speed. A question was sent after that repeat. Do not infer physical acceptance
from reported RPM or native deactivation. Both drives were left inhibited and the
temporary motor container was removed.

Earlier raised0.1m/s forward/stop evidence remains applicable within its scope;
0.03m/s no-visible-motion discrepancy, actual firmware identity, production
limits/timing, effective calibration, ground displacement, isolated timeout/link-loss
stopping, full model/real-EKF integration and complete V1 acceptance remain open.

[Evidence archive](artifacts/m1-native-reverse-20261007.tar.gz) includes exact
reviewed temporary scripts, profile/geometry, initial/final FC03 bytes, native
launch/ROS/commands, summary/hash manifest and permission-failure evidence.
Archived scripts are evidence, not instructions for unsupervised motor operation.

## Operator-requested 10-second repeat

At the explicit operator request, the same guarded native workflow repeated
reverse -0.1m/s for100 commands over10 seconds, followed by explicit zero,
fresh feedback checks, native deactivation and independent inhibited/zero readback.
The longer trial uses the same300RPM/.1m/s commissioning caps and current model.
No other control or drive parameter changed; no physical acceptance is inferred
from the earlier unobserved run.

The repeat completed NATIVE_OBSERVATION_COMPLETED. Final FC03 at
2026-10-07T04:28:06Z confirms both status6/alarm0/currentRPM0/targetRPM0 with
both integrity checks. The temporary motor container was removed afterwards.
Operator explicitly confirmed both wheels turned toward AMR-reverse and both
stopped during this10-second repeat. This completes the supervised raised reverse
direction/stop observation for this case only.

[Repeat raw evidence](artifacts/m1-native-reverse-10s-20261007.tar.gz) includes
scripts, profile/model, public ROS data, commands, initial/final readbacks,
summary and per-file hash manifest. Source commit301aaa6.

Independent temporary-script Standards/Spec reviews initially identified incomplete
wheel-feedback guards, stale final-zero acceptance and launch-before-cleanup;
these were fixed and rereviewed before activation. No remaining actionable
finding was reported. The README documents the proven native container device
mapping/group prerequisite; no production Docker/Compose or runtime behavior was
modified as part of this test.

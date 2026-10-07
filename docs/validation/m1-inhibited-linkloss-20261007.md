# M1 inhibited USB link-loss diagnostics — 2026-10-07

Ticket35; source6faf96f. Operator agreed that actual firmware remains unknown,
confirmed onsite raised AMR, and physically unplugged the motor USB→RS485 adapter.
No production runtime code or drive parameter changed. The checked-in bounded
commissioning profile retains explicit UNIDENTIFIED firmware metadata. Unknown
firmware is not treated as a newly discovered version or a prerequisite to this
bounded diagnostic test; production compatibility remains unaccepted.

## Sequence and evidence

An isolated software-only container first built the current M1 package and used
the existing external PTY peer. Native controller-manager initial hardware state
was configured INACTIVE; public services verified exactly M1 INACTIVE and no
loaded controllers. Fresh source-specific inhibited/alarm-free feedback was
required again after those service calls. No command was observed before the
healthy gate. After peer silence, both source diagnostics became ERROR with
feedback_valid=False. Full wire trace after native cleanup contained only ISTOP0
commands: no Servo ON6 or nonzero command. This validates the inactive test setup,
not physical drive behavior. Review findings concerning stale diagnostics,
process exits, mode selection, post-shutdown trace checking and stale readiness
were corrected before real device mapping.

A separate network-none/domain212 container mapped only the motor serial device
with actual GID20. Exclusive CRC/prefix-checked initial FC03 at05:20:38Z confirmed
IDs1/2 status6, alarm0, currentRPM0 and targetRPM0. The same native inactive setup
read healthy inhibited feedback and verified its hardware/controller services;
no controller activation or velocity publisher was used. Operator was then asked
to unplug only the motor USB adapter, leaving it disconnected.

Both sources reported ERROR: `feedback read failed/timeout: Connection timed out;
hardware error, ISTOP requested, physical stop unverified; no automatic re-enable`.
Left diagnostic identified drive2, right drive1; feedback_valid=False and
motion_available=False. Last known motor status/alarm fields are retained context,
not fresh measurements during disconnection. Healthy baseline and subsequent
invalid diagnostics, message-header and receipt timestamps are archived.

The acceptance window began after Operator reported unplugging. Its observed
0.443s to a qualifying fresh diagnostic is NOT unplug-to-detection latency:
actual physical unplug time was not instrumented. This test imposes no invented
physical stopping deadline. Hardware no-Servo-ON/no-nonzero wire-proof fields
remain null because the real serial wire was not independently captured; native
inactive services and software setup proof remain separate evidence.

Shutdown attempted native cleanup and reported failure while the USB remained
unplugged. That failure is retained, not converted into successful deenergization.
All test processes and both temporary containers were removed before requesting
reconnection. A separate exclusive FC03-only probe after reconnection confirms
final physical drive state; no automatic restart or enable is performed.

## Boundary

This confirms real inhibited-device link-loss diagnosis and source identity. It
does not validate stopping on an enabled-drive link failure. Watchdog05-17 remains
0/disabled; command timeout cannot guarantee delivery across a disconnected bus.
Real drive alarms, ground displacement/calibration, production settings, AGX Orin
compatibility and the full Operator workflow remain open. Existing software fault
coverage is reusable and does not replace these physical checks. Ticket35 remains
open with its dependency on subsequent estimation integration unchanged.

[Raw evidence](artifacts/m1-inhibited-linkloss-20261007.tar.gz) retains exact temporary
scripts, profile/model, native parameters/logs, ROS diagnostics, PTY wire trace,
initial/final FC03 and hashes. Scripts are commissioning evidence, not unattended
operator instructions.

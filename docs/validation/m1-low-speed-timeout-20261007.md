# M1 low-speed and command-timeout checks — 2026-10-07

Ticket: Teleop/wheel feedback. Operator explicitly authorized both tests and
confirmed ready with raised AMR, visible wheel markers and onsite observation.
Source0d9d5eb on integration/v1-spec-32; no production runtime code changed.
Dedicated temporary container/domain210/network-none maps only the motor serial
device with its host group20. Existing domain176 sensor view was left intact.
Each trial starts/ends with exclusive FC03 status/alarm/currentRPM/targetRPM
checks, final CRC and per-drive prefix checks. Both drives end inhibited6,
alarm0,currentRPM0,targetRPM0. The temporary motor container was removed.

## Low-speed physical observation

The checked-in commissioning profile uses native limit0.03m/s,150motorRPM,
nominal ratio20/radius0.08m/separation0.555m. Native actual caps/limit, per-source
health/freshness, complete finite left/right feedback and post-zero new samples
are verified before accepting the software observation. Native deactivation succeeds.

Ten-second case:100positive commands,10.000036527s to explicit zero.
Reported feedback range left[-0.005235988,0.392699082]rad/s,
right[0,0.387463094]rad/s. Operator confirms both wheels moved forward and stopped.
Two-second controlled comparison:20positive commands,2.000129371s to explicit zero;
reported feedback peaks0.392699082/0.387463094rad/s. Operator confirms both wheels
moved and stopped. Trace archives contain full timing, not just peak values;
peak assertions alone do not establish uninterrupted speed regulation.

The historical2026-10-02 two-second no-visible-motion observation is not reproduced
under current conditions, including visible markers. Its cause remains unknown.
No code fix, deadband cause, observer error or universal minimum reliable speed is
inferred. The old record remains historical evidence; current two- and ten-second
raised0.03m/s capability has independent physical support.

## Separate command-publication timeout test

Explicit commissioning profile caps300motorRPM/native0.1m/s. Actual native
cmd_vel_timeout reads0.3s. Publish100positive0.1m/s commands over10seconds, then
cease publication for3seconds while hardware remains enabled. Cleanup zero and
native deactivation follow that observation window. Aborts request immediate zero
but cannot pass timeout acceptance. This is not serial/network disconnection.

Independent review caught stale/queued-zero and no-preceding-motion false-positive
risks in the temporary acceptance checker. The corrected checker requires recent
nonzero native output and both wheels moving immediately before silence, verifies
receipt AND message header times, rejects stale zeros or resumed output, and
requires new complete wheel-stop samples before cleanup. Eight adversarial trace
cases were rejected and a valid trace accepted without hardware access. Rereview
reported no actionable remaining finding.

Native zeroing engineering gate0.25–0.5s applies to generated output; receipt must
be within0.5s. Upper margin derives from configured0.3s plus four nominal0.05s
control periods; lower bound rejects unrelated early zeros. This is a test gate,
not a V1 production timing guarantee or a physical-stop deadline. During silence,
an invalid transition aborts immediately after this observation deadline.

Actual observed last-command-to-native-zero receipt0.319094121s; first complete
near-zero wheel feedback0.470864336s. Cleanup zero was only3.105787138s after last
nonzero publication. Message headers and fresh moving-to-zero transition confirm
the zero/stop feedback preceded cleanup. Native deactivation succeeds; independent
final FC03 confirms both drives inhibited/zero. These are bounded observed
latencies, not worst-case guarantees.

Operator reports that the wheels stopped after approximately ten seconds, but
cannot identify the stopping cause. Physical stopping was observed; independent
physical confirmation that timeout preceded cleanup remains UNRESOLVED. The
software trace supports command-timeout zeroing without claiming that additional
physical timing acceptance.

## Remaining scope

Production firmware identity/limits/timing, effective calibration, ground scales,
physical communication-loss stopping and real EKF/Bringup acceptance remain open.
The drive watchdog remains disabled; command timeout cannot prove bus-loss stop.
No EEPROM/RAM drive parameter, controller source, model or TF owner was changed.

[Raw evidence](artifacts/m1-low-speed-timeout-20261007.tar.gz) holds three separate
cases, exact temporary scripts, profiles/model, ROS traces, commands, FC03 bytes,
summary/manifests and the software acceptance-checker test. Archived motor scripts
are evidence, not unsupervised run instructions.

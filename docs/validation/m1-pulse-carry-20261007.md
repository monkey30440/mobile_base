# M1 mode0 pulse carry — 2026-10-07

Source0905809, tickets35/38. Operator confirmed AMR remained raised and was present
with immediate hardware-stop access. This check addresses the fractional/pulse
carry follow-up identified in the previous position-format checkpoint. No runtime
source, drive parameters or formal target profile changed.

## Observed carry and usable commissioning conversion

Prior live parameter reads established both drives01-06=2500,02-14=0, and standard
Index/Pos matching Multi-drive ReadData5/6. Here strict read-only pre/post probes
captured a bounded native0.03m/s short trial. The publisher sent seven nonzero
messages and explicit zero after0.699913s. Native observer completed readiness,
freshness/diagnostics, complete finite feedback and stop/deactivation checks.

| Drive | Before signed Index / unsigned Pos | After Index / Pos | Delta using10000 steps/index | Native velocity-integrated motor turns |
| --- | --- | --- | ---: | ---: |
| Left ID2 | -4 / 3130 | -3 / 1307 | +0.8177 turns | +0.817451 |
| Right ID1 | 2 / 6367 | 1 / 8172 | -0.8195 turns | -0.816792 |

Positive left motor movement increments Index while Pos wraps lower; negative
right motor movement decrements Index while Pos wraps higher. Both observed
endpoint changes are consistent with signed Index plus unsigned residual pulse,
not signed32 concatenation. The documented10000-step/index conversion matches
this fractional carry trial as well as the prior approximately12-turn trial.
Using native receipt-time velocity integration to estimate steps/index gives
9986(left),9852(right); these noisy consistency estimates are not replacement
calibration values. Do not fit separate scales to these samples. Native RPM
quantization/timing and nominal20:1 gear assumptions limit the comparison.

This supplies hardware commissioning evidence for mode0/10000-step interpretation
on these actual configured drives. Wheel-angle conversion can use signed Index +
Pos/10000 motor turns, then configured direction and20:1 gearing, with explicit
position-validity, reset, reconnect and rollover semantics. The point is real
position feedback through the existing M1 adapter and native JointState/RSP,
without fake wheel position or replacement wheel-TF publication.

This is not independent mechanical/ground scale calibration, proof across firmware
or other parameter configurations, or a signed16 Index overflow test. Future
implementation still needs software invalid-data, wrap/reset and reconnect checks;
complete model TF and dynamic estimation acceptance remain open. No position state
interface was implemented by this checkpoint. Earlier reader's position_scale
UNRESOLVED string and signed32 candidate are historical acquisition labels, not
final format conclusions; raw transactions are retained verbatim.

## Stop and ownership evidence

Both pre/post readbacks required exactly inhibited6, alarm0, measuredRPM0 and
native targetRPM0. Position reads occurred only before native launch or after
native observer/launch exit. No concurrent RS485 owner was introduced. Native
explicit-zero, lifecycle deactivation and independent stopped readback completed,
and the dedicated container was removed. Existing development/view containers
were retained. Operator confirmed both wheels moved in the AMR forward direction and finally
stopped. This visual confirmation is separate from native stopped readback.

[Evidence archive](artifacts/m1-pulse-carry-20261007.tar.gz) retains executed
observer/publisher/profile/model, strict read-only script, pre/post raw responses,
actual command/ROS trace, analysis script/results and SHA256 manifest. Observer,
profile and model match the preceding trial; the sole publisher change is the
shorter seven-cycle0.7s bound. Both pre-run reviews found no actionable issues.

Manufacturer evidence: reference/M1-COMM_UM-01-S0686.pdf revision1.1 p24 default
10000steps/index; prior live parameter/register provenance is in
[position-format checkpoint](m1-position-format-20261007.md). Tickets35/38 remain
partial and blockers unchanged.

# M1 position format / raised commissioning check — 2026-10-07

Source b7ad033; ticket35/38 follow-up. Operator confirmed AMR raised and present,
able to observe and immediately stop. Existing reviewed native0.03m/s ten-second
observer/publisher and commissioning profile were reused unchanged, with the
currently verified model. No runtime code or drive parameter was modified.

## Confirmed format, bounded scale evidence

Both actual drives read01-06=2500 and02-14=0 using standard FC03 and checked CRC.
Manufacturer M1 communication manual revision1.1 p24 defines mode0 as Index
(motor-shaft revolutions) plus Step, default10000 steps per index; mode1 is high/low
step representation. Single-phase encoder parameter2500 alone is not that mapping.
Standard current-position4615/4616 are labelled Index/Pos. Their actual values
matched the Multi-drive2 Read Data5/6 pair after the trial for both IDs. These
combined facts establish that the first word must not be concatenated with the
second as a signed32-bit step count in this device configuration.

| Drive | Before signed Index / unsigned Pos | After Index / Pos | Motor-turn delta using documented10000 steps/index | Motor turns from actual native velocity integral |
| --- | --- | --- | ---: | ---: |
| Right ID1 | 14 / 6336 | 2 / 6367 | -11.9969 | -11.9296 |
| Left ID2 | -16 / 3181 | -4 / 3130 | +11.9949 | +11.9402 |

Raw second words exceed2500. The documented10000 default is consistent with actual
position representation and the approximately12 motor-turn movement. It is a
supported commissioning conversion, not an independently calibrated displacement
scale or proof of all encoder settings. Velocity-derived turns use the existing
nominal20:1 gear conversion and observed velocities, trapezoidal receipt-time
integration, including startup/settling samples. Differences of about0.5% are
observations, not accuracy guarantees; RPM quantization/receipt timing are not
removed. A dedicated fractional-turn/low-word wrap check can strengthen the
10000-step mapping before production acceptance. Signed-index rollover, reset,
reconnect and invalid-position cases still require explicit handling/verification
in any subsequent position-state implementation.

Earlier static evidence's signed32_position_raw values are interpretation
candidates only, not real position units. That interpretation is now rejected for
this mode0 configuration. Raw words/transactions remain unchanged and retained.

## Native motion and stopping evidence

The native observer passed readiness, freshness/diagnostics, complete finite wheel
feedback, hardware caps and actual0.03m/s controller limit. Commands were bounded
to ten seconds, followed by explicit zero and native hardware deactivation. Native
observation completed successfully. The pre/post/final independent FC03 probes
strictly required both inhibited(status6), alarm0, currentRPM0 and targetRPM0.
Only one serial owner existed at a time: position/parameter readers ran outside
native-controller lifetime. All temporary containers were removed. No IMU/EKF
or additional serial reader ran during motion.

Operator confirmed both wheels turned in the AMR forward direction and finally
stopped. This is a separate visual observation; no physical turn count was measured. No full-model TF,
position runtime interface, production limits or calibration acceptance is claimed;
tickets35/38 remain partial and dependencies unchanged.

[Evidence](artifacts/m1-position-format-20261007.tar.gz) retains exact native
scripts/profile/model, strict position reader, both read-only parameter-query
versions, FC03 transactions, ROS/command traces, analysis and SHA256 manifest.
The first parameter-query script is reconstructed by removing only the two later
added standard-position reads; provenance records that distinction. Historical
signed32 interpretation is explicitly labelled candidate in the new reader.

Next implementation input: preserve native RSP ownership and provide real wheel
position through the M1 hardware adapter, with explicit mode/scale provenance and
failure/reset/rollover semantics. Do not fabricate JointState position or publish
replacement wheel TF. This checkpoint itself does not implement that change.

Follow-up: [fractional pulse carry](m1-pulse-carry-20261007.md) observed both
Index/Pos carry directions, supporting the documented10000-step commissioning
conversion. Independent mechanical calibration and full runtime/TF acceptance
remain separate.

# M1 wheel hardware

This package fills the confirmed M1-specific device gap from spec #32 / decision #22 / ticket #35. Native `ros2_control` and `diff_drive_controller` own differential kinematics, wheel odometry, velocity limits and command timeout. The adapter only exchanges Modbus Multi-drive2.0 wheel commands and valid velocity and encoder-derived position feedback. It publishes no TF and computes no wheel odometry. `robot_localization` remains the single odom→base_footprint owner.

## Required target profile

Start from `config/rwf.target.yaml` for the inspected RWF target, or use the empty `config/target.template.yaml` for another target. Fill **every** remaining null from applicable evidence. The RWF profile records the user-confirmed path and nominal gear ratio20:1, wheel radius0.08m and wheel separation0.555m. Bounded read-only FC03 evidence confirms transport230400/8N1, left ID2/right ID1, speed mode0, command source4 and PDO mapping0. Velocity feedback is documented in motor RPM (1RPM/count); encoder resolution2500 pulses/rev is a different quantity. User confirms left positive motor RPM and right negative motor RPM move the corresponding wheel forward (`left_direction=+1`, `right_direction=-1`). Actual firmware identity and production permitted limits remain unresolved. `config/rwf.commissioning.yaml` records separate conservative engineering settings for bounded commissioning; its firmware metadata explicitly says UNIDENTIFIED. Nominal geometry is not effective calibration. The incomplete target and empty template fail closed until completed; software fixture values are never deployment defaults. Provenance is recorded in `docs/validation/m1-software.md`.

`gear_ratio` means motor revolutions per wheel revolution; `direction` is +1 or -1 mapping positive wheel radians to positive/CW motor RPM. `feedback_rpm_per_count` converts signed16 current-speed feedback to motor RPM. The minimal adapter supports verified speed mode, Multi-drive2.0, PDO mapping0 or1, two distinct IDs1–8, and status STOP0/RUN2 or WAIT/INHIBIT6 with no alarm. Status6 provides valid feedback but reports WARN/motion unavailable and rejects a nonzero command; it cannot establish Teleop usability. Activation validates no-alarm feedback, reads target speed (index12), requests ISTOP0, and requires target0 before requesting SVON6 once. It polls bounded readiness and target0. Deactivation/shutdown requests ISTOP0 then SVOFF7 only with fresh no-alarm proof, and verifies inhibited readback. Failure returns ERROR. SVOFF can implicitly reset alarms: a captured fault prevents it, but a fault appearing between read and write cannot be ruled out. No explicit alarm reset, parameter edits, STO release or brake manipulation occurs; recovery is deliberate and no automatic re-enable occurs. Operators must establish the verified drive mode and hardware conditions separately.

The communication manual revision1.1 (2025-02-03), pages37–42, specifies FC03 reads at index0 (status/alarm/current speed) and FC10 writes at index8 (Multi-drive Lite command/data), addressed by the drive ID bitmask. The current combined read requests Data0–6 plus each drive's Error_Check: FC03 Num16, drive strides8. It consumes state, alarm, speed and position; the intermediate voltage/current words are not new published capabilities. The earlier Num8/stride4 read covered velocity-only feedback. On the inspected target, each Error_Check equals Modbus CRC16 over the cumulative response prefix to that drive's last requested data word, encoded big endian; the adapter validates both checks. This rule is supported by varied live read-only responses and literal tests, not a universal manufacturer firmware claim. Standard final frame CRC/error handling comes from libmodbus. The adapter enforces at least1.75ms RTU silence or3.5 character times, whichever is longer. Page33 specifies signed16 JG RPM and clamps a nonzero command below60RPM to60RPM. Such commands are rejected and request best-effort zero on both drives; otherwise the adapter could move faster than requested. A verified target with adequate gearing/command range is required; this limitation is not hidden by another kinematics engine.

## Start and Teleop

Build with the repository container workflow. For real hardware, additionally map
the actual host serial device to the configured container path and add its host
device group to the non-root container user. On the inspected AMR this is
`/dev/ttyUSB0` (configured alias `/dev/fihRobotBaseMotor`), group `dialout`/GID20,
mode660. Native Docker `--device` plus `--group-add` provides this access; mapping
alone does not grant Unix group permission. Check the actual host device/group
rather than assuming GID20 on another platform. The minimal development Compose
has no serial mapping or group grant and must not be treated as hardware bringup.
See the raised reverse commissioning record for configure-failure/readback evidence.

Then, inside the correctly provisioned hardware container:

```bash
# Terminal 1: model only; loading the profile opens no motor device.
ros2 launch mobile_base_description description.launch.py hardware_config:=/absolute/target.yaml
# Terminal 2: starts/activates native hardware and controllers (may Servo ON).
ros2 launch mobile_base_control m1.launch.py hardware_config:=/absolute/target.yaml
ros2 control list_controllers
ros2 topic echo /base_controller/odom
ros2 topic echo /diagnostics
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -p stamped:=true -r cmd_vel:=/base_controller/cmd_vel
```

Description alone owns the complete model and native RSP. Supply the **same**
explicit profile to both launches; Description adds the M1 ros2_control declaration
without starting hardware. Control consumes the native `/robot_description` topic
and starts no RSP or other package launch. Its `model_file` argument is removed;
explicit geometry overrides belong to Description. Geometry-only Description
(without hardware_config) cannot initialize M1; restart Description with the
selected profile before starting Control. Do not change profiles/model during a
run or rely on native topic loading to compare two different YAML files. Wrong,
missing or mismatched configuration is an Operator setup error, not readiness.
Native logs/spawner failures must be preserved and resolved. Control startup
without the required description does not establish usable hardware/controllers.

Controller feedback uses velocity, `open_loop=false`, and `enable_odom_tf=false`. Native `/base_controller/cmd_vel` is stamped Twist; `/base_controller/odom` remains the wheel-feedback odometry source. Limits and controller timeout come from the explicit profile.

Before Teleop, cancel Navigation and wait for its native terminal result. Before Navigation, end the Teleop process (Ctrl-C). Do not interpret zero speed, lack of messages, command timeout, controller inactive or zero acknowledgement as session completion or evidence that the physical robot stopped. Use the operator's actual hardware stop procedure and independent observation. Shutdown/deactivation attempts bounded stop/off with readback; error handling requests ISTOP and preserves its cause. A disconnected link cannot guarantee delivery.

## Diagnose

Use `/diagnostics`, native controller logs and `ros2 control list_hardware_components`. Per-wheel status includes drive ID, configured firmware, motor status, alarm code, feedback validity and the basic cause. Communication/CRC/short-response/timeouts and alarms, STO or unknown statuses invalidate both wheels’ velocity/position interfaces; inhibited6 is valid measurement with unavailable motion. Integrity errors invalidate all wheel feedback interfaces; previous data are never substituted as current valid measurements. The controller manager receives ERROR so it can deactivate affected controllers. Fault reset/brake/STO recovery is a deliberate operator hardware procedure, not automatic adapter behavior. Initial read-only observation found both drives in6 WAIT/INHIBIT with no alarm and0RPM. A later bounded zero-speed protocol gate verified SVON transitions both toSTOP0 and SVOFF returns both to6, always alarm0/currentRPM0/target0. Check actual main/CTRL power and the SERVO ON prerequisite before expecting motion; controller active alone does not mean Bringup/Teleop ready. Live communication watchdog05-17=0 is disabled, so a disconnected link/process loss cannot rely on a drive watchdog to stop.

If launch rejects a target fact, complete it from authoritative evidence. If serial connection fails, check the actual container device mapping, path permissions and serial settings. If current-speed/status reads fail, verify Multi-drive2.0 mode, IDs/bitmask and applicable firmware/manual revision. If a command is rejected, check documented minimum RPM, configured gear/direction and speed limits. Do not resume until the cause and hardware conditions are understood.

## Evidence boundary

The software suite uses a pseudo-terminal Modbus peer at the external serial boundary and public ROS topics with the real native controller; fixture geometry, IDs, RPM and timeouts are controlled inputs. Bounded protocol tests verify signed scale/direction, the documented minimum-speed rejection, fault/STO invalidity and inhibited availability. Prefix-check corruption is rejected despite a valid final Modbus CRC. These do not validate real firmware compatibility, encoder feedback, wheel direction, displacement, stopping or calibrated odometry.

**REQUIRES HARDWARE VALIDATION:** verified target startup, valid wheel feedback, motion direction/displacement, alarms/disconnection, timeout/shutdown stop, and Teleop handover. **REQUIRES CALIBRATION:** effective wheel radius/separation, effective gearing/scales/polarity, limits/timeouts and downstream odometry performance. Actual test versions/results are recorded in the implementation evidence; software completion is not hardware acceptance.

Commissioning-only `controller.native_hardware_execution_budget_us` optionally forwards mean/stddev WARN/ERROR microsecond thresholds to native controller-manager hardware diagnostics. Omission/null retains upstream defaults. Statistical thresholds do not prove deadlines; periodicity/overrun diagnostics remain enabled, and genuine ERROR prevents commissioning motion. See the validation record for the measured RS485 timing rationale and interruption-related loss of historical temporary artifacts.

A single raised0.1m/s, two-second native trial confirmed both wheels forward and both stopped by onsite observation; its temporary300RPM/.1m/s profile and raw evidence are archived in the validation record. The earlier0.03m/s trial had no observed wheel motion; on2026-10-07, separate raised0.03m/s two- and ten-second trials had operator-confirmed wheel motion and stopping. The historical symptom was not reproduced and its cause remains unknown. Separate command-silence evidence supports native timeout zeroing before cleanup, but independent physical timeout stop timing remains unresolved. See `docs/validation/m1-low-speed-timeout-20261007.md`. The repository commissioning profile stays150RPM/.03m/s; neither trial establishes minimum reliable velocity, production limits, calibrated odometry or link-loss/isolated-timeout physical stopping.

## Real position state

Confirmed mode0 Index/Pos feedback removes the missing-position/NaN defect recorded in
`docs/validation/real-static-estimation-20261007.md`. The same Multi-drive read
now obtains Data0–6 plus each drive’s prefix check; there is one serial owner and
no added runtime TF or JointState publisher. Full base-to-wheel TF also requires an explicit
model responsibility for the intervening drive seats. The V1 description uses
Operator-confirmed nominal fixed seats; M1 does not measure their suspension travel. Native JointState broadcaster exposes
position; native RSP consumes it. Native diff_drive_controller continues using
velocity feedback (`position_feedback=false`); odometry ownership is unchanged.

An explicit profile must supply `position_format: 0`, each wheel’s
`position_steps_per_motor_revolution` and `encoder_pulses_per_motor_revolution`.
Configure reads actual02-14 and01-06 for each ID before Servo ON, rejecting mismatch.
Only the validated mode0 is supported; mode1 is not guessed. RWF commissioning
uses10000 steps/motor turn and2500 single-phase encoder pulses, backed by actual
register and fractional-carry checks, not independent mechanical calibration.

First valid sample uses the device counter origin, not a calibrated mechanical
wheel phase. Subsequent signed16 Index carry is unwrapped from real count deltas.
Pulse out of range or a jump exceeding configured motor RPM with bounded response
timing allowance invalidates all wheel feedback and latches a position fault until
explicit reconfigure. Detected reset is not silently rebased during an active run.
A reset whose delta resembles physically possible motion cannot be distinguished
by this protocol; power/reset recovery requires a deliberate new configure epoch.
Do not change drive format/encoder parameters while running. A configure/reconnect
starts a new device-origin reference, without claiming cross-reset continuity.
Physical signed-index overflow and power-reset behavior are not hardware-accepted.

## Package and verification phase (2026-10-07)

This package replaces mobile_base_m1; its plugin is mobile_base_control/M1System.
Protocol and public native control workflow tests remain in this package and
use its installed m1.launch.py entry with explicit hardware_config, after
independently starting Description with the same profile.
Core device acceptance precedes ticket #38 local estimation integration and
#39/#41 product Bringup delivery. No calibrated covariance or default deployment
model is supplied by this component entry.

# M1 configuration and position-feedback evidence

## Confirmed hardware observations

The [2026-09-09 configuration dump](m1-current-settings-20260909-172133.md)
and its [raw JSON record](m1-current-settings-20260909-172133.json) establish:

| M1 parameter | EEPROM / active RAM | Slave 1 | Slave 2 |
|---|---|---|---|
| 01-06 Encoder Resolution | `0x0105` / `0x3D05` | 2500 | 2500 |
| 02-14 Position Command Format | `0x020D` / `0x3E0D` | 0 | 0 |

Normal FC03 configuration reads, including `0x3D05`, succeeded on the AMR.
These observations are reused; no new hardware experiment was performed.
The encoder-resolution value is M1-owned and is not a ROS configuration input.
65535 is not the observed encoder-resolution value.

## Meaning established by the vendor manuals

The private vendor manuals are under `src/mobile_base_control/docs/`:

- `M1-UserManual_UM-01-S0701.pdf`, revision 1.0, printed page 3:
  01-06 is the encoder's single-phase pulse count per motor-shaft revolution.
- `M1-COMM_UM-01-S0686.pdf`, revision 1.1, printed pages 15 and 17:
  the 01-06 and 02-14 parameter tables identify their RAM addresses and meanings.
- The communication manual, sections 4.3–4.3.1, printed pages 24–25:
  position-command examples use a default of 10,000 steps per revolution.
  The examples do not establish a formula relating Multi-drive 2.0 feedback to 01-06.
- Section 6.3, printed pages 37–38, lists current-position high/low words
  (or Hall counts). It does not unambiguously establish the feedback scale
  or the effect of 02-14 on those words.

The checked-in conversion code previously consumed a ROS-supplied divisor;
it is not independent evidence of device semantics. Neither the manual defaults
nor the captured value 2500 proves a production divisor of 2500, 10000, 65535,
or any other number. The user manual's divided pulse-output example (page 12)
describes a different signal and does not prove the position-feedback scale.

## Current verification boundary

The production [driver](../src/mobile_base_control/src/m1_driver.cpp) reads the
confirmed configuration semantics. Its `M1DeviceConfig` snapshot represents only
confirmed M1-derived fields (`driver_id`, `encoder_resolution_pulses_per_rev`,
`position_command_format`). Position feedback scaling is not an M1 configuration
property and remains unverified. Raw `MotorState::position_steps` currently represents
the two words packed as a signed 32-bit integer; its physical interpretation remains unverified.

The [hardware interface](../src/mobile_base_control/src/m1_hardware.cpp) can
configure successfully after both reads, but rejects activation before Servo-On
when either feedback scale is unavailable. It does not publish guessed wheel
positions or accept motion. This implements the unavailable-feedback boundary
of SYS-029 and the activation boundary of SYS-030; it does not establish full
hardware compliance with those requirements. Default `serial_port=mock` provides
no configuration/scale fixture; software tests inject explicit fixtures.

Software tests cover configuration reads and failures, snapshot invalidation,
activation refusal, and conversion using independent synthetic per-drive scales.
Those fixtures are not hardware evidence or production defaults. Package results
are recorded by the existing colcon workflow under `build/*/test_results/` and
`log/latest_test/`; software evidence cannot establish the missing physical scale.

Software verification on 2026-09-10 used the existing
`mobile_base-mobile_base:latest` development image with the workspace mounted and
no hardware devices. Both affected packages built successfully:

```bash
colcon build --packages-select mobile_base_control mobile_base_description --cmake-args -DBUILD_TESTING=ON
colcon test --packages-select mobile_base_control mobile_base_description --return-code-on-test-failure
```

All 90 C++ tests and the launch/URDF functional tests passed. Formatting checks
passed after correction. Full package validation is **not entirely green**:
both packages' `xmllint` checks cannot retrieve the unchanged package XML's
external `http://download.ros.org/schema/package_format3.xsd`, including with
network access. The existing cppcheck wrapper skips 31 checks because of its
cppcheck 2.13.0 performance policy. These remain unverified; no XML validation or
static-analysis success is inferred from the functional tests.

GitNexus impact checks were attempted before changes and `detect_changes` after
changes. The MCP graph retained stale/incomplete dependency information despite
a local index refresh, so complete dependency impact could not be determined.
Direct source inspection and the affected package tests provide the additional
software evidence; the graph's zero-caller results are not proof of zero impact.

## Required later hardware verification

With the AMR available and secured for a manual shaft rotation:

1. Record the drive identity/firmware, active 01-06 and 02-14, and both raw
   Multi-drive current-position words, plus their current `position_steps` packing.
2. Record the initial position, rotate the **motor shaft** exactly one revolution
   in a known direction, and record the final position and raw words.
3. Determine the actual word interpretation and position delta. Check whether an
   Index/Step transition occurs with 02-14=0; a packed integer delta alone must
   not be mistaken for a linear count if the words encode turns and subturns.
4. Repeat in the reverse direction and across a turn boundary; verify both drives
   before enabling production conversion. Record the evidence and its applicable
   configuration/firmware alongside this dump.
5. Implement the established relationship in the driver-owned configuration path,
   then validate wheel position, direction, rollover, and feedback odometry on the
   AMR. Update the tracker/decoder if the words are not a signed linear count.

Blocked: production position conversion, M1Hardware activation, and physical
wheel/odometry validation. No new controller-on-hardware or physical-observation
validation has been performed, and this change does not establish Feature Freeze.

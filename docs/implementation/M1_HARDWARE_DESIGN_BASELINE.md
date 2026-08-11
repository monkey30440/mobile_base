# M1Hardware Design Baseline

**Project:** mobile_base  
**Scope:** ros2_control hardware layer for the M1 differential-drive base  
**Status:** MVP design baseline  
**Date:** 2026-08-11

---

## 1. Architecture

The MVP motor stack is:

```text
Nav2
  |
  v
diff_drive_controller
  |
  v
ros2_control
  |
  v
M1Hardware
  |
  v
M1Driver
  |
  v
libmodbus
  |
  v
RS485 / M1 × 2
```

The previous independent `SerialTransport` application layer is removed from
the MVP.

This does **not** change the `M1Hardware` public design.

`M1Hardware` only depends on `M1Driver`'s motor-oriented API and must never
depend directly on libmodbus.

---

## 2. Responsibility boundary

`M1Hardware` owns:

```text
ROS 2 / ros2_control lifecycle
joint command/state interfaces
left/right driver mapping
wheel rad/s <-> motor RPM conversion
gear ratio
motor direction signs
command validation / clamp / rounding
continuous position tracking
motor position -> wheel position [rad]
motor RPM -> wheel velocity [rad/s]
device-health policy
ros2_control ERROR policy
activation/deactivation sequencing
cached/latest motor state for the A2 control model
```

`M1Hardware` does **not** own:

```text
Modbus
Multi-drive 2.0 address layout
FC03 / FC17 frame semantics
driver bitmap
JG / SVON / SVOFF encoding
CRC / RTU framing
libmodbus context
serial open/read/write
raw response parsing
Standard Modbus register implementation
```

Those belong to `M1Driver` and its private libmodbus implementation.

---

## 3. Robot / motor baseline

Current baseline:

```text
wheel_radius     = 0.08 m
wheel_separation = 0.5545 m
gear_ratio       = 20.0

ID1 = right motor
ID2 = left motor

right motor sign = -1
left motor sign  = +1
```

Important ownership rule:

```text
wheel_radius / wheel_separation
-> diff_drive_controller configuration

gear_ratio / motor sign / driver mapping
-> M1Hardware
```

`M1Hardware` does **not** need wheel radius or wheel separation to translate
wheel angular velocity into motor RPM.

---

## 4. ros2_control joint contract

MVP exports:

```text
left_wheel_joint
  command:
    velocity [rad/s]
  state:
    position [rad]
    velocity [rad/s]

right_wheel_joint
  command:
    velocity [rad/s]
  state:
    position [rad]
    velocity [rad/s]
```

`diff_drive_controller` converts robot-level linear/angular motion into wheel
angular-velocity commands.

`M1Hardware` begins at those wheel joint commands.

---

## 5. Driver-facing data

`M1Hardware` consumes the M1Driver data model:

```cpp
struct MotorCommand
{
  int driver_id;
  int16_t target_rpm;
};

struct MotorState
{
  int driver_id;
  int16_t actual_rpm;
  int32_t position_steps;
  uint16_t status;
  uint16_t alarm;
};

struct ExchangeResult
{
  std::array<MotorState, 2> states;
};
```

`M1Hardware` maps:

```text
ID1 -> right wheel
ID2 -> left wheel
```

M1Driver itself remains unaware of left/right robot semantics.

---

## 6. A2 control-loop model

Frozen MVP decision: **A2**.

```text
M1Hardware::read()
    |
    +-- consume latest_motor_state_
    +-- update ROS joint position/velocity
    |
controller_manager update
    |
M1Hardware::write()
    |
    +-- convert wheel command -> motor RPM
    +-- M1Driver::exchange()
    +-- cache returned motor state
```

Normal ACTIVE `read()` performs no communication transaction.

Normal ACTIVE `write()` performs one M1Driver FC17 exchange.

This keeps one runtime communication transaction per control cycle.

---

## 7. Command conversion

Input from ros2_control:

```text
wheel velocity [rad/s]
```

Motor command:

```text
motor_rpm =
    wheel_rad_s
    * 60 / (2*pi)
    * gear_ratio
    * motor_sign
```

Current signs:

```text
left  / ID2 = +1
right / ID1 = -1
```

M1Hardware then:

```text
validate finite command
clamp to operational motor RPM limit
round to integer RPM
build MotorCommand
```

M1Driver receives only the final motor-domain integer RPM.

---

## 8. Velocity feedback conversion

From M1Driver:

```text
actual_rpm
```

Convert:

```text
wheel_rad_s =
    actual_rpm
    * motor_sign
    / gear_ratio
    * 2*pi / 60
```

The same sign convention is used for command and feedback.

ROS-positive wheel velocity always represents the robot-forward wheel
direction on both sides.

---

## 9. Position baseline

Selected M1 position format:

```text
02-14 = 1
```

M1Driver returns:

```text
signed int32 position_steps
```

M1Hardware converts the raw finite-width counter into a continuous relative
position using one `PositionTracker` per motor.

```text
raw int32 position_steps
        |
        v
PositionTracker
        |
        v
continuous int64 motor steps
        |
        v
motor rotation
        |
        / gear_ratio
        v
wheel position [rad]
        |
        * motor_sign
        v
ROS joint position
```

---

## 10. PositionTracker

MVP state:

```cpp
struct PositionTracker
{
  bool initialized;
  int32_t previous_raw;
  int64_t accumulated_steps;
};
```

Behavior:

```text
first valid sample:
  previous_raw = current_raw
  accumulated_steps = 0

later sample:
  compute wrapped int32 delta
  accumulated_steps += delta
```

Purpose:

```text
preserve continuous relative motor position across int32 rollover
```

MVP activation policy:

```text
every on_activate()
-> current motor position becomes the new ROS joint-position origin
-> position starts from 0 rad
```

MVP does not preserve absolute odometry across process/lifecycle restart.

---

## 11. Position scaling

The verified mechanical baseline is:

```text
encoder resolution = 2500 pulse/rev
effective motor position scale used in validation = 10000 steps/motor rev
gear ratio = 20.0
```

Therefore the currently validated nominal relationship is:

```text
200000 motor steps
= 1 wheel revolution
= 2*pi wheel rad
```

Thus:

```text
wheel_position_rad =
    continuous_motor_steps
    * 2*pi / 200000
    * motor_sign
```

This conversion belongs only in `M1Hardware`.

If future M1 configuration changes encoder resolution, position format, or
mechanical gearing, this scale must be revalidated rather than silently assumed.

---

## 12. on_init()

`on_init()` is configuration only.

Minimum responsibilities:

```text
parse mandatory hardware parameters
validate driver IDs
validate gear ratio
validate motor signs
validate motor-position scale
initialize ROS command/state values
initialize PositionTracker objects
construct/configure M1Driver
```

Do not:

```text
enable motors
send motion commands
perform normal runtime traffic
```

MVP mandatory configuration conceptually includes:

```text
serial device
baud
left_driver_id
right_driver_id
gear_ratio
left_sign
right_sign
motor_steps_per_rev or equivalent validated position scale
operational max_motor_rpm
```

Serial/RTU details are passed to M1Driver configuration; they are not used
directly by M1Hardware after construction.

---

## 13. on_activate()

MVP sequence:

```text
M1Driver.connect()
        |
        v
M1Driver.read_state()
        |
        v
verify:
  communication succeeded
  alarm == 0
  RPM == 0
        |
        v
reset left/right PositionTracker
set ROS positions = 0
set ROS velocity commands = 0
        |
        v
M1Driver.enable()
        |
        v
bounded read_state() polling
        |
        +-- status leaves WAIT/INHIBIT
        +-- alarm remains 0
        +-- RPM remains 0
        |
        v
ACTIVE
```

Hardware evidence:

```text
SVON immediate FC17 response can still show status=6.
A later poll changes to status=0.
```

Therefore activation must use a bounded transition check rather than assuming
the immediate response is final.

Exact poll delay/count remains open.

---

## 14. read()

While ACTIVE:

```text
latest_motor_state_
        |
        +-- validate state availability/health
        |
        +-- actual_rpm -> wheel velocity [rad/s]
        |
        +-- position_steps
                |
                v
          PositionTracker
                |
                v
          wheel position [rad]
```

`read()` normally performs no communication.

It must not fabricate state when no valid state has been received.

---

## 15. write()

Normal ACTIVE path:

```text
ROS left/right wheel velocity command
        |
        v
validate / convert / sign / clamp / round
        |
        v
MotorCommand ID1 + ID2
        |
        v
M1Driver.exchange()
        |
        v
ExchangeResult
        |
        v
latest_motor_state_
```

A successful exchange replaces the cached state.

A communication/protocol failure is propagated upward; MVP does not silently
retry indefinitely.

---

## 16. Operational RPM limit

`M1Hardware` owns an operational `max_motor_rpm` clamp.

This is intentionally different from the drive's absolute/no-load RPM.

The final deployment value is **not yet frozen**.

It should be selected from robot-level speed/safety requirements and then
verified against the configured `diff_drive_controller` limits.

---

## 17. Device-health policy

M1Driver reports protocol transaction success independently from drive state.

Example:

```text
FC17 response is structurally valid
alarm = 21
```

means:

```text
M1Driver transaction: success
M1Hardware health decision: unhealthy / ERROR
```

M1Hardware owns checks such as:

```text
alarm != 0
unexpected lifecycle status
communication failure
invalid/no latest state
```

MVP does not automatically clear alarms.

---

## 18. stop behavior

Normal controlled stop:

```text
M1Driver.stop()
-> FC17 JG 0 + state
```

Hardware evidence shows the first stop response may still contain a non-zero
RPM sample.

Therefore M1Hardware owns bounded stop confirmation:

```text
repeat/check zero-RPM state a small bounded number of times
```

Exact threshold/retry count is not yet frozen.

---

## 19. on_deactivate()

MVP sequence:

```text
set ROS command variables to zero
        |
        v
M1Driver.stop()
        |
        v
bounded zero-RPM confirmation
        |
        v
M1Driver.disable()
        |
        v
bounded lifecycle polling if needed
        |
        v
M1Driver.disconnect()
```

Hardware evidence:

```text
SVOFF immediate response can still show status=0.
A later poll changes to status=6.
```

Shutdown policy is best-effort:

> A failure in one stop/disable action must not prevent attempting the remaining
> safe shutdown actions.

No independent `SerialTransport` cleanup step exists in the new MVP
architecture; `M1Driver.disconnect()` owns the private libmodbus context.

---

## 20. Error propagation

```text
libmodbus / RTU failure
        |
        v
M1Driver Result<...>
        |
        v
M1Hardware
        |
        v
ros2_control return type / lifecycle error
```

M1Hardware should log:

```text
operation
driver IDs
error category
latest status/alarm when available
```

It should not expose libmodbus types, `errno`, or libmodbus error objects to
ros2_control-facing interfaces. M1Hardware only consumes M1Driver `ErrorCode`
categories and motor state.

---

## 21. Runtime M1Driver contract

M1Hardware relies on this frozen intent:

```text
read_state()
  -> read both motor states

enable()
  -> request Servo ON for both motors and return immediate state

exchange()
  -> send both motor RPM commands and return state

stop()
  -> command both motor RPM to zero and return state

disable()
  -> request Servo OFF for both motors and return immediate state
```

M1Hardware does **not** care whether these are encoded as FC03, FC17, how raw
request/response validation is implemented, or how libmodbus transports them.

That implementation detail remains fully inside M1Driver.

---

## 22. Hardware evidence already supporting M1Hardware

Verified:

```text
ID1 = right motor
ID2 = left motor

ID1 +RPM corresponds to ROS-negative right-wheel direction
ID2 +RPM corresponds to ROS-positive left-wheel direction

gear ratio ~= 20:1 on both sides

02-14 = 1

Multi-drive 2.0 FC03 reads both drivers

FC17 JG/RPM controls and returns feedback

FC17 JG0 stops

FC17 SVON transitions status 6 -> 0

FC17 SVOFF transitions status 0 -> 6
```

Thus the principal M1Hardware lifecycle assumptions are supported by hardware
evidence.

---

## 23. Timing status

Existing communication measurements reached roughly the mid-20 ms range.

Therefore:

```text
50 Hz controller period = 20 ms
```

is not accepted as the current baseline.

Still open:

```text
controller_manager update_rate
M1Driver/libmodbus response timeout
M1 watchdog configuration
SVON/SVOFF poll delay/count
stop confirmation threshold/count
```

These are system timing decisions, not M1Hardware architecture decisions.

---

## 24. Software-test baseline

Pure tests should cover:

```text
wheel rad/s -> motor RPM
motor RPM -> wheel rad/s
left/right signs
RPM clamp/rounding
position scale
PositionTracker initialization
positive/negative movement
positive/negative rollover
activate state machine using fake M1Driver
write success/failure
alarm -> hardware error
stop/deactivate best-effort behavior
SVON/SVOFF delayed transition handling
```

A fake M1Driver is sufficient for these tests; a fake transport layer is not
required by the MVP architecture.

---

## 25. MVP non-goals

Do not add yet:

```text
SerialTransport abstraction
background communication thread
automatic reconnect
complex retry state machine
automatic alarm reset
persistent odometry across restart
runtime encoder/gear auto-calibration
generic N-motor hardware architecture
CAN backend support
```

---

## 26. Frozen architecture

```text
diff_drive_controller
        |
        | wheel velocity command [rad/s]
        v
M1Hardware
  - ROS lifecycle
  - left/right mapping
  - gear ratio / signs
  - command clamp
  - PositionTracker
  - wheel state conversion
  - health/error policy
  - A2 cached state
        |
        | MotorCommand / MotorState
        v
M1Driver
  - M1 / Multi-drive 2.0
  - runtime lifecycle protocol
  - Standard Modbus maintenance access
  - private libmodbus implementation
        |
        v
libmodbus
        |
        v
RS485
        |
  +-----+-----+
  |           |
M1 ID1      M1 ID2
right       left
```

Boundary rule:

> `M1Hardware` knows ROS and robot semantics, but not Modbus or libmodbus.  
> `M1Driver` knows M1 / Multi-drive 2.0 and privately owns libmodbus, but not
> robot geometry or ROS joint semantics.

**M1Hardware MVP design: FROZEN.**

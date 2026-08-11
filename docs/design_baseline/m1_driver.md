# M1Driver Design Baseline

**Project:** mobile_base  
**Scope:** M1 protocol / runtime communication layer  
**Status:** MVP design baseline  
**Date:** 2026-08-11

---

## 1. Architecture

The MVP motor stack is now intentionally **two application layers**:

```text
ros2_control / diff_drive_controller
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

There is **no independent `SerialTransport` class in the MVP**.

`libmodbus` is a private implementation detail of `M1Driver`.
No libmodbus type, function, or raw Modbus representation may leak into
`M1Hardware`.

If a second transport/backend is required in the future, a transport
abstraction can be extracted later without changing the
`M1Hardware <-> M1Driver` public contract.

---

## 2. M1Driver responsibilities

`M1Driver` owns:

```text
M1 protocol semantics
Multi-drive 2.0 addressing / driver bitmap
Multi-drive 2.0 FC03 / FC17 request construction
JG / SVON / SVOFF command encoding
signed RPM encoding / decoding
signed int32 position decoding
response semantic validation
M1 MotorState parsing
runtime lifecycle protocol
Standard Modbus register access for configuration / maintenance

libmodbus RTU context ownership
connect / disconnect
response timeout configuration
raw request send / response receive
mapping libmodbus failures into ErrorCode
request/response ordering for the selected driver IDs
```

`M1Driver` does **not** own:

```text
ROS 2 / ros2_control lifecycle
left/right wheel semantics
wheel rad/s <-> motor RPM conversion
gear ratio
wheel radius
wheel separation
robot kinematics
continuous position rollover tracking
wheel position [rad]
device-health policy such as "alarm means ros2_control ERROR"
```

---

## 3. Runtime protocol policy

Normal ros2_control runtime should use Multi-drive 2.0 as much as practical.

Frozen runtime path:

```text
read_state()
    -> Multi-drive 2.0 FC03

enable()
    -> Multi-drive 2.0 FC17 + SVON + simultaneous state read

exchange()
    -> Multi-drive 2.0 FC17 + JG/RPM + simultaneous state read

stop()
    -> Multi-drive 2.0 FC17 + JG/0 + simultaneous state read

disable()
    -> Multi-drive 2.0 FC17 + SVOFF + simultaneous state read
```

Principle:

> Prefer Multi-drive 2.0 for runtime control, but do not force every operation
> through FC17 when Multi-drive 2.0 FC03 is the natural read-only operation.

Standard Modbus register access remains available only for configuration,
startup validation, maintenance, and diagnostics.

---

## 4. Hardware baseline

Current verified baseline:

```text
RS485 device       = /dev/ttyUSB0
RTU settings       = 230400, 8N1

ID1 = right motor
ID2 = left motor

09-26 = 0
02-14 = 1
01-06 = 2500 pulse/rev

gear_ratio = 20.0

right motor native sign = -1 relative to ROS-forward wheel direction
left motor native sign  = +1 relative to ROS-forward wheel direction
```

The driver layer does not interpret the sign as left/right robot motion.
It only preserves M1-native RPM and position values.

---

## 5. Runtime data model

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

Rules:

```text
M1Driver does not know "left" or "right".
Every state carries driver_id.
RPM is already an integer motor-domain value.
position_steps is raw M1 signed-int32 position semantics.
```

Continuous position tracking belongs to `M1Hardware`.

---

## 6. Public API

MVP public API:

```cpp
class M1Driver
{
public:
  Result<void> connect();
  Result<void> disconnect();

  Result<ExchangeResult> read_state(
      int driver_a,
      int driver_b);

  Result<ExchangeResult> enable(
      int driver_a,
      int driver_b);

  Result<ExchangeResult> exchange(
      const MotorCommand& command_a,
      const MotorCommand& command_b);

  Result<ExchangeResult> stop(
      int driver_a,
      int driver_b);

  Result<ExchangeResult> disable(
      int driver_a,
      int driver_b);

  // Configuration / maintenance only.
  Result<uint16_t> read_register(
      int driver_id,
      uint16_t address);

  Result<void> write_register(
      int driver_id,
      uint16_t address,
      uint16_t value);

private:
  modbus_t* ctx_{nullptr};
};
```

`modbus_t*` is private and must never appear in the public API.

---

## 7. connect()

`connect()` owns RTU setup through libmodbus.

Conceptual responsibilities:

```text
reject a repeated connect while already connected
create RTU context
configure device / baud / parity / data bits / stop bits
configure response timeout
connect
return Result<void>
```

Frozen lifecycle invariant:

```text
connect() success -> ctx_ != nullptr and communication is ready
connect() failure -> all partial resources are released and ctx_ == nullptr
repeated connect while ctx_ != nullptr -> ALREADY_CONNECTED
```

`ctx_` is deliberately the single connection-state indicator for the MVP; do
not add a second `is_connected_` flag.

For the current MVP:

```text
device = /dev/ttyUSB0
baud   = 230400
8N1
```

The exact final response timeout is intentionally not frozen yet.

No motor enable or motion command occurs in `connect()`.

---

## 8. disconnect()

`disconnect()` only releases communication resources.

It does **not** replace the motor stop/disable lifecycle.

Expected shutdown order is owned by `M1Hardware`:

```text
stop
disable
disconnect
```

`disconnect()` must remain safe to call after partial failures.

Frozen cleanup behavior:

```text
ctx_ != nullptr -> modbus_close() + modbus_free() + ctx_ = nullptr
ctx_ == nullptr -> return success
```

Therefore repeated `disconnect()` is intentionally safe/idempotent. A destructor
may perform final communication-resource cleanup, but must not issue JG0, SVON,
or SVOFF commands; motor safety actions belong to the explicit lifecycle.

---

## 9. Private transaction boundary

Although there is no `SerialTransport` class, libmodbus calls should remain
concentrated in a very small private boundary.

Recommended internal shape:

```cpp
Result<std::vector<uint8_t>> transact(
    const std::vector<uint8_t>& request_without_backend_crc);
```

Conceptually:

```text
protocol helper builds request
        |
        v
transact()
        |
        +-- libmodbus raw send
        +-- libmodbus receive confirmation
        +-- map timeout/I/O failure
        |
        v
raw response bytes
        |
        v
M1Driver validator / parser
```

This preserves an extraction point if a future transport abstraction becomes
necessary.

Do not scatter raw libmodbus calls across every protocol helper.

---

## 10. CRC / RTU framing ownership

With the selected libmodbus backend:

```text
M1Driver
  -> constructs the Multi-drive 2.0 request semantics

libmodbus RTU backend
  -> owns backend RTU framing / CRC during actual transport
```

Therefore the production M1Driver request builder should not independently
append a second RTU CRC before sending through the libmodbus raw-request path.

However, M1Driver still owns response **semantic validation**:

```text
expected function code
expected group/unit semantics
byte count
response length
exception response
driver block count/order
Multi-drive payload structure
```

Do not assume low-level receive success means the response is semantically the
response M1Driver expected.

---

## 11. Multi-drive 2.0 read_state()

Purpose:

```text
read both M1 states without writing a motor command
```

Runtime implementation:

```text
Multi-drive 2.0 FC03
one request
driver bitmap selects ID1 + ID2
Read Data0..Data6
```

Returned state fields:

```text
Data0 -> status
Data1 -> alarm
Data2 -> actual_rpm
Data5 + Data6 -> signed int32 position_steps
```

Data3/Data4 are not part of the MVP control-state model.

Hardware test status:

```text
PASS
```

One Multi-drive 2.0 FC03 request successfully returned both drivers and matched
the Standard Modbus reference for status, alarm, RPM, and position semantics.

---

## 12. Generic FC17 command path

Do not implement separate FC17 frame builders for JG, SVON, and SVOFF.

Use one generic command builder internally:

```text
(driver_id, command_code, data)
(driver_id, command_code, data)
```

Applications:

```text
enable()   -> SVON, 0
exchange() -> JG, signed RPM
stop()     -> JG, 0
disable()  -> SVOFF, 0
```

Current `09-26 = 0` runtime mapping uses:

```text
Write Data8 = Multi-drive Lite command
Write Data9 = command data
```

The same FC17 command path simultaneously reads Data0..Data6.

---

## 13. enable()

Runtime implementation:

```text
FC17
ID1 -> SVON, 0
ID2 -> SVON, 0
+
simultaneous state read
```

Hardware-verified behavior:

```text
immediate response may still show status=6
a later poll shows status=0
RPM remains 0
alarm remains 0
```

Therefore:

```text
M1Driver enable() = transaction
M1Hardware        = lifecycle transition policy / bounded polling
```

`M1Driver` must not hide an unbounded wait/retry state machine inside
`enable()`.

---

## 14. exchange()

Normal ACTIVE control transaction:

```text
FC17

ID1 -> JG + target RPM
ID2 -> JG + target RPM

simultaneously read both states
```

`exchange()` receives already converted integer motor RPM commands.

It must not perform:

```text
gear ratio conversion
left/right sign conversion
wheel rad/s conversion
robot motion policy
```

Hardware test status:

```text
PASS
```

FC17 JG/RPM has already controlled both drives and returned state feedback.

---

## 15. stop()

`stop()` is a convenience API using the same generic FC17 command path:

```text
ID1 -> JG 0
ID2 -> JG 0
+
state feedback
```

Hardware evidence shows the immediate response can still contain the previous
non-zero RPM. Final stop confirmation is therefore an upper-layer policy.

---

## 16. disable()

Runtime implementation:

```text
FC17
ID1 -> SVOFF, 0
ID2 -> SVOFF, 0
+
simultaneous state read
```

Hardware-verified behavior:

```text
immediate response may still show status=0
a later poll shows status=6
RPM remains 0
alarm remains 0
```

Again, bounded transition checking belongs to `M1Hardware`.

---

## 17. Standard Modbus register path

Standard Modbus is intentionally outside the normal runtime control loop.

Keep small helpers:

```text
read_register()
write_register()
```

Typical use:

```text
02-14 position format
05-17 / 05-18 / 05-21 watchdog configuration
09-19 driver ID
09-20 baud selection
09-26 Multi-drive 2.0 mapping
NET-IN maintenance/fallback access
other startup/configuration checks
```

Do not interleave these register transactions into every ros2_control control
cycle.

---

## 18. Response validation and parser

The fixed protocol pipeline is:

```text
build request
    -> transact()
    -> validate response
    -> parse MotorState
```

`transact()` does not decide whether an FC03/FC17 response has the expected
M1 semantics. Validation occurs before parsing and checks, at minimum:

```text
expected function code
exception response
byte count / total response length consistency
expected Multi-drive payload/block structure
expected selected-driver block count/order
```

RTU CRC is not independently recalculated by the M1Driver semantic validator;
backend RTU framing/CRC belongs to libmodbus.

### 18.1 Response parser

FC03 and FC17 share one MotorState parsing implementation after their
respective framing/header validation. Driver IDs are placed in a deterministic
ascending order when constructing the request, and returned state blocks are
mapped using that same ordered-ID list. Robot left/right meaning is not inferred
from response position.

Minimum decode:

```text
Data0 -> uint16 status
Data1 -> uint16 alarm
Data2 -> int16 actual_rpm
Data5 + Data6 -> int32 position_steps
```

Explicit signed conversion is required.

Each selected driver contributes the verified Multi-drive state block:

```text
Data0..Data6 + Error_Check = 8 words = 16 bytes per driver
```

For the two-driver MVP the state payload is therefore 32 bytes. Parsing uses
word indices rather than scattered magic byte offsets. The response payload
start is derived from the libmodbus backend/header semantics used by the raw
receive path.

Do not perform position rollover unwrapping here.

---

## 19. Error model

MVP uses a compact result/error model rather than `bool` or a large exception
hierarchy.

```cpp
enum class ErrorCode
{
  NONE,

  CONTEXT_CREATE_FAILED,
  CONFIG_FAILED,
  CONNECT_FAILED,
  ALREADY_CONNECTED,

  NOT_CONNECTED,
  SEND_FAILED,
  TIMEOUT,
  RECEIVE_FAILED,

  BAD_FUNCTION,
  BAD_LENGTH,
  INVALID_RESPONSE,
  MODBUS_EXCEPTION,
};
```

Example result:

```cpp
template<typename T>
struct Result
{
  bool ok;
  ErrorCode error;
  T value;
};
```

Error ownership is deliberately split:

```text
connect/configuration
  -> CONTEXT_CREATE_FAILED / CONFIG_FAILED / CONNECT_FAILED / ALREADY_CONNECTED

transact() communication
  -> NOT_CONNECTED / SEND_FAILED / TIMEOUT / RECEIVE_FAILED

response semantic validation
  -> BAD_FUNCTION / BAD_LENGTH / INVALID_RESPONSE / MODBUS_EXCEPTION
```

Raw `errno` / libmodbus error details remain inside M1Driver and may be logged
for diagnostics, but must not leak into M1Hardware.

Important rule:

```text
valid transaction
MotorState.alarm != 0
```

is still a successful protocol transaction.

Device-health policy belongs to `M1Hardware`.

---

## 20. Unit-test boundary

The following must remain pure and testable without hardware/libmodbus I/O:

```text
driver bitmap calculation
FC03 request semantic construction
FC17 request semantic construction
signed RPM encoding/decoding
signed int32 position decoding
response semantic validation
MotorState parsing
driver order mapping
boundary values
```

The libmodbus-dependent integration surface is intentionally small:

```text
connect()
transact()
disconnect()
```

This is sufficient for MVP testability without introducing a third transport
abstraction.

---

## 21. Hardware evidence

Current relevant hardware evidence:

```text
Multi-drive 2.0 FC03 ID1+ID2 read       PASS
FC17 JG/RPM + simultaneous state        PASS
FC17 JG0 stop path                      PASS
FC17 SVON lifecycle                     PASS
FC17 SVOFF lifecycle                    PASS

gear ratio 20:1 left                    PASS
gear ratio 20:1 right                   PASS

ID1 right-wheel native direction        verified
ID2 left-wheel native direction         verified

02-14 = 1 on both drivers               verified
```

Thus the runtime protocol selected by this baseline has hardware evidence.

---

## 22. Timing status

Existing FC17 measurements showed response/transaction time reaching roughly
the mid-20 ms range.

Therefore:

```text
50 Hz control period = 20 ms
```

is not accepted as the current baseline.

Still open:

```text
final controller update_rate
final libmodbus response timeout
final watchdog timing
final lifecycle poll delay/count
```

These must be decided together using measured system behavior.

---

## 23. MVP non-goals

Do not add yet:

```text
SerialTransport abstraction
generic ITransport hierarchy
background communication thread
automatic reconnect state machine
complex retries
automatic alarm reset
support for arbitrary motor counts
CAN backend
TCP/RTU backend switching
```

If a real second backend appears, extract the transport abstraction then.

---

## 24. Frozen M1Driver baseline

```text
M1Hardware
    |
    v
M1Driver
    |
    +-- M1 / Multi-drive 2.0 semantics
    +-- MotorCommand / MotorState
    +-- runtime lifecycle protocol
    +-- Standard Modbus maintenance access
    +-- private libmodbus RTU context
    +-- private transact() boundary
    |
    v
libmodbus
    |
    v
RS485 / M1 ID1 + ID2
```

Baseline rule:

> `M1Driver` owns M1 semantics and privately owns libmodbus communication.
> `libmodbus` is an implementation detail, not an application-layer
> abstraction.

**M1Driver MVP design: FROZEN.**

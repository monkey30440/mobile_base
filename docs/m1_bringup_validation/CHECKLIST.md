# M1 / Multi-drive 2.0 validation checklist

Rule: preserve raw logs and distinguish **development configuration** from **deployment configuration**.

## A. Physical / safety evidence

- [ ] Wheels lifted for initial motion tests.
- [ ] E-stop/STO immediately available.
- [ ] Motor/driver electrical compatibility confirmed.
- [ ] RS485 wiring/termination/reference ground inspected.
- [ ] Wheel rolling radius measured under representative load.
- [ ] Wheel separation measured at effective rolling centerlines.

## B. Transport / Modbus

- [ ] `00_preflight.sh`
- [ ] `01_scan_bus.py`
- [ ] baud proven
- [ ] unique IDs proven
- [ ] repeated Multi-drive 2.0 reads without timeout / CRC / frame failure

## C. Hardware-specific parameters

These follow the actual motor/electrical system, not ROS preferences.

- [ ] 01-01 motor/sensor type verified against actual motor
- [ ] 01-03 motor poles verified
- [ ] 01-06 encoder resolution verified
- [ ] 01-16 encoder/Hall offset verified if applicable
- [ ] 02-18 rated output verified
- [ ] protection / torque limits / PID reviewed as motor-system parameters

## D. Architecture-level parameters

- [ ] 01-10 = 1
- [ ] 01-11 = 0
- [ ] 01-12 = 4
- [ ] 02-14 = 1
- [ ] 02-15 = 3
- [ ] 09-18 = 0
- [ ] IDs match deployment mapping
- [ ] baud selector matches host
- [ ] 09-21 = 0 baseline
- [ ] 09-26 = 0

Development audit:

```bash
python3 scripts/09_audit_recommended_config.py \
  --port /dev/ttyUSB0 \
  --baud 230400 \
  --ids 1,2 \
  --profile development
```

Deployment audit:

```bash
python3 scripts/09_audit_recommended_config.py \
  --port /dev/ttyUSB0 \
  --baud 230400 \
  --ids 1,2 \
  --profile deployment
```

## E. SERVO lifecycle

- [ ] SERVO-EN mapping read and recorded
- [ ] ID1 enable -> STOP/0 RPM -> disable
- [ ] ID2 enable -> STOP/0 RPM -> disable
- [ ] original NET-IN values restored after tests

## F. FC17 motor control

- [ ] only right motor moves when right is commanded
- [ ] only left motor moves when left is commanded
- [ ] alarm remains 0
- [ ] commanded RPM and actual RPM are consistent
- [ ] stop is confirmed
- [ ] physical forward direction recorded for both sides
- [ ] command sign recorded
- [ ] feedback sign recorded

## G. Gear ratio

- [ ] right: ~20 motor rev corresponds to ~1 wheel rev
- [ ] left: ~20 motor rev corresponds to ~1 wheel rev
- [ ] visual observations written to a result file

## H. Position format 1

- [ ] `07_set_position_format1.py` PASS
- [ ] config snapshot shows 02-14=1 on both drivers
- [ ] right `08_verify_position_format1.py` PASS in + and - native directions
- [ ] left `08_verify_position_format1.py` PASS in + and - native directions
- [ ] `06_conversion_test.py` PASS using signed 32-bit model
- [ ] production design includes int32 rollover unwrapping

## I. Communication timing evidence

- [ ] FC17 timing measured at 50 Hz
- [ ] 50 Hz rejected if transaction time exceeds the 20 ms cycle budget
- [ ] FC17 timing measured at 30 Hz
- [ ] p95 / p99 / max reviewed
- [ ] candidate ros2_control update rate chosen from evidence
- [ ] host serial transaction timeout chosen from evidence

## J. Development communication-safety profile

During bring-up/driver development, communication protection is intentionally disabled:

```text
05-17 = 0
05-18 = 0
05-21 = 0
```

- [ ] development profile intentionally selected
- [ ] `--profile development` audit passes
- [ ] team understands this is **not deployment-safe**
- [ ] deployment safety remains an explicit open item

## K. Deployment communication-safety profile

Before deployment, the development exception must be removed.

Required policy shape:

```text
05-17 > 0
05-18 = 1..10
05-21 = 1 or 2
```

Exact values must come from timing and fault-injection evidence.

Current fault-injection evidence to preserve:

- `05-17=100`, `05-18=3`, `05-21=2` successfully triggered communication timeout protection.
- Communication timeout produced Alarm 21.
- Remote NET-IN / SERVO-EN was cleared.
- In the observed test, Alarm 21 did not clear with the attempted NET-X ALM-RST pulse or `0A00h` Alarm Reset.
- Power cycling cleared Alarm 21.
- Therefore `05-21=2` must **not** be accepted as final deployment policy solely because its register values look correct.
- `05-21=1` remains a candidate that requires a separate real fault/recovery test.

Deployment gates:

- [ ] final 05-17 chosen
- [ ] final 05-18 chosen
- [ ] final 05-21 chosen
- [ ] communication-loss stop behavior proven
- [ ] recovery behavior proven
- [ ] no power-cycle-only recovery unless explicitly accepted as a system requirement
- [ ] `--profile deployment` audit passes
- [ ] communication-error history captured around fault tests

## L. ros2_control contract ready

- [ ] RIGHT driver ID known
- [ ] LEFT driver ID known
- [ ] command signs known
- [ ] feedback signs known
- [ ] gear ratio known
- [ ] encoder counts/rev known
- [ ] position representation fixed
- [ ] FC17 read/write mapping fixed
- [ ] lifecycle enable/disable behavior fixed
- [ ] development vs deployment watchdog policy explicit
- [ ] maximum safe command RPM / wheel velocity policy fixed

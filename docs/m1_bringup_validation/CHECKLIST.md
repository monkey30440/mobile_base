# M1 / Multi-drive 2.0 validation checklist v2

Rule: do not proceed past a failed gate. Preserve every raw log.

## A. Physical/safety evidence
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
- [ ] 20 consecutive Multi-drive 2.0 read transactions without timeout/CRC/frame failure

## C. Hardware-specific parameters
- [ ] 01-01 motor/sensor type verified against actual motor
- [ ] 01-03 motor poles verified
- [ ] 01-06 encoder resolution verified
- [ ] 01-16 encoder/Hall offset verified if applicable
- [ ] 02-18 rated output verified
- [ ] electrical protection / torque limits / PID treated as motor-system parameters

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

Run:
```bash
python3 scripts/09_audit_recommended_config.py --port /dev/ttyUSB0 --baud 230400 --ids 1,2
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
- [ ] new config snapshot shows 02-14=1 on both drivers
- [ ] right `08_verify_position_format1.py` PASS in + and - native directions
- [ ] left `08_verify_position_format1.py` PASS in + and - native directions
- [ ] `06_conversion_test.py` PASS using signed 32-bit model
- [ ] production design includes int32 rollover unwrapping

## I. Timing / communication safety
- [ ] `10_fc17_timing.py` recorded at proposed control rate
- [ ] p95/p99/max FC17 latency reviewed
- [ ] ros2_control update rate chosen from evidence
- [ ] host serial transaction timeout chosen from evidence
- [ ] 05-17 set to non-zero with margin
- [ ] 05-18 intentionally selected
- [ ] 05-21 intentionally selected
- [ ] communication-loss behavior tested after watchdog is configured
- [ ] communication-error history saved before/after fault tests

## J. ros2_control contract ready
- [ ] RIGHT driver ID known
- [ ] LEFT driver ID known
- [ ] command signs known
- [ ] feedback signs known
- [ ] gear ratio known
- [ ] encoder counts/rev known
- [ ] position representation fixed
- [ ] FC17 read/write mapping fixed
- [ ] lifecycle enable/disable behavior fixed
- [ ] watchdog policy fixed
- [ ] maximum safe command RPM/velocity policy fixed

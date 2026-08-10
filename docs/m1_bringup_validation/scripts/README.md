# Additional M1 bring-up scripts

Copy these files into:

```text
docs/m1_bringup_validation/scripts/
```

They depend on the existing `m1_modbus.py` from the original validation bundle.

## 02b — read control / SERVO mapping

Read-only:

```bash
python3 scripts/02b_read_control_mapping.py \
  --port /dev/ttyUSB0 \
  --baud 230400 \
  --ids 1,2 \
  | tee logs/manual/control_mapping.txt
```

## 03b — SERVO Enable/Disable only

No JG / RPM command is sent.

Driver 1:

```bash
python3 scripts/03b_servo_enable_test.py \
  --port /dev/ttyUSB0 \
  --baud 230400 \
  --id 1 \
  --arm I_UNDERSTAND \
  | tee logs/manual/servo_id1.txt
```

Driver 2:

```bash
python3 scripts/03b_servo_enable_test.py \
  --port /dev/ttyUSB0 \
  --baud 230400 \
  --id 2 \
  --arm I_UNDERSTAND \
  | tee logs/manual/servo_id2.txt
```

## 04 — safe motor test

`--ids` means `RIGHT_ID,LEFT_ID`.

First test one wheel at a time with wheels lifted and E-stop/STO ready:

```bash
python3 scripts/04_motor_test_safe.py \
  --port /dev/ttyUSB0 \
  --baud 230400 \
  --ids 1,2 \
  --right-rpm 80 \
  --left-rpm 0 \
  --seconds 1 \
  --arm I_UNDERSTAND \
  | tee logs/manual/right_80rpm_safe.txt
```

Then, only after reviewing the right-wheel result:

```bash
python3 scripts/04_motor_test_safe.py \
  --port /dev/ttyUSB0 \
  --baud 230400 \
  --ids 1,2 \
  --right-rpm 0 \
  --left-rpm 80 \
  --seconds 1 \
  --arm I_UNDERSTAND \
  | tee logs/manual/left_80rpm_safe.txt
```

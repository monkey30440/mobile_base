# M1 Bring-up Validation v2

目的：從硬體與 M1 官方通訊定義開始建立可重現證據，不把「目前實機設定」自動當成正確設計。

## 目前建議驗證順序

```bash
cd docs/m1_bringup_validation

# read-only
bash scripts/00_preflight.sh
python3 scripts/01_scan_bus.py --port /dev/ttyUSB0
python3 scripts/02_read_config.py --port /dev/ttyUSB0 --baud 230400 --ids 1,2
python3 scripts/02b_read_control_mapping.py --port /dev/ttyUSB0 --baud 230400 --ids 1,2
python3 scripts/03_md2_read.py --port /dev/ttyUSB0 --baud 230400 --ids 1,2 --samples 20 --hz 10

# lifecycle only
python3 scripts/03b_servo_enable_test.py --port /dev/ttyUSB0 --baud 230400 --id 1 --arm I_UNDERSTAND
python3 scripts/03b_servo_enable_test.py --port /dev/ttyUSB0 --baud 230400 --id 2 --arm I_UNDERSTAND

# low-speed motion
python3 scripts/04_motor_test_safe.py --port /dev/ttyUSB0 --baud 230400 --ids 1,2 --right-rpm 80 --left-rpm 0 --seconds 1 --arm I_UNDERSTAND
python3 scripts/04_motor_test_safe.py --port /dev/ttyUSB0 --baud 230400 --ids 1,2 --right-rpm 0 --left-rpm 80 --seconds 1 --arm I_UNDERSTAND

# mechanical ratio
python3 scripts/05_gear_ratio_test.py ...

# target position representation
python3 scripts/07_set_position_format1.py --port /dev/ttyUSB0 --baud 230400 --ids 1,2 --arm I_UNDERSTAND
python3 scripts/08_verify_position_format1.py --port /dev/ttyUSB0 --baud 230400 --ids 1,2 --wheel right --rpm 80 --arm I_UNDERSTAND
python3 scripts/08_verify_position_format1.py --port /dev/ttyUSB0 --baud 230400 --ids 1,2 --wheel left --rpm 80 --arm I_UNDERSTAND
python3 scripts/06_conversion_test.py

# architecture config audit
python3 scripts/09_audit_recommended_config.py --port /dev/ttyUSB0 --baud 230400 --ids 1,2

# timing evidence needed before choosing communication watchdog
python3 scripts/10_fc17_timing.py --port /dev/ttyUSB0 --baud 230400 --ids 1,2 --samples 300 --hz 50 --arm I_UNDERSTAND

# read-only error-history snapshot
python3 scripts/11_read_comm_error_history.py --port /dev/ttyUSB0 --baud 230400 --ids 1,2
```

For phase-level timing of the production C++/libmodbus path, use the existing
zero-speed harness with detailed capture enabled:

```bash
ros2 run mobile_base_control m1_fc17_latency_check \
  --device /dev/ttyUSB0 --baud 230400 --samples 300 \
  --execute --raw-output /tmp/fc17_detailed.csv
```

`--raw-output` buffers timestamps in memory during the measured FC17 loop and
writes the CSV only after the stop/disable/post-check sequence. The test remains
hard-bound to JG 0 RPM and retains the physical E-stop/STO requirements.

## Target architecture-level M1 configuration

These are design choices, not values to accept merely because the hardware currently has them:

- `01-10 = 1`: lifecycle-controlled SERVO-ON.
- `01-11 = 0`: Speed closed-loop.
- `01-12 = 4`: Multi-drive Lite JG speed source.
- `02-14 = 1`: signed 32-bit Step position representation.
- `02-15 = 3`: 100 Hz RPM/monitor refresh.
- `09-18 = 0`: Modbus RTU.
- unique driver IDs matching deployment mapping.
- `09-20`: baud matching host configuration.
- `09-21 = 0`: standard RTU timing baseline.
- `09-26 = 0`: fixed Multi-drive 2.0 mapping expected by these scripts.
- `05-17 > 0`: communication watchdog enabled; exact value comes after timing measurement.
- `05-18`: intentionally selected error-count policy, not left at zero by accident.
- `05-21 = 2` is the current safety recommendation: alarm stop + clear remote virtual I/O.

Motor/sensor, motor poles, encoder resolution, encoder/Hall offset, rated power and protection/PID parameters
must be selected from the actual motor/electrical system, not from this software architecture.

See `RESULTS_REVIEW.md` and `CHECKLIST.md`.

# M1 Hardware Diagnostic & Maintenance Toolkit

This directory provides standalone diagnostic and maintenance utilities for the M1 dual-motor differential drive system over RS-485 Modbus RTU.

> [!IMPORTANT]
> **Authority & Canonical Baselines:**
> * These scripts are diagnostic and maintenance utilities. They are **not** the normative system requirement or formal verification authority.
> * For canonical architecture, protocol details, and motor parameters, refer to [`docs/04_SYSTEMS.md`](file:///home/jim/mobile_base/docs/04_SYSTEMS.md).
> * Active runtime configuration is maintained in [`src/mobile_base_control/config/base_control_params.yaml`](file:///home/jim/mobile_base/src/mobile_base_control/config/base_control_params.yaml).

---

## Retained Diagnostic Scripts

### 1. Read-Only Utilities

These scripts perform passive inspection or standard Modbus read transactions (FC03). They do not alter motor state, write configuration registers, or command motion.

| Script | Purpose | Example Usage |
|---|---|---|
| [`00_preflight.sh`](file:///home/jim/mobile_base/docs/m1_bringup_validation/scripts/00_preflight.sh) | OS serial port, permission (`dialout`), and USB kernel diagnostics | `bash scripts/00_preflight.sh` |
| [`01_scan_bus.py`](file:///home/jim/mobile_base/docs/m1_bringup_validation/scripts/01_scan_bus.py) | Scan Modbus RTU baud rates and slave IDs on the bus | `python3 scripts/01_scan_bus.py --port /dev/ttyUSB0 --ids 1-8` |
| [`02_read_config.py`](file:///home/jim/mobile_base/docs/m1_bringup_validation/scripts/02_read_config.py) | Read and display key M1 configuration registers | `python3 scripts/02_read_config.py --port /dev/ttyUSB0 --baud 230400 --ids 1,2` |
| [`02b_read_control_mapping.py`](file:///home/jim/mobile_base/docs/m1_bringup_validation/scripts/02b_read_control_mapping.py) | Verify speed control method (01-12) and `SERVO-EN` virtual I/O mapping | `python3 scripts/02b_read_control_mapping.py --port /dev/ttyUSB0 --baud 230400 --ids 1,2` |
| [`03_md2_read.py`](file:///home/jim/mobile_base/docs/m1_bringup_validation/scripts/03_md2_read.py) | Stream real-time Multi-drive 2.0 FC03 feedback (status, alarm, RPM, bus voltage, current, position steps) | `python3 scripts/03_md2_read.py --port /dev/ttyUSB0 --baud 230400 --ids 1,2 --samples 20 --hz 10` |
| [`09_audit_recommended_config.py`](file:///home/jim/mobile_base/docs/m1_bringup_validation/scripts/09_audit_recommended_config.py) | Audit driver register settings against development or deployment baselines | `python3 scripts/09_audit_recommended_config.py --port /dev/ttyUSB0 --baud 230400 --ids 1,2 --profile development` |
| [`11_read_comm_error_history.py`](file:///home/jim/mobile_base/docs/m1_bringup_validation/scripts/11_read_comm_error_history.py) | Dump driver communication error history registers (`0x4800..0x4809`) | `python3 scripts/11_read_comm_error_history.py --port /dev/ttyUSB0 --baud 230400 --ids 1,2` |
| [`14_multidrive2_fc03_state_test.py`](file:///home/jim/mobile_base/docs/m1_bringup_validation/scripts/14_multidrive2_fc03_state_test.py) | Compare Standard Modbus individual reads with Multi-drive 2.0 FC03 group state read | `python3 scripts/14_multidrive2_fc03_state_test.py --port /dev/ttyUSB0 --baud 230400 --ids 1,2` |

---

### 2. State-Changing Utilities (Zero-Motion)

> [!WARNING]
> **Safety Warning:**
> State-changing scripts interact directly with drive lifecycle controls. Although they do **not** command non-zero RPM, wheels must be lifted or E-stop/STO made accessible before execution.

| Script | Purpose | Operational Risk | Example Usage |
|---|---|---|---|
| [`15_multidrive2_lifecycle_test.py`](file:///home/jim/mobile_base/docs/m1_bringup_validation/scripts/15_multidrive2_lifecycle_test.py) | Test Multi-drive 2.0 FC17 SVON -> JG 0 -> SVOFF lifecycle transitions with simultaneous state read | **ZERO-MOTION WRITE** (Armed with `--arm I_UNDERSTAND`, explicitly commands 0 RPM) | `python3 scripts/15_multidrive2_lifecycle_test.py --port /dev/ttyUSB0 --baud 230400 --ids 1,2 --arm I_UNDERSTAND` |

---

### 3. Shared Library

* [`m1_modbus.py`](file:///home/jim/mobile_base/docs/m1_bringup_validation/scripts/m1_modbus.py): Provides shared Modbus RTU CRC16 calculation, request framing, response checking, and helper read functions for Python diagnostic tools.

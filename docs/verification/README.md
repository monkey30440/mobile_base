> [!WARNING]
> **SUPERSEDED**
>
> This verification entrypoint is no longer authoritative. Use [`evidence_index.md`](evidence_index.md) for the canonical verification evidence catalog and [`traceability_matrix.md`](traceability_matrix.md) for requirement-to-verification traceability.

# Verification Evidence Storage

本目錄保存 `mobile_base` v0.1 checklist #7–#27 每個 implementation item 的原始 verification evidence。

Storage convention 定義於 [`docs/07_implementation.md §4`](../07_implementation.md)（Verification Evidence Storage Convention）。本 README 是快速參照索引；以 §4 為 normative source。

---

## Directory Structure

```text
docs/verification/
  README.md          ← 本文件（快速索引）
  IMP-007/           ← S7 M1Driver transport vertical slice
  IMP-008/           ← S7 M1Hardware ros2_control integration
  IMP-009/           ← S1 Robot Description
  IMP-010/           ← S2 LiDAR acquisition and scan baseline
  IMP-011/           ← S2 TDK IMU runtime integration
  IMP-012/           ← historical superseded RF2O and selected-scan evidence
  IMP-013/           ← S3 State Estimation
  IMP-014/           ← S4 Mapping and MapIO
  IMP-015/           ← S5 Localization
  IMP-016/           ← S6 Target Admission thin gaps
  IMP-017/           ← S6 Route-assisted Navigation execution
  IMP-018/           ← TF and frame authority closure
  IMP-019/           ← Perception data-flow closure
  IMP-020/           ← Motion-command and physical-stop closure
  IMP-021/           ← Feedback and odometry closure
  IMP-022/           ← Operational-mode and lifecycle closure
  IMP-023/           ← UC-001 Mapping end-to-end acceptance
  IMP-024/           ← UC-002 Navigation end-to-end acceptance
  IMP-025/           ← Requirement and custom-gap traceability audit
  IMP-026/           ← Reproducibility and clean-environment audit
  IMP-027/           ← v0.1 Feature Freeze review
```

Each item directory contains `.gitkeep` until the first real evidence file is added.

---

## Evidence File Naming

```text
<YYYY-MM-DD>T<HHmmss>_<layer>_<desc>.txt
```

- `YYYY-MM-DD`: execution date
- `T<HHmmss>`: execution time (24 h, no colons), e.g. `T103817` = 10:38:17
- `layer`: `build` / `unit` / `intg` / `hw` / `neg`
- `desc`: lowercase underscore-separated description

Example — same-day FAIL → PASS run:

```text
2026-08-20T094501_unit_m1driver_read.txt    ← FAIL (first run)
2026-08-20T101738_unit_m1driver_read.txt    ← PASS (after fix); FAIL file kept
```

Timestamp uniqueness guarantees no two runs on the same day overwrite each other.
Execution order is recoverable from the filename without any external database.

---

## Evidence Metadata Header (required in every .txt file)

```text
# IMP: IMP-NNN
# Layer: build | unit | integration | hardware | negative
# Timestamp: YYYY-MM-DDThh:mm:ss±HH:MM
# Env: <image digest or tag, or 'host'> / <ROS distro> / <OS>
# Target: <package(s) or hardware identity>
# Command: <exact command or procedure reference>
# Version: <git rev-parse --short HEAD>
# Result: PASS | FAIL
# Proved: <one sentence: what this evidence actually proves>
# Not-proved: <one sentence: what this evidence cannot prove>
```

All fields are **required**. `Result` must be `PASS` or `FAIL` only.
`Timestamp` uses ISO 8601 with timezone offset, e.g. `2026-08-20T10:38:17+08:00`.

---

## Re-run Policy

- Old evidence files are **never deleted or overwritten**.
- Each run (including same-day reruns) produces a new file with a unique timestamp.
- A FAIL followed by a PASS on the same day produces **two distinct files**; the FAIL is retained.
- `07_implementation.md` item record Storage path points to the **most recent** authoritative (PASS) file.
- Authoritative = latest timestamp with `Result: PASS` for the same item + layer.
- FAIL files are retained permanently for traceability.

---

## External Artifacts

If a raw artifact is too large for Git (>~1 MB, binary, ROS bag), keep a `.ref.txt` file here with:

```text
# ExternalRef: <storage location>
# SizeBytes: <approximate>
# Checksum: <sha256 if available>
# Retained-by: <person/machine>
```

Name the `.ref.txt` with the same timestamp-based convention:
`<YYYY-MM-DD>T<HHmmss>_<layer>_<desc>.ref.txt`

The `.ref.txt` enters Git; the external artifact does not.

---

## Pre-IMP Evidence

Hardware evidence collected before the IMP convention was established is preserved at:

```text
docs/m1_bringup_validation/logs/manual/
```

New evidence from IMP-007 onward goes into the corresponding `IMP-NNN/` directory here.

---

## Canonical Build & Test Commands

Build and test commands to generate evidence artifacts are defined in [`docs/07_implementation.md §5`](../07_implementation.md) (Build and Test Command Baseline).
- Full build: `docker compose exec mobile_base bash -c "source /opt/ros/jazzy/setup.bash && colcon build --symlink-install"`
- Selective build: `docker compose exec mobile_base bash -c "source /opt/ros/jazzy/setup.bash && colcon build --symlink-install --packages-select <pkg>"`
- Package test: `docker compose exec mobile_base bash -c "source /opt/ros/jazzy/setup.bash && colcon test --packages-select <pkg> --event-handlers console_direct+ && colcon test-result --all --verbose"`

---

> See [`07_implementation.md §4`](../07_implementation.md) for evidence storage rules, [`07_implementation.md §5`](../07_implementation.md) for canonical build/test commands, and [`07_implementation.md §6`](../07_implementation.md) for hardware safety preflight gates.

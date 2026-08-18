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
  IMP-012/           ← S2 RF2O and selected scan integration
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
<YYYY-MM-DD>_<layer>_<desc>.txt
```

Layer abbreviations: `build` / `unit` / `intg` / `hw` / `neg`

Example: `2026-08-20_build_colcon_all.txt`

---

## Evidence Metadata Header (required in every .txt file)

```text
# IMP: IMP-NNN
# Layer: build | unit | integration | hardware | negative
# Date: YYYY-MM-DD
# Env: <image digest or tag, or 'host'> / <ROS distro> / <OS>
# Target: <package(s) or hardware identity>
# Command: <exact command or procedure reference>
# Version: <git rev-parse --short HEAD>
# Result: PASS | FAIL
# Proved: <one sentence: what this evidence actually proves>
# Not-proved: <one sentence: what this evidence cannot prove>
```

All fields are **required**. `Result` must be `PASS` or `FAIL` only.

---

## Re-run Policy

- Old evidence files are **never deleted or overwritten**.
- Each re-run produces a new file with the new date.
- `07_implementation.md` item record Storage path points to the **most recent** authoritative (PASS) file.
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

The `.ref.txt` enters Git; the external artifact does not.

---

## Pre-IMP Evidence

Hardware evidence collected before the IMP convention was established is preserved at:

```text
docs/m1_bringup_validation/logs/manual/
```

New evidence from IMP-007 onward goes into the corresponding `IMP-NNN/` directory here.

---

> See [`07_implementation.md §4`](../07_implementation.md) for the full normative specification.

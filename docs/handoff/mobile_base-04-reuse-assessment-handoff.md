# mobile_base 04 Reuse Assessment Handoff

## Workspace

- Repository: `/home/zzz/mobile_base`
- Current HEAD: `7724f27 Add research documentation for SYS-022, SYS-023, and SYS-026 assessments`
- `git status --short` was clean when this handoff was created.
- Follow the repository `AGENTS.md`, especially GitNexus impact analysis before edits and `gitnexus_detect_changes()` before any commit.

## Collaboration Contract

- Discuss exactly one concrete issue at a time.
- Research and propose the coverage conclusion first.
- Wait for explicit user approval before writing that requirement record into 04.
- After approval, edit only that scope, run `git diff --check`, check references, and run GitNexus change detection.
- `01_use_cases.md`–`03_requirements.md` are normative product inputs. If 04 discovers an upstream issue, stop and obtain approval before changing 01–03.
- Do not review or modify 05–07 until 04 is complete; afterwards review 05, then 06, then 07 in order.
- Prefer focused local inspection plus 1–3 exact-version primary sources to reduce token use.

## Authoritative Artifacts

- Workflow and status: `/home/zzz/mobile_base/docs/04_reuse_assessment_checklist.md`
- Current assessment records: `/home/zzz/mobile_base/docs/04_reuse_assessment.md`
- Normative requirements: `/home/zzz/mobile_base/docs/03_requirements.md`
- Research evidence: `/home/zzz/mobile_base/docs/research/`
- M1 approved design baselines:
  - `/home/zzz/mobile_base/docs/design_baseline/m1_driver.md`
  - `/home/zzz/mobile_base/docs/design_baseline/m1_hardware.md`

Do not duplicate those documents in new artifacts. Read the relevant record and research note before continuing.

## Current Progress

- Checklist progress: `11 / 40`
- Completed common rules: items 1–5.
- Completed requirements:
  - 6: SYS-023 Robot Description
  - 7: SYS-003 LiDAR Perception
  - 8: SYS-004 IMU Perception
  - 9: SYS-005 System Odometry
  - 10: SYS-022 Base Motion Control
  - 11: SYS-026 Base Fault Handling
- Next and only active issue: item 12, `SYS-027 Motion-command Timeout`.

## Important Approved Decisions

- Preserve both raw LiDAR `LaserScan` sources. RF2O alone uses a derived merged scan.
- The selected merge package is ROS 2 Jazzy `dual_laser_merger` 0.3.1. TF, synchronization, QoS, resampling, overlap/occlusion, latency, dropout semantics, and real-hardware evidence remain downstream configuration/verification work.
- System odometry composition is wheel odometry + merged-scan RF2O odometry + TDK IMU through `robot_localization` EKF.
- EKF is the sole `odom -> base_footprint` publisher.
- SYS-005 intentionally permits native `robot_localization` behavior when inputs fail or time out: use remaining valid measurements or prediction and continue output. No all-input validity gate and no prohibition on degraded odometry remain.
- SYS-022 uses ROS 2 Jazzy `ros2_control + diff_drive_controller`, with `TwistStamped` as the canonical velocity command. It is `Fully Covered` at mature controller-capability level.
- SYS-026 was deliberately simplified. Current normative text requires only: when the hardware interface returns `ERROR`, stop controllers using that hardware and expose an observable error state.
- Therefore SYS-026 is `Fully Covered` by native ros2_control hardware-error handling. It no longer requires M1 alarm interpretation, fault latch, JG0, zero-RPM confirmation, detailed fault reporting, physical-stop proof, or recovery behavior.
- Do not silently restore stricter SYS-026 behavior from older research text or M1 implementation plans.

## Next Task: SYS-027

Read the exact SYS-027 text in `docs/03_requirements.md`, then perform a narrow mature-solution assessment of ROS 2 Jazzy `diff_drive_controller` command timeout behavior.

Questions to answer before proposing a conclusion:

1. Does the exact Jazzy controller accept `TwistStamped` and enforce a command-age timeout natively?
2. What command does it write after timeout, and is that sufficient for the approved wording "使底盤停止"?
3. Does controller-level zero wheel command prove physical stopping, or does the current requirement require integration/real-hardware evidence only?
4. Which timeout parameter, timestamp semantics, lifecycle state, and command chain constraints apply?
5. Is coverage `Fully Covered` with configuration/evidence gaps, or is any custom behavior genuinely required?

Use the research convention and create one note under `docs/research/` only. Do not edit 04/checklist until the user approves the conclusion.

## Suggested Skills

- `architecture-convergence`: preserve the 01–04 authority chain, mature-solution-first assessment, and minimum-gap discipline.
- `research`: delegate exact Jazzy primary-source research and save one cited Markdown note in `docs/research/`.
- `brainstorming`: use only when a requirement or behavior change is proposed; present the exact change and consequences before editing.

## GitNexus Note

- For tracked requirement sections, run `gitnexus_impact` using the section name and `docs/03_requirements.md` as the file hint before changing it.
- New/untracked 04 sections may return `UNKNOWN` until indexed; report that accurately rather than converting it to LOW.
- Before committing, run `gitnexus_detect_changes({scope: "unstaged" or "all"})` and report affected symbols/processes.

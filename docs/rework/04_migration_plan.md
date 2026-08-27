# Documentation Migration Plan

## 1. Purpose

This document defines the execution roadmap for migrating the `mobile_base` documentation from its current audited state to the approved [Target Documentation Structure](file:///home/zzz/mobile_base/docs/rework/03_target_structure.md).

To ensure zero disruption to production code, automated test baselines, and historical traceability:
* Documentation convergence is executed in **small, discrete, and reviewable batches**.
* Every batch has an isolated authority scope, strict entry/exit conditions, verifiable deliverables, and independent rollback capabilities.
* **Evidence-first discipline:** As-verified and as-built facts are indexed and stabilized before high-level entrypoints and narratives are rewritten.
* **Zero production code mutation:** Production source code, launch files, parameter YAMLs, and test suites are not modified during documentation convergence.

---

## 2. Migration Guardrails

The following guardrails strictly govern all migration execution batches:

1. **No Source or Configuration Modification:** Production source code (`src/*`), launch files, YAML configurations, URDF models, Behavior Trees, and test implementations are frozen. If a discrepancy indicates a potential A-class blocker, stop execution immediately and report.
2. **No Navigation or Controller Debugging:** Navigation tuning, MPPI parameters, and Station yaw adjustments remain closed during documentation convergence.
3. **No Unindexed Evidence Deletion:** No evidence file may be deleted or modified. Raw logs (`docs/verification/IMP-007~015`) and phase reports (`docs/evidence/`) remain in their exact existing file paths.
4. **Classification Precedes Physical Relocation:** Designating a document as `HISTORICAL` or `SUPERSEDED` is an informational classification. Physical file moves are decoupled and subject to explicit decision gates.
5. **No Combined Move and Content Rewrite:** File restructuring and deep content rewriting must not occur in the same batch.
6. **Cross-Link Integrity:** Relative markdown links and file references must be verified after every batch.
7. **Clean Working Tree Baseline:** `git status --short` must be clean before beginning any batch and immediately following each batch execution.
8. **One Batch = One Reviewable Intent:** Every batch produces a self-contained diff subject to explicit human review and approval before committing.
9. **No-Op is a Valid Review Outcome:** For review-oriented batches, if existing documentation already matches its authority source, a no-op outcome (zero file modifications) is completely valid. Documents must not be rewritten merely to produce a commit.

---

## 3. Pre-Migration Baseline

* **Target-Structure Commit Baseline:** `02ba162`
* **Execution Baseline:** Once this Migration Plan (`04_migration_plan.md`) is approved and committed, the execution baseline becomes that resulting Migration Plan commit hash.
* **Accepted Phase 1 Audit:** [`docs/rework/01_phase1_audit.md`](file:///home/zzz/mobile_base/docs/rework/01_phase1_audit.md)
* **Documentation Authority Model:** [`docs/rework/02_authority_model.md`](file:///home/zzz/mobile_base/docs/rework/02_authority_model.md)
* **Target Documentation Structure:** [`docs/rework/03_target_structure.md`](file:///home/zzz/mobile_base/docs/rework/03_target_structure.md)
* **Working Tree:** Pristine (zero untracked or uncommitted changes).

---

## 4. Migration Dependency Graph

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        Pre-Migration Baseline                          │
│               (Audit Baseline + Authority Model + Target)              │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
                 ┌──────────────────────────────────────┐
                 │  Batch 1: Verification Evidence Index │
                 │  (Pure creation of evidence_index.md)│
                 └──────────────────┬───────────────────┘
                                    │
                                    ▼
                 ┌──────────────────────────────────────┐
                 │ Batch 2: Requirement Traceability    │
                 │ (Map SYS -> Code -> Method -> Evid.) │
                 └──────────────────┬───────────────────┘
                                    │
                                    ▼
                 ┌──────────────────────────────────────┐
                 │ [Decision Gate 1: Arch. Packaging]   │
                 └──────────────────┬───────────────────┘
                                    │
                                    ▼
                 ┌──────────────────────────────────────┐
                 │  Batch 3: Architecture Consolidation │
                 │  (As-built S1~S7, TF, data flows)    │
                 └──────────────────┬───────────────────┘
                                    │
                                    ▼
                 ┌──────────────────────────────────────┐
                 │  Batch 4: Requirements Consistency   │
                 │  (Align 01/02/03 in place)           │
                 └──────────────────┬───────────────────┘
                                    │
                        ┌───────────┴───────────┐
                        │ [Normative Req Gate]  │ (Triggered ONLY if normative changes needed)
                        └───────────┬───────────┘
                                    │
                                    ▼
                 ┌──────────────────────────────────────┐
                 │  Batch 5: Component Design Baseline  │
                 │  (m1_driver.md, m1_hardware.md)      │
                 └──────────────────┬───────────────────┘
                                    │
                                    ▼
                 ┌──────────────────────────────────────┐
                 │  Batch 6: Operational Guidance Review│
                 │  (MAPPING.md, NAVIGATION.md)         │
                 └──────────────────┬───────────────────┘
                                    │
                                    ▼
                 ┌──────────────────────────────────────┐
                 │  Batch 7: System Entrypoint README   │
                 │  (Rewrite root docs/README.md)       │
                 └──────────────────┬───────────────────┘
                                    │
                 ┌──────────────────┴───────────────────┐
                 │ [Decision Gate 2: Historical Status] │
                 └──────────────────┬───────────────────┘
                                    │
                                    ▼
                 ┌──────────────────────────────────────┐
                 │  Batch 8: Historical Classification  │
                 │  (Banners on research, handoff, etc.)│
                 └──────────────────┬───────────────────┘
                                    │
                 ┌──────────────────┴───────────────────┐
                 │ [Decision Gate 3: Empty IMP Cleanup] │
                 └──────────────────┬───────────────────┘
                                    │
                                    ▼
                 ┌──────────────────────────────────────┐
                 │  Batch 9: Placeholder Cleanup        │
                 │  (Retire empty IMP-016~027 dirs)     │
                 └──────────────────┬───────────────────┘
                                    │
                 ┌──────────────────┴───────────────────┐
                 │ [Decision Gate 4: docs/rework Status]│
                 └──────────────────┬───────────────────┘
                                    │
                                    ▼
                 ┌──────────────────────────────────────┐
                 │  Batch 10: Final Repo Verification   │
                 │  (Static checks, link scan, clean git│
                 └──────────────────────────────────────┘
```

---

## 5. Proposed Execution Batches

### Batch 1 — Verification Evidence Index
* **Goal:** Create the authoritative catalog of all committed verification artifacts, classifying each individual file in place without moving, renaming, or deleting any files.
* **Allowed Files:**
  - Create: `docs/verification/evidence_index.md`
* **Forbidden Files:** `docs/verification/README.md` (deferred to Batch 8), all production source, launch, config, tests, `docs/evidence/*.txt`, `docs/verification/IMP-*/*.csv`, requirements, architecture.
* **Changes:**
  1. Inventory every evidence report in `docs/evidence/` (17 files) and raw log directory in `docs/verification/IMP-007` ~ `IMP-015`.
  2. Classify each artifact individually: *Current-supporting historical runtime*, *Historical*, *Superseded*, *Investigation-only*, or *Obsolete*.
  3. Record context metadata: originating commit, execution date, hardware setup, and scope.
  4. Explicitly state that test suite pass records (e.g. 515 tests) are historically recorded at commit `8ab06d9`.
* **Entry Conditions:** Pre-migration baseline committed; working tree clean.
* **Exit Conditions:** `evidence_index.md` exists and indexes 100% of committed evidence files; all paths match existing filesystem locations.
* **Verification:** Verify all indexed file paths exist on disk using automated link checking or read checks.
* **Rollback Boundary:** `git revert <batch-1-commit>`.
* **Risks:** Misclassifying an artifact or generating incorrect relative paths.
* **Stop Conditions:** Missing evidence file referenced in Git history; file path discrepancy.

---

### Batch 2 — Requirement Traceability Matrix
* **Goal:** Establish the single authoritative traceability matrix linking system requirements to production code, verification methods, and execution evidence without fabricating evidence.
* **Allowed Files:**
  - Create: `docs/verification/traceability_matrix.md`
* **Forbidden Files:** All production source, config, tests, `docs/03_requirements.md`, `docs/05_architecture.md`, `docs/evidence/*`.
* **Changes:**
  1. Create a structured matrix with an explicit row for every requirement from SYS-001 through SYS-034.
  2. Map each requirement to:
     - Responsible Subsystem (S1–S7)
     - Implementation Source Path(s)
     - Verification Method (Automated Test, Static / Config Inspection, Hardware Procedure, Runtime Observation, Integration Test)
     - Execution Evidence Reference (pointing into `docs/verification/evidence_index.md`)
     - Verification Status (`CURRENT VERIFIED`, `HISTORICALLY VERIFIED`, `IMPLEMENTED / NOT RE-VERIFIED`, `PARTIAL`, `GAP`, `UNKNOWN / INSUFFICIENT EVIDENCE`)
  3. Ensure non-automated requirements (e.g. static TF uniqueness, baud rate, physical wiring) are mapped to their actual verification method rather than artificial test claims.
* **Entry Conditions:** Batch 1 committed (`evidence_index.md` available).
* **Exit Conditions:** All 34 SYS IDs are explicitly represented; no silently blank cells; unsupported claims are explicitly categorized; any potential A-class gap triggers a stop condition.
* **Verification:** Cross-check requirement IDs against `docs/03_requirements.md` and evidence references against `docs/verification/evidence_index.md`.
* **Rollback Boundary:** `git revert <batch-2-commit>`.
* **Risks:** Inaccurate verification method assignment.
* **Stop Conditions:** Identification of an unresolvable A-class functional blocker.

---

### Batch 3 — Architecture Consolidation
* **Goal:** Establish the authoritative system architecture specification matching as-built reality, eliminating ghost interfaces and stale design assumptions.
* **Decision Gate (Gate 1):** User selects **Option A** (single `system_architecture.md` / `05_architecture.md`) or **Option B** (`system_architecture.md` + companion `subsystems.md`).
* **Allowed Files:**
  - Update / Rewrite: `docs/05_architecture.md` (or `docs/architecture/system_architecture.md` per Gate 1)
  - Update: `docs/06_subsystem.md` (mark as superseded by the consolidated architecture)
* **Forbidden Files:** All production source, launch files, parameter YAMLs, requirements (`01`~`03`), verification artifacts.
* **Changes:**
  1. Rebuild system architecture from production source, launch files, YAML configs, and URDF models.
  2. Document 7-subsystem allocation, coordinate frames (REP-103/105), dynamic TF authority (EKF sole `odom->base_footprint` owner; SLAM/AMCL `map->odom`), and dual-LiDAR data flows.
  3. Document command interception chain (`controller_server` -> `collision_monitor` -> `diff_drive_controller`).
  4. Document Station ID navigation flow (`navigate_to_station` CLI -> `TargetAdmission` -> native Nav2 `NavigateToPose`).
  5. Formally excise obsolete `mobile_base_msgs/action/NavigateToStation`, outdated goal tolerances (0.15m vs 0.25m), and stale catalog schemas.
  6. Add top-of-file superseded notice to `docs/06_subsystem.md`.
* **Entry Conditions:** Batch 2 committed; Decision Gate 1 resolved.
* **Exit Conditions:** Unified architecture accurately documents all 7 subsystems; zero ghost interfaces remain; `06_subsystem.md` is marked superseded.
* **Verification:** Compare topic names, TF owners, and node compositions directly against `src/*/launch/*` and `src/*/config/*`.
* **Rollback Boundary:** `git revert <batch-3-commit>`.
* **Risks:** Parameter duplication or accidental divergence from as-built configuration.
* **Stop Conditions:** Inconsistency discovered between production launch/config files and core architecture topology.

---

### Batch 4 — Requirements & Capabilities Consistency Review
* **Goal:** Review and update `docs/01_use_cases.md`, `docs/02_capabilities.md`, and `docs/03_requirements.md` in place to eliminate stale terminology while preserving normative requirements.
* **Allowed Files:**
  - Update: `docs/01_use_cases.md`
  - Update: `docs/02_capabilities.md`
  - Update: `docs/03_requirements.md`
* **Forbidden Files:** All production source, launch, config, `docs/05_architecture.md`, `docs/verification/*`.
* **Scope of Changes:**
  - *Safe Documentation Corrections (Allowed):* Remove stale component names (e.g. pre-Kinematic-ICP RF2O, merged scan, custom station action), correct broken file paths, and fix wording that conflicts with accepted design terminology without changing normative intent.
  - *Normative Requirement Changes (Forbidden without Gate):* If changes to acceptance criteria, safety bounds, numerical limits, or MVP commitments are needed, **STOP** and invoke the **Normative Requirement Change Gate**.
  - *No-Op Outcome:* If review confirms the existing files are already consistent, record review completion and proceed without file modifications.
* **Entry Conditions:** Batch 3 committed.
* **Exit Conditions:** All requirement texts are internally consistent with as-built reality and target traceability; zero unauthorized normative changes.
* **Verification:** Diff check ensuring no requirement numbers, acceptance tolerances, or safety bounds were weakened or altered.
* **Rollback Boundary:** `git revert <batch-4-commit>`.
* **Risks:** Unintentional modification of normative acceptance criteria.
* **Stop Conditions:** Unapproved normative requirement modification required.

---

### Batch 5 — Component Design Baseline Review
* **Goal:** Review `docs/design_baseline/m1_driver.md` and `m1_hardware.md` against production M1 source code.
* **Allowed Files:**
  - Update: `docs/design_baseline/m1_driver.md`
  - Update: `docs/design_baseline/m1_hardware.md`
* **Forbidden Files:** Production code (`src/mobile_base_control/**/*`), parameter YAMLs, requirements, architecture.
* **Changes:**
  1. Compare Modbus register mappings, baud rates, timeouts, and `SystemInterface` lifecycle descriptions against `m1_driver.cpp` and `m1_hardware.cpp`.
  2. If perfectly consistent, retain files as-is (no-op).
  3. If minor component-level factual discrepancies exist, correct them strictly within component boundaries without duplicating system architecture.
* **Entry Conditions:** Batch 4 committed / completed.
* **Exit Conditions:** Component design documents match production source code.
* **Verification:** Direct cross-check against `src/mobile_base_control/src/m1_driver.cpp` and `m1_hardware.cpp`.
* **Rollback Boundary:** `git revert <batch-5-commit>`.
* **Risks:** Copying system architecture details into component baseline docs.
* **Stop Conditions:** Hardware interface code discrepancy requiring source modification.

---

### Batch 6 — Operational Guidance Review
* **Goal:** Review and update package-local operational bringup guides against current launch arguments, scripts, and CLI syntax.
* **Allowed Files:**
  - Update: `src/mobile_base_bringup/MAPPING.md`
  - Update: `src/mobile_base_bringup/NAVIGATION.md`
* **Forbidden Files:** Production launch files, scripts, parameter YAMLs, source code.
* **Changes:**
  1. Verify `MAPPING.md` instructions match canonical launch CLI (`mobile_base.launch.py mode:=mapping site:=test_site`) and `save_map.sh`.
  2. Verify `NAVIGATION.md` instructions match canonical launch CLI (`mobile_base.launch.py mode:=navigation site:=test_site`) and `navigate_to_station` CLI options.
  3. Ensure guides point to parameter YAMLs rather than duplicating configuration blocks.
  4. If already fully accurate, confirm no-op.
* **Entry Conditions:** Batch 5 committed / completed.
* **Exit Conditions:** Operational guides reflect exact working CLI commands.
* **Verification:** Verify launch arguments and script flags against `src/mobile_base_bringup/launch/mobile_base.launch.py` and `scripts/*.sh`.
* **Rollback Boundary:** `git revert <batch-6-commit>`.
* **Risks:** Documenting non-existent launch arguments or obsolete flags.
* **Stop Conditions:** Operational documentation requires commands that fail syntax parsing.

---

### Batch 7 — Root System Entrypoint Rewrite (`docs/README.md`)
* **Goal:** Rewrite `docs/README.md` as the authoritative, up-to-date repository front door and navigation index.
* **Allowed Files:**
  - Update / Rewrite: `docs/README.md`
* **Forbidden Files:** All production source, config, requirements, architecture, verification artifacts.
* **Changes:**
  1. Synchronize project summary and milestone status (v0.1.0 MVP closed, CAP-001/002 verified).
  2. Provide high-level system overview without duplicating architecture diagrams.
  3. Present role-based entry paths (General/PM, Software Engineer, Verification Engineer, AI Agent).
  4. Link directly to canonical documents: Use Cases, Capabilities, Requirements, Architecture, Traceability Matrix, Evidence Index, and Operational Guides.
  5. Explicitly state the Known Limitation boundary (Station B -> A return timeout, root cause undetermined).
  6. Remove references to deleted files (`compose.hardware.yaml`, `07_backlog.md`).
* **Entry Conditions:** Batches 1 through 6 committed / completed (all canonical target destinations exist and are verified).
* **Exit Conditions:** `docs/README.md` is fully up-to-date, contains zero broken links, and serves as the clean repository index.
* **Verification:** Automated markdown link verification across all links in `docs/README.md`.
* **Rollback Boundary:** `git revert <batch-7-commit>`.
* **Risks:** Broken links to canonical targets.
* **Stop Conditions:** Target link destination missing or ambiguous.

---

### Batch 8 — Historical Material Classification
* **Goal:** Apply formal historical disclaimer banners to non-authoritative documents and superseded notices to superseded files.
* **Decision Gate (Gate 2):** In-place historical banners vs. physical relocation to `docs/archive/`.
* **Allowed Files:**
  - Update (Header banner): `docs/research/*.md` (32 files), `docs/handoff/*.md` (5 files), `docs/*checklist.md` (4 files), `docs/04_reuse_assessment.md`, `docs/07_implementation.md`, `docs/m1_bringup_validation/README.md`, `docs/design_baseline/write_*.md`, `docs/verification/README.md`.
* **Forbidden Files:** Active canonical documents, raw evidence (`IMP-007~015`), `docs/evidence/*`, source code. No files may be deleted in this batch.
* **Changes:**
  1. Add standard historical disclaimer banners to the top of all historical research, handoff, checklist, and construction narrative documents.
  2. Add superseded notice to `docs/verification/README.md` pointing to `docs/verification/evidence_index.md`.
* **Entry Conditions:** Batch 7 committed; Decision Gate 2 resolved.
* **Exit Conditions:** All historical materials are clearly marked non-authoritative; zero evidence files moved or deleted.
* **Verification:** Verify all modified files contain the approved disclaimer banner; verify `git status` shows only file modifications and zero deletions.
* **Rollback Boundary:** `git revert <batch-8-commit>`.
* **Risks:** Inadvertently modifying content below header banner.
* **Stop Conditions:** Unintended modification of active documentation content.

---

### Batch 9 — Verification Placeholder Cleanup
* **Goal:** Retire empty `.gitkeep` placeholder directories in `docs/verification/IMP-016` ~ `IMP-027`.
* **Decision Gate (Gate 3):** Explicit approval of Empty IMP Directory Retirement Gate.
* **Allowed Files:**
  - Delete: `docs/verification/IMP-016/.gitkeep` through `IMP-027/.gitkeep`
* **Forbidden Files:** `docs/verification/IMP-007` ~ `IMP-015` (raw data), `docs/evidence/*`, all other files.
* **Changes:**
  1. Remove empty `.gitkeep` files in `IMP-016` through `IMP-027` after confirming all historical evidence is fully cataloged in `evidence_index.md`.
* **Entry Conditions:** Batch 8 committed; Decision Gate 3 approved.
* **Exit Conditions:** 12 empty `.gitkeep` placeholder directories cleanly removed; zero data files deleted.
* **Verification:** Verify that `git status` lists only deleted `.gitkeep` files in `IMP-016~027`; confirm `IMP-007~015` remain 100% intact.
* **Rollback Boundary:** `git revert <batch-9-commit>`.
* **Risks:** Deleting an active directory.
* **Stop Conditions:** Any file other than `.gitkeep` found in target directories.

---

### Batch 10 — Final Repository Cross-Link & Static Verification
* **Goal:** Perform comprehensive static verification across the repository, ensuring complete link integrity, absence of stale terms, authority compliance, and clean Git status.
* **Decision Gate (Gate 4):** Final disposition of `docs/rework/` workspace (retain for audit vs. archive).
* **Allowed Files:**
  - Minor link fixups across documentation if identified during scan.
* **Forbidden Files:** Production source code, configs, tests, raw evidence.
* **Verification Actions:**
  1. **Link Verification:** Validate all relative Markdown links across all `.md` files.
  2. **Stale Terminology Scan:** Grep codebase and docs for prohibited active references:
     - `RF2O` as current
     - `dual_laser_merger` as current
     - `/navigate_to_station` as custom action
     - `compose.hardware.yaml`
     - CAP-001/002 marked "未開始"
  3. **Authority Model Audit:** Confirm no parameter duplication, no phantom action servers, and no unindexed verification claims.
  4. **Automated Test Scope:** Full software automated test execution is **optional and requires explicit approval** unless a migration batch unexpectedly modified source, config, launch, URDF, BT, or test code. If such files need modification, stop and re-scope before continuing.
  5. **Working Tree Verification:** Confirm `git status --short` is clean.
* **Entry Conditions:** Batches 1 through 9 committed.
* **Exit Conditions:** 100% of links valid; zero stale terms in active docs; working tree clean; documentation convergence Definition of Done satisfied.
* **Verification:** Full static grep scan and link validation output logged.
* **Rollback Boundary:** `git revert <batch-10-commit>`.
* **Risks:** Unresolved broken link.
* **Stop Conditions:** Detection of unresolved architectural discrepancy.

---

## 6. Recommended Batch Ordering

```text
Sequence    Batch / Gate   Name                                        Focus Deliverable
──────────────────────────────────────────────────────────────────────────────────────────────────
1           Batch 1        Verification Evidence Index                 docs/verification/evidence_index.md
2           Batch 2        Requirement Traceability Matrix             docs/verification/traceability_matrix.md
[Gate 1]    Gate 1         Architecture Packaging Selection            Option A vs Option B
3           Batch 3        Architecture Consolidation                  docs/05_architecture.md / 06_subsystem.md
4           Batch 4        Requirements Consistency Review             docs/01_, 02_, 03_requirements.md
[Gate Req]  Gate (Cond.)   Normative Requirement Change Gate           Triggered ONLY if criteria change
5           Batch 5        Component Design Baseline Review            docs/design_baseline/m1_*.md
6           Batch 6        Operational Guidance Review                 src/mobile_base_bringup/*.md
7           Batch 7        System Entrypoint README Rewrite            docs/README.md
[Gate 2]    Gate 2         Historical Material Treatment Gate          In-Place Banners vs Physical Move
8           Batch 8        Historical Material Classification          research/, handoff/, checklists, etc.
[Gate 3]    Gate 3         Empty IMP Directory Cleanup Gate            Retire vs Retain IMP-016~027
9           Batch 9        Verification Placeholder Cleanup            Delete empty IMP-016~027 .gitkeep
[Gate 4]    Gate 4         docs/rework Workspace Final Disposition     Retain vs Archive
10          Batch 10       Final Repository Cross-Link & Static Check  Full repo static verification
```

---

## 7. Commit Strategy

Each batch must be committed individually with clear, standardized semantic commit messages:

| Batch | Commit Message Convention |
|---|---|
| Batch 1 | `docs(verification): create evidence index and artifact catalog` |
| Batch 2 | `docs(verification): establish requirement traceability matrix` |
| Batch 3 | `docs(architecture): consolidate system architecture and subsystem design` |
| Batch 4 | `docs(requirements): synchronize use cases capabilities and requirements` (if modified) |
| Batch 5 | `docs(design): align component design baselines with motor driver source` (if modified) |
| Batch 6 | `docs(operations): align bringup operational guides with launch entrypoints` (if modified) |
| Batch 7 | `docs: rewrite root entrypoint readme and navigation index` |
| Batch 8 | `docs(archive): apply historical classification banners to non-authoritative materials` |
| Batch 9 | `docs(verification): retire empty verification placeholder directories` |
| Batch 10 | `docs: complete repository link verification and convergence baseline` |

*Note on No-Op Batches:* If Batch 4, 5, or 6 concludes with zero changes required, no empty commit will be generated; the review completion will be recorded in the batch summary.

---

## 8. Review Protocol

To prevent unreviewed modifications or drift:

```text
  [Codex Executes Batch]
           │
           ▼
  [Display Execution Summary & Scope Analysis]
           │
           ▼
  [Display git status --short & git diff --stat]
           │
           ▼
  [Display Full File Diffs]
           │
           ▼
  [Human / Peer Review Checkpoint]
     ├── If changes requested ──► Apply corrections & re-diff
     └── If approved ───────────► Stage ONLY batch files & commit
```

* **No Blind Commits:** Codex self-reports are not sufficient; explicit `git status` and `git diff` outputs are required for every batch.
* **Explicit Approval Required:** Commit only after the user or reviewer explicitly approves the batch diff.

---

## 9. Rollback Strategy

* **Isolated Batch Commits:** Because each batch modifies an isolated information domain, any batch can be independently reverted using standard Git commands without affecting other batches:
  ```bash
  git revert <batch-commit-hash> --no-edit
  ```
* **No Mega-Commits:** Multi-batch grouping or monolithic "final cleanup" commits are strictly forbidden.

---

## 10. Decision Gates

The following decision gates require explicit user alignment before proceeding with their respective batches:

### Decision Gate 1: Architecture Packaging Selection (Before Batch 3)
* **Option A:** Single unified `docs/05_architecture.md` (or `docs/architecture/system_architecture.md`) with structured subsystem sections.
* **Option B:** `system_architecture.md` + companion `subsystems.md`.
* *Recommendation:* **Option A** to minimize file fragmentation and prevent parameter drift.

### Conditional Decision Gate: Normative Requirement Changes (During Batch 4)
* Triggered ONLY if Batch 4 identifies a need to modify acceptance criteria, safety bounds, numerical limits, or MVP scope.
* Requires formal user approval before modifying any normative text.

### Decision Gate 2: Historical Material Physical Disposition (Before Batch 8)
* **Option 1 (In-Place):** Keep `docs/research/`, `docs/handoff/`, `04_reuse_assessment.md`, `07_implementation.md`, and checklists in their current directories, adding prominent top-of-file historical disclaimer banners.
* **Option 2 (Physical Move):** Move historical directories into `docs/archive/`.
* *Recommendation:* **Option 1 (In-Place with Banners)** to prevent link churn across historical commits and external references, with Option 2 evaluated as a future optional cleanup.

### Decision Gate 3: Empty IMP Directory Retirement (Before Batch 9)
* **Option 1:** Remove the 12 empty `.gitkeep` directories (`docs/verification/IMP-016` ~ `IMP-027`).
* **Option 2:** Retain directories with explanatory placeholder notes.
* *Recommendation:* **Option 1 (Retire)** since `docs/verification/evidence_index.md` fully indexes actual evidence.

### Decision Gate 4: `docs/rework/` Final Workspace Disposition (Before Batch 10)
* **Option 1:** Retain `docs/rework/` as an immutable record of the convergence process.
* **Option 2:** Move `docs/rework/` into `docs/archive/rework/`.
* *Recommendation:* **Option 1 (Retain)** to preserve the audit trail.

---

## 11. Stop Conditions

Execution of any migration batch must **immediately stop and report** if any of the following conditions occur:

1. A discrepancy between production code/config and requirements is identified that constitutes a potential **A-class functional blocker**.
2. Any newly analyzed runtime evidence contradicts the established **MVP closure baseline**.
3. Reconciling documentation requires modifying production navigation behavior or controller algorithms.
4. Unexpected modifications appear in `src/`, `maps/`, `config/`, or tests during documentation updates.
5. An unresolved authority conflict arises that cannot be settled by `docs/rework/02_authority_model.md`.
6. A migration action requires deleting unique, unindexed physical evidence.
7. Markdown link churn exceeds planned batch boundaries.

---

## 12. Definition of Done

The `mobile_base` documentation convergence is complete when:

* [ ] System architecture has exactly **one canonical authority** aligned with as-built code, launch files, and YAML configurations.
* [ ] Requirements (SYS-001 ~ SYS-034) are normative, unambiguous, and free of obsolete component references.
* [ ] Requirement traceability matrix exists, mapping 100% of SYS requirements to code, verification methods, verification status, and evidence.
* [ ] Verification evidence index exists, classifying all committed raw logs and phase reports in place.
* [ ] Root `docs/README.md` is completely up to date, presenting verified milestone status, system overview, and role-based entrypoints.
* [ ] Operational bringup guides (`MAPPING.md`, `NAVIGATION.md`) match production launch arguments and scripts.
* [ ] Superseded documents (`06_subsystem.md`, `verification/README.md`) are clearly marked or replaced.
* [ ] Historical materials (`research/`, `handoff/`, `04_reuse_assessment.md`, `07_implementation.md`, checklists) are designated non-authoritative.
* [ ] Zero broken relative links exist across the documentation tree.
* [ ] Zero unintended modifications exist in production source code, launch files, parameter YAMLs, URDF models, or tests.
* [ ] `git status --short` is clean across the repository.

---

## 13. Recommended First Execution Batch

* **Recommended First Batch:** **Batch 1 — Verification Evidence Index** (`docs/verification/evidence_index.md`).
* **Rationale:**
  1. *Completely Non-Destructive:* Operates in pure addition mode; zero existing files moved, renamed, or deleted.
  2. *Solid Ground Truth:* Catalogs 100% of physical evidence and historical test records, establishing the factual basis needed for Batch 2 (Traceability Matrix) and Batch 3 (Architecture Consolidation).
  3. *Zero Risk to Active System:* Does not touch requirements, architecture, or code.

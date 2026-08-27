# Target Documentation Structure

## 1. Design Principles

This target documentation structure is designed to establish a clean, maintainable, and unambiguous documentation baseline for `mobile_base`. It adheres to [`docs/rework/02_authority_model.md`](file:///home/zzz/mobile_base/docs/rework/02_authority_model.md) and follows these core principles:

1. **One Technical Fact, One Canonical Owner:** Every architectural fact, interface specification, or operational rule is maintained in exactly one authoritative location. Other documents cross-reference rather than duplicate.
2. **Minimal Canonical Entry Set:** Maintain a small canonical documentation set with as few entry documents as necessary. Avoid optimizing toward an arbitrary document count.
3. **Source and Configuration as As-Built Authority:** Runtime parameter values, topics, and launch arguments live in source code and YAML configuration files. Documentation describes architectural roles and patterns without mirroring volatile numerical constants.
4. **Generalized Verification Traceability:** Traceability links requirements to implementation, explicit verification methods (automated test, static inspection, hardware procedure, runtime observation), and execution evidence.
5. **Decoupled Classification from Physical Relocation:** Information status (`ACTIVE`, `HISTORICAL`, `SUPERSEDED`) is established conceptually. Physical file relocation is evaluated independently based on link churn and maintenance benefit.
6. **Operational Guidance Close to Executable Code:** Operator workflows and launch instructions are maintained alongside the executable launch files in `mobile_base_bringup`.
7. **In-Place Evidence Indexing:** Verification evidence artifacts are classified and indexed in place, avoiding link churn across historical commits and reports.

---

## 2. Reader Entry Points

The target documentation structure provides clear, role-specific entry paths without duplicating content:

```text
                                 [docs/README.md]
                     (Root System Overview & Document Index)
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        ▼                              ▼                              ▼
  [General / PM]              [Software Engineer]           [Verification Engineer]
  - 01_use_cases.md           - System Architecture         - traceability_matrix.md
  - 02_capabilities.md        - MAPPING.md / NAVIGATION.md  - evidence_index.md
  - 03_requirements.md        - design_baseline/m1_*.md     - tests & raw evidence
        │                              │                              │
        └──────────────────────────────┼──────────────────────────────┘
                                       ▼
                                  [AI Agent]
                         - AGENTS.md (Workflow & Policies)
                         - docs/README.md (Entrypoint & Doc Map)
                         - Target Canonical Document
```

* **General / PM / New Engineer:** Enters at [`docs/README.md`](file:///home/zzz/mobile_base/docs/README.md) to understand system purpose, verified v0.1.0 milestone status, high-level capabilities, and navigation links.
* **Software Engineer:** Enters via System Architecture documentation for subsystem responsibilities, coordinate frames, and data flows; uses `src/mobile_base_bringup/` operational guides for bringup and execution.
* **Verification Engineer:** Enters via `docs/verification/traceability_matrix.md` and `evidence_index.md` to audit requirement coverage, verification methods, and committed evidence logs.
* **AI Agent:** Enters via [`AGENTS.md`](file:///home/zzz/mobile_base/AGENTS.md) for workflow policies, reads [`docs/README.md`](file:///home/zzz/mobile_base/docs/README.md) for documentation routing, and inspects only the canonical document relevant to the active task.
  * *Note on Workspace Governance:* During this convergence rework, [`docs/rework/02_authority_model.md`](file:///home/zzz/mobile_base/docs/rework/02_authority_model.md) serves as temporary governance. `docs/rework/` is not a permanent production entrypoint; its final disposition will be decided upon migration completion.

---

## 3. Proposed Canonical Documentation Set

The active, canonical documentation set consists of the following documents:

### 1. `docs/README.md` (System Entrypoint and Navigation Index)
* **Information Role:** `ACTIVE`
* **Purpose:** Serves as the authoritative front door to the repository.
* **Information Owned:** Project summary, verified v0.1.0 milestone status, high-level capability summary, and canonical document navigation index.
* **Information NOT Owned:** Detailed requirement lists, subsystem interface tables, launch parameter values, or raw verification logs.
* **Primary Readers:** All contributors, PMs, engineers, and AI agents.
* **Derives From:** Current as-built status and confirmed Phase 1 audit baseline.
* **Target Action:** **REWRITE** (replaces stale `docs/README.md`).

### 2. `docs/01_use_cases.md` (Operational Use Cases)
* **Information Role:** `ACTIVE`
* **Purpose:** Defines operator workflows and operational boundaries from an external user perspective.
* **Information Owned:** UC-001 (Mapping) and UC-002 (Navigation) basic flows, alternative flows, and completion criteria.
* **Information NOT Owned:** ROS 2 node architecture, algorithms, topic names, or controller configurations.
* **Primary Readers:** PMs, software engineers, verification engineers.
* **Target Action:** **KEEP IN PLACE** (retains approved normative content; avoids path churn).

### 3. `docs/02_capabilities.md` (System Capabilities)
* **Information Role:** `ACTIVE`
* **Purpose:** Defines the external capabilities provided by the robot base.
* **Information Owned:** CAP-001 (Map creation and persistence) and CAP-002 (Autonomous destination navigation).
* **Information NOT Owned:** Internal software component decomposition or execution steps.
* **Primary Readers:** PMs, system engineers.
* **Target Action:** **KEEP IN PLACE** (retains approved normative content; avoids path churn).

### 4. `docs/03_requirements.md` (System Requirements)
* **Information Role:** `ACTIVE`
* **Purpose:** Defines normative, observable system requirements and acceptance criteria.
* **Information Owned:** SYS-001 through SYS-034 requirement definitions and UC/CAP traceability links.
* **Information NOT Owned:** Internal code structure, class interfaces, or tuning parameters.
* **Primary Readers:** Software engineers, verification engineers.
* **Target Action:** **KEEP IN PLACE** (retains approved normative content; avoids path churn).

### 5. System Architecture & Subsystem Design Documentation
* **Information Role:** `ACTIVE`
* **Purpose:** Serves as the authoritative architecture specification for `mobile_base`.
* **System Architecture Domain Owns:** 7-subsystem allocation model, coordinate frames (REP-103/105), dynamic TF ownership, system data flows (LiDAR, IMU, odometry, SLAM, AMCL, Nav2, Collision Monitor), velocity safety intercept chain, operational mode mutual exclusion, and 6 custom gap boundaries.
* **Subsystem-Level Design Domain Owns:** Internal subsystem node responsibilities, interface message types, failure/error handling behaviors, and component-specific design details (without duplicating YAML parameters).
* **Packaging Decision (UNDECIDED):**
  * *Option A:* Single unified `docs/architecture/system_architecture.md` (or updated `docs/05_architecture.md`) with concise subsystem sections.
  * *Option B:* System architecture document + one companion `subsystems.md`.
  * *Excluded:* Decomposing into 7 individual S1–S7 files is explicitly rejected to prevent fragmentation and duplicate maintenance.
* **Target Action:** **REWRITE / CONSOLIDATE** (replaces `docs/05_architecture.md` and supersedes `docs/06_subsystem.md`).

### 6. `docs/design_baseline/m1_driver.md` & `m1_hardware.md` (Component Design Baselines)
* **Information Role:** `ACTIVE`
* **Purpose:** Provide authoritative low-level reference for the M1 motor driver Modbus protocol and `ros2_control` hardware interface.
* **Information Owned:** Modbus RTU register mapping, FC17 timing constraints, checksums, error codes, and `SystemInterface` lifecycle.
* **Information NOT Owned:** System-level navigation architecture or high-level requirements.
* **Primary Readers:** Base control engineers, embedded software engineers.
* **Target Action:** **KEEP IN PLACE**.

### 7. `src/mobile_base_bringup/MAPPING.md` & `NAVIGATION.md` (Operational Execution Guides)
* **Information Role:** `ACTIVE`
* **Purpose:** Provide operational step-by-step instructions for launching, teleoperating, and navigating the robot.
* **Information Owned:** Canonical launch CLI commands (`mobile_base.launch.py mode:=mapping|navigation site:=<site>`), prerequisite checks, map saving commands (`save_map.sh`), and station navigation execution (`navigate_to_station`).
* **Information NOT Owned:** Normative requirement definitions or theoretical architecture derivations.
* **Primary Readers:** Robot operators, test engineers, software developers.
* **Target Action:** **KEEP IN PLACE** (package-local adjacent to launch files).

### 8. `docs/verification/traceability_matrix.md` (Requirement Traceability Matrix)
* **Information Role:** `ACTIVE`
* **Purpose:** Establishes complete bidirectional traceability across requirements, implementation, verification methods, and evidence.
* **Information Owned:** Mapping table: SYS-xxx $\longrightarrow$ Subsystem $\longrightarrow$ Implementation Artifact $\longrightarrow$ Verification Method $\longrightarrow$ Execution Evidence.
* **Information NOT Owned:** Test execution logs, narrative implementation stories, or code implementations.
* **Primary Readers:** Verification engineers, PMs, auditors.
* **Target Action:** **NEW** (replaces obsolete traceability tables in `docs/07_implementation.md`).

### 9. `docs/verification/evidence_index.md` (Verification Evidence Index)
* **Information Role:** `ACTIVE`
* **Purpose:** Catalogs and classifies all committed verification evidence artifacts.
* **Information Owned:** Structured index of raw logs in `docs/verification/` and phase reports in `docs/evidence/`, specifying commit hash, date, hardware context, evidence classification, and status.
* **Information NOT Owned:** Requirement definitions or raw log data itself.
* **Primary Readers:** Verification engineers, AI agents.
* **Target Action:** **NEW** (replaces drifted `docs/verification/README.md`).

### 10. `docs/XX_backlog.md` (Post-v0.1 Backlog)
* **Information Role:** `ACTIVE`
* **Purpose:** Tracks features, enhancements, and research subjects intentionally deferred beyond v0.1.0.
* **Information Owned:** Backlog items (dynamic obstacle avoidance replanning, simulation platforms, fleet action server).
* **Information NOT Owned:** Active v0.1 baseline commitments.
* **Primary Readers:** PMs, software engineers.
* **Target Action:** **KEEP IN PLACE**.

---

## 4. Requirements Strategy

* **Decision: KEEP IN PLACE `docs/01_use_cases.md`, `docs/02_capabilities.md`, and `docs/03_requirements.md`.**
* **Rationale:**
  1. *Distinct Abstraction Tiers:*
     - `01_use_cases.md`: Operational workflows and boundary conditions from an operator's perspective (UC-001, UC-002).
     - `02_capabilities.md`: High-level system functional capabilities (CAP-001, CAP-002).
     - `03_requirements.md`: Observable engineering requirements, mathematical constraints, and acceptance criteria (SYS-001 ~ SYS-034).
  2. *Link Stability and Churn Prevention:* System requirements, test references, git history, and existing documentation cross-reference these exact filenames. Relocating them to a subfolder provides minimal structural benefit while introducing significant link churn.
* **Boundary Enforcement:**
  * `01_use_cases.md` must not specify internal ROS node names or topics.
  * `02_capabilities.md` must remain high-level functional boundaries.
  * `03_requirements.md` must specify observable behavioral and safety constraints without specifying internal algorithm classes or implementation structures.

---

## 5. Architecture & Design Strategy

* **Information Domain Division:**
  * **System Architecture Domain:** Owns system-level decomposition, subsystem allocation, system-wide data flows, coordinate frames (REP-103/105), dynamic TF ownership, operational mode boundaries, velocity safety interception, and cross-subsystem contracts.
  * **Subsystem-Level Design Domain:** Owns internal node decomposition, interface message types, failure/error handling, and component design details without duplicating YAML parameters.
* **Packaging Options (UNDECIDED):**
  * *Option A:* Single `system_architecture.md` (or updated `05_architecture.md`) containing concise subsystem sections.
  * *Option B:* `system_architecture.md` + one companion `subsystems.md`.
  * *Rule:* Decomposing into 7 individual S1–S7 files is explicitly rejected. The final choice between Option A and Option B will be made during Migration Plan formulation.
* **Reuse Assessment Disposition:**
  * `docs/04_reuse_assessment.md` is classified as `HISTORICAL / NON-AUTHORITATIVE`.
  * Active selection rationale (Kinematic-ICP, Nav2, `slam_toolbox`, EKF) and the 6 thin custom gap boundaries (GAP-01 through GAP-06) will be summarized in the system architecture documentation.
  * Physical relocation of `04_reuse_assessment.md` is `UNDECIDED` (evaluated during Migration Plan).
* **Component Design Baselines:**
  * `docs/design_baseline/m1_driver.md` and `m1_hardware.md` remain `ACTIVE` and `KEEP IN PLACE` as specialized component-level references for M1 Modbus protocol and `ros2_control` interface.

---

## 6. Implementation Narrative Strategy

* **Information Decision:** `docs/07_implementation.md` is classified as `HISTORICAL / NON-AUTHORITATIVE`.
* **Rationale:**
  1. `docs/07_implementation.md` was a temporary tracking mechanism during construction. It combines process manuals, draft templates, superseded RF2O evaluations, checklist duplicates, and citations of 6 nonexistent test filenames.
  2. It must stop serving as an active architecture or verification authority.
  3. Its essential active responsibilities migrate to:
     * `docs/verification/traceability_matrix.md` (traceability from requirements to code, verification methods, and evidence).
     * `docs/verification/evidence_index.md` (structured catalog of committed evidence).
* **Physical Disposition:** Physical relocation / archive destination is `UNDECIDED` (deferred to Migration Plan based on link churn evaluation).

---

## 7. Operations Strategy

* **Keep Operational Guides Package-Local:**
  - `src/mobile_base_bringup/MAPPING.md` and `NAVIGATION.md` remain `KEEP IN PLACE` in `src/mobile_base_bringup/`, colocated with the launch files and scripts they document.
  - `docs/README.md` provides direct links to these guides.
* **Single Source for Launch Syntax:**
  - Operational guides document execution CLI commands and options.
  - Launch files and YAML files remain the sole authority for default parameters.
  - Operational guides must not duplicate full YAML parameter blocks.

---

## 8. Verification & Evidence Strategy

* **Generalized Verification Traceability Model:**
  $$\text{Requirement (SYS-xxx)} \longrightarrow \text{Implementation Source} \longrightarrow \text{Verification Method} \longrightarrow \text{Execution Evidence}$$
  * **Verification Methods include:**
    - Automated test (unit, integration, launch tests in `src/*/test/`)
    - Static / config inspection (YAML, URDF, launch syntax)
    - Hardware procedure (pre-flight checks, physical wiring/motion verification)
    - Runtime observation (AMCL convergence, teleoperation response)
    - Integration test (end-to-end launch verification)
  * Not every requirement mandates an automated software test; the traceability matrix records the actual, appropriate verification method.
* **Individual Artifact Classification in `evidence_index.md`:**
  * `docs/verification/evidence_index.md` will index and classify each artifact individually:
    - **Current-supporting historical runtime evidence:** (e.g. Phase R1, R2, R3, R3.5, R5 reports; scan decoupling report; launch optimization report; IMP-007~015 raw logs).
    - **Historical evidence:** (e.g. baseline reset audit reports, discovery reports).
    - **Superseded evidence:** (e.g. `phase_cm_f1_collision_scan_self_filter_report.txt` for removed filter).
    - **Investigation-only:** (e.g. station navigation design investigation notes).
    - **Obsolete / invalid:** (e.g. pre-Kinematic-ICP RF2O trial artifacts).
* **Preserve Evidence File Locations:**
  - Raw evidence files in `docs/verification/IMP-007` ~ `IMP-015` and reports in `docs/evidence/` **remain in their exact existing file paths**.
  - Classification and indexing do not require physical file movement.
* **Empty Directories (`IMP-016` ~ `IMP-027`):**
  - **Status:** Candidate for retirement during cleanup because they contain no evidence artifacts.
  - **Physical Disposition:** `UNDECIDED` until Migration Plan.

---

## 9. Historical Material Strategy

* **Decouple Classification from Relocation:**
  - The following artifacts are formally classified as `HISTORICAL / NON-AUTHORITATIVE`:
    - `docs/research/` (32 feasibility notes)
    - `docs/handoff/` (5 session transcripts)
    - Checklists (`04_reuse_assessment_checklist.md`, `05_architecture_checklist.md`, `06_subsystem_checklist.md`, `07_implementation_checklist.md`)
    - `docs/04_reuse_assessment.md` (historical candidate evaluations)
    - `docs/07_implementation.md` (historical construction narrative)
    - `docs/m1_bringup_validation/` (early bringup scripts and notes)
    - `docs/design_baseline/write_from_use_case_to_architecture.md` (process guide)
* **Physical Disposition:**
  - Physical relocation (e.g. into a consolidated `docs/archive/` folder vs. keeping in place with a historical banner) remains **`UNDECIDED`**.
  - This will be evaluated during the Migration Plan based on link churn, Git history preservation, and maintenance benefit.

---

## 10. Proposed Final Information Tree

The following tree represents the **Target Information Model** (not a forced file-movement plan):

```text
mobile_base/
├── AGENTS.md                                  # [ACTIVE | KEEP] Agent workflow and collaboration policy
├── Dockerfile                                 # [ACTIVE | KEEP] Container build baseline
├── compose.yaml                               # [ACTIVE | KEEP] Development compose service
├── maps/
│   ├── test_site/                             # [ACTIVE | KEEP] Operational deployment site data
│   │   ├── map.yaml
│   │   ├── map.pgm
│   │   ├── stations.yaml
│   │   └── route_graph.geojson
│   └── template/                              # [ACTIVE | KEEP] Site template layout
├── src/                                       # [ACTIVE | KEEP] 10 ROS 2 packages & automated tests
│   └── mobile_base_bringup/
│       ├── MAPPING.md                         # [ACTIVE | KEEP] Operational mapping workflow guide
│       └── NAVIGATION.md                      # [ACTIVE | KEEP] Operational navigation workflow guide
└── docs/
    ├── README.md                              # [ACTIVE | REWRITE] Root system entrypoint and doc index
    ├── 01_use_cases.md                        # [ACTIVE | KEEP IN PLACE] Normative operational use cases
    ├── 02_capabilities.md                     # [ACTIVE | KEEP IN PLACE] Normative system capabilities
    ├── 03_requirements.md                     # [ACTIVE | KEEP IN PLACE] Normative requirements (SYS-001~034)
    ├── 05_architecture.md (or architecture/)  # [ACTIVE | REWRITE] System architecture (Packaging: A vs B UNDECIDED)
    ├── 06_subsystem.md                        # [SUPERSEDED] Superseded by consolidated architecture
    ├── 04_reuse_assessment.md                 # [HISTORICAL] Historical candidate trade-offs (Physical: UNDECIDED)
    ├── 07_implementation.md                   # [HISTORICAL] Historical construction narrative (Physical: UNDECIDED)
    ├── XX_backlog.md                          # [ACTIVE | KEEP] Post-v0.1 backlog items
    ├── *checklist.md (04, 05, 06, 07)         # [HISTORICAL] Historical stage checklists (Physical: UNDECIDED)
    ├── design_baseline/                       # [ACTIVE | KEEP]
    │   ├── m1_driver.md                       # [ACTIVE | KEEP] M1 Modbus protocol reference
    │   ├── m1_hardware.md                     # [ACTIVE | KEEP] M1 ros2_control SystemInterface reference
    │   └── write_*.md                         # [HISTORICAL] Process manual (Physical: UNDECIDED)
    ├── verification/                          # [ACTIVE | RESTRUCTURE]
    │   ├── traceability_matrix.md             # [ACTIVE | NEW] Traceability: SYS -> Code -> Method -> Evidence
    │   ├── evidence_index.md                  # [ACTIVE | NEW] Classified catalog of all evidence artifacts
    │   ├── README.md                          # [SUPERSEDED] Replaced by evidence_index.md
    │   ├── IMP-007/ ... IMP-015/              # [ACTIVE | KEEP IN PLACE] Committed raw logs & CSVs
    │   └── IMP-016/ ... IMP-027/              # [RETIRE CANDIDATE] Empty dirs (Physical: UNDECIDED)
    ├── evidence/*.txt (17 files)              # [ACTIVE/HIST/SUP | KEEP IN PLACE] Classified in evidence_index
    ├── research/ (32 files)                   # [HISTORICAL] Research notes (Physical: UNDECIDED)
    ├── handoff/ (5 files)                     # [HISTORICAL] Session transcripts (Physical: UNDECIDED)
    └── m1_bringup_validation/                 # [HISTORICAL] Early bringup logs (Physical: UNDECIDED)
```

---

## 11. Current → Target Mapping

| Current File / Directory | Information Role | Target Role | Physical Action | Notes |
|---|:---:|---|:---:|---|
| [`docs/README.md`](file:///home/zzz/mobile_base/docs/README.md) | `ACTIVE` | System Entrypoint & Navigation Index | **REWRITE** | Synchronize milestone status, system overview, and canonical doc index. |
| [`docs/01_use_cases.md`](file:///home/zzz/mobile_base/docs/01_use_cases.md) | `ACTIVE` | Normative Operational Use Cases | **KEEP IN PLACE** | Retains approved use cases (UC-001, UC-002); prevents link churn. |
| [`docs/02_capabilities.md`](file:///home/zzz/mobile_base/docs/02_capabilities.md) | `ACTIVE` | Normative System Capabilities | **KEEP IN PLACE** | Retains approved capabilities (CAP-001, CAP-002); prevents link churn. |
| [`docs/03_requirements.md`](file:///home/zzz/mobile_base/docs/03_requirements.md) | `ACTIVE` | Normative System Requirements | **KEEP IN PLACE** | Retains approved requirements (SYS-001 ~ SYS-034); prevents link churn. |
| [`docs/04_reuse_assessment.md`](file:///home/zzz/mobile_base/docs/04_reuse_assessment.md) | `HISTORICAL` | Historical Reuse Trade-offs | **UNDECIDED** | Non-authoritative; active reuse summarized in architecture. |
| [`docs/05_architecture.md`](file:///home/zzz/mobile_base/docs/05_architecture.md) | `ACTIVE` | System Architecture Specification | **REWRITE** | Authoritative architecture; incorporates as-built subsystem details. |
| [`docs/06_subsystem.md`](file:///home/zzz/mobile_base/docs/06_subsystem.md) | `SUPERSEDED` | Superseded Subsystem Baseline | **MERGE / RETIRE** | As-built specifications merged into architecture; removes ghost interfaces. |
| [`docs/07_implementation.md`](file:///home/zzz/mobile_base/docs/07_implementation.md) | `HISTORICAL` | Historical Construction Narrative | **UNDECIDED** | Non-authoritative; active functions migrate to traceability & evidence index. |
| [`docs/07_implementation_checklist.md`](file:///home/zzz/mobile_base/docs/07_implementation_checklist.md) | `HISTORICAL` | Historical Milestone Record | **UNDECIDED** | Preserved for auditability. |
| `docs/04`~`06_*_checklist.md` | `HISTORICAL` | Historical Stage Records | **UNDECIDED** | Preserved for auditability. |
| [`docs/design_baseline/m1_*.md`](file:///home/zzz/mobile_base/docs/design_baseline) | `ACTIVE` | Component Design Baselines | **KEEP IN PLACE** | Component-level M1 protocol and `ros2_control` interface authority. |
| `write_from_use_case_to_architecture.md` | `HISTORICAL` | Process Guide | **UNDECIDED** | Historical process manual. |
| [`docs/research/`](file:///home/zzz/mobile_base/docs/research) (32 files) | `HISTORICAL` | Feasibility Research Notes | **UNDECIDED** | Reference-only; non-authoritative. |
| [`docs/handoff/`](file:///home/zzz/mobile_base/docs/handoff) (5 files) | `HISTORICAL` | Session Transcripts | **UNDECIDED** | Reference-only; non-authoritative. |
| [`docs/evidence/*.txt`](file:///home/zzz/mobile_base/docs/evidence) (17 files) | `MIXED` | Evidence Artifacts | **KEEP IN PLACE** | Classified individually in `evidence_index.md`. |
| `docs/verification/IMP-007`~`015` | `ACTIVE` | Raw Hardware Verification Logs | **KEEP IN PLACE** | Retain in place; indexed by `evidence_index.md`. |
| `docs/verification/IMP-016`~`027` | `SUPERSEDED` | Empty Placeholders | **RETIRE CANDIDATE** | Empty `.gitkeep` directories; final disposition in Migration Plan. |
| [`docs/verification/README.md`](file:///home/zzz/mobile_base/docs/verification/README.md) | `SUPERSEDED` | Drifted IMP Index | **REPLACE** | Replaced by `evidence_index.md`. |
| [`docs/m1_bringup_validation/`](file:///home/zzz/mobile_base/docs/m1_bringup_validation) | `HISTORICAL` | Early Motor Bringup Suite | **UNDECIDED** | Reference-only; non-authoritative. |
| [`src/mobile_base_bringup/MAPPING.md`](file:///home/zzz/mobile_base/src/mobile_base_bringup/MAPPING.md) | `ACTIVE` | Operational Mapping Guide | **KEEP IN PLACE** | Package-local bringup documentation. |
| [`src/mobile_base_bringup/NAVIGATION.md`](file:///home/zzz/mobile_base/src/mobile_base_bringup/NAVIGATION.md) | `ACTIVE` | Operational Navigation Guide | **KEEP IN PLACE** | Package-local bringup documentation. |
| [`docs/XX_backlog.md`](file:///home/zzz/mobile_base/docs/XX_backlog.md) | `ACTIVE` | Future Backlog Tracking | **KEEP IN PLACE** | Retains backlog items. |

---

## 12. Duplication Prevention Rules

To prevent future documentation drift and maintain strict Single Source of Truth integrity:

| Information Category | Sole Authoritative Location | Forbidden in Other Documents |
|---|---|---|
| **Numerical Parameter Values & Watchdogs** | Parameter YAMLs (`src/*/config/*.yaml`) | Must not be duplicated into architecture or requirement docs. |
| **Subsystem Allocation, Data Flows & TF Ownership** | System Architecture documentation | Must not be redefined in bringup guides or README. |
| **Observable Requirements & Acceptance Criteria** | [`docs/03_requirements.md`](file:///home/zzz/mobile_base/docs/03_requirements.md) | Must not be rewritten or diluted in architecture or test files. |
| **Operational CLI Commands & Bringup Steps** | `src/mobile_base_bringup/MAPPING.md`, `NAVIGATION.md` | Must not be duplicated into architecture documents. |
| **Traceability Mapping & Verification Methods** | `docs/verification/traceability_matrix.md` | Must not be maintained in separate parallel matrices. |
| **Evidence Metadata & Execution Log Catalogs** | `docs/verification/evidence_index.md` | Must not be asserted as narrative prose in requirements. |
| **Design Trade-off History & Superseded Analyses** | Historical documents (marked `HISTORICAL`) | Must not be intermingled with active runtime architecture. |

---

## 13. Decisions Still Open

The following decisions remain intentionally open and will be evaluated during Migration Plan formulation:
1. **Architecture Packaging:** Whether as-built subsystem specifications are integrated entirely into a single system architecture document (Option A) or held in a companion `subsystems.md` (Option B).
2. **Physical Relocation of Historical Files:** Whether `docs/research/`, `docs/handoff/`, `04_reuse_assessment.md`, `07_implementation.md`, and checklists are physically moved to a `docs/archive/` folder or retained in place with top-of-file historical banners.
3. **Empty Directory Retirement:** The exact batch and mechanism for removing the 12 empty `docs/verification/IMP-016~027` `.gitkeep` directories.
4. **Post-Migration Workspace Disposition:** The final cleanup/retention disposition of temporary convergence files in `docs/rework/`.

---

## 14. Recommended Next Batch

* **Recommended Next Batch:** **Phase 2 — Batch 3: Migration Plan & Execution Roadmap** (`docs/rework/04_migration_plan.md`).
* **Objective:** Define staged, reviewable, and reversible execution batches for migrating documentation to the approved target information structure without disrupting repository baseline stability or test traceability.

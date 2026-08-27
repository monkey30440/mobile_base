# Documentation Authority Model

## 1. Purpose

The purpose of this document is to establish unambiguous rules for information authority across the `mobile_base` repository.

Parallel, duplicate maintenance of the same architectural or runtime facts across multiple documents is prohibited. Each information domain has a designated primary source of truth. When documentation, code, configuration, or historical notes conflict, this Authority Model governs which source takes precedence.

---

## 2. Core Information Classes

### Requirement
* **Definition:** Defines what the system must do, its observable behaviors, safety limits, and acceptance criteria.
* **Primary Authority:** [`docs/03_requirements.md`](file:///home/zzz/mobile_base/docs/03_requirements.md), [`docs/01_use_cases.md`](file:///home/zzz/mobile_base/docs/01_use_cases.md), [`docs/02_capabilities.md`](file:///home/zzz/mobile_base/docs/02_capabilities.md).
* **Governance Rule:** Requirements specify product intent and verification obligations. They are subject to formal consistency review, but serve as the normative benchmark against which implementation compliance is judged.

### Design
* **Definition:** Documents the chosen architectural patterns, subsystem decomposition, rationale, and component integration strategies.
* **Primary Authority:** Formal architecture and component design baseline documents ([`docs/05_architecture.md`](file:///home/zzz/mobile_base/docs/05_architecture.md), [`docs/design_baseline/m1_driver.md`](file:///home/zzz/mobile_base/docs/design_baseline/m1_driver.md), [`docs/design_baseline/m1_hardware.md`](file:///home/zzz/mobile_base/docs/design_baseline/m1_hardware.md)).
* **Governance Rule:** Design documents provide rationale and structural guidelines, but cannot override as-built implementation facts. If a design document specifies an interface, parameter, or component that differs from production source or launch files, the design document is stale and must be updated.

### As-Built
* **Definition:** Represents the physical and software reality currently implemented and executed.
* **Primary Authority:** Production source code (`src/*`), launch files (`src/*/launch/*`), parameter YAMLs (`src/*/config/*`), URDF/Xacro models, Behavior Tree XML definitions, and package manifests (`package.xml`, `CMakeLists.txt`).
* **Governance Rule:** As-built artifacts are the supreme authority for topics, coordinate frames, TF ownership, launch arguments, and node composition.

### Site / Runtime Data
* **Definition:** Specifies the exact map image, origin, coordinate points, station definitions, and topological route graphs for an operational deployment site.
* **Primary Authority:** Production site directories under `maps/<site>/` (e.g. [`maps/test_site/`](file:///home/zzz/mobile_base/maps/test_site): `map.yaml`, `stations.yaml`, `route_graph.geojson`).
* **Governance Rule:** Template directories (e.g. `maps/template/`) are structural placeholders and are non-authoritative for runtime deployment.

### As-Verified
* **Definition:** Records what has been tested, under what conditions, and with what evidence.
* **Authority Model:** As-verified status is established by a combination of:
  1. **Test / verification definition** (specifying what should be executed and its pass/fail criteria),
  2. **Execution record** (specifying what was actually executed, by whom, at what commit, and its result),
  3. **Supporting raw/log artifact where applicable** (providing observable verification data).
* **Governance Rule:**
  * Test definitions specify what should be executed.
  * Execution records state what was actually executed and its outcome.
  * Raw artifacts support the execution result.
  * Structured reports are summaries and indices of verification evidence; they do not automatically supersede raw artifacts.
  * If a historical report is the sole retained execution record for a past test run, it serves as historical evidence bound to its originating context and commit.
  * Narrative assertions in documentation without execution records or supporting artifacts do not constitute proof. Historical evidence does not automatically certify current HEAD or subsequent commits.

### Operational Guidance
* **Definition:** Instructs engineers and operators on how to build, launch, operate, and maintain the system.
* **Primary Authority:** Bringup operational guides ([`src/mobile_base_bringup/MAPPING.md`](file:///home/zzz/mobile_base/src/mobile_base_bringup/MAPPING.md), [`src/mobile_base_bringup/NAVIGATION.md`](file:///home/zzz/mobile_base/src/mobile_base_bringup/NAVIGATION.md)), deployment scripts, and approved operational manuals.
* **Governance Rule:** If operational guides conflict with launch files or parameter YAMLs, the production code/config is authoritative, and the operational guide must be corrected.

### Historical Context
* **Definition:** Preserves architectural research, prior candidate trade-offs, session handoffs, and superseded validation attempts.
* **Primary Authority:** [`docs/research/`](file:///home/zzz/mobile_base/docs/research), [`docs/handoff/`](file:///home/zzz/mobile_base/docs/handoff), [`docs/04_reuse_assessment.md`](file:///home/zzz/mobile_base/docs/04_reuse_assessment.md) (historical candidate comparisons), and [`docs/m1_bringup_validation/`](file:///home/zzz/mobile_base/docs/m1_bringup_validation).
* **Governance Rule:** Strictly informational and reference-only. Prohibited from serving as current system truth or overriding active baselines.

### Collaboration & AI Workflow
* **Definition:** Defines rules of engagement for human and AI contributors, change workflows, GitNexus usage, and quality discipline.
* **Primary Authority:** [`AGENTS.md`](file:///home/zzz/mobile_base/AGENTS.md).
* **Governance Rule:** Governs developer and agent behavior; does not define robot technical requirements or software architecture.

---

## 3. Conflict Resolution Rules

1. **Requirement vs Implementation:**
   * Neither is automatically presumed incorrect.
   * Requirements define required observable behavior; implementation defines current runtime reality.
   * Implementation does NOT override or redefine requirements. Discrepancies between requirements and implementation represent either a compliance gap to be resolved in code or an outdated requirement requiring formal revision approval.
2. **Design vs Implementation:**
   * For determining current as-built reality, production source, launch files, and configuration take precedence over design documentation.
   * Conflicting design documents must be updated to align with the approved as-built state.
3. **Documentation Narrative vs Runtime Evidence:**
   * Concrete runtime evidence (raw CSVs, logs, execution outputs) supersedes text narrative claims.
   * Narrative text claiming completion without committed test sources or raw logs is classified as an unverified claim.
4. **Historical Evidence vs Current Implementation:**
   * Verification evidence is valid only for the commit, configuration, and hardware environment in which it was captured.
   * When architectural refactoring (e.g. scan decoupling) modifies a subsystem, pre-refactor evidence for affected scopes is marked historical/superseded.
5. **Multiple Documents Describing the Same Fact:**
   * Only ONE canonical document is permitted to maintain any given architectural fact.
   * Other documents must link to the canonical document rather than duplicating parameter lists, topics, or schemas.

---

## 4. Evidence Language Rules

To maintain technical precision, documentation and reports must use the following standard terms:

* **`Implemented`:** The source code, launch file, parameter configuration, or URDF definition exists in the repository.
* **`Automated test exists`:** An executable automated test source exists under `src/*/test/`.
* **`Historically tested`:** A past test execution result is documented in committed evidence reports or logs from a specific commit.
* **`Verified on hardware`:** A physical hardware execution was performed and supported by committed raw logs, telemetry, or structured phase reports.
* **`Current verified`:** Validation was executed and confirmed on the active HEAD and working tree baseline.
* **`Known limitation`:** An observed runtime symptom exists that is documented and bounded, but does not invalidate the accepted MVP scope.
* **`Root cause undetermined`:** Telemetry or diagnostic data is insufficient to conclusively identify the underlying failure mechanism.
* **Prohibited Terms (unless strictly defined with direct evidence):** "fully verified", "100% complete", "production ready", "proven".

---

## 5. Single-Source-of-Truth Rule

In all future documentation convergence work:
* Requirement information describes ONLY required observable behaviors and acceptance criteria.
* Architecture-level design information describes ONLY subsystem decomposition, data flows, coordinate transformations, TF ownership, and system-wide contracts.
* Subsystem-level design information describes internal structure, interfaces, parameter roles, and error handling without duplicating system architecture or runtime configuration values.
* Verification information indexes test definitions, execution records, traceability mappings, and evidence artifacts.
* Operational information describes execution commands, deployment workflows, and maintenance procedures.
* Historical information is isolated to preserve decision context without redefining active truth.

---

## 6. Authority Decision Table

| Information Type | Primary Source of Truth | Secondary Reference | Must Not Override |
|---|---|---|---|
| **Requirements** | [`docs/03_requirements.md`](file:///home/zzz/mobile_base/docs/03_requirements.md), [`01_use_cases.md`](file:///home/zzz/mobile_base/docs/01_use_cases.md), [`02_capabilities.md`](file:///home/zzz/mobile_base/docs/02_capabilities.md) | Verification acceptance criteria | As-built implementation facts |
| **Design** | [`docs/05_architecture.md`](file:///home/zzz/mobile_base/docs/05_architecture.md), [`docs/design_baseline/m1_*.md`](file:///home/zzz/mobile_base/docs/design_baseline) | [`04_reuse_assessment.md`](file:///home/zzz/mobile_base/docs/04_reuse_assessment.md) | Production source, launch, and config |
| **As-Built** | Production source (`src/*`), launch files, YAML configs, URDF, BT XML | As-built architecture documentation | Normative requirements (cannot silently alter specs) |
| **Site Data** | [`maps/<site>/`](file:///home/zzz/mobile_base/maps) (`map.yaml`, `stations.yaml`, `route_graph.geojson`) | Operational site guides | As-built coordinate frames and robot footprint |
| **Verification** | Combination of test definitions (`src/*/test/`), execution records, and supporting raw logs/artifacts (`docs/verification/`, `docs/evidence/`) | Verification summary reports and traceability matrices | Code reality (cannot claim uncommitted behavior) or requirement definitions |
| **Operations** | [`src/mobile_base_bringup/MAPPING.md`](file:///home/zzz/mobile_base/src/mobile_base_bringup/MAPPING.md), [`NAVIGATION.md`](file:///home/zzz/mobile_base/src/mobile_base_bringup/NAVIGATION.md) | Launch CLI help strings | Launch files and parameter YAMLs |
| **Historical Context** | [`docs/research/`](file:///home/zzz/mobile_base/docs/research), [`docs/handoff/`](file:///home/zzz/mobile_base/docs/handoff), historical archives | Prior meeting / handoff notes | Current as-built reality or requirements |
| **Workflow** | [`AGENTS.md`](file:///home/zzz/mobile_base/AGENTS.md) | Repository guidelines | Architecture, requirements, or code truth |

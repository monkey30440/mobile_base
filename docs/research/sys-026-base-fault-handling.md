> [!WARNING]
> **HISTORICAL / NON-AUTHORITATIVE**
>
> This document is retained for historical traceability only. It does not define the current system architecture, requirements, operational procedure, or verification authority. Use `docs/README.md` to locate the current canonical documentation.

# SYS-026 Base Fault Handling — Reuse Research

## 1. Research Scope

本筆記只研究 `03_requirements.md` 的下列定案需求，不修改或擴張需求：

> **SYS-026 底盤故障處理**：系統偵測到底盤通訊失敗、馬達驅動器警報或無效／缺失之底盤回授時，應停止接受持續運動輸出、嘗試使底盤停止，並回報故障；實際停止結果與復原行為應經實機驗證。

研究問題是：ROS 2 Jazzy `ros2_control` 能覆蓋哪些 controller/hardware error propagation 與 lifecycle 行為，哪些 M1 communication、alarm、feedback validity、stop attempt 與 fault-detail reporting 仍是 project-specific behavior。

本筆記不以 SYS-026 同時關閉下列相鄰需求：

- SYS-027 運動命令逾時；
- SYS-030 底盤安全啟用與停用；
- SYS-031 底盤安全關閉。

故障後的實際停止與 recovery 只記錄其 evidence boundary，不在本研究虛構已驗證結果或完整 recovery policy。

## 2. Assessment Conclusion

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy `ros2_control` Controller Manager + `hardware_interface::SystemInterface` error contract；hardware diagnostics 使用標準 `diagnostic_updater` mechanism |
| Exact Version / Platform | ROS 2 Jazzy；Ubuntu 24.04 Noble；2026-08-13 Jazzy rosdistro metadata：`ros2_control` 4.47.0-1 |
| Coverage Status | **Partially Covered** |
| Covered Scope | hardware `read()`／`write()` 可回傳 `return_type::ERROR`；Controller Manager 會停止使用該 hardware command/state interfaces 的 controllers；controller/hardware lifecycle state change 可由 `~/activity` 觀察；hardware component 可使用標準 diagnostics mechanism 回報狀態 |
| Known Constraints | framework 不理解 M1 protocol、alarm code 或 feedback validity；controller stopped 不等於實體底盤已停止；標準 activity/timing diagnostics 不包含 M1 fault cause |
| Uncovered Gap | M1-specific failure detection/classification、fault latch、拒絕後續持續運動輸出、bounded best-effort stop attempt、stop-attempt/result state 與具體 fault-detail reporting |
| Missing Evidence | target image exact installed version；fault injection 下的 controller deactivation、command rejection、stop attempt、diagnostic content；communication loss／drive alarm／invalid feedback 時的實際停止結果與 recovery behavior |
| MVP Change Candidate | `None` |

`Partially Covered` 的理由不是 ros2_control error path 不存在，而是 SYS-026 明確要求偵測 M1-specific faults、嘗試使實體底盤停止並回報 fault。這些語意不能由 generic framework 自動推導。

## 3. Requirement Fragments

| Requirement fragment | Mature framework coverage | Minimum remaining behavior / evidence |
|---|---|---|
| 偵測底盤通訊失敗 | 提供 `read()`／`write()` failure return contract | M1Driver 將 timeout/send/receive/protocol failures 分類；M1Hardware 判斷為 unhealthy |
| 偵測馬達驅動器警報 | 無 vendor alarm interpretation | 解析且檢查兩顆 M1 的 alarm/status，保留 driver identity 與 fault detail |
| 偵測無效／缺失回授 | `read()` 可回 `ERROR`，但 framework 不定義 M1 valid/fresh state | 定義 state availability、semantic validity 與不可接受條件；不得 fabricate feedback |
| 停止接受持續運動輸出 | hardware `ERROR` 後 Controller Manager 停止依賴該 hardware interfaces 的 controllers | M1Hardware fault latch／state 必須拒絕後續非零 command，直到核准的 recovery path 成功 |
| 嘗試使底盤停止 | 無通用 vendor stop command | 在仍可通訊的條件下執行 bounded best-effort M1 stop attempt，並區分「已嘗試」與「已確認停止」 |
| 回報故障 | lifecycle `~/activity` 與標準 hardware diagnostics mechanism 可承載狀態 | 發布 M1 fault category、driver identity、alarm/status、stop attempt/result；介面與欄位待後續設計 |
| 實際停止與復原經實機驗證 | framework 文件無法證明 | 對 communication loss、alarm、invalid/missing feedback 做 target-AMR fault injection 並記錄 stop/recovery outcome |

## 4. Primary-source Evidence

### 4.1 Hardware read/write error contract

- **Evidence Type:** Official exact-distribution API documentation
- **Source:** [Jazzy `hardware_interface::SystemInterface` API](https://control.ros.org/jazzy/doc/api/classhardware__interface_1_1SystemInterface.html)
- **Exact Version / Revision:** ROS 2 Jazzy documentation；`ros2_control` 4.47.0-1 per current Jazzy rosdistro metadata
- **Target Platform:** ROS 2 Jazzy / Ubuntu 24.04 Noble
- **Observed or Documented Scope:** A system hardware component implements `read()` to update hardware state and `write()` to update physical hardware from command interfaces. The methods return `return_type::OK` on success and `return_type::ERROR` on failure. Hardware lifecycle callbacks distinguish failure from critical error handled through `on_error`.
- **Limitations:** The API does not define what constitutes an M1 communication fault, alarm, invalid/missing feedback, or successful physical stop. The project hardware plugin must make those decisions.
- **Access Date:** 2026-08-13

### 4.2 Controller Manager response to hardware error

- **Evidence Type:** Official exact-distribution documentation
- **Source:** [Jazzy Controller Manager documentation](https://control.ros.org/jazzy/doc/ros2_control/controller_manager/doc/userdoc.html)
- **Exact Version / Revision:** ROS 2 Jazzy documentation；`controller_manager` release family 4.47.0-1 per current Jazzy rosdistro metadata
- **Target Platform:** ROS 2 Jazzy / Ubuntu 24.04 Noble
- **Observed or Documented Scope:** If hardware returns `return_type::ERROR` from `read()` or `write()`, Controller Manager stops all controllers using that hardware's command and state interfaces. It also publishes `~/activity` with controller and hardware lifecycle state changes using transient-local QoS.
- **Limitations:** Stopping controllers prevents continued controller output through the claimed interfaces, but does not guarantee a zero-speed frame reached an already-failed drive or that the physical base stopped. `~/activity` reports managed lifecycle state, not the M1 fault cause or stop outcome.
- **Access Date:** 2026-08-13

### 4.3 Hardware lifecycle and diagnostics extension point

- **Evidence Type:** Official exact-distribution documentation
- **Source:** [Jazzy guide for writing a hardware component](https://control.ros.org/jazzy/doc/ros2_control/hardware_interface/doc/writing_new_hardware_component.html)；linked official [hardware diagnostics example](https://control.ros.org/jazzy/doc/ros2_control_demos/example_17/doc/userdoc.html)
- **Exact Version / Revision:** ROS 2 Jazzy documentation；`ros2_control` 4.47.0-1 release family
- **Target Platform:** ROS 2 Jazzy / Ubuntu 24.04 Noble
- **Observed or Documented Scope:** A custom hardware component owns lifecycle callbacks including error handling. The official demo recommends using the hardware component's framework-managed node with `diagnostic_updater` to publish structured hardware status on `/diagnostics` without placing ROS publication work directly in the real-time loop.
- **Limitations:** The framework supplies the extension point and reporting mechanism only. It does not supply M1 alarm taxonomy, fault latch/recovery policy, stop procedure, acknowledgement logic, or diagnostic fields.
- **Access Date:** 2026-08-13

### 4.4 Exact-version limitation

Current Jazzy rosdistro release metadata lists `ros2_control` 4.47.0-1 and Ubuntu Noble as a release platform. The Jazzy documentation pages are distribution-scoped but continuously updated; they are not immutable binary snapshots. Therefore final exact-version closure still requires the target image's `dpkg`／`apt-cache policy` evidence and a runtime contract test against that installed build.

## 5. Approved Local Baseline Evidence

### 5.1 `M1Driver` design baseline

`docs/design_baseline/m1_driver.md` defines the frozen project protocol boundary:

- communication failures are categorized as `NOT_CONNECTED`, `SEND_FAILED`, `TIMEOUT`, `RECEIVE_FAILED` and protocol/semantic validation errors;
- a structurally valid transaction with `MotorState.alarm != 0` remains protocol success, leaving device-health policy to M1Hardware;
- `stop()` uses the verified FC17 JG0 path and returns simultaneous state;
- the immediate stop response may still show previous non-zero RPM, so final stop confirmation is an upper-layer policy;
- automatic reconnect, complex retries and automatic alarm reset are explicit MVP non-goals.

The baseline records hardware PASS evidence for FC17 JG0 as a callable stop path. It does not prove stop completion for every SYS-026 fault condition, especially loss of communication.

### 5.2 `M1Hardware` design baseline

`docs/design_baseline/m1_hardware.md` assigns the following project-specific responsibilities to M1Hardware:

- device-health and ros2_control `ERROR` policy;
- communication failure, `alarm != 0`, unexpected status and invalid/no latest state detection;
- no fabrication of state when valid feedback is unavailable;
- propagation from M1Driver errors to ros2_control return type/lifecycle error;
- M1 stop command plus bounded zero-RPM confirmation;
- logging operation, driver IDs, error category and latest status/alarm.

The baseline also states that exact response timeout, stop confirmation threshold/count and recovery behavior remain open. Its normal deactivation/shutdown sequence is adjacent lifecycle evidence and must not be reused to claim SYS-026 fault-path closure without a dedicated fault test.

### 5.3 Implementation and legacy reference status

`docs/implementation/SUB-001-base-control-plan.md` records a future C++ `SystemInterface` with M1 diagnostics and reports that Stage C hardware interface, Stage D controller configuration and Stage E real-hardware verification are not complete in the inspected workspace state. It also notes an older plan for alarm reset, but the newer frozen M1 baselines explicitly keep automatic alarm reset outside the MVP.

The legacy `ref/base_motor_controller` at commit `f05d8cbb43a812e39c0b038c56baee8ada699b2c` can parse and publish motor alarm details and contains an alarm-reset path. It is a behavior/protocol reference only: it is not the selected ros2_control implementation, does not prove the frozen M1Hardware error path, and must not silently reintroduce an unapproved recovery contract.

No current `src/` hardware implementation, target runtime fault-injection artifact or real-hardware SYS-026 test result was found during this research step.

## 6. Coverage and Minimum Gap

### Mature ros2_control coverage

- standard hardware `OK`／`ERROR` return boundary;
- Controller Manager stops controllers that consume failed hardware interfaces;
- hardware/controller lifecycle state visibility;
- standard mechanism for structured hardware diagnostics.

### Minimum Custom Behavior Gap

The minimum custom behavior belongs at the already-required M1Driver/M1Hardware device boundary; it does not justify a new generic fault framework:

1. Detect and classify M1 communication/protocol failure, non-zero drive alarm, and invalid/missing feedback.
2. Latch an unhealthy/fault state so continuing non-zero motion commands are rejected rather than silently retried.
3. Return ros2_control `ERROR` so Controller Manager stops dependent controllers.
4. When communication remains possible, make a bounded best-effort JG0 stop attempt; record attempted/not-attemptable and confirmed/unconfirmed outcome separately.
5. Publish structured fault detail outside the real-time loop using the standard diagnostics mechanism or a later approved project fault interface.
6. Expose no implicit automatic recovery; recovery conditions and operator/API ownership remain a later decision and require real-hardware evidence.

### Configuration Gap

- Pin `ros2_control`/Controller Manager version installed in the target image.
- Configure controller/hardware lifecycle so M1Hardware `ERROR` reaches the intended Controller Manager instance and no fallback controller reacquires the failed hardware unexpectedly.
- Define diagnostic identity, update mechanism, QoS and stale/fault retention behavior.
- Define bounded stop-attempt timing and confirmation criteria from measured M1 behavior; do not borrow SYS-027 command timeout as the device-fault threshold.

### Evidence Gap

- Unit/fake-driver evidence for every M1Driver error category, alarm, invalid/no state, fault latch, non-zero command rejection and diagnostic payload.
- Runtime evidence that `read()`/`write()` `ERROR` stops the dependent controller chain and lifecycle/activity state is observable.
- Integration evidence that JG0 is attempted only when communication permits and that attempt/result are reported independently.
- Target-AMR fault injection for cable/USB loss, timeout/invalid response, each relevant drive alarm and missing/invalid feedback.
- Measured physical motion and stop outcome for each failure class, including cases where software cannot communicate with the drive.
- Explicit recovery tests showing which faults require restart, reconfigure/reactivate or another later-approved recovery action.

## 7. Handoff to 04 Assessment

Recommended 04 conclusion:

- **Coverage Status:** `Partially Covered`.
- **Mature covered scope:** ros2_control hardware error return contract, dependent-controller stop/deactivation behavior, lifecycle visibility and standard diagnostics extension mechanism.
- **Minimum Custom Behavior Gap:** M1-specific fault detection/classification, latch and command rejection, bounded best-effort stop attempt, stop outcome tracking and detailed fault publication within the already-required hardware component.
- **Configuration/evidence gaps:** exact installed version, lifecycle composition, diagnostic contract, stop criteria and comprehensive fault-injection/real-hardware evidence.
- **Actual-stop claim:** not closed by framework documentation or the current local baseline; must remain explicitly unverified until target-AMR tests pass.
- **Recovery claim:** no automatic alarm reset/reconnect is selected; exact recovery behavior remains unverified and must not be inferred from legacy code.
- **MVP Change Candidate:** `None`.

## 8. Search Boundary

The search covered the official Jazzy ros2_control SystemInterface API, Controller Manager error behavior, official hardware-component/diagnostics guidance, the two approved M1 design baselines, the implementation plan and focused legacy M1 fault source. The generic framework already provides the error propagation seam, while the remaining behavior is inseparable from the M1 device protocol and physical stop evidence; therefore no additional generic fault-manager candidate was introduced.

## 9. Subsequent Approved Decision

The earlier option-1 decision was superseded by an approved MVP requirement simplification. SYS-026 now requires only that a hardware-interface `ERROR` causes ros2_control to stop controllers using that hardware and expose the managed error state. M1 alarm interpretation, fault latch, JG0 attempt, physical-stop confirmation, detailed fault reporting and recovery are no longer SYS-026 requirement fragments. Against this final wording, mature ros2_control capability is `Fully Covered`; target-version, composition and runtime evidence gaps remain.

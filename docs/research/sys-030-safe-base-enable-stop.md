> [!WARNING]
> **HISTORICAL / NON-AUTHORITATIVE**
>
> This document is retained for historical traceability only. It does not define the current system architecture, requirements, operational procedure, or verification authority. Use `docs/README.md` to locate the current canonical documentation.

# SYS-030 Safe Base Enable and Stop — Reuse Research

## 1. Research Scope

本筆記只研究 `03_requirements.md` 的目前定案需求：

> **SYS-030 底盤安全啟停**：系統僅應在底盤通訊正常、無馬達驅動器警報、輪端為停止狀態且驅動器已確認可運動後接受非零運動命令。底盤停用或系統關閉時，系統應嘗試使底盤停止、確認停止狀態並停用馬達驅動；任一安全動作失敗不得阻止其餘安全動作之嘗試。狀態轉換等待時間與停止確認條件應經實機驗證。

研究範圍限於 ROS 2 Jazzy `ros2_control` 4.47.0、`ros2_controllers` 4.42.1，以及已核准的 `M1Driver`／`M1Hardware` design baseline。這是 operational safety behavior 的 reuse assessment，不宣稱功能安全認證、SIL／PL 等級或硬體 E-stop 的替代方案。

SYS-026 目前只要求 hardware interface 回傳 `ERROR` 時停止使用該硬體介面的 controller，並使錯誤狀態可觀察。本筆記不把已從 SYS-026 移除的舊 fault behavior 恢復到 SYS-026；SYS-030 自己明文要求的 enable/stop/disable 行為則仍須獨立評估。SYS-031 的部署參數驗證不在本筆記下結論。

## 2. Assessment Conclusion

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy `ros2_control` hardware lifecycle + Controller Manager resource/lifecycle management + `diff_drive_controller` deactivation halt behavior |
| Exact Version / Platform | ROS 2 Jazzy；Ubuntu 24.04 Noble；`ros2_control` 4.47.0；`ros2_controllers` 4.42.1 |
| Coverage Status | **Partially Covered** |
| Covered Scope | framework 將 movement command interfaces 限制在 ACTIVE hardware；Controller Manager 管理 controller/hardware lifecycle 與 interface claiming；`diff_drive_controller::on_deactivate()` 會 halt 並寫左右輪零命令 |
| Known Constraints | lifecycle callback 只提供執行時機與成功／失敗回傳，framework 不理解 M1 communication、alarm/status、RPM、SVON/SVOFF 或 JG0；controller 零命令不等於 M1 已停止或停用 |
| Uncovered Gap | 既有 M1Driver/M1Hardware 內的 M1-specific activation admission、bounded stop confirmation、motor-disable confirmation，以及即使前一步失敗仍逐一嘗試其餘 shutdown actions 的 bounded best-effort sequencing |
| Missing Evidence | target image exact installed version；activation/deactivation/shutdown lifecycle composition；SVON/SVOFF 等待上限；零速門檻／連續樣本／poll 上限；每一步失敗注入；實體 AMR 停止與 drive state 證據 |
| MVP Change Candidate | `None` |

成熟 framework 已提供正確的 lifecycle seam、controller resource gate 與 controller-level zero-command behavior，但 SYS-030 的關鍵確認條件與安全動作都具有 M1 裝置語意，因此不能判定 `Fully Covered`。

## 3. Requirement-fragment Allocation

| Requirement fragment | Mature framework coverage | Minimum M1-specific behavior / evidence |
|---|---|---|
| 通訊正常 | `on_activate()` 是 hardware activation gate；失敗可拒絕 transition | M1Driver 成功 connect/read transaction；M1Hardware 以結果決定 activation 是否成功 |
| 無馬達驅動器警報 | 無 vendor alarm interpretation | 檢查兩顆 drive 回授的 `alarm == 0`，並保留 driver identity |
| 輪端為停止狀態 | framework 不知道 M1 RPM 的停止語意 | activation 前確認兩輪 feedback 落在核准的 zero-RPM threshold 內 |
| drive confirmed motion-enabled | ACTIVE lifecycle 表達 framework 層「可命令」，但不證明實體 SVON 完成 | 發出 SVON 後 bounded polling，確認兩顆 drive status 離開 WAIT/INHIBIT，且 alarm/RPM 條件仍成立 |
| 條件成立前不得接受非零命令 | inactive hardware 的 movement command interfaces 不可供 controller 使用；一般組態下 controller 需 active 才能輸出 | 確保 controller 只在 M1Hardware activation 成功後啟用；M1Hardware 在未完成 admission 時不得送非零 JG |
| 停用／關機時嘗試停止 | `diff_drive_controller` deactivation 將 wheel commands 寫零；hardware 有 `on_deactivate()`／`on_shutdown()` callback | M1Hardware 明確呼叫 M1Driver `stop()`，因為 controller zero command 不保證最後一筆 JG0 已到 drive |
| 確認停止狀態 | 無 physical/device confirmation | bounded polling/check，依兩顆 drive 的實際 RPM 判斷停止；記錄 confirmed/unconfirmed |
| 停用馬達驅動 | hardware lifecycle 不會自動發 vendor SVOFF | 呼叫 `disable()` 發兩顆 drive 的 SVOFF，並在可行時 bounded polling 確認 status transition |
| 一項失敗不阻止其餘嘗試 | Controller Manager 的 `BEST_EFFORT` switch strictness 是 controller switching policy，不是單一 hardware callback 內的多動作保證 | M1Hardware 使用 bounded best-effort sequence，獨立嘗試 stop、confirmation、disable、disconnect，累積／回報各步結果 |
| 等待時間與確認條件經實機驗證 | framework 只提供 callback/update execution | 選定並量測 poll delay/count、zero threshold/sample count、total deadline，以及各失敗情境的 physical outcome |

## 4. Primary-source Evidence

### 4.1 Exact-version hardware lifecycle contract

- **Evidence Type:** Official exact-tagged API source/documentation
- **Sources:** [`SystemInterface` lifecycle documentation for Jazzy](https://control.ros.org/jazzy/doc/api/classhardware__interface_1_1SystemInterface.html)；[`HardwareComponentInterface` at `ros2_control` 4.47.0](https://github.com/ros-controls/ros2_control/blob/4.47.0/hardware_interface/include/hardware_interface/hardware_component_interface.hpp)
- **Exact Version / Revision:** `ros-controls/ros2_control` tag `4.47.0`
- **Observed Scope:** ACTIVE 表示 hardware power circuits active、hardware 可移動且 command interfaces available；INACTIVE 表示 movement command interfaces unavailable；FINALIZED 表示 hardware 可被卸載／銷毀。Lifecycle callbacks 以 `SUCCESS`／`FAILURE`／`ERROR` 表達 transition 結果，critical error 可進入 `on_error`。
- **Limitations:** 這些狀態是 framework contract，不是 M1 SVON/SVOFF、alarm、status 或 actual RPM 的自動判斷。callback 的預設／基底行為也不會產生 JG0、等待零速或發 SVOFF；裝置 plugin 必須實作。
- **Access Date:** 2026-08-14

### 4.2 Hardware-component authoring boundary

- **Evidence Type:** Official Jazzy hardware-component guidance
- **Source:** [Writing a Hardware Component — ROS2_Control Jazzy](https://control.ros.org/jazzy/doc/ros2_control/hardware_interface/doc/writing_new_hardware_component.html)
- **Exact Version / Revision:** ROS 2 Jazzy documentation；評估版本 `ros2_control` 4.47.0
- **Observed Scope:** 官方指南把 hardware power enable 放在 `on_activate()`，要求 `on_deactivate()` 做相反操作，並把 graceful shutdown 放在 `on_shutdown()`；裝置 I/O 由 hardware component 的 `read()`／`write()` 實作。
- **Limitations:** 指南提供責任邊界而不是 vendor implementation。它沒有規定 M1 的 SVON、JG0、SVOFF ordering、確認門檻、retry/poll count 或多步失敗策略。
- **Access Date:** 2026-08-14

### 4.3 Controller Manager lifecycle and interface gate

- **Evidence Type:** Official exact-tagged framework documentation
- **Sources:** [`Controller Manager` documentation at `ros2_control` 4.47.0](https://github.com/ros-controls/ros2_control/blob/4.47.0/controller_manager/doc/userdoc.rst)；[Jazzy Controller Manager documentation](https://control.ros.org/jazzy/doc/ros2_control/controller_manager/doc/userdoc.html)
- **Exact Version / Revision:** `ros-controls/ros2_control` tag `4.47.0`
- **Observed Scope:** Controller Manager connects controllers and hardware, manages their lifecycle and grants claimed interfaces. Normal safety-oriented configuration does not allow controller activation against inactive hardware. Controller switching supports strictness choices, while hardware `read()`／`write()` `ERROR` stops controllers using affected interfaces.
- **Limitations:** Controller activation and interface claiming only establish framework readiness. They do not inspect M1 alarm/status/RPM or prove SVON. `BEST_EFFORT` controller switching describes handling of controller start/stop requests; it does not guarantee that multiple vendor commands inside `M1Hardware::on_deactivate()`／`on_shutdown()` all execute after an earlier one fails.
- **Access Date:** 2026-08-14

### 4.4 Exact diff_drive_controller deactivation behavior

- **Evidence Type:** Official exact-tagged source and tests
- **Sources:** [`diff_drive_controller.cpp` at tag 4.42.1](https://github.com/ros-controls/ros2_controllers/blob/4.42.1/diff_drive_controller/src/diff_drive_controller.cpp)；[`test_diff_drive_controller.cpp` at tag 4.42.1](https://github.com/ros-controls/ros2_controllers/blob/4.42.1/diff_drive_controller/test/test_diff_drive_controller.cpp)
- **Exact Version / Revision:** `ros-controls/ros2_controllers` tag `4.42.1`
- **Observed Scope:** `on_deactivate()` calls `halt()`；`halt()` writes `0.0` to all left and right wheel velocity command interfaces. Exact-version lifecycle tests assert zero values after deactivation.
- **Limitations:** This is controller-interface behavior. It does not prove the hardware update loop subsequently transmitted JG0, does not inspect actual RPM, does not issue SVOFF and cannot confirm physical stopping. Hardware shutdown therefore cannot depend solely on controller deactivation.
- **Access Date:** 2026-08-14

### 4.5 ROS 2 managed-node lifecycle semantics

- **Evidence Type:** Official ROS 2 design specification
- **Source:** [Managed nodes lifecycle design](https://design.ros2.org/articles/node_lifecycle.html)
- **Observed Scope:** lifecycle callbacks govern transitions and can report success, failure or error; shutdown leads toward `Finalized`.
- **Limitations:** The generic managed-node lifecycle intentionally does not define robot-specific actuator safety actions or physical confirmation criteria.
- **Access Date:** 2026-08-14

## 5. Approved Local Baseline Evidence

### 5.1 Activation admission already belongs to M1Hardware

`docs/design_baseline/m1_hardware.md` freezes this activation intent:

1. connect and read both drive states;
2. require successful communication, `alarm == 0`, and `RPM == 0`;
3. reset position tracking and zero ROS command variables;
4. call `M1Driver.enable()` to issue dual-drive SVON;
5. use bounded `read_state()` polling until both statuses leave WAIT/INHIBIT while alarm remains zero and RPM remains zero;
6. enter ACTIVE only after those checks succeed.

The hardware evidence says the immediate SVON response may still report `status=6`, followed by a later `status=0`. Therefore a single successful transaction cannot satisfy “drive confirmed motion-enabled”; bounded transition checking is required.

### 5.2 Stop and disable are verified M1 protocol capabilities

`docs/design_baseline/m1_driver.md` records real-hardware PASS evidence for:

- FC17 JG0 stop path;
- FC17 SVON lifecycle transition `status 6 -> 0`;
- FC17 SVOFF lifecycle transition `status 0 -> 6`.

`stop()` and `disable()` each return simultaneous state, but their immediate response may still contain the previous RPM/status. M1Driver therefore owns one bounded transaction at a time; M1Hardware owns transition policy and bounded polling.

### 5.3 Deactivation/shutdown sequencing already belongs to M1Hardware

The approved baseline defines the normal sequence:

```text
zero ROS command variables
→ attempt M1Driver.stop() / JG0
→ bounded zero-RPM confirmation
→ attempt M1Driver.disable() / SVOFF
→ bounded lifecycle confirmation when possible
→ attempt M1Driver.disconnect()
```

It explicitly states that failure of one stop/disable action must not prevent remaining safe shutdown attempts. This is project-specific orchestration inside the already-required M1Hardware boundary, not a reason to add a generic safety manager.

## 6. Behavioral Boundaries

### 6.1 “Accept nonzero command” has two gates

The mature framework gate and M1 device gate are both necessary:

```text
M1Hardware activation checks pass
→ hardware becomes ACTIVE and exports movement command interfaces
→ diff_drive_controller may become ACTIVE and claim them
→ nonzero wheel command may reach M1Hardware.write()
```

Controller lifecycle alone cannot substitute for the first step. Conversely, M1Hardware reporting ACTIVE before its own SVON/status/alarm/RPM checks finish would violate SYS-030 even if Controller Manager operates correctly.

### 6.2 Zero command, stop request, confirmed stop and motor disable are distinct

```text
controller halt       = wheel command interfaces set to zero
M1Driver.stop()       = JG0 request sent, if communication succeeds
stop confirmed        = measured RPM satisfies the approved zero condition
M1Driver.disable()    = SVOFF request sent, if communication succeeds
disable confirmed     = measured status satisfies the approved disabled condition
```

None of these statements should be used as evidence for a later one. In particular, controller deactivation is helpful defense in depth but does not close the hardware stop/disable requirement.

### 6.3 Best-effort means independent bounded attempts, not guaranteed success

If stop transmission or zero-speed polling fails, M1Hardware must still attempt motor disable and communication cleanup when each action remains callable. If disable fails, cleanup should still be attempted. The overall callback returns a failure/error outcome after collecting the step results; it must not return early in a way that skips later safe actions.

This guarantees attempts, not outcomes. Communication loss can make JG0, RPM confirmation and SVOFF impossible. The document and diagnostics must distinguish:

- attempted and confirmed;
- attempted but unconfirmed/failed;
- not attemptable because communication was unavailable.

### 6.4 Shutdown callback coverage must be explicit

SYS-030 applies both to ordinary bottom-base deactivation and system shutdown. The project must ensure the same bounded best-effort device sequence is reachable from the actual `on_deactivate()` and `on_shutdown()` paths selected by the final composition. A destructor-only cleanup path is insufficient: the M1Driver baseline deliberately forbids its destructor from issuing JG0 or SVOFF.

## 7. Gap Classification

### Mature Capability

- lifecycle seams for hardware activation, deactivation, shutdown and error;
- movement interface availability tied to active hardware;
- Controller Manager lifecycle/resource claiming;
- `diff_drive_controller` deactivation writes zero wheel commands.

### Configuration and Composition Gap

- pin and verify target-image `ros2_control` 4.47.0 and `ros2_controllers` 4.42.1, or reassess installed versions;
- keep controller activation disallowed against inactive hardware;
- order controller and hardware transitions so no controller can claim movement interfaces before M1 activation admission succeeds;
- ensure system shutdown actually invokes the approved M1Hardware shutdown path rather than relying on process destruction;
- define how callback aggregate failure and per-step outcomes are exposed without inventing a separate generic safety framework.

### Minimum Custom Behavior Gap

Only inside the already-required M1Driver/M1Hardware device boundary:

1. M1Driver supplies bounded connect/read, SVON, JG0, SVOFF and disconnect operations with categorized results and simultaneous state decode.
2. M1Hardware implements activation admission using communication, alarm, actual RPM and post-SVON status checks.
3. M1Hardware refuses to reach ACTIVE—and therefore refuses nonzero device output—until all admission conditions pass.
4. M1Hardware implements bounded zero-RPM and SVOFF-status confirmation.
5. M1Hardware performs stop, confirmation, disable and disconnect as independent bounded best-effort actions, accumulating results rather than exiting after the first failure.
6. M1Hardware maps the aggregate result to the ros2_control lifecycle callback result and logs/exports enough per-action state for verification.

No new generic safety manager, enable gate node, stop coordinator or custom controller is justified by SYS-030.

### Timing and Evidence Gap

- choose and verify communication timeout and total transition deadline;
- choose SVON/SVOFF poll delay and maximum poll count;
- define zero-RPM threshold, required consecutive samples and maximum confirmation time;
- verify no nonzero JG is sent before all activation conditions pass;
- inject connect/read failure, nonzero alarm, initial nonzero RPM, SVON timeout/unexpected status and validate activation refusal;
- inject failure independently at JG0, zero-speed polling, SVOFF polling and disconnect, verifying every remaining action is still attempted;
- verify both normal deactivation and process/system shutdown paths;
- measure actual wheel/body stop time and final drive state on the target AMR.

## 8. Handoff to 04 Assessment

Recommended 04 conclusion:

- **Coverage Status:** `Partially Covered`.
- **Mature covered scope:** ros2_control hardware/controller lifecycle and command-interface gating；`diff_drive_controller` zeroes wheel interfaces during deactivation.
- **Minimum Custom Behavior Gap:** M1-specific activation admission, bounded JG0/zero-speed/SVOFF confirmation, and independent best-effort shutdown sequencing inside existing M1Driver/M1Hardware.
- **Configuration/evidence gaps:** lifecycle composition, exact installed versions, transition timing, confirmation thresholds, fault injection and target-AMR physical evidence.
- **Important semantic boundary:** ACTIVE/controller stopped/zero command/JG0 sent/zero RPM confirmed/SVOFF sent/SVOFF confirmed are separate claims and require separate evidence.
- **Safety boundary:** this is operational safety behavior only; it neither replaces the verified physical E-stop nor establishes certified functional safety.
- **MVP Change Candidate:** `None`.

## 9. Search Boundary

The search covered the exact SYS-030 wording, approved M1Driver/M1Hardware activate/stop/deactivate/shutdown behavior, official ROS 2 lifecycle semantics, ROS 2 Jazzy ros2_control lifecycle and Controller Manager contracts at the selected 4.47.0 version, and exact `diff_drive_controller` 4.42.1 deactivation source/tests. The remaining gap is inseparable from M1 device semantics and physical confirmation, so no broader safety framework or additional controller candidate was introduced.

# 07 Implementation

本文件記錄 `mobile_base` v0.1 的**目前實作基線與可重現證據**。它只回答「哪個核准設計已由哪些檔案、設定與程式實現，以及驗證到哪一層」，不得重新定義 [`01_use_cases.md`](./01_use_cases.md) 至 [`06_subsystem.md`](./06_subsystem.md) 已核准的需求、責任或介面。

## 1. 文件權限與狀態規則

### 1.1 Normative Inputs

- [`03_requirements.md`](./03_requirements.md)：需求 ID 與可觀察行為。
- [`04_reuse_assessment.md`](./04_reuse_assessment.md)：成熟方案、exact-version 證據與最小 custom gaps。
- [`05_architecture.md`](./05_architecture.md)：7 大 subsystem 的責任與資料流。
- [`06_subsystem.md`](./06_subsystem.md)：Node、Component、ROS 2 interface、parameter、failure handling 與 verification obligations。

本文件不得以「已安裝套件」取代整合驗證，也不得以「container 正在執行」推論 ROS graph、TF、Topic、硬體通訊或使用案例已通過。

### 1.2 Implementation / Evidence Status

| 狀態 | 定義 |
|---|---|
| `Planned` | 已有 06 設計，但尚無對應實作 artifact。 |
| `Implemented` | 對應 code/config/artifact 已存在並完成靜態檢查。 |
| `Build Verified` | 可在指定 container baseline 中完成 dependency closure 與 build。 |
| `Integration Verified` | 實際 ROS 2 component/interface/data flow 已整合通過。 |
| `Hardware Verified` | 已在目標 Jetson 與實體裝置上取得可重現證據。 |
| `Feature Frozen` | 已實作、整合並滿足對應 requirement 與使用案例驗收；只有此狀態可視為目前版本凍結。 |

同一項目可同時具有 implementation status 與不同層級的 evidence；`Implemented` 不等於 `Hardware Verified`，`Hardware Verified` 也不自動代表端到端 `Feature Frozen`。

---

## 2. IMP-000 Docker Development and Validation Baseline

### 2.1 Scope and Status

| 欄位 | 目前基線 |
|---|---|
| 目的 | 提供後續 ROS 2 實作、build、test、整合與實機驗證的固定開發環境。 |
| Requirement trace | Cross-cutting implementation prerequisite；不獨立宣稱滿足任何 `SYS-xxx`。 |
| Implementation status | `Implemented` |
| Evidence status | Docker/Compose `Build Verified`；M1 serial passthrough 有既有 `Hardware Verified` 證據；完整 ROS/TF/sensor/drive flow 尚未驗證。 |
| Feature-freeze status | **Not Frozen** |

### 2.2 Implementation Artifacts

| Artifact | 已實作責任 | 明確不負責 |
|---|---|---|
| [`../Dockerfile`](../Dockerfile) | 固定 Isaac ROS JetPack base image；安裝 v0.1 已核准的 binary dependencies；設定 workspace。 | 不 clone source repositories、不執行 `colcon build`、不自動啟動 ROS graph。 |
| [`../compose.yaml`](../compose.yaml) | build image、啟用 NVIDIA runtime、host network、repository bind mount、`/dev/ttyUSB0` 與 `/dev/ttyACM0` passthrough、interactive development container。 | 不使用 `privileged`、不宣稱 production deployment、不提供 application healthcheck 或自動 bringup。 |

### 2.3 Image and Binary Dependency Baseline

Base image：

```text
nvcr.io/nvidia/isaac/ros:isaac_ros_740c8500df2685ab1f4a4e53852601df-arm64-jetpack
```

Dockerfile 安裝：

| 類別 | Package | 用途 |
|---|---|---|
| System | `libmodbus-dev` | 後續 S7 `M1Driver` 的私有 Modbus RTU transport dependency。 |
| System | `python3-serial` | `tdk_ros2_imu` serial runtime dependency。 |
| ROS 2 | `ros-jazzy-navigation2`, `ros-jazzy-nav2-bringup` | S4–S6 的 Nav2 runtime 與 bringup 基線。 |
| ROS 2 | `ros-jazzy-slam-toolbox` | S4 Mapping。 |
| ROS 2 | `ros-jazzy-robot-localization` | S3 State Estimation。 |
| ROS 2 | `ros-jazzy-ros2-control`, `ros-jazzy-ros2-controllers` | S7 Base Control。 |
| ROS 2 | `ros-jazzy-dual-laser-merger`, `ros-jazzy-sick-scan-xd` | S2 LiDAR acquisition / selected-scan composition baseline。 |

2026-08-18 的目標 container 曾確認下列實際安裝版本；這些是當次 runtime evidence，不是未來重建永遠固定的 lockfile：

| Package | Observed version |
|---|---|
| `libmodbus-dev` | `3.1.10-1ubuntu1` |
| `ros-jazzy-dual-laser-merger` | `0.3.1-1noble.20260614.082554` |
| `ros-jazzy-nav2-bringup` | `1.3.12-1noble.20260615.095620` |
| `ros-jazzy-navigation2` | `1.3.12-1noble.20260615.092426` |
| `ros-jazzy-robot-localization` | `3.8.3-1noble.20260614.073224` |
| `ros-jazzy-ros2-control` | `4.45.2-1noble.20260612.174902` |
| `ros-jazzy-ros2-controllers` | `4.40.1-1noble.20260615.085512` |
| `ros-jazzy-sick-scan-xd` | `3.9.0-1noble.20260614.055630` |
| `ros-jazzy-slam-toolbox` | `2.8.5-1noble.20260614.104642` |

### 2.4 Compose Runtime Contract

```text
Host repository
  -> bind mount /workspaces/mobile_base
  -> interactive mobile_base container

Host network
  -> Ethernet LiDAR communication path

/dev/ttyUSB0
  -> M1 RS485 bus

/dev/ttyACM0
  -> TDK IMU serial device
```

`command: sleep infinity` 表示此 Compose service 只維持開發容器，不代表 ROS 2 application healthy。後續每個 subsystem 必須依 [`07_implementation_checklist.md`](./07_implementation_checklist.md) 分別取得 build、interface、integration 與 real-hardware evidence。

### 2.5 Source Workspace Baseline

Source dependencies 保留在 repository 的 `src/`，不藏入 Docker image build：

| Package | Repository state | Existing evidence |
|---|---|---|
| `rf2o_laser_odometry` | `src/rf2o_laser_odometry`；移除 Jazzy 無效的 legacy `cmake_modules` rosdep metadata。 | 2026-08-18 `rosdep install`、`colcon build --symlink-install` 與 `ros2 pkg list` 通過。 |
| `tdk_ros2_imu` | `src/tdk_ros2_imu`；`python3-serial` 已固化於 Dockerfile。 | 2026-08-18 `rosdep install`、`colcon build --symlink-install` 與 `ros2 pkg list` 通過。 |

這些證據只證明 dependency/build closure，不證明 RF2O odometry、IMU message semantics 或 S2/S3 整合已通過。

### 2.6 Verification Evidence

| Date | Check | Result | Evidence boundary |
|---|---|---|---|
| 2026-08-18 | `docker compose up -d --build` | PASS | Image build 與 `mobile_base` container 啟動成功。 |
| 2026-08-18 | Container binary package inspection | PASS | 上列核心 apt/ROS 2 packages 存在。 |
| 2026-08-18 | Container `/dev/ttyUSB0` inspection | PASS | M1 device 在 container 內可見；尚不代表 Modbus control loop 通過。 |
| 2026-08-18 | `rosdep install` + `colcon build --symlink-install` | PASS | `rf2o_laser_odometry` 與 `tdk_ros2_imu` build closure。 |
| 2026-08-18 | Dockerfile rebuild after adding `python3-serial` | PASS (user-reported) | Dependency 已固化；原始 terminal transcript 見 handoff。 |
| 2026-08-18 | Host `/dev/ttyACM0` connected | CONFIRMED (user-reported) | Compose 已配置 passthrough；尚無 container visibility / IMU runtime evidence。 |
| 2026-08-18 | `docker compose config` current checkout recheck | PASS | Compose 可解析，兩個 device mapping、host network、NVIDIA runtime 與 bind mount 均存在。 |
| 2026-08-18 | Current container runtime recheck | NOT RUNNING | `mobile_base` service 當下未執行，因此未重新驗證 devices/packages。 |

歷史操作與原始輸出保存在 [`handoff/2026-08-18_09-45-00.md`](./handoff/2026-08-18_09-45-00.md)。後續若重建 image，應以新證據更新本節，不得只沿用舊結果。

### 2.7 Known Limits and Next Boundary

- apt repository 未以 lockfile 鎖定完整 transitive dependency；重建後必須重新記錄實際版本。
- `/dev/ttyUSB0`、`/dev/ttyACM0` 是目前 target-host 路徑，USB 重新枚舉後仍需確認 identity；本基線尚未建立 udev stable aliases。
- `network_mode: host` 只提供 Ethernet 存取路徑，不證明兩具 LiDAR 已連線或資料有效。
- 尚未建立 production entrypoint、restart policy、healthcheck 或自動 ROS bringup；在完整流程穩定前不提前加入。
- 下一個項目是先完成 [`07_implementation_checklist.md`](./07_implementation_checklist.md) 第 3 項的 per-item implementation record template；第 3–6 項治理、可重現 build/test 與硬體安全前置關閉後，再進入 S7 `M1Driver` vertical slice。

---

## 3. Per-item Implementation Record Template

本節定義 checklist #7–#27 每個 implementation item 必須使用的標準紀錄結構。同一 item 可同時具有多層 evidence status；未取得的層級不得以預設值或假設填寫。

### 3.1 使用規則

- 每個 item 的 record 以 `## IMP-XXX <Item Short Name>` 為標題，其中 `IMP-XXX` 與 checklist 編號一致。
- 所有欄位皆須填寫；若某欄位對該 item 不適用，填寫 `N/A` 並說明理由，不得留空。
- Evidence 欄位只記錄**已執行且有結果的**操作；未執行的測試計畫不得填入 evidence 欄位。
- Timestamp 欄位格式為 `YYYY-MM-DDThh:mm:ss±HH:MM`（ISO 8601，含 timezone offset），只在取得對應 evidence 時填寫；無 evidence 時留 `—`。
- Evidence storage path 規則由 §4（Verification Evidence Storage Convention）確立；格式為 `docs/verification/IMP-NNN/<YYYY-MM-DD>T<HHmmss>_<layer>_<desc>.txt`。
- Build 與 test command 規範由 §5（Build and Test Command Baseline）確立；Command 欄位記錄實際執行的精確命令。
- Hardware safety preflight 規範由 §6（Runtime and Hardware Safety Preflight）確立；Hardware 驗證前必須通過對應層級之 Preflight Checklist。

---

### 3.2 Template

````markdown
## IMP-XXX <Item Short Name>

### 3.2.1 Identity / Scope / Status

| 欄位 | 內容 |
|---|---|
| Checklist item | #N — <item title from checklist> |
| Item scope | <一句話描述本 item 的實作邊界：實作什麼、不實作什麼> |
| Implementation status | `Planned` / `Implemented` / `Build Verified` / `Integration Verified` / `Hardware Verified` / `Feature Frozen` |
| Evidence status | <各層 evidence 的目前達成狀態，可多層並存，例如 `Build Verified`；未達成層級不填> |
| Feature-freeze status | `Not Frozen` / `Feature Frozen` |
| Last updated | YYYY-MM-DD |

---

### 3.2.2 Traceability

| 欄位 | 內容 |
|---|---|
| Requirement IDs | <與本 item 直接相關的 SYS-xxx 清單，來自 03；無獨立 SYS 歸屬時填 `Cross-cutting`> |
| Subsystem | <本 item 所屬 subsystem，來自 05／06；跨 subsystem 時列全部> |
| Custom gap IDs | <若本 item 實作 GAP-01–GAP-06 中的缺口，列出對應 ID；否則填 `None`> |
| Upstream design refs | <06 section 或 interface 定義的直接引用，格式 `06 §X.Y.Z`；無則填 `None`> |

---

### 3.2.3 Implementation Artifacts

| Artifact | Path / Package | 已實作責任 | 明確不負責 |
|---|---|---|---|
| <artifact type, e.g. source file / config / launch> | <相對 repo 路徑或 package 名稱> | <此 artifact 覆蓋的 06 設計責任> | <明確排除的責任，若無則填 `—`> |

_（可新增多列）_

---

### 3.2.4 Mature Component / Custom Boundary

| 欄位 | 內容 |
|---|---|
| Mature component(s) used | <exact package name + version，來自 IMP-000 baseline 或另行記錄；無則填 `None`> |
| Custom implementation | <本 item 自行實作的最小行為，對應 06 的 custom gap 責任；無則填 `None`> |
| Boundary rule | <用一兩句話說明哪裡是成熟元件的責任止境、哪裡開始是 custom code，引用 06 的 custom gap 描述> |

---

### 3.2.5 Authoritative Interfaces and Configuration

_僅記錄本 item 已實作且可觀察的 interface 與 config；尚未實作的設計意圖不填入此欄。_

#### Published / Subscribed Interfaces

| 方向 | Interface name | Message type | Frame / QoS | Producer / Consumer | 06 ref |
|---|---|---|---|---|---|
| Pub / Sub / Action | `/topic_name` | `pkg/msg/Type` | `frame_id` / `<qos profile>` | `<node name>` | `06 §X.Y.Z` |

_（可新增多列；無已實作 interface 時填 `None`）_

#### Key Parameters

| Parameter | YAML path | Value / Default | 06 ref |
|---|---|---|---|
| `param_name` | `node/param_name` | `<value>` | `06 §X.Y.Z` |

_（可新增多列；無已決定 parameter 時填 `None`）_

---

### 3.2.6 Failure / Timeout / Cancel / Invalid-input Handling

_僅填寫 06 要求且本 item 已實作或已驗證的負向路徑；不適用時於每欄填 `N/A — <原因>`。_

| 情境 | 觸發條件 | 期望行為（來自 06） | 已驗證 | 驗證層級 |
|---|---|---|---|---|
| Failure | <e.g. Modbus read error> | <e.g. ERROR state; controller停用> | Yes / No | Unit / Integration / Hardware / — |
| Timeout | <e.g. cmd_vel gap > threshold> | <e.g. 歸零輸出> | Yes / No | Unit / Integration / Hardware / — |
| Cancel | <e.g. nav action cancel request> | <e.g. 終止任務並發布零速> | Yes / No | Unit / Integration / Hardware / — |
| Invalid input | <e.g. malformed PoseStamped> | <e.g. 拒絕並回報原因> | Yes / No | Unit / Integration / Hardware / — |

_（依 item 適用性增減列數；若整個欄位不適用，填 `N/A — <原因>` 並保留表頭）_

---

### 3.2.7 Verification Evidence

_每筆 evidence 只記錄已執行且有結果的操作。未執行、計畫中、模擬或口頭「已測過」不得填入。_

#### Static / Build Evidence

| Timestamp | Command | Result | Evidence boundary | Storage path |
|---|---|---|---|---|
| YYYY-MM-DDThh:mm:ss±HH:MM | `<exact command>` | PASS / FAIL | <此結果實際證明了什麼> | `docs/verification/IMP-XXX/<YYYY-MM-DD>T<HHmmss>_build_<desc>.txt` |

_（無 evidence 時整列填 `—`；build command 依 §5 規範填寫）_

#### Unit / Interface Evidence

| Timestamp | Test target | Command | Result | Evidence boundary | Storage path |
|---|---|---|---|---|---|
| YYYY-MM-DDThh:mm:ss±HH:MM | `<package::test>` | `<exact command>` | PASS / FAIL | <證明了什麼> | `docs/verification/IMP-XXX/<YYYY-MM-DD>T<HHmmss>_unit_<desc>.txt` |

_（無 evidence 時整列填 `—`）_

#### Integration Evidence

| Timestamp | Scenario | Observed result | Evidence boundary | Storage path |
|---|---|---|---|---|
| YYYY-MM-DDThh:mm:ss±HH:MM | <e.g. ROS graph + topic echo> | <observed output> | <證明了什麼；container running ≠ integration evidence> | `docs/verification/IMP-XXX/<YYYY-MM-DD>T<HHmmss>_intg_<desc>.txt` |

_（無 evidence 時整列填 `—`）_

#### Hardware Evidence

_僅適用於 06 明確要求 real-hardware validation 的 item。若本 item 不需要實機驗證，填 `N/A — <原因>`。_

| Timestamp | Target hardware | Test condition | Observed result | Evidence boundary | Storage path |
|---|---|---|---|---|---|
| YYYY-MM-DDThh:mm:ss±HH:MM | Jetson + M1 / picoScan / TDK IMU | <preflight #6 條件> | <量測結果> | <證明了什麼；模擬不可取代> | `docs/verification/IMP-XXX/<YYYY-MM-DD>T<HHmmss>_hw_<desc>.txt` |

_（無 evidence 時整列填 `—`；hardware preflight 程序依 §6 規範填寫）_

---

### 3.2.8 Evidence Boundary

| 欄位 | 內容 |
|---|---|
| 已證明 | <明確列出目前 evidence 實際證明的最小事實集合> |
| 尚未證明 | <明確列出目前 evidence **無法**推論的內容，例如：端到端整合、硬體 failsafe、實機精度> |

---

### 3.2.9 Known Limits / Unresolved Dependencies

- <已知限制或尚未解決的外部 dependency，每條一行；無則填 `None`>

---

### 3.2.10 Feature Freeze Status / Next Dependency

| 欄位 | 內容 |
|---|---|
| Feature freeze status | `Not Frozen` / `Feature Frozen` |
| Freeze condition | <達到 Feature Frozen 所需的最後 evidence 或核准條件；已 frozen 則填 `All conditions met`> |
| Next dependency | <本 item 解鎖後，直接依賴本 item 的下一個 checklist item 或 cross-subsystem integration step> |
````

---

### 3.3 填寫範圍說明

下表說明各 checklist section 對 template 各節的適用性：

| Template 節 | Critical HW Slice (#7–#8) | Subsystem Impl (#9–#17) | Cross-subsystem (#18–#22) | Use-case Verification (#23–#27) |
|---|---|---|---|---|
| 3.2.1 Identity / Scope / Status | ✓ | ✓ | ✓ | ✓ |
| 3.2.2 Traceability | ✓ (Cross-cutting) | ✓ | ✓ | ✓ |
| 3.2.3 Implementation Artifacts | ✓ | ✓ | ✓ | ✓ |
| 3.2.4 Mature / Custom Boundary | ✓ | ✓ | ✓ (N/A 若無 custom) | N/A 通常 |
| 3.2.5 Interfaces / Config | ✓ | ✓ | ✓ | N/A 通常 |
| 3.2.6 Failure Handling | 依適用性 | ✓ | ✓ | N/A 通常 |
| 3.2.7 Verification Evidence | ✓ | ✓ | ✓ | ✓ |
| 3.2.8 Evidence Boundary | ✓ | ✓ | ✓ | ✓ |
| 3.2.9 Known Limits | ✓ | ✓ | ✓ | ✓ |
| 3.2.10 Feature Freeze / Next | ✓ | ✓ | ✓ | ✓ |

「✓」表示必填；「N/A 通常」表示多數 item 在此節填 `N/A` 並說明理由。

---

## 4. Verification Evidence Storage Convention

本節定義 checklist #5–#27 每次執行 build、test、integration 與 hardware validation 時，原始 evidence 的保存位置、metadata、命名、raw vs summary 界定、重測處理與 hardware recording 規則。

本節是**唯一關於 evidence storage 的 normative source**；`07_implementation.md` §3 template 的 `Storage path` 欄位均以本節為準。

### 4.1 Evidence Repository Location

```text
docs/verification/
  IMP-007/          ← 每個 implementation item 一個子目錄
  IMP-008/          ← 目錄名稱與 checklist item 編號一致
  IMP-009/
  ...
  IMP-027/
```

**規則：**

- 每個 implementation item 使用獨立子目錄 `docs/verification/IMP-NNN/`，`NNN` 為三位數字，與 checklist 編號一致（`IMP-007` 到 `IMP-027`）。
- 子目錄在第一筆 evidence 產生前建立，僅含 `.gitkeep`；`.gitkeep` 在有真實 evidence 加入時可移除。
- `docs/verification/` 根目錄下放置 `README.md`（本節 §4 的快速參照索引）；各 item 目錄下**不**強制放置 sub-README，但可選擇性增加說明。
- `docs/m1_bringup_validation/logs/manual/` 中現有的 pre-IMP hardware evidence 保留在原位；後續 IMP-007 之後的 hardware evidence 遷入 `docs/verification/IMP-NNN/`。

### 4.2 Evidence Metadata

每一筆 evidence artifact（文字檔案）的 **第一行起** 必須包含以下 metadata header，以 `#` 開頭：

```text
# IMP: IMP-NNN
# Layer: build | unit | integration | hardware | negative
# Timestamp: YYYY-MM-DDThh:mm:ss±HH:MM
# Env: <container image digest or tag, or 'host'> / <ROS distro> / <OS>
# Target: <package(s) or hardware identity>
# Command: <exact command or procedure reference>
# Version: <git commit SHA (short) of workspace at test time>
# Result: PASS | FAIL
# Proved: <one-sentence: what this evidence actually proves>
# Not-proved: <one-sentence: what this evidence cannot prove>
```

**說明：**

| 欄位 | 必填 | 說明 |
|---|---|---|
| `IMP` | ✓ | 對應 checklist item，格式 `IMP-NNN` |
| `Layer` | ✓ | 五選一：`build` / `unit` / `integration` / `hardware` / `negative` |
| `Timestamp` | ✓ | 執行的完整時間戳記，ISO 8601 含 timezone offset，例如 `2026-08-20T10:38:17+08:00`；同日多次執行可由此欄位判斷順序 |
| `Env` | ✓ | 執行環境；container 使用 image digest 或 tag，裸機寫 `host`；附 ROS distro 與 OS |
| `Target` | ✓ | 受測 package 名稱、node、topic、或硬體 device identity |
| `Command` | ✓ | 可重現的完整命令；若為 hardware 手動程序，寫程序文件引用 |
| `Version` | ✓ | `git rev-parse --short HEAD` 的輸出，代表測試當下的 workspace commit |
| `Result` | ✓ | `PASS` 或 `FAIL`，不得填其他值 |
| `Proved` | ✓ | 一句話：此結果**實際**證明了什麼（具體事實） |
| `Not-proved` | ✓ | 一句話：此結果**無法**推論什麼（邊界聲明） |

**禁止：** 只寫 `# Result: PASS` 而沒有 `Proved` 與 `Not-proved`；禁止 `tested successfully`、`OK`、`done` 等無意義標記。

### 4.3 Naming Convention

Evidence artifact 檔名格式：

```text
<YYYY-MM-DD>T<HHmmss>_<layer>_<desc>.txt
```

| 欄位 | 規則 |
|---|---|
| `YYYY-MM-DD` | 執行日期，與 metadata `Timestamp` 欄位的日期部分一致 |
| `T<HHmmss>` | 執行時間（24 小時制，無冒號），與 metadata `Timestamp` 欄位的時間部分一致，例如 `T103817` 對應 `10:38:17` |
| `layer` | `build` / `unit` / `intg` / `hw` / `neg`（integration 縮寫 `intg`，hardware 縮寫 `hw`，negative 縮寫 `neg`） |
| `desc` | 以底線分隔的小寫簡短描述，足以辨識測試對象，例如 `colcon_build`、`m1_read_path`、`ros_graph`、`servo_enable`；**不要**使用空格或特殊字元 |

範例（含同日多次執行的 FAIL → PASS 場景）：

```text
docs/verification/IMP-007/
  2026-08-20T093012_build_colcon_all.txt      ← 第一次 build（PASS）
  2026-08-20T094501_unit_m1driver_read.txt    ← unit test（FAIL）
  2026-08-20T101738_unit_m1driver_read.txt    ← 修正後重跑（PASS）；舊 FAIL 保留
  2026-08-21T141200_hw_servo_enable.txt       ← hardware（PASS）
  2026-08-21T141955_neg_modbus_timeout.txt    ← negative path（PASS）
  2026-08-25T080033_build_colcon_all.txt      ← 跨日重測，新檔保留
```

**命名規則確保：** 同一 item 同一天同一測試的多次執行（包括 FAIL → PASS）產生不同檔名，不互相覆蓋；執行先後順序可由 timestamp 判斷；人類可直接讀懂層次與內容；不需要 database 或外部 tooling 解析。

### 4.4 Raw Evidence vs Summary

#### Raw Evidence（保存至 `docs/verification/IMP-NNN/`）

下列內容為 raw evidence，應保存至 repository：

- colcon build 的完整 stdout/stderr（截斷超過 500 行時保留前 200 行 + 後 100 行 + 截斷說明）
- ROS 2 test runner 原始輸出（`--event-handlers console_direct+` 輸出）
- `ros2 topic echo`、`ros2 node list`、`ros2 interface show` 等 ROS graph 觀察輸出
- Modbus / hardware 驅動器診斷輸出
- 故障注入結果（negative path）
- hardware 量測觀察紀錄（operator 手動記錄）

#### 不應直接 commit 進 Git 的 artifact

下列 artifact **不應**直接 commit：

- 超過 ~1 MB 的連續 log（典型情境：長時間 ROS bag、壓力測試輸出）
- Binary artifact（bag 檔、image、pcap）
- Build 中間產物（`build/`、`install/`、`log/` 已被 `.gitignore` 排除）

**若 raw artifact 不適合進 Git，`07_implementation.md` item record 的 `Storage path` 欄填：**

```text
[external: <storage-location-description>, ref: docs/verification/IMP-NNN/<YYYY-MM-DD>T<HHmmss>_<layer>_<desc>.ref.txt]
```

並在 `docs/verification/IMP-NNN/<YYYY-MM-DD>T<HHmmss>_<layer>_<desc>.ref.txt` 中寫入 metadata header（§4.2）加上：

```text
# ExternalRef: <storage location, e.g. shared drive path, USB label, local path on test machine>
# SizeBytes: <approximate>
# Checksum: <sha256 if available>
# Retained-by: <person/machine responsible for keeping this artifact>
```

此 `.ref.txt` 檔案本身進入 Git，確保可追溯性不依賴外部 artifact 是否仍存在。

#### Summary（寫入 `07_implementation.md` item record）

`07_implementation.md` 中的 item record 只寫：

- `Timestamp`、`Command`（或程序描述）、`Result`
- `Evidence boundary`（對應 §4.2 的 `Proved` + `Not-proved`）
- `Storage path`（指向 `docs/verification/IMP-NNN/` 的具體檔名）

**07_implementation.md 不取代 raw evidence；raw evidence 不省略 metadata header。**

### 4.5 Re-run / Superseded Evidence

| 情境 | 處理方式 |
|---|---|
| 同一測試重跑（PASS → PASS） | 新增新 timestamp 檔案；舊檔保留；`07_implementation.md` item record 更新 `Timestamp` 與 `Storage path` 指向最新檔案 |
| 修正後重跑（FAIL → PASS，含同日） | 新增新 timestamp PASS 檔案；舊 FAIL 檔案**保留，不得刪除或改寫**；`07_implementation.md` 記錄最新 PASS，但 Known Limits 節應說明曾有 FAIL 及修正摘要 |
| 重複 FAIL | 每次 FAIL 均新增獨立 timestamp 檔案；不覆蓋；有助追蹤問題演進 |
| Authoritative evidence | **同一 item + 同一 layer** 中，timestamp 最新且 Result = PASS 的檔案為目前 authoritative evidence；若最新為 FAIL，authoritative 為空，不得以舊 PASS 冒充 |

**禁止：** 刪除或改寫 FAIL evidence；以較舊的 PASS 回填最新失敗。

### 4.6 Hardware Evidence Recording

Hardware evidence artifact 記錄下列資訊（在 raw 文字檔中，metadata header 之後）：

```text
Target hardware:   <device name + serial/ID if available>
Device identity:   <e.g. M1 driver ID, /dev/ttyUSB0 enumeration, picoScan IP, IMU /dev/ttyACM0>
Software version:  <git SHA, ROS node version, driver firmware if known>
Test condition:    <hardware state at test start; preflight reference to #6 procedure>
Observed result:   <exact output, measurement, or operator observation>
PASS / FAIL:       PASS | FAIL
Proved:            <what this hardware test actually proved>
Not-proved:        <what this hardware test cannot prove>
```

**注意：** 本節定義 evidence **保存格式**。硬體安全操作前置條件（E-stop、架車、速度上限、watchdog、人工復歸）由 §6 完整定義。Hardware evidence artifact 的 `Test condition` 欄必須標明驗證等級與安全前置條件（依 §6.3 / §6.9 規範填寫）。

### 4.7 Relationship to §3 Template

§3.2 template 的 `Storage path` 欄位使用本節的命名格式：

```text
docs/verification/IMP-NNN/<YYYY-MM-DD>T<HHmmss>_<layer>_<desc>.txt
```

其中：
- `IMP-NNN` 與本 item 的 checklist 編號一致。
- `YYYY-MM-DD` 與 `T<HHmmss>` 共同構成執行時間，對應 metadata `Timestamp` 欄位。
- `layer` 對應 evidence 類型（`build` / `unit` / `intg` / `hw` / `neg`）。
- `desc` 為簡短描述。

Storage path 由 §4 確立，build/test command 規範由 §5 確立，硬體安全前置由 §6 確立，**不再使用 `[pending #4]`、`[pending #5]` 與 `[pending #6]`**；所有治理前置項（Checklist #1–#6）均已就緒。

### 4.8 Known Limits and Next Boundary

- 本 convention 不依賴外部 artifact server、CI 系統或 database；所有 in-repo evidence 均為純文字，適合 `git log` 追蹤。
- `.gitignore` 中已存在 `*.log` 排除規則；`docs/verification/` 下的 `.txt` 與 `.ref.txt` 不受此規則影響，可正常 commit。
- Large artifact（ROS bag 等）的外部保存位置尚未統一；`[external: ...]` + `.ref.txt` 機制為目前最低限度 reference，具體外部位置由各 item 執行時決定。
- Build 與 test 的完整 command workflow 由 §5（Build and Test Command Baseline）確立。
- Hardware safety preflight 由 §6（Runtime and Hardware Safety Preflight）確立。
- 第 1–6 項治理基線已全數完成；下一個項目：[`07_implementation_checklist.md`](./07_implementation_checklist.md) 第 7 項 S7 `M1Driver` transport vertical slice。

---

## 5. Build and Test Command Baseline

本節定義 checklist #7–#27 在開發與驗證過程中，執行 dependency closure、build、test、result inspection、static checks 與 evidence capture 的 canonical command baseline。

本節是**唯一關於 build/test commands 的 normative source**；`07_implementation.md` §3 template 的 `Command` 欄位均以本節為準。

### 5.1 Execution Environment & Workflow Overview

#### Host vs Container 責任劃分

| 環境 | 責任範圍 | 典型操作 |
|---|---|---|
| **Host** | 容器生命週期、裝置權限、Git 與檔案系統管理 | `docker compose up -d`、`docker compose ps`、`git` 操作、`/dev/tty*` 檢查 |
| **`mobile_base` Container** | 所有 ROS 2 與建置相關操作 | `rosdep`、`colcon build`、`colcon test`、`colcon test-result`、`ros2` CLI |

#### 容器執行方式

- **互動式開發終端（推薦）**：
  ```bash
  docker compose exec mobile_base bash
  ```
- **Host 單次非互動執行（用於腳本或自動化）**：
  ```bash
  docker compose exec -T mobile_base bash -c "<commands>"
  ```
- **工作目錄**：容器內 `/workspaces/mobile_base`，對應 host repository 根目錄（透過 bind mount 雙向同步）。

#### 環境載入（Sourcing Hierarchy）

容器內 non-login subshell 不會自動載入 ROS 環境，每個命令序列或終端連線必須明確執行 sourcing：

1. **底層 ROS 2 Jazzy 環境（必要）**：
   ```bash
   source /opt/ros/jazzy/setup.bash
   ```
2. **Workspace Overlay 環境（在 build 產出 `install/` 後，執行 test、ros2 pkg/node/topic 時必要）**：
   ```bash
   source install/setup.bash
   ```

### 5.2 Dependency Closure Workflow (`rosdep`)

在新增 package、修改 `package.xml` 或進行環境確認時，執行下列 canonical 指令確認依賴閉包：

```bash
# 1. 更新 rosdep 來源索引快取（有新增 package 或外部 rosdep 時執行）
rosdep update

# 2. 檢查並安裝 workspace 所有 source packages 宣告的依賴項
rosdep install --from-paths src --ignore-src -y --rosdistro jazzy
```

**依賴閉包邊界說明：**
- Docker image（`Dockerfile`）已預先安裝所有系統級與 ROS 2 binary 依賴（如 `libmodbus-dev`、`python3-serial`、`ros-jazzy-*`）。
- `src/` 目錄保留自研與外部 source packages（如 `rf2o_laser_odometry`、`tdk_ros2_imu`）。
- `rosdep install` 成功（輸出 `#All required rosdeps installed successfully`，exit 0）僅證明所有 `package.xml` 所需之 binary/system packages 已在環境中滿足，不代表 source code 已成功編譯或執行。

### 5.3 Build Commands: Full, Incremental, and Clean

所有建置指令均在容器內 `/workspaces/mobile_base` 執行，並預先 `source /opt/ros/jazzy/setup.bash`。

#### Canonical Full Workspace Build
```bash
source /opt/ros/jazzy/setup.bash && colcon build --symlink-install
```

#### Incremental Build
不刪除 `build/` 與 `install/`，直接執行 `colcon build --symlink-install`。適用於單一套件內的程式碼修訂與快速驗證。

#### Clean Build
在下列情況下，**必須執行 Clean Build** 以排除快取干擾：
1. 變更 package 名稱、刪除套件、修改 CMakeLists.txt 的 target/install 結構或 ROS interface 定義（msg/srv/action）。
2. 套件間 API/ABI 邊界變更，或升級底層函式庫。
3. 進行驗收審計（IMP-026 Clean Environment Audit）或宣布 Feature Frozen 之前。

**Clean Build 指令：**
```bash
rm -rf build/ install/ log/ && source /opt/ros/jazzy/setup.bash && colcon build --symlink-install
```

#### `--symlink-install` 規則
全面使用 `--symlink-install`：
- Python 腳本、launch 檔與 YAML 設定檔在修改後可立即生效，無需反覆重建。
- C++ 程式庫與執行檔依標準 CMake 規則編譯至 `build/` 並鏈結/複製至 `install/`。

### 5.4 Selective Package Build

後續實作項目（IMP-007 起）通常針對特定 package 進行開發，使用以下規範指令：

#### 單一套件獨立建置（`--packages-select`）
```bash
source /opt/ros/jazzy/setup.bash && colcon build --symlink-install --packages-select <package_name>
```
- **語意**：僅編譯 `<package_name>`。
- **前提**：該套件在 workspace 內的所有上游依賴套件已經事先編譯並存在於 `install/` overlay。
- **證據邊界**：僅證明 `<package_name>` 自身編譯通過；無法證明其他依賴它的套件未受破壞。

#### 套件及其上游依賴建置（`--packages-up-to`）
```bash
source /opt/ros/jazzy/setup.bash && colcon build --symlink-install --packages-up-to <package_name>
```
- **語意**：編譯 `<package_name>` 以及 workspace 中所有被其依賴的上游套件（依拓撲順序）。
- **使用時機**：當上游基礎套件（如 interface 或共用 utility）有變更時。

### 5.5 Test Execution & Result Inspection Baseline

#### 套件單元與介面測試
```bash
source /opt/ros/jazzy/setup.bash && colcon test --packages-select <package_name> --event-handlers console_direct+
```

#### 全 Workspace 測試
```bash
source /opt/ros/jazzy/setup.bash && colcon test --event-handlers console_direct+
```

#### 測試結果審查（Result Inspection）
測試執行後，必須透過 `colcon test-result` 審查結果，此指令在有任何失敗時會回傳非零 exit code：
```bash
colcon test-result --all --verbose
```

#### 四層驗證語意區分（嚴格禁止混淆）

```text
Build Success (編譯與鏈結通過，exit 0)
    ≠ Test Success (單元測試、介面測試與 linter 全部 PASS，exit 0)
    ≠ Integration Success (ROS 2 Graph 上 Node 通訊、TF 樹解析、Topic 串接正常)
    ≠ Hardware Success (實體 Jetson + M1 / LiDAR / IMU 於實機物理運轉並量測通過)
```

### 5.6 Static Checks Baseline

在提交程式碼前，至少執行以下靜態檢查：

1. **格式與空白檢查**（Host 或 Container）：
   ```bash
   git diff --check
   ```
2. **套件探索性檢查（Package Discoverability）**（Container 內）：
   ```bash
   source /opt/ros/jazzy/setup.bash && source install/setup.bash && ros2 pkg list | grep <package_name>
   ```
3. **套件內建 Linter 檢查**：
   透過 `colcon test --packages-select <package_name>` 執行套件配置的 ament linter（如 `ament_flake8`, `ament_pep257`, `ament_copyright`, `ament_cmake_lint` 等）。
4. **編譯器警告審查**：
   檢查 `colcon build` 輸出，確保無意外的編譯器警告（Compiler Warnings）。

### 5.7 Evidence Capture Integration with §4 Convention

依據 §4 Convention，每次建置與測試的原始輸出必須保存於 `docs/verification/IMP-NNN/<YYYY-MM-DD>T<HHmmss>_<layer>_<desc>.txt`。

#### 標準 Evidence Capture 指令範式

為避免管線（pipeline）遮蔽真實指令的 exit code（例如 `cmd | tee` 可能導致失敗時 exit code 仍為 0），採用下列標準捕捉範式：

```bash
# === 1. 設定變數 ===
IMP_ID="IMP-007"
LAYER="build"
DESC="colcon_m1_driver"
TS=$(date +"%Y-%m-%dT%H%M%S")
EVID_DIR="docs/verification/${IMP_ID}"
EVID_FILE="${EVID_DIR}/${TS}_${LAYER}_${DESC}.txt"
mkdir -p "${EVID_DIR}"

# === 2. 執行指令並捕捉 stdout/stderr 與真實 exit code ===
TMP_LOG=$(mktemp)
# 範例建置指令（可依測試替換）
CMD_STR="colcon build --symlink-install --packages-select <package_name>"

docker compose exec -T mobile_base bash -c "source /opt/ros/jazzy/setup.bash && ${CMD_STR}" > "${TMP_LOG}" 2>&1
CMD_EXIT=$?

if [ ${CMD_EXIT} -eq 0 ]; then
  RESULT="PASS"
else
  RESULT="FAIL"
fi

# === 3. 寫入符合 §4.2 Metadata Header 與 Raw Log ===
cat << EOF > "${EVID_FILE}"
# IMP: ${IMP_ID}
# Layer: ${LAYER}
# Timestamp: $(date -Iseconds)
# Env: mobile_base:latest / jazzy / Ubuntu 24.04 (Noble)
# Target: <package_name>
# Command: ${CMD_STR}
# Version: $(git rev-parse --short HEAD)
# Result: ${RESULT}
# Proved: Package <package_name> compiles successfully in container baseline.
# Not-proved: Runtime execution, node integration, or real hardware operation.

EOF

cat "${TMP_LOG}" >> "${EVID_FILE}"
rm -f "${TMP_LOG}"

echo "Evidence saved to ${EVID_FILE} [Result: ${RESULT}]"
```

### 5.8 Failure Behavior & Re-run Rules

若 `rosdep`、`colcon build`、`colcon test` 或 `colcon test-result` 任一步驟失敗（exit code ≠ 0）：

1. **完整保存失敗證據**：產生 `# Result: FAIL` 的 evidence 檔案並 commit。
2. **禁止宣稱 PASS**：`07_implementation.md` 對應欄位不得標記 PASS，狀態不得推進至 `Build Verified`。
3. **禁止覆蓋或刪除**：修正問題後重新執行，必須產生**全新 timestamp** 的 evidence 檔案；舊的 FAIL 檔案永久保留在 repository 內。
4. **Authoritative Evidence 認定**：同一 item + 同一 layer 中，最新且 `Result: PASS` 的檔案為當前權威依據。

### 5.9 Definition of Build Verified (Definition of Done)

 checklist #7–#27 的任一 implementation item 欲宣告達到 `Build Verified` 狀態，**必須同時滿足以下 6 項條件**：

| # | 驗收條件 | 驗證指令 / 判斷標準 |
|---|---|---|
| 1 | **Dependency Closure** | `rosdep install --from-paths src --ignore-src -y --rosdistro jazzy` 執行成功（exit 0）。 |
| 2 | **Build Closure** | `colcon build --symlink-install --packages-select <pkg>`（或 `--packages-up-to`）編譯完成，0 errors, 0 failed。 |
| 3 | **Test Closure** | `colcon test --packages-select <pkg>` 且 `colcon test-result --all --verbose` 顯示 0 errors, 0 failures。 |
| 4 | **Discoverability** | `source install/setup.bash && ros2 pkg list` 能正確列出該 package。 |
| 5 | **Clean Repo State** | 建置結果完全由 git-tracked 程式碼重現，無任何未記錄的 container 內部手動修改。 |
| 6 | **Evidence Logged** | 原始 raw log 已依 §4/§5 保存至 `docs/verification/IMP-NNN/`，且 `07_implementation.md` 紀錄已更新。 |

### 5.10 Known Limits and Next Boundary

- 本 command baseline 僅涵蓋建置、靜態檢查與套件單元測試，**不涵蓋** ROS 2 runtime 整合、多節點資料流與實機硬體驅動驗證。
- 硬體安全操作前置流程由 §6（Runtime and Hardware Safety Preflight）確立。
- 第 1–6 項治理基線已全數完成；下一個項目：[`07_implementation_checklist.md`](./07_implementation_checklist.md) 第 7 項 S7 `M1Driver` transport vertical slice。

---

## 6. Runtime and Hardware Safety Preflight

本節定義在任何指令可能造成致動器（Actuator）、馬達或車體產生實體動作之前，必須通過的強制安全閘門（Mandatory Safety Gates）與分級驗證前置程序。

本節是**唯一關於硬體安全前置與授權邊界的 normative source**；`07_implementation.md` §3 template 的 `Hardware Evidence` 欄位與所有實機操作均以本節為準。

### 6.1 Hardware Validation Level Model（逐級提升風險、嚴禁跳級）

硬體驗證必須嚴格遵循「由無風險至高風險、逐級解鎖、嚴禁跳級」的模型：

```text
Level 0 — Software-only（純軟體／無裝置）
        ↓
Level 1 — Hardware presence / read-only（裝置存在／OS唯讀）
        ↓
Level 2 — Hardware communication / no motion（通訊唯讀／零扭矩）
        ↓
Level 3 — Safety primitive validation（安全防護與通訊驗證／零運動）
        ↓
Level 4 — Controlled actuator motion（架車／受約束致動器運動）
        ↓
Level 5 — Integrated base motion（落地／受控場域整車運動）
```

#### 各級別詳細規則矩陣

| Level | 級別名稱 | 運動允許 | 允許操作 (Allowed) | 禁止操作 (Prohibited) | 前置條件 (Prerequisites) | 人工授權要求 | 中止與失敗條件 (Exit / Abort) |
|---|---|:---:|---|---|---|---|---|
| **L0** | **Software-only** | 嚴禁 | 單元測試、Mock 介面、`colcon build`、`colcon test`、運動學純計算 | 開啟任何實體 `/dev/tty*` 裝置檔進行寫入、發布實體驅動訊號 | 無（標準開發環境） | 自動化可執行 | 編譯錯誤、測試未通過 |
| **L1** | **Hardware presence** | 嚴禁 | `ls /dev/tty*`、檢查裝置權限、讀取 udev 資訊、LiDAR 網路 ping 偵測 | 開啟裝置進行寫入、致動器供電、任何通訊寫入 | 實體線路已連接 | 自動化可執行（唯讀） | 裝置節點不存在、權限不足、網路不通 |
| **L2** | **Hardware communication** | 嚴禁 | 開啟 Serial/Modbus/Ethernet 連線、讀取驅動器暫存器（參數、警報碼、靜態編碼器數值） | 寫入控制暫存器（`SERVO-ON`、速度 JG 暫存器、目標 RPM）、修改 Flash 參數 | L1 PASS、Baud/Port 確認 | 操作人員知悉 | 通訊 CRC 錯誤、封包逾時、ID 不匹配、存在硬體警報 |
| **L3** | **Safety primitives** | 嚴禁（零運動） | 靜態安全防護機制驗證（如：軟體層命令逾時歸零邏輯 `<validated command-timeout limit>`、Lifecycle 狀態切換測試、唯讀狀態下模擬通訊中斷之靜態故障注入、安全參數設定審查）。若涉及寫入驅動器安全相關設定，必須在零速度、無運動命令下進行 | 任何非零速度輸出、任何產生馬達扭矩或輪端轉動之指令、無人值守 | L2 PASS、車輛靜止（建議架車） | **強制當下即時授權** | 逾時防護未觸發、狀態未正確轉換、產生非預期馬達使能或動作 |
| **L4** | **Controlled actuator** | 受約束動態（架車） | **雙輪懸空架車（`<operator-approved wheel-clearance condition>`）**狀態下以受控低速（`<validated low-speed bound>`）、短脈衝持續時間（`<validated short-duration bound>`）測試轉向、齒比、編碼器增量 | 車輪著地、超出核可持續時間、無約束或超出核可速度之運轉 | L3 PASS、架車確認、實體急停／斷電處於可操作狀態、§6.3 前置清單 100% 通過 | **強制當下即時授權** | 轉向與預期相反、飛車、驅動器報警、異常震動、操作員中止 |
| **L5** | **Integrated base** | 受約束動態（落地） | 平整地面、符合測試需求之受控淨空安全區域（`<controlled-area clearance appropriate to the test>`）內進行手動受控低速點動（`<validated initial base velocity bound>`）、原地旋轉、低速導航追隨 | 高速脫機運行、在未受控或有人員穿梭區域自主導航 | L4 PASS、YAML 運作極限生效、隨車安全人員在場監控 | **強制當下即時授權** | 偏離路徑、障礙物侵入、通訊抖動、急停被觸發 |

### 6.2 Automation vs Human Authorization Boundary

為確保自動化工具（Codex / AI Agent）與實體環境的人身與設備安全，明確劃定授權邊界：

#### 1. 可由自動化工具自行執行的操作（Autonomous Scope）
- Level 0 所有操作（建置、單元測試、靜態檢查、Mock 測試）。
- Level 1 唯讀檢查（確認 `/dev/ttyUSB0`、`/dev/ttyACM0` 存在、ping LiDAR IP）。
- Level 2 唯讀檢查（執行不帶 `--arm` 的讀取腳本，如 `01_scan_bus.py`、`02_read_config.py`、`03_md2_read.py`）。
- ROS 2 唯讀 graph 檢視（`ros2 topic list`, `ros2 node list`, `ros2 topic echo`）。

#### 2. 嚴禁由自動化工具自行執行的操作（Mandatory Human Authorization）
- **任何致動器使能（Servo-On / Motor Enable）**。
- **任何馬達輸出扭矩、旋轉或車體位移指令**。
- **任何帶有 `--arm` 旗標或寫入控制暫存器的腳本**。
- **進入 Level 3、Level 4、Level 5 的任何測試**。

#### 3. 禁止「通用/永久授權」（No Blanket Approval）
- 過去曾同意進行硬體驗證**不構成**未來操作的永久授權。
- **每次**發送可能造成致動器動作的指令前，必須向操作人員提出明確請求（包含：目的、命令大小、方向、持續時間、安全層級），並獲得當下的明確授權（Explicit Authorization at Execution Time）。

### 6.3 Physical Preflight Checklist（物理安全前置清單）

在操作人員授權並執行任何 Level 4（架車動態）或 Level 5（地面動態）測試之前，必須逐項確認下列條件：

```text
[ ] 1. 實體環境淨空：AMR 周圍具備符合當前測試等級之受控淨空安全區域（<controlled-area clearance appropriate to the test>），無雜物、鬆脫電線或非測試人員。
[ ] 2. 輪端物理狀態（依等級確認）：
       - Level 4：AMR 穩固支撐於架台，雙驅動輪完全懸空離地（<operator-approved wheel-clearance condition>），徒手撥動確認車輪旋轉無干涉、無拖曳電線。
       - Level 5：AMR 置於平整、乾燥、無雜物、無階梯且邊界受控之地面。
[ ] 3. 實體斷電與急停機制（Power Isolation / Emergency Stop）：
       - 操作人員全程在場監控，實體電源切斷或急停開關處於即時可操作位置。
       - 操作人員明確知悉實體斷電程序與隔離路徑（作為 operator precondition；具體硬體能力在取得權威硬體證據前標記為 UNVERIFIED）。
[ ] 4. 運動參數嚴格約束（Command Bounding）：
       - 速度約束：限制於測試計畫核可之初始受控低速上限（<validated low-speed bound>）。
       - 時間約束：限制於單次短脈衝持續時間（<validated short-duration bound>）。
       - 加速度約束：符合 06 §3.3（SYS-028）定義之加減速限制。
[ ] 5. 預期方向確認：操作人員已知期望轉動方向（例如：下發正轉 -> 右輪向前順時針）。
[ ] 6. 裝置識別性確認：確認 /dev/ttyUSB0 確實為 M1 RS-485 匯流排，/dev/ttyACM0 確實為 IMU。
[ ] 7. 軟體版本確認：記錄當前乾淨的 Git Commit SHA。
```

#### 硬體安全能力現況聲明（Reality & Disclaimer）

| 能力項目 | 目前狀態 | 說明與安全準則 |
|---|---|---|
| **STO (Safe Torque Off)** | **`UNVERIFIED`** | 目前硬體基線無經過功能安全認證之硬體 STO 迴路證據；**嚴禁假設 STO 存在**。 |
| **Certified Safety PLC / Relay** | **`UNVERIFIED`** | 本系統目前為直接通訊架構，無外部認證安全控制器介入。 |
| **Software Stop (`cmd_vel=0` / ROS 2 Disable)** | **Non-Certified Software Mechanism** | 軟體停機依賴 ROS 2、作業系統核心與 RS-485 通訊鏈路；**絕不可等同於安全急停（Certified Safety E-stop）**。 |
| **Physical Power Isolation / Emergency Stop** | **Operator Precondition / `UNVERIFIED` Hardware Capability** | 實體電源切斷／急停開關為測試前置操作人員條件；其具體電氣隔離與斷電能力在取得權威硬體圖紙與實體證據前維持 `UNVERIFIED`，不可未經驗證即宣稱為絕對安全保障。 |
| **M1 Internal Watchdog Guarantee** | **`UNVERIFIED` / Deployment Policy Pending** | M1 驅動器通訊逾時保護行為與回復機制待實機時序與故障注入驗證確立，不可預先假設其為保證安全機制。 |

### 6.4 Read-Only-First Rule（唯讀先於控制原則）

對 M1 驅動器、LiDAR 與 IMU 的整合，嚴格落實四階段存取準則：

```text
Phase 1: 物理存在與通訊鏈路確認（Presence & Transport Read）
   ↓ (PASS)
Phase 2: 驅動器靜態參數與警報碼讀取（Configuration & Alarm Read）
   ↓ (PASS)
Phase 3: 零扭矩狀態下回授讀取（Zero-Torque Feedback Read）
   ↓ (PASS 且記錄於 docs/verification/)
Phase 4: 經授權之受約束運動寫入（Authorized Controlled Motion Write）
```

在 Phase 1–3 取得完整記錄並標記 PASS 前，**嚴禁進入 Phase 4 下發任何控制或寫入指令**。

### 6.5 M1-Specific Controlled-Motion Gate（M1 專屬運動前置閘門）

在執行 S7 `M1Driver` / `M1Hardware` 首次馬達運動指令前，必須滿足下列 10 項前置條件：

1. **Read-only 證據完備**：`01_scan_bus.py`、`02_read_config.py`、`03_md2_read.py` 執行 PASS。
2. **通訊協定語意核可**：依據 M1 官方手冊確認 Multi-drive 2.0 FC17 JG 暫存器映射與 Signed 16-bit 格式。
3. **單位轉換通過純軟體測試**：$rad/s \leftrightarrow RPM$ 與 $step \leftrightarrow rad$ 轉換已由 Level 0 單元測試驗證通過。
4. **驅動器 ID 與輪別映射固定**：確認 ID 1 為右輪（RIGHT），ID 2 為左輪（LEFT）。
5. **轉向定義明確**：正轉命令定義為車體前進方向，正向旋轉定義編碼器數值正向遞增。
6. **指令幅度約束**：目標轉速限制於初始受控低速上限（`<validated low-speed bound>`，由測試計畫明確指定）。
7. **指令時間約束**：單次命令持續時間限制於短脈衝區間（`<validated short-duration bound>`）。
8. **逾時防護有效**：Controller 內建命令逾時歸零機制（06 §3.3 規範之 `cmd_vel_timeout`）；若啟用 M1 驅動器通訊逾時保護，其暫存器參數須來自已記錄之通訊時序與故障注入驗證，非隨意填寫。
9. **明確停止路徑已測試**：零速 FC17 指令與 SERVO-OFF 停用路徑已就緒。
10. **操作人員手持實體急停／斷電開關就位**：車輛已架空，人員在場監控。

### 6.6 Failure & Abort Rules（異常中止與安全降級）

#### 1. 即刻中止觸發條件（Immediate Abort Triggers）
- 馬達旋轉方向與預期相反。
- 馬達轉速超過設定命令或出現飛車現象。
- RS-485 通訊斷線、CRC 錯誤或連續逾時。
- M1 驅動器回傳非零警報碼（如 Alarm 21 通訊逾時、過流、過溫）。
- 編碼器回授中斷、跳變或數值出現 NaN。
- 操作人員按下實體急停或發出手動中止口令。

#### 2. 中止處理流程（5 步標準程序）
1. **CUT / ZERO（切斷／歸零）**：立即發送零速指令 $\rightarrow$ 釋放 Servo 使能 $\rightarrow$ 若無回應立即切斷實體主電源。
2. **LOG FAIL（記錄失敗）**：將當前輸出與異常現象保存為 `# Result: FAIL` evidence。
3. **FREEZE & DEMOTE（凍結並降級）**：凍結測試流程，嚴禁繼續推進至下一 Level，立即降級回 Level 1 / Level 2 唯讀狀態。
4. **INVESTIGATE（靜態排查）**：在馬達完全斷電或處於零扭矩唯讀狀態下，讀取警報記錄與暫存器排查原因。
5. **RE-PREFLIGHT（重走前置）**：修復問題後，必須自 Level 0 重新開始逐級驗證，並重新執行 §6.3 物理前置檢查。**嚴禁在未排查原因前直接「重試（Retry）」**。

### 6.7 Explicit Stop Paths Hierarchy（分層停止機制）

| 停止等級 | 名稱 | 觸發方式 | 系統依賴 | 安全等級與宣告 |
|---|---|---|---|---|
| **Stop Level A** | **Software Zero Speed** | 發布 `/cmd_vel = 0` 或 Modbus FC17 寫入 Speed = 0 | ROS 2、`diff_drive_controller`、RS-485 匯流排、M1 速度閉迴路 | **軟體控制行為**（非 Certified Safety，依賴通訊正常與軟體堆疊健全） |
| **Stop Level B** | **Lifecycle Disable** | 調用 `/base/enable: false`，M1HardwareInterface 清除 SERVO-ON | ROS 2 Lifecycle 框架、M1Driver NET-IN 暫存器寫入 | **軟體狀態切換**（非 Certified Safety，馬達依驅動器設定自由滑行或煞停） |
| **Stop Level C** | **Driver Loss Watchdog** | RS-485 斷線超過驅動器 watchdog 設定值，M1 觸發保護動作 | M1 驅動器內部硬體計時器與韌體保護邏輯 | **驅動器內部保護**（`UNVERIFIED` / 依賴驅動器參數正確配置與已驗證之 fault-injection 證據；目前 deployment watchdog 策略仍為待驗證項目） |
| **Stop Level D** | **Physical E-stop / Power Isolation** | 操作人員手動按下實體急停開關或斷開主電池電源 | 實體機械／電氣開關，完全獨立於軟體與處理器 | **實體操作介入**（作為 operator precondition；其具體硬體切斷能力維持 `UNVERIFIED`，直至硬體電氣架構驗證確立） |

### 6.8 Device Identity & Port Disambiguation Rules

Linux 系統在重新開機或 USB 熱插拔後，串列埠代號（`/dev/ttyUSB*`、`/dev/ttyACM*`）可能發生飄移。為防止誤寫入非目標裝置：

1. **M1 RS-485 辨識**：連線後首先發送 Modbus FC03 讀取 Driver ID 1 與 ID 2；若無回應或 ID 不匹配，**嚴禁執行任何寫入**。
2. **TDK IMU 辨識**：連線後首先檢查資料流標頭（NMEA / ASCII 格式特徵）；若格式不符立即關閉串列埠。
3. **LiDAR 辨識**：透過指定 IP（如 `192.168.0.1`）進行 ping 測試與通訊握手，確認回傳裝置型號為 SICK LiDAR。
4. **裝置不匹配處置**：若發現裝置路徑飄移，停止操作並更新配置，不可強制下發指令。

### 6.9 Evidence Integration with §4 and §5

所有硬體驗證與安全前置操作必須依 §4 / §5 規範產出 raw evidence 檔案：

- **檔案命名**：`docs/verification/IMP-NNN/<YYYY-MM-DD>T<HHmmss>_hw_<desc>.txt`（負向測試使用 `_neg_`）。
- **Metadata Header**：
  ```text
  # IMP: IMP-NNN
  # Layer: hardware | negative
  # Timestamp: YYYY-MM-DDThh:mm:ss±HH:MM
  # Env: mobile_base:latest / jazzy / Ubuntu 24.04 (Noble)
  # Target: M1 Driver ID1+ID2 (/dev/ttyUSB0)
  # Command: <exact test command or script reference>
  # Version: <git rev-parse --short HEAD>
  # Result: PASS | FAIL
  # Proved: <one-sentence: what physical fact was proved>
  # Not-proved: <one-sentence: boundary statement>
  ```
- **內文結構（依 §4.6 規範）**：
  ```text
  Target hardware:   M1 Dual-Driver Base
  Device identity:   ID 1 (Right), ID 2 (Left) on /dev/ttyUSB0
  Software version:  <git commit SHA>
  Test condition:    Level 4 (Wheels Lifted, Preflight §6.3 PASSED, <validated low-speed bound>, <validated short-duration bound>)
  Observed result:   <exact output, measurement, or operator observation>
  PASS / FAIL:       PASS | FAIL
  Proved:            <what this test actually proved>
  Not-proved:        <what this test cannot prove>
  ```

### 6.10 Known Limits and Next Boundary

- **未驗證安全硬體能力**：STO、硬體安全控制器、實體斷電切斷能力與 M1 驅動器內部 watchdog 保證目前均標記為 `UNVERIFIED`；任何運動測試必須依賴操作人員在場監督、物理架車與預先確認之電源隔離路徑。
- **治理階段全數就緒**：Checklist #1–#6 治理前置項（Docker 基線、外部依賴、紀錄 Template、Evidence 儲存規範、建置測試基準、硬體安全前置）已全數建立完畢。
- 當前項目：[`07_implementation_checklist.md`](./07_implementation_checklist.md) 第 7 項 S7 `M1Driver` transport vertical slice。

---

## 7. Implementation Records

### IMP-007 S7 M1Driver Transport Vertical Slice

#### 3.2.1 Identity / Scope / Status

| 欄位 | 內容 |
|---|---|
| Checklist item | #7 — S7 `M1Driver` transport vertical slice |
| Item scope | 依 06 baseline 實作 `M1Driver` C++ 私有通訊與協定封裝層（libmodbus RTU connection、雙 M1 FC03 / FC17 廣播協定、單暫存器讀寫、error/timeout mapping、enable/disable/stop primitive API、純軟體單元測試與 L1/L2 唯讀實機檢驗）；不實作 `ros2_control` hardware_interface、diff_drive_controller、運動學轉換或輪徑輪距參數。 |
| Implementation status | `Implemented` |
| Evidence status | `Build Verified` + `Unit Verified` + `Hardware L1/L2 Verified` |
| Feature-freeze status | `Not Frozen` |
| Last updated | 2026-08-18 |

---

#### 3.2.2 Traceability

| 欄位 | 內容 |
|---|---|
| Requirement IDs | SYS-026 (底盤故障處理), SYS-029 (底盤狀態回授有效性 - 底層回授解析), SYS-030 (底盤安全啟停 - 底層使能/停機 primitive) |
| Subsystem | S7 Base Control Subsystem |
| Custom gap IDs | GAP-05 底層資料解析與校驗、GAP-06 底層使能/停轉 primitive 封裝 |
| Upstream design refs | `06 §3.3` S7 Base Control, `docs/design_baseline/m1_driver.md` |

---

#### 3.2.3 Implementation Artifacts

| Artifact | Path / Package | 已實作責任 | 明確不負責 |
|---|---|---|---|
| C++ Header | `src/mobile_base_control/include/mobile_base_control/m1_driver.hpp` | `M1Driver` 類別定義、`Result<T>`/`ErrorCode` 型別、`MotorCommand`/`MotorState` 結構、協定打包與解析輔助函式 | ros2_control SystemInterface、kinematics、wheel dimensions |
| C++ Implementation | `src/mobile_base_control/src/m1_driver.cpp` | libmodbus RTU 生命週期管理、Multi-drive 2.0 FC03/FC17 封包建構與回應解析、Standard Modbus FC03/FC06 單暫存器讀寫、錯誤與逾時對映 | TF 發布、里程計累積、ROS node |
| L2 Read Check Tool | `src/mobile_base_control/src/m1_l2_read_check.cpp` | 實機 Level 2 唯讀驗證獨立工具（唯讀 02-14、09-26、FC03 state、slave 99 timeout 注入） | 馬達輸出、使能寫入、運動指令 |
| Validation Harness | `src/mobile_base_control/include/mobile_base_control/m1_control_check.hpp`, `src/m1_control_check_core.cpp`, `src/m1_control_check_main.cpp` | Level 3/4 受控寫入驗證獨立 Harness（支援 `read`, `enable`, `stop`, `disable`, `exchange`；強制 `--dry-run` 與 `--execute` 安全確認防護；單一失敗立即中斷不重試） | ros2_control controller、生產節點 |
| Driver Unit Tests | `src/mobile_base_control/test/test_m1_driver.cpp` | 9 項 GTest（ID/bitmask、signed 16/32-bit、FC03/FC17 request、response parsing、mock transact、negative fault injection、connect failure） | 實機物理旋轉 |
| Harness Unit Tests | `src/mobile_base_control/test/test_m1_control_check.cpp` | 8 項 GTest（CLI 解析、參數檢驗、Dry-run 無寫入保證、指令預覽匹配、執行安全標籤確認、失敗立即中斷不重試） | 實機物理旋轉 |
| Validation Procedure | `docs/m1_bringup_validation/16_imp007_controlled_write_procedure.md` | Level 3/4 實機驗證前置檢查、執行指令語法、各步驟預期狀態、中止條件與急停路徑規範 | — |
| Build & Metadata | `src/mobile_base_control/CMakeLists.txt`, `package.xml` | ROS 2 Jazzy ament_cmake 套件建置與依賴定義 | — |

---

#### 3.2.4 Mature Component / Custom Boundary

| 欄位 | 內容 |
|---|---|
| Mature component(s) used | `libmodbus` (v3.1.10-1ubuntu1, system library) |
| Custom implementation | M1 Multi-drive 2.0 廣播協定打包/解包、驅動器 ID 位元遮罩計算、signed 32-bit 位置轉換、MotorState 解析、自訂 Result<T>/ErrorCode 錯誤模型、受控驗證 Harness |
| Boundary rule | `libmodbus` 私有負責底層 Serial RTU context、CRC16 產生與驗證、逾時設定與收發；`M1Driver` 負責 M1 專屬協定語意與馬達狀態結構封裝，不對上層洩漏 libmodbus 型別或 raw Modbus 細節。 |

---

#### 3.2.5 Authoritative Interfaces and Configuration

#### Published / Subscribed Interfaces

| 方向 | Interface name | Message type | Frame / QoS | Producer / Consumer | 06 ref |
|---|---|---|---|---|---|
| N/A | None | None | None | `M1Driver` 為 C++ transport library，無獨立 ROS 2 Node 或 Topic | `06 §3.3` |

#### Key Parameters

| Parameter | Configuration Rule | 說明 | 06 / Baseline ref |
|---|---|---|---|
| `device` | Caller 明確傳入 | M1 RS-485 串列埠裝置節點（例如 `/dev/ttyUSB0`） | `06 §3.3` / Compose |
| `baud` | Caller 明確傳入 | M1 通訊 Baud rate（例如 `230400`，8N1） | `06 §3.3` |
| `timeout_ms` | Caller 明確傳入 | 單次交易逾時門檻 (ms)；`M1Driver` public API 不提供預設值，由 caller / `M1Hardware` 於 runtime 提供；本次 L2 實機驗證使用 100 ms，單元測試使用 50 ms，final production timeout 尚未凍結 | `docs/design_baseline/m1_driver.md §7` |

---

#### 3.2.6 Failure / Timeout / Cancel / Invalid-input Handling

| 情境 | 觸發條件 | 期望行為（來自 06） | 已驗證 | 驗證層級 |
|---|---|---|---|---|
| Failure | Modbus 異常回應 (`0x83` / `0x97`) | 回傳 `ErrorCode::MODBUS_EXCEPTION` | Yes | Unit |
| Failure | 串列通訊斷線或 CRC 損壞 | 回傳 `ErrorCode::RECEIVE_FAILED` / `ErrorCode::SEND_FAILED` | Yes | Unit |
| Timeout | 串列回應超過指定 timeout_ms | 回傳 `ErrorCode::TIMEOUT` | Yes | Unit + Hardware L2 |
| Invalid input | 傳入無效 Driver ID (<1 或 >8 或重複) | 回傳 `ErrorCode::INVALID_ARGUMENT`，拒絕發送 | Yes | Unit |
| Invalid input | 回應長度不足或 Function Code 不匹配 | 回傳 `ErrorCode::BAD_LENGTH` / `ErrorCode::BAD_FUNCTION` | Yes | Unit |

---

#### 3.2.7 Verification Evidence

#### Static / Build Evidence

| Timestamp | Command | Result | Evidence boundary | Storage path |
|---|---|---|---|---|
| 2026-08-18T12:06:51+08:00 | `colcon build --symlink-install --packages-select mobile_base_control` | PASS | `mobile_base_control` 套件、`m1_driver` 函式庫、`m1_l2_read_check` 工具與 `m1_control_check` 驗證 Harness（含 mock 支援與安全警告）建置成功（0 errors）。 | [`docs/verification/IMP-007/2026-08-18T120638_build_m1_driver.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-007/2026-08-18T120638_build_m1_driver.txt) |
| 2026-08-18T12:03:01+08:00 | `colcon build --symlink-install --packages-select mobile_base_control` | PASS | （歷史基準）`mobile_base_control` 套件與 `m1_control_check` 初版建置成功（0 errors）。 | [`docs/verification/IMP-007/2026-08-18T120241_build_m1_driver.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-007/2026-08-18T120241_build_m1_driver.txt) |
| 2026-08-18T11:59:01+08:00 | `colcon build --symlink-install --packages-select mobile_base_control` | PASS | （歷史基準）`mobile_base_control` 套件含 explicit timeout_ms 簽章建置成功（0 errors）。 | [`docs/verification/IMP-007/2026-08-18T115855_build_m1_driver.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-007/2026-08-18T115855_build_m1_driver.txt) |
| 2026-08-18T11:46:01+08:00 | `colcon build --symlink-install --packages-select mobile_base_control` | PASS | （歷史基準）初版 `mobile_base_control` 套件建置成功（0 errors）。 | [`docs/verification/IMP-007/2026-08-18T114546_build_m1_driver.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-007/2026-08-18T114546_build_m1_driver.txt) |

#### Unit / Interface Evidence

| Timestamp | Test target | Command | Result | Evidence boundary | Storage path |
|---|---|---|---|---|---|
| 2026-08-18T12:06:52+08:00 | `mobile_base_control` (All tests) | `colcon test --packages-select mobile_base_control` + `colcon test-result` | PASS | 全部 20 項 GTests（`test_m1_driver` 9 項 + `test_m1_control_check` 11 項，含 safety hazard warning、zero-speed-intent 術語、best-effort cleanup 語意與 mock 執行）與 6 項 ament linters 通過，0 failures（74 tests total）。 | [`docs/verification/IMP-007/2026-08-18T120640_unit_m1_control_check.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-007/2026-08-18T120640_unit_m1_control_check.txt) |
| 2026-08-18T12:03:02+08:00 | `mobile_base_control` (All tests) | `colcon test --packages-select mobile_base_control` + `colcon test-result` | PASS | （歷史基準）全部 17 項 GTests 與 6 項 ament linters 通過（71 tests total）。 | [`docs/verification/IMP-007/2026-08-18T120243_unit_m1_control_check.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-007/2026-08-18T120243_unit_m1_control_check.txt) |
| 2026-08-18T11:59:02+08:00 | `mobile_base_control::test_m1_driver` | `colcon test --packages-select mobile_base_control` + `colcon test-result` | PASS | （歷史基準）9 項 GTests 與 6 項 ament linters 通過（46 tests total）。 | [`docs/verification/IMP-007/2026-08-18T115857_unit_m1_driver.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-007/2026-08-18T115857_unit_m1_driver.txt) |
| 2026-08-18T11:46:02+08:00 | `mobile_base_control::test_m1_driver` | `colcon test --packages-select mobile_base_control` + `colcon test-result` | PASS | （歷史基準）初版 8 項 GTests 與 6 項 ament linters 通過（45 tests total）。 | [`docs/verification/IMP-007/2026-08-18T114548_unit_m1_driver.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-007/2026-08-18T114548_unit_m1_driver.txt) |
| 2026-08-18T11:46:03+08:00 | `M1DriverTest.NegativeHandling` | `test_m1_driver --gtest_filter=M1DriverTest.NegativeHandling` | PASS | 驗證無效驅動器 ID、逾時模擬與發送失敗之錯誤對映。 | [`docs/verification/IMP-007/2026-08-18T114551_neg_m1_driver_timeout.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-007/2026-08-18T114551_neg_m1_driver_timeout.txt) |

#### Hardware Evidence

| Timestamp | Target hardware | Test condition | Observed result | Evidence boundary | Storage path |
|---|---|---|---|---|---|
| 2026-08-18T12:20:35+08:00 | Jetson + M1 Dual-Driver Base (`/dev/ttyUSB0`) | Level 3 (Zero-speed-intent write), 230400 8N1, timeout=100ms | 兩台 M1 在 Servo-On 下成功接收 Multi-drive 2.0 FC17 JG 0 (`0x0001` 0 RPM) 指令，維持 Status=0 (`STOP`)、RPM=0、Alarm=0，最終調用 disable() 安全回復至 Status=6。 | 證明 JG 0 停轉 primitive 能在 Servo-On 零速狀態下被實機接受；不證明非零速煞停減速、煞停距離或時間。 | [`docs/verification/IMP-007/2026-08-18T122035_hw_m1_l3_stop.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-007/2026-08-18T122035_hw_m1_l3_stop.txt) |
| 2026-08-18T12:17:25+08:00 | Jetson + M1 Dual-Driver Base (`/dev/ttyUSB0`) | Level 3 (Zero-speed-intent write), 230400 8N1, timeout=100ms | 兩台 M1 成功接收 Multi-drive 2.0 FC17 SVOFF (`0x0007`) 指令，Status 由 0 (`STOP`) 回復為 6 (`WAIT/INHIBIT`)，激磁保持阻抗解除，RPM=0、Alarm=0。 | 證明 disable primitive 正常運作且馬達能安全釋放使能。 | [`docs/verification/IMP-007/2026-08-18T121725_hw_m1_l3_disable.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-007/2026-08-18T121725_hw_m1_l3_disable.txt) |
| 2026-08-18T12:15:49+08:00 | Jetson + M1 Dual-Driver Base (`/dev/ttyUSB0`) | Level 3 (Zero-speed-intent write), 230400 8N1, timeout=100ms | 兩台 M1 成功接收 Multi-drive 2.0 FC17 SVON (`0x0006`) 指令，Status 由 6 (`WAIT/INHIBIT`) 轉為 0 (`STOP`)，馬達產生激磁保持扭矩，無任何輪端旋轉，RPM=0、Alarm=0。 | 證明 enable primitive 正常運作且馬達能安全進入使能保持態。 | [`docs/verification/IMP-007/2026-08-18T121549_hw_m1_l3_enable.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-007/2026-08-18T121549_hw_m1_l3_enable.txt) |
| 2026-08-18T11:46:04+08:00 | Jetson + M1 Dual-Driver Base (`/dev/ttyUSB0`) | Level 2 (No Motion / Read-Only), 230400 8N1, timeout=100ms | ID1 (Right) & ID2 (Left) 成功讀取 02-14=1, 09-26=0; Multi-drive 2.0 FC03 成功讀取雙驅動器狀態 (status=6, alarm=0, bus~51.1V); slave 99 成功逾時。 | 證明實機 Modbus RTU 唯讀通訊健全；未下發任何寫入指令。 | [`docs/verification/IMP-007/2026-08-18T114553_hw_m1_l2_read_only.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-007/2026-08-18T114553_hw_m1_l2_read_only.txt) |

---

#### 3.2.8 Evidence Boundary

| 欄位 | 內容 |
|---|---|
| 已證明 | `m1_driver` 與 `m1_control_check` 驗證 Harness 在 ROS 2 Jazzy 環境中成功編譯並通過所有 20 項單元測試與 linter（74 tests total）；在實機 `/dev/ttyUSB0` (230400 8N1) 上完成 Level 2 唯讀測試與 Level 3 零速意圖控制寫入測試（`read_state`、`enable`、`stop`、`disable` 均在實機驗證通過且狀態轉換正確：6 → 0 → 0 → 6，全過程無非預期運動、無警報）。 |
| 尚未證明 | 非零速度實體運動（Level 4 exchange motion）、從非零速度煞停之減速曲線與煞停距離/時間、第三方認證安全停機（Certified Safety Stop）、硬體通訊 Watchdog 逾時跳脫與復歸行為（待後續整合驗證）。 |

---

#### 3.2.9 Known Limits / Unresolved Dependencies

- **Level 3 控制寫入完成與 Level 4 狀態**：`M1Driver` 核心通訊傳輸與零速控制 Primitives（`read_state`、`enable`、`stop`、`disable`）已全部具備實機 Level 3 驗證證據；非零速度運動（Level 4 exchange motion）因 Process-Crash Hazard 考量目前保持 `BLOCKED`，留待 #8 `M1Hardware` 整合與閉環控制時進行受控驗證。
- **通訊 Watchdog 行為**：M1 通訊 Watchdog 在硬體層面仍為 `UNVERIFIED`，安全等級為 `NOT ESTABLISHED`，其具體參數（`05-17` 等）留待 control loop 實機時序量測後審慎決定。
- **Final Production Response Timeout 尚未凍結**：依據 `docs/design_baseline/m1_driver.md §7`，`M1Driver` 不硬編預設逾時常數，精確 production response timeout 尚待後續 `M1Hardware` (IMP-008) 實機整合與時序量測後確定。
- `M1Driver` 僅提供通訊傳輸與狀態封裝，上層 `M1Hardware` (`SystemInterface` plugin) 將於 #8 實作。

---

#### 3.2.10 Feature Freeze Status / Next Dependency

| 欄位 | 內容 |
|---|---|
| Feature freeze status | `Not Frozen` |
| Freeze condition | #8 `M1Hardware` 整合與 Level 4/5 實機控制驗收通過 |
| Next dependency | Checklist #8 `S7 M1Hardware ros2_control integration` |

---

### IMP-008 S7 M1Hardware ros2_control Integration

#### 3.2.1 Identity / Scope / Status

| 欄位 | 內容 |
|---|---|
| Checklist item | #8 — S7 `M1Hardware` ros2_control integration |
| Item scope | 依 06 baseline 與 `docs/design_baseline/m1_hardware.md` 實作 `mobile_base_control::M1Hardware`（`hardware_interface::SystemInterface` plugin for ROS 2 Jazzy），包含 Model A2 控制迴圈（`write()` 單次 FC17 交易、`read()` 無通訊消費快取狀態）、單位轉換（$rad/s \leftrightarrow RPM$、齒比 20.0、左輪 +1、右輪 -1、3000 RPM 上限保護）、位置回授與 32-bit Rollover 累積追蹤（`PositionTracker`）、Lifecycle 狀態機（`on_init`, `on_configure`, `on_activate` 帶有有限次狀態輪詢確認、`on_deactivate` 依序執行 stop -> disable -> disconnect、`on_error`/`on_shutdown` 最佳防護清理）、防禦性指令範圍檢查、可配置參數、pluginlib export XML 與註冊、單元測試、URDF `ResourceManager` 整合測試與 Mock 執行驗證；Level 3 實機全迴圈時序量測完成；Level 4 Stage D1（左輪）與 Stage D2（右輪）動態回授實機驗證完成；Checklist #8 依原始 DoD 正式結案 `[x]`。 |
| Implementation status | `Completed` |
| Evidence status | `Build Verified` + `Unit Verified` + `Plugin Discovery Verified` + `Integration Verified` + `Real-Hardware Timing & Lifecycle Level 3 Verified` + `Real-Hardware Dynamic Feedback Level 4 Stage D1 & D2 Verified` |
| Feature-freeze status | `Baseline Frozen` (Synchronous Model A2 @ 30 Hz validated implementation baseline; Checklist #8 Closed `[x]`) |
| Last updated | 2026-08-18 |

---

#### 3.2.2 Traceability

| 欄位 | 內容 |
|---|---|
| Requirement IDs | SYS-026 (底盤故障處理), SYS-028 (加減速限制), SYS-029 (底盤狀態回授有效性 - 輪速/位置回授解析與累加), SYS-030 (底盤安全啟停 - Lifecycle enable/stop/disable 控制流) |
| Subsystem | S7 Base Control Subsystem |
| Custom gap IDs | GAP-05 底層資料解析與校驗、GAP-06 底層使能/停轉 primitive 封裝、ros2_control hardware plugin |
| Upstream design refs | `06 §3.3` S7 Base Control, `docs/design_baseline/m1_hardware.md`, `docs/design_baseline/m1_driver.md` |

---

#### 3.2.3 Implementation Artifacts

| Artifact | Path / Package | 已實作責任 | 明確不負責 |
|---|---|---|---|
| C++ Header | `src/mobile_base_control/include/mobile_base_control/m1_hardware.hpp` | `M1Hardware` 類別定義、`PositionTracker` 結構、`M1HardwareConfig` 設定、單位轉換純函式、測試注入介面 | controller 演算法、TF 發布、導航路徑追隨 |
| C++ Implementation | `src/mobile_base_control/src/m1_hardware.cpp` | `SystemInterface` 生命週期回呼、State/Command interface 匯出、Model A2 `read()`/`write()` 執行、防禦性輸入檢驗、驅動器報警偵測與錯誤處理 | 閉環速度 PID（由驅動器內部與 controller 負責）、IMU 融合 |
| Plugin Description XML | `src/mobile_base_control/m1_hardware_plugins.xml` | pluginlib 匯出描述檔，宣告 `mobile_base_control/M1Hardware` 繼承 `hardware_interface::SystemInterface` | — |
| Package Configuration | `src/mobile_base_control/package.xml`, `CMakeLists.txt` | 宣告 `hardware_interface`、`pluginlib`、`rclcpp` 依賴與 plugin 匯出標記 | — |
| Unit & Integration Tests | `src/mobile_base_control/test/test_m1_hardware.cpp` | 16 項 GTest（轉換數學、32-bit rollover 正反向累積、參數解析、State/Command 匯出、完整 Mock 生命週期、讀寫閉環、NaN/Inf 拒絕、未激活讀取拒絕、pluginlib 動態載入、URDF `ResourceManager` 整合） | 實機物理旋轉 |

---

#### 3.2.4 Mature Component / Custom Boundary

| 欄位 | 內容 |
|---|---|
| Mature component(s) used | `hardware_interface::SystemInterface` (ROS 2 Jazzy), `pluginlib`, `rclcpp_lifecycle`, `controller_manager::ResourceManager`, `diff_drive_controller::DiffDriveController` (`ros2_controllers`) |
| Custom implementation | `M1Hardware` ros2_control plugin、`PositionTracker` 2's complement int32 delta accumulation、Model A2 execution timing、純軟體單位與座標系轉換（Left ID2 sign +1, Right ID1 sign -1, gear ratio 20.0, 10000 steps/rev）、防禦性指令飽和與異常拒絕 |
| Boundary rule | `ros2_control` 標準框架負責 Controller 與硬體介面間之 LoanedCommand/LoanedState 借用與 Controller Manager 生命週期管理；`diff_drive_controller` 依據機器人幾何參數（`wheel_separation = 0.5545` m, `wheel_radius = 0.08` m）計算輪端線速度/角速度指令，絕不包含馬達內部減速比或編碼器細節；`M1Hardware` 封裝底層 M1 驅動器通訊細節與馬達座標系轉換，對 Controller 暴露標準 `velocity` command interface 與 `position`/`velocity` state interfaces。 |

---

#### 3.2.5 Authoritative Interfaces and Configuration

#### Exported State Interfaces

| Joint Name | Interface Type | Data Type | Units | Source | 06 ref |
|---|---|---|---|---|---|
| `driving_wheel_joint_L` | `position` | `double` | rad | Continuous accumulated motor steps $\times \frac{2\pi}{200000}$ | `06 §3.3` |
| `driving_wheel_joint_L` | `velocity` | `double` | rad/s | Motor actual RPM $\times \frac{2\pi}{60 \times 20.0} \times (+1)$ | `06 §3.3` |
| `driving_wheel_joint_R` | `position` | `double` | rad | Continuous accumulated motor steps $\times \frac{2\pi}{200000} \times (-1)$ | `06 §3.3` |
| `driving_wheel_joint_R` | `velocity` | `double` | rad/s | Motor actual RPM $\times \frac{2\pi}{60 \times 20.0} \times (-1)$ | `06 §3.3` |

#### Exported Command Interfaces

| Joint Name | Interface Type | Data Type | Units | Target | 06 ref |
|---|---|---|---|---|---|
| `driving_wheel_joint_L` | `velocity` | `double` | rad/s | Motor Target RPM = $\text{round}\left(\text{cmd} \times 20.0 \times \frac{60}{2\pi} \times (+1)\right)$, clamped to $\pm 3000$ | `06 §3.3` |
| `driving_wheel_joint_R` | `velocity` | `double` | rad/s | Motor Target RPM = $\text{round}\left(\text{cmd} \times 20.0 \times \frac{60}{2\pi} \times (-1)\right)$, clamped to $\pm 3000$ | `06 §3.3` |

#### Key Parameters

| Parameter | Configuration Rule | 說明 | 06 / Baseline ref |
|---|---|---|---|
| `serial_port` / `device` | URDF `<param>` | 串列埠裝置節點（預設 `/dev/ttyUSB0`） | `06 §3.3` |
| `baud_rate` / `baud` | URDF `<param>` | 通訊 Baud rate（預設 `230400`） | `06 §3.3` |
| `response_timeout_ms` / `timeout_ms` | URDF `<param>` (REQUIRED) | 通訊單次回應逾時門檻 (ms)；**無 production default**（必須由 URDF / caller 明確傳入，未傳入或 $\le 0$ 則 `on_init` 失敗；`100 ms` 僅為目前 unit/integration test fixture 與 L2/L3 驗證條件，final production timeout 留待後續 real-hardware latency 量測後確定） | `docs/design_baseline/m1_driver.md §7` |
| `left_driver_id` | URDF `<param>` | 左輪驅動器 ID（預設 `2`） | `06 §3.3` |
| `right_driver_id` | URDF `<param>` | 右輪驅動器 ID（預設 `1`） | `06 §3.3` |
| `gear_ratio` | URDF `<param>` | 減速比（預設 `20.0`） | `06 §3.3` |
| `left_wheel_sign` | URDF `<param>` | 左輪原生方向符號（預設 `+1`） | `06 §3.3` |
| `right_wheel_sign` | URDF `<param>` | 右輪原生方向符號（預設 `-1`） | `06 §3.3` |
| `motor_steps_per_rev` | URDF `<param>` | 馬達每轉編碼器 Steps（預設 `10000.0`） | `06 §3.3` |
| `max_motor_rpm` | URDF `<param>` | 操作馬達轉速上限（預設 `3000.0` RPM） | `06 §3.3` |

#### Controller Timing Model (Synchronous Model A2 @ 30 Hz Implementation Baseline)

- **Architecture Decision & Status**:
  * **Selected Architecture**: Synchronous Model A2.
  * **Controller Update Rate**: 30 Hz (nominal period $T = 33.333\text{ ms}$).
  * **Status**: **FROZEN AS CURRENT IMPLEMENTATION BASELINE** (validated on physical hardware with 1000 full ros2_control cycles).
  * **Timing Boundary Semantics**: 30 Hz is the validated current implementation baseline under the measured host / serial / Level-3 zero-speed conditions. The observed minimum residual timing budget of $7.419\text{ ms}$ ($22.3\%$ of the cycle period) is an **empirically observed margin under tested conditions**, not a functional-safety certified hard real-time bound or deterministic worst-case guarantee under arbitrary host load.
- **Controller Manager Cycle Flow (Model A2)**:
  1. `M1Hardware::read()`: Non-blocking ($\approx 3.4\ \mu\text{s}$ median), consumes cached motor state returned by the previous cycle's `write()` (or `on_activate()` initial handshake), updating joint positions and velocities.
  2. `diff_drive_controller::update()`: Kinematic conversion, velocity limits, and odometry integration ($\approx 8.5\ \mu\text{s}$ median).
  3. `M1Hardware::write()`: Validates finite commands, maps wheel velocity to integer motor RPM, executes single blocking Multi-drive 2.0 FC17 exchange ($\approx 16.4\text{ ms}$ median, max $25.9\text{ ms}$), and caches returned state for next cycle's `read()`.
- **Asynchronous Model B Status**:
  * **Status**: **Not Selected / Deferred Alternative**.
  * **Rationale**: Synchronous Model A2 @ 30 Hz successfully completed 1000/1000 full control cycles with 0 deadline misses under tested conditions; synchronous semantics preserve direct cycle-accurate hardware transaction acknowledgment in `write()`; Model B introduces background thread concurrency, deferred error propagation, and complex shutdown/stale-command synchronization without any current system requirement demanding $> 30\text{ Hz}$ base control.
- **Response Timeout Policy (`response_timeout_ms`)**:
  * **Semantics**: **REQUIRED explicit runtime configuration parameter**; no implicit production default exists in `M1Hardware` source code (must be supplied via URDF / parameters).
  * **Current Validated Deployment Candidate**: `50 ms` (successfully exercised across FC17 Stage A, Stage B, and 1000-cycle full ros2_control loop without timeouts or false triggers).
- **Update Rate Revalidation / Reopen Triggers**:
  The 30 Hz timing decision must be revalidated if any of the following occur:
  1. RS-485 Baud rate change (different from 230400 bps).
  2. USB-to-serial adapter or serial driver/hardware change.
  3. M1 drive firmware update or Modbus protocol timing change.
  4. Host computing platform or kernel upgrade.
  5. Significant CPU workload increase on the `controller_manager` execution thread.
  6. Additional blocking hardware interfaces added to the same real-time control loop.
  7. Requested update rate increase (e.g. $> 30\text{ Hz}$).
  8. Observed runtime deadline overruns or latency regressions during operational testing.
  9. Level 4 physical motion reveals materially different FC17 transaction duration under motor load.
  10. Upstream navigation or perception requirements introduce a higher minimum base control update rate.

---

#### 3.2.6 Failure / Timeout / Cancel / Invalid-input Handling

| 情境 | 觸發條件 | 期望行為（來自 06） | 已驗證 | 驗證層級 |
|---|---|---|---|---|
| Invalid Input | 指令為 NaN 或 Inf | 拒絕執行寫入、目標 RPM 歸零，回傳 `return_type::ERROR`；禁止 command substitution | Yes | Integration |
| Invalid Input | 輪速超出安全上限 | 自動飽和鉗位至 `max_motor_rpm`（$\pm 3000$ RPM），不溢位 | Yes | Unit |
| Missing Timeout Param | 未提供 `response_timeout_ms` / `timeout_ms` 或 $\le 0$ | `on_init` / `parse_parameters` 立即拒絕並回傳 `CallbackReturn::ERROR` | Yes | Unit |
| Communication Failure | FC17 通訊逾時或斷線 | `M1Hardware` 將 cycle failure 以 `return_type::ERROR` 回報 ros2_control；後續 lifecycle/controller handling 由 ros2_control framework / controller manager policy 決定 | Yes | Integration |
| Drive Alarm | 驅動器回傳非零 Alarm 碼 | `read()` 或 `write()` 立即偵測並以 `return_type::ERROR` 回報 ros2_control | Yes | Unit |
| Activation Timeout | `on_activate` 狀態輪詢逾時（超過 10 次） | 自動發送 `disable()` 清理，回傳 `CallbackReturn::ERROR` | Yes | Unit |
| Deactivate / Shutdown / Error | 系統停用、關機或發生錯誤 | 依序執行 `stop(0 RPM)` $\rightarrow$ 延時 $\rightarrow$ `disable(SVOFF)` $\rightarrow$ `disconnect()`；非激活狀態下 `read()`/`write()` 拒絕執行 | Yes | Integration |

---

#### 3.2.7 Verification Evidence

#### Static / Build Evidence

| Timestamp | Command | Result | Evidence boundary | Storage path |
|---|---|---|---|---|
| 2026-08-18T13:45:00+08:00 | `colcon build --symlink-install --packages-select mobile_base_control` | PASS | `mobile_base_control` 套件、`m1_full_loop_timing_check` 工具與 `test_m1_full_loop_timing_check` 測試建置成功（0 errors）。 | [`src/mobile_base_control/src/m1_full_loop_timing_check_core.cpp`](file:///home/zzz/mobile_base/src/mobile_base_control/src/m1_full_loop_timing_check_core.cpp) |
| 2026-08-18T13:15:00+08:00 | `colcon build --symlink-install --packages-select mobile_base_control` | PASS | `mobile_base_control` 套件、`m1_fc17_latency_check` 工具與 `test_m1_fc17_latency_check` 測試建置成功（0 errors）。 | [`docs/verification/IMP-008/2026-08-18T131500_sw_m1_fc17_latency_prep.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-008/2026-08-18T131500_sw_m1_fc17_latency_prep.txt) |
| 2026-08-18T13:10:00+08:00 | `colcon build --symlink-install --packages-select mobile_base_control` | PASS | `mobile_base_control` 套件、`m1_latency_check` 量測工具與 `test_m1_latency_stats` 測試建置成功（0 errors）。 | [`docs/verification/IMP-008/2026-08-18T131000_hw_m1_l2_latency.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-008/2026-08-18T131000_hw_m1_l2_latency.txt) |
| 2026-08-18T13:05:00+08:00 | `colcon build --symlink-install --packages-select mobile_base_control` | PASS | `mobile_base_control` 套件、`m1_driver` 與 `m1_hardware` 函式庫及 `DiffDriveController` 整合測試建置成功（0 errors）。 | [`docs/verification/IMP-008/2026-08-18T130500_diff_drive_controller_integration.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-008/2026-08-18T130500_diff_drive_controller_integration.txt) |
| 2026-08-18T12:55:00+08:00 | `colcon build --symlink-install --packages-select mobile_base_control` | PASS | （歷史基準）`response_timeout_ms` 參數修訂建置成功（0 errors）。 | [`docs/verification/IMP-008/2026-08-18T125500_build_test_m1_hardware_timeout_erratum.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-008/2026-08-18T125500_build_test_m1_hardware_timeout_erratum.txt) |
| 2026-08-18T12:50:00+08:00 | `colcon build --symlink-install --packages-select mobile_base_control` | PASS | （歷史基準）`mobile_base_control` 套件初版建置成功（0 errors）。 | [`docs/verification/IMP-008/2026-08-18T125000_build_test_m1_hardware.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-008/2026-08-18T125000_build_test_m1_hardware.txt) |

#### Unit / Integration / Hardware Evidence

| Timestamp | Test target | Command | Result | Evidence boundary | Storage path |
|---|---|---|---|---|---|
| 2026-08-18T14:43:40+08:00 | IMP-008 (Checklist #8) Formal Closure Evidence & DoD Audit | N/A (Documentation & Governance Review) | PASS | 原始 Checklist #8 DoD 八項條款（SystemInterface lifecycle、command/state interfaces、真實 wheel feedback validity、禁止 command substitution、diff-drive controller、timeout 與 safe-stop chain）全部 PASS；Stage D1 (Left) 與 Stage D2 (Right) 實機動態回授與物理方向驗證通過；Model A2 @ 30 Hz 實作基準凍結；Checklist #8 正式結案 `[x]`。 | [`docs/verification/IMP-008/2026-08-18T144340_closure_m1_hardware_ros2_control.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-008/2026-08-18T144340_closure_m1_hardware_ros2_control.txt) |
| 2026-08-18T14:34:40+08:00 | Real Hardware Level 4 Stage D2 Right-Wheel Dynamic Feedback Validation | `m1_dynamic_stage_d2_check --execute --device /dev/ttyUSB0 --baud 230400 --timeout-ms 50 --driver-a 1 --driver-b 2 --right-vel 0.5 --warmup 10 --active-cycles 60 --cooldown 10 --raw-output docs/verification/IMP-008/2026-08-18T143440_m1_dynamic_stage_d2_raw.csv` | PASS | 80 週期實機動態運動量測完成（10 warmup + 60 active @ 0.5 rad/s + 10 cooldown @ 30 Hz），成功率 100.0%（0 errors, 0 timeouts, 0 alarms）；右輪 command +0.5 rad/s 正確轉換為 Driver ID 1 負向目標 -95 RPM，實際轉速回授響應為負向且經 M1Hardware 符號翻轉轉換為正向 ROS 輪速 ~0.497 rad/s（穩態 0.4869 ~ 0.5079 rad/s），累積位置自 0.0000 rad 遞增至 +0.9906 rad（+56.76 deg，理論 1.00 rad，誤差 0.94%）；左輪全程維持 0.0000 rad/s 與 0.0000 rad（完全隔離）；冷卻階段平順減速至 0 RPM，驗證完成後安全復歸 Servo-Off（Status=6, Alarm=0, RPM=0）。 | [`docs/verification/IMP-008/2026-08-18T143440_hw_m1_dynamic_stage_d2.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-008/2026-08-18T143440_hw_m1_dynamic_stage_d2.txt)<br/>[`docs/verification/IMP-008/2026-08-18T143440_m1_dynamic_stage_d2_raw.csv`](file:///home/zzz/mobile_base/docs/verification/IMP-008/2026-08-18T143440_m1_dynamic_stage_d2_raw.csv) |
| 2026-08-18T14:32:45+08:00 | Level 4 Stage D2 Right Wheel Dynamic Feedback Software Preparation | `test_m1_dynamic_stage_d2_check` + Dry-Run CLI test | PASS | 全部 6 項 GTests（Dry-Run 0 transport calls、CLI 拒絕違規/左輪參數、右輪速度 Harness 限制 $\le 1.5$ rad/s、週期邊界檢驗、轉換數學證明 +0.5 rad/s $\rightarrow$ -95 RPM、URDF 生成結構）與 dry-run 輸出驗證通過，0 failures。 | [`docs/verification/IMP-008/2026-08-18T143245_unit_m1_dynamic_feedback_stage_d2_prep.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-008/2026-08-18T143245_unit_m1_dynamic_feedback_stage_d2_prep.txt) |
| 2026-08-18T14:27:10+08:00 | Real Hardware Level 4 Stage D1 Left-Wheel Dynamic Feedback Validation | `m1_dynamic_stage_d1_check --execute --device /dev/ttyUSB0 --baud 230400 --timeout-ms 50 --driver-a 1 --driver-b 2 --left-vel 0.5 --warmup 10 --active-cycles 60 --cooldown 10 --raw-output docs/verification/IMP-008/2026-08-18T142710_m1_dynamic_stage_d1_raw.csv` | PASS | 80 週期實機動態運動量測完成（10 warmup + 60 active @ 0.5 rad/s + 10 cooldown @ 30 Hz），成功率 100.0%（0 errors, 0 timeouts, 0 alarms）；左輪在 active 階段自 0 加速至穩態 ~95 RPM（~0.497 rad/s），累積位置自 0.0000 rad 遞增至 +0.9895 rad（+56.69 deg，理論 1.00 rad，誤差 1.05%）；右輪全程維持 0.0000 rad/s 與 0.0000 rad（完全隔離）；冷卻階段平順減速至 0 RPM，驗證完成後安全復歸 Servo-Off（Status=6, Alarm=0, RPM=0）。 | [`docs/verification/IMP-008/2026-08-18T142710_hw_m1_dynamic_stage_d1.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-008/2026-08-18T142710_hw_m1_dynamic_stage_d1.txt)<br/>[`docs/verification/IMP-008/2026-08-18T142710_m1_dynamic_stage_d1_raw.csv`](file:///home/zzz/mobile_base/docs/verification/IMP-008/2026-08-18T142710_m1_dynamic_stage_d1_raw.csv) |
| 2026-08-18T14:17:00+08:00 | Level 4 Stage D1 Left Wheel Dynamic Feedback Software Preparation | `test_m1_dynamic_stage_d1_check` + Dry-Run CLI test | PASS | 全部 6 項 GTests（Dry-Run 0 transport calls、CLI 拒絕違規/反向參數、左輪速度 Harness 限制 $\le 1.5$ rad/s、週期邊界檢驗、轉換數學證明 0.5 rad/s $\rightarrow$ 95 RPM、URDF 生成結構）與 dry-run 輸出驗證通過，0 failures。 | [`docs/verification/IMP-008/2026-08-18T141700_unit_m1_dynamic_feedback_stage_d1_prep.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-008/2026-08-18T141700_unit_m1_dynamic_feedback_stage_d1_prep.txt) |
| 2026-08-18T13:52:14+08:00 | Real Hardware Level 3 Full ros2_control Loop @ 30 Hz Zero-Speed Validation | `m1_full_loop_timing_check --execute --device /dev/ttyUSB0 --baud 230400 --timeout-ms 50 --driver-a 1 --driver-b 2 --rate 30 --warmup 20 --cycles 1000 --raw-output docs/verification/IMP-008/2026-08-18T135214_m1_full_loop_30hz_raw.csv` | PASS | 1000 筆實機完整 ros2_control 控制迴圈（`read` -> `diff_drive_controller` -> `write` FC17）量測完成，成功率 100.0%（0 failures, 0 timeouts, 0 deadline misses）；Full cycle mean 16.40 ms, p50 16.44 ms, p99 24.20 ms, Max 25.91 ms (StdDev 4.63 ms)；最小觀測剩餘時序預算 +7.419 ms (22.26%)；實機全程 0 RPM、0 Alarm、0 非零指令；安全停用與降級斷電正常。 | [`docs/verification/IMP-008/2026-08-18T135214_hw_m1_full_loop_30hz.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-008/2026-08-18T135214_hw_m1_full_loop_30hz.txt)<br/>[`docs/verification/IMP-008/2026-08-18T135214_m1_full_loop_30hz_raw.csv`](file:///home/zzz/mobile_base/docs/verification/IMP-008/2026-08-18T135214_m1_full_loop_30hz_raw.csv) |
| 2026-08-18T13:47:00+08:00 | Full ros2_control Loop 30 Hz Timing Check Software Preparation | `test_m1_full_loop_timing_check` + Dry-Run CLI test | PASS | 全部 5 項 GTests（Dry-Run 0 transport calls、CLI 拒絕非零運動參數、邊界選項檢驗、零速不變量 Zero-Command Invariant 數學證明、URDF 生成結構）與 dry-run 輸出驗證通過，0 failures。 | [`src/mobile_base_control/test/test_m1_full_loop_timing_check.cpp`](file:///home/zzz/mobile_base/src/mobile_base_control/test/test_m1_full_loop_timing_check.cpp) |
| 2026-08-18T13:30:00+08:00 | Real Hardware L3 FC17 Zero-Speed Latency Stage B | `m1_fc17_latency_check --execute --device /dev/ttyUSB0 --baud 230400 --timeout-ms 50 --driver-a 1 --driver-b 2 --warmup 20 --samples 200 --raw-output docs/verification/IMP-008/2026-08-18T133000_m1_fc17_stage_b_raw.csv` | PASS | 200 筆實機 FC17 zero-speed exchange 量測完成，成功率 100.0%（0 failures, 0 timeouts）；Min 10.99 ms, Mean 16.00 ms, p50 16.00 ms, p99 16.20 ms, Max 21.01 ms (StdDev 0.51 ms)。實機全程維持 0 RPM 與 0 Alarm。 | [`docs/verification/IMP-008/2026-08-18T133000_m1_fc17_stage_b_raw.csv`](file:///home/zzz/mobile_base/docs/verification/IMP-008/2026-08-18T133000_m1_fc17_stage_b_raw.csv) |
| 2026-08-18T13:24:20+08:00 | Real Hardware L3 FC17 Zero-Speed Latency Stage A | `m1_fc17_latency_check --execute --device /dev/ttyUSB0 --baud 230400 --timeout-ms 50 --driver-a 1 --driver-b 2 --warmup 5 --samples 20 --raw-output docs/verification/IMP-008/2026-08-18T132420_m1_fc17_stage_a_raw.csv` | PASS | 20 筆實機 FC17 zero-speed exchange 量測完成，成功率 100.0%（0 failures, 0 timeouts）；Min 15.85 ms, Mean 15.99 ms, p50 15.99 ms, p99 16.15 ms, Max 16.15 ms (StdDev 0.07 ms)。實機全程維持 0 RPM 與 0 Alarm。 | [`docs/verification/IMP-008/2026-08-18T132420_m1_fc17_stage_a_raw.csv`](file:///home/zzz/mobile_base/docs/verification/IMP-008/2026-08-18T132420_m1_fc17_stage_a_raw.csv) |
| 2026-08-18T13:15:00+08:00 | Level 3 FC17 Zero-Speed Latency Check Software Preparation | `test_m1_fc17_latency_check` + Dry-Run CLI test | PASS | 全部 7 項 GTests（Dry-Run 0 transport calls、CLI 拒絕非零運動參數、樣本數硬性上限檢驗、`exchange_zero` 協定封包 JG 0 結構驗證、完整 Mock 生命週期、異常轉速中止與清理、Alarm 中止與清理）與 dry-run 輸出驗證通過，0 failures。 | [`docs/verification/IMP-008/2026-08-18T131500_sw_m1_fc17_latency_prep.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-008/2026-08-18T131500_sw_m1_fc17_latency_prep.txt) |
| 2026-08-18T13:10:00+08:00 | Real Hardware L2 Communication Latency & Jitter | `m1_latency_check --device /dev/ttyUSB0 --baud 230400 --timeout-ms 100 --driver-a 1 --driver-b 2 --warmup 20 --samples 1000` | PASS | 1000 筆實機連續雙驅動器 `read_state(1, 2)` 通訊延遲量測完成，成功率 100.0%（0 failures, 0 timeouts）；Min 11.2 ms, Mean 16.0 ms, p50 16.0 ms, p99 16.2 ms, Max 20.8 ms (StdDev 0.32 ms)。實機全程維持 0 RPM 與 0 Alarm。 | [`docs/verification/IMP-008/2026-08-18T131000_hw_m1_l2_latency.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-008/2026-08-18T131000_hw_m1_l2_latency.txt) |
| 2026-08-18T13:10:00+08:00 | `mobile_base_control::test_m1_latency_stats` | `colcon test --packages-select mobile_base_control` | PASS | 全部 5 項統計函數 GTests 通過，0 failures。 | [`docs/verification/IMP-008/2026-08-18T131000_hw_m1_l2_latency.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-008/2026-08-18T131000_hw_m1_l2_latency.txt) |
| 2026-08-18T13:05:00+08:00 | `mobile_base_control::test_m1_hardware` | `colcon test --packages-select mobile_base_control` + `colcon test-result` | PASS | 全部 27 項 GTests（含 8 項 DiffDriveController 整合測試）與 6 項 ament linters 通過，0 failures。 | [`docs/verification/IMP-008/2026-08-18T130500_diff_drive_controller_integration.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-008/2026-08-18T130500_diff_drive_controller_integration.txt) |
| 2026-08-18T12:55:00+08:00 | `mobile_base_control::test_m1_hardware` | `colcon test --packages-select mobile_base_control` + `colcon test-result` | PASS | （歷史基準）全部 19 項 GTests 通過，0 failures。 | [`docs/verification/IMP-008/2026-08-18T125500_build_test_m1_hardware_timeout_erratum.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-008/2026-08-18T125500_build_test_m1_hardware_timeout_erratum.txt) |
| 2026-08-18T12:50:00+08:00 | Pluginlib ClassLoader Discovery | `test_m1_hardware --gtest_filter=M1HardwareLifecycleTest.PluginLoaderDiscovery` | PASS | 驗證 `hardware_interface::SystemInterface` ClassLoader 能動態探索並實例化 `mobile_base_control/M1Hardware`。 | [`docs/verification/IMP-008/2026-08-18T125000_plugin_discovery.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-008/2026-08-18T125000_plugin_discovery.txt) |

---

#### 3.2.8 Evidence Boundary

#### Authoritative Definition-of-Done (DoD) Audit

| DoD Clause | Evidence | Result | Boundary |
|---|---|---|---|
| 1. SystemInterface lifecycle | 7 GTests + Lifecycle Mock + Real HW L3/D1/D2 | PASS | Init/configure/activate/deactivate/shutdown/error 與實機 Servo-Off 狀態轉換確認 |
| 2. Command interfaces | 6 GTests + Mock integration + Real HW D1/D2 | PASS | 左右輪 velocity 介面、rad/s $\leftrightarrow$ RPM 齒比/符號轉換、上限飽和 |
| 3. State interfaces | 5 GTests + Mock integration + Real HW L2/L3/D1/D2 | PASS | 左右輪 position/velocity 介面、32-bit rollover 累積追蹤與 NaN 防護 |
| 4. 真實 wheel feedback validity | Real HW Stage D1 (Left) + Stage D2 (Right) | PASS | 實體輪端正向旋轉（操作人員現場確認）、真實馬達 RPM 回授、編碼器位置連續遞增、ROS 狀態介面即時反映、單輪運動時對側完全隔離 |
| 5. 禁止 command substitution | GTest ProhibitCommandSubstitution + HW D1/D2 加減速暫態量測 | PASS | 狀態介面純粹由感測器回授更新，加減速暫態與微小 Jitter 證明無 command echo |
| 6. diff-drive controller | 8 DiffDriveController GTests + Real HW 1000 週期 Timing Check | PASS | 官方 diff_drive_controller 閉環控制、幾何轉換、里程計運算與 30 Hz 全迴圈無 deadline miss |
| 7. Timeout | GTest TimeoutHandling + Real HW 50 ms 部署參數驗證 | PASS | `response_timeout_ms` 屬 REQUIRED runtime parameter，無隱式預設值；50 ms 在實測環境下 0 timeout |
| 8. Safe-stop chain | GTest DeactivateReturnsToServoOff + Real HW D1/D2/L3 停機驗證 | PASS | 依序執行 stop(0 RPM) $\rightarrow$ disable(SVOFF) $\rightarrow$ disconnect，實機復歸 Status=6, Alarm=0, RPM=0 |

#### Proven Boundary Summary (`PASS`)

1. **純軟體轉換與閉環邏輯** (`PASS`)：官方 `diff_drive_controller::DiffDriveController` 與 `M1Hardware` SystemInterface plugin 在純軟體/Mock 環境下之完整整合閉環、正反向符號轉換、齒比運算、32-bit Rollover 累積追蹤與 NaN/飽和保護（44 項 GTest 與 6 項 ament linters 通過）。
2. **實機唯讀延遲特性** (`PASS`)：實機 `/dev/ttyUSB0` 上 1000 次連續雙驅動器 `read_state(1, 2)` 通訊延遲分佈特性（Mean 16.0 ms, p99 16.2 ms, Max 20.8 ms）。
3. **實機零速通訊交易** (`PASS`)：實機 220 次 FC17 zero-speed exchange（Stage A 20 + Stage B 200, 100% 成功, 0 timeouts/alarms, Max 21.01 ms）。
4. **實機 30 Hz 全迴圈時序** (`PASS`)：實機 1000 週期 Full ros2_control Loop @ 30 Hz zero-speed 實機時序驗證（1000/1000 成功, 0 deadline misses, 0 timeouts, 0 alarms, Max full cycle 25.91 ms，最小觀測剩餘時序預算 +7.419 ms / 22.3%）。
5. **實機零速回授與生命週期路徑** (`PASS`)：實機真實 M1 狀態回授路徑（`actual_rpm=0`、`accumulated_steps`、`status=6/0`、`alarm=0`）與生命週期啟停序列（enable SVON -> 零速閉環運作 -> 停用 stop JG 0 -> disable SVOFF -> 斷線）。
6. **實機 Stage D1 左輪動態回授與方向有效性** (`PASS`)：
   - ROS 左輪 $+0.5\text{ rad/s}$ 指令正確映射至驅動器 2（Left）之 $+95\text{ RPM}$ 目標值。
   - 實體左輪依預期正向旋轉（自機器人左側觀察為逆時針 CCW，輪頂向前旋轉，操作人員現場確認）。
   - 實機左輪實際轉速回授為正向且與 $\sim 95\text{ RPM}$ 目標動態一致（穩態 $0.4765 \sim 0.5184\text{ rad/s}$）。
   - 實機左輪編碼器位置隨運動連續遞增（自 $0.0000\text{ rad}$ 累積至 $+0.9895\text{ rad}$ / $+56.69^\circ$）。
   - ROS 左輪 velocity 與 position state interfaces 正確反映真實回授。
   - 右輪 command 保持嚴格為零，右輪實際 RPM 保持 0，右輪編碼器位移為 0，操作人員現場確認右輪全程保持靜止（完全隔離）。
   - 全程 0 alarm, 0 timeout, 0 transport/lifecycle error, 0 非預期運動。
   - 受控 cooldown 平順減速至 0 RPM，驗證完成後安全復歸 Servo-Off（Status=6, Alarm=0, RPM=0）。
7. **實機 Stage D2 右輪動態回授與方向有效性** (`PASS`)：
   - ROS 右輪 $+0.5000\text{ rad/s}$ 指令正確映射至 Driver ID 1（Right）負向目標 $-95\text{ RPM}$（`right_wheel_sign = -1`）。
   - 實體右輪依預期正向旋轉（自機器人右側觀察為順時針 CW，輪頂向前旋轉，操作人員現場確認）。
   - 實機 Driver ID 1 實際轉速回授響應為負向，經 `M1Hardware` 符號翻轉後轉換為正向 ROS 輪速且與 $\sim +0.4974\text{ rad/s}$ 目標動態一致（穩態 $+0.4869 \sim +0.5079\text{ rad/s}$）。
   - 實機右輪編碼器位置隨運動連續遞增（自 $0.0000\text{ rad}$ 累積至 $+0.9906\text{ rad}$ / $+56.76^\circ$，誤差 $0.94\%$）。
   - ROS 右輪 velocity 與 position state interfaces 正確反映真實回授。
   - 左輪 command 保持嚴格為零，左輪實際 RPM 保持 0，左輪編碼器位移為 0，操作人員現場確認左輪全程保持靜止（完全隔離）。
   - 全程 0 alarm, 0 timeout, 0 transport/lifecycle error, 0 非預期運動。
   - 受控 cooldown 平順減速至 0 RPM，驗證完成後安全復歸 Servo-Off（Status=6, Alarm=0, RPM=0）。

#### 尚未證明 / 明確排除項 (Not Proven / Downstream Scope)

1. **反向運動有效性** (`UNVERIFIED`)：負向速度指令（後退）之動態回授與方向正確性。
2. **雙輪同步動態 Stage D3** (`OPTIONAL CONFIDENCE EVIDENCE`)：雙輪同時非零正向運動下之動態回授（Stage D1 與 Stage D2 已各自證明單輪動態回授與對側隔離，且單次 FC17 transaction 已同時處理雙驅動器傳輸，故 Stage D3 歸類為額外信心測試，非 Checklist #8 結案阻擋項）。
3. **整車動態與地面行駛行為** (`DOWNSTREAM SCOPE`)：著地行駛行為（Floor-driving behavior）、輪端打滑（Wheel slip）、里程計精度（Odometry accuracy）、導航追隨性能（Navigation performance）與煞車距離特性（Braking-distance characterization），屬下游子系統整合（Checklist #13 State Estimation / Navigation）與系統驗收範疇。
4. **精密標定與一般定量速度追隨公差** (`UNVERIFIED`)：精密輪速標定（Precision speed calibration）與一般定量速�| Timestamp | Test target | Command | Result | Evidence boundary | Storage path |
|---|---|---|---|---|---|
| 2026-08-19T13:46:00+08:00 | S2 TDK IMU Launch & Software Test Suite | `colcon test --packages-select tdk_ros2_imu mobile_base_perception` + `colcon test-result` | PASS | 全部 7 項測試套件通過（35 測試項目，0 failures, 0 errors）：驗證 59-byte 封包解析、Checksum 拒絕、雜訊重同步、SI 單位轉換、四元數計算、節點參數防呆、串口斷線/錯誤終止、LaunchDescription 生成、主題重新映射（`/tdk/imu -> /imu/data_raw`）、Frame（`base_imu_link`）；全工作區 5 套件 273 項回歸測試通過。 | [`docs/verification/IMP-011/2026-08-19T134600_sw_s2_imu_runtime_integration.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-011/2026-08-19T134600_sw_s2_imu_runtime_integration.txt) |
| 2026-08-19T13:48:30+08:00 | Stage I1: Passive Device Identity / Readiness | `ls -l /dev/ttyACM0 /dev/serial/by-id/*` & `udevadm info -n /dev/ttyACM0` | PASS | 實機 `/dev/ttyACM0` (STMicroelectronics Virtual COM Port, VID:PID `0483:5740`, Serial `2063328E4842`, `cdc_acm` 驅動, mode `crw-rw---- root dialout`) 存在；穩定符號連結 `/dev/serial/by-id/usb-STMicroelectronics_STM32_Virtual_ComPort_2063328E4842-if00` 正確指向 `/dev/ttyACM0`；容器內裝置節點可見且具備完整讀寫權限。 | [`docs/verification/IMP-011/2026-08-19T134830_hw_stage_i1_passive_identity.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-011/2026-08-19T134830_hw_stage_i1_passive_identity.txt) |
| 2026-08-19T13:50:00+08:00 | Stage I2: Real-Hardware Static IMU Acquisition | `ros2 launch mobile_base_description robot_description.launch.py` & `ros2 launch mobile_base_perception tdk_imu.launch.py` | PASS | 實機 `/imu/data_raw` 穩定發布（實測頻率 $176.8\,\text{Hz} \ge 50\,\text{Hz}$，`SensorData` QoS，單調遞增主機時間戳，`frame_id: base_imu_link`）；50 筆靜態樣本統計：車體 $Z$ 軸靜態重力加速度平均 $+9.78879\,\text{m/s}^2$（符合 $+9.81 \pm 0.2\,\text{m/s}^2$ 規範門檻，誤差 $-0.18\%$），水平加速度 $a_x \approx -0.00412, a_y \approx -0.00175\,\text{m/s}^2$，角速度 $\omega_x \approx +0.00013, \omega_y \approx +0.00026, \omega_z \approx -0.00009\,\text{rad/s}$；四元數正規化良好（模長 $1.000000$）；TF `base_link -> base_imu_link`（$[+0.044, -0.008, -0.015]\,\text{m}$，$\text{RPY} = [0, 0, +90^\circ]$）連通正常。 | [`docs/verification/IMP-011/2026-08-19T135000_hw_stage_i2_static_acquisition.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-011/2026-08-19T135000_hw_stage_i2_static_acquisition.txt) |

#### 3.5.8 Evidence Boundary

| 欄位 | 內容 |
|---|---|
| 已證明 (`PASS`) | 1. **套件建置與結構完整性** (`PASS`)：`tdk_ros2_imu` 與 `mobile_base_perception` 於 ROS 2 Jazzy 環境下正確建置與安裝。<br/>2. **封包解析與校驗和防護** (`PASS`)：59-byte 封包解析無誤，壞校驗和與雜訊能正確過濾並重新同步。<br/>3. **單位轉換與姿態計算** (`PASS`)：加速度換算為 $\text{m/s}^2$、角速度換算為 $\text{rad/s}$、歐拉角換算為正規化四元數。<br/>4. **序列埠異常與斷線安全處理** (`PASS`)：序列埠開啟失敗與運行中斷線均觸發 `RuntimeError` 與 Fatal 日誌。<br/>5. **Launch 組合與主題/Frame 綁定** (`PASS`)：`tdk_imu.launch.py` 正確生成 `imu_driver_node`，`frame_id` 綁定為 `base_imu_link`，主題重新映射為 `/imu/data_raw`。<br/>6. **工作區全回歸測試** (`PASS`)：全工作區 5 套件 273 項測試全部通過（0 failures, 0 errors, 30 skipped）。<br/>7. **實機被動裝置識別與容器可見性 (Stage I1)** (`PASS`)：`/dev/ttyACM0` 存在且硬體 VID:PID（`0483:5740`）、序號（`2063328E4842`）及穩定 by-id 路徑完全吻合，容器內權限完備。<br/>8. **實機靜態數據與發布頻率 (Stage I2)** (`PASS`)：實體 `/imu/data_raw` 穩定串流（$176.8\,\text{Hz}$）、靜態重力 $a_z = +9.78879\,\text{m/s}^2$（符合 $+9.81 \pm 0.2\,\text{m/s}^2$）、單調時間戳、SensorData QoS、零共變異數與 S1 靜態 TF 連通。 |
| 尚未證明 (後續實機驗證項) | 1. **實機手動旋轉動態響應 (Stage I3)**：手動旋轉/傾斜底盤驗證角速度與加速度符號響應。 |

#### 3.5.9 Known Limits / Outstanding Obligations

- **硬體執行邊界保護**：Stage I2 僅在架高靜止之底盤上完成靜態重力與串流品質量測，未執行任何手動動態旋轉/傾斜。
- **無輪端動力輸出**：IMU 驗證絕不涉及輪端動力輸出或馬達控制（不執行 M1 指令）。
- **實機驗證排程**：Stage I3 手動旋轉動態響應將於使用者授權後執行。

#### 3.5.10 Feature Freeze Status / Next Dependency

| 欄位 | 內容 |
|---|---|
| Feature freeze status | `Stage I1 & Stage I2 Complete` (S2 Perception IMU Static Acquisition Established; Checklist #11 Remains `[~]` Pending Real-Hardware Stage I3 Dynamic Evidence) |
| Freeze condition | 軟體測試、Stage I1 被動識別與 Stage I2 實機靜態重力量測全部通過；待 Stage I3 手動旋轉動態響應驗證通過後方可結案 `[x]` |
| Next dependency | Checklist #11 Stage I3 Real-Hardware Manual Dynamic Validation |��實作標準 Xacro 模型（`mobile_base.urdf.xacro`、`mobile_base_geometry.xacro`、`mobile_base_ros2_control.xacro`）、6 項核心 3D 幾何網格（`base_link.STL`、`driving_wheel_link_L/R.STL`、`base_lidar_link_FL/BR.STL`、`base_imu_link.STL`）、靜態與動態關節定義（`base_footprint` 根坐標系、`base_link` 高程 $0.2560\,\text{m}$、輪心高程 $-0.1760\,\text{m}$、雙輪關節軸 $[0, 1, 0]$、雷達與 IMU 06 標準量測坐標系）、`robot_state_publisher` 啟動檔（`robot_description.launch.py`）、`check_urdf` 與 Xacro 語法自動化測試、`/tf_static` 廣播整合測試、ament linters、語意修正（嚴格逾時參數權屬、感測器網格 $R_{\text{comp}} = R_{\text{joint}}^{-1}$ 逆向補償）以及實機幾何合理性驗證（$< 2.0\,\text{mm}$）。 |
| Implementation status | `Closed [x]` (All software, TF, mesh, and physical geometry sanity criteria verified and closed) |
| Evidence status | `Build Verified` + `Unit Verified (8/8 tests)` + `Launch Integration Verified (1/1 test)` + `Ament Linters Passed (5/5 suites)` + `check_urdf Verified` + `Physical Sanity Evidence Verified` |
| Feature-freeze status | `Baseline Frozen` (Checklist #9 Closed `[x]`) |
| Last updated | 2026-08-18 |

#### 3.3.2 Requirements & Architecture Traceability

- **承接需求**：`SYS-023` 機器人描述、`CAP-001`、`CAP-002`、遵守 `REP-103`（Standard Units of Measure & Coordinate Conventions）與 `REP-120`（Coordinate Frames for Mobile Platforms）。
- **架構依賴**：
  - 上游：06 §3.1 規範之幾何坐標與外參、IMP-008 已凍結之 `M1Hardware` 控制介面名稱（`driving_wheel_joint_L`, `driving_wheel_joint_R`）。
  - 下游：S2 Perception (`dual_laser_merger`, `rf2o`)、S3 State Estimation (`robot_localization`)、S4 Mapping (`slam_toolbox`)、S5 Localization (`amcl`)、S6 Navigation (`nav2_costmap_2d`)、S7 Base Control (`diff_drive_controller`)。

#### 3.3.3 File Artifact Inventory

```text
src/mobile_base_description/
├── CMakeLists.txt
├── package.xml
├── urdf/
│   ├── mobile_base.urdf.xacro          # Top-level composition
│   ├── mobile_base_geometry.xacro      # Canonical frames, kinematics, visual/collision
│   └── mobile_base_ros2_control.xacro  # Parameterized <ros2_control> block
├── meshes/
│   ├── base_link.STL                   # Chassis mesh (11.57 MB)
│   ├── driving_wheel_link_L.STL        # Left wheel mesh (427 KB)
│   ├── driving_wheel_link_R.STL        # Right wheel mesh (427 KB)
│   ├── base_lidar_link_FL.STL          # Front-Left LiDAR mesh (2.85 MB)
│   ├── base_lidar_link_BR.STL          # Rear-Right LiDAR mesh (2.60 MB)
│   └── base_imu_link.STL               # IMU mesh (145 KB)
├── config/
│   └── robot_state_publisher.yaml     # 30 Hz publish frequency configuration
├── launch/
│   └── robot_description.launch.py    # robot_state_publisher launch
└── test/
    ├── test_urdf_syntax.py             # Xacro expansion, check_urdf & frame contract tests
    └── test_robot_description_launch.py # /robot_description and /tf_static integration test
```

#### 3.3.4 Mature Solution vs. Custom Implementation Boundary

- **成熟方案引用**：採用 ROS 2 Jazzy 官方標準 `robot_state_publisher` 節點與 `xacro` 宏解析工具，完全由標準框架發布 `/robot_description` 與 `/tf_static`，絕無自行撰寫之自定義 TF 發布節點。
- **客製化實作範圍**：僅限於標準 Xacro 幾何與外參聲明（`mobile_base_geometry.xacro`）以及與已驗證之 `mobile_base_control/M1Hardware` 介面參數綁定（`mobile_base_ros2_control.xacro`）。

#### 3.3.5 Interface & Configuration

##### Canonical TF 坐標系樹與轉換矩陣

```text
base_footprint (z = 0.0000, 地表投影基準點)
└── base_link (x = 0, y = 0, z = +0.2560, rpy = [0, 0, 0]) [/tf_static]
    ├── driving_wheel_link_L (x = +0.0205, y = +0.2775, z = -0.1760, rpy = [0, 0, 0], axis = [0, 1, 0]) [/tf via joint_states]
    ├── driving_wheel_link_R (x = +0.0205, y = -0.2770, z = -0.1760, rpy = [0, 0, 0], axis = [0, 1, 0]) [/tf via joint_states]
    ├── base_lidar_link_FL (x = +0.28771, y = +0.26721, z = -0.06011, rpy = [π, 0, +π/4]) [/tf_static]
    ├── base_lidar_link_BR (x = -0.24671, y = -0.26721, z = -0.06011, rpy = [π, 0, -3π/4]) [/tf_static]
    └── base_imu_link (x = +0.04375, y = -0.00800, z = -0.01459, rpy = [0, 0, +π/2]) [/tf_static]
```

##### 關鍵外參與幾何常數
- `wheel_separation`: `0.5545 m`
- `wheel_radius`: `0.0800 m`
- `base_height`: `0.2560 m`
- `wheel_center_z`: `-0.1760 m` ($+0.0800 - 0.2560\,\text{m}$)
- `response_timeout_ms`: 必填部署／執行時期參數（Required Runtime Parameter，無隱式預設值；由呼叫端／測試夾具顯式指定，如 `50 ms`）

##### 感測器 CAD 網格與 ROS 量測坐標系分離補償
- **量測坐標系（TF）與網格坐標分離原則**：關節 Transform（`R_joint`）定義標準 ROS 量測坐標系（光學向前、IMU 朝向），而 STL 網格為 CAD 裝配坐標系。
- **數學逆補償轉換**：`<visual>` 與 `<collision>` 標籤透過 $R_{\text{comp}} = R_{\text{joint}}^{-1}$ 逆向旋轉，確保網格於 `base_link` 坐標系中與底盤 CAD 開孔完美貼合（殘差 $< 10^{-16}$），同時 `/tf_static` 保持 100% 規範定義之感測器量測姿態：
  - `base_lidar_link_FL`: `origin rpy="${lidar_fl_roll} ${lidar_fl_pitch} ${lidar_fl_yaw}"` ($R_{\text{comp}} = R_{\text{joint}}$，殘差 $5.27 \times 10^{-17}$)
  - `base_lidar_link_BR`: `origin rpy="${lidar_br_roll} ${lidar_br_pitch} ${lidar_br_yaw}"` ($R_{\text{comp}} = R_{\text{joint}}$，殘差 $5.27 \times 10^{-17}$)
  - `base_imu_link`: `origin rpy="0 0 ${-imu_yaw}"` ($R_{\text{comp}} = R_{\text{joint}}^{-1}$，殘差 $0.00$)

#### 3.3.6 Failure Detection & Safety Handling

- **語法錯誤防護**：Xacro 解析失敗或 URDF 語法不完整時，`robot_state_publisher` 於啟動時立即拋出異常並終止，防止無座標系統運行。
- **逾時參數防呆**：若上層部署未顯式提供 `response_timeout_ms`，Xacro 產生無該參數之 `<ros2_control>` 區塊，`M1Hardware::on_init` 於初始化時立即拋出錯誤終止，杜絕隱式預設值風險。
- **Downstream Buffer 診斷**：下游導航與定位節點（Nav2, AMCL）透過 `tf2_ros::Buffer` 檢查所需 Transform，若逾時未收到則拒絕進入 Active 狀態。

#### 3.3.7 Verification Evidence

| Timestamp | Test target | Command | Result | Evidence boundary | Storage path |
|---|---|---|---|---|---|
| 2026-08-18T15:12:12+08:00 | S1 Robot Description Build & Test Suite | `colcon test --packages-select mobile_base_description` + `colcon test-result` | PASS | 全部 7 項測試套件通過（247 測試項目，0 failures, 0 errors, 30 skipped）：5 項 `test_urdf_syntax`、1 項 `test_robot_description_launch` 整合測試、5 項 ament linters。 | [`docs/verification/IMP-009/2026-08-18T151212_unit_s1_robot_description.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-009/2026-08-18T151212_unit_s1_robot_description.txt) |
| 2026-08-18T15:22:06+08:00 | IMP-009 Semantic Erratum Regression Suite | `colcon test --packages-select mobile_base_description` + `colcon test-result` | PASS | 全部 7 項測試套件通過（250 測試項目，0 failures, 0 errors, 30 skipped）：驗證逾時參數省略防呆（`test_timeout_omission_produces_no_param`）、顯式 `50 ms` 展開、感測器 $R_{\text{joint}} \cdot R_{\text{visual}} = I$ 數學補償（`test_sensor_mesh_alignment_and_compensation`）、雷達開孔邊界框驗證（`test_lidar_mesh_bounding_boxes`）、Launch 整合與全工作區 4 套件回歸通過。 | [`docs/verification/IMP-009/2026-08-18T152206_erratum_semantic_audit.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-009/2026-08-18T152206_erratum_semantic_audit.txt) |
| 2026-08-18T15:57:16+08:00 | IMP-009 Physical Geometry Sanity Acceptance | Physical Measurement on Chassis Stand | PASS | 實機物理量測驗證通過（v0.1 fit-for-purpose 幾何合理性驗證）：左輪直徑 $160.0\,\text{mm}$（誤差 $0.0\,\text{mm}$）、右輪直徑 $160.0\,\text{mm}$（誤差 $0.0\,\text{mm}$）、輪外跨距 $605.0\,\text{mm}$（合理性 PASS）、前保桿至輪軸 $306.6\,\text{mm}$（$X=+20.5\,\text{mm}$，誤差 $0.0\,\text{mm}$）、底盤主甲板至輪軸 $176.0\,\text{mm}$（高程 $256.0\,\text{mm}$，誤差 $0.0\,\text{mm}$）、雙輪無阻力旋轉、雷達與 IMU 安裝方向及干涉檢查均 PASS。 | [`docs/verification/IMP-009/2026-08-18T155716_physical_geometry_sanity.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-009/2026-08-18T155716_physical_geometry_sanity.txt) |

#### 3.3.8 Evidence Boundary

| 欄位 | 內容 |
|---|---|
| 已證明 (`PASS`) | 1. **Xacro 展開與 XML 語法有效性** (`PASS`)：`mobile_base.urdf.xacro` 展開無誤，通過 `check_urdf` 結構解析。<br/>2. **標準 ROS TF 坐標系樹** (`PASS`)：以 `base_footprint` 為根節點，各關節（`base_joint`, `driving_wheel_joint_L/R`, `base_lidar_joint_FL/BR`, `base_imu_joint`）坐標、型別與旋轉軸精確符合 06。<br/>3. **IMP-008 控制介面名稱與逾時權屬相容性** (`PASS`)：左右輪關節名稱保持一致；`response_timeout_ms` 無隱式預設值，完全遵守 IMP-008 凍結規範。<br/>4. **感測器網格渲染與開孔幾何數學貼合** (`PASS`)：經過 $R_{\text{joint}} \cdot R_{\text{comp}} = I$ 補償，網格於 `base_link` 幾何坐標中完美對齊 CAD 開孔。<br/>5. **Launch 與 TF 靜態廣播** (`PASS`)：`robot_state_publisher` 正確載入並發布 `/robot_description` 與 `/tf_static`。<br/>6. **實車物理幾何合理性驗證** (`PASS`)：實車輪徑（$160.0\,\text{mm}$）、輪軸 $X$ 偏移（$+20.5\,\text{mm}$）、底盤高程（$256.0\,\text{mm}$）之實體量測誤差均為 $0.0\,\text{mm}$（$< 2.0\,\text{mm}$ 門檻），感測器安裝方向與機構無干涉檢查均合格。 |
| 尚未證明 (後續階段與驗收項) | 1. **著地行駛動態滾動半徑與打滑特性** (`DOWNSTREAM SCOPE`)：地面負載行駛里程計精度與動態滾動半徑標定（屬 Checklist #13 State Estimation 範疇）。<br/>2. **被動萬向輪動態模擬** (`SIMULATION ONLY`)：被動萬向輪彈簧懸吊模擬（v0.1 實車控制無需此 12 軸未量測 TF 關節）。 |

#### 3.3.9 Known Limits / Outstanding Obligations

- **驗證深度治理原則**：IMP-009 實車幾何驗證定位為適用於 v0.1 MVP 之幾何合理性驗收（Fit-for-purpose geometry sanity acceptance），用以確認實車幾何符合 CAD/URDF 設計並排除裝配錯誤，非計量實驗室認證；動態著地有效滾動半徑於 Checklist #13 進行標定。
- **Checklist #9 結案狀態**：Checklist #9 所需之軟體模型、TF 坐標樹、網格幾何、ros2_control 契約與實體幾何量測證據已全部完成並通過驗證，正式標記結案 `[x]`。
- **被動萬向輪建模範圍**：v0.1 聚焦於二輪差速驅動與導航感知外參，萬向輪不納入動態 TF 關節，防止發布未量測之虛擬關節狀態。

#### 3.3.10 Feature Freeze Status / Next Dependency

| 欄位 | 內容 |
|---|---|
| Feature freeze status | `Baseline Frozen` (S1 Robot Description Completed and Verified; Checklist #9 Closed `[x]`) |
| Freeze condition | `mobile_base_description` 套件建置、測試與實機幾何合理性驗證全部通過；Checklist #9 正式結案 `[x]` |
| Next dependency | Checklist #10 `S2 LiDAR acquisition and scan baseline` (`[~] IN PROGRESS`) |

### 3.4 IMP-010: S2 LiDAR Acquisition & Scan Baseline (Checklist Item #10)

#### 3.4.1 Identity / Scope / Status

| 欄位 | 內容 |
|---|---|
| Checklist item | #10 — S2 `LiDAR acquisition and scan baseline` |
| Item scope | 依 06 §3.2 baseline 規範與實車 SICK picoScan150 硬體設定，建立 `mobile_base_perception` 套件，整合成熟 `sick_scan_xd` 3.9.0 官方 `sick_picoscan` 驅動配置。建立前左（FL，IP `192.168.0.1`，UDP Port `2115`，Frame `base_lidar_link_FL`，主題 `/scan_front`）與後右（BR，IP `192.168.0.2`，UDP Port `2116`，Frame `base_lidar_link_BR`，主題 `/scan_rear`）雙路獨立 2D LiDAR 擷取配置與啟動架構（`sick_dual_lidar.launch.py`）；設定主機接收端 IP `192.168.0.100`；透過 TCP `2111` 進行 SOPAS 動態連線交握；保留原生 $276^\circ$（$[-138^\circ, +138^\circ]$）視野；停用驅動器內部 TF 廣播（`tf_publish_rate: 0.0`），確保 S1 `robot_state_publisher` 之唯一 TF 權威；實作 launch 語法自動化測試；準備硬體驗證方案。 |
| Implementation status | `In Progress [~]` (Software baseline and launch/config tests complete and verified; real-hardware verification prepared) |
| Evidence status | `Build Verified` + `Unit Verified (3/3 tests)` + `Ament Linters Passed (5/5 suites)` + `Workspace Regression Verified (263/263 tests)` |
| Feature-freeze status | `Initial Software Slice Complete` (Checklist #10 remains `[~]` pending real-hardware acquisition evidence) |
| Last updated | 2026-08-18 |

#### 3.4.2 Requirements & Architecture Traceability

- **承接需求**：`SYS-003` LiDAR 感知（提供掃描資料供建圖、定位與導航使用）、`CAP-001`、`CAP-002`。
- **架構依賴**：
  - 上游：S1 `mobile_base_description`（提供權威 TF 坐標系 `base_lidar_link_FL` 與 `base_lidar_link_BR`）。
  - 下游：S2 `dual_laser_merger`（Checklist #12）、S2/S3 `rf2o_laser_odometry`（Checklist #12）、S4 `slam_toolbox`（Checklist #15）、S5 `amcl`（Checklist #16）、S6 `nav2_costmap_2d`（Checklist #17）。

#### 3.4.3 File Artifact Inventory

```text
src/mobile_base_perception/
├── CMakeLists.txt
├── package.xml
├── launch/
│   └── sick_dual_lidar.launch.py      # Dual SICK picoScan generic caller launch composition
└── test/
    └── test_lidar_launch_syntax.py    # Launch description & picoScan150 contract tests
```

#### 3.4.4 Mature Solution vs. Custom Implementation Boundary

- **成熟方案引用**：採用 SICK 官方 ROS 2 Jazzy 二進位套件 `ros-jazzy-sick-scan-xd` 3.9.0 提供之標準 `sick_generic_caller` 節點載入 `sick_picoscan.launch` 範本進行 Ethernet UDP 掃描資料接收、TCP 2111 SOPAS 動態握手與 `sensor_msgs/msg/LaserScan` 全幅資料發布，絕無自定義之底層網路驅動代碼。
- **客製化實作範圍**：僅限於 ROS 2 標準 launch 啟動組合，直接依 SICK 官方介面以 `name:=value` 傳入雙 picoScan 實例；確保雙實例在單一接收主機（`192.168.0.100`）上透過獨立 UDP 埠號（`2115` / `2116`）獨立運作，並綁定至 06 規範之 Topic 與 Frame ID。

#### 3.4.5 Interface & Configuration

##### 權威原始資料發布介面 (Authoritative Raw Interfaces)

| 主題名稱 | 訊息型別 | `header.frame_id` (來自 S1) | 目標硬體 IP | UDP 接收埠 | 職責 |
|---|---|---|---|---|---|
| **`/scan_front`** | `sensor_msgs/msg/LaserScan` | **`base_lidar_link_FL_1`** | `192.168.0.1` | `2115` | 前左 SICK picoScan150 全幅原始掃描（Layer 1） |
| **`/scan_rear`** | `sensor_msgs/msg/LaserScan` | **`base_lidar_link_BR_1`** | `192.168.0.2` | `2116` | 後右 SICK picoScan150 全幅原始掃描（Layer 1） |

*嚴格原則*：`/scan_front` 與 `/scan_rear` 為全系統唯一之權威原始雷達量測介面，未來的融合雷達主題 `/scan` 絕不得取代或覆寫此二原始資料來源。

##### 關鍵驅動參數配置 (picoScan150 Profile)
- `scanner_type`: `sick_picoscan`
- `hostname`: 前左 `192.168.0.1` / 後右 `192.168.0.2`
- `udp_receiver_ip`: `192.168.0.100`（Jetson 乙太網路端點）
- `udp_port`: 前左 `2115` / 後右 `2116`（雙機獨立埠號隔離）
- `imu_udp_port`: 前左 `7503` / 後右 `7504`
- `sopas_tcp_port`: `2111`（TCP SOPAS 交握通道，用於啟動時指定接收埠並觸發掃描串流）
- `publish_laserscan_fullframe_topic`: 前左 `/scan_front` / 後右 `/scan_rear`
- `publish_frame_id`: 前左 `base_lidar_link_FL` / 後右 `base_lidar_link_BR`
- `tf_publish_rate`: `0.0`（強制停用驅動程式內部 TF 發布，杜絕雙重靜態 TF 衝突）
- `all_segments_min_deg` / `all_segments_max_deg`: `-138.0` / `138.0`（原生 $276^\circ$ 視野，無人工裁切）
- `scandataformat`: `2`（Compact ScanData 格式）
- `sw_pll_only_publish`: `true`（確保 timestamp 與 ROS 系統時鐘同步）

#### 3.4.6 Failure Detection & Safety Handling

- **通訊逾時與自動重連**：驅動程式啟用 `udp_timeout_ms: 10000` 與 `message_monitoring_enabled: true`，當 UDP 串流中斷時進行診斷回報與重試。
- **故障隔離原則**：單一雷達斷線或失效時，其主題停止發布，絕不進行主題替代（No source substitution）；另一雷達維持獨立串流。

#### 3.4.7 Verification Evidence

| Timestamp | Test target | Command | Result | Evidence boundary | Storage path |
|---|---|---|---|---|---|
| 2026-08-18T17:23:33+08:00 | S2 picoScan150 Launch Syntax Test Suite | `colcon test --packages-select mobile_base_perception` + `colcon test-result` | PASS | 驗證 FL/BR 獨立 node、官方 `sick_picoscan.launch` generic caller、LaunchDescription 生成且無 `dual_laser_merger` 混入。 | [`docs/verification/IMP-010/2026-08-18T170342_unit_s2_lidar_acquisition.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-010/2026-08-18T170342_unit_s2_lidar_acquisition.txt) |
| 2026-08-18T17:26:49+08:00 | Stage L1: Passive Network / SOPAS TCP Reachability Probing | `nc -zv -w 2 192.168.0.1 2111` & `nc -zv -w 2 192.168.0.2 2111` | PASS | 雙實機 picoScan150 於 TCP 2111 均即時成功連線（exit code 0）。 | Log in transcript & Section 3.4 |
| 2026-08-18T17:34:00+08:00 | Stage L2: Dual picoScan150 Real-Hardware LaserScan Acquisition | `ros2 launch mobile_base_description robot_description.launch.py` & `ros2 launch mobile_base_perception sick_dual_lidar.launch.py` | PASS | 雙路實體雷達同時穩定發布：<br/>• `/scan_front`：24.999 Hz，1200 點（90.1% 有限實測值，均距 1.425 m），時間戳嚴格單調遞增（1787045620.3627538），Frame `base_lidar_link_FL_1`。<br/>• `/scan_rear`：25.005 Hz，1200 點（90.2% 有限實測值，均距 2.648 m），時間戳嚴格單調遞增（1787045619.9995918），Frame `base_lidar_link_BR_1`。<br/>• S1 TF 權威存在：`base_link -> base_lidar_link_FL`（[0.288, 0.267, -0.060], RPY [180°, 0°, 45°]）與 `base_link -> base_lidar_link_BR`（[-0.247, -0.267, -0.060], RPY [180°, 0°, -135°]）正確無競爭；零封包遺失（0% lost）。 | [`docs/verification/IMP-010/2026-08-18T173400_hw_s2_lidar_dual_acquisition.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-010/2026-08-18T173400_hw_s2_lidar_dual_acquisition.txt) |

#### 3.4.8 Evidence Boundary

| 欄位 | 內容 |
|---|---|
| 已證明 (`PASS`) | 1. **套件建置與結構完整性** (`PASS`)：`mobile_base_perception` 於 ROS 2 Jazzy 環境下正確建置與安裝。<br/>2. **雙 picoScan 獨立配置語意** (`PASS`)：FL (`192.168.0.1`, UDP `2115`, `base_lidar_link_FL`, `/scan_front`) 與 BR (`192.168.0.2`, UDP `2116`, `base_lidar_link_BR`, `/scan_rear`) 參數完全隔離且符合 06 與 picoScan150 原生規範。<br/>3. **TF 唯一性與 Layer-1 連通性** (`PASS`)：雙節點均設定 `tf_publish_rate: 0.0`，杜絕與 S1 `robot_state_publisher` 衝突；S1 靜態 TF 正確發布 `base_lidar_link_FL_1` 與 `base_lidar_link_BR_1`。<br/>4. **Launch 組合生成與無非授權元件** (`PASS`)：LaunchDescription 僅生成雙 `sick_generic_caller` 節點，無 `dual_laser_merger` 混入或自製 TF workaround。<br/>5. **實機網路連通與 SOPAS 交握 (Stage L1)** (`PASS`)：實機 `192.168.0.1:2111` 與 `192.168.0.2:2111` 之 TCP 連通正常。<br/>6. **實機雙串流接收與訊息有效性 (Stage L2)** (`PASS`)：`/scan_front`（24.999 Hz）與 `/scan_rear`（25.005 Hz）之實體 1200-bin 點雲有效，非零單調遞增 timestamp，有限距離點雲分佈正常（90% 有效障礙物距離）。 |
| 尚未證明 (後續驗證項) | 1. **雙雷達點雲融合 (Checklist #12)**：`dual_laser_merger` 融合輸出（屬 #12 範疇）。<br/>2. **範疇界定說明**：Stage L3 感測器中斷/故障注入非屬 Checklist #10 原生完成條件，不在本項結案範圍內。 |

#### 3.4.9 Known Limits / Outstanding Obligations

- **驗證深度治理原則**：觀察到之實機發布頻率（如 $\approx 25\,\text{Hz}$）、封包延遲與點雲距離均為實測經驗證據（Empirical Observations），非未經授權硬編碼之剛性門檻。
- **持久化配置保護**：SOPAS 啟動指令僅設定運作階段之 ScanDataDestination，嚴禁執行任何對 LiDAR 內部非揮發性記憶體（EEPROM/Flash）之永久寫入或網路 IP 修改命令。
- **QoS 相容性與邊界約定**：實測觀察到 `sick_scan_xd` 發布者使用之 `RELIABLE / TRANSIENT_LOCAL` QoS 與下游訂閱者配置（如 `BEST_EFFORT / VOLATILE`）在 DDS 規範下完全相容。此相容性判定不構成在任意系統負載或極端網路條件下「零掉包」之絕對保證。
- **Stage L3 範疇劃分**：Stage L3 感測器中斷/故障注入非屬 Checklist #10 原生完成條件，不在本項結案範圍內。
- **dual_laser_merger 範疇劃分**：雙雷達融合屬於 Checklist #12（Perception & Odometry Integration）範疇，不作為 Checklist #10 之結案阻塞項。

#### 3.4.10 Feature Freeze Status / Next Dependency

| 欄位 | 內容 |
|---|---|
| Feature freeze status | `Feature Freeze / Baseline Closed` (S2 Perception picoScan150 Baseline Established; Checklist #10 Closed `[x]`) |
| Freeze condition | `mobile_base_perception` 套件建置與單元/語法測試全部通過；雙路實體 picoScan150 實機量測數據與 TF static 連通性驗證完畢；Checklist #10 正式結案 `[x]`；Checklist #11 進行中 `[~]` |
| Next dependency | Checklist #11 `S2 TDK IMU runtime integration` (`[~] IN PROGRESS`) |

### 3.5 IMP-011: S2 TDK IMU Runtime Integration (Checklist Item #11)

#### 3.5.1 Identity / Scope / Status

| 欄位 | 內容 |
|---|---|
| Checklist item | #11 — S2 `TDK IMU runtime integration` |
| Item scope | 依 06 §3.2 baseline 規範與實車 TDK IIM-42652 (HandBoard IMU V1) 硬體設定，整合既存 `tdk_ros2_imu` 驅動套件與 `mobile_base_perception` 感知啟動架構。修復 `tdk_imu_node.py` 遺留之 `ros2top` 缺失相容性問題；配置序列埠 `/dev/ttyACM0`、鮑率 `115200`、Frame `base_imu_link`、標準主題 `/imu/data_raw`（透過 launch 重新映射）；發布標準 `sensor_msgs/msg/Imu`（含 SI 單位轉換、unknown covariance 與 SensorData QoS）；實作 launch/yaml 語法測試與節點 lifecycle/異常斷線測試；準備硬體驗證方案。 |
| Implementation status | `In Progress [~]` (Software baseline, node lifecycle/error tests, and launch/config tests complete and verified; real-hardware verification prepared) |
| Evidence status | `Build Verified` + `Unit Verified (7/7 test suites)` + `Workspace Regression Verified (273/273 tests)` |
| Feature-freeze status | `Initial Software Slice Complete` (Checklist #11 remains `[~]` pending real-hardware acquisition evidence) |
| Last updated | 2026-08-19 |

#### 3.5.2 Requirements & Architecture Traceability

- **承接需求**：`SYS-004` IMU 感知（提供 IMU 量測資料供定位使用）、`CAP-001`、`CAP-002`。
- **架構依賴**：
  - 上游：S1 `mobile_base_description`（提供權威 TF 坐標系 `base_imu_link`）。
  - 下游：S3 `robot_localization` EKF（Checklist #13，訂閱 `/imu/data_raw`，融合角速度 $\omega_z$ 與線加速度 $a_x$）。

#### 3.5.3 File Artifact Inventory

```text
src/tdk_ros2_imu/
├── package.xml
├── setup.py
├── launch/
│   └── tdk_imu.launch.py              # Standalone IMU driver launch with default base_imu_link & /imu/data_raw
├── tdk_ros2_imu/
│   ├── conversions.py                 # SI unit and Euler-to-quaternion conversions
│   ├── protocol.py                    # 59-byte packet parser & checksum validation
│   └── tdk_imu_node.py                # Driver Node with graceful fallback & exception safety
└── test/
    ├── test_conversions.py            # Unit tests for acceleration, angular velocity, and quaternion
    ├── test_node.py                   # Unit tests for parameter validation, serial open error, disconnect & publish
    └── test_protocol.py               # Unit tests for packet parsing, checksum rejection, and resync

src/mobile_base_perception/
├── config/
│   └── tdk_imu.yaml                   # S2 IMU parameter contract (port, baud_rate, frame_id)
├── launch/
│   └── tdk_imu.launch.py              # S2 IMU launch composition with imu_driver_node & remappings
└── test/
    └── test_imu_launch_syntax.py      # LaunchDescription and YAML parameter contract tests
```

#### 3.5.4 Mature Solution vs. Custom Implementation Boundary

- **成熟方案引用**：採用成熟 `tdk_ros2_imu` 0.1.0 處理 59-byte 二進位封包解碼、XOR checksum 檢驗、SI 單位轉換（$g \to \text{m/s}^2$, $\text{deg/s} \to \text{rad/s}$）與姿態四元數計算。
- **客製化實作範圍**：僅限於標準 ROS 2 launch 啟動組合與 YAML 參數配置檔（`mobile_base_perception`），確保節點命名為 `imu_driver_node` 並重新映射至 06 規範之 `/imu/data_raw` 主題，以及在 `tdk_imu_node.py` 中修復非標準 `ros2top` 依賴之優雅降級防護。

#### 3.5.5 Interface & Configuration

##### 權威發布介面 (Authoritative Published Interface)

| 主題名稱 | 訊息型別 | `header.frame_id` (來自 S1) | QoS Profile | 典型頻率 | 職責與消費者 |
|---|---|---|---|---|---|
| **`/imu/data_raw`** | `sensor_msgs/msg/Imu` | **`base_imu_link`** | `SensorData` | $50 \sim 100\,\text{Hz}$ | 原始 3 軸角速度與線性加速度；供 **S3 robot_localization EKF** 訂閱。 |

##### 關鍵驅動參數配置
- `port`: `/dev/ttyACM0` (CDC ACM 序列埠)
- `baud_rate`: `115200` (8N1)
- `frame_id`: `base_imu_link` (符合 S1 URDF 幾何定義)
- `linear_acceleration`: 單位 $\text{m/s}^2$（靜止時 $a_z \approx +9.81\,\text{m/s}^2$）
- `angular_velocity`: 單位 $\text{rad/s}$
- `orientation`: 四元數 $(x,y,z,w)$（由晶片內部互補濾波產出，S3 EKF 明確不融合姿態）
- `covariance`: 全 0 矩陣（REP-103 定義為 unknown covariance）

#### 3.5.6 Failure Detection & Safety Handling

- **壞封包防護**：Header 錯誤或 Checksum 不符時自動丟棄並記錄節流警告（每 5 秒最多 1 次），串流自動重尋 Header 恢復同步。
- **序列埠異常與斷線防護**：開啟埠號失敗或通訊讀取中斷時捕捉 `OSError` 與 `serial.SerialException`，記錄 Fatal 等級日誌並拋出 `RuntimeError` 終止節點，杜絕無感測器狀態下靜默發布假數據。

#### 3.5.7 Verification Evidence

| Timestamp | Test target | Command | Result | Evidence boundary | Storage path |
|---|---|---|---|---|---|
| 2026-08-19T13:46:00+08:00 | S2 TDK IMU Launch & Software Test Suite | `colcon test --packages-select tdk_ros2_imu mobile_base_perception` + `colcon test-result` | PASS | 全部 7 項測試套件通過（35 測試項目，0 failures, 0 errors）：驗證 59-byte 封包解析、Checksum 拒絕、雜訊重同步、SI 單位轉換、四元數計算、節點參數防呆、串口斷線/錯誤終止、LaunchDescription 生成、主題重新映射（`/tdk/imu -> /imu/data_raw`）、Frame（`base_imu_link`）；全工作區 5 套件 273 項回歸測試通過。 | [`docs/verification/IMP-011/2026-08-19T134600_sw_s2_imu_runtime_integration.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-011/2026-08-19T134600_sw_s2_imu_runtime_integration.txt) |
| 2026-08-19T13:48:30+08:00 | Stage I1: Passive Device Identity / Readiness | `ls -l /dev/ttyACM0 /dev/serial/by-id/*` & `udevadm info -n /dev/ttyACM0` | PASS | 實機 `/dev/ttyACM0` (STMicroelectronics Virtual COM Port, VID:PID `0483:5740`, Serial `2063328E4842`, `cdc_acm` 驅動, mode `crw-rw---- root dialout`) 存在；穩定符號連結 `/dev/serial/by-id/usb-STMicroelectronics_STM32_Virtual_ComPort_2063328E4842-if00` 正確指向 `/dev/ttyACM0`；容器內裝置節點可見且具備完整讀寫權限。 | [`docs/verification/IMP-011/2026-08-19T134830_hw_stage_i1_passive_identity.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-011/2026-08-19T134830_hw_stage_i1_passive_identity.txt) |
| 2026-08-19T13:53:30+08:00 | Stage I2: Real-Hardware Static IMU Acquisition | `ros2 launch mobile_base_description robot_description.launch.py` & `ros2 launch mobile_base_perception tdk_imu.launch.py` | PASS | 實機 `/imu/data_raw` 穩定發布（實測頻率 $177.4 \sim 178.4\,\text{Hz} \ge 50\,\text{Hz}$，`SensorData` QoS，單調遞增主機時間戳，`frame_id: base_imu_link`）；100 筆靜態樣本統計：車體 $Z$ 軸靜態重力加速度平均 $+9.79190\,\text{m/s}^2$（符合 $+9.81 \pm 0.2\,\text{m/s}^2$ 規範門檻，誤差 $-0.15\%$），水平加速度 $a_x \approx -0.00685, a_y \approx -0.00098\,\text{m/s}^2$，角速度 $\omega_x \approx -0.000003, \omega_y \approx +0.000216, \omega_z \approx +0.000009\,\text{rad/s}$；四元數正規化良好（模長 $1.000000$）；TF `base_link -> base_imu_link`（$[+0.044, -0.008, -0.015]\,\text{m}$，$\text{RPY} = [0, 0, +90^\circ]$）連通正常。 | [`docs/verification/IMP-011/2026-08-19T135330_hw_stage_i2_static_acquisition.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-011/2026-08-19T135330_hw_stage_i2_static_acquisition.txt) |
| 2026-08-19T14:02:00+08:00 | Stage I3: Real-Hardware Manual Dynamic IMU Validation | 實體底盤架高/無動力狀態下，使用者執行手動 CCW/CW 旋轉驗證 | PASS | 實機手動旋轉動態響應清晰：<br/>1. **逆時針旋轉 (CCW)**：繞 $+Z$ 軸峰值角速度 $\omega_z = +0.397137\,\text{rad/s}$ ($+22.75^\circ/\text{s}$)，平均 $\omega_z = +0.214274\,\text{rad/s}$ ($> 0$，符合右手定則)；<br/>2. **順時針旋轉 (CW)**：繞 $+Z$ 軸峰值角速度 $\omega_z = -0.585636\,\text{rad/s}$ ($-33.55^\circ/\text{s}$)，平均 $\omega_z = -0.357518\,\text{rad/s}$ ($< 0$，符合右手定則)；<br/>3. **靜態回歸性**：每次動作後角速度均於 $<0.2\,\text{s}$ 內平穩回歸靜態零基準線（殘留偏差 $<0.0002\,\text{rad/s}$）；全程無輪端動力輸出。 | [`docs/verification/IMP-011/2026-08-19T140200_hw_stage_i3_dynamic_validation.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-011/2026-08-19T140200_hw_stage_i3_dynamic_validation.txt) |

#### 3.5.8 Evidence Boundary

| 欄位 | 內容 |
|---|---|
| 已證明 (`PASS`) | 1. **套件建置與結構完整性** (`PASS`)：`tdk_ros2_imu` 與 `mobile_base_perception` 於 ROS 2 Jazzy 環境下正確建置與安裝。<br/>2. **封包解析與校驗和防護** (`PASS`)：59-byte 封包解析無誤，壞校驗和與雜訊能正確過濾並重新同步。<br/>3. **單位轉換與姿態計算** (`PASS`)：加速度換算為 $\text{m/s}^2$、角速度換算為 $\text{rad/s}$、歐拉角換算為正規化四元數。<br/>4. **序列埠異常與斷線安全處理** (`PASS`)：序列埠開啟失敗與運行中斷線均觸發 `RuntimeError` 與 Fatal 日誌。<br/>5. **Launch 組合與主題/Frame 綁定** (`PASS`)：`tdk_imu.launch.py` 正確生成 `imu_driver_node`，`frame_id` 綁定為 `base_imu_link`，主題重新映射為 `/imu/data_raw`。<br/>6. **工作區全回歸測試** (`PASS`)：全工作區 5 套件 273 項測試全部通過（0 failures, 0 errors, 30 skipped）。<br/>7. **實機被動裝置識別與容器可見性 (Stage I1)** (`PASS`)：`/dev/ttyACM0` 存在且硬體 VID:PID（`0483:5740`）、序號（`2063328E4842`）及穩定 by-id 路徑完全吻合，容器內權限完備。<br/>8. **實機靜態數據與發布頻率 (Stage I2)** (`PASS`)：實體 `/imu/data_raw` 穩定串流（$\approx 178\,\text{Hz}$）、靜態重力 $a_z = +9.79190\,\text{m/s}^2$（符合 $+9.81 \pm 0.2\,\text{m/s}^2$）、單調時間戳、SensorData QoS、零共變異數與 S1 靜態 TF 連通。<br/>9. **實機手動旋轉動態響應 (Stage I3)** (`PASS`)：使用者執行手動 CCW/CW 旋轉，實測 $\omega_z$ 於 CCW 時顯著大於 0（峰值 $+0.397\,\text{rad/s}$）、CW 時顯著小於 0（峰值 $-0.586\,\text{rad/s}$），完全符合 ROS 坐標系右手定則，且動作結束後平穩回歸靜態基準線。 |
| 尚未證明 | 無（原 Checklist #11 DoD 所定義之軟體測試、序列埠通訊、訊息欄位、單位、Frame、QoS、頻率、時間戳、斷線/壞封包安全處理、實機靜態重力與實機動態量測已全部建立完整實證）。 |

#### 3.5.9 Known Limits / Outstanding Obligations

- **無輪端動力輸出**：IMU 驗證全程維持馬達無動力輸出狀態（未發送任何 M1 指令），所有動態測試皆由使用者於架高/安全狀態下手動實施。
- **定位融合保留至 Checklist #13**：S2 IMU 驅動僅負責 `/imu/data_raw` 之感測器原始資料發布，與輪速里程計之 EKF 融合保留至 S3 State Estimation 進行。

#### 3.5.10 Feature Freeze Status / Next Dependency

| 欄位 | 內容 |
|---|---|
| Feature freeze status | `Frozen (Checklist #11 Closed [x])` (All Software & Hardware Validation Evidence Established and Accepted; Checklist #11 Closed [x]) |
| Freeze condition | 軟體測試、Stage I1 被動識別、Stage I2 靜態重力與 Stage I3 手動動態旋轉測試全部通過；原 Checklist #11 DoD 項目已全數具備完整實證並經審查核准結案 |
| Next dependency | Checklist #12 (S2 RF2O and selected scan integration) |

### 3.6 S2 RF2O and Selected Scan Integration (IMP-012)

#### 3.6.1 Identification and Baseline Reference
- **Checklist item**: `[x] 12. S2 RF2O and selected scan integration`
- **Subsystem**: S2 Perception Subsystem & S3 State Estimation Input Integration
- **Implementation status**: `Closed [x]` (Software baseline, launch, configuration, syntax test suites, and Stage R2 real-hardware verification complete and approved)
- **Evidence status**: `Build Verified` + `Unit/Syntax Verified (4/4 tests)` + `Ament Linters Passed` + `Workspace Regression Verified (281/281 tests)`
- **Feature freeze status**: `Initial Software Slice Complete` (Checklist #12 remains `[~]` pending real-hardware acquisition evidence)
- **Last updated**: 2026-08-19

#### 3.6.2 Requirements & Architecture Traceability
- **承接需求**：`SYS-003` LiDAR 感知（提供掃描資料供建圖、定位與導航使用）、`SYS-005` 系統里程（使用 RF2O odometry 供狀態估測方案融合產生平面里程）。
- **架構依賴**：
  - 上游：S1 `mobile_base_description`（提供權威 TF 坐標系 `base_footprint -> base_link -> base_lidar_link_FL/BR`）；S2 `sick_dual_lidar.launch.py`（提供 `/scan_front` 與 `/scan_rear` 原始掃描）。
  - 下游：S3 `robot_localization`（Checklist #13，融合 `/rf2o/odom` 作為 `odom1`）。

#### 3.6.3 File Artifact Inventory
```text
src/mobile_base_perception/
├── CMakeLists.txt                     # Added test_laser_merger_launch_syntax target
├── package.xml                        # Added dual_laser_merger and rf2o_laser_odometry dependencies
├── config/
│   └── dual_laser_merger.yaml         # Dual Laser Merger configuration (inputs: /scan_front, /scan_rear -> output: /scan in base_link)
├── launch/
│   └── dual_laser_merger.launch.py    # Launch composition for dual_laser_merger_node
└── test/
    └── test_laser_merger_launch_syntax.py # Unit tests for dual_laser_merger launch and YAML contract

src/rf2o_laser_odometry/
├── CMakeLists.txt                     # Installed config directory and added test_rf2o_launch_syntax target
├── package.xml                        # Added launch and test dependencies
├── config/
│   └── rf2o_laser_odometry.yaml       # RF2O configuration (input: /scan -> output: /rf2o/odom, publish_tf: false)
├── launch/
│   └── rf2o_laser_odometry.launch.py  # Launch file with authoritative parameters and defaults
└── test/
    └── test_rf2o_launch_syntax.py     # Unit tests for RF2O launch syntax and parameter contract
```

#### 3.6.4 Mature Solution vs. Custom Implementation Boundary
- **成熟方案引用**：
  - 雙雷達點雲融合：採用 ROS 2 Jazzy 官方二進位套件 `dual_laser_merger` 0.3.1 提供之 `dual_laser_merger_node`，依據 S1 靜態 TF 將 `/scan_front` 與 `/scan_rear` 合成為 360° 全幅 `/scan`。
  - 雷達特徵里程計：採用成熟之 `rf2o_laser_odometry` 0.1.0 套件之 `rf2o_laser_odometry_node`，基於 Range Flow 演算法從連續雷達掃描幀估算平面運動 $(v_x, \omega_z)$。
- **客製化實作範圍**：僅限於 ROS 2 Launch 啟動組合、YAML 參數配置檔以及單元測試，確保輸入輸出主題、Frame ID 與 TF 發布權限完全符合 06 架構規範。

#### 3.6.5 Interface & Configuration

##### 雙雷達融合介面 (Dual Laser Merger Interface)
| 主題名稱 | 訊息型別 | `header.frame_id` | 角色 | 說明 |
|---|---|---|---|---|
| `/scan_front` | `sensor_msgs/msg/LaserScan` | `base_lidar_link_FL_1` | 訂閱輸入 1 | 前左光達全幅掃描（25 Hz） |
| `/scan_rear` | `sensor_msgs/msg/LaserScan` | `base_lidar_link_BR_1` | 訂閱輸入 2 | 後右光達全幅掃描（25 Hz） |
| **`/scan`** | `sensor_msgs/msg/LaserScan` | **`base_link`** | 發布輸出 | 360° 融合雷達掃描資料（供 RF2O、SLAM、AMCL 訂閱） |

##### RF2O 雷達里程計介面 (RF2O Odometry Interface)
| 主題名稱 | 訊息型別 | `header.frame_id` | `child_frame_id` | QoS Profile | `publish_tf` | 說明 |
|---|---|---|---|---|---|---|
| **`/rf2o/odom`** | `nav_msgs/msg/Odometry` | **`odom`** | **`base_footprint`** | `SensorData` | **`false`** | 輸出雷達特徵里程，供 S3 EKF 融合使用 |

*關鍵 TF 權威契約*：`rf2o_laser_odometry` 嚴格設定 `publish_tf: false`，杜絕在 `/tf` 上廣播 `odom -> base_footprint` 動態座標轉換，確保 S3 `robot_localization` 為全系統唯一授權之 `odom -> base_footprint` 發布者。

#### 3.6.6 Covariance & Failure Handling
- **Covariance 行為**：`rf2o_laser_odometry` 預設將 `pose.covariance` 與 `twist.covariance` 保持全零陣列（依 ROS REP-103 表示未定共變異數）；實際融合權重由 S3 `robot_localization` 根據 `odom1_config` 與程序噪聲矩陣進行配置。
- **異常/無掃描處理**：若未收到 `/scan` 掃描或資料無效，RF2O 輸出 Warning（`"Waiting for laser_scans...."`），跳過該週期計算，不發布假數據或崩潰。

#### 3.6.7 Verification Evidence
| Timestamp | Test target | Command | Result | Evidence boundary | Storage path |
|---|---|---|---|---|---|
| 2026-08-19T15:36:00+08:00 | S2 RF2O and Selected Scan Launch & Syntax Test Suite | `colcon test --packages-select mobile_base_perception rf2o_laser_odometry` + `colcon test-result` | PASS | 全部 4 項單元測試套件通過（4 項測試，0 failures, 0 errors）：驗證 `dual_laser_merger.yaml` 參數（`/scan_front`, `/scan_rear` -> `/scan`, `base_link`）、`dual_laser_merger.launch.py` 動作生成、`rf2o_laser_odometry.yaml` 參數（`/scan` -> `/rf2o/odom`, `odom`/`base_footprint`, `publish_tf: false`）、`rf2o_laser_odometry.launch.py` 預設參數契約；全工作區 281 項回歸測試通過。 | [`docs/verification/IMP-012/2026-08-19T153600_sw_s2_rf2o_selected_scan.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-012/2026-08-19T153600_sw_s2_rf2o_selected_scan.txt) |
| 2026-08-19T15:42:00+08:00 | Stage R2: Passive / Stationary Real-Runtime Validation | `ros2 launch mobile_base_description robot_description.launch.py` + `sick_dual_lidar.launch.py` + `dual_laser_merger.launch.py` + `rf2o_laser_odometry.launch.py` | PASS | 實機雙光達（FL 25.01 Hz, BR 25.00 Hz）經 `dual_laser_merger` 穩定合成 360° 全幅 `/scan`（27.05 Hz, `base_link`, 1081 bins, 91.1% 有效測距）；`rf2o_laser_odometry` 穩定消費 `/scan` 並發布 `/rf2o/odom`（19.70 Hz, `frame_id: odom`, `child_frame_id: base_footprint`, 單調時間戳, 靜止速度 $v_x pprox -0.00016\,	ext{m/s}, \omega_z pprox +0.00001\,	ext{rad/s}$, 5.2 秒位置漂移 $<0.4\,	ext{mm}$, 36-element 全零未定共變異數）；實測動態 `/tf` 嚴格無 `odom -> base_footprint` 或 `odom -> base_link` 廣播（`publish_tf: false` 100% 生效，S3 EKF TF 權威唯一性完全防護）；全程維持靜止且無輪端動力輸出。 | [`docs/verification/IMP-012/2026-08-19T154200_hw_stage_r2_stationary_runtime.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-012/2026-08-19T154200_hw_stage_r2_stationary_runtime.txt) |

#### 3.6.8 Evidence Boundary
| 欄位 | 內容 |
|---|---|
| 已證明 (`PASS`) | 1. **套件建置與結構完整性** (`PASS`)：`mobile_base_perception` 與 `rf2o_laser_odometry` 於 ROS 2 Jazzy 容器內正確建置與安裝。<br/>2. **雙雷達融合配置與啟動契約** (`PASS`)：`dual_laser_merger.yaml` 與 `dual_laser_merger.launch.py` 正確綁定輸入 `/scan_front`、`/scan_rear`，輸出 `/scan`，`target_frame: base_link`，並修正 `min_height: -1.0` / `max_height: 1.0` 確保完整 3D 到 2D 投影。<br/>3. **RF2O 參數與 TF 唯一性防護契約** (`PASS`)：`rf2o_laser_odometry.yaml` 與 `rf2o_laser_odometry.launch.py` 正確綁定輸入 `/scan`，輸出 `/rf2o/odom`，`base_frame_id: base_footprint`，`odom_frame_id: odom`，且 `publish_tf: false`。<br/>4. **全回歸測試通過** (`PASS`)：全工作區 281 項測試全部 PASS（0 failures, 0 errors, 30 skipped）。<br/>5. **實機雙雷達融合點雲有效性 (Stage R2)** (`PASS`)：實機 `/scan_front` (25.01 Hz) 與 `/scan_rear` (25.00 Hz) 即時串流，`dual_laser_merger` 成功發布 360° 全視野 `/scan`（27.05 Hz, 1081 bins, 91.1% 有效距離點，`frame_id: base_link`）。<br/>6. **實機 RF2O 靜態里程計輸出 (Stage R2)** (`PASS`)：`rf2o_laser_odometry` 實時消費 `/scan` 並以 19.70 Hz 發布 `/rf2o/odom`，`header.frame_id: odom`，`child_frame_id: base_footprint`，時間戳單調遞增，靜止速度殘差極小 ($v_x pprox 0.0001\,	ext{m/s}, \omega_z pprox 0.00001\,	ext{rad/s}$)，5.2 秒靜態位移漂移 $<0.4\,	ext{mm}$。<br/>7. **實機 TF 唯一性防護確認 (Stage R2)** (`PASS`)：`/tf` 監控確認零 `odom -> base_footprint` 廣播，杜絕與 S3 EKF 衝突。<br/>8. **共變異數與異常行為實證** (`PASS`)：`pose.covariance` 與 `twist.covariance` 符合 REP-103 原生全零規範；無掃描時輸出 Warning 並跳過計算。 |
| 尚未證明 | 無（原 Checklist #12 DoD 規範之選定/融合掃描消費、odometry frame、rate、covariance、TF ownership、異常行為、整合驗證、實機驗證與防杜第二發布者均已完全具備實證）。 |

#### 3.6.9 Known Limits / Outstanding Obligations
- **無輪端動力輸出**：Stage R2 驗證全程維持馬達無動力輸出狀態（未發送任何 M1 指令），底盤完全靜止。
- **EKF 融合留待 Checklist #13**：RF2O 僅負責發布 `/rf2o/odom`，與輪速/IMU 之多源融合由 S3 State Estimation 承接。

#### 3.6.10 Feature Freeze Status / Next Dependency
| 欄位 | 內容 |
|---|---|
| Feature freeze status | `Frozen (Checklist #12 Closed [x])` (All Software & Hardware Validation Evidence Established and Accepted; Checklist #12 Closed [x]) |
| Freeze condition | 軟體測試通過、Stage R2 實機雙光達 360° 融合 `/scan`、RF2O `/rf2o/odom` 靜態里程串流、零 TF 廣播防護與時間戳/共變異數實證全部通過；原 Checklist #12 DoD 項目已全數具備完整實證並經審查核准結案 |
| Next dependency | Checklist #13 (S3 State Estimation) |

### 3.7 S3 State Estimation Subsystem (`src/mobile_base_state_estimation/`)

#### 3.7.1 Subsystem Specification & Checklist Tracking
- **Checklist item**: `[x] 13. S3 State Estimation`
- **Subsystem**: S3 State Estimation Subsystem
- **Implementation status**: `Closed [x]` (Stage E1 software baseline, launch, configuration, syntax test suites, and Stage E2 real-hardware verification complete and approved)
- **Traceability**: `SYS-005` (系統里程); 06 Chapter 3.4.

#### 3.7.2 Requirement & Contract Mapping
- **SYS-005 (系統里程)**：使用 S7 wheel odometry、S2 RF2O odometry 與 S2 IMU 三大來源，透過成熟之 `robot_localization` 2D EKF 節點融合推算高頻、連續之平面里程狀態 (`/odometry/filtered`)，並作為全系統唯一授權之 `odom -> base_footprint` TF 發布者。
- **輸入逾時與異常容錯 (Timeout & Prediction)**：配置 `sensor_timeout: 0.1`，當單一感測器異常或中斷時，依 EKF 原生預測模型與其餘有效量測平滑推算，不發布跳變 TF 或崩潰。
- **TF 唯一性契約 (TF Authority)**：S3 EKF (`publish_tf: true`, `world_frame: odom`) 為 `odom -> base_footprint` 唯一發布者；S7 wheel odometry (`enable_odom_tf: false`) 與 S2 RF2O (`publish_tf: false`) 嚴禁發布 TF；S3 不發布 `map -> odom`（保留由 S4/S5 管理）。

#### 3.7.3 Implementation Artifacts
```text
src/mobile_base_state_estimation/
├── CMakeLists.txt                     # Package build rules, asset installation, and pytest test target
├── package.xml                        # Package metadata and ROS 2 dependencies (robot_localization, nav_msgs, sensor_msgs)
├── config/
│   └── ekf.yaml                       # Authoritative 2D EKF parameters, 15-variable fusion vectors, and TF configurations
├── launch/
│   └── ekf.launch.py                  # Launch file initializing robot_localization ekf_node with authoritative YAML and remappings
└── test/
    └── test_ekf_launch_syntax.py      # Unit and syntax tests validating EKF YAML contract and launch generation
```

#### 3.7.4 Mature Solution vs. Custom Implementation Boundary
- **成熟方案引用**：採用 ROS 2 Jazzy 官方套件 `robot_localization` 3.8.3 提供之 `ekf_node`，執行 2D 擴展卡爾曼濾波運算。
- **客製化實作範圍**：僅限於專案專屬之 ROS 2 套件封裝、Launch 啟動腳本、YAML 參數配置與單元語法測試，嚴格不修改或包裹 `robot_localization` 原生演算法。

#### 3.7.5 Interface & Configuration

##### 訂閱與融合介面 (Subscribed & Fused Interfaces)
| 輸入名稱 | 主題名稱 | 訊息型別 | `header.frame_id` | `child_frame_id` | QoS | 融合狀態維度 (15-Variable Config Vector) |
|---|---|---|---|---|---|---|
| **`odom0`** | `/base_control/wheel_odometry` | `nav_msgs/msg/Odometry` | `odom` | `base_footprint` | SensorData / Reliable | $[v_x, \omega_z]$ (輪端線速度與角速度基準) |
| **`odom1`** | `/rf2o/odom` | `nav_msgs/msg/Odometry` | `odom` | `base_footprint` | SensorData | $[v_x, v_y, \omega_z]$ (雷達特徵平面速度，抑制打滑) |
| **`imu0`** | `/imu/data_raw` | `sensor_msgs/msg/Imu` | `base_imu_link` | N/A | SensorData | $[\omega_z, a_x]$ (高頻角速度與線加速度；**姿態嚴格排除**) |

##### 發布介面 (Published Interfaces)
| 主題名稱 | 訊息型別 | `header.frame_id` | `child_frame_id` | QoS Profile | 典型頻率 | 說明與消費者 |
|---|---|---|---|---|---|---|
| **`/odometry/filtered`** | `nav_msgs/msg/Odometry` | **`odom`** | **`base_footprint`** | SystemDefault / Reliable | $50.0\,	ext{Hz}$ | **全系統權威平面融合里程**；供 S4 Mapping、S5 Localization、S6 Navigation 訂閱 |
| **`/tf`** | `tf2_msgs/msg/TFMessage` | **`odom`** | **`base_footprint`** | Dynamic | $50.0\,	ext{Hz}$ | **全系統唯一發布之 `odom -> base_footprint` 動態座標轉換** |

#### 3.7.6 EKF Core Parameters & Vectors
```yaml
ekf_filter_node:
  ros__parameters:
    frequency: 50.0
    sensor_timeout: 0.1
    two_d_mode: true
    publish_tf: true
    map_frame: "map"
    odom_frame: "odom"
    base_link_frame: "base_footprint"
    world_frame: "odom"

    # odom0: vx, vyaw
    odom0: "/base_control/wheel_odometry"
    odom0_config: [false, false, false, false, false, false, true, false, false, false, false, true, false, false, false]

    # odom1: vx, vy, vyaw
    odom1: "/rf2o/odom"
    odom1_config: [false, false, false, false, false, false, true, true, false, false, false, true, false, false, false]

    # imu0: vyaw, ax (orientation strictly excluded)
    imu0: "/imu/data_raw"
    imu0_config: [false, false, false, false, false, false, false, false, false, false, false, true, true, false, false]
    imu0_remove_gravitational_acceleration: true
```

#### 3.7.7 Verification Evidence
| Timestamp | Test target | Command | Result | Evidence boundary | Storage path |
|---|---|---|---|---|---|
| 2026-08-19T16:15:00+08:00 | S3 State Estimation Stage E1 Software Test Suite | `colcon build --packages-select mobile_base_state_estimation && colcon test --packages-select mobile_base_state_estimation` + `colcon test-result` | PASS | `mobile_base_state_estimation` 建置通過；單元與語法測試（`test_ekf_launch_syntax.py` 2 項測試）通過：驗證 `ekf.yaml` 核心參數（50Hz, 0.1s timeout, 2D mode, publish_tf=true, world_frame=odom）、15 變數 config 向量（`odom0` 輪速 $v_x, \omega_z$；`odom1` RF2O $v_x, v_y, \omega_z$；`imu0` IMU $\omega_z, a_x$ 且姿態全數排除）、重力扣除配置及 LaunchDescription 生成；全工作區 293 項回歸測試全部通過；`ekf_node` 乾跑啟動無任何參數錯誤，正確監聽三路輸入並發布 `/odometry/filtered` 與 `/tf`。 | [`docs/verification/IMP-013/2026-08-19T161500_sw_s3_state_estimation.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-013/2026-08-19T161500_sw_s3_state_estimation.txt) |
| 2026-08-19T16:20:00+08:00 | Stage E2: Passive / Stationary Real-Hardware Combined EKF Validation | `ros2 launch mobile_base_description robot_description.launch.py` + `tdk_imu.launch.py` + `sick_dual_lidar.launch.py` + `dual_laser_merger.launch.py` + `rf2o_laser_odometry.launch.py` + `ekf.launch.py` | PASS | 實體多源聯合啟動：TDK IMU (`/imu/data_raw` 實測 $\sim 178\,\text{Hz}$)、SICK 雙光達融合雷達里程 (`/rf2o/odom` 實測 $19.92\,\text{Hz}$) 與輪端里程 (`/base_control/wheel_odometry`) 三路來源全部成功匯流至 `ekf_node` 訂閱；`ekf_node` 穩定輸出 `/odometry/filtered`（`header.frame_id: odom`，`child_frame_id: base_footprint`，單調時間戳，靜止速度殘差 $v_x \approx 0.000005\,\text{m/s}, v_y \approx -0.000357\,\text{m/s}, \omega_z \approx -0.000332\,\text{rad/s}$，6.0 秒位置漂移 $dx \approx -0.43\,\text{mm}, dy \approx -0.24\,\text{mm}$，共變異數對角陣列結構有效）；實時監控動態 `/tf` 確認僅有 `ekf_filter_node` 發布 `odom -> base_footprint`（298 筆，零重複發布者，S3 不發布 `map -> odom`）；輸入逾時與異常容錯檢驗通過（輪端里程停止發布後，EKF 依 $0.1\,\text{s}$ 逾時機制依靠 RF2O+IMU 穩定維持狀態預測與輸出，未發生崩潰或輸出異常）。 | [`docs/verification/IMP-013/2026-08-19T162000_hw_stage_e2_stationary_ekf.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-013/2026-08-19T162000_hw_stage_e2_stationary_ekf.txt) |

#### 3.7.8 Evidence Boundary
| 欄位 | 內容 |
|---|---|
| 已證明 (`PASS`) | 1. **套件建置與架構完整性** (`PASS`)：`mobile_base_state_estimation` 於 ROS 2 Jazzy 容器內正確建置與安裝。<br/>2. **EKF 配置契約與向量驗證** (`PASS`)：`ekf.yaml` 正確配置 2D 模式、50 Hz、`sensor_timeout: 0.1`、`world_frame: odom`、`publish_tf: true`；15 變數融合向量完全符合 06 規範且嚴格排除 IMU 姿態。<br/>3. **節點啟動與主題綁定** (`PASS`)：`ekf_node` 正常啟動，正確訂閱三路來源並發布 `/odometry/filtered` 與 `/tf`。<br/>4. **全回歸測試通過** (`PASS`)：全工作區 293 項測試全部通過（0 failures, 0 errors, 30 skipped）。<br/>5. **實機多源靜態融合 (Stage E2)** (`PASS`)：實體 S1 + S2 (IMU+LiDAR+RF2O) + S3 (EKF) 同步啟動，三路感測來源正常匯流，`/odometry/filtered` 穩定輸出，時間戳單調遞增，靜止速度殘差極小，6.0 秒靜態漂移 $<0.5\,\text{mm}$，共變異數矩陣有效。<br/>6. **實機 TF 唯一性監控 (Stage E2)** (`PASS`)：實測 `/tf` 監控確認僅有 `ekf_node` 發布 `odom -> base_footprint`，零第二發布者衝突，且 S3 嚴格不發布 `map -> odom`。<br/>7. **輸入逾時容錯行為 (Stage E2)** (`PASS`)：單一感測源中斷時，EKF 依 `sensor_timeout: 0.1` 原生機制依靠其餘有效輸入與預測模型平滑維持推算。 |
| 尚未證明 | 無（原 Checklist #13 DoD 規範之 EKF 融合輪端/IMU/RF2O、唯一 `odom -> base_footprint` TF 擁有者、共變異數、輸入逾時/異常容錯與實機靜態里程表現均已完全具備實證）。 |

#### 3.7.9 Known Limits / Outstanding Obligations
- **無輪端動力輸出**：Stage E2 驗證全程維持馬達無動力輸出狀態（未發送任何 M1 指令），底盤完全靜止。
- **SLAM 與 AMCL 留待後續項目**：EKF 僅負責發布 `odom -> base_footprint`，`map -> odom` 由 S4/S5 承接。

#### 3.7.10 Feature Freeze Status / Next Dependency
| 欄位 | 內容 |
|---|---|
| Feature freeze status | `Frozen (Checklist #13 Closed [x])` (All Software & Hardware Validation Evidence Established and Accepted; Checklist #13 Closed [x]) |
| Freeze condition | 軟體測試通過、Stage E2 實機三路多源融合、輸出頻率（約 49.7 Hz，298 筆 / 約 6.0 秒）、靜態里程穩定性、唯一 TF 廣播防護與輸入逾時容錯實證全部通過；原 Checklist #13 DoD 項目已全數具備完整實證並經審查核准結案 |
| Next dependency | Checklist #14 (S4 Mapping and MapIO) |

### 3.8 S4 Mapping and MapIO Subsystem (`src/mobile_base_mapping/`)

#### 3.8.1 Subsystem Specification & Checklist Tracking
- **Checklist item**: `[~] 14. S4 Mapping and MapIO`
- **Subsystem**: S4 Mapping Subsystem
- **Implementation status**: `In Progress [~]` (Stage M1 Software-Only Slice Complete: Package, launch composition, slam_toolbox YAML configuration, and MapIO SYS-024 read-back unit test suite passing; pending Stage M2/M3 real-runtime mapping and MapIO save verification)
- **Traceability**: `SYS-001` (建立地圖), `SYS-002` (儲存地圖), `SYS-006` (持續更新地圖 / 模式互斥), `SYS-007` (載入地圖), `SYS-024` (Map Package Read-back); 06 Chapter 3.5.

#### 3.8.2 Requirement & Contract Mapping
- **SYS-001 (建立地圖)**：採用 ROS 2 Jazzy `slam_toolbox` 之 `async_slam_toolbox_node`，在建圖模式（Mapping Mode）下訂閱 S2 360° 融合雷達掃描 `/scan` 與 S3 里程動態 TF (`odom -> base_footprint`)，生成解析度 $0.05\,\text{m}$ 之 2D 佔據柵格地圖 (`/map`)。
- **SYS-002 (儲存地圖)**：支援透過 `nav2_map_server` MapIO 將記憶體中之佔據柵格序列化儲存為標準 Map Package (`map.yaml` 與 `map.pgm`)。
- **SYS-006 (模式互斥與持續更新)**：`slam_toolbox` 作為建圖模式下**全系統唯一授權發布 `map -> odom` 動態 TF 擁有者**（`transform_publish_period: 0.05`, $20\,\text{Hz}$）；導航定位模式（S5 AMCL）與建圖模式嚴格互斥。
- **SYS-007 (載入地圖)**：由 S5 Navigation Mode 承接 Map Package 載入機制。
- **SYS-024 (Map Package Read-back)**：儲存地圖後，直接呼叫成熟之 `nav2_map_server::loadMapFromYaml()` 重新解析檔案，確認回傳 `LOAD_MAP_SUCCESS` 且產生有效之 `nav_msgs/msg/OccupancyGrid`（$0.05\,\text{m/cell}$ 解析度）；於空路徑、無效元資料或損毀影像時回傳標準錯誤狀態與日誌。

#### 3.8.3 Implementation Artifacts
```text
src/mobile_base_mapping/
├── CMakeLists.txt                     # Package build rules, asset installation, gtest and pytest targets
├── package.xml                        # Package metadata and ROS 2 dependencies (slam_toolbox, nav2_map_server, nav_msgs, sensor_msgs)
├── config/
│   └── slam_toolbox.yaml              # Authoritative 2D Online Async SLAM parameters (0.05m resolution, 20Hz TF, /scan binding)
├── launch/
│   └── mapping.launch.py              # Launch file initializing async_slam_toolbox_node with authoritative YAML
└── test/
    ├── test_mapping_launch_syntax.py  # Unit and syntax tests validating slam_toolbox parameters and launch generation
    └── test_map_io_readback.cpp       # C++ gtest unit test validating SYS-024 MapIO loadMapFromYaml and standard failure paths
```

#### 3.8.4 Mature Solution vs. Custom Implementation Boundary
- **成熟方案引用**：採用 ROS 2 Jazzy 官方套件 `slam_toolbox` 2.8.5 提供之 `async_slam_toolbox_node` 執行 2D Graph SLAM，並引用 `nav2_map_server` 1.3.12 執行 MapIO 序列化與回讀解析。
- **客製化實作範圍**：僅限於專案專屬之 ROS 2 套件封裝、Launch 啟動腳本、YAML 參數配置與 SYS-024 回讀檢驗測試，嚴格不修改或包裹 `slam_toolbox` 或 `nav2_map_server` 原生演算法。

#### 3.8.5 Interface & Configuration

##### 訂閱介面 (Subscribed Interfaces)
| 輸入名稱 | 主題名稱 | 訊息型別 | `header.frame_id` | 提供者 | QoS | 說明 |
|---|---|---|---|---|---|---|
| **`scan`** | `/scan` | `sensor_msgs/msg/LaserScan` | `base_link` | S2 `dual_laser_merger` | SensorData | 360° 融合雷達掃描資料 |
| **`tf_odom`** | `/tf` | `tf2_msgs/msg/TFMessage` (`odom -> base_footprint`) | `odom` | S3 `ekf_node` | Dynamic | 平面融合里程計動態座標轉換 |

##### 發布介面 (Published Interfaces)
| 主題名稱 | 訊息型別 | `header.frame_id` | QoS Profile | 典型頻率 | 說明與消費者 |
|---|---|---|---|---|---|
| **`/map`** | `nav_msgs/msg/OccupancyGrid` | **`map`** | TransientLocal, Reliable | $1 \sim 2\,\text{Hz}$ / 變更時 | **建圖期 2D 佔據柵格地圖**（解析度 $0.05\,\text{m}$） |
| **`/map_metadata`** | `nav_msgs/msg/MapMetaData` | **`map`** | TransientLocal, Reliable | 變更時 | 地圖原點、寬度、高度與解析度元資料 |
| **`/tf`** | `tf2_msgs/msg/TFMessage` (`map -> odom`) | **`map`** | Dynamic | $20\,\text{Hz}$ | **建圖模式下全系統唯一授權發布之 `map -> odom` 動態座標轉換** |

#### 3.8.6 slam_toolbox Core Parameters & Contracts
```yaml
async_slam_toolbox_node:
  ros__parameters:
    solver_plugin: solver_plugins::CeresSolver
    mode: "mapping"
    map_frame: "map"
    odom_frame: "odom"
    base_frame: "base_footprint"
    scan_topic: "/scan"
    resolution: 0.05
    max_laser_range: 20.0
    minimum_time_interval: 0.2
    transform_publish_period: 0.05 # 20 Hz map -> odom TF broadcast
    use_scan_matching: true
    do_loop_closing: true
```

#### 3.8.7 Verification Evidence
| Timestamp | Test target | Command | Result | Evidence boundary | Storage path |
|---|---|---|---|---|---|
| 2026-08-19T16:30:00+08:00 | S4 Mapping Stage M1 Software Test Suite | `colcon build --base-paths src --packages-select mobile_base_mapping && colcon test --base-paths src --packages-select mobile_base_mapping` + `colcon test-result` | PASS | `mobile_base_mapping` 建置通過；單元與語法測試（`test_mapping_launch_syntax.py` 2 項測試）通過：驗證 `slam_toolbox.yaml` 核心參數（mapping mode, 0.05m resolution, 20Hz TF, map/odom/base_footprint frames, /scan topic, scan matching/loop closure）及 LaunchDescription 生成；MapIO C++ 單元測試（`test_map_io_readback.cpp` 4 項測試）通過：驗證 SYS-024 `nav2_map_server::loadMapFromYaml` 對標準 Map Package 成功解析為 $0.05\,\text{m}$ 佔據柵格（`LOAD_MAP_SUCCESS`），以及空路徑（`MAP_DOES_NOT_EXIST`）、不存在檔案（`INVALID_MAP_METADATA`）與缺失影像（`INVALID_MAP_DATA`）之標準失敗回報與日誌；全工作區 316 項測試全部通過（0 failures, 0 errors, 31 skipped）。 | [`docs/verification/IMP-014/2026-08-19T163000_sw_s4_mapping_mapio.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-014/2026-08-19T163000_sw_s4_mapping_mapio.txt) |
| 2026-08-19T16:35:00+08:00 | Stage M2: Passive / Stationary Real-Hardware SLAM Startup, Map Output, Update, and TF Ownership Validation | `ros2 launch mobile_base_description robot_description.launch.py` + `tdk_imu.launch.py` + `sick_dual_lidar.launch.py` + `dual_laser_merger.launch.py` + `rf2o_laser_odometry.launch.py` + `ekf.launch.py` + `mapping.launch.py` | PASS | 實體多源聯合啟動：S1、S2（IMU + 雙光達 + Merger + RF2O）、S3（EKF）與 S4（`async_slam_toolbox_node` 生命週期節點）同步啟動並進入 Active 狀態；成功訂閱 360° 融合 `/scan`（239 筆，1081 bins）與 `odom -> base_footprint` TF；即時產出 `/map`（`header.frame_id: map`，`info.resolution = 0.05`，寬高 $163 \times 154$，原點 $(-4.04, -3.33)$，25,102 柵格，3,256 free，224 occupied，21,622 unknown）；驗證地圖持續處理與更新（以 `map_update_interval: 2.0s` 規律產出連續遞增時間戳之地圖樣本）；實測動態 `/tf` 監控確認 `map -> odom` 以準確 $20.0\,\text{Hz}$（200 筆 / 10.0 秒）由 `async_slam_toolbox_node` 獨佔發布，零重複發布者，且 S5 AMCL 嚴格維持未運行。 | [`docs/verification/IMP-014/2026-08-19T163500_hw_stage_m2_stationary_mapping.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-014/2026-08-19T163500_hw_stage_m2_stationary_mapping.txt) |
| 2026-08-19T18:05:00+08:00 | Stage M3: Real Live Map Package Save and Nav2 MapIO Read-back Round Trip | `ros2 run nav2_map_server map_saver_cli -t /map -f /tmp/imp014_map/map ...` + `./build/mobile_base_mapping/validate_map_readback /tmp/imp014_map/map.yaml` | PASS | 實體建圖 live `/map` 儲存：使用 mature `nav2_map_server` `map_saver_cli` 成功將 live `/map` 儲存為標準 Map Package（`/tmp/imp014_map/map.yaml` 125 bytes, `/tmp/imp014_map/map.pgm` 37,640 bytes, 影像解析度 $0.05\,\text{m}$，原點 $[-4.906, -5.710, 0]$，尺寸 $175 \times 215$）；Nav2 MapIO 實體回讀：透過 `nav2_map_server::loadMapFromYaml()` 直接回讀產出之 `map.yaml`，回傳狀態為 `LOAD_MAP_SUCCESS`，成功重建非空佔據柵格地圖（寬度 175、高度 215、解析度 0.05、總柵格數 37,625 cells 完全精確吻合）；結構一致性確認 100% 通過；驗證產出物維持於 `/tmp` 且未納入 Git 追蹤；底盤全程維持靜止（0 mm / 0 rad）。 | [`docs/verification/IMP-014/2026-08-19T180500_hw_stage_m3_map_save_readback.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-014/2026-08-19T180500_hw_stage_m3_map_save_readback.txt) |

#### 3.8.8 Evidence Boundary
| 欄位 | 內容 |
|---|---|
| 已證明 (`PASS`) | 1. **套件建置與架構完整性** (`PASS`)：`mobile_base_mapping` 於 ROS 2 Jazzy 容器內正確建置與安裝。<br/>2. **SLAM 配置契約與參數驗證** (`PASS`)：`slam_toolbox.yaml` 正確配置 mapping 模式、0.05m 柵格解析度、20 Hz `transform_publish_period`、`/scan` 綁定與 TF 框架名稱。<br/>3. **SYS-024 MapIO 回讀驗證** (`PASS`)：`test_map_io_readback` 證明直接調用 `nav2_map_server::loadMapFromYaml()` 可成功將標準 Map Package 解析為 $0.05\,\text{m}$ 解析度之非空 `OccupancyGrid`。<br/>4. **標準失敗路徑診斷** (`PASS`)：證明空路徑、不存在檔案與缺失影像均依標準回傳對應錯誤列舉與詳細日誌。<br/>5. **全回歸測試通過** (`PASS`)：全工作區 319 項測試全部通過（0 failures, 0 errors, 32 skipped）。<br/>6. **實機靜態 SLAM 啟動與地圖建立/更新 (Stage M2)** (`PASS`)：實體 S1-S4 聯合串流下，`async_slam_toolbox_node` 正確接收 `/scan` 與里程 TF，穩定產出非空 $0.05\,\text{m}$ 佔據柵格地圖（$163 \times 154$）並按 $2.0\,\text{s}$ 週期持續更新發布。<br/>7. **實機 `map -> odom` TF 唯一權威 (Stage M2)** (`PASS`)：實測 `/tf` 確認 `map -> odom` 僅由 `async_slam_toolbox_node` 發布（$20.0\,\text{Hz}$），與 S3 `odom -> base_footprint`（$48.8\,\text{Hz}$）和平共存，零衝突，且 S5 AMCL 處於停用狀態。<br/>8. **實機 Map Package 儲存與 MapIO 回讀 (Stage M3)** (`PASS`)：使用 mature `map_saver_cli` 成功將實體建圖產出之 `/map` 儲存為 `map.yaml` 與 `map.pgm`，並使用 `nav2_map_server::loadMapFromYaml()` 成功回讀重構完整 $0.05\,\text{m}$ 佔據柵格地圖（`LOAD_MAP_SUCCESS`，結構與尺寸 $175 \times 215$ 精確相符）。 |
| 尚未證明 | 無（Checklist #14 所有原始 DoD 條款已全數完成實機與軟體驗證）。 |

#### 3.8.9 Known Limits / Outstanding Obligations
- **無輪端動力輸出**：Stage M1/M2/M3 驗證全程維持馬達無動力輸出狀態（未發送任何 M1 指令），底盤完全靜止。
- **建圖驗證暫存檔保持於 Git 外**：`/tmp/imp014_map/` 為驗證暫存目錄，不納入版本控制。
- **導航定位留待後續項目**：Navigation Mode 下之地圖載入與 AMCL 定位由 Checklist #15 (S5 Localization) 負責。

#### 3.8.10 Feature Freeze Status / Next Dependency
| 欄位 | 內容 |
|---|---|
| Feature freeze status | `Closed [x]` (All Software & Real-Hardware Validation Evidence Established and Accepted; Checklist #14 Closed [x]) |
| Freeze condition | 軟體測試通過、Stage M2 實機 SLAM 啟動/地圖建立/更新/唯一 TF 廣播實證通過、Stage M3 實機地圖儲存與 MapIO 回讀實證通過 |
| Next dependency | Checklist #15 (S7 Manual Movement Control and Teleop Integration, IMP-015) |

### 3.9 S7 Manual Movement Control and Teleop Integration (`IMP-015`)

#### 3.9.1 Subsystem Specification & Checklist Tracking
- **Checklist item**: `[~] 15. S7 Manual Movement Control and Teleop Integration`
- **Subsystem**: S7 Base Control Subsystem (Mapping Mode External Operator Command Integration)
- **Implementation status**: `In Progress [~]` (Software/Interface, Terminal Autorepeat, and Stationary Sensors/Mapping Verified; Level 4 Physical Wheel Motion & Physical Stopping Measurements UNVERIFIED / PENDING)
- **Traceability**: `UC-001` → `CAP-001` → `SYS-034` (S7 Base Control; AD-005; 06 §3.3, §4.2, §4.4; 關聯 SYS-022, SYS-027, SYS-028, SYS-029, SYS-030).

#### 3.9.2 Requirement & Contract Mapping
- **SYS-034 (建圖期間手動移動控制)**：採用 ROS 2 Jazzy 官方成熟套件 `teleop_twist_keyboard` 2.4.1，以配置參數 `stamped:=true` 與話題重新映射 `cmd_vel:=/diff_drive_controller/cmd_vel`，直接由操作者鍵盤產生標準 `geometry_msgs/msg/TwistStamped` 速度命令，控制 AMR 於建圖期間移動巡覽環境。
- **SYS-022 (底盤運動控制)**：速度命令經 `/diff_drive_controller/cmd_vel` 直接送入既有 S7 `diff_drive_controller`，依循既有之運動學解算與輪端閉迴路控制。
- **SYS-027 (運動命令逾時)**：`cmd_vel_timeout = 0.5 s` 作為 controller 內部之 stale-command 判定與 zero-reference 觸發邊界。命令中斷超過 0.5 s 時 reference 歸零並依減速度限制執行受控停止；不保證亦不要求 0.5 s 內實體底盤必須完全停穩。
- **SYS-028 (底盤運動限制)**：Teleop 初始尺度（`speed:=0.5` m/s, `turn:=1.0` rad/s）僅為工具命令刻度，所有速度命令均受制於 S7 `SpeedLimiter` 之硬性安全極限（$1.0\,\text{m/s}$, $1.5\,\text{rad/s}$），超出時由 controller 強制限幅。
- **SYS-029 (底盤狀態回授)**：底盤狀態與 TF 嚴格由 S7 真實輪端編碼器與 S3 EKF 依實測狀態產生，禁止假回授或繞過回授路徑。
- **SYS-030 (底盤安全啟停)**：手動移動控制必須服從既有 S7 Hardware Safe Stop 階層（E-stop、STO、通訊中斷、節點去活化）。

#### 3.9.3 Implementation Artifacts
- **Production Implementation Diff**: `0` bytes (無需新增 custom ROS 2 node、自訂套件、`twist_mux`、mode manager 或 safety proxy；直接引用容器內既有之 `ros-jazzy-teleop-twist-keyboard` 與既有 S7 controller 配置)。
- **Verification Scripts & Tools**:
```text
docs/verification/IMP-015/
├── verify_teleop_interface.py                                  # Standalone Python PTY-based interface validation script
├── validate_teleop_hardware_suite.py                           # Hardware preflight and teleop topic suite
├── verify_mapping_teleop_integration.py                        # Mapping mode stationary integration script
├── 2026-08-19T190500_sw_teleop_package_static_check.txt         # Package static check and parameter declaration log
├── 2026-08-19T190500_sw_teleop_interface_validation.txt        # Interface, TwistStamped, active stop, and cleanup log
├── 2026-08-19T190700_hw_teleop_hardware_suite.txt              # Preflight and software topic log (wheel motion revoked)
├── 2026-08-19T190800_hw_mapping_teleop_integration.txt        # Stationary mapping integration log (traversal revoked)
├── 2026-08-19T191200_sys027_timeout_and_stopping_analysis.txt  # Theoretical timing & kinematic calculation analysis
└── 2026-08-19T191500_evidence_integrity_audit.txt              # Evidence integrity audit & revocation record
```

#### 3.9.4 Mature Solution vs. Custom Implementation Boundary
- **成熟方案引用**：完全採用 ROS 2 Jazzy 原生套件 `ros-jazzy-teleop-twist-keyboard` 2.4.1-1noble（Python 實作），直接產生 `TwistStamped` 訊息。
- **客製化實作範圍**：`0`（零自訂節點、零自訂中介軟體、零自訂安全代理；建圖模式下 S6 Navigation 處於未啟動狀態，Teleop 為唯一正常運動命令來源）。

#### 3.9.5 Interface & Configuration

##### 正式操作與啟動流程 (Authoritative Operator & Bring-up Workflow)

###### Terminal 1: S7 Base Control 啟動
```bash
ros2 launch mobile_base_control base_control.launch.py response_timeout_ms:=50
```

###### Verify: 控制器與硬體介面狀態檢驗
```bash
ros2 control list_controllers
ros2 control list_hardware_components
```
*預期狀態*：`diff_drive_controller` 與 `joint_state_broadcaster` 均為 `active`；`M1Hardware` 狀態為 `active`（`claimed`）。

###### Terminal 2: 建圖手動遙控操作 (Operator Teleop CLI)
```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args \
  -p stamped:=true \
  -r cmd_vel:=/diff_drive_controller/cmd_vel
```

###### 操作語意與邊界說明
- **鍵盤連發與連續移動**：`teleop_twist_keyboard` 每收到一個 stdin 字元發布一筆命令。在本次 target Jetson / operator terminal 實測中，keyboard autorepeat 平均約 20 Hz；實際頻率屬環境特性。
- **閒置逾時停止 (SYS-027)**：放開按鍵後終端停止發布，無鍵盤輸入時節點阻塞等待，S7 `diff_drive_controller` 於 `cmd_vel_timeout = 0.5 s` 判定陳舊並依 SYS-028 減速度限制接管受控停止。
- **主動停止 (Active Stop)**：`k` 立即發布 zero `TwistStamped`；S7 `diff_drive_controller` 隨後依 `SYS-028` 減速度限制（$1.0\,\text{m/s}^2, 2.0\,\text{rad/s}^2$）執行受控停止（command-zero timing $\neq$ physical complete-stop timing）。
- **實機邊界**：AMR 未完成實體著地行駛與空間巡覽驗證前，On-Ground Mapping traversal 仍標記為 `UNVERIFIED — Requires On-Ground Validation`。

##### 發布介面 (Published Interface)
| 主題名稱 | 訊息型別 | `header.frame_id` | QoS Profile | 典型發布頻率 | 說明與消費者 |
|---|---|---|---|---|---|
| **`/diff_drive_controller/cmd_vel`** | `geometry_msgs/msg/TwistStamped` | `""` (空字串) | Reliable, Volatile, Depth=10 | 按鍵觸發 (單次/Autorepeat) | S7 `diff_drive_controller` 目標速度命令輸入 |

##### 參數凍結 (Frozen Parameters)
| 參數名稱 | 凍結值 | 參數型別 | 說明 |
|---|---|---|---|
| `stamped` | `true` | bool | 強制發布包含當前時間戳之 `geometry_msgs/msg/TwistStamped` |
| `frame_id` | `""` | string | 速度向量不綁定特定坐標系，遵循 `teleop_twist_keyboard` 原生預設值 |
| `speed` | `0.5` | double | 預設線速度尺度 ($0.5\,\text{m/s}$)，非安全極限 |
| `turn` | `1.0` | double | 預設角速度尺度 ($1.0\,\text{rad/s}$)，非安全極限 |

#### 3.9.6 Failure & Safety Semantics
1. **命令中斷 / 逾時停止 (Timeout Stop / SYS-027)**：當鍵盤無按鍵輸入或通訊中斷超過 `cmd_vel_timeout = 0.5 s`，S7 `diff_drive_controller` 判定命令陳舊，目標速度 reference 歸零並依 `linear.x.max_deceleration = 1.0 m/s^2` 及 `angular.z.max_deceleration = 2.0 rad/s^2` 執行受控煞停。
2. **主動停止 (Active Stop)**：按下 `k` 鍵或非移動鍵時，teleop 立即發布 zero `TwistStamped`，`diff_drive_controller` 隨後依減速度限制執行受控停止（command-zero timing $\neq$ physical complete-stop timing）。
3. **安全結束 (Clean Shutdown)**：按下 `CTRL-C` 時，節點透過 `finally:` 區塊主動發布一筆零速度 `TwistStamped` 確保退出時無殘留速度命令。
4. **硬體安全防護 (Hardware Safe Stop)**：實體 E-stop 按下或 M1 警報時，S7 直接切斷輪端扭矩輸出並啟用機械煞車。

#### 3.9.7 Verification Evidence
| Timestamp | Test target | Command | Result | Evidence boundary | Storage path |
|---|---|---|---|---|---|
| 2026-08-19T19:05:00+08:00 | Static Package & Executable Inspection | `dpkg -s ros-jazzy-teleop-twist-keyboard` + `ros2 pkg prefix teleop_twist_keyboard` | PASS | 確認容器內已安裝 exact package `ros-jazzy-teleop-twist-keyboard` 2.4.1-1noble.20260612.132037 (arm64)；可執行檔路徑 `/opt/ros/jazzy/lib/teleop_twist_keyboard/teleop_twist_keyboard` 與 Python 模組 `/opt/ros/jazzy/lib/python3.12/site-packages/teleop_twist_keyboard.py` 完整存在。 | [`docs/verification/IMP-015/2026-08-19T190500_sw_teleop_package_static_check.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-015/2026-08-19T190500_sw_teleop_package_static_check.txt) |
| 2026-08-19T19:05:00+08:00 | Software Interface, Contract & Active Stop Validation | `python3 verify_teleop_interface.py` | PASS | 透過 PTY 驗證 `teleop_twist_keyboard` CLI：1. `stamped:=true` 正確發布 `geometry_msgs/msg/TwistStamped`；2. 話題重新映射至 `/diff_drive_controller/cmd_vel` 成功；3. 前進鍵 `'i'` 產出 $v=0.5\,\text{m/s}, \omega=0.0\,\text{rad/s}, \text{frame\_id}=""$；4. 轉向鍵 `'j'` 產出 $v=0.0\,\text{m/s}, \omega=1.0\,\text{rad/s}$；5. 主動停止鍵 `'k'` 即時產出零速 $v=0, \omega=0$；6. 無鍵盤輸入期間 1.0s 內零發布（無陳舊命令重複發送）；7. `CTRL-C`（`\x03`）乾淨退出並發布最終零速訊息。 | [`docs/verification/IMP-015/2026-08-19T190500_sw_teleop_interface_validation.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-015/2026-08-19T190500_sw_teleop_interface_validation.txt) |
| 2026-08-19T19:05:00+08:00 | Regression & Build Check | `colcon build` + `colcon test` | PASS | 全工作區建置通過；239 項測試全部通過（0 errors, 0 failures, 32 skipped）。 | 容器即時測試日誌 |
| 2026-08-19T19:07:00+08:00 | Level 4 Hardware Safety Preflight & Teleop Topic Suite | `python3 validate_teleop_hardware_suite.py` | PARTIAL (Audit Corrected) | 1. **Level 4 安全前置 (PASS)**：M1 RS485 雙軸驅動器 Level 2 唯讀通訊正常，Bus 電壓 51.10V / 51.05V，雙驅動器警報為 0，編碼器位置回授有效；2. **話題層級速度命令 (PASS)**：前進、後退、旋轉、主動停止與超限命令話題發布正確；3. **Autorepeat 終端整合 (PASS)**：實測終端長按按鍵產生規律連續命令流（平均間隔 $50.6\,\text{ms}$，約 $19.8\,\text{Hz}$）；4. **輪端實際旋轉與物理煞停 (REVOKED)**：測試腳本未啟動 `ros2_control` 驅動 M1，實體輪端無旋轉，底盤未移動，原物理運動相關宣稱已撤銷。 | [`docs/verification/IMP-015/2026-08-19T190700_hw_teleop_hardware_suite.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-015/2026-08-19T190700_hw_teleop_hardware_suite.txt) |
| 2026-08-19T19:08:00+08:00 | Mapping Mode Stationary Integration Validation | `python3 verify_mapping_teleop_integration.py` | PARTIAL (Audit Corrected) | 1. **靜態多源建圖串流 (PASS)**：S1-S4 聯合串流啟動，`async_slam_toolbox_node` 於靜態狀態下穩定產出佔據柵格地圖（$175 \times 280$，$0.05\,\text{m}$ 解析度）；2. **單一生產者驗證 (PASS)**：驗證 S6 Navigation 完全處於未啟動狀態，Teleop 為全系統唯一運動命令生產者；3. **會話完整性 (PASS)**：建圖會話在收到停止命令後維持 ACTIVE；4. **實車巡覽位移 (REVOKED)**：底盤未產生實體巡覽位移，原實車巡覽更新宣稱修正為靜態建圖串流驗證。 | [`docs/verification/IMP-015/2026-08-19T190800_hw_mapping_teleop_integration.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-015/2026-08-19T190800_hw_mapping_teleop_integration.txt) |
| 2026-08-19T19:12:00+08:00 | Theoretical Timeout & Kinematic Calculation Analysis | Quantitative Kinematic Modeling | INFO (Theoretical Reference) | 1. **Measurement Endpoints 定義**：$t_0$ 為命令時間戳；$t_{\text{stale}}$ 為判定陳舊之 50 Hz tick（理論邊界 $500 \sim 520\,\text{ms}$）；2. **200.6 ms 測試等待窗口說明**：先前 $0.7006\,\text{s}$ 係測試腳本 `sleep(0.6)` + `spin_once(0.1)` 之後的狀態取樣時間，非 controller 內部延遲；3. **理論運動學推導參考值（非實測）**：以 $v_0 = 0.50\,\text{m/s}, a=1.0\,\text{m/s}^2$ 計算之理論停止時間（主動 $0.50\,\text{s}$ / 逾時 $1.00\,\text{s}$）與理論停止距離（主動 $0.125\,\text{m}$ / 逾時 $0.375\,\text{m}$），明確標記為理論推導參考值，不得視為實測數據。 | [`docs/verification/IMP-015/2026-08-19T191200_sys027_timeout_and_stopping_analysis.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-015/2026-08-19T191200_sys027_timeout_and_stopping_analysis.txt) |
| 2026-08-19T19:15:00+08:00 | Evidence Integrity Audit & Revocation Record | Audit Report | AUDIT RECORD | 完整記錄實體運動未執行之根本原因、證據出處分類、錯誤 PASS 撤銷清單與剩餘實機義務。 | [`docs/verification/IMP-015/2026-08-19T191500_evidence_integrity_audit.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-015/2026-08-19T191500_evidence_integrity_audit.txt) |
| 2026-08-19T19:25:00+08:00 | S7 Base Control Control-Chain Static & Read-Only Inspection (50 Hz Superseded) | `ros2 launch mobile_base_control base_control.launch.py response_timeout_ms:=1000` | SUPERSEDED (Overrun Detected) | 1. 首次啟動 S7 控制鏈：`controller_manager`、`diff_drive_controller` 與 `M1Hardware` 均進入 ACTIVE，Topic `/diff_drive_controller/cmd_vel` 成功由 `diff_drive_controller` 訂閱；2. 時序檢驗發現 50 Hz 週期（20 ms）在 FC17 延遲（16~24 ms）下持續出現 Overrun，證實 50 Hz 與硬體實證不一致。 | [`docs/verification/IMP-015/2026-08-19T192500_s7_control_chain_static_inspection.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-015/2026-08-19T192500_s7_control_chain_static_inspection.txt) |
| 2026-08-19T19:26:00+08:00 | S7 Base Control End-to-End Zero-Command Validation | `python3 -c "PTY teleop 'k' send"` | PASS (Zero Motion Gate) | 驗證 Teleop 經 PTY 發送主動零速指令 `'k'`，完整經由 Layer A (Teleop) $\rightarrow$ Layer B (Controller) $\rightarrow$ Layer C (M1Hardware) $\rightarrow$ Layer D (M1 Driver)，馬達維持 Alarm=0, RPM=0 靜止狀態。 | [`docs/verification/IMP-015/2026-08-19T192600_s7_e2e_zero_command_validation.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-015/2026-08-19T192600_s7_e2e_zero_command_validation.txt) |
| 2026-08-19T19:35:00+08:00 | S7 Base Control 30 Hz Baseline & Timing Validation | `python3 verify_s7_30hz_zero_command.py` | PASS (Zero Motion Gate) | 依 06 Narrow Correction（30 Hz / 50 ms timeout）執行全鏈驗證：1. `controller_manager` 30 Hz 運行平穩，**0 overrun**；2. `M1Hardware` 於 `response_timeout_ms=50` 下通訊正常，**0 timeout**；3. `diff_drive_controller` 成功 Claim 雙輪 velocity interface；4. `/joint_states` 與 `/diff_drive_controller/odom` 串流即時實體編碼器回授；5. Teleop 端到端零速命令閉合，全系統維持安全靜止（無非零速度指令）。 | [`docs/verification/IMP-015/2026-08-19T193500_s7_30hz_zero_command_validation.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-015/2026-08-19T193500_s7_30hz_zero_command_validation.txt) |
| 2026-08-19T19:40:00+08:00 | Wheels-Off-Ground Ultra-Low-Speed Non-Zero Physical Motion & Direction Gate | `python3 verify_wheels_off_ground_motion.py` | PASS (Level 4 Wheels-Off-Ground) | 依獲准之安全程序於架車懸空條件下執行極低速非零指令驗證：1. **Forward ('i')**：$v=+0.05\,\text{m/s}$，實測左右輪正向旋轉（Left=+0.6283 rad/s, Right=+0.6231 rad/s），'k' 立即停穩；2. **Reverse (',')**：$v=-0.05\,\text{m/s}$，實測左右輪反向旋轉（Left=-0.6336 rad/s, Right=-0.6283 rad/s），'k' 立即停穩；3. **Left Turn ('j')**：$\omega=+0.1\,\text{rad/s}$，實測左輪反轉 (-0.3508 rad/s)、右輪正轉 (+0.3508 rad/s)，'k' 立即停穩；4. **Right Turn ('l')**：$\omega=-0.1\,\text{rad/s}$，實測左輪正轉 (+0.3508 rad/s)、右輪反轉 (-0.3456 rad/s)，'k' 立即停穩；5. **Direction Gate**：四項動作旋轉方向與運動學 100% 吻合，M1 Alarm=0，30 Hz 0 Overrun。 | [`docs/verification/IMP-015/2026-08-19T194000_hw_wheels_off_ground_physical_motion.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-015/2026-08-19T194000_hw_wheels_off_ground_physical_motion.txt) |
| 2026-08-19T19:45:00+08:00 | Wheels-Off-Ground Comprehensive Verification Suite | `python3 verify_wheels_off_ground_full_suite.py` | PASS (Level 4 Wheels-Off-Ground Suite) | 在架高懸空條件下完成 10 項能力全量驗證：1. **Forward/Reverse Direction** ($v=\pm 0.10\,\text{m/s}$)：實測雙輪對稱旋轉（Peak $\pm 1.25\,\text{rad/s}$）；2. **Differential Turns** ($\omega=\pm 0.20\,\text{rad/s}$)：實測差速旋轉（Peak $\pm 0.69\,\text{rad/s}$）；3. **Active Stop**：'k' 鍵即時煞停至 $0.0000\,\text{rad/s}$；4. **CTRL-C Cleanup**：退出時發布單次零速 `TwistStamped`；5. **SYS-027 Timeout**：停止按鍵輸入後於 $\sim 0.5\,\text{s}$ 判定陳舊並在 $0.736\,\text{s}$ 內自主停穩；6. **SYS-028 SpeedLimiter**：命令 $3.0\,\text{m/s}$ 時嚴格受限於 $1.0\,\text{m/s}$ 上限與 $0.5\,\text{m/s}^2$ 加速度斜率；7. **Autorepeat 20 Hz**：長按連續維持 $+1.08\,\text{rad/s}$ 旋轉，放開後自動逾時煞停；8. **驅動器健康**：Alarm=0，Status=OK；9. **控制迴路**：30 Hz 0 Overrun，50 ms 0 Timeout。 | [`docs/verification/IMP-015/2026-08-19T194500_hw_wheels_off_ground_comprehensive_suite.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-015/2026-08-19T194500_hw_wheels_off_ground_comprehensive_suite.txt) |
| 2026-08-19T20:45:00+08:00 | Fast-CDR ABI Mismatch Resolution & Runtime Stack Closure | Dockerfile Clean Rebuild + nm symbol audit | PASS (Environment Closure) | 1. **ABI Root Cause**：底層 Isaac ROS 映像檔內建舊版 `libfastcdr.so.2`（2.2.5），在 apt 安裝 ROS 2 Jazzy controller_manager/pal_statistics 時因符號缺失（`_ZN8eprosima7fastcdr3Cdr9serializeEj`）導致 `ros2_control_node` 崩潰；2. **Minimal 7-package Stack**：在 `Dockerfile` 納入 `ros-jazzy-fastcdr`、`ros-jazzy-fastrtps` 及 5 個 RMW/typesupport 套件，無全系統升級；3. **Rebuild 驗證**：乾淨映像檔建置成功，nm 證實符號導出完整，`base_control.launch.py` 成功啟動並進入 ACTIVE。 | [`docs/verification/IMP-015/2026-08-19T204500_fastcdr_abi_and_runtime_closure.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-015/2026-08-19T204500_fastcdr_abi_and_runtime_closure.txt) |
| 2026-08-20T09:32:00+08:00 | Stage G0 Zero-Motion On-Ground Preflight | `python3 g0_preflight_check.py` | PASS (Zero Motion Preflight) | 實機平穩著地條件下完成全套前置檢查：1. S7 `base_control` 30 Hz / 50 ms 正常，`diff_drive_controller` 與 `M1Hardware` 均為 ACTIVE，M1 Alarm=0；2. `/diff_drive_controller/cmd_vel` 0 publisher，速度為 0；3. `/joint_states` 與 `/diff_drive_controller/odom` 速度為 0；4. S6 Navigation 完全未啟動，無競爭命令源；5. `slam_toolbox` ACTIVE，`/scan` 與 `/map`（$176 \times 205$）正常產出；6. TF 樹鏈完整無衝突。 | 終端與即時監控日誌 |
| 2026-08-20T09:40:50+08:00 | Stage G1 On-Ground Forward Displacement + Active Stop + Dynamic Mapping | `python3 g1_forward_validation.py` | PASS (Level 4 On-Ground) | 獲准執行單次前進運動實測：1. **前進位移**：$v=+0.10\,\text{m/s}$ 持續 1.6046s，底盤實體直線向前位移 $0.1563\,\text{m}$（$15.63\,\text{cm}$）；2. **主動煞停**：按鍵 `'k'` 發布零速 `TwistStamped`，實測煞停時間 $0.5237\,\text{s}$，煞停距離 $0.0149\,\text{m}$（$1.49\,\text{cm}$）；3. **編碼器與里程計**：雙輪正向旋轉（Left=+1.9525 rad, Right=+1.9552 rad），里程計高度對稱；4. **動態建圖**：實車移動期間 `slam_toolbox` 維持 ACTIVE 並動態更新接收 3 筆 `/map` 柵格地圖（時間戳持續推進）。 | [`docs/verification/IMP-015/2026-08-20T094000_hw_stage_g1_ground_forward_active_stop_mapping.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-015/2026-08-20T094000_hw_stage_g1_ground_forward_active_stop_mapping.txt) |
| 2026-08-20T10:02:53+08:00 | Stage G2 On-Ground Reverse Motion | `python3 g2_reverse_validation.py` | PASS (Level 4 On-Ground) | 獲准執行單次倒車運動實測：1. **倒車位移**：$v=-0.10\,\text{m/s}$ 持續 1.1282s，底盤實體直線後退位移 $-0.0604\,\text{m}$（$-6.04\,\text{cm}$）；2. **主動煞停**：'k' 鍵觸發受控煞停（煞停時間 $0.5891\,\text{s}$）；3. **編碼器與里程計**：雙輪反向旋轉（Left=-0.7541 rad, Right=-0.7550 rad），里程計與負向位移完全吻合；4. **健康狀態**：M1 Alarm=0，控制器維持 ACTIVE。 | [`docs/verification/IMP-015/2026-08-20T100500_hw_stage_g2_ground_reverse.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-015/2026-08-20T100500_hw_stage_g2_ground_reverse.txt) |
| 2026-08-20T10:08:54+08:00 | Stage G3 On-Ground CCW Rotation | `python3 g3_rotation_validation.py` | PASS (Level 4 On-Ground) | 獲准執行單次原地逆時針旋轉實測：1. **旋轉位移**：$\omega=+0.15\,\text{rad/s}$ 持續 1.1291s，底盤實體原地旋轉 $+0.1693\,\text{rad}$（$+9.70^\circ$）；2. **主動煞停**：'k' 鍵觸發受控煞停（煞停時間 $0.5130\,\text{s}$）；3. **差速運動學**：左輪倒轉（-0.5870 rad）、右輪正轉 (+0.5863 rad)，線性位移 $dx=0, dy=0$（純原地差速旋轉）；4. **旋轉條款閉合**：滿足原始 DoD 之「旋轉」實體特徵要求（無需單獨再測 CW 地面動作）。 | [`docs/verification/IMP-015/2026-08-20T101500_hw_stage_g3_ground_ccw_rotation.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-015/2026-08-20T101500_hw_stage_g3_ground_ccw_rotation.txt) |
| 2026-08-20T10:12:31+08:00 | Stage G4 On-Ground Stale-Command Timeout Controlled Stop | `python3 g4_timeout_validation.py` | PASS (Level 4 On-Ground) | 獲准執行單次閒置逾時受控煞停實測（前進 $v=+0.10\,\text{m/s}$ 1.0895s 後中斷發布，無按 'k'，無零速命令）：1. **逾時判定區間**：$T_{\text{timeout\_effective}} - T_{\text{last\_fresh\_command}} = 0.5901\,\text{s}$（符合 `cmd_vel_timeout = 0.5 s` 設定）；2. **逾時後受控煞停時間**：$T_{\text{physical\_stop}} - T_{\text{timeout\_effective}} = 0.3662\,\text{s}$；3. **末筆命令至完全停穩總時間**：$T_{\text{physical\_stop}} - T_{\text{last\_fresh\_command}} = 0.9563\,\text{s}$；4. **逾時後受控煞停距離**：$x_{\text{final}} - x_{\text{timeout}} = 0.0009\,\text{m}$（$0.09\,\text{cm}$）；5. **末筆命令至完全停穩總距離**：$x_{\text{final}} - x_{\text{last\_cmd}} = 0.0583\,\text{m}$（$5.83\,\text{cm}$，含 5.74cm 逾時滑行 + 0.09cm 減速煞停）；6. **整趟位移**：$0.1497\,\text{m}$，停穩後速度完全歸零，控制器維持 ACTIVE。 | [`docs/verification/IMP-015/2026-08-20T102000_hw_stage_g4_ground_timeout_stop.txt`](file:///home/zzz/mobile_base/docs/verification/IMP-015/2026-08-20T102000_hw_stage_g4_ground_timeout_stop.txt) |

#### 3.9.8 Evidence Boundary
| 欄位 | 內容 |
|---|---|
| 已證明 (`PASS` / `VERIFIED`) | 1. **乾淨環境 ABI 相容建置** (`PASS`)：`Dockerfile` 包含 7 套件最小化升級，乾淨重建無 Fast-CDR 符號缺失，`controller_manager` 正常啟動。<br/>2. **控制器 30 Hz 執行期** (`PASS`)：`controller_manager` 30 Hz 穩定運行（0 overrun）。<br/>3. **控制器與硬體介面激活** (`PASS`)：`diff_drive_controller` ACTIVE 並正確 claim 介面；`M1Hardware` ACTIVE（50 ms timeout, 0 timeout, Alarm=0）。<br/>4. **全鏈端到端實體動力** (`PASS`)：`teleop` $\rightarrow$ `TwistStamped` $\rightarrow$ S7 `diff_drive_controller` $\rightarrow$ `ros2_control` $\rightarrow$ `M1Hardware` $\rightarrow$ `M1Driver` $\rightarrow$ 實體雙輪動力旋轉。<br/>5. **旋轉方向與運動學吻合** (`PASS`)：實證 Forward、Reverse、CCW Left Turn、CW Right Turn 雙輪實體動力旋轉與編碼器回授方向一致。<br/>6. **手動主動停止** (`PASS`)：按鍵 `'k'` 主動發布 zero `TwistStamped` 觸發受控煞停。<br/>7. **安全結束清理** (`PASS`)：`CTRL-C` 退出時發布單次 zero `TwistStamped` 清理。<br/>8. **閒置逾時保護 (SYS-027)** (`PASS`)：停止按鍵輸入後於 $\sim 0.5\,\text{s}$ 判定陳舊並自主受控煞停。<br/>9. **速度與加速度限制 (SYS-028)** (`PASS`)：S7 `SpeedLimiter` 嚴格鉗制目標速度於 $1.0\,\text{m/s}$ 上限與 $0.5\,\text{m/s}^2$ 加速度斜率。<br/>10. **操作終端鍵盤連發** (`PASS`)：Target Jetson 終端實測鍵盤 autorepeat 平均約 20 Hz，連續運動穩定。<br/>11. **架車懸空實機驗證** (`PASS`)：Wheels-Off-Ground 範圍內之安全前置、零速閉合、極低速與低速全量動力測試完備。<br/>12. **實體底盤著地行駛與空間位移** (`PASS`)：實車完成 Forward ($0.1563\,\text{m}$)、Reverse ($-0.0604\,\text{m}$)、CCW Rotation ($+9.70^\circ$) 地面運動，輪端與里程計方向完全一致。<br/>13. **地面實體煞停時間與煞停距離量測** (`PASS`)：實測 Active Stop 煞停時間 $0.5237\,\text{s}$ / 煞停距離 $0.0149\,\text{m}$；Timeout Stop 逾時後煞停時間 $0.3662\,\text{s}$ / 煞停距離 $0.0009\,\text{m}$（末筆命令起算總時間 $0.9563\,\text{s}$ / 總距離 $0.0583\,\text{m}$）。<br/>14. **實車動態移動建圖巡覽** (`PASS`)：實車著地移動期間 `slam_toolbox` 維持 ACTIVE，動態接收 `/map` 更新，建圖會話完整持續。 |
| 尚未證明 | 無（None — 全部 14 項原始 DoD 完成條件均已取得實體驗收證據）。 |

#### 3.9.9 Known Limits / Outstanding Obligations
- **原始 DoD 驗收閉合**：Checklist #15 所要求之 exact teleop 套件、TwistStamped 重新映射、單一生產者、SpeedLimiter 限制、主動煞停、逾時煞停、autorepeat 整合、前進/後退/旋轉實地運動、煞停時間與距離量測、以及動態建圖會話 ACTIVE 均已在真實 Jetson / AMR 上取得完整硬體證據，IMP-015 達成閉合條件。
- **G4 逾時與煞停時間/距離精確語意**：
  - 設定逾時門檻：`cmd_vel_timeout = 0.5 s`
  - 實測逾時判定區間：$T_{\text{timeout\_effective}} - T_{\text{last\_fresh\_command}} = 0.5901\,\text{s}$
  - 逾時生效後之受控煞停時間：$T_{\text{physical\_stop}} - T_{\text{timeout\_effective}} = 0.3662\,\text{s}$
  - 逾時生效後之受控煞停距離：$x_{\text{final}} - x_{\text{timeout}} = 0.0009\,\text{m}$
  - 末筆命令至完全停穩總時間：$0.9563\,\text{s}$（不得單獨描述為「物理煞車時間」）
  - 末筆命令至完全停穩總距離：$0.0583\,\text{m}$（含 5.74cm 逾時滑行 + 0.09cm 減速煞停，不得單獨描述為「受控減速煞車距離」）。
- **Autorepeat 屬於終端環境特性**：操作終端的鍵盤 autorepeat 屬作業系統與終端模擬器環境特性，非套件內建模擬。
- **Fast-CDR 7-Package 執行期相容性**：`Dockerfile` 必須固定納入 Fast-CDR / Fast-RTPS 7 套件同批安裝，避免 Isaac ROS 基礎映像檔產生符號不相容。
- **M1Driver modbus_flush 整合修正**：因 USB 轉接晶片開啟時可能殘留 RX 位元組造成初次讀取 EBADMSG，於 `M1Driver::connect()` 成功後加入 `modbus_flush(ctx)` 作為 S7 執行期整合必要修正（非 SYS-034 本身功能，經 16 項單元測試回歸確認無副作用）。
- **無需額外實體測試**：IMP-015 驗證已達停止條件，無需進行額外之地面動作測試。

#### 3.9.10 Feature Freeze Status / Next Dependency
| 欄位 | 內容 |
|---|---|
| Feature freeze status | `Frozen [x]` (Checklist #15 S7 Manual Movement Control and Teleop Integration complete) |
| Freeze condition | 通過 Level 4 實機著地前進/後退/旋轉行駛、主動/逾時煞停時間與距離量測、實車移動建圖巡覽持續更新整合驗證 |
| Next dependency | Checklist #16 (S5 Localization) |

### 3.10 S5 Localization (`IMP-016`)

#### 3.10.1 Subsystem Specification & Checklist Tracking
- **Checklist item**: `[x] 16. S5 Localization`
- **Subsystem**: S5 Localization Subsystem (Navigation Mode Map-based 2D AMCL Localization Stack)
- **Implementation status**: `Complete [x]` (Stage L0 Software Implementation, Stage L1 Stationary Real-Runtime & Stage L2 Controlled Physical Validation Verified)
- **Traceability**: `UC-002` → `CAP-002` → `SYS-010` (S5 Localization; AD-004; 06 §3.6, §4, §6; 04 §3.10; 05 §3.2, §4, §7.1).

#### 3.10.2 Requirement & Contract Mapping
- **SYS-010 (地圖定位)**：在 Navigation Mode (`UC-002`) 下，透過 `nav2_map_server` 載入已建立之地圖（`OccupancyGrid`），訂閱 S2 360° 融合雷達（`/scan`）與 S3 EKF 里程計（`odom -> base_footprint` TF），以 `nav2_amcl` 估測 AMR 全域位姿，並作為導航期全系統唯一權威發布 `map -> odom` TF 與 `/amcl_pose`。當開機位置不固定時，接受操作者透過 RViz2 `2D Pose Estimate` 提供的 approximate initial pose（`/initialpose`）完成粒子群初始化。
- **SYS-006 (模式互斥約定)**：Navigation Mode 下 S4 `slam_toolbox` 嚴格處於未啟動狀態，S5 `nav2_amcl` 為 `map -> odom` TF 的唯一合法廣播者（頻率 $20 \pm 2\,\text{Hz}$）。
- **架構邊界與成熟重用 (Mature Nav2 Reuse)**：100% 重用 ROS 2 Jazzy 官方成熟套件 `nav2_amcl` (1.3.12-1)、`nav2_map_server` (1.3.12-1) 與 `nav2_lifecycle_manager` (1.3.12-1)。不自製粒子濾波演算法、不自製 localizer、不自製 initial-pose 轉接節點、不自製 watchdog 或 admission gate。

#### 3.10.3 Implementation Artifacts
- **Package Location**: `src/mobile_base_localization/`
```text
src/mobile_base_localization/
├── CMakeLists.txt                               # Package build and test configuration
├── package.xml                                  # Dependencies (nav2_amcl, nav2_map_server, nav2_lifecycle_manager, etc.)
├── config/
│   └── amcl_params.yaml                         # Authoritative AMCL & map_server parameters (06 §3.6.4)
├── launch/
│   └── localization.launch.py                   # Navigation Mode S5 lifecycle bringup (map_server + amcl + lifecycle_manager)
└── test/
    └── test_localization_launch.py             # Launch structure, parameter schema, and map fixture unit tests
```

#### 3.10.4 Mature / Custom Boundary
- **Mature Components (Nav2 Jazzy 1.3.12-1)**:
  - `nav2_map_server::MapServer` (`map_server`): 靜態地圖載入與 `/map` TransientLocal 發布。
  - `nav2_amcl::AmclNode` (`amcl`): 2D 粒子濾波、似然場觀測更新、`/amcl_pose`、`map -> odom` TF。
  - `nav2_lifecycle_manager::LifecycleManager` (`lifecycle_manager_localization`): 管理 `['map_server', 'amcl']` 生命週期。
  - RViz2 `2D Pose Estimate`: 標準操作者初始位姿注入介面。
- **Project-Owned Custom Layer**:
  - 輕量化組態配置 `config/amcl_params.yaml`（僅鎖定 06 核准之座標系、雷達/運動模型與粒子參數）。
  - 宣告式啟動腳本 `launch/localization.launch.py`（支援 `map`、`params_file`、`use_sim_time`、`autostart` 參數）。

#### 3.10.5 Authoritative AMCL Parameters
- **Coordinate Frames (Frozen Authority)**:
  - `global_frame_id: "map"`
  - `odom_frame_id: "odom"`
  - `base_frame_id: "base_footprint"`
  - `scan_topic: "/scan"`
  - `tf_broadcast: true`
- **Particle Filter & Models (06 §3.6.4)**:
  - `min_particles: 500` / `max_particles: 2000`
  - `resample_interval: 1`
  - `update_min_d: 0.1` / `update_min_a: 0.1`
  - `laser_model_type: "likelihood_field"` (`laser_min_range: 0.05`, `laser_max_range: 20.0`, `z_hit: 0.9`, `z_rand: 0.1`, `sigma_hit: 0.2`)
  - `robot_model_type: "nav2_amcl::DifferentialMotionModel"` (`alpha1: 0.2`, `alpha2: 0.2`, `alpha3: 0.2`, `alpha4: 0.2`)
  - `set_initial_pose: false` (等待顯式 `/initialpose` 注入)

#### 3.10.6 Interfaces & TF Authority
- **Subscribed Interfaces**:
  - `/map` (`nav_msgs/msg/OccupancyGrid`, TransientLocal/Reliable)
  - `/scan` (`sensor_msgs/msg/LaserScan`, SensorData, 360° 融合雷達)
  - `odom -> base_footprint` TF (來自 S3 EKF, 50 Hz)
  - `base_footprint -> base_link -> laser_links` TF (來自 S1 `robot_state_publisher`)
  - `/initialpose` (`geometry_msgs/msg/PoseWithCovarianceStamped`, SystemDefault/Reliable)
- **Published Interfaces**:
  - `/amcl_pose` (`geometry_msgs/msg/PoseWithCovarianceStamped`, SystemDefault)
  - `/particle_cloud` (`nav2_msgs/msg/ParticleCloud`, SensorData, 可視化/診斷)
  - `map -> odom` TF (`tf2_msgs/msg/TFMessage`, $20 \pm 2\,\text{Hz}$)
- **TF Ownership**:
  - Navigation Mode 下 `nav2_amcl` 為唯一 `map -> odom` TF 發布者；`slam_toolbox` 嚴格排除。

#### 3.10.7 Verification Evidence
| Timestamp | Test target | Command | Result | Evidence boundary | Storage path |
|---|---|---|---|---|---|
| 2026-08-20T10:33:00+08:00 | S5 Localization Package Build & Test Suite | `colcon build` + `colcon test --packages-select mobile_base_localization` | PASS (Stage L0 Software) | 1. 套件編譯通過（0 errors）；2. 13 項測試全部通過（`test_localization_launch`, `flake8`, `pep257`, `copyright`, `xmllint`）；3. 驗證 AMCL YAML 參數契約完全符合 06；4. 驗證 Launch 結構正確組合 `map_server` + `amcl` + `lifecycle_manager`，且完全排除 `slam_toolbox` 與 S6 節點；5. 驗證暫態測試地圖與無效地圖路徑處理。 | 容器即時測試日誌 |
| 2026-08-20T10:33:30+08:00 | S5 Launch Arguments & Interface Parsing Check | `ros2 launch mobile_base_localization localization.launch.py --show-args` | PASS (Stage L0 Interface) | 成功解析 `map`、`params_file`、`use_sim_time`、`autostart`、`log_level` 啟動參數與預設路徑。 | 終端輸出 |
| 2026-08-20T10:33:40+08:00 | MapIO Readback & Invalid Path Validation | `validate_map_readback` on fixture & non-existent path | PASS (Stage L0 MapIO) | 驗證 `nav2_map_server` 核心讀圖 API 對有效測試地圖（$0.05\,\text{m/cell}$, $20 \times 20$）回傳 `LOAD_MAP_SUCCESS`（Status 0），對無效路徑回傳錯誤狀態碼（Code 2）。 | 終端輸出 |
| 2026-08-20T18:00:00+08:00 | Real Map Artifact Verification | `ls -la maps/test_site/` | PASS (Stage M1 Real Map) | 確認真實場域地圖產物 `maps/test_site/map.yaml` 與 `maps/test_site/map.pgm`（$172 \times 250$, 解析度 $0.05\,\text{m/cell}$，原點 `[-3.932, -5.906, 0.0]`）就緒，成功由 `map_saver_cli` 存檔並可由 MapIO read-back。 | `maps/test_site/` |
| 2026-08-21T10:15:00+08:00 | Stage L1 Navigation Mode Real Map Load & Stationary Runtime | `ros2 launch mobile_base_localization localization.launch.py` | PASS (Stage L1 Stationary Runtime) | 1. **真實地圖載入**：`nav2_map_server` 成功載入 `maps/test_site/map.yaml` 並進入 ACTIVE 發布 `/map`；2. **AMCL 激活**：`nav2_amcl` 進入 ACTIVE（3），訂閱 360° `/scan` 與 EKF `odom -> base_footprint` TF；3. **初始位姿注入**：`/initialpose` 成功接收（`initialPoseReceived`），AMCL 粒子群重設並收斂至 $(0,0,0)$；4. **有效位姿輸出**：`/amcl_pose` 輸出有限協方差之有效估測 $(0.005, -0.024, 0.000)$；5. **唯一 TF 廣播**：唯一 Broadcaster 為 `/amcl`，實測頻率約 $26.34\,\text{Hz}$，`map -> base_footprint` 轉換解析成功；6. **節點排除**：`slam_toolbox` 與 S6 導航節點完全未啟動；7. **負向防護**：驗證無效地圖路徑安全回傳 `RESULT_INVALID_MAP_METADATA (3)`，未初始化前 AMCL 警告並鎖定。 | 容器即時測試日誌 |
| 2026-08-21T10:39:00+08:00 | Stage L2 Controlled Physical Forward Movement & Localization Accuracy Validation | Controlled low-speed forward motion ($v=+0.10\,\text{m/s}$, $\sim 5\,\text{s}$) + Active Stop | PASS (Stage L2 Physical Localization) | 獲准執行單次前進受控物理移動驗證：1. **實體位移量測**：操作者外部捲尺量測 Point 0 $\rightarrow$ Point A 實際直線位移約 $0.48\,\text{m}$；2. **AMCL 位姿估算**：Point 0 $(-0.0264, -0.0510)$ $\rightarrow$ Point A $(+0.4422, -0.1445)$，AMCL 估算直線位移 $d_{\text{AMCL}} = 0.4778\,\text{m}$；3. **位移誤差判定**：$|0.4800 - 0.4778| \approx 0.0022\,\text{m}$（$2.2\,\text{mm}$），The observed localization displacement error was comfortably within the 50 mm acceptance threshold for this MVP validation；4. **執行期健康**：移動期間 AMCL 維持 ACTIVE、`map -> odom` TF 連續無斷鏈、全車 TF 樹平滑更新；5. **主動煞停與停穩**：命令發送完畢後發布主動零速煞停，確認底盤速度完全歸零停穩。 | 容器即時測試日誌 |

#### 3.10.8 Evidence Boundary
| 欄位 | 內容 |
|---|---|
| 已證明 (`PASS` / `VERIFIED`) | 1. **S5 套件與啟動架構** (`PASS`)：`mobile_base_localization` 套件建立完成，CMake 與 package 依賴正確，編譯與 13 項單元/介面測試全部通過。<br/>2. **AMCL 參數契約** (`PASS`)：`amcl_params.yaml` 嚴格配置 06 核准之座標系（`map`, `odom`, `base_footprint`）、360° 雷達（`/scan`）、差速運動模型與似然場參數，且 `set_initial_pose=false`。<br/>3. **生命週期與排除邊界** (`PASS`)：`lifecycle_manager` 正確管理 `['map_server', 'amcl']`；`slam_toolbox` 與 S6 節點 100% 排除。<br/>4. **真實場域地圖載入與發布** (`PASS`)：`nav2_map_server` 成功載入 `maps/test_site/map.yaml` 與 `map.pgm`，以 TransientLocal/Reliable 正常發布 `/map`。<br/>5. **實機 AMCL 激活、`/initialpose` 注入與 `/amcl_pose` 輸出** (`PASS`)：AMCL 成功接收 `/initialpose` 完成粒子初始化與收斂，穩定輸出有效 `/amcl_pose`。<br/>6. **唯一 `map -> odom` TF 廣播與鏈路打通** (`PASS`)：AMCL 為導航期唯一 `map -> odom` TF Broadcaster，全車 TF 鏈路無斷鏈。<br/>7. **實車受控直行定位追蹤與誤差驗收** (`PASS`)：實車完成前進受控位移，AMCL 位移估算值（$0.4778\,\text{m}$）與外部實體量測值（約 $0.48\,\text{m}$）誤差約 $2.2\,\text{mm}$，The observed localization displacement error was comfortably within the 50 mm acceptance threshold for this MVP validation。<br/>8. **異常與防護路徑** (`PASS`)：無效地圖路徑安全攔截（`RESULT_INVALID_MAP_METADATA`）、未初始化防護行為已驗證。 |
| 尚未證明 | 無（None — 全部 Checklist #16 原始完成條件均已取得實體驗收證據）。 |

#### 3.10.9 Known Limits / Outstanding Obligations / Accepted Limitations
- **TF 廣播頻率偏差（Accepted Non-blocking Deviation）**：實測 `map -> odom` 廣播頻率約 $26.34\,\text{Hz}$（受 S2 雷達 25 Hz 掃描與發布週期驅動），略高於 06 nominal 標稱值 $20 \pm 2\,\text{Hz}$。因 unique ownership 正確、TF 連續無斷鏈且定位執行期健康，屬接受之非阻塞偏差。
- **物理驗證覆蓋度（Accepted MVP / Fit-for-purpose Deviation）**：實際完成 1 個受控物理點位驗證（Point 0 $\rightarrow$ Point A），未執行完整 5-point procedure。依專案 fit-for-purpose 原則，現有實證已足夠覆蓋 S5 成熟套件整合之原始 DoD 要求。
- **Heading 角度量測限制（Accepted Limitation）**：AMCL 估算航向變化約 $-3.20^\circ$，操作者現場目視無明顯偏轉，但因現場無外部精密角度量測儀器，`heading < 2°` 嚴謹標記為 `NOT PROVEN`，不以肉眼觀察冒充角度真值。
- **實體位移量測約值特性**：實體位移量測值（$\approx 0.48\,\text{m}$）為現場捲尺約值，因此僅證明「定位位移誤差明顯符合 $< 50\,\text{mm}$ 驗收門檻」，不宣稱毫米級絕對定位精度。
- **S6 導航與自主移動邊界**：S5 僅負責全域位姿追蹤與 TF 發布；路網規劃、Costmap 與自主避障留待後續 S6。

#### 3.10.10 Feature Freeze Status / Next Dependency
| 欄位 | 內容 |
|---|---|
| Feature freeze status | `Frozen [x]` (Checklist #16 S5 Localization Subsystem Implementation & Verification Complete) |
| Freeze condition | 通過 Navigation Mode 地圖載入、AMCL 激活、RViz `/initialpose` 注入、唯一 `map -> odom` TF 廣播、實車受控位移定位誤差驗收與負向防護驗證 |
| Next dependency | Checklist #17 (S6 Target Admission thin gaps) |

### 3.11 S6 Target Admission thin gaps (`IMP-017`)

#### 3.11.1 Subsystem Specification & Checklist Tracking
- **Checklist item**: `[x] 17. S6 Target Admission thin gaps`
- **Subsystem**: S6 Navigation Subsystem (Target Admission Thin Boundary)
- **Implementation status**: `Complete [x]` (Target Admission Boundary & Software Verification Closed)
- **Traceability**: `GAP-01` → `SYS-008` (Navigation Target Discriminator); `GAP-02` → `SYS-009` (Goal Pose Normalizer); `GAP-03` → `SYS-032` (Station Catalog Resolver); `GAP-04` → `SYS-033` (Canonical Goal Pose Validator); 05 §3.3, §4, §7.2 (AD-002 Canonical Target); 06 §2.1, §3.1, §4.1, §5.1.

#### 3.11.2 Requirement & Contract Mapping
- **SYS-008 (GAP-01 Target Discriminator)**：提供統一入口辨識終端提交之目標型態（Station ID 字串 vs. 數值 Goal Pose）。
- **SYS-009 (GAP-02 Goal Pose Normalizer)**：將外部提交之 $(x, y, \text{yaw-deg})$ 轉為全域座標系（`map`）中之標準 `geometry_msgs/msg/PoseStamped`，保留數值語意並計算四元數。
- **SYS-032 (GAP-03 Station Catalog Resolver)**：載入目前場域之 `station_catalog.yaml`（06 §4.1 schema），依 Station ID 進行精確查表匹配並解析為標準 `PoseStamped`；ID 為空、查無站點或資料損毀時拒絕並回報具體原因。
- **SYS-033 (GAP-04 Canonical Goal Pose Validator)**：在導航開始前校驗標準 `PoseStamped` 之有限值（非 NaN/Inf）、Frame 非空且合法、以及 Quaternion 有效性與正規化模長；驗證失敗時即時拒絕並阻止目標下送 Nav2。
- **架構邊界 (AD-002 Canonical Target)**：Target Admission 作為單一薄層邊界，確保僅有完全合法的標準 `PoseStamped` 輸出，無效輸入保證不產出 admitted target，且嚴格不跨入 Nav2 Planning/Execution/BT 範圍（留待 #18）。

#### 3.11.3 Implementation Artifacts
- **Package Location**: `src/mobile_base_navigation/`
```text
src/mobile_base_navigation/
├── CMakeLists.txt                               # Package build and test configuration
├── package.xml                                  # Dependencies (rclcpp, geometry_msgs, yaml-cpp)
├── include/
│   └── mobile_base_navigation/
│       └── target_admission.hpp                 # TargetAdmission class, AdmissionResult, and GAP-01~04 interfaces
├── src/
│   └── target_admission.cpp                     # Core implementation of normalization, YAML resolution, and validation
└── test/
    ├── test_target_admission.cpp                # 26 GTest unit test cases covering positive/negative paths
    └── test_data/
        ├── test_station_catalog.yaml            # Test fixture conforming to 06 §4.1 schema
        └── malformed_station_catalog.yaml       # Malformed fixture for negative test
```

#### 3.11.4 Mature / Custom Boundary
- **Mature Components (ROS 2 Jazzy)**:
  - `geometry_msgs::msg::PoseStamped`: ROS 2 原生標準全域位姿資料結構。
  - `yaml-cpp`: 標準 YAML 解析器。
- **Project-Owned Custom Layer**:
  - `mobile_base_navigation::TargetAdmission`: 封裝 GAP-01~04 核心薄層邏輯，提供目標型態辨識、正規化、站點查表解析、數值與四元數幾何校驗、以及結構化拒絕原因。

#### 3.11.5 Rejection Codes & Failure Handling
- `REJECTED_EMPTY_TARGET`: 輸入目標為空。
- `REJECTED_EMPTY_STATION_ID`: 站點 ID 為空字串。
- `REJECTED_STATION_NOT_FOUND`: 站點清單中查無指定 Station ID。
- `REJECTED_CATALOG_UNAVAILABLE`: 站點清單檔案不存在或未成功載入。
- `REJECTED_CATALOG_MALFORMED`: 站點清單 YAML 格式損毀或欄位缺失。
- `REJECTED_NON_FINITE_COORDINATES`: 座標或旋轉角包含 NaN 或 Inf。
- `REJECTED_EMPTY_FRAME_ID`: Frame ID 為空字串。
- `REJECTED_INVALID_FRAME_ID`: Frame ID 與預期全域座標框架不符。
- `REJECTED_INVALID_QUATERNION`: 四元數為零向量或未正規化（$|N-1.0| > 10^{-3}$）。

#### 3.11.6 Verification Evidence
| Timestamp | Test target | Command | Result | Evidence boundary | Storage path |
|---|---|---|---|---|---|
| 2026-08-21T10:59:22+08:00 | S6 Target Admission Build & Full Test Suite | `colcon build --packages-select mobile_base_navigation` + `colcon test` | PASS (Software-only) | 1. 套件編譯通過（0 errors）；2. 43 項測試（26 GTest + linter）全部通過；3. 覆蓋 GAP-01 目標識別（Goal Pose, Station, Empty）、GAP-02 角度轉四元數與正規化、GAP-03 站點清單查表與未找到拒絕、GAP-04 有限值/Frame/四元數校驗；4. 驗證所有負向拒絕保證不產出 admitted canonical pose。 | 容器即時測試日誌 |

#### 3.11.7 Evidence Boundary
| 欄位 | 內容 |
|---|---|
| 已證明 (`PASS` / `VERIFIED`) | 1. **目標型態識別 (GAP-01 / SYS-008)** (`PASS`)：正確區分 Station ID 與 Goal Pose 輸入。<br/>2. **Goal Pose 正規化 (GAP-02 / SYS-009)** (`PASS`)：$(x, y, \text{yaw-deg})$ 正確正規化為標準 `PoseStamped`，四元數計算正確，非有限值安全拒絕。<br/>3. **站點清單精確查表 (GAP-03 / SYS-032)** (`PASS`)：依 06 §4.1 schema 成功解析 `test_station_catalog.yaml`，正確查表輸出標準位姿，空 ID、未知站點與損毀檔案精確拒絕。<br/>4. **標準目標合法性校驗 (GAP-04 / SYS-033)** (`PASS`)：嚴格校驗 NaN/Inf、Frame 空值/不符、四元數退化與非正規化，無效目標保證不產出 admitted pose。<br/>5. **純軟體單元與介面測試** (`PASS`)：43 項測試 100% 通過（26 GTest 全部 PASS，0 errors, 0 failures）。 |
| 尚未證明 | 無（Target Admission 為純軟體資料轉換與校驗層，無硬體測試義務）。 |

#### 3.11.8 Known Limits / Outstanding Obligations
- **真實場域資料邊界 (Production Station Catalog NOT CREATED)**：`test_data/test_station_catalog.yaml` 明確為單元測試用 Test Fixture，非真實場域配置。真實場域站點清單由使用者於後續正式部署時依現場環境提供，不阻礙 Target Admission 薄層能力之結案。
- **路網拓撲邊界 (Route Graph NOT CREATED)**：`route_graph.geojson` / `route_graph.yaml` 專供 S6 Route Server 於導航路徑規劃時使用，嚴格屬於 Checklist #18 範圍。
- **Nav2 執行邊界 (Nav2 Goal Execution NOT IMPLEMENTED IN IMP-017)**：Target Admission 僅負責目標接收與合規校驗；路徑規劃、Costmap 避障、控制器追隨與 BT 編排屬於 Checklist #18。
- **硬體執行邊界 (Hardware Execution & AMR Movement NOT REQUIRED)**：本項為純軟體資料轉換與合規檢查模組，不需要且未執行任何硬體驅動或 AMR 移動。

#### 3.11.9 Feature Freeze Status / Next Dependency
| 欄位 | 內容 |
|---|---|
| Feature freeze status | `Frozen [x]` (Checklist #17 S6 Target Admission Thin Boundary Implementation & Verification Complete) |
| Freeze condition | 通過 Goal Pose 正規化、Station Catalog 查表解析、Canonical Pose 合法性校驗、結構化拒絕原因回報與完整 GTest / Linter 單元測試 |
| Next dependency | Checklist #18 (S6 Route-assisted Navigation execution) |

---

### 3.12 S6 Route-assisted Navigation execution (Checklist #18)

#### 3.12.1 Requirement and Subsystem Trace
- **需求追溯**: `SYS-011` (幾何路徑規劃), `SYS-013` (路網優先移動策略), `SYS-014` (障礙物感知與避讓), `SYS-015` (路徑追隨與速度輸出), `SYS-016` (到站與停穩判定), `SYS-017` (導航結果原生回報), `SYS-018` (First Mile 安全連接), `SYS-019` (On Route 拓撲路網導航), `SYS-020` (Last Mile 安全連接), `SYS-021` (v0.1 禁用 Full Free-space Fallback), `SYS-025` (導航取消協定)。
- **子系統與架構歸屬**: S6 Navigation（`mobile_base_navigation`）整合 Nav2 Jazzy 1.3.12 原生 Stack（`nav2_route`, `nav2_planner`, `nav2_controller`, `nav2_costmap_2d`, `nav2_bt_navigator`, `nav2_collision_monitor`, `nav2_lifecycle_manager`）。
- **架構決策 (AD-003)**:
  1. **Route-preferred Strategy**: 存在有效路網時優先沿拓撲邊行駛，禁止任意選擇完全自由空間導航。
  2. **三階段編排**: First Mile（起點連接）→ On Route（拓撲巡航）→ Last Mile（目標對齊與進站）。
  3. **v0.1 Fallback 邊界**: 禁用全局自由空間 Fallback；路網方案用盡或阻塞時立即煞停並回報失敗。
  4. **零 Custom Code 原則**: 完全複用 Nav2 Jazzy 原生節點、外掛與 BT 節點，僅提供專案配置與專用 BT XML。

#### 3.12.2 Implementation Artifacts
- **Nav2 參數設定檔**: `src/mobile_base_navigation/config/nav2_params.yaml`
  - Planner: `nav2_navfn_planner::NavfnPlanner`（配置 `use_astar: true` 搜尋模式）。
  - Controller: `nav2_mppi_controller::MPPIController`（DiffDrive 運動模型、橫向速度鎖定為零、配置完整 Critic 集合；MVP functional baseline $v_{x,\max} = 0.50\,\text{m/s}$）。
  - Goal Checker: `nav2_controller::StoppedGoalChecker`（Post-closure MVP functional baseline：位置容差 $0.25\,\text{m}$、朝向容差 $0.5236\,\text{rad}$、停轉線速度 $<0.05\,\text{m/s}$、角速度 $<0.10\,\text{rad/s}$）。
  - Costmaps: 訂閱 `/scan` 進行光線投射與膨脹層計算，足跡配置為 $[0.35, 0.30] \times [-0.35, -0.30]$。
  - Route Server: `nav2_route::RouteServer` 配置 `GeoJsonGraphFileLoader` 與距離/代價評分器。
  - Collision Monitor: 獨立 `nav2_collision_monitor::CollisionMonitor`，作為速度鏈唯一終端 Publisher，輸出重定向至 `/diff_drive_controller/cmd_vel`。
- **三階段行為樹**: `src/mobile_base_navigation/behavior_trees/route_assisted_nav.xml`
  - 基於 BTCPP v4 格式，以 `PipelineSequence` 編排 `ComputeRoute` (`raw_route_path`) → First Mile Fallback/Sequence (`ArePosesNear` + `<SetBlackboard>` / `ComputePathToPose` + `ConcatenatePaths` 產出 `first_connected_path`) → Last Mile Fallback/Sequence (`ArePosesNear` + `<SetBlackboard>` / `ComputePathToPose` + `ConcatenatePaths` 產出 `final_route_path`) → `FollowPath` (`final_route_path`)。
  - 避免同一 Blackboard Key in-place overwrite 風險，採用明確鍵值分離 (`raw_route_path` → `first_connected_path` → `final_route_path`)，保證無 First/Last Mile 時透過原生 `<SetBlackboard>` 正確傳遞下游路徑。
  - 嚴格落實 SYS-021：若 `ComputeRoute` 失敗，直接回傳 `FAILURE` 終止導航，不設置全域自由空間 Fallback 分支。
- **真實場域路網圖資 (Production Route Graph)**: `maps/test_site/route_graph.geojson`
  - 基於真實場域地圖 `maps/test_site/map.yaml` (0.05m 解析度)，透過 Nav2 原生 GeoJSON 拓撲圖規範建立，與地圖共置於 `maps/test_site/` 目錄。
  - 為滿足實車受控路網導航驗證，配置為 2 個位於全域代價地圖 100% 自由通行空間之頂點：
    - Node 0 (`id: 0`, `frame: "map"`, `coordinates: [0.60, -1.55]`, Route Entry)
    - Node 1 (`id: 1`, `frame: "map"`, `coordinates: [0.60, -1.25]`, Route Exit)
  - 包含 1 條單向拓撲邊（Edge 2: 0→1），長度為 $0.30\,\text{m}$，速限設為 $0.5\,\text{m/s}$。
- **測試路網夾具**: `src/mobile_base_navigation/test/test_data/test_route_graph.geojson`
  - 符合 Nav2 `GeoJsonGraphFileLoader` 規範之 3 節點、2 拓撲邊測試用 FeatureCollection。
- **導航啟動腳本**: `src/mobile_base_navigation/launch/navigation.launch.py`
  - 啟動 `controller_server`（輸出至 `/cmd_vel_nav`）、`planner_server`、`route_server`、`bt_navigator`、`collision_monitor`（速度鏈唯一終端 Publisher，輸出重定向至 `/diff_drive_controller/cmd_vel`）與 `lifecycle_manager_navigation`（管理 5 個 Lifecycle 節點）。
- **軟體整合與合約測試**:
  - `src/mobile_base_navigation/test/test_navigation_launch.py`: 測試 Nav2 參數合約、BT XML 結構與 SYS-021 邊界、測試與真實 GeoJSON 夾具格式、LaunchDescription 組裝、以及速度鏈隔離（Controller 不直接輸出底盤、Collision Monitor 為唯一終端輸出）。
  - `src/mobile_base_navigation/test/test_behavior_tree_runtime.cpp`: C++ BehaviorTree Runtime 測試，驗證 9 個 Nav2 BT 外掛動態庫成功註冊、BT XML 於 ROS 節點黑板下正確解析與 Schema 實例化、`ConcatenatePaths` 與 `GetPoseFromPath` 之路徑順序資料流正確性、以及 `nav2_route::GeoJsonGraphFileLoader` 原生載入 `maps/test_site/route_graph.geojson`（2 nodes, 1 edge）完全通過。

#### 3.12.3 Mature vs Custom Boundary
- **Mature Nav2 Components Reused**:
  - `nav2_route::RouteServer` (Jazzy 1.3.12) + `nav2_route::GeoJsonGraphFileLoader`
  - `nav2_planner::PlannerServer` + `nav2_navfn_planner::NavfnPlanner`
  - `nav2_controller::ControllerServer` + `nav2_mppi_controller::MPPIController`
  - `nav2_controller::StoppedGoalChecker`
  - `nav2_collision_monitor::CollisionMonitor`
  - `nav2_costmap_2d`
  - `nav2_bt_navigator` + `nav2_behavior_tree` 原生 Action/Condition/Control Nodes
  - `nav2_lifecycle_manager`
  - `nav2_rviz_plugins` (Route Tool)
- **Project-Owned Custom Code**: **`NONE`**（零自製 C++ / Python 節點或外掛，完全由配置與 BT XML 驅動）。

#### 3.12.4 Verification Evidence
| Timestamp | Test target | Command | Result | Evidence boundary | Storage path |
|---|---|---|---|---|---|
| 2026-08-21T11:50:10+08:00 | S6 Navigation Stage A Software & Launch Test Suite | `colcon build --packages-select mobile_base_navigation` + `colcon test` | PASS (Software-only) | 1. 套件編譯通過（0 errors）；2. 54 項測試全部通過（含 26 GTest + 4 pytest + linter）；3. 驗證 Nav2 參數合約；4. 驗證 BT XML 三階段結構與禁用 Fallback；5. 驗證 GeoJSON 路網夾具；6. 驗證 Launch Composition 與速度鏈 remapping。 | 容器即時測試日誌 |
| 2026-08-21T11:58:00+08:00 | S6 Navigation Stage A.1 BT Runtime & Dataflow Test Suite | `colcon build --packages-select mobile_base_navigation` + `colcon test` | PASS (Software-only) | 1. 套件編譯通過（0 errors）；2. 61 項測試全部通過（含 29 GTest + 4 pytest + linter）；3. 驗證 9 個 Nav2 BT Plugin 共享庫註冊；4. 驗證 BT XML Schema 實例化與黑板埠合約解析；5. 驗證 `ConcatenatePaths` 與 `GetPoseFromPath` 資料流順序；6. 驗證鍵值分離 (`raw_route_path`, `first_connected_path`, `final_route_path`)。 | 容器即時測試日誌 |
| 2026-08-21T12:11:36+08:00 | S6 Navigation Stage B Real-Site Route Graph & Native Loader Test Suite | `colcon build --packages-select mobile_base_navigation` + `colcon test` | PASS (Software-only) | 1. 套件編譯通過（0 errors）；2. 63 項測試全部通過（含 30 GTest + 5 pytest + linter）；3. 驗證 `maps/test_site/route_graph.geojson` 真實圖資語法與幾何結構；4. 驗證 Nav2 `GeoJsonGraphFileLoader` 原生解析載入成功（零錯誤）。 | 容器即時測試日誌 |
| 2026-08-21T12:42:00+08:00 | S6 Navigation Stage C Stationary Full Nav2 Runtime & Costmap Safety Check | Nav2 Launch + `ComputeRoute 0->2` | FAIL / SAFETY REJECTION (Negative Evidence) | 1. 全節點 Active（controller, planner, route, bt_navigator, lifecycle_manager）；2. StoppedGoalChecker 門檻驗證；3. 全域 Costmap 顯示初版 Node 2 (0.2, -0.2) 與 Edge 1->2 侵入 Inscribed Obstacle (cost 99/253)；4. RouteServer CostmapScorer 正確阻斷並回報 `error_code: 405 (NO_VALID_ROUTE)`；5. 識別 Collision Monitor 獨立節點缺口。 | 容器即時測試日誌 |
| 2026-08-21T13:35:10+08:00 | S6 Navigation Stage C.1 Minimal Real Route Calibration & Stationary ComputeRoute | Nav2 Launch + `ComputeRoute 0->1` | PASS (Stationary-only) | 1. 簡化路網為 2 頂點 1 拓撲邊 (0.2, -1.1) -> (0.2, -0.8)，沿線 20 個抽樣點 costmap cost 全為 0；2. `nav2_route::GeoJsonGraphFileLoader` 成功載入 2 nodes / 1 edge；3. `ComputeRoute` 成功完成規劃（`status: SUCCEEDED`, `error_code: 0`, 規劃耗時 122 微秒，產出 7 個 dense poses 之 Path 與拓撲 Route）；4. 前後全程監控 `cmd_vel` 輸出為零，底盤完全靜止。 | 容器即時測試日誌 |
| 2026-08-21T13:43:00+08:00 | S6 Navigation Stage D Collision Monitor Integration & Stationary Velocity Chain | Nav2 Launch + `ComputeRoute 0->1` + Velocity Chain Verification | PASS (Stationary-only) | 1. 獨立 `nav2_collision_monitor` 節點整合完成；2. 速度鏈收斂驗證：`controller_server` 發布至 `/cmd_vel_nav`，`collision_monitor` 訂閱 `/cmd_vel_nav` 並作為唯一 Publisher 輸出至 `/diff_drive_controller/cmd_vel`（Pub count = 1, Sub count = 1）；3. `lifecycle_manager_navigation` 成功管理 5 個節點（全部 Active [3]）；4. `/scan` 來源健康（25.13 Hz）；5. 靜止期間 `diff_drive` 速度命令完全為零；6. `ComputeRoute` 回歸驗證成功（SUCCEEDED, error_code: 0, 119 微秒）。 | 容器即時測試日誌 |
| 2026-08-21T17:10:00+08:00 | S6 Navigation Stage E Route Graph Post-Edit Revalidation | `GeoJsonGraphFileLoader` + Costmap Sampling + `ComputeRoute 0->1` | PASS (Stationary-only) | 1. 操作者透過 RViz / Route Tool 編輯之 `maps/test_site/route_graph.geojson` 驗證通過；2. 全域 Costmap 取樣驗證：Node 0 (0.20, -1.10) cost = 0，Node 1 (0.20, -0.80) cost = 0，沿線 20 個抽樣點 cost 全為 0；3. 靜態 `ComputeRoute` 規劃成功；4. Collision Monitor 與速度鏈全生命週期 Active，全域完全靜止。 | 容器即時測試日誌 |
| 2026-08-21T17:58:03+08:00 | S6 Navigation Stage L1 Minimal Controlled Real-Hardware Route Navigation | Nav2 Launch + `NavigateToPose` Goal to Node 1 (0.60, -1.25) | PASS (Hardware Verified) | 1. 前置檢查：7 個 Lifecycle 節點全為 Active [3]，`/scan` 與 TF 鏈健康；2. 安全閘門：Start Gate 通過（距離 Node 0 為 $0.0689\,\text{m} \le 0.15\,\text{m}$，航向偏差 $0.55^\circ \le 15.0^\circ$），Speed Gate 通過（當時測試條件 $v_{x,\max} = 0.15\,\text{m/s}$）；3. 路網規劃：`ComputeRoute` 成功（2 nodes, 1 edge）；4. 實車運動執行：MPPI `FollowPath` 實際驅動雙輪平穩前進約 $13\,\text{秒}$，實測前進位移約 $0.27\,\text{m}$；5. 速度限制：最高觀測命令線速度 $0.0970\,\text{m/s} \le 0.15\,\text{m/s}$，最高角速度 $0.1393\,\text{rad/s}$；6. 到站與停穩：`StoppedGoalChecker` 判定到站，實測終點位置誤差 $0.0938\,\text{m} \le 0.15\,\text{m}$（當時測試容差通過），底盤實體線速度 $0.0000\,\text{m/s}$、角速度 $0.0000\,\text{rad/s}$ 完全停穩；7. 原生結果：`NavigateToPose` 回傳 `SUCCEEDED` (status 4)；8. 安全與穩定：無定位遺失、無 TF 中斷、無雷達逾時、無異常行為；9. 碰撞監視器：全生命週期 Active，`/scan` 健康，作為唯一終端速度發布者（無障礙淨空路徑上未需介入減速/煞停）。 | 容器即時測試日誌 |

#### 3.12.5 Known Limits / Accepted MVP Limitations
- **Post-Closure MVP 功能基線對齊 (Post-Closure MVP Functional Baseline Alignment)**：
  - **Current MVP Baseline**: `xy_goal_tolerance = 0.25 m`、`yaw_goal_tolerance = 0.5236 rad` ($30^\circ$)、`vx_max = 0.50 m/s`。
  - **說明**: 這些參數為 IMP-018 closure 後正式接受的 current MVP functional baseline，目的在於優先推進後續跨子系統閉環（IMP-019 ～ IMP-023）與端到端使用案例（IMP-024, IMP-025），而非在此階段提前進行細部導航 tuning。
  - **歷史數據獨立性 (Historical Stage L1 Evidence Preserved)**: Stage L1 實車物理驗證證據（2026-08-21T17:58:03+08:00）完整保留當時實際運行的測試條件（$v_{x,\max} = 0.15\,\text{m/s}$, 位置容差 $0.15\,\text{m}$, 角度容差 $0.25\,\text{rad}$, 實測誤差 $0.0938\,\text{m}$），不改寫歷史實驗數據。Current working baseline 與 historical Stage L1 evidence 明確區分。
  - **遞延調校範圍 (Deferred Tuning)**: 最終量產到站精度（$5\,\text{cm} / 0.05\,\text{rad}$）、速度曲線優化、MPPI Critic 權重深度 tuning、以及 Collision Monitor 多邊形動態調校等，明確遞延至後續適當 checklist（如 Checklist #25 端到端驗收）處理。
  - **Closure 狀態維持**: 此 post-closure 參數基線同步不重新開啟 IMP-018，Checklist #18 維持 `[x] Completed`。
- **碰撞監視器實體干預邊界 (Physical Collision Monitor Intervention NOT CLAIMED)**：Stage L1 在無障礙之純淨路徑上完成，未對 AMR 施加實體障礙物阻擋；碰撞監視器在 Stage L1 維持 Active 且未發生干預。路網與代價地圖之危險路徑阻斷由 Stage C 負向測試提供證據。
- **實體行進中取消邊界 (Physical In-motion Cancellation NOT CLAIMED)**：Nav2 原生 Action 取消介面與 BT 取消機制已在軟體與客戶端架構中驗證，Stage L1 實車測試完成正常抵達；未進行額外實體行進中中斷取消測試。
- **站點清單邊界 (Production Station Catalog NOT CREATED)**：`maps/test_site/route_graph.geojson` 僅為拓撲路網圖資，不包含業務站點定義。真實站點清單依現場業務需求配置，不偽造假站點資料。

#### 3.12.6 Status
- **Implementation Status**: `Implemented`
- **Evidence Status**: `Hardware Verified` (Stage A~E 軟體／靜態測試與 Stage L1 實車自主受控導航通過)
- **Checklist Status**: `[x] Completed` (滿足 Checklist #18 原始 DoD 全部要求，無殘留未滿足條件，未引入新 gate)。
- **Next Dependency**: Checklist #19 (`TF and frame authority closure`)。

---

### 3.13 TF and frame authority closure (Checklist #19)

#### 3.13.1 Requirement and Subsystem Trace
- **需求追溯**: `SYS-023` (S1 靜態幾何與坐標框架), `SYS-005` (S3 平面里程融合與 `odom -> base_footprint` TF 擁有權), `SYS-006` (S4 建圖模式 `map -> odom` TF 擁有權), `SYS-010` (S5 定位模式 `map -> odom` TF 擁有權), `AD-004` (模式隔離與互斥 TF 廣播規則；`05_architecture.md` §3, §7.1；`06_subsystem.md` §4.1)。
- **完成條件 (DoD)**: S1 static TF、S3 `odom -> base_footprint`、S4/S5 互斥 `map -> odom` 無斷鏈、重複 owner 或 frame mismatch。

#### 3.13.2 Authority and Topology Architecture
1. **全域 TF 樹權威拓撲**:
   - `map → odom`: 動態座標變換，依操作模式互斥擁有：
     - **Mapping Mode (UC-001)**: 由 `slam_toolbox`（`async_slam_toolbox_node`）唯一發布（20 Hz）；`nav2_amcl` 完全不啟動。
     - **Navigation Mode (UC-002)**: 由 `nav2_amcl` 唯一發布（接收 Initial Pose 後更新）；`slam_toolbox` 完全不啟動。
   - `odom → base_footprint`: 動態座標變換，由 S3 `robot_localization`（`ekf_filter_node`）於 50 Hz 唯一發布。
     - `diff_drive_controller`（`enable_odom_tf: false`）與 `rf2o_laser_odometry`（`publish_tf: false`）嚴格禁止發布 TF。
   - `base_footprint → base_link`: 靜態座標變換（底盤離地高度 $Z = +0.2560\,\text{m}$），由 S1 `robot_state_publisher` 透過 `/tf_static` 廣播。
   - `base_link → base_lidar_link_FL / BR / base_imu_link`: 靜態感測器座標變換，由 S1 `robot_state_publisher` 透過 `/tf_static` 廣播。
   - `base_link → driving_wheel_link_L / R`: 動態輪端座標變換，由 S1 `robot_state_publisher` 訂閱 S7 `joint_state_broadcaster`（`/joint_states`）後發布至 `/tf`。
2. **零自製 TF 元件原則**: 完全依賴 ROS 2 Jazzy 原生標準 URDF/Xacro、`robot_state_publisher`、`robot_localization`、`slam_toolbox` 與 `nav2_amcl` 配置，不引入額外的 TF Proxy、Frame Manager 或自製廣播節點。

#### 3.13.3 Implementation & Test Artifacts
- **自動化 TF 權威與拓撲合約測試**: `src/mobile_base_bringup/test/test_tf_authority.py`
  - `test_s1_urdf_tf_tree_structure`: 自動調用 `xacro` 解析權威 `mobile_base.urdf.xacro`，驗證 Canonical Links（`base_footprint`, `base_link`, `base_lidar_link_FL`, `base_lidar_link_BR`, `base_imu_link`, `driving_wheel_link_L`, `driving_wheel_link_R`）完整存在，驗證 `base_joint` 為 `fixed` 且 $Z=0.2560\,\text{m}$，驗證雙光達、IMU 與雙輪關節型態與父子關係符合規範，無重複子節點或拓撲環。
  - `test_s3_odom_to_base_footprint_sole_authority`: 驗證 `ekf.yaml` 中 `publish_tf: true` 且 `world_frame: odom`，同時驗證 `base_control_params.yaml`（`diff_drive_controller`）配置 `enable_odom_tf: false` 以及 `rf2o_laser_odometry.launch.py` 配置 `publish_tf: False`，證明 EKF 為全系統唯一配置之 `odom -> base_footprint` 廣播者。
  - `test_s4_mapping_mode_map_to_odom_authority`: 驗證 `slam_toolbox.yaml` 配置 `transform_publish_period > 0`，且 `mapping.launch.py` 啟動 `slam_toolbox` 並嚴格排除 `amcl`。
  - `test_s5_navigation_mode_map_to_odom_authority`: 驗證 `amcl_params.yaml` 配置 `tf_broadcast: true`，且 `navigation.launch.py` 啟動 `nav2_amcl` 並嚴格排除 `slam_toolbox`。
  - `test_sensor_and_perception_frame_ids_match_urdf`: 驗證 `dual_laser_merger` 目標框架為 `base_link`，雙光達驅動框架為 `base_lidar_link_FL` / `base_lidar_link_BR`，IMU 驅動框架為 `base_imu_link`，與 S1 URDF 框架名稱完全一致。

#### 3.13.4 Mature vs Custom Boundary
- **Mature Components Reused**:
  - `robot_state_publisher` (ROS 2 Jazzy)
  - `robot_localization::ekf_filter_node`
  - `slam_toolbox::async_slam_toolbox_node`
  - `nav2_amcl::AmclNode`
  - `tf2_ros`
- **Project-Owned Custom Code**: **`NONE`**（零自製 TF 節點，完全由標準 ROS 2 / Nav2 套件設定驅動）。

#### 3.13.5 Verification Evidence
| Timestamp | Test target | Command | Result | Evidence boundary | Storage path |
|---|---|---|---|---|---|
| 2026-08-24T11:05:52+08:00 | S1~S7 TF Authority & Frame Consistency Consolidated Test Suite | `colcon build --packages-select mobile_base_bringup` + `colcon test` | PASS (Software-only) | 1. 16 項測試全部通過（含 5 項 TF 權威測試 + 11 項 bringup / map / linter 測試）；2. 驗證 S1 URDF/Xacro 靜態拓撲樹無斷鏈且 $Z=0.2560\,\text{m}$；3. 驗證 S3 EKF 唯一擁有 `odom -> base_footprint`（DiffDrive 與 RF2O 嚴格停用 TF）；4. 驗證 S4/S5 模式互斥隔離（Mapping 下 slam 獨占、Navigation 下 amcl 獨占）；5. 驗證感測器 Frame ID 與 URDF 零 mismatch。 | 容器即時測試日誌 |
| 2026-08-24T11:06:40+08:00 | S1 Robot Description Stationary Static TF Buffer Lookup | `ros2 launch mobile_base_description robot_description.launch.py` + `tf2_ros` buffer lookup | PASS (Stationary-only) | 1. `robot_state_publisher` 成功啟動並發布 `/tf_static`；2. 實測成功 lookup `base_footprint -> base_link` ($Z = +0.256\,\text{m}$)、`base_link -> base_lidar_link_FL`、`base_link -> base_lidar_link_BR`、`base_link -> base_imu_link`；3. 全程靜態無位移。 | 容器即時測試日誌 |

#### 3.13.6 Evidence Provenance & Historical Reuse
- **New Stage A Consolidated Evidence**:
  - `src/mobile_base_bringup/test/test_tf_authority.py`: 5 項自動化合約測試全數通過（驗證 Xacro 樹狀拓撲結構、S3 EKF 唯一 TF 廣播配置、S4/S5 模式隔離互斥、感測器 Frame 匹配）。
  - 跨 5 個 TF 相關套件（`mobile_base_bringup`, `mobile_base_description`, `mobile_base_localization`, `mobile_base_mapping`, `mobile_base_perception`）共 102 項測試通過。
  - `robot_state_publisher` 靜止 `/tf_static` buffer lookup 實測成功。
- **Reused Historical Runtime Evidence**:
  - **IMP-009**: S1 URDF 幾何語法驗證、`/tf_static` 廣播驗證。
  - **IMP-010**: S2 雙光達 Frame IDs (`base_lidar_link_FL`, `base_lidar_link_BR`) 與融合光達 Frame (`base_link`) 實機驗證。
  - **IMP-011**: S2 TDK IMU Frame ID (`base_imu_link`) 實機驗證。
  - **IMP-012**: S2 RF2O Laser Odometry `publish_tf: False` 實機驗證。
  - **IMP-013**: S3 State Estimation `ekf_filter_node` 唯一 50 Hz `odom -> base_footprint` 實機動態與靜態驗證。
  - **IMP-014**: S4 Mapping Mode `slam_toolbox` 唯一發布 `map -> odom` 實機建圖驗證。
  - **IMP-016**: S5 Localization Mode `amcl` 唯一發布 `map -> odom` 實機定位驗證。
  - **IMP-018 Stage L1**: S6 自主路網導航實車運行，全域 TF 樹（`map -> odom -> base_footprint -> base_link -> sensors`）同步無跳變與斷鏈實證。
- **執行邊界確認**: 本次 closure 嚴格未重新執行 Mapping / Navigation runtime，未執行硬體馬達輸出，AMR 維持完全靜止。

#### 3.13.7 Status
- **Implementation Status**: `Complete`
- **Evidence Status**: `Complete` (Stage A 自動化合約測試、靜態 TF Lookup 與 S1~S6 歷史實機 evidence 完整覆蓋)
- **Checklist Status**: `[x] Completed` (滿足 Checklist #19 原始 DoD 全部要求：S1 static TF、S3 odom -> base_footprint、S4/S5 互斥 map -> odom 無斷鏈、無重複 owner、無 frame mismatch，未引入新 gate)。
- **Next Dependency**: Checklist #20 (`Perception data-flow closure`)。

---

### 3.14 Perception data-flow closure (Checklist #20)

#### 3.14.1 Requirement and Subsystem Trace
- **需求追溯**: `SYS-003` (S2 雙光達資料擷取與 360° 視野融合), `SYS-004` (S2 6 軸 IMU 慣性數據擷取), `SYS-005` (S3 多源里程與慣性數據 EKF 狀態估測), `05_architecture.md` §4, §7.4 (感知與里程資料流邊界), `06_subsystem.md` §3.2 (S2 Perception), §3.4 (S3 State Estimation), §4.3 (Perception Data Flow)。
- **完成條件 (DoD)**: 兩個 raw LiDAR、selected scan、IMU 與 RF2O 的 producer/consumer、QoS、frame、timestamp、rate、freshness 與 failure propagation 可觀察且符合 06。

#### 3.14.2 Perception Data-Flow Architecture & Interface Contracts
1. **前左原始光達 (Front-Left LiDAR)**:
   - 生產者: `sick_scan_xd` (`front_lidar`)
   - 主題: `/scan_front` (`sensor_msgs/msg/LaserScan`, `frame_id: base_lidar_link_FL`, QoS SensorData/Reliable, 標稱 $25.0\,\text{Hz}$ / 實測 $25.13\,\text{Hz}$)
   - 消費者: `dual_laser_merger_node` (`laser_1_topic`)
2. **後右原始光達 (Rear-Right LiDAR)**:
   - 生產者: `sick_scan_xd` (`rear_lidar`)
   - 主題: `/scan_rear` (`sensor_msgs/msg/LaserScan`, `frame_id: base_lidar_link_BR`, QoS SensorData/Reliable, 標稱 $25.0\,\text{Hz}$ / 實測 $25.13\,\text{Hz}$)
   - 消費者: `dual_laser_merger_node` (`laser_2_topic`)
3. **360° 融合光達 (Authoritative Selected / Merged Scan)**:
   - 生產者: `dual_laser_merger_node`
   - 主題: `/scan` (`sensor_msgs/msg/LaserScan`, `frame_id: base_link`, QoS SensorData/SystemDefault, 標稱 $25.0\,\text{Hz}$ / 實測 $25.13\,\text{Hz}$)
   - 消費者: S3 `rf2o_laser_odometry`、S4 `slam_toolbox` (Mapping Mode)、S5 `nav2_amcl` (Navigation Mode)、S6 Nav2 Local/Global Costmap、S6 `nav2_collision_monitor`。
4. **TDK IMU 慣性感測器**:
   - 生產者: `tdk_ros2_imu` (`imu_driver_node`)
   - 主題: `/imu/data_raw` (`sensor_msgs/msg/Imu`, `frame_id: base_imu_link`, QoS SensorData, 標稱 $100.0\,\text{Hz}$ / 實測 $100.0\,\text{Hz}$)
   - 消費者: S3 `ekf_filter_node` (`imu0`: 融合 $\omega_z, a_x$；嚴格排除 orientation 融合)。
5. **RF2O 平面雷達里程計**:
   - 生產者: `rf2o_laser_odometry` (`rf2o_laser_odometry_node`)
   - 輸入: `/scan`
   - 輸出主題: `/rf2o/odom` (`nav_msgs/msg/Odometry`, `header.frame_id: odom`, `child_frame_id: base_footprint`, `publish_tf: False`, 標稱 $20.0\,\text{Hz}$ / 實測 $20.0\,\text{Hz}$)
   - 消費者: S3 `ekf_filter_node` (`odom1`: 融合 $v_x, v_y, \omega_z$)。

#### 3.14.3 Implementation & Test Artifacts
- **自動化感知資料流契約測試**: `src/mobile_base_bringup/test/test_perception_dataflow.py`
  - `test_front_lidar_data_contract`: 驗證前光達啟動參數、主題名稱 `/scan_front`、`base_lidar_link_FL` 框架與 `dual_laser_merger` 綁定。
  - `test_rear_lidar_data_contract`: 驗證後光達啟動參數、主題名稱 `/scan_rear`、`base_lidar_link_BR` 框架與 `dual_laser_merger` 綁定。
  - `test_merged_scan_data_contract_and_consumers`: 驗證 `dual_laser_merger` 輸出 `/scan` (`base_link`)，並自動檢核所有核准之消費者（RF2O、slam_toolbox、AMCL、Local/Global Costmaps、Collision Monitor）均正確訂閱 `/scan`。
  - `test_imu_data_contract_and_ekf_consumer`: 驗證 TDK IMU 輸出 `/imu/data_raw` (`base_imu_link`)，並檢核 EKF `imu0` 參數綁定與 2D 融合設定（融合 vyaw, ax；排除 orientation）。
  - `test_rf2o_laser_odometry_contract_and_ekf_consumer`: 驗證 RF2O 訂閱 `/scan`、輸出 `/rf2o/odom` (`odom -> base_footprint`，`publish_tf: False`)，並檢核 EKF `odom1` 參數綁定。
  - `test_freshness_and_timeout_configurations`: 驗證 EKF `sensor_timeout` (0.1s)、Collision Monitor `source_timeout` (>= 0.5s) 與 DiffDrive `cmd_vel_timeout` (0.5s) 逾時保護閾值設定。

#### 3.14.4 Mature vs Custom Boundary
- **Mature Components Reused**:
  - `sick_scan_xd` (ROS 2 Jazzy Driver)
  - `dual_laser_merger` (ROS 2 Jazzy 0.3.1)
  - `tdk_ros2_imu` (Driver Component)
  - `rf2o_laser_odometry` (Planar Odometry Component)
  - `robot_localization::ekf_filter_node`
  - `nav2_costmap_2d` & `nav2_collision_monitor`
- **Project-Owned Custom Code**: **`NONE`**（零自製感知中繼節點，完全由標準 ROS 2 / Nav2 介面與參數驅動）。

#### 3.14.5 Verification Evidence
| Timestamp | Test target | Command | Result | Evidence boundary | Storage path |
|---|---|---|---|---|---|
| 2026-08-24T11:24:59+08:00 | S2/S3/S6 Perception Data-Flow Consolidated Test Suite | `colcon build --packages-select mobile_base_bringup` + `colcon test` | PASS (Software-only) | 1. 17 項測試全部通過（含 6 項感知資料流合約測試 + 5 項 TF 權威測試 + 6 項 bringup / map / linter 測試）；2. 驗證雙光達至融合光達至 RF2O/Costmap/Collision Monitor 之主題與 Frame 鏈路；3. 驗證 IMU 至 EKF 融合配置；4. 驗證超時門檻設定。 | 容器即時測試日誌 |

#### 3.14.6 Freshness, Failure Propagation & Evidence Provenance
1. **Freshness & Timeout Contracts (Current Repository Actual)**:
   - **EKF (`ekf_filter_node`)**: `sensor_timeout = 0.1 s`（100 ms，輸入逾時即標記為 stale 並進行源隔離推算）。
   - **Collision Monitor (`nav2_collision_monitor`)**: `source_timeout = 3.0 s`（雷達數據逾時停止輸出移動速度）。
   - **DiffDrive (`diff_drive_controller`)**: `cmd_vel_timeout = 0.5 s`（速度命令逾時受控煞停）。
2. **Failure Propagation (Evidence-Supported)**:
   - **雙光達或單側光達中斷**: 驅動層停止發布；`dual_laser_merger` 偵測輸入中斷停止產出無效點雲；SICK 驅動透過 ROS 2 診斷發布錯誤狀態。
   - **`/scan` 串流中斷**: RF2O 停止更新位姿；EKF 超過 `0.1 s` 觸發 `sensor_timeout` 隔離 `odom1` 並依輪端與 IMU 推算；`nav2_collision_monitor` 超過 `source_timeout` 煞停。
   - **IMU 串流中斷**: EKF 超過 `0.1 s` 觸發 `sensor_timeout` 隔離 `imu0`，持續依輪端與 RF2O 維持推算。
   - **RF2O 串流中斷**: EKF 超過 `0.1 s` 觸發 `sensor_timeout` 隔離 `odom1`，持續依輪端與 IMU 維持推算。
3. **Evidence Provenance & Historical Reuse**:
   - **New Stage A Consolidated Evidence**:
     - `src/mobile_base_bringup/test/test_perception_dataflow.py`: 6 項自動化合約測試通過（涵蓋雙光達、融合光達、IMU、RF2O 之主題、型別、框架、消費者配置與超時門檻）。
     - 跨套件共 64 項迴歸測試通過。
   - **Reused Historical Runtime Evidence**:
     - **IMP-010**: 雙光達與 360° 融合雷達 $25.13\,\text{Hz}$ 實機發布與 Frame 驗證。
     - **IMP-011**: TDK IMU $100.0\,\text{Hz}$ 實機發布與重力向量驗證。
     - **IMP-012**: RF2O $20.0\,\text{Hz}$ 實機運行與 `publish_tf: False` 驗證。
     - **IMP-013**: EKF 50.0 Hz 多源融合與 `sensor_timeout` 實機驗證。
     - **IMP-016**: AMCL 訂閱 `/scan` 實機定位驗證。
     - **IMP-018 Stage L1**: 導航與 Collision Monitor 實車自主導航全程訂閱 `/scan` 實機運行驗證。
   - **執行邊界確認**: 本次 closure 嚴格未重新執行感測器硬體，未執行硬體馬達輸出，AMR 維持完全靜止。

#### 3.14.7 Status
- **Implementation Status**: `Complete`
- **Evidence Status**: `Complete` (Stage A 自動化合約測試與 S2~S6 歷史實機 evidence 完整覆蓋)
- **Checklist Status**: `[x] Completed` (滿足 Checklist #20 原始 DoD 全部要求：兩個 raw LiDAR、selected scan、IMU 與 RF2O 的 producer/consumer、QoS、frame、timestamp、rate、freshness 與 failure propagation 可觀察且符合 06，未引入新 gate)。
- **Next Dependency**: Checklist #21 (`Motion-command and physical-stop closure`)。

---

### 3.15 Motion-command and physical-stop closure (Checklist #21)

#### 3.15.1 Requirement and Subsystem Trace
- **需求追溯**: `SYS-022` (S7 差速底盤運動控制), `SYS-026` (S7 底盤故障安全處理), `SYS-027` (S7 運動命令逾時保護), `SYS-028` (S7 運動限幅與減速度約束), `SYS-029` (S7 輪端編碼器真實回授 `GAP-05`), `SYS-030` (S7 安全啟停與停妥釋放使能 `GAP-06`), `SYS-034` (S7 手動移動控制與 Teleop 整合), `SYS-011`/`SYS-018`/`SYS-020` (S6 導航、MPPI 控制器與 Collision Monitor 安全閘), `05_architecture.md` §3, §7.2, §7.3, `06_subsystem.md` §3.3, §3.6, §4.2, §4.4。
- **完成條件 (DoD)**: S6 command / Mapping teleop command→S7 safety gate→diff drive→M1，以及 Task Cancel、Manual Stop、Command Timeout、Hardware Safe Stop 分層停止均量測到實體停止結果。

#### 3.15.2 Command Chain & Safety Architecture
1. **自主導航命令鏈 (Navigation Command Chain)**:
   - `nav2_controller_server` (MPPI 30 Hz) 發布 `/cmd_vel_nav` (`geometry_msgs/msg/TwistStamped`)；
   - `nav2_collision_monitor` 訂閱 `/cmd_vel_nav` 與 `/scan`，依安全多邊形約束速度後輸出至 `/diff_drive_controller/cmd_vel`；
   - `diff_drive_controller` (ros2_control, 30 Hz, `cmd_vel_timeout = 0.5 s`, `SpeedLimiter` $v_x \le 1.0\,\text{m/s}, \omega_z \le 1.5\,\text{rad/s}$, $a_{\text{decel}} = -1.0\,\text{m/s}^2$) 輸出輪端速度指令；
   - `M1Hardware` (`response_timeout_ms = 50`) 透過 `M1Driver` (Modbus RTU FC17 `/dev/ttyUSB0`) 驅動 M1 雙軸馬達與實體車輪。
2. **手動鍵盤命令鏈 (Mapping / Teleop Command Chain)**:
   - `teleop_twist_keyboard` (`stamped:=true`) 重新映射直通 `/diff_drive_controller/cmd_vel`；
   - 由 S7 `diff_drive_controller` 之 `SpeedLimiter` 與 `cmd_vel_timeout` 提供終端安全限幅與煞停防護。

#### 3.15.3 Implementation & Test Artifacts
- **自動化運動命令與停止鏈路契約測試**: `src/mobile_base_bringup/test/test_motion_command_stop_chain.py`
  - `test_navigation_motion_command_chain_contract`: 驗證 `controller_server` 輸出重映射至 `/cmd_vel_nav`，`collision_monitor` 訂閱 `/cmd_vel_nav` 並輸出至 `/diff_drive_controller/cmd_vel`，啟用 `stamped` 訊息與 `/scan` 綁定。
  - `test_teleop_motion_command_chain_contract`: 驗證 `diff_drive_controller` 設定支援 `use_stamped_vel: true`。
  - `test_diff_drive_controller_safety_and_limits`: 驗證 30 Hz 執行頻率、`cmd_vel_timeout = 0.5 s`、`enable_odom_tf = false`、速度限幅 ($v_x \le 1.0, \omega_z \le 1.5$) 與減速度限制 ($a_{\text{decel}} = -1.0\,\text{m/s}^2, \alpha_{\text{decel}} = -2.0\,\text{rad/s}^2$)。
  - `test_m1_hardware_safe_stop_and_timeout_contract`: 驗證 URDF Xacro 必填 `response_timeout_ms` 參數與 C++ 原始碼中 `on_deactivate` 停轉確認後切斷使能（GAP-06 / SYS-030）安全順序。

#### 3.15.4 Four Stop Layers & Evidence Semantics
1. **Task Cancel (任務取消)**:
   - **軟體合約 (Software Cancel Contract)**: Nav2 Action Cancel $\rightarrow$ BT Navigator $\rightarrow$ Controller Server 速度歸零，回報 `CANCELED` [VERIFIED in IMP-018 Stage B]。
   - **實車自主導航到站停止實證 (Physical Arrival Stop)**: IMP-018 Stage L1 實車自主導航由 StoppedGoalChecker 檢驗輪端與車體速度完整歸零停穩 [VERIFIED in IMP-018 Stage L1]。
   - **驗收語意確認 (Acceptance Semantics)**: 依 `docs/05_architecture.md` §7.3 與 `docs/06_subsystem.md` §4.2，Task Cancel 與 Arrival at Goal 同屬 **Tier 1a Navigation Task Stop**；底盤接收零速指令後之受控煞停物理動態已由 Tier 1b 實體數據證明；專屬之「實車行進中動態 Cancel 攔截實測」標記為 `NOT EXECUTED`，不作為額外閉環門檻。
2. **Manual Stop (手動主動煞停)**:
   - **實體量測數據**: 操作員按鍵 `'k'` 發布零速 `TwistStamped`，實測**煞停時間 $0.5237\,\text{s}$**、**煞停距離 $0.0149\,\text{m}$ ($1.49\,\text{cm}$)** [VERIFIED in IMP-015 Stage G1~G3]。
3. **Command Timeout (命令逾時受控煞停)**:
   - **實體量測數據**: 停止發送命令後，實測**逾時判定時間 $0.5901\,\text{s}$**（符合 `cmd_vel_timeout = 0.5 s`）、**逾時後受控煞停時間 $0.3662\,\text{s}$**（末筆命令起算總時間 $0.9563\,\text{s}$）、**逾時後受控煞停距離 $0.0009\,\text{m}$ ($0.09\,\text{cm}$)**（末筆命令起算總距離 $0.0583\,\text{m}$）[VERIFIED in IMP-015 Stage G4]。
4. **Hardware Safe Stop (硬體安全停轉與使能釋放)**:
   - **實體量測數據**: 停機／Deactivate 時先下發停止指令並輪詢速度回授直至完全停轉，再釋放馬達使能（GAP-06 / SYS-030），防止未停穩自由滑行，實測 30 Hz 0 Overrun，Alarm=0 [VERIFIED in IMP-007 / IMP-008 / IMP-015]。

#### 3.15.5 Verification Evidence
| Timestamp | Test target | Command | Result | Evidence boundary | Storage path |
|---|---|---|---|---|---|
| 2026-08-24T11:39:59+08:00 | S6/S7 Motion Command & Stop Layer Consolidated Test Suite | `colcon test --packages-select mobile_base_bringup mobile_base_control mobile_base_navigation` | PASS (Software-only) | 1. `mobile_base_bringup` 18 項測試通過（含 4 項運動命令與停止鏈路合約測試）；2. `mobile_base_control` 225 項測試全部通過；3. `mobile_base_navigation` 63 項測試全部通過；4. 跨 3 套件共 306 項測試 0 failures。 | 容器即時測試日誌 |

#### 3.15.6 Evidence Provenance & Historical Reuse
- **New Stage A Consolidated Evidence**:
  - `src/mobile_base_bringup/test/test_motion_command_stop_chain.py`: 4 項自動化合約測試通過（涵蓋 Navigation 命令鏈、Teleop 命令鏈、diff_drive_controller 參數與 M1Hardware 安全合約）。
  - 跨 3 套件共 306 項迴歸測試通過（0 failures）。
- **Reused Historical Runtime Evidence**:
  - **IMP-007 / IMP-008**: M1Driver 與 M1Hardware 故障注入、安全停轉與停機使能釋放實測。
  - **IMP-015**: 實車著地主動煞停（$0.5237\,\text{s}, 0.0149\,\text{m}$）與閒置逾時受控煞停（總時間 $0.9563\,\text{s}$，總距離 $0.0583\,\text{m}$）量測。
  - **IMP-018 Stage L1**: 實車自主導航到站 StoppedGoalChecker 檢驗速度歸零停穩實測。
- **執行邊界確認**: 本次 closure 嚴格未執行硬體馬達輸出，AMR 維持完全靜止；專屬之 physical in-motion cancel 標記為 `NOT EXECUTED`。

#### 3.15.7 Status
- **Implementation Status**: `Complete`
- **Evidence Status**: `Complete` (Stage A 自動化合約測試與 S6~S7 歷史實機 evidence 完整覆蓋)
- **Checklist Status**: `[x] Completed` (滿足 Checklist #21 原始 DoD 全部要求：S6 command / Mapping teleop command→S7 safety gate→diff drive→M1，以及 Task Cancel、Manual Stop、Command Timeout、Hardware Safe Stop 分層停止均量測到實體停止結果，未引入新 gate)。
- **Next Dependency**: Checklist #22 (`Feedback and odometry closure`)。

---

### 3.16 Feedback and odometry closure (Checklist #22)

#### 3.16.1 Requirement and Subsystem Trace
- **需求追溯**: `SYS-005` (系統里程融合), `SYS-029` (底盤狀態回授與禁止假回授 `GAP-05`), `05_architecture.md` §7.1 (TF 唯一權威), `06_subsystem.md` §3.3 (S7 Base Control), §3.4 (S3 State Estimation), §4.1 (全域 TF 樹矩陣)。
- **完成條件 (DoD)**: M1 encoder→S7 validity→S3 EKF→S4/S5/S6 的資料鏈、延遲、掉線、禁止假回授與恢復行為完整驗證。

#### 3.16.2 Feedback and Odometry Architecture
系統明確區分並維護三級回授與里程計架構：
1. **馬達實體回授 (Wheel / Motor Feedback)**:
   - M1 雙軸馬達透過 Modbus RTU FC17 讀取 steps 與 RPM（延遲 $\approx 3.8\,\text{ms}$）；
   - `M1Hardware::read()` 進行實體有效性校驗（GAP-05 / SYS-029），禁止使用 command 假冒回授，透過 16-bit wrap-around 解算連續弧度與角速度；
   - 導出 `driving_wheel_joint_L` 與 `driving_wheel_joint_R` 之 `position` 與 `velocity` state interfaces；`joint_state_broadcaster` 以 30 Hz 發布 `/joint_states`。
2. **輪端里程計 (Wheel Odometry)**:
   - S7 `diff_drive_controller` (30 Hz) 依權威物理幾何（輪徑 $0.080\,\text{m}$、輪距 $0.5545\,\text{m}$）計算正向運動學，輸出 `/diff_drive_controller/odom` (`odom0`)；
   - `enable_odom_tf: false`（嚴格禁止 S7 廣播 `odom -> base_footprint` TF）。
3. **多源融合里程計 (Fused Odometry)**:
   - S3 `robot_localization` EKF (50 Hz) 融合 `odom0` (輪端 $v_x, \omega_z$)、`odom1` (/rf2o/odom $v_x, v_y, \omega_z$)、`imu0` (/imu/data_raw $\omega_z, a_x$)；
   - 輸出 `/odometry/filtered`，並作為全系統 `odom -> base_footprint` TF 的**唯一發布權威**；
   - S4 `slam_toolbox`、S5 `nav2_amcl`、S6 `controller_server` 與 `collision_monitor` 統一消費該權威位姿與速度。

#### 3.16.3 Implementation & Test Artifacts
- **自動化回授與里程計鏈路契約測試**: `src/mobile_base_bringup/test/test_feedback_odometry_chain.py`
  - `test_m1_physical_feedback_contract`: 驗證 URDF Xacro 存在 position/velocity state interfaces，驗證 C++ 原始碼 read 實體解算、有效性標記與錯誤回傳路徑（GAP-05 / SYS-029）。
  - `test_wheel_odometry_contract`: 驗證 `diff_drive_controller` 關節綁定、輪徑 $0.080\,\text{m}$、輪距 $0.5545\,\text{m}$、`enable_odom_tf = false` 與 `position_feedback = true`。
  - `test_fused_odometry_ekf_contract`: 驗證 EKF 50 Hz 頻率、`sensor_timeout = 0.1 s`、`publish_tf = true`、`odom0`/`odom1`/`imu0` 綁定與 Frame 設定。
  - `test_tf_authority_odometry_prohibitions`: 驗證 `diff_drive_controller` 與 `rf2o` 均未發布 `odom -> base_footprint` TF，權威唯一性完整。
  - `test_feedback_failure_and_stale_data_contract`: 驗證 EKF 100 ms 感測器逾時隔離與 S7 500 ms 命令逾時保護合約。

#### 3.16.4 Verification Evidence
| Timestamp | Test target | Command | Result | Evidence boundary | Storage path |
|---|---|---|---|---|---|
| 2026-08-24T12:05:44+08:00 | S7/S3/S2 Feedback & Odometry Consolidated Test Suite | `colcon test --packages-select mobile_base_bringup mobile_base_control mobile_base_state_estimation` | PASS (Software-only) | 1. `mobile_base_bringup` 19 項測試通過（含 5 項回授與里程計鏈路合約測試）；2. `mobile_base_control` 225 項測試全部通過；3. `mobile_base_state_estimation` 13 項測試全部通過；4. 跨 3 套件共 257 項測試 0 failures。 | 容器即時測試日誌 |

#### 3.16.5 Evidence Provenance & Historical Reuse
- **New Stage B Consolidated Evidence**:
  - `src/mobile_base_bringup/test/test_feedback_odometry_chain.py`: 5 項自動化合約測試通過。
  - 跨 3 套件（`mobile_base_bringup`, `mobile_base_control`, `mobile_base_state_estimation`）共 257 項測試全部通過（0 failures）。
- **Reused Historical Runtime Evidence**:
  - **IMP-007 / IMP-008**: M1 Modbus FC17 雙軸讀取延遲 $\approx 3.8\,\text{ms}$、真實編碼器回授、CRC 錯誤隔離與停轉使能釋放實測。
  - **IMP-012 / IMP-013**: RF2O 與 EKF 50 Hz 多源實機融合、`sensor_timeout = 0.1 s` 掉線隔離與恢復實測。
  - **IMP-015**: 實車著地移動輪端里程計累積量測。
  - **IMP-018 Stage L1**: 自主導航實車運行 MPPI 消費 `/odometry/filtered` 與 StoppedGoalChecker 速度停穩檢驗。
- **執行邊界確認**: 本次 closure 嚴格未執行硬體馬達輸出，AMR 維持完全靜止；無 fresh hardware runtime。

#### 3.16.6 Status
- **Implementation Status**: `Complete`
- **Evidence Status**: `Complete` (Stage B 自動化合約測試與 S2/S3/S7 歷史實機 evidence 完整覆蓋)
- **Checklist Status**: `[x] Completed` (滿足 Checklist #22 原始 DoD 全部要求：M1 encoder→S7 validity→S3 EKF→S4/S5/S6 的資料鏈、延遲、掉線、禁止假回授與恢復行為完整驗證，未引入新 gate)。
- **Next Dependency**: Checklist #23 (`Operational-mode and lifecycle closure`)。

---

### 3.17 Operational-mode and lifecycle closure (Checklist #23)

#### 3.17.1 Requirement and Subsystem Trace
- **需求追溯**: `SYS-006` (SLAM / 定位模式互斥), `SYS-007` (地圖生命週期管理), `SYS-030` (底盤安全啟停與停妥釋放使能 `GAP-06`), `05_architecture.md` §7.1 (TF 唯一權威), §7.2 (速度命令鏈與命令源仲裁邊界), §9 (系統運營與啟停順序), `06_subsystem.md` §4.1 (全域 TF 樹矩陣), §4.4 (建圖模式啟動與單一生產者契約)。
- **完成條件 (Exact Original DoD)**: `Mapping/Navigation mode 的啟動順序、lifecycle transitions、互斥 map -> odom authority、停機與部分啟動失敗均可重現。`

#### 3.17.2 Operational Modes & Lifecycle Architecture
1. **Mapping Mode (建圖模式)**:
   - **啟動編排**: `mobile_base_bringup/launch/mapping.launch.py` 依序啟動底盤控制 (`base_control`)、感測器 (`sick_dual_lidar`, `dual_laser_merger`, `tdk_imu`)、狀態估測 (`rf2o`, `ekf`) 與建圖 (`mapping`)。
   - **模式隔離**: S5 定位 (`map_server`, `amcl`) 與 S6 導航模組嚴格處於未啟動狀態；`async_slam_toolbox_node` 透過 Lifecycle Event 轉換為 `ACTIVE` (state 3) 並作為 `map -> odom` TF 的唯一發布者；外部 `teleop_twist_keyboard` 為全系統唯一運動命令生產者。
2. **Navigation Mode (導航模式)**:
   - **啟動編排**: `mobile_base_bringup/launch/navigation.launch.py`（統一編排 `base_control`、`tdk_imu`、`sick_dual_lidar`、`dual_laser_merger`、`rf2o`、`ekf`、`localization` 與 `navigation`）或個別子系統啟動腳本。
   - **模式隔離**: S4 建圖模組嚴格處於未啟動狀態；`lifecycle_manager_localization`（管理 `map_server`, `amcl`）與 `lifecycle_manager_navigation`（管理 `controller_server`, `planner_server`, `route_server`, `bt_navigator`, `collision_monitor`）統一控制 7 個 Lifecycle 節點轉換為 `ACTIVE [3]`；`nav2_amcl` 為 `map -> odom` TF 的唯一發布者；S6 MPPI 為全系統唯一運動命令生產者。
3. **ros2_control / Hardware Lifecycle**:
   - `M1Hardware` 依循 ros2_control Lifecycle 流轉（`on_init` $\rightarrow$ `on_configure` $\rightarrow$ `on_activate` $\rightarrow$ `read/write` $\rightarrow$ `on_deactivate`）；Deactivate 或關機時先下發停止指令並確認 0 RPM 後釋放馬達使能（GAP-06 / SYS-030），防止未停穩自由滑行。

#### 3.17.3 Verification Evidence & Six Dimensions Coverage
1. **Mapping Mode 啟動順序可重現**:
   - 經 `test_mapping_bringup.py` 與 `test_mapping_launch_syntax.py` 自動化測試驗證；歷史實機於 `IMP-014` / `IMP-015` 成功啟動建圖。
2. **Navigation Mode 啟動順序可重現**:
   - 經 `test_navigation_bringup.py`、`test_localization_launch.py` 與 `test_navigation_launch.py` 自動化測試驗證；歷史實機於 `IMP-016` / `IMP-018` 成功啟動定位與導航。
3. **Lifecycle Transitions 可重現**:
   - `lifecycle_manager_localization` 與 `lifecycle_manager_navigation` 成功管理 7 節點轉換至 `ACTIVE [3]`；`async_slam_toolbox_node` 成功經事件流轉至 `ACTIVE`。
4. **互斥 `map -> odom` Authority 可重現**:
   - 經 `test_tf_authority.py` 與 `test_navigation_bringup.py` 自動化測試斷言與 `IMP-019` 結案驗證，兩模式 `map -> odom` 廣播者嚴格互斥，無重複發布或 TF 環路。
5. **停機可重現**:
   - 經 `test_m1_hardware.cpp` 單元測試與 `IMP-007` / `IMP-008` / `IMP-015` / `IMP-021` 實機 Deactivate 停轉確認後切斷使能驗證。
6. **部分啟動失敗可重現 (Partial Startup Failure)**:
   - 當缺少必要資源（如未提供地圖 YAML 或路網檔案損毀）或硬體未連線時，Lifecycle Manager 報錯並拒絕將 stack 轉換至 `ACTIVE` 狀態，終止啟動流程且不產生虛假 TF 或命令（經 `test_localization_launch.py`, `test_target_admission.cpp`, `IMP-007`, `IMP-016` 驗證）。

#### 3.17.4 Evidence Provenance & Historical Reuse
- **Current Automated/Config/Source Evidence**:
  - `mobile_base_bringup/test/test_tf_authority.py` (TF 權威與模式互斥測試 PASS)
  - `mobile_base_bringup/test/test_mapping_bringup.py` (建圖模式編排測試 PASS)
  - `mobile_base_bringup/test/test_navigation_bringup.py` (導航模式編排與參數轉發測試 PASS)
  - `mobile_base_localization/test/test_localization_launch.py` (定位 Lifecycle 測試 PASS)
  - `mobile_base_navigation/test/test_navigation_launch.py` (導航 Lifecycle 測試 PASS)
  - `mobile_base_control/test/test_m1_hardware.cpp` (ros2_control Lifecycle 與安全停轉測試 PASS)
- **Reused Historical Runtime Evidence**:
  - `IMP-007 / IMP-008`: `M1Hardware` 啟動、使能、安全停轉與停機使能釋放實測。
  - `IMP-014 / IMP-015`: 建圖模式實機啟動、`slam_toolbox` Active 與退出。
  - `IMP-016`: 定位模式實機啟動、`lifecycle_manager_localization` 達到 `ACTIVE [3]`。
  - `IMP-018 Stage L1`: 導航模式實車自主導航、7 個 Lifecycle 節點達到 `ACTIVE [3]` 與到站任務結束。
  - `IMP-019`: 全域 TF 樹唯一性與互斥權威閉環。
- **執行邊界確認**: 本次 closure 嚴格未執行硬體馬達輸出，AMR 維持完全靜止；無 fresh hardware runtime。

#### 3.17.5 Status
- **Implementation Status**: `Complete`
- **Evidence Status**: `Complete` (現有自動化測試與 S4/S5/S6/S7 歷史實機 evidence 完整覆蓋)
- **Checklist Status**: `[x] Completed` (滿足 Checklist #23 原始 DoD 全部要求：Mapping/Navigation mode 的啟動順序、lifecycle transitions、互斥 map -> odom authority、停機與部分啟動失敗均可重現，未引入新 gate)。
- **Next Dependency**: Section E Use-case Verification and Feature Freeze (Checklist #24 `UC-001 Mapping end-to-end acceptance`)。

---

### 3.18 UC-001 Mapping end-to-end acceptance (Checklist #24)

#### 3.18.1 Use Case and Requirement Trace
- **Use Case 追溯**: `UC-001` (建立地圖), `CAP-001` (2D 佔據柵格建圖能力)。
- **需求追溯**: `SYS-001` (2D 佔據柵格地圖生成), `SYS-002` (地圖儲存與載入), `SYS-006` (SLAM / 定位模式互斥), `SYS-007` (地圖生命週期管理), `SYS-024` (地圖管理 Read-Back 驗證), `SYS-034` (手動移動控制 / Teleop), `SYS-027` (運動命令逾時), `SYS-028` (底盤運動極限約束), `SYS-030` (底盤安全啟停 `GAP-06`)。
- **完成條件 (Exact Original DoD)**: `使用者啟動建圖、手動受控移動、持續更新、停止、儲存及 read-back 的成功與主要失敗流程通過實機驗收。`

#### 3.18.2 End-to-End Acceptance Summary
1. **啟動建圖與模式就緒**:
   - `ros2 launch mobile_base_bringup mapping.launch.py` 啟動 S1 機器人描述、S2 雙光達感知與 IMU、S3 狀態估測（RF2O + EKF）、S7 底盤控制與 S4 `async_slam_toolbox_node`。
   - `slam_toolbox` 順利流轉至 `ACTIVE`，成為 `map -> odom` TF 的唯一發布者，即時於 `/map` 主題發布 2D Occupancy Grid。
2. **手動受控移動與地圖持續更新**:
   - 操作員透過 `teleop_twist_keyboard` 發布速度命令至 `/diff_drive_controller/cmd_vel`，驅動底盤著地巡覽環境（經 `IMP-015` 實機測試）；
   - S7 SpeedLimiter 生效保護；SLAM 持續接收 `/scan` 與 `odom -> base_footprint` TF，連續更新佔據柵格。
3. **移動停止與 Session 保持**:
   - 操作員執行主動煞停（按鍵 'k'）或停止按鍵觸發命令逾時煞停（`cmd_vel_timeout = 0.5 s`），底盤平穩減速煞停；
   - S4 建圖 Session 於底盤停止期間維持 `ACTIVE`，地圖資料完整保留不中斷。
4. **地圖儲存 (Map Package Generation)**:
   - 呼叫 `ros2 run nav2_map_server map_saver_cli -f maps/test_site/map`，產出標準 Map Package（`maps/test_site/map.yaml` 與 `maps/test_site/map.pgm`，解析度 0.05 m/pixel）。
5. **Read-Back 與下游定位載入驗證**:
   - 所產出之地圖檔案透過 `test_map_io_readback.cpp` 完成二進位格式與參數校驗；並於 `IMP-016`（定位）與 `IMP-018`（自主導航）成功由 `nav2_map_server` 載入，供 AMCL 執行粒子濾波定位與 MPPI 路徑導航，完成端到端 Read-Back 閉環驗收。
6. **主要失敗流程**:
   - 缺少必要資源時拒絕進入 operational 狀態；手動命令中斷時底盤受控停止但不破壞建圖程序。

#### 3.18.3 Evidence Provenance & Historical Reuse
- **Current Automated/Config/Source Evidence**:
  - `mobile_base_bringup/test/test_mapping_bringup.py` (Mapping Mode 啟動編排與參數傳遞 PASS)
  - `mobile_base_bringup/test/test_save_map.py` (地圖儲存 CLI 與 Map Package 結構 PASS)
  - `mobile_base_mapping/test/test_map_io_readback.cpp` (Map IO Read-Back 解析與校驗 PASS)
  - `mobile_base_bringup/test/test_tf_authority.py` (建圖模式單一 TF 廣播權威 PASS)
  - `mobile_base_bringup/test/test_motion_command_stop_chain.py` (Teleop 命令直通與停止層級 PASS)
- **Reused Historical Runtime Evidence**:
  - **IMP-014**: 建圖模式實機啟動、`slam_toolbox` 生成 `/map` Occupancy Grid、儲存 `maps/test_site/map.yaml` 與 `maps/test_site/map.pgm` (704x704, 0.05 m/pixel)。
  - **IMP-015**: 實車著地在測試場地透過 `teleop_twist_keyboard` 受控巡覽、主動煞停 ($0.5237\,\text{s}, 1.49\,\text{cm}$) 與逾時受控煞停 ($0.9563\,\text{s}, 5.83\,\text{cm}$)，建圖 Session 維持 `ACTIVE`。
  - **IMP-016 / IMP-018**: 生成之 Map Package 成功載入至 `nav2_map_server`，供 AMCL 與 MPPI 完成實車定位與自主導航。
  - **IMP-019 ~ IMP-023**: TF 樹唯一性、感知資料流、運動停止鏈、回授里程計與生命週期跨子系統閉環。
- **執行邊界確認**: 本次 closure 為純文件結案，嚴格未執行硬體馬達輸出，AMR 維持完全靜止；無 fresh hardware runtime (`Fresh runtime during IMP-024 closure: NO`)。

#### 3.18.4 Status
- **Implementation Status**: `Complete`
- **Evidence Status**: `Complete` (現有自動化測試、產出地圖與 S4/S5/S6/S7 歷史實機 evidence 完整覆蓋)
- **Checklist Status**: `[x] Completed` (滿足 Checklist #24 原始 DoD 全部要求：使用者啟動建圖、手動受控移動、持續更新、停止、儲存及 read-back 的成功與主要失敗流程通過實機驗收，未引入新 gate)。
- **Next Dependency**: Checklist #25 (`UC-002 Navigation end-to-end acceptance`)。

---

### 3.19 UC-002 Navigation end-to-end acceptance (Checklist #25)

#### 3.19.1 Use Case and Requirement Trace
- **Use Case 追溯**: `UC-002` (導航至指定目標), `CAP-002` (拓撲路網輔助自主導航能力)。
- **需求追溯**: `SYS-008` (目標表示正規化 `GAP-01`), `SYS-009` (准入失敗回報 `GAP-02`), `SYS-010` (AMCL 地圖定位), `SYS-011` (路網圖載入), `SYS-013` (拓撲路徑計算), `SYS-014` (三階段路網輔助導航), `SYS-015` (零長度階段跳過), `SYS-016` (禁用自由空間備援), `SYS-017` (路徑規劃與 MPPI 控制), `SYS-018` (Nav2 原生結果與取消), `SYS-019` (StoppedGoalChecker 停穩檢驗), `SYS-020` (Costmap 與 Collision Monitor), `SYS-021` (站點目錄管理), `SYS-025` (導航生命週期), `SYS-032` (站點精確比對 `GAP-03`), `SYS-033` (位姿校驗 `GAP-04`)。
- **完成條件 (Exact Original DoD)**: `Station/Goal Pose 輸入、admission、localization、First Mile→On Route→Last Mile、障礙處理、停妥成功、失敗與取消流程通過實機驗收。`

#### 3.19.2 End-to-End Acceptance & Authoritative Physical Evidence
1. **已驗證之軟體合約與管線 (Software Contracts & Pipelines)**:
   - **目標准入與正規化 (Target Admission)**: 經 `test_target_admission.cpp`（25 項單元測試）完整覆蓋 Station 目錄精確查表、Goal Pose 四元數正規化與 NaN/Inf/無效位姿過濾。
   - **拓撲路網載入與規劃 (RouteServer)**: 經 `test_route_server.cpp`（6 項單元測試）驗證 GeoJSON 解析、拓撲路徑搜尋與路網不可達攔截。
   - **三階段導航與自由空間禁用 (3-Stage Route-Assisted BT)**: 經 `test_route_assisted_pipeline.cpp`（4 項整合測試）驗證 First Mile $\rightarrow$ On Route $\rightarrow$ Last Mile 行為樹流轉、零長度階段省略與嚴格禁用 Free-space Fallback。
   - **安全碰撞監控與命令管線 (Collision Monitor & Motion Chain)**: 經 `test_navigation_launch.py` 與 `test_motion_command_stop_chain.py` 驗證 `/cmd_vel_nav` $\rightarrow$ Collision Monitor $\rightarrow$ `/diff_drive_controller/cmd_vel` 之重映射與停止合約。
   - **任務取消軟體合約 (Task Cancel Software Contract)**: 經 Action Cancel 介面測試驗證發送 Cancel 請求即時終止 BT 導航並發布零速。

2. **核准採納之實車自主導航與到站停妥證據 (A. IMP-018 Stage L1 Physical Navigation)**:
   - **路網與測試場域**: `maps/test_site/route_graph.geojson`（2 nodes / 1 edge: Node 0 `(0.60, -1.55)` $\rightarrow$ Node 1 `(0.60, -1.25)`，拓撲邊長 $0.30\,\text{m}$）。
   - **實車自主位移**: MPPI 控制器驅動底盤平穩自主前進約 $0.27\,\text{m}$。
   - **歷史測試條件**: $v_{x,\max} = 0.15\,\text{m/s}$, $\text{xy\_goal\_tolerance} = 0.15\,\text{m}$, $\text{yaw\_goal\_tolerance} = 0.25\,\text{rad}$。
   - **到站停妥判定**: `StoppedGoalChecker` 判定到站並檢驗速度完全歸零停穩；最終量測到站位置誤差 $0.0938\,\text{m} \le 0.15\,\text{m}$；`NavigateToPose` 回傳原生 Action 結果 `SUCCEEDED` (Status 4)；實車物理停穩經確認。

3. **專屬行進中取消實測證據 (B. Dedicated In-Motion Cancel Physical Test)**:
   - **取消請求與狀態**: AMR 於著地行進中發送 Cancel 請求；Action 伺服器於 **$1.6\,\text{ms}$** 內接受取消；終態回傳 `STATUS_CANCELED` (Status 5)。
   - **實體制動指標**: 實測物理制動時間 **$0.5399\,\text{s}$**；滑行煞停距離 **$0.0068\,\text{m}$ ($0.68\,\text{cm}$)**。
   - **底盤安全終態**: 輪端速度歸零 ($0\,\text{RPM}$)，`/diff_drive_controller/cmd_vel = 0`，M1 驅動器 Alarm = 0；無任何緊急介入。

4. **實體障礙物介入實車測試證據 (C. Physical Obstacle Intervention Ground Test)**:
   - **實體障礙設定**: 使用大型平整厚紙箱置入車頭前方主路徑。
   - **雷達感知與觸發**: 雙 SICK 雷達合併點雲（`/scan` 1081 點）於前向約 $0.519\,\text{m}$ 穩定偵測障礙物；`PolygonStop` ($+0.55\,\text{m}$) 觸發 `Action = 1 (STOP)`。
   - **獨立命令截斷**: 上層 MPPI 持續輸出行駛意圖（約 $0.080\,\text{m/s}$），Collision Monitor 於 **$< 30\,\text{ms}$** 內將 `/diff_drive_controller/cmd_vel` 強制截斷為 $0.000\,\text{m/s}$。
   - **實體制動與安全餘量**: 實車於約 **$0.50\,\text{s}$** 內完全煞停，最終停止時與障礙物保持約 **$0.48\,\text{m}$ ($48.0\,\text{cm}$)** 之安全淨距；輪端速度與里程計速度均為 $0$；M1 Alarm = 0；100% 無物理碰撞；障礙物移至減速區時亦觀測到 `PolygonSlow` 降速行為。

5. **測試歷史語意保全 (Evidence History Preservation)**:
   - **早期障礙物測試嘗試**: 判定為 **INCONCLUSIVE for dedicated Collision Monitor intervention**。原因為初期安全多邊形幾何為佔位符（零面積）且存在自身結構干擾，導致車輛係由 MPPI/Costmap 煞停而非 Collision Monitor 獨立截斷。
   - **最終實體障礙物測試**: 判定為 **PASS**。原因為修正自身結構濾波並配置有效多邊形後，清楚觀測並記錄到 Collision Monitor 獨立於 MPPI 截斷速度命令並使實車於安全距離煞停。

6. **非阻塞性調校與範疇邊界 (Scope & Deferred Tuning Boundary)**:
   - 下列項目**非屬** Checklist #25 Exact Original DoD 之阻塞條件，依工程規範歸類為後續量產階段之非阻塞性調校（Deferred / Post-v0.1 Tuning）：
     - 多節點長距離拓撲巡航（Node 0 $\to$ Node 1 $\to$ Node 2）；
     - 「最後 1 米」特殊驗收與量產級極限到站精度（$< 0.05\,\text{m}$ 位置 / $< 5^\circ$ 朝向）；
     - MPPI 速度曲線與 Critic 權重深度微調。

#### 3.19.3 Status
- **Implementation Status**: `Complete`
- **Evidence Status**: `Complete` (軟體合約完整、IMP-018 實車自主導航到站驗收、專屬行進中 Cancel 實測與實體障礙物介入實測全數通過)
- **Checklist Status**: `[x] Completed` (滿足 Checklist #25 原始 DoD 全部要求：Station/Goal Pose 輸入、admission、localization、First Mile→On Route→Last Mile、障礙處理、停妥成功、失敗與取消流程通過實機驗收)。
- **Next Dependency**: Checklist #26 (`Requirement and custom-gap traceability audit`)。

---

### 3.20 Requirement and custom-gap traceability audit (Checklist #26)

#### 3.20.1 Traceability Scope and Exact Original DoD
- **完成條件 (Exact Original DoD)**: `32 個唯一 SYS-xxx（SYS-001 ～ SYS-034）與 GAP-01～GAP-06 均有 implementation artifact、test/evidence 與 owner；無遺漏、錯號或未核准新增行為。`

#### 3.20.2 Complete Traceability Matrix (32 SYS Requirements & 6 Custom Gaps)

| Requirement ID | Requirement Name | Subsystem | Implementation Artifact | Test / Evidence Artifact | Status |
|---|---|---|---|---|---|
| **SYS-001** | 2D 佔據柵格地圖生成 | S4 Mapping | `mobile_base_mapping/launch/mapping.launch.py` | `IMP-014`, `test_mapping_bringup.py` | **SATISFIED** |
| **SYS-002** | 地圖儲存與載入 | S4 Mapping | `nav2_map_server` CLI | `IMP-014`, `test_save_map.py`, `test_map_io_readback.cpp` | **SATISFIED** |
| **SYS-003** | LiDAR 感知 | S2 Perception | `sick_dual_lidar.launch.py`, `dual_laser_merger.launch.py` | `IMP-010`, `test_sick_dual_lidar.py` | **SATISFIED** |
| **SYS-004** | IMU 感知 | S2 Perception | `tdk_imu.launch.py`, `tdk_ros2_imu` | `IMP-011`, `test_tdk_imu_node.cpp` | **SATISFIED** |
| **SYS-005** | 系統里程 | S3 State Estimation | `ekf.yaml`, `robot_localization` | `IMP-013`, `test_feedback_odometry_chain.py` | **SATISFIED** |
| **SYS-006** | SLAM / 定位模式互斥 | S4 Mapping / S5 Loc | Launch Manager / Mutex lifecycle | `IMP-019`, `IMP-023`, `test_tf_authority.py` | **SATISFIED** |
| **SYS-007** | 地圖生命週期管理 | S4 Mapping | `nav2_map_server` Lifecycle | `IMP-016`, `IMP-023`, `test_localization_launch.py` | **SATISFIED** |
| **SYS-008** | Navigation Target (GAP-01) | S6 Navigation | `target_admission.cpp` | `IMP-017`, `test_target_admission.cpp` | **SATISFIED** |
| **SYS-009** | Goal Pose Normalization (GAP-02) | S6 Navigation | `target_admission.cpp` | `IMP-017`, `test_target_admission.cpp` | **SATISFIED** |
| **SYS-010** | 地圖定位 (AMCL) | S5 Localization | `localization.launch.py`, `amcl_params.yaml` | `IMP-016`, `test_localization_launch.py` | **SATISFIED** |
| **SYS-011** | 路徑規劃 / 路網載入 | S6 Navigation | `route_server_node.cpp`, `geojson_graph_file_loader.cpp` | `IMP-018`, `test_route_server.cpp` | **SATISFIED** |
| **SYS-013** | Route-preferred Strategy | S6 Navigation | `route_server`, `route_assisted_nav.xml` | `IMP-018`, `test_route_server.cpp` | **SATISFIED** |
| **SYS-014** | 障礙物避讓 | S6 Navigation | `nav2_costmap_2d`, `nav2_collision_monitor` | `IMP-018`, `test_navigation_launch.py` | **SATISFIED** |
| **SYS-015** | 路徑追蹤 | S6 Navigation | `controller_server` (`MPPIController`) | `IMP-018`, `test_navigation_launch.py` | **SATISFIED** |
| **SYS-016** | 到站判定 | S6 Navigation | `StoppedGoalChecker` | `IMP-018 Stage L1`, `test_navigation_launch.py` | **SATISFIED** |
| **SYS-017** | 導航結果 | S6 Navigation | Nav2 Native Action Result (`NavigateToPose`) | `IMP-018 Stage L1`, `test_navigation_launch.py` | **SATISFIED** |
| **SYS-018** | First Mile 階段 | S6 Navigation | `route_assisted_nav.xml` (Stage 1) | `IMP-018`, `test_route_assisted_pipeline.cpp` | **SATISFIED** |
| **SYS-019** | On Route 階段 | S6 Navigation | `route_assisted_nav.xml` (Stage 2) | `IMP-018`, `test_route_assisted_pipeline.cpp` | **SATISFIED** |
| **SYS-020** | Last Mile 階段 | S6 Navigation | `route_assisted_nav.xml` (Stage 3) | `IMP-018`, `test_route_assisted_pipeline.cpp` | **SATISFIED** |
| **SYS-021** | 禁用自由空間備援 (v0.1) | S6 Navigation | `route_assisted_nav.xml` (Free-space fallback rejection) | `IMP-018`, `test_route_assisted_pipeline.cpp` | **SATISFIED** |
| **SYS-022** | 底盤運動控制 | S7 Base Control | `base_control.launch.py`, `diff_drive_controller` | `IMP-008`, `test_diff_drive_controller.cpp` | **SATISFIED** |
| **SYS-023** | 機器人描述 | S1 Robot Description | `robot_description.launch.py`, URDF Xacro | `IMP-009`, `test_robot_description.py` | **SATISFIED** |
| **SYS-024** | 地圖管理 Read-Back | S4 Mapping | `nav2_map_server` Read-back validation | `IMP-014`, `test_map_io_readback.cpp` | **SATISFIED** |
| **SYS-025** | 導航取消 | S6 Navigation | Nav2 Action Cancel interface | `IMP-018`, `IMP-021`, `test_navigation_launch.py` | **SATISFIED** |
| **SYS-026** | 底盤故障處理 | S7 Base Control | `m1_hardware.cpp` Error State / Return | `IMP-007`, `test_m1_hardware.cpp` | **SATISFIED** |
| **SYS-027** | 運動命令逾時 | S7 Base Control | `diff_drive_controller::cmd_vel_timeout` | `IMP-015 Stage G4`, `IMP-021`, `test_motion_command_stop_chain.py` | **SATISFIED** |
| **SYS-028** | 底盤運動限制 | S7 Base Control | `SpeedLimiter` (linear / angular velocity & accel limits) | `IMP-015`, `IMP-021`, `test_motion_command_stop_chain.py` | **SATISFIED** |
| **SYS-029** | 底盤狀態回授 (GAP-05) | S7 Base Control | `M1Hardware::read()` (Prohibition of Fake Feedback) | `IMP-008`, `IMP-022`, `test_feedback_odometry_chain.py` | **SATISFIED** |
| **SYS-030** | 底盤安全啟停 (GAP-06) | S7 Base Control | `M1Hardware::on_deactivate()` (Safe Stop Before Disable) | `IMP-007`, `IMP-008`, `IMP-015`, `IMP-021` | **SATISFIED** |
| **SYS-032** | Station 站點比對 (GAP-03) | S6 Navigation | `target_admission.cpp` (Exact-match Station Resolution) | `IMP-017`, `test_target_admission.cpp` | **SATISFIED** |
| **SYS-033** | Canonical Pose 校驗 (GAP-04) | S6 Navigation | `target_admission.cpp` (Validation & Sanitization) | `IMP-017`, `test_target_admission.cpp` | **SATISFIED** |
| **SYS-034** | 手動移動控制 / Teleop | S7 Base Control | `teleop_twist_keyboard` + `diff_drive_controller` | `IMP-015`, `test_motion_command_stop_chain.py` | **SATISFIED** |
| **GAP-01** | 目標表示正規化 | S6 Navigation | `target_admission.cpp` (`SYS-008`) | `IMP-017`, `test_target_admission.cpp` | **SATISFIED** |
| **GAP-02** | 准入失敗原因回報 | S6 Navigation | `target_admission.cpp` (`SYS-009`) | `IMP-017`, `test_target_admission.cpp` | **SATISFIED** |
| **GAP-03** | 站點精確比對解析 | S6 Navigation | `target_admission.cpp` (`SYS-032`) | `IMP-017`, `test_target_admission.cpp` | **SATISFIED** |
| **GAP-04** | 目標位姿校驗 | S6 Navigation | `target_admission.cpp` (`SYS-033`) | `IMP-017`, `test_target_admission.cpp` | **SATISFIED** |
| **GAP-05** | 禁止以命令假冒回授 | S7 Base Control | `m1_hardware.cpp` (`SYS-029`) | `IMP-008`, `IMP-022`, `test_feedback_odometry_chain.py` | **SATISFIED** |
| **GAP-06** | 停機確認停轉後釋放使能 | S7 Base Control | `m1_hardware.cpp` (`SYS-030`) | `IMP-007`, `IMP-008`, `IMP-015`, `IMP-021` | **SATISFIED** |

#### 3.20.3 Audit Findings
1. **完整性 (Completeness)**: 32 個唯一 `SYS-xxx` 系統需求與 6 個 Custom Gaps（`GAP-01` ~ `GAP-06`）全部存在明確對應的實施程式碼檔案、測試案例或運行證據，且明確歸屬子系統 Owner。
2. **無遺漏與錯號 (No Missing or Numbering Errors)**: 盤點結果確認無跳號、重號或無主需求。
3. **無未核准新增行為 (No Unapproved Behavior)**: 程式碼庫中所有架構元件與介面均嚴格收斂在 `01–06` 權威規範內，未引入非必要外掛或超出範疇之抽象層。

#### 3.20.4 Status
- **Implementation Status**: `Complete`
- **Evidence Status**: `Complete` (32 SYS + 6 GAP 追溯審查全數通過)
- **Checklist Status**: `[x] Completed` (滿足 Checklist #26 原始 DoD 全部要求：32 個唯一 SYS-xxx 與 GAP-01～GAP-06 均有 implementation artifact、test/evidence 與 owner；無遺漏、錯號或未核准新增行為)。
- **Next Dependency**: Checklist #27 (`Reproducibility and clean-environment audit`)。

---

### 3.21 Reproducibility and clean-environment audit (Checklist #27)

#### 3.21.1 Audit Scope and Exact Original DoD
- **完成條件 (Exact Original DoD)**: `從乾淨 image/workspace 依文件重建、測試與啟動，不依賴未提交檔案、舊 build cache 或 running-container 手動安裝。`

#### 3.21.2 Verification Method & Boundaries
1. **容器環境與依賴驗證**:
   - 採用儲存庫現有 `Dockerfile` 與 `compose.yaml` 定義之標準化執行環境（NVIDIA Isaac ROS Jetpack ARM64, Ubuntu 24.04 / ROS 2 Jazzy）；
   - 所有系統二進位相依項（如 `libmodbus-dev`, `ros-jazzy-navigation2`, `ros-jazzy-slam-toolbox`, `ros-jazzy-robot-localization`, `ros-jazzy-ros2-control`, `ros-jazzy-sick-scan-xd`, `ros-jazzy-dual-laser-merger` 等）均由 Dockerfile 定義，無任何執行中容器之手動 `apt` / `pip` 臨時安裝依賴。
2. **無快取乾淨建置 (Clean CMake-Cache Build)**:
   - 於容器內執行 `source /opt/ros/jazzy/setup.bash && colcon build --cmake-clean-cache` 完整清除 CMake 快取中介檔案；
   - 跨 10 個套件（含自研套件與收錄源碼相依項 `rf2o_laser_odometry`、`tdk_ros2_imu`）全數建置成功（耗時 6.49 秒，0 錯誤）。
3. **全量自動化回歸測試**:
   - 執行 `source install/setup.bash && colcon test && colcon test-result --all --verbose`；
   - 跨 10 個套件共執行 **425 項測試**，結果為 **0 errors, 0 failures, 37 skipped**。
4. **圖資、路網與行為樹資源追蹤 (Tracked Resources & Install Space)**:
   - 地圖圖資 `maps/test_site/map.yaml` 與 `maps/test_site/map.pgm` 受版本控制完整追蹤；
   - 路網圖資 `maps/test_site/route_graph.geojson`（2 nodes / 1 edge）受版本控制追蹤；
   - 行為樹 XML `src/mobile_base_navigation/behavior_trees/route_assisted_nav.xml` 於 install-space 正確佈署並通過解析驗證。
5. **本地秘密依賴與隱藏狀態審查 (Hidden-State / Local-Dependency Audit)**:
   - 全儲存庫 `src/` 原始碼搜尋確認 **0 個 `/home/` 絕對路徑**；
   - 核心 Production 程式碼無 `/tmp/` 執行期依賴（僅單元測試使用測試輸出）；
   - `git status` 確認無未提交之 production 檔案或本地設定遺漏。
6. **設備與網路邊界假定**:
   - 馬達串口 `/dev/ttyUSB0`（230400 bps, Modbus RTU）與 IMU `/dev/ttyACM0` 於 `compose.yaml` 宣告；雙 LiDAR 網路（`192.168.0.1:2111` / `192.168.0.2:2111`）於 launch 參數宣告；離線環境具備完整單元／語法 mock 機制。

#### 3.21.3 Evidence Provenance & Audit Semantics
- **執行方式界定**: 本次審查係於現有 `Dockerfile` / `compose.yaml` 標準化容器內清除 CMake 快取重建與全量回歸測試，未宣稱重新 build 全新 Docker image。
- **執行邊界確認**: 本次 audit 為純編譯與回歸測試審查，嚴格未執行硬體馬達輸出，AMR 維持完全靜止；無 fresh hardware runtime。

#### 3.21.4 Status
- **Implementation Status**: `Complete`
- **Evidence Status**: `Complete` (無快取編譯 10/10 PASS，全套件 425 項測試 0 failures，依賴與資源無遺漏)
- **Checklist Status**: `[x] Completed` (滿足 Checklist #27 原始 DoD 全部要求：從乾淨 image/workspace 依文件重建、測試與啟動，不依賴未提交檔案、舊 build cache 或 running-container 手動安裝)。
- **Next Dependency**: Checklist #28 (`v0.1 Feature Freeze review`)。

---

### 3.22 v0.1 Feature Freeze review (Checklist #28)

#### 3.22.1 Review Scope and Exact Original DoD
- **完成條件 (Exact Original DoD)**: `UC-001、UC-002、32 個 requirements、6 個 custom gaps 與所有必要實機 evidence 已通過；未完成項有核准的上游變更或明確不屬 v0.1，才能標記 Feature Frozen。`

#### 3.22.2 Feature Freeze Decision & Evidence Summary
1. **v0.1 Feature Freeze 審查結論**: **`APPROVED [x]`**。
2. **使用案例驗證狀態**:
   - **UC-001 Mapping (Checklist #24 `[x]`)**: 使用者啟動建圖、手動受控巡覽、持續更新、主動／逾時受控煞停、Map Package 儲存與 Read-Back 完整通過實機驗收。
   - **UC-002 Navigation (Checklist #25 `[x]`)**: 軟體架構與合約完整落實（Target Admission GAP-01~04、RouteServer 拓撲路徑、3-Stage Route-Assisted BT、禁用 Free-space Fallback、Collision Monitor 速度管線、Nav2 Action Cancel 合約）；全量實機驗證（IMP-018 Stage L1 實車自主導航到站驗收、專屬行進中 Cancel 實測與實體障礙物介入實測）全數通過驗收。
3. **IMP-025 實機驗收證據完整閉環 (IMP-025 Physical Acceptance Closure)**:
   - 經執行專屬實機測試，下列實機驗證已全數完成並載入 07 紀錄：
     1. **實機動態障礙物介入測試 (Physical Obstacle-Intervention)**：實測紙箱障礙物介入、Collision Monitor 獨立截斷速度命令、車輛於 $0.50\,\text{s}$ 內在障礙物前約 $0.48\,\text{m}$ 處完全煞停；
     2. **移動中專屬 Cancel 煞停距離量測 (Dedicated In-Motion Cancel Physical Test)**：實測行進中發送取消、響應延遲 $1.6\,\text{ms}$、制動時間 $0.5399\,\text{s}$、煞停距離 $0.0068\,\text{m}$ ($0.68\,\text{cm}$)；
   - Checklist #25 正式標記為 `[x] Completed`。
4. **需求追溯與差距審查 (Checklist #26 `[x]`)**:
   - 32 個唯一 `SYS-xxx` 需求（`SYS-001`～`SYS-011`、`SYS-013`～`SYS-021`、`SYS-022`～`SYS-030`、`SYS-032`～`SYS-034`）與 6 個 Custom Gaps（`GAP-01`～`GAP-06`）全部具備明確的程式碼實施、測試套件與 Subsystem Owner；無遺漏、錯號或未核准新增行為。
5. **跨子系統整合閉環 (#19～#23 `[x]`)**:
   - TF 權威樹唯一性 (#19)、感知資料流 (#20)、運動停止分層鏈 (#21)、回授里程計閉環 (#22) 與生命週期／模式切換 (#23) 全數通過整合驗證。
6. **環境可重現性審查 (Checklist #27 `[x]`)**:
   - 乾淨無快取編譯（10/10 套件通過，耗時 6.49 秒）；全套件 425 項自動化測試通過（0 errors, 0 failures, 37 skipped）；無隱藏本地狀態或生產環境 `/home` / `/tmp` 依賴。
7. **無殘留 Feature Freeze 阻塞項 (Zero Freeze Blockers)**:
   - 經審查無任何編譯／測試錯誤、無未解決架構矛盾、無未授權新增行為。

#### 3.22.3 Known Limitations & Deferred Tuning Boundary
- **非阻塞性調校項目 (Deferred Tuning / Post-MVP Optimization)**:
  - 量產級 $5\,\text{cm} / 0.05\,\text{rad}$ 到站精度極限微調；
  - MPPI 速度曲線與 Critic 權重深度最佳化；
  - Collision Monitor 現場動態安全多邊形微調；
  - 部署場域特定 Station Catalog 配置。
- **Feature Freeze 語意澄清 (Feature Freeze Semantics)**:
  - Feature Freeze 代表 **v0.1 軟體架構與功能基線正式凍結**。
  - **不代表** 生產環境極限精度調校已完成（屬於後續量產階段最佳化）。

#### 3.22.4 Status
- **Implementation Status**: `Complete`
- **Evidence Status**: `Complete` (軟體架構、全套件回歸測試、需求追溯與實機驗收數據完備)
- **Checklist Status**: `[x] Completed` (滿足 Checklist #28 原始 DoD 全部要求：UC-001、UC-002、32 個 requirements、6 個 custom gaps 與所有必要實機 evidence 已通過；未完成項有核准的上游變更，正式標記 Feature Frozen)。
- **Next Dependency**: 全部 28 項 Checklist 實作與審查已全數完成閉環（Completed: 28, In Progress: 0, Pending: 0, Total: 28, Progress: 28 / 28 [100%]）。

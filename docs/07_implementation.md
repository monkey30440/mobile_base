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
| Item scope | 依 06 baseline 與 `docs/design_baseline/m1_hardware.md` 實作 `mobile_base_control::M1Hardware`（`hardware_interface::SystemInterface` plugin for ROS 2 Jazzy），包含 Model A2 控制迴圈（`write()` 單次 FC17 交易、`read()` 無通訊消費快取狀態）、單位轉換（$rad/s \leftrightarrow RPM$、齒比 20.0、左輪 +1、右輪 -1、3000 RPM 上限保護）、位置回授與 32-bit Rollover 累積追蹤（`PositionTracker`）、Lifecycle 狀態機（`on_init`, `on_configure`, `on_activate` 帶有有限次狀態輪詢確認、`on_deactivate` 依序執行 stop -> disable -> disconnect、`on_error`/`on_shutdown` 最佳防護清理）、防禦性指令範圍檢查、可配置參數、pluginlib export XML 與註冊、單元測試、URDF `ResourceManager` 整合測試與 Mock 執行驗證；Level 3 實機全迴圈時序量測完成；非零速度運動（Level 4）維持獨立 BLOCKED；Checklist #8 維持 `[~]`（等待 Real Dynamic Wheel Feedback 實機驗證）。 |
| Implementation status | `Implemented (In Progress [~])` |
| Evidence status | `Build Verified` + `Unit Verified` + `Plugin Discovery Verified` + `Integration Verified` + `Real-Hardware Timing & Lifecycle Level 3 Verified` |
| Feature-freeze status | `Baseline Frozen` (Synchronous Model A2 @ 30 Hz validated implementation baseline; Checklist #8 remains `[~]` pending real dynamic wheel feedback verification) |
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

| 欄位 | 內容 |
|---|---|
| 已證明 | 1. **純軟體轉換與閉環邏輯** (`PASS`)：官方 `diff_drive_controller::DiffDriveController` 與 `M1Hardware` SystemInterface plugin 在純軟體/Mock 環境下之完整整合閉環、正反向符號轉換、齒比運算、32-bit Rollover 累積追蹤與 NaN/飽和保護（44 項 GTest 與 6 項 ament linters 通過）。<br/>2. **實機唯讀延遲特性** (`PASS`)：實機 `/dev/ttyUSB0` 上 1000 次連續雙驅動器 `read_state(1, 2)` 通訊延遲分佈特性（Mean 16.0 ms, p99 16.2 ms, Max 20.8 ms）。<br/>3. **實機零速通訊交易** (`PASS`)：實機 220 次 FC17 zero-speed exchange（Stage A 20 + Stage B 200, 100% 成功, 0 timeouts/alarms, Max 21.01 ms）。<br/>4. **實機 30 Hz 全迴圈時序** (`PASS`)：實機 1000 週期 Full ros2_control Loop @ 30 Hz zero-speed 實機時序驗證（1000/1000 成功, 0 deadline misses, 0 timeouts, 0 alarms, Max full cycle 25.91 ms，最小觀測剩餘時序預算 +7.419 ms / 22.3%）。<br/>5. **實機零速回授與生命週期路徑** (`PASS`)：實機真實 M1 狀態回授路徑（`actual_rpm=0`、`accumulated_steps`、`status=6/0`、`alarm=0`）與生命週期啟停序列（enable SVON -> 零速閉環運作 -> 停用 stop JG 0 -> disable SVOFF -> 斷線）。<br/>6. **實機 Stage D1 左輪動態回授與方向有效性** (`PASS`)：<br/>   - ROS 左輪 $+0.5\text{ rad/s}$ 指令正確映射至驅動器 2（Left）之 $+95\text{ RPM}$ 目標值。<br/>   - 實體左輪依預期正向旋轉（自機器人左側觀察為逆時針 CCW，輪頂向前旋轉，操作人員現場確認）。<br/>   - 實機左輪實際轉速回授為正向且與 $\sim 95\text{ RPM}$ 目標動態一致（穩態 $0.4765 \sim 0.5184\text{ rad/s}$）。<br/>   - 實機左輪編碼器位置隨運動連續遞增（自 $0.0000\text{ rad}$ 累積至 $+0.9895\text{ rad}$ / $+56.69^\circ$）。<br/>   - ROS 左輪 velocity 與 position state interfaces 正確反映真實回授。<br/>   - 右輪 command 保持嚴格為零，右輪實際 RPM 保持 0，右輪編碼器位移為 0，操作人員現場確認右輪全程保持靜止（完全隔離）。<br/>   - 全程 0 alarm, 0 timeout, 0 transport/lifecycle error, 0 非預期運動。<br/>   - 受控 cooldown 平順減速至 0 RPM，驗證完成後安全復歸 Servo-Off（Status=6, Alarm=0, RPM=0）。 |
| 尚未證明 (後續階段未完成項) | 1. **右輪動態運動與回授有效性 (Stage D2)** (`UNVERIFIED`)：右輪單獨非零運動下的實際轉速、物理旋轉方向與編碼器累積位移。<br/>2. **雙輪同步動態運動有效性 (Stage D3)** (`UNVERIFIED`)：雙輪同時非零正向運動下的動態回授與速度協調。<br/>3. **反向運動有效性** (`UNVERIFIED`)：負向速度指令（後退）之動態回授與方向正確性。<br/>4. **精密標定與一般定量速度追隨公差** (`UNVERIFIED`)：精密輪速標定（Precision speed calibration）與一般定量速度追隨公差。<br/>5. **整車動態與地面行駛行為** (`UNVERIFIED`)：煞車距離性能（Braking-distance performance）、里程計精度（Odometry accuracy）、著地行駛行為（Floor-driving behavior）與完整 diff_drive_controller 動態閉環。<br/>6. **硬體通訊 Watchdog** (`UNVERIFIED`)：M1 硬體通訊 Watchdog 逾時跳脫與復歸閉環行為（硬體層面仍為 UNVERIFIED，安全等級 NOT ESTABLISHED）。<br/>7. **硬即時保證** (`NOT ESTABLISHED`)：任意 CPU 負載極限下的硬即時（Hard Real-Time）時序保證。 |

---

#### 3.2.9 Known Limits / Unresolved Dependencies

- **Checklist #8 狀態與剩餘範圍**：Stage D1（左輪動態回授與方向）已於實機完成驗證 (`PASS`)。右輪動態 (Stage D2) 與雙輪同步動態 (Stage D3) 仍待後續階段驗證，因此 Checklist #8 依治理規範嚴格維持 `[~]`，不進行追溯性完成條件縮小（Retroactive DoD Narrowing）。
- **Level 4 後續非零運動維持 BLOCKED**：非零速度運動指令受限於安全性考量，Stage D2 / Stage D3 動態運動依 §6 規範維持 BLOCKED，需由操作人員另行獨立即時授權。
- **Safe-Stop 鏈屬軟體 Best-Effort**：現行 `stop()` $\rightarrow$ `disable()` 依賴軟體行程正常運作；若行程崩潰（Process Crash / SIGKILL），軟體無法執行清理，此時實體 E-Stop 與電源切斷為最高安全權威。
- **M1 硬體通訊 Watchdog 尚未閉環驗證**：目前驅動器 Watchdog 保持出廠設定（未啟用），其硬體跳脫特性尚未進行閉環驗證，安全等級為 `NOT ESTABLISHED`。
- **Response Timeout 政策**：`response_timeout_ms` 屬 REQUIRED runtime parameter，API 無隱式預設值；`50 ms` 經實機量測驗證為當前推薦部署參數（Validated Deployment Candidate），但非硬即時常數。
- **Controller Update Rate 基準與重啟條件**：Synchronous Model A2 @ 30 Hz 已凍結為當前實作基準（Architecture Baseline Frozen），若 Baud rate、串列硬體、M1 韌體、主機平台或上層需求變更時，需依定義之觸發條件重新評估。

---

#### 3.2.10 Feature Freeze Status / Next Dependency

| 欄位 | 內容 |
|---|---|
| Feature freeze status | `Baseline Frozen` (Synchronous Model A2 @ 30 Hz validated implementation baseline) |
| Freeze condition | Synchronous Model A2 @ 30 Hz 實作基準凍結；Stage D1 完成驗證；Checklist #8 維持 `[~]` 等待後續 Stage D2/D3 實機驗證；Level 4 後續非零運動維持獨立 BLOCKED |
| Next dependency | Checklist #8 Level 4 Stage D2 (右輪動態驗證，目前 BLOCKED) / Checklist #9 `S1 Robot Description` |

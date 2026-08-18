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
- 若 build / test command 尚未由 checklist #5 確立，於對應欄位填寫 `[pending #5]`。
- 若 hardware preflight 尚未由 checklist #6 確立，於對應欄位填寫 `[pending #6]`。

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

_（無 evidence 時整列填 `—`；build command 格式待 #5 確立時補填）_

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

_（無 evidence 時整列填 `—`；hardware preflight 程序待 #6 確立時補填）_

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

**注意：** 本節只定義 evidence **保存格式**。硬體安全操作前置條件（E-stop、STO、架車、速度上限、watchdog、人工復歸）屬於 checklist #6 的責任，本節不定義。在 #6 完成之前，hardware evidence artifact 的 `Test condition` 欄填寫 `[pending #6 preflight procedure]`。

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

`[pending #5]` 與 `[pending #6]` placeholder 仍保留在 §3.2 的說明注意事項中，表示 build/test command 格式（待 #5）與 hardware preflight（待 #6）尚未確立；storage path 本身已由本節確立，**不再使用 `[pending #4]`**。

### 4.8 Known Limits and Next Boundary

- 本 convention 不依賴外部 artifact server、CI 系統或 database；所有 in-repo evidence 均為純文字，適合 `git log` 追蹤。
- `.gitignore` 中已存在 `*.log` 排除規則；`docs/verification/` 下的 `.txt` 與 `.ref.txt` 不受此規則影響，可正常 commit。
- Large artifact（ROS bag 等）的外部保存位置尚未統一；`[external: ...]` + `.ref.txt` 機制為目前最低限度 reference，具體外部位置由各 item 執行時決定。
- Build 與 test 的完整 command workflow 由 checklist #5 確立；本節只定義 evidence 保存，不預先決定命令格式。
- Hardware safety preflight 由 checklist #6 確立；本節只定義 hardware evidence 的保存格式。
- 下一個項目：[`07_implementation_checklist.md`](./07_implementation_checklist.md) 第 5 項 Build and test command baseline。

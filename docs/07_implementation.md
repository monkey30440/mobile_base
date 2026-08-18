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

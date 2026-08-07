# Development Environment — Implementation Plan

本文件為專案容器化開發／執行環境（`Dockerfile`、`compose.yaml`）之實作計畫，非正式規格文件。

此環境為所有子系統（SUB-001 ~ SUB-011）共用之基礎設施，非特定子系統之實作項目，因此獨立於 `SUB-001-base-control-plan.md` 之外。

---

## 背景 (Context)

- 目標硬體：Jetson AGX Orin Developer Kit（依 `05_subsystem.md` 各子系統系統邊界）。
- ROS 版本基準：ROS 2 Jazzy（依 `04_architecture.md` Design Principles、`05_subsystem.md` 全部子系統系統邊界）。
- Base Image：`nvcr.io/nvidia/isaac/ros:isaac_ros_740c8500df2685ab1f4a4e53852601df-arm64-jetpack`。
  - 已由使用者於 2026-08-07 以 `printenv ROS_DISTRO` 驗證確認為 **ROS 2 Jazzy**，與 Design Baseline 一致。

---

## 開發平台與目標平台 (Dev vs Target Platform)

目前開發與實機部署使用不同運算平台：

| 角色 | 平台 | 狀態 |
|---|---|---|
| 開發平台 | Jetson AGX Thor | 目前所有容器驗證於此完成 |
| 目標平台 | Jetson AGX Orin Developer Kit | 實際連接底盤硬體，尚未驗證 |

因此：

- 開發平台無 `/dev/ttyUSB0` 等實機裝置節點，`compose.yaml` 不綁定裝置節點，實機裝置以 `compose.hardware.yaml` 疊加。
- **所有已通過之容器驗證項目均僅代表 AGX Thor 之結果，不等同目標平台 AGX Orin 已驗證。**

### 高風險假設 (High-Risk Assumption)

Base Image 於 AGX Thor 上確認為 ROS 2 Jazzy，但**尚未於 AGX Orin 驗證同一 image 可用**。

依 NVIDIA Isaac ROS 目前公開之支援矩陣，ROS 2 Jazzy 對應 Jetson Thor + JetPack 7.x；AGX Orin 過去對應之組合為 JetPack 6.x + ROS 2 Humble。若此 image 無法於 AGX Orin 運行，將直接衝擊 `04_architecture.md` 與 `05_subsystem.md` 全部子系統所依據之「ROS 2 Jazzy」基準。

處置：於取得 AGX Orin 實機後，優先驗證此 image 可於 AGX Orin 啟動並提供 ROS 2 Jazzy；驗證結果若與 Design Baseline 不符，須先修正架構文件再繼續實作。

---

## 範圍 (Scope)

僅涵蓋容器化開發／執行環境本身：

- `Dockerfile`：以指定 Base Image 為基礎，建立可建置與執行本專案 ROS 2 package 之環境。
- `compose.yaml`：定義容器執行方式（volume mount、device passthrough、network 等）。

不包含：

- 任何子系統之 ROS 2 package 原始碼（各子系統另有各自實作計畫）。
- CI/CD（見 `06_backlog.md`）。

---

## 現況 (Current State)

- `Dockerfile`、`compose.yaml` 皆為空檔案。
- `src/` 尚未建立，尚無任何 ROS 2 package。

---

## 實作項目 (Planned Work Items)

1. **Dockerfile**
   - `FROM nvcr.io/nvidia/isaac/ros:isaac_ros_740c8500df2685ab1f4a4e53852601df-arm64-jetpack`。
   - 僅安裝目前 MVP（SUB-001 Base Control）所需之最小依賴（例如 RS-485 / Modbus 相關函式庫），不預先安裝尚未開始實作之子系統依賴（Avoid Premature Structure）。
   - 建立 ROS 2 workspace 慣例路徑（例如 `/workspace`），供後續 `src/` 掛載與 colcon build。

2. **compose.yaml**（平台中立）
   - 定義單一服務執行上述映像。
   - Volume mount：專案根目錄（含 `src/`、`maps/`）進容器。
   - Network mode／權限依 ROS 2 DDS 需求設定。
   - 不綁定任何實機裝置節點，使無對應硬體之開發平台可直接使用。

3. **compose.hardware.yaml**（實機疊加）
   - 以 `docker compose -f compose.yaml -f compose.hardware.yaml` 疊加使用。
   - Device passthrough：`/dev/ttyUSB0`（SUB-001 RS-485），後續依需要新增其他子系統之裝置（`/dev/ttyACM0`、LiDAR 網路介面等）。

4. 提供最基本之啟動說明（如何 build、如何進入容器），暫不建立額外文件，待穩定後視需要補充。

---

## 待確認事項 (Open Items)

- Base Image 內建 ROS 2 Jazzy 之確切套件集（是否已含 Nav2、SLAM Toolbox、robot_localization，或需另行安裝）：建置時確認，非現在假設。
  - 2026-08-07 實機建置確認：base image 未預裝 `pip3`，已於 Dockerfile 補上 `apt-get install python3-pip`。
- Jetson 裝置節點權限（`/dev/ttyUSB0` 等）於容器內之存取方式，待實機測試確認。

---

## 驗證計畫 (Verification Plan)

- [x] `docker compose build` 成功（2026-08-07，於 AGX Thor 開發機確認）。
- [x] 容器內 `ROS_DISTRO` 為 `jazzy`（2026-08-07，於 AGX Thor 開發機確認）。
- [x] 容器內可執行 `colcon build`（2026-08-07，於 AGX Thor 開發機確認）。
- [ ] 容器可存取 `/dev/ttyUSB0`（需 AGX Orin 實機，見「開發平台與目標平台」）。
- [ ] Volume mount 正確反映主機端 `src/`、`maps/` 內容。
- [ ] 於 AGX Orin 目標平台重跑上述全部項目。

---

## 狀態 (Status)

- [x] Design Baseline reviewed（ROS 2 Jazzy 假設已與 base image 交叉驗證，無矛盾）
- [x] Implementation（`Dockerfile`、`compose.yaml`、`compose.hardware.yaml` 初版完成）
- [ ] Verification（AGX Thor 開發機驗證已通過；AGX Orin 目標平台與硬體存取待驗證）
- [ ] Feature Freeze

---

## 完成後之文件更新清單 (Closure Checklist)

- [x] `README.md`：Repository 樹狀圖已補上 `compose.hardware.yaml`、`docs/implementation/`、`src/`，並說明 compose 疊加用法。
- [ ] 取得 AGX Orin 實機後，確認 base image 於目標平台可提供 ROS 2 Jazzy；若不符，先修正 `04_architecture.md` 與 `05_subsystem.md` 之 ROS 版本基準。
- [ ] 若安裝套件版本與 `04_architecture.md` Design Principles 所列版本（Nav2、SLAM Toolbox、Robot Localization、Nav2 Route）有出入，回頭修正該章節。
- [ ] 完成後本計畫文件可歸檔或刪除。

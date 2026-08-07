# Development Environment — Implementation Plan

本文件為專案容器化開發／執行環境（`Dockerfile`、`compose.yaml`）之實作計畫，非正式規格文件。

此環境為所有子系統（SUB-001 ~ SUB-011）共用之基礎設施，非特定子系統之實作項目，因此獨立於 `SUB-001-base-control-plan.md` 之外。

---

## 背景 (Context)

- 目標硬體：Jetson AGX Orin Developer Kit（依 `05_subsystem.md` 各子系統系統邊界）。
- ROS 版本基準：ROS 2 Jazzy（依 `04_architecture.md` Design Principles、`05_subsystem.md` 全部子系統系統邊界）。
- Base Image：`nvcr.io/nvidia/isaac/ros:isaac_ros_740c8500df2685ab1f4a4e53852601df-arm64-jetpack`。
  - 已由使用者於 2026-08-07 以 `printenv ROS_DISTRO` 驗證確認為 **ROS 2 Jazzy**，與 Design Baseline 一致，無需修正架構文件。

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

2. **compose.yaml**
   - 定義單一服務執行上述映像。
   - Volume mount：專案根目錄（含 `src/`、`maps/`）進容器。
   - Device passthrough：`/dev/ttyUSB0`（SUB-001 RS-485），後續依需要新增其他子系統之裝置（`/dev/ttyACM0`、LiDAR 網路介面等）。
   - Network mode／權限依 ROS 2 DDS 需求設定。

3. 提供最基本之啟動說明（如何 build、如何進入容器），暫不建立額外文件，待穩定後視需要補充。

---

## 待確認事項 (Open Items)

- Base Image 內建 ROS 2 Jazzy 之確切套件集（是否已含 Nav2、SLAM Toolbox、robot_localization，或需另行安裝）：建置時確認，非現在假設。
  - 2026-08-07 實機建置確認：base image 未預裝 `pip3`，已於 Dockerfile 補上 `apt-get install python3-pip`。
  - 2026-08-07 實機建置確認：base image 內建之 NVIDIA L4T apt 來源（`repo.download.nvidia.com/jetson/common`）於一般 build context 下因無裝置端認證會回 401。由於 Docker BuildKit 預設忽略宿主機的 default-runtime 設定，本專案最終決議採用「在 Dockerfile 中使用 Dir::Etc::SourceParts=/dev/null 暫時忽略 sources.list.d」之正規做法解決。
- Jetson 裝置節點權限（`/dev/ttyUSB0` 等）於容器內之存取方式，待實機測試確認。

---

## 驗證計畫 (Verification Plan)

- [x] `docker compose config` 語法驗證通過。
- [ ] `docker compose build` 成功（需 NGC 登入拉取 base image，於實機／有 NGC 認證環境執行）。
- [ ] 容器內 `ROS_DISTRO` 為 `jazzy`。
- [ ] 容器內可執行 `colcon build`（空 workspace 或最小測試 package）。
- [ ] 容器可存取 `/dev/ttyUSB0`（供 SUB-001 後續開發使用）。
- [ ] Volume mount 正確反映主機端 `src/`、`maps/` 內容。

---

## 狀態 (Status)

- [x] Design Baseline reviewed（ROS 2 Jazzy 假設已與 base image 交叉驗證，無矛盾）
- [x] Implementation（`Dockerfile`、`compose.yaml` 已建立，`src/` 建立為 mount target）
- [ ] Verification（語法檢查已通過，實機建置與硬體存取待使用者於有 NGC 認證之環境執行）
- [ ] Feature Freeze

---

## 完成後之文件更新清單 (Closure Checklist)

- [ ] `README.md`：Repository 樹狀圖確認 `Dockerfile`、`compose.yaml` 已非空檔案（內容不重複列出，僅樹狀圖本身已涵蓋）。
- [ ] 若安裝套件版本與 `04_architecture.md` Design Principles 所列版本（Nav2、SLAM Toolbox、Robot Localization、Nav2 Route）有出入，回頭修正該章節。
- [ ] 完成後本計畫文件可歸檔或刪除。

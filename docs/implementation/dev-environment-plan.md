# Development Environment

專案容器化開發／執行環境之實作紀錄。

此環境為所有子系統（SUB-001 ~ SUB-011）共用之基礎設施，非特定子系統之實作項目。

本文件僅記錄結果與結論，不保留規劃過程。

---

## 組成

| 檔案 | 用途 |
|---|---|
| `Dockerfile` | 以 Isaac ROS base image 建立 ROS 2 Jazzy 建置／執行環境，並安裝 ros2_control |
| `compose.yaml` | 平台中立之容器設定，不綁定實機裝置節點 |
| `compose.hardware.yaml` | 疊加實機裝置節點（device passthrough） |

Base Image：

```text
nvcr.io/nvidia/isaac/ros:isaac_ros_740c8500df2685ab1f4a4e53852601df-arm64-jetpack
```

使用方式：

```bash
# 開發平台（無實機硬體）
docker compose up -d --build

# 目標平台（連接底盤硬體）
docker compose -f compose.yaml -f compose.hardware.yaml up -d --build
```

---

## 平台

| 角色 | 平台 |
|---|---|
| 開發平台 | Jetson AGX Thor |
| 目標平台 | Jetson AGX Orin Developer Kit |

同一 Base Image 已確認可於兩平台運行，開發成果可直接部署至目標平台。

---

## 驗證結果

2026-08-07 完成，AGX Thor 與 AGX Orin 皆通過：

| 項目 | 結果 |
|---|---|
| `docker compose build` | 通過（兩平台） |
| `ROS_DISTRO` | `jazzy`（AGX Thor 直接確認；AGX Orin 使用同一 image 並成功運行） |
| `colcon build` | 通過（兩平台） |
| `/dev/ttyUSB0` 存取 | 通過（AGX Orin，經 `compose.hardware.yaml` 疊加） |
| `src/` volume mount | 通過（`colcon build` 於 `/workspace` 成功即為佐證） |

`maps/` mount 於 SUB-008 Map Management 實作時一併驗證，現階段無使用者。

---

## 結論與已知事項

- **ROS 2 Jazzy 基準於目標平台成立**，`05_architecture.md` 與 `06_subsystem.md` 之 ROS 版本基準無需修正。
- Base image 未預裝 `pip3`，已於 Dockerfile 補上 `apt-get install python3-pip`。
- Base image 未預裝 ros2_control，已於 Dockerfile 安裝
  `ros-jazzy-ros2-control` 4.45.2 與 `ros-jazzy-ros2-controllers` 4.40.1。
- 容器內存取 `/dev/ttyUSB0` 僅需 device passthrough，無需額外權限設定。
- colcon 之 `build/`、`install/`、`log/` 產生於 `/workspace`，未掛載至主機，
  容器重建後需重新 `colcon build`。

---

## 狀態

- [x] Design Baseline reviewed
- [x] Implementation
- [x] Verification
- [x] Feature Freeze（2026-08-07）

待辦：若後續安裝之套件版本與 `04_reuse_assessment.md` 的版本盤點或 `05_architecture.md` 的架構決策有出入，回到最早受影響的文件修正。

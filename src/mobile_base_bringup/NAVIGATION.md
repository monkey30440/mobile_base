# 導航操作指南

## 用途

`mobile_base_bringup` 的導航模式會組合各個已驗證子系統的 launch 檔案，啟動完整的實機自主導航系統，包括：

- S7 Base Control
- S1 Robot Description
- S2 Perception：IMU、雙 LiDAR、雷射掃描合併與 RF2O
- S3 State Estimation：EKF
- S5 Localization：Map Server 與 AMCL
- S6 Navigation：Nav2 路線輔助導航堆疊與 Collision Monitor

各子系統套件仍是驅動程式、控制器、狀態估測、AMCL 參數、Nav2 設定與 TF 權限的權威來源。

啟動導航模式本身不會命令底盤移動。系統只有在收到有效的導航目標後才會移動。

## 啟動導航模式

不啟用 Foxglove：

```bash
ros2 launch mobile_base_bringup navigation.launch.py \
  map:=$(pwd)/maps/test_site/map.yaml \
  route_graph:=$(pwd)/maps/test_site/route_graph.geojson
```

啟用選用的 Foxglove 視覺化工具：

```bash
ros2 launch mobile_base_bringup navigation.launch.py \
  map:=$(pwd)/maps/test_site/map.yaml \
  route_graph:=$(pwd)/maps/test_site/route_graph.geojson \
  use_foxglove:=true
```

導航模式正常運作時，會提供下列主要執行期契約：

- `/scan`：合併後的前、後 LiDAR 掃描資料
- `/imu/data_raw`：原始 IMU 量測資料
- `/rf2o/odom`：RF2O 雷射里程計，且 RF2O 的 TF 發布功能停用
- `/odometry/filtered`：EKF 融合後的里程計資料
- `/map`：由 `nav2_map_server` 發布的靜態地圖
- `/amcl_pose`：AMCL 估測的全域位姿
- TF `odom -> base_footprint`：僅由 EKF 負責發布
- TF `map -> odom`：收到初始位姿後，僅由 `nav2_amcl` 負責發布
- 速度命令鏈：`controller_server`（`/cmd_vel_nav`）→ `collision_monitor` → `/diff_drive_controller/cmd_vel`
- S4 `slam_toolbox` 必須完全排除且不得執行

## 設定初始位姿

啟動導航模式後，使用 RViz2 的 `2D Pose Estimate` 工具，或透過 `/initialpose` topic，提供 AMR 的概略初始位姿。AMCL 隨後會初始化粒子濾波器，並開始發布 `map -> odom` TF。

## Foxglove

Foxglove Bridge 是選用的視覺化工具。只有在啟動導航模式時指定 `use_foxglove:=true` 才會啟動。請使用 Foxglove 用戶端連線至 Bridge 啟動輸出中顯示的端點。

## 停止與安全

`Ctrl-C` 只會停止前景程序，不是緊急停止功能。緊急狀況請使用 AMR 的 E-stop／STO。

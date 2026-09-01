# 導航操作指南

## 用途

`mobile_base_bringup` 的導航模式會組合各個已驗證子系統的 launch 檔案，啟動完整的實機自主導航系統，包括：

- S7 Base Control
- S1 Robot Description
- S2 Perception：IMU 與雙實體 LiDAR（/scan_front, /scan_rear）
- S3 State Estimation：Kinematic-ICP（前 LiDAR + wheel prior）與 EKF
- S5 Localization：Map Server 與 AMCL
- S6 Navigation：Nav2 路線輔助導航堆疊

各子系統套件仍是驅動程式、控制器、狀態估測、AMCL 參數、Nav2 設定與 TF 權限的權威來源。

啟動導航模式本身不會命令底盤移動。系統只有在收到有效的導航目標後才會移動。

## 啟動導航模式

### 正式標準入口 (Canonical Entry Point)

使用高階 `site` 參數自動解析場域資源（地圖與拓撲路網）：

不啟用 Foxglove：

```bash
ros2 launch mobile_base_bringup mobile_base.launch.py \
  mode:=navigation \
  site:=test_site
```

啟用選用的 Foxglove 視覺化工具：

```bash
ros2 launch mobile_base_bringup mobile_base.launch.py \
  mode:=navigation \
  site:=test_site \
  use_foxglove:=true
```

若需低階手動覆寫個別資源檔案：

```bash
ros2 launch mobile_base_bringup mobile_base.launch.py \
  mode:=navigation \
  map:=$(pwd)/maps/test_site/map.yaml \
  route_graph:=$(pwd)/maps/test_site/route_graph.geojson
```

### 向下相容入口 (Compatibility Wrapper)

```bash
ros2 launch mobile_base_bringup navigation.launch.py \
  site:=test_site
```

或使用舊版低階參數：

```bash
ros2 launch mobile_base_bringup navigation.launch.py \
  map:=$(pwd)/maps/test_site/map.yaml \
  route_graph:=$(pwd)/maps/test_site/route_graph.geojson
```

導航模式正常運作時，會提供下列主要執行期契約：

- `/scan_front`：實體前 LiDAR 原始掃描資料（供 Kinematic-ICP、AMCL 與 Nav2 成本地圖使用）
- `/scan_rear`：實體後 LiDAR 原始掃描資料（供 Nav2 成本地圖使用）
- `/imu/data_raw`：原始 IMU 量測資料
- `/diff_drive_controller/odom`：Kinematic-ICP 的 encoder wheel prior
- `/lidar_odometry`：Kinematic-ICP 平面里程，且 `publish_odom_tf=false`
- `/odometry/filtered`：EKF 融合後的里程計資料
- `/map`：由 `nav2_map_server` 發布的靜態地圖
- `/amcl_pose`：AMCL 估測的全域位姿
- TF `odom -> base_footprint`：僅由 EKF 負責發布
- TF `map -> odom`：AMCL 以部署設定的預設初始位姿或 `/initialpose` 覆寫完成初始化後，僅由 `nav2_amcl` 負責發布
- 速度命令鏈：`controller_server` → `/diff_drive_controller/cmd_vel`
- S4 `slam_toolbox` 必須完全排除且不得執行

## 設定初始位姿

導航模式啟動時，AMCL 會使用部署設定的預設初始位姿 `x=0.0`、`y=0.0`、`z=0.0`、`yaw=0.0` 初始化粒子濾波器，並開始發布 `map -> odom` TF。

若 AMR 實際開機位置不符合此預設，請使用 RViz2 的 `2D Pose Estimate` 工具，或透過 `/initialpose` topic，提供概略初始位姿以覆寫預設值。

## 執行站點導航 (Station Navigation)

確認 AMCL 已完成初始定位且 `map -> odom` TF 正常發布後，開啟第二個已載入環境的容器終端，執行 `navigate_to_station` CLI 應用程式：

```bash
ros2 run mobile_base_navigation navigate_to_station \
  --station <station_id> \
  --catalog maps/<site>/stations.yaml
```

例如前往 `test_site` 的 `station_b`：

```bash
ros2 run mobile_base_navigation navigate_to_station \
  --station station_b \
  --catalog maps/test_site/stations.yaml
```

### 站點導航架構與流程

1. `navigate_to_station` CLI 載入指定的站點目錄（`stations.yaml`）。
2. 透過 `TargetAdmission` 解析並驗證目標站點的 canonical `geometry_msgs/msg/PoseStamped`。
3. 透過 ROS 2 原生 Action Client 將目標提交至 Nav2 `bt_navigator` 的 `navigate_to_pose` Action Server（`nav2_msgs/action/NavigateToPose`）。
4. 導航堆疊依行為樹（`route_assisted_nav.xml`）執行路線輔助導航（First Mile → On Route → Last Mile）。
5. CLI 接收 Nav2 即時反饋（`NAV_FEEDBACK`）並於完成時輸出原生結果（`NAV_SUCCEEDED` / `NAV_ABORTED` / `NAV_CANCELED`）。

若需取消進行中的導航，可在 CLI 終端按下 `Ctrl-C` 請求取消進行中的 Nav2 目標並等待確認。若 Nav2 確認取消，CLI 回報 `NAV_CANCELED`；若未在時限內確認則回報 `CANCELLATION_UNCONFIRMED`。

### 已知限制 (Known Limitation B)

在 `test_site` 場域實機驗證中，Station A 前往 Station B 導航已驗收通過；反向 Station B 前往 Station A 於接近目標時觀察到進度逾時（`error_code=105`），此現象列為 Known Limitation B（root cause undetermined），操作時請留意進度狀態。

## 執行視覺停靠 (AprilTag Direct Docking)

在導航模式運行期間，若需使 AMR 精準停靠於視覺標記（AprilTag）前，可透過 Trigger 服務一鍵觸發。

### 前置條件

1. 導航模式已啟動（`mobile_base.launch.py mode:=navigation`）。
2. Nav2 `docking_server` 處於 Active 生命週期狀態，且 `apriltag_dock_trigger` 節點正常運作。
3. 外部視覺系統（Upper Body）已持續在 `/detected_dock_pose` 發布標記相對於基座之姿態（`geometry_msgs/msg/PoseStamped`，`frame_id: "base_link"`）。
4. AprilTag 穩定可見。

> **第一階段實機建議起始條件**（保守初次驗證範圍）：
> - 距 AprilTag 約 1.0–1.5 m
> - lateral error 建議 < 20 cm
> - heading error 建議 < 10–15°

### 操作步驟

1. **確認視覺偵測串流**（選用）：
   ```bash
   ros2 topic echo /detected_dock_pose --once
   ```
   確認已收到帶有 `frame_id: base_link` 的有效位姿。

2. **觸發視覺停靠**：
   開啟終端執行 Trigger 服務：
   ```bash
   ros2 service call /apriltag_dock std_srvs/srv/Trigger "{}"
   ```

### 停靠行為與架構說明

- `apriltag_dock_trigger` 會自動取用最新一筆快取的 `/detected_dock_pose` 作為初始停靠目標，並送出 `DockRobot` Action Goal。
- Trigger 節點不修改任何位姿幾何；標記至停等點的 70 cm 外參幾何轉換完全由 `docking_server` 的 `SimpleNonChargingDock` 外掛處理。
- 服務呼叫端會同步等待停靠完成，並於結束時回傳結果（`success: true` 與 `message: "Docking succeeded"`）。
- **失敗與防護**：
  - 尚未收到任何視覺偵測資料時：立即回傳失敗（`No detected dock pose received yet`）。
  - 停靠任務已在進行中時：重複觸發立即拒絕（`Docking already in progress`）。
  - `docking_server` 離線、拒絕目標、偵測逾時或停靠控制失敗時：服務回傳失敗並附帶具體錯誤訊息。

### 停止與取消方式

- **取消介面現況**：MVP-1 的 `/apriltag_dock` Trigger API 尚未提供獨立 cancel 介面，請勿捏造或假設存在 `/apriltag_dock/cancel`。
- **維運停止**：若需非緊急中斷停靠，可直接停止導航模式 launch 程序。
- **緊急停止**：緊急狀況請直接使用 AMR 實體 E-stop / STO 按鈕。

## Foxglove

Foxglove Bridge 是選用的視覺化工具。只有在啟動導航模式時指定 `use_foxglove:=true` 才會啟動。請使用 Foxglove 用戶端連線至 Bridge 啟動輸出中顯示的端點。

## 停止與安全

1. 取消導航任務：於 `navigate_to_station` 終端按下 `Ctrl-C` 請求取消目標。
2. 關閉導航模式：停止導航模式的 launch 程序。
3. 緊急停止：`Ctrl-C` 僅為軟體層級的導航取消或程序終止機制，不是硬體緊急停止功能；緊急狀況請使用 AMR 的實體 E-stop／STO 按鈕。

## 故障排除

### AMCL 未發布 `map -> odom` TF

```bash
ros2 topic echo /amcl_pose --once
ros2 run tf2_ros tf2_echo map odom
```

確認 AMCL 已使用部署設定的預設初始位姿完成初始化，或已透過 RViz2 `2D Pose Estimate`／`/initialpose` 覆寫初始位姿，且 `/scan_front` 正常發布。

### `navigate_to_station` 回報 `NAV2_UNAVAILABLE`

```bash
ros2 action list | grep navigate_to_pose
ros2 node list | grep -E '(bt_navigator|controller_server|planner_server)'
```

確認 Nav2 相關節點皆處於 Active 生命週期狀態。

### `navigate_to_station` 回報 `RESOLUTION_FAILED`

檢查指定之 `--catalog` 檔案路徑與 `--station` 名稱是否存在且格式正確。

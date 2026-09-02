# 導航操作指南

## 用途

`mobile_base_bringup` 的導航模式（Navigation Mode）會啟動實機自主導航所需的底盤控制、感測感知、全域定位與 Nav2 導航堆疊，支援以下兩大核心操作：

1. **站點導航 (Station Navigation)**：依指定站點 ID 或地圖座標執行路網輔助自主移動。
2. **視覺停靠 (AprilTag Direct Docking)**：依外部 AprilTag 視覺偵測執行最後一哩精準停靠。

> **安全提醒**：啟動 Navigation Mode 本身不會命令底盤移動；系統僅在收到明確的導航或停靠指令後才會驅動底盤。

---

## 啟動導航模式

### 標準啟動方式 (Canonical Entry Point)

使用 `site` 參數自動載入指定場域之地圖與路網資源：

```bash
ros2 launch mobile_base_bringup mobile_base.launch.py \
  mode:=navigation \
  site:=test_site
```

若需啟用 Foxglove 視覺化工具：

```bash
ros2 launch mobile_base_bringup mobile_base.launch.py \
  mode:=navigation \
  site:=test_site \
  use_foxglove:=true
```

> **進階與相容操作**：
> - 低階檔案覆寫：可手動傳入 `map:=$(pwd)/maps/<site>/map.yaml` 與 `route_graph:=$(pwd)/maps/<site>/route_graph.geojson`。
> - 相容 launch 入口：亦可使用 `ros2 launch mobile_base_bringup navigation.launch.py site:=test_site`。

---

## 設定初始位姿

導航模式啟動後，AMCL 會使用預設位姿（`x=0.0, y=0.0, yaw=0.0`）進行初始化。

若 AMR 實機開機位置與預設不符：
1. 開啟 RViz2，使用工具列的 **`2D Pose Estimate`** 在地圖上點選 AMR 當前位置與朝向。
2. 或透過指令發布至 `/initialpose` topic 覆寫初始位姿。

確認 AMCL 定位正常且無明顯漂移後，即可開始執行導航任務。

---

## 執行站點導航 (Station Navigation)

確認定位正常後，開啟第二個終端執行 `navigate_to_station` CLI 應用程式：

```bash
ros2 run mobile_base_navigation navigate_to_station \
  --station <station_id> \
  --catalog maps/<site>/stations.yaml
```

**範例**（前往 `test_site` 的 `station_b`）：

```bash
ros2 run mobile_base_navigation navigate_to_station \
  --station station_b \
  --catalog maps/test_site/stations.yaml
```

### 操作說明與取消

- **執行結果**：CLI 會將站點目標提交至 Nav2 執行導航，並在終端即時顯示進度與最終結果（`NAV_SUCCEEDED` / `NAV_ABORTED` / `NAV_CANCELED`）。
- **中途取消**：在 `navigate_to_station` 終端按下 `Ctrl-C`，CLI 會向 Nav2 請求取消進行中的目標並確認底盤安全停止。
- **已知限制 (Known Limitation B)**：在 `test_site` 實機測試中，Station A 前往 Station B 已驗收通過；反向由 Station B 前往 Station A 於接近目標時可能因進度逾時（`error_code=105`）而終止，操作時請留意進度狀態。

---

## 執行視覺停靠 (AprilTag Direct Docking)

在導航模式運行期間，若需使 AMR 精準停靠於視覺標記前，可透過 Trigger 服務一鍵觸發。

### 前置條件與建議起始位置

- **前置條件**：導航模式已啟動，外部視覺系統（Upper Body）已持續在線並發布 `/detected_dock_pose`，AprilTag 穩定可見。
- **第一階段實機測試建議**（保守初次驗證範圍）：
  - 距 AprilTag 約 1.0–1.5 m
  - lateral error 建議 < 20 cm
  - heading error 建議 < 10–15°

### 三步操作流程

**Step 1：確認導航模式已啟動**
```bash
ros2 launch mobile_base_bringup mobile_base.launch.py \
  mode:=navigation \
  site:=test_site
```
*(實際部署時將 `test_site` 替換為現場 site 名稱)*

**Step 2：確認 AprilTag 視覺偵測串流**（感知串流確認）
```bash
ros2 topic echo /detected_dock_pose --once
```
確認已收到 `frame_id: base_link` 的有效 PoseStamped（由 Upper Body 視覺感知持續發布）：
- `header.frame_id = "base_link"`
- `header.stamp` 必須為感知取樣時間戳（Lower 以此檢驗 2.0s 幀時效）
- `pose` 為相機估測之原始 AprilTag 位姿（Upper 嚴格不加 `-0.7m` 偏移，偏移由 Lower 外掛幾何計算）

**Step 3：發送 Nav2 原生 DockRobot Action 目標**（正式任務介面）
Upper Body 決策模組應透過 ROS 2 Action Client 發送 `nav2_msgs/action/DockRobot` 至 `/dock_robot`。

*(CLI 手動調試範例 — 注意：Thor 在未安裝實體馬達/光達時禁止發送會產生物理運動之 Goal)*：
```bash
ros2 action send_goal /dock_robot nav2_msgs/action/DockRobot "{
  use_dock_id: false,
  dock_id: '',
  dock_pose: {
    header: {frame_id: 'base_link'},
    pose: {
      position: {x: 1.2, y: 0.0, z: 0.0},
      orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}
    }
  },
  dock_type: 'apriltag_dock',
  max_staging_time: {sec: 0, nanosec: 0},
  navigate_to_staging_pose: false
}"
```

### 停靠行為與防護

- **任務與感知分離**：`/detected_dock_pose` 是純感知資料串流，偵測到標記不等於啟動停靠；發送 `/dock_robot` Action Goal 才是唯一的停靠觸發。
- **幾何與控制責任**：70 cm 停靠幾何偏移由 Lower 的 `SimpleNonChargingDock` 外掛獨佔計算，Upper 僅提供原始標記位姿。
- **原生 Action 語意**：
  - Upper 可即時接收 Feedback（`state`, `docking_time`, `num_retries`）。
  - 任務結束時接收結構化 Result（`success`, `error_code`, `error_msg`）。
  - 若視覺逾時（2.0s）、初始感知逾時（5.0s）或控制逾時（30.0s），Action Server 自動煞停並回傳對應錯誤碼。

### 停靠停止與安全

- **原生 Action 取消 (Cancel)**：Upper Body 作為 Action Client 可隨時發送 Action Cancel 請求；`docking_server` 收到後立即中斷控制迴圈、發布零速 `cmd_vel` 煞停並將狀態標記為 `CANCELED`。
- **維運停止**：若需非緊急中斷停靠，可直接停止導航模式 launch 程序。
- **緊急停止**：緊急狀況請直接使用 AMR 實體 E-stop / STO 按鈕。

---

## 停止與安全

1. **取消站點導航**：於 `navigate_to_station` 終端按下 `Ctrl-C` 取消目標。
2. **取消視覺停靠**：由 Upper Body Action Client 發送 Action Cancel 請求。
3. **關閉導航模式**：於 launch 終端按下 `Ctrl-C` 停止導航模式所有節點。
4. **緊急停止**：軟體取消非硬體急停；緊急狀況請立即按下 AMR 實體 E-stop / STO 按鈕。

---

## 故障排除

### 1. AMCL 未發布定位 TF (`map -> odom`)

```bash
ros2 topic echo /amcl_pose --once
ros2 run tf2_ros tf2_echo map odom
```
- 確認 AMCL 是否已透過預設位姿或 RViz2 `2D Pose Estimate` 完成初始化。
- 確認前雷達 `/scan_front` 是否正常發布。

### 2. `navigate_to_station` 回報 `NAV2_UNAVAILABLE`

```bash
ros2 action list | grep navigate_to_pose
ros2 node list | grep -E '(bt_navigator|controller_server|planner_server)'
```
- 確認 Nav2 核心節點皆處於 Active 生命週期狀態。

### 3. `navigate_to_station` 回報 `RESOLUTION_FAILED`

- 檢查 `--catalog` 檔案路徑與 `--station` 名稱是否存在且格式正確。

### 4. AprilTag 停靠無法觸發或回報失敗

```bash
ros2 action list -t | grep dock_robot
ros2 topic echo /detected_dock_pose --once
```
- 若 `/dock_robot` 不存在：確認 Nav2 `docking_server` 是否已啟動且處於 Active 生命週期狀態（`ros2 lifecycle get /docking_server`）。
- 若未收到標記位姿：確認 Upper Body 是否已啟動並持續發布 `/detected_dock_pose`（`frame_id: "base_link"`）。
- 若 Action 回傳 `FAILED_TO_DETECT_DOCK`（904）：確認 `/detected_dock_pose` 發布時間戳是否即時更新（時效需在 2.0s 內）。

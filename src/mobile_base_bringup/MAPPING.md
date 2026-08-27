# 建圖操作指南

## 用途

`mobile_base_bringup` 的建圖模式會組合各個已驗證子系統的 launch 檔案，啟動完整的實機建圖系統。各子系統套件仍是驅動程式、控制器、狀態估測、SLAM 參數與 TF 權限的權威來源。

啟動建圖模式本身不會命令底盤移動。操作員必須在另一個終端中明確啟動鍵盤遙控。

## 啟動建圖模式

### 正式標準入口 (Canonical Entry Point)

不啟用 Foxglove：

```bash
ros2 launch mobile_base_bringup mobile_base.launch.py mode:=mapping
```

啟用選用的 Foxglove 視覺化工具：

```bash
ros2 launch mobile_base_bringup mobile_base.launch.py mode:=mapping use_foxglove:=true
```

### 向下相容入口 (Compatibility Wrapper)

```bash
ros2 launch mobile_base_bringup mapping.launch.py
```

建圖模式正常運作時，會提供下列主要執行期契約：

- `/scan_front`：實體前 LiDAR 原始掃描資料（供 Kinematic-ICP 與 `slam_toolbox` 使用）
- `/scan_rear`：實體後 LiDAR 原始掃描資料
- `/imu/data_raw`：原始 IMU 量測資料
- `/diff_drive_controller/odom`：Kinematic-ICP 的 encoder wheel prior
- `/lidar_odometry`：Kinematic-ICP 平面里程，且 `publish_odom_tf=false`
- `/odometry/filtered`：EKF 融合後的里程計資料
- `/map`：由 `slam_toolbox` 產生的佔據柵格地圖
- TF `odom -> base_footprint`：由 EKF 唯一負責發布
- TF `map -> odom`：由 `slam_toolbox` 唯一負責發布

建圖模式不會啟動 AMCL、`mobile_base_localization` 或 S6 Navigation。

## 在第二個終端啟動鍵盤遙控

先確認建圖模式運作正常且現場安全，再開啟第二個容器終端、載入環境並執行：

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard \
  --ros-args \
  -p stamped:=true \
  -p speed:=0.10 \
  -r cmd_vel:=/diff_drive_controller/cmd_vel
```

操作按鍵：

- `i`：前進
- `,`：後退
- `j`：左轉
- `l`：右轉
- `k`：主動停止

## 建圖操作

- 緩慢起步，並維持已設定的低速。
- 完整涵蓋環境中的固定幾何特徵。
- 從不同視角重複經過有辨識價值的特徵。
- 避免不必要的高速移動。
- 儲存地圖前按下 `k`，並確認 AMR 已停止。

## Foxglove

Foxglove Bridge 是選用的視覺化工具，不是正確建圖的必要條件。只有在啟動建圖模式時指定 `use_foxglove:=true` 才會啟動。請使用 Foxglove 用戶端連線至 Bridge 啟動輸出中顯示的端點。

## 儲存並驗證地圖

AMR 停止後，在建圖模式仍持續發布 `/map` 時，開啟第三個已載入環境的容器終端並執行：

```bash
ros2 run mobile_base_bringup save_map.sh
```

此工具會依本機儲存時間，以 `YYYYMMDD_HHMMSS` 格式在儲存庫的地圖根目錄下建立目錄。例如：

```text
maps/20260820_143012/
├── map.yaml
└── map.pgm
```

工具會沿用已驗證的 `nav2_map_server map_saver_cli` topic、格式、模式、閾值、Transient Local 訂閱設定與逾時設定。儲存成功後，工具會自動執行：

```bash
ros2 run mobile_base_mapping validate_map_readback \
  maps/<timestamp>/map.yaml
```

成功回讀時會顯示下列證據：

```text
STATUS: LOAD_MAP_SUCCESS
RESOLUTION: 0.05
WIDTH: <大於 0 的數值>
HEIGHT: <大於 0 的數值>
DATA_SIZE: <等於 WIDTH * HEIGHT 的數值>
```

Git 預設會忽略依時間戳記建立的執行期地圖。`maps/template/` 則保留為納入版本控制的儲存庫目錄結構範本。

## 關閉流程

1. 按下 `k`，確認 AMR 已停止。
2. 結束鍵盤遙控。
3. 如需儲存地圖，請在 `/map` 仍可用時完成儲存。
4. 停止建圖模式的 launch 程序。
5. 視需要離開容器。

`Ctrl-C` 只會停止前景程序，不是緊急停止功能。緊急狀況請使用 AMR 的 E-stop／STO。

## 故障排除

### 找不到 `/map`

```bash
ros2 topic list | grep '^/map$'
ros2 lifecycle get /async_slam_toolbox_node
ros2 topic hz /scan_front
ros2 run tf2_ros tf2_echo odom base_footprint
```

確認 `slam_toolbox` 處於 Active 狀態，且 `/scan_front` 與里程計 TF 均可用。

### 找不到 `/scan_front` 或 `/scan_rear`

```bash
ros2 topic list | grep -E '^/scan(_front|_rear)$'
ros2 topic hz /scan_front
ros2 topic hz /scan_rear
ros2 node list | grep -E 'lidar'
```

檢查兩台 SICK 裝置與各自的網路連線設定。

### AMR 未回應鍵盤遙控

```bash
ros2 topic hz /diff_drive_controller/cmd_vel
ros2 control list_controllers
ros2 topic echo /diff_drive_controller/cmd_vel --once
```

確認鍵盤遙控終端目前取得輸入焦點、控制器處於 Active 狀態、硬體已啟用，且沒有安全停止訊號。不可繞過 E-stop／STO。

### 儲存地圖逾時

```bash
ros2 topic info /map --verbose
ros2 topic echo /map --once
```

保持建圖模式運作，並確認 `/map` 有使用 Transient Local 的有效發布者，再重新嘗試。

### 地圖回讀失敗

```bash
ls -l maps/<timestamp>/map.yaml maps/<timestamp>/map.pgm
ros2 run mobile_base_mapping validate_map_readback \
  maps/<timestamp>/map.yaml
```

使用 `save_map.sh` 回報的確切時間戳記目錄。檢查驗證工具的錯誤訊息及地圖 YAML 中的影像路徑；不可手動修改未完整儲存的檔案，使其看似有效。

### Foxglove 無法連線

```bash
ros2 node list | grep foxglove
ros2 node info /foxglove_bridge
```

確認啟動建圖模式時已指定 `use_foxglove:=true`，再使用啟動時顯示的 Bridge 端點，並檢查容器與網路連線。

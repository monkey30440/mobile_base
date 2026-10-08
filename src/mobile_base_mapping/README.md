# mobile_base_mapping

平台原生配置啟用 `check_min_dist_and_heading_precisely: true`，讓足夠的平移
或旋轉都能提供新建圖視角。距離／角度門檻仍為原生 commissioning defaults，
不是已標定的地圖品質保證。需使用 Docker 內固定的 SICK measurement-bounds
與 SLAM 倒裝 angle-bounds overlays；直接使用 apt 基線版本無法補足已確認 gaps。

使用本 repository Docker image 的固定原生 SLAM overlay；apt 2.8.5 單獨使用
未修正倒裝非對稱 scan 的角度缺陷。部署版本／patch 可由
`/opt/mobile_base/slam_toolbox/source-version.txt` 追溯。獨立套件的靜止、旋轉、
直線往返及 scan/map 對齊已完成現場驗收；量化精度與 calibration 仍另行驗證。
產品情境入口與 readiness 程序見 [Bringup](../mobile_base_bringup/README.md)。

此套件只啟動原生 `slam_toolbox` 非同步建圖，使用前左
`/lidar/fl/scan`（`base_lidar_link_FL_1`）。不啟動感測器、馬達、
robot_state_publisher、EKF、AMCL 或 Navigation。

## 啟動獨立套件

先在已 source workspace 的不同終端啟動既有元件：

```bash
ros2 launch mobile_base_description description.launch.py
ros2 launch mobile_base_perception dual_picoscan.launch.py
ros2 launch mobile_base_perception imu.launch.py
ros2 launch mobile_base_control m1.launch.py
ros2 launch mobile_base_odometry odometry.launch.py
```

Control 啟動可能 Servo ON，但不應產生非零動作。實機操作須在現場且能停止。
所有終端使用相同 ROS_DOMAIN_ID；不要同時啟動另一套元件或 Navigation。

在鍵盤控制終端：

```bash
bash ./scripts/teleop.sh
```

先按 `k` 傳送零速度。既有 diff_drive_controller 冷啟動要收到首筆
有效命令才開始發布 odom；保留既有 3600 秒 timeout，不新增初始化 publisher。
先確認 `/base_controller/odom`、`/imu/data_raw`、`/odometry/filtered`、
前左 scan 及 `odom → base_footprint → base_link → base_lidar_link_FL_1`
有效，再於另一终端啟動：

```bash
ros2 launch mobile_base_mapping mapping.launch.py
```

預設讀取套件 `config/slam.yaml`。`--symlink-install` 時修改 source YAML，
下次 launch 生效；不支援 hot reload。必要時覆寫：

```bash
ros2 launch mobile_base_mapping mapping.launch.py mapping_config:=/absolute/slam.yaml
```

缺少指定檔案會直接失敗，不回退其他設定。原生 launch 自動 configure／activate，
使用實機時鐘。Native defaults 提供 solver／scan matching；0.05 m 格網與 5 秒
地圖更新為 commissioning 起始值，不是已標定地圖精度。詳細能力與限制見
[原生研究](../../docs/research/mapping-native-20261008.md)。

## 觀察與建圖

```bash
ros2 lifecycle get /slam_toolbox
ros2 topic echo /map --once --field info
```

應看到 active 與實際 map 資料。Lifecycle active 不等於所有輸入正常；
資料／TF 失聯時查看原生 log、來源 diagnostics及 topic／TF 工具，不宣稱可用。
`slam_toolbox` 唯一發布 `map → odom`；EKF 唯一發布 `odom → base_footprint`，
Description 的 RSP 負責模型 TF。右後 driver 可一同運作，但 SLAM 不訂閱其 scan。

需要 Foxglove 時另開終端：

```bash
ros2 launch foxglove_bridge foxglove_bridge_launch.xml
```

連線 `ws://localhost:8765`，3D panel 的 Fixed frame／Display frame 都選 `map`，
開啟 `/robot_description`、`/lidar/fl/scan`、`/map`。用 Teleop 慢速巡覽建圖區域，
需要停止時按 `k`；不要把沒有按鍵輸入視為停止。

開發驗收須在同一 `map` frame 確認 scan 與地圖牆面／固定障礙輪廓對齊，
涵蓋靜止、移動／旋轉、回訪已建圖區域，不能有持續明顯偏移或雙牆。
這是實機地圖品質驗收，不是每次保存都要新增的操作檢查。

## 保存並結束

Operator 自行選定並建立可寫目錄；下列路徑只是例子，目錄名稱不屬於產品 contract：

```bash
mkdir -p /workspace/maps/mapping_acceptance
ros2 run nav2_map_server map_saver_cli -t /map \
  -f /workspace/maps/mapping_acceptance/map --fmt pgm
```

直接使用原生 CLI，不加保存 wrapper。成功輸出固定 `map.pgm`、`map.yaml`，
YAML 使用同目錄的 `image: map.pgm`。保留原生結果／error／log：exit 0 代表
原生保存成功，非零代表失敗，應修正原因後重試；沒有可接收 map 或圖片路徑
不可寫時不能宣稱保存完成。這不是原子雙檔寫入／斷電耐久性保證。

保存成功後流程即結束：Teleop 按 `k` 並確認實體停止，再退出 Teleop，
停止 Mapping 與其他元件。不等待 route graph，不增加保存後讀回／品質檢查。
後續合法 graph 由人工準備，屬 Navigation dataset 流程。

## 開發驗收的原生重載

保存／重載是開發驗收，並非日常 Operator 的額外步驟。
停止 Mapping 後可用原生 loader 確認保存地圖：

```bash
ros2 run nav2_map_server map_server --ros-args \
  -p yaml_filename:=/workspace/maps/mapping_acceptance/map.yaml
```

另一終端：

```bash
ros2 lifecycle set /map_server configure
ros2 lifecycle set /map_server activate
```

核對重載的 `/map` 輪廓、resolution、origin 符合原生保存語意。
Nav2 1.3.13 把 origin X/Y 保存至小數三位，重載的每軸差異最多約 0.5 mm，
不要求任意 double bitwise 相等；這不是實體建圖精度驗收。
Map Server 不發布 `map → odom`；停止 SLAM 後不要以缺少此 TF 的 live scan
疊圖冒充定位驗收。實機重載疊圖比較可在 SLAM 仍在運作、AMR 靜止時，
將原生 loader 命名為 `saved_map_server` 並把輸出 remap 至 `/saved_map`；
它只供驗收，不是 runtime map owner 或正式操作入口。

## 軟體驗證

```bash
colcon build --packages-select mobile_base_mapping --symlink-install
source install/setup.bash
ROS_DOMAIN_ID=149 colcon test --packages-select mobile_base_mapping
colcon test-result --verbose
```

公開 ROS tests 使用真實 package URDF、合成房間 scan／odom TF，驗证原生
lifecycle、前左單 scan 訂閱、map/TF、已知牆面對齊、原生保存／重載及失敗。
Fixture 的數值容差不等於實機精度；真實 scan/map 對齊及估測標定仍需硬體 evidence。

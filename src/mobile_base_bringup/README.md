# mobile_base_bringup

## Mapping 情境（#39）

獨立套件驗證完成後，產品入口組合 Description、雙 LiDAR、IMU、Control、
Odometry 與 Mapping 的既有原生入口。以本 repository Docker image 執行：

```bash
ros2 launch mobile_base_bringup mapping.launch.py
```

另一終端啟動鍵盤控制，先按 `k` 發出零速度：

```bash
bash ./scripts/teleop.sh
```

這是人工啟動程序的一部分：既有 diff_drive_controller 必須收到第一筆有效
命令才開始發布輪端 odom。沒有自動初始化 publisher 或統一 readiness boolean。
保留既定 3600 秒命令 timeout；使用者按 `k` 停止並確認實體停止後才退出鍵盤。

Bringup 不能只以 process 存在或 SLAM active 判定完成。移動前應確認：

- 原生 Control 的 hardware 與 controllers active，輪端回授有效。
- 前左 scan、IMU、`/base_controller/odom`、`/odometry/filtered` 持續更新，
  原生來源 diagnostics／logs 沒有影響功能的異常。
- 完整 `odom → base_footprint → base_link → base_lidar_link_FL_1` 可用，
  原生 SLAM active 且能接收建圖輸入；不要求先有保存地圖。

使用原生工具判讀，例如：

```bash
ros2 control list_hardware_components
ros2 control list_controllers
ros2 lifecycle get /slam_toolbox
ros2 topic hz /base_controller/odom
ros2 topic hz /imu/data_raw
ros2 topic hz /lidar/fl/scan
ros2 topic hz /odometry/filtered
ros2 run tf2_ros tf2_echo odom base_lidar_link_FL_1
ros2 topic echo /diagnostics
```

每個觀察命令可用 Ctrl+C 結束。缺資料、必要 TF、裝置異常或 configure／activate
失敗時不可開始建圖；保留原生原因、停止情境、修正輸入後重新啟動，不宣稱 ready。
Mapping 的 map→odom 由 SLAM 單獨負責；EKF 與 RSP 各自保留原本 TF ownership。
這個入口不啟動 AMCL／Navigation，情境切換前先結束 Mapping。

各 config 預設由其 owning package 提供。需要覆寫時：

```bash
ros2 launch mobile_base_bringup mapping.launch.py \
  hardware_config:=/absolute/m1.yaml \
  lidar_config:=/absolute/lidar.yaml \
  imu_config:=/absolute/imu.yaml \
  filter_config:=/absolute/ekf.yaml \
  mapping_config:=/absolute/slam.yaml
```

同一 `hardware_config` 同時傳給 Description 與 Control，避免模型與裝置設定
分歧。指定檔案缺失不 fallback；各原生／owning package 保留解析與啟動責任。
不複製各套件 config、不把 Foxglove 或 Teleop 包成新的 runtime manager。

建圖觀察、原生保存固定 map.pgm／map.yaml、保存成功即結束及開發驗收重載，
見 [Mapping 操作說明](../mobile_base_mapping/README.md)。完成後先按 k、確認停止，
Ctrl+C 結束 Teleop，再 Ctrl+C 結束 Mapping Bringup，讓原生 Control 停用馬達。

## Dataset loading (#40)

`dataset.launch.py` accepts one required `dataset` directory and selects exactly
`map.pgm`, `map.yaml`, and `route_graph.geojson`. It checks that each required path
is an existing file before starting any native node, and reports the directory
and missing path on failure. Selected paths are logged. Relative paths resolve
against the launch caller's working directory; `~` is expanded. No root directory,
time-based folder name, manifest, dataset catalog or fallback is imposed.

## Prepare and load

Choose a writable directory yourself, for example:

```bash
mkdir -p /workspace/maps/warehouse
```

Place the native saved `map.pgm`/`map.yaml` there. The operator contract is that
`map.yaml` uses `image: map.pgm` from this same directory. Prepare the native
GeoJSON route graph manually in the map's coordinates as `route_graph.geojson`.
Use graph `Point` features with unique `properties.id` and `frame: map`, and
`LineString` edges whose `properties.startid`/`endid` refer to nodes. Legal routes,
direction and costs are engineering inputs, not automatically generated here.
See the [official Nav2 1.3.13 graph example](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_route/graphs/sample_graph.geojson)
and [native GeoJSON loader](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_route/src/plugins/graph_file_loaders/geojson_graph_file_loader.cpp).

```bash
ros2 launch mobile_base_bringup dataset.launch.py dataset:=/workspace/maps/warehouse
```

This narrow launch starts native `map_server` and `route_server` **unconfigured**;
it performs no automatic motion/readiness transition. In another sourced shell:

```bash
ros2 lifecycle set /map_server configure
ros2 lifecycle set /route_server configure
ros2 lifecycle set /map_server activate
ros2 lifecycle get /map_server
ros2 lifecycle get /route_server
```

Both configure results must succeed. Map Server should then be active and Route
Server inactive. Failed configure is failed dataset loading; preserve its native
screen/log reason and fix that selected dataset. A running process is not load
success. No graphless configure, empty graph, alternative dataset or previous map
is offered as a substitute. Full Navigation composition/lifecycle ownership is
provided by subsequent bringup work; this standalone workflow only verifies
native dataset loading and map publication.

Map Server owns YAML/image parsing and I/O errors. Route Server owns JSON/graph
parsing and required graph-to-map TF failures. A nonempty `graph_filepath` is
always supplied, preventing upstream's intentionally permitted graphless
configuration mode. Launch does not parse/read back the map YAML or graph,
rewrite the image reference, inspect map quality, or add a custom validator.
Maintaining the `image: map.pgm` contract and matching graph/map coordinates is
operator responsibility. Native parsing success does not prove semantic pairing,
physical traversability or complete Navigation readiness.

## Software verification

Build/test with the development image and source the overlay. The package's
pytest tests invoke the installed `ros2 launch` entrypoint, real native lifecycle
services and a transient-local `/map` subscription. Tests require isolation from
other ROS applications (use a separate `ROS_DOMAIN_ID`, e.g. 142 for this fixture).

```bash
colcon build --packages-select mobile_base_bringup --symlink-install
source install/setup.bash
colcon test --packages-select mobile_base_bringup
colcon test-result --verbose
```

The controlled 10×10 map/two-node GeoJSON fixture verifies native load and map
publication, with Route Server remaining inactive. Each of the three missing
files fails launch immediately with source path. Invalid YAML, invalid PGM,
invalid JSON, empty graph and missing graph TF each fail the relevant native
configure and do not become inactive/active. These are software fixtures, not a
real robot map, legal route-network review or hardware acceptance.

## 本地里程估測 (#38)

原生 EKF 的 launch／config／公開 ROS 測試已搬至
[`mobile_base_odometry`](../mobile_base_odometry/README.md)。
Bringup 不提供 EKF 入口或重複配置；使用 Odometry 的 `odometry.launch.py`。
後續 Mapping／Navigation 產品組合使用 Odometry 的原生入口。

## Development phase correction (2026-10-07)

Core Control/IMU/LiDAR verification uses each owning package's installed entry.
After core acceptance, ticket #38 integrates the model, real wheel/IMU data and
native EKF; #39/#41 then deliver Mapping/Navigation product composition.
The existing dataset entry is a partial software delivery, not complete product
Bringup or a prerequisite for component tests. Local estimation now belongs to
mobile_base_odometry.
The additional component/base wrappers introduced in dc3f6ee were withdrawn.
Their recorded software results remain historical evidence, not current entries.

# mobile_base_odometry

將 Control 的真實輪端里程計與 Perception 的 IMU 角速度送入原生
`robot_localization/ekf_node`，提供本地融合里程計。
本套件只包含 launch／config，不實作融合演算法或自製 TF 程式。

## 責任與介面

- 輸入：`/base_controller/odom`、`/imu/data_raw`。
- 輸出：`/odometry/filtered`，唯一發布 `odom → base_footprint`。
- Control 的 odom TF 維持 disabled；Description 的單一 RSP 負責模型 TF。
- Description、Control、IMU 各自啟動；這個入口不啟動其他套件、
  Teleop、SLAM、AMCL 或 Navigation，不宣告產品 Bringup ready。

## 啟動

先分別啟動既有元件，確認輪端與 IMU 資料、模型 TF 有效：

```bash
ros2 launch mobile_base_description description.launch.py
ros2 launch mobile_base_control m1.launch.py
ros2 launch mobile_base_perception imu.launch.py
```

每行使用不同 terminal。Control 啟動涉及馬達 enable，必須符合現場操作條件。
既有 3600 秒 command timeout 保留。原生 controller 首筆有效命令前可能不發布
odometry；透過既有 Teleop 送出零速度初始化，再檢查來源。後續產品 Bringup
必須承接初始化／readiness，這裡沒有永久 command publisher。

另開 terminal，明確指定已安裝的起始 profile：

```bash
ros2 launch mobile_base_odometry local_estimation.launch.py \
  filter_config:=$(ros2 pkg prefix --share mobile_base_odometry)/config/ekf.yaml
```

`filter_config` 仍為必填，可改用其他原生 YAML 的完整路徑。相對路徑以目前
工作目錄解析，支援 `~`；缺檔報錯，YAML 解析由原生 ROS 參數載入負責。
node 名稱為 `ekf_filter_node`。修改 source config 使用 `--symlink-install`，
下一次 launch 才套用，不支援 runtime hot reload。

## Commissioning 設定與限制

Operator 已採用起始設定，標定留後續。設定從原 Bringup 搬移，EKF 參數不變：
20 Hz、planar estimation、輪端 vx 與非完整約束 vy=0、IMU yaw rate。
不融合不可用 orientation／acceleration；安裝旋轉由模型負責，不重複套用。

輪端 covariance 使用原生 diff_drive_controller 文件的起始建議值；IMU 使用
既有靜止實測 second moments about zero，包含當時 bias。這不是 covariance
標定、bias 補償或漂移上限，也不宣稱定位精度已通過。
保留 `3600 秒／0.50／0.50` 與既有硬體設定。

架高轉輪只驗證輪端資料鏈與模型；不能當成底座實際移動或落地動態融合驗收。
靜止／架高／落地證據必須分開記錄，精度及 calibration 留後續。

## 軟體驗證

```bash
colcon build --symlink-install --packages-select mobile_base_odometry
source install/setup.bash
ROS_DOMAIN_ID=93 colcon test --packages-select mobile_base_odometry
colcon test-result --verbose
```

公開 ROS 測試使用合成 wheel／IMU、真實 native EKF／RSP，涵蓋明確選定的 fixture
配置及已安裝 commissioning 配置，確認 filtered odometry、模型 TF 與停止 EKF
後 odom edge 停止。合成速度與 uncertainty 不代表實車標定。
全套測試使用 sequential executor 或隔離 domain，避免合成來源互相污染。

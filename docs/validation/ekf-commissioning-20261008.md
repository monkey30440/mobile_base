# #38：commissioning 起始設定與真實資料鏈

Operator 採用「commissioning 起始設定，標定留後續」。本次只將原生配置納入
既有套件及驗證其公開 ROS 行為，不新增融合／TF 程式或完整产品 Bringup。
平台為 AGX Thor、Ubuntu 24.04／ROS 2 Jazzy，既有映像 `566d8ff74d6b`、Fast DDS。
實機 domain 197，軟體 fixture 分開執行。實作前基準 `f447874`。

## 配置與 responsibility

- Control 將 YAML 的 pose／twist covariance diagonal 傳給原生 controller。
  起始值 `[0.001, 0.001, 0.001, 0.001, 0.001, 0.01]` 出自
  [diff_drive_controller 4.42.1 原生參數文件](https://github.com/ros-controls/ros2_controllers/blob/4.42.1/diff_drive_controller/src/diff_drive_controller_parameter.yaml)。
  不代表實車 covariance 已標定。
- Perception 使用先前已驗證靜止資料的 gyro second moments about zero：
  `[4.576113064280129e-7, 9.063136025567312e-8, 2.7384782088781707e-7] (rad/s)^2`。
  包含當時 bias；不是 bias 補償、標定 variance 或 drift bound。
- 既有 narrow local-estimation 入口安裝可重用 `config/ekf.yaml`；caller 明確選取。
  原生 EKF 融合輪端 vx、非完整約束 vy=0、IMU yaw rate，不融合不可用 orientation
  或 acceleration。模型獨自負責安裝旋轉；RSP 獨自負責模型 TF。
- 保留 `3600 秒／0.50／0.50`、馬達上限及硬體設定，不改 RMW 或 protocol。

## 首次 odometry 初始化根因

首次靜止觀測有有效 JointState／IMU，卻沒有 wheel odometry。
[原生 4.42.1 source](https://github.com/ros-controls/ros2_controllers/blob/4.42.1/diff_drive_controller/src/diff_drive_controller.cpp)
的 reset buffer 初值為 NaN；有效命令或 timeout 歸零之前，非有限 reference 會讓
update 在 odometry publish 前返回。既有 3600 秒 timeout 使此狀態不會立即消失。

送有效零速度後，原生 wheel odometry 即開始發布。不是 QoS、topic 名稱或融合程式錯誤。
本次只由驗證者／既有 Teleop 初始化，不新增永久 command publisher。
後續產品 Bringup 須承接 initialization/readiness ownership。

## 使用正式套件的靜止實機驗證

Description、Control、IMU 分別使用已安裝入口；EKF 使用已安裝 `config/ekf.yaml`。
11 筆全零 TwistStamped 初始化，publisher 隨後移除，沒有非零速度。
15 秒取得 wheel 300、IMU 2589、filtered 300 筆；frame、有限值、normalized quaternion
及 base/sensor/wheel TF 均通過。controller odom TF disabled。

停止 EKF 後 `odom → base_footprint` 停止更新，來源仍健康、RSP 模型 TF 保留。
這比只數 `/tf` publisher 更能支持 edge ownership。
最後 native M1 inactive，獨立 FC03 讀回兩輪 status 6、alarm 0、目前／目標 RPM 0。

## 架高原生 Keyboard 資料鏈

Operator 確認仍架高、在旁可立即停止。正式套件搭配原生 teleop_twist_keyboard，
暫時測試 speed 0.03 m/s、前後各 2 秒，未修改正式速度限值。

| 方向 | 末段 wheel vx | 末段 filtered vx | 原生停止回授 |
|---|---:|---:|---|
| 前進 | +0.030013 m/s | +0.030221 m/s | 歸零 |
| 後退 | −0.030076 m/s | −0.030305 m/s | 歸零 |

兩個輪子 TF 有效；EKF 停止後 odom edge 停止，最終獨立讀回兩輪 inhibited、alarm 0、RPM 0。
Operator 回覆「沒注意到」；現場目視尚未確認，不以軟體回授代替獨立觀察。

第一次 PTY attempt 因測試器過量送鍵造成 pending input，之後只向 parent 發 SIGINT
也未讓鍵盤退出，逾時為 FAILED；清理仍成功。第二次限制送鍵 10 Hz、停止前清除
pending terminal input、使用真正 `\x03` Ctrl-C，PASS。未修改產品 runtime。
原生 Jazzy keyboard 不提供 repeat_rate/key_timeout 行為，成功 attempt 未使用這些參數。

**架高時底座未移動；wheel-derived 虛擬位移不是實際 chassis travel 證據。
本輪尚未通過落地動態融合、physical pose accuracy 或 covariance 標定；#38 不提前關閉。**
靜止 yaw 漂移符合目前未補償 bias 限制，不宣稱定位精度。

## 軟體驗證及 review

公開原生 Odometry covariance 測試先 RED（全零），新增原生參數傳遞後 GREEN。
已安裝 EKF profile 另經原生 EKF／RSP 合成資料 seam 驗證。
完整 suite 初次並行受兩套件共用 domain 的合成 IMU topic 污染；
獨立 domain 重跑受影響 Perception，最後 **79 tests，0 errors，0 failures**。
無修改測試 assertion 以繞過失敗。執行全套時應隔離 domain 或按套件 sequential 執行。

Standards review 0 findings；Spec review 0 findings。Spec 明確指出不能僅憑配置交付關閉 #38。
原生 controller_manager pal_statistics 停止時有 invalid-context ERROR；
程序仍 finished cleanly、停用與獨立零 RPM 讀回通過，不宣稱所有日誌均無 ERROR。

## 原始 evidence

[執行配置、觀測器、ROS raw events、TF、logs、失敗及成功 attempt、最終讀回](artifacts/ekf-commissioning-20261008.tar.gz)

SHA256：`d141189bc3612c1cf933fb2115b5ae53d719ba2a7ea123fa796ecb9763050f0a`。

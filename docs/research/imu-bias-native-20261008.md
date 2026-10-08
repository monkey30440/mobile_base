# V1 IMU gyro bias：native capability research

日期：2026-10-08。問題／驗證背景：[研究票 #48](https://github.com/monkey30440/mobile_base/issues/48)。範圍限 Operator 人工靜止標定、保存及套用 offset，並保留合法慢速旋轉；本筆記不操作硬體、不設定正式標定值。

結論：已查核的 native 能力未提供完整要求。`robot_localization` 3.8.3 沒有 gyro bias state；Jazzy `imu_complementary_filter` 的 online steady-state estimator 會有吸收 0.10 rad/s 合法等速旋轉的條件，且沒有 Operator 標定／保存／載入 offset 的完整介面。HandBoard 文件不足以證實 USB firmware 的人工 trigger 或 persistence。最小補足候選是人工離線估計加上既有必要 IMU adapter 的明確 SI offset 設定與固定減法，而非引入新 orientation filter；這是待決策候選，尚未完成實車驗證。

## CONFIRMED：版本與 upstream 能力

- 部署基準由本次診斷確認為 `robot_localization` 3.8.3。該版本 state 明列 position、orientation、linear/angular velocity、linear acceleration，共 15 維，沒有 gyro bias；因此 EKF 不會把常量 gyro offset 當成獨立 bias state 估計。調 covariance 或新增 wheel yaw-rate 是量測融合，不等同 bias calibration。[3.8.3 state 定義](https://github.com/cra-ros-pkg/robot_localization/blob/3.8.3/include/robot_localization/filter_common.hpp)
- 查核時 Jazzy rosdistro 對 `imu_tools` 的 release 是 **2.1.6-1**，source branch `jazzy`；網頁索引仍可能顯示舊的 2.1.5-1。本研究查 **2.1.6 tag**，不以 rolling 替代；實車未確認安裝 imu_tools，不能宣稱此版已部署。[Jazzy distribution](https://github.com/ros/rosdistro/blob/master/jazzy/distribution.yaml)
- 2.1.6 complementary filter 初始三軸 bias 是零，預設 bias alpha 0.01。`checkState` 只檢查加速度模長接近 9.81（容差 0.1）、相鄰角速度差不超過 0.01，以及角速度與既有 bias 差不超過 **0.2 rad/s**。通過就向目前角速度更新 bias，預測扣除 bias。因此水平、近重力、變化平緩的 **0.10 rad/s** yaw turn 可以通過並逐步被吸收；這是 source 推導，不是本車重播結果。突然轉動可能暫時被 delta gate 擋住，無法保證持續轉動受保護。[2.1.6 implementation](https://github.com/CCNYRoboticsLab/imu_tools/blob/2.1.6/imu_complementary_filter/src/complementary_filter.cpp)
- ROS wrapper 會在 `imu/data` 扣除三軸估計 bias，所以不只是 orientation smoothing。它複製 raw message，再換 orientation 和 orientation covariance；angular velocity covariance 並未加上 bias estimate uncertainty。`do_bias_estimation` 和 `bias_alpha` 啟動時宣告 read-only；沒有人工 calibration service、保存／載入三軸 offset 參數。停用估計會同時停用 wrapper 的扣 bias。[2.1.6 ROS wrapper](https://github.com/CCNYRoboticsLab/imu_tools/blob/2.1.6/imu_complementary_filter/src/complementary_filter_ros.cpp)
- library 有 bias getter、估計 enable 與 alpha setter，但沒有 bias setter 或 serialization interface；ROS wrapper 也沒有對應保存介面。因此即便另寫控制器在靜止後 freeze library，仍須自建生命週期及 persistence，不能算原生完整解法。[2.1.6 public API](https://github.com/CCNYRoboticsLab/imu_tools/blob/2.1.6/imu_complementary_filter/include/imu_complementary_filter/complementary_filter.h)

## CONFIRMED／UNRESOLVED：晶片與 USB firmware 分開判讀

**CONFIRMED（文件內容）**：授權 reference 的 [HandBoard guide](../../reference/tdk_ros2_imu/HandBoard_IMU_V1_Quick_Guide.md) 說上電約 2 秒校正後開始 59-byte USB binary 輸出，gyro 單位 dps、acceleration 單位 g；也警告無磁力計 yaw 長期漂移。它沒有說明這 2 秒是否估計 gyro rate bias、是否改正 Gyro X/Y/Z、靜止前提、結果 readback 或掉電保存；「有 startup calibration」不能直接解讀為本次完整需求已滿足。

**CONFIRMED（晶片能力）**：TDK datasheet 的 user-programmable gyro offset registers 解析度為 1/32 dps（約 0.0005454 rad/s）、範圍 ±64 dps。解析度比本次約 0.0003131 rad/s yaw bias 大；單純整數 register offset 可能無法精確表示這次殘差。[TDK IIM-42652 datasheet，user programmable offset](https://invensense.tdk.com/wp-content/uploads/2022/04/DS-000440-IIM-42652-TYP-v1.1.pdf)

**UNRESOLVED**：沒有板商 USB command／firmware source 證據支持人工 trigger、讀回 offsets、寫入 nonvolatile storage、開機載入或 reset 指令；不能從 SPI/I²C 晶片 registers 推論 USB 支援，也不能宣稱 firmware 一定沒有這些能力。若取得板商協定且驗證符合完整要求，應重新評估板端 ownership。

## 最小 confirmed gap 與責任候選

Gap 是「Operator 確認靜止 → 明確產生可審查 bias → 保存 → 下次啟動同樣套用 → 運行時不把慢速旋轉判為零」這個生命週期。native EKF 保留融合責任；不需因 rate offset 另造 orientation fusion。

候選責任邊界：offline 工具只讀一段由 Operator 指定且確認靜止的 **未套 host offset** 三軸 rate，產出樣本數、時間窗、mean、dispersion、sensor/frame、單位與來源紀錄，拒絕資料缺漏／非有限值；Operator 審查後保存三軸常量。既有必要 adapter 只负责 dps→rad/s 後 `ω_corrected = ω_raw − b`，保留原始證據並明確區分 corrected input。沒有 deadband、運行時自學習或低角速度歸零，所以固定 bias 不會隨 0.10 rad/s turn 累積；這是代數性質，仍須實車驗證。若 bias 存於 IMU frame，就在同 frame 扣除再依既有 TF 轉換；不能把 base yaw bias 偷當 chip Z offset。

ROS `sensor_msgs/Imu` 要求 rad/s、m/s²；covariance 零矩陣表示未知，未提供 orientation 應標記首元素 −1。固定減法不會使 noise variance 消失；bias calibration uncertainty 如何納入 corrected covariance，必須由獨立量測決定，不能用去平均後的好看結果捏造 confidence。[Jazzy Imu message](https://github.com/ros2/common_interfaces/blob/jazzy/sensor_msgs/msg/Imu.msg)

## REQUIRES HARDWARE VALIDATION／REQUIRES CALIBRATION

- **REQUIRES HARDWARE VALIDATION**：板端 startup 校正究竟作用在哪些欄位、上電靜止與非靜止效果、重啟／掉電後殘差，以及是否提供可驗證 USB trigger/readback/persist；目前均未測。以不同開機、溫度／暖機狀態驗證固定 host offset 有效性，避免雙重補償。
- **REQUIRES CALIBRATION**：正式 window 長度、允許 dispersion／漂移、有效條件與重標定時機尚未確立。必須以獨立靜止資料和正／負慢速旋轉驗證 rate 與 EKF yaw；不把本次診斷均值直接寫入正式設定。
- **診斷證據而非 release validation**：#48 背景是新靜止 mean −0.0003131 rad/s；同窗減此均值約改善 96%，wheel yaw fusion 約 0.2%。本次父流程的 held-out console 約 7.65 s：未補償 yaw delta −0.00248974 rad，診斷減法 −0.00017324 rad（約 93% 改善）；時間短，尚不足跨開機／温度及慢速旋轉保證。追溯以 #48 與父流程診斷產物為準，不將這些數字當 upstream 保證。

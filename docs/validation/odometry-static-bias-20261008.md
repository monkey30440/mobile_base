# 靜止 odometry yaw 漂移診斷 — 2026-10-08

基準 `ddab777`；Operator 要求暫停 Navigation 主線並先排查靜止漂移，
後續明確將人工靜止 IMU 零偏標定、保存／套用補償與靜止／慢速旋轉驗證納入 V1。
本輪診斷不啟動 Control／Servo ON、不發布任何實車速度命令。

## 已重現的症狀

之前 Mapping 實機採集有 533 筆連續零輪端速度資料，跨 135.6006 秒。
輪端 yaw delta 0，融合 yaw delta −0.0508842 rad（約 −2.92°），
融合位置 delta 0.00001574 m。IMU 平均 yaw-rate −0.000374886 rad/s，
融合平均 yaw-rate −0.000378269 rad/s。
因此這份證據主要是 yaw 漂移，不能把所有位置誤差也直接歸因 IMU。

Agent-runnable historical detector：`python3 /tmp/odom-drift-diagnosis/check_recorded.py`。
已執行並因零輪端速度期間融合 yaw 改變而 RED；0.001 rad 只是此診斷
辨別門檻，並非 V1 精度規格。歷史錄製不會因未來修正而變成 GREEN。
後續修正必須用新採集／重播驗證，不能修改原始歷史證據。

## 新採集與因果差異驗證

Operator 確認實車靜止、沒有 Teleop；只啟動 Perception IMU 35 秒。
取最後 3000 個有效樣本：yaw-rate mean −0.000313096 rad/s，
standard deviation 0.000137931 rad/s；相當於若持續積分，每分鐘約 −1.076°。
來源 frame 為 base_imu_link。

使用原生 robot_localization 3.8.3、完整已確認模型、實際 angular covariance、
同一 wheel 零速度與現有 twist covariance，在隔離 ROS domain 151 重播。
每次只改一個因素；所有案例使用相同新的 receipt timestamps／發送時序，
此為差異重播，不宣稱原始 acquisition timing 已復原。

| 案例 | 融合 yaw slope（rad/s） |
| --- | ---: |
| 現有配置 | −0.000327373 |
| 只加入 wheel yaw-rate 融合 | −0.000326679 |
| 只扣本次量得的 gyro yaw mean | −0.0000131935 |

加入輪端 yaw-rate 在現有 uncertainty 下只改善約 0.2%，不能解決本症狀。
零偏減除顯著下降約 96%；這是因果探針，不是部署標定。

另將 3000 樣本分成前／後 1500：只由前段算 bias（−0.000302775 rad/s），
只重播後段，以避免同一資料估計再驗證的過度樂觀。
現有配置 slope −0.000325429，加入 wheel yaw-rate −0.000325454，
零偏減除 −0.0000226462 rad/s（約下降 93%）。這仍只是短時間、同一現場／
同一 session 的 holdout，不能宣稱跨溫度／重啟／長期穩定性已驗證。

## 結論與邊界

CONFIRMED：未補償 gyro yaw-rate 的非零平均值在目前「輪端 vx/vy + IMU yaw-rate」
配置下，被原生 EKF 積分成靜止 yaw 漂移；不需要錯誤 TF 或資料中斷才能重現。
目前不證明任何時刻所有 TF／時間均無錯，而是排除它們作為此差異測試的必要原因。

現有 covariance 為 commissioning 起始值，IMU second moment 包含當時 bias；
把 covariance 加大或任意壓低輪端 covariance 不能當成完成零偏標定。
正式補償／標定 workflow 與 responsibility 必須先完成原生研究及真人 decision。

REQUIRES CALIBRATION：有效靜止條件、標定時段／暖機、三軸 SI offsets、
bias 去除後 covariance 與部署 uncertainty。
REQUIRES HARDWARE VALIDATION：補償後較長靜止觀察、合法慢速旋轉保持方向／尺度，
以及重啟後配置能重用；溫度依賴性尚未量測。

研究 ticket：[IMU 零偏標定與慢速旋轉的原生能力](https://github.com/monkey30440/mobile_base/issues/48)。
現有配置不修改；未宣稱漂移已修復。後續 Navigation 保持暫停。

[原始資料／差異驗證 archive](artifacts/odometry-static-bias-20261008.tar.gz)
SHA256：`dd4f1a7a142a11ae92260a45b5c4e8a790fa32f1a433d655b436020bc0f84f22`。

原生依據：
[3.8.3 configuration guide](https://github.com/cra-ros-pkg/robot_localization/blob/3.8.3/doc/configuring_robot_localization.rst)
建議利用輪端 velocities 與非完整約束；
[3.8.3 state vector](https://github.com/cra-ros-pkg/robot_localization/blob/3.8.3/include/robot_localization/filter_common.hpp)
只有 15 項 pose／velocity／acceleration states，沒有 gyro bias state。

## Covariance 替代假設的補充驗證

Operator 提出是否改 covariance。以同一後段實測資料／模型／native EKF
再比較以下案例；倍率只是 sensitivity probe，不是實測 covariance。

| 案例 | 融合 yaw slope（rad/s） |
| --- | ---: |
| 現有配置 | −0.000325332 |
| 只將 IMU covariance ×1000 | −0.000325103 |
| 加 wheel yaw-rate，IMU covariance ×1000 | −0.000324394 |
| 加 wheel yaw-rate，IMU covariance ×1000000 | −0.0000738249 |

只調 covariance 不能提供額外 yaw 約束。加入 wheel yaw-rate 並大幅降低 IMU
信任可以降低偏差（本 probe 約77%），但仍未去偏，也未驗證動態估測代價。
不能把這些膨脹倍率部署當標定。正式責任是固定 bias 補償，並分別以 evidence
決定去偏後量測不確定性、wheel uncertainty 與應融合的來源。

Operator 已對 [人工 IMU 零偏標定、補償與使用邊界](https://github.com/monkey30440/mobile_base/issues/49#issuecomment-6055576784)
的兩項 frontier 回覆採用；此段記錄研究／決策當時的狀態。
後續 #50 實作與實機驗證見 [人工 IMU 零偏補償驗證](imu-bias-calibration-20261008.md)。

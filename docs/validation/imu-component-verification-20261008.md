# #36 IMU元件驗證（2026-10-08）

正式主機AGX Thor；無其他IMU driver／serial owner時啟動原生installed imu.launch.py。
不啟動馬達。兩次12秒passive session均接收有效資料，launch退出0。
首次observer把JSON diagnostics level字串誤判為bytes而assert失敗；修正observer型別判斷，
不修改driver。第二次1942樣本、172.545Hz、frame base_imu_link、stamp無倒退、
所有量測finite、orientation covariance[0]=-1、accel/gyro covariance全零unknown。
最後diagnostics OK、valid_samples1933、invalid_packets0。各topic不同receipt時間，
樣本數與diagnostic計數不要求完全相同。重啟與SIGINT clean shutdown通過。
這是host receipt timestamp，不等於acquisition time／同步或延遲已標定。

IMU/packet/ROS/launch相關18tests通過，3個native LiDAR source tests排除。
完整Perception首次21cases有1項前左publisher discovery失敗，保留此回歸問題，
不得宣稱完整套件全綠；該案例屬#37，不據此推定IMU driver故障。
原始完整結果仍在build/mobile_base_perception/pytest.xml與colcon test log。

[實機原始observer/topic traces/logs](artifacts/imu-component-verification-20261008.tar.gz)。

## #36仍未解決的硬體驗收項目

封包/單位轉換/invalidity/timeout/communication diagnostics有軟體與文件證據，
實機baud/framing、靜止重力與frame安裝已有適用觀測／Operator確認。
但目前未找到實機受控旋轉gyro方向／尺度資料；架高轉輪不使底座IMU旋轉，
不能以輪向、model yaw或stationarygravity推定gyro sign/scale。
需要Operator完成落地條件，再執行左右受控底座旋轉並同步觀測wheel/IMU與TF。
這不是再次要求精密地面角度標定，而是確認實際資料正負與基本尺度相容。
若需要量化精度/bias/covariance，仍屬後續calibration，unknown不能當calibrated。

本輪不改runtime，不關閉#36，不解除#38 dependency；所有驗證程序已停止。

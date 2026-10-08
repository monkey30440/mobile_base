# #38：架高與落地本地估測整合驗收

基準 `bb265bf`，AGX Thor／Jazzy／Fast DDS，既有映像 `566d8ff74d6b`、domain197。
本輪沒有修改產品 source、launch 或配置，只執行實機驗證及保存 evidence。
使用已安裝、各自獨立的 Description／Control／Perception IMU／Odometry 入口；
EKF 明確選取 `mobile_base_odometry/config/ekf.yaml`。沒有完整產品 Bringup。

## 現場條件與原生流程

先唯讀確認兩輪 inhibited、alarm0、目前／目標RPM0。
Operator 確認仍穩固架高、在旁可觀察並立即停止，才啟動零速度元件。
各 trial 先驗證15秒靜止資料，再等待獨立 motion gate；通知觀察時段後才釋放。
動作使用原生 `teleop_twist_keyboard`，啟用 stamped，cmd_vel remap 至
`/base_controller/cmd_vel`。既有 timeout3600與速度上限0.50／0.50不變。
測試器只是暫時 PTY 操作者／ROS 觀測器，不是新增產品 runtime。

## 架高：真實輪端與融合速度

0.03 m/s 前進、後退命令時段各5秒，中間停止約3秒。
原生回授／filtered速度方向一致，來源健康，模型輪TF可取得。

| 方向 | 末段 wheel vx | 末段 filtered vx | 停止 |
|---|---:|---:|---|
| 前進 | +0.029908 m/s | +0.029993 m/s | 原生回授歸零 |
| 後退 | −0.030013 m/s | −0.030073 m/s | 原生回授歸零 |

Operator 回覆「方向都正確，中間與最後都停止」。
命令時段不是精確機械轉動時間；前進回授的非零窗口約4秒，後退約5.1秒，
包含啟動／DDS發現／速度濾波／停止響應。沒有以此建立位移精度要求。
架高時 chassis 未移動，EKF 的 wheel-derived 位移不可當成實際地面 travel。

## 落地：真實 wheel／IMU／EKF 旋轉資料鏈

原生停用並獨立讀回零RPM後，由 Operator 落地，確認整個旋轉範圍淨空，
在旁可立即停止。0.10 rad/s 左轉／右轉命令時段各1.75秒，名義各約10°，
中間停止約3秒。先送零速度按鍵 warmup2秒讓原生 keyboard publisher 完成發現。

| 方向 | 末段 wheel wz | 末段 raw IMU z | 末段 filtered wz | filtered yaw 變化 |
|---|---:|---:|---:|---:|
| 左轉 | +0.09902 rad/s | +0.10402 rad/s | +0.10401 rad/s | +10.3167° |
| 右轉 | −0.09917 rad/s | −0.10740 rad/s | −0.10499 rad/s | −10.3610° |

這些是實際觀測 snapshot／filter delta，不是量測誤差上限或精度標定。
不同來源的瞬時值不代表同步統計或彼此獨立的真實角度 reference。
Operator 目視回覆「左轉、右轉方向與約略角度正確，中間及最後停止」。
因此實際底座旋轉、三個來源正負方向、名義rad/s尺度及停止獲得有界實機支持。
沒有精密角度或地面直線位移 reference，不宣稱 translation/yaw accuracy 通過。

## TF ownership 與最後狀態

兩次trial均有有效輪端／IMU／filtered資料，base與兩台scan frame及IMU的TF可取得；
驅動輪TF沒有NaN或缺失。Controller odom TF disabled；原生 EKF 唯一發布
`odom → base_footprint`，RSP唯一模型TF owner。

各次停止EKF後 odom edge停止，source仍健康、模型TF保留，支持 edge attribution。
原生controller雖宣告 `/tf` publisher，不能只按publisher數判斷特定edge ownership。
最後 native M1 inactive、keyboard與所有硬體workers退出；獨立FC03讀回
ID1／ID2均status6、alarm0、目前RPM0、目標RPM0。沒有保留啟動中的馬達流程。
原生 pal_statistics shutdown invalid-context ERROR仍存在，程序finished cleanly；
沒有宣稱整份日誌無ERROR，也沒有修改native runtime去隱藏它。

## #38 acceptance 對照與可重用證據

| AC | 本輪／既有證據 |
|---|---|
| URDF authority／footprint與模型tree | 自含Description assets、已確認安裝姿態；名稱統一base_footprint、URDF單父graph軟體驗證，模型本輪未改 |
| 原生RSP／sensor TF／真實必要joint state | [模型原生輪TF](m1-position-native-tf-20261007.md)、Operator已確認座標與雙scan；[雙LiDAR原生stream/TF](lidar-power-soak-20261008.md)可復用；本輪base/sensor/driving-wheel TF與真實feedback通過 |
| 原生RL融合／唯一odom TF owner | [配置交付](ekf-commissioning-20261008.md)、[新套件搬移／靜止](odometry-package-20261008.md)、本輪控制停止歸因與真實動態資料 |
| 公開TF/odom／實機Teleop方向與尺度 | 本輪架高前後＋落地左右，Operator獨立目視確認；nominal geometry／gyro units與既有元件scale evidence復用；正式標定依Operator確認留後續 |
| Mapping/Navigation重用及責任範圍 | 已安裝Odometry/RSP/config可被後續composition使用；本輪不宣稱Mapping/Navigation流程已驗收，不承擔上半身joint/control或全機碰撞安全 |

沒有將未量測的passive caster joint state當成即時量測或補假state。
此驗收只涵蓋Mapping/Navigation需要的base、sensor及驅動輪TF，不宣稱所有被動機械分支的動態TF已取得。
名義輪座姿態與量測輪角的區分保留。

正式 covariance、IMU bias補償、有效輪徑／輪距、精密機械／地面位移和估測精度
仍為 REQUIRES CALIBRATION，依最新confirmed spec與Operator「commissioning起始設定，標定留後續」處理。
不把原AC中「標定evidence」寫成已標定；issue須明示本次commissioning acceptance修訂與這些保留項目。
完成#38配置／資料鏈slice不等同V1 calibration、Feature Freeze或量產精度ready。

## 軟體與原始 evidence

產品程式與配置沒有變更，復用`bb265bf`的79tests／0errors／0failures，不無故重跑全套。
原生觀測器含健康／有限值／direction／stop／cleanup檢查，raw ROS events與TF皆保存。
summary的`counts`／`last_filtered`／`limits`是15秒pre-motion靜止phase；
動態結果在對應`*_native_keyboard_*`欄位，不能用靜止snapshot當成動態末值。
`observations`是重複觀測迴圈檢查數，不是獨立topic訊息數。

[架高／落地觀測器、raw事件／TF／logs、實際配置、Operator確認與獨立讀回](artifacts/odometry-dynamic-20261008.tar.gz)

SHA256：`61be9ec992d23988cafd51f162c3a9018684e0d302b3dc5f49ca2ac70499008f`。

## Standards

0 findings。基準、平台、配置、現場條件、Operator確認與hash一致；
未將名義尺度或架高位移當成精度標定，未新增runtime smell。

## Spec

0 remaining findings。配置與資料鏈commissioning slice可結案，條件是先同步
AC4的明示修訂：方向／名義尺度／資料鏈已驗證，正式標定依Operator確認留後續。
必要TF、實際融合與停止、配置重用獲得支持；不宣稱passive caster動態state、
Mapping/Navigation完整workflow、bias補償、精密位移/yaw精度、量產或Feature Freeze。

兩軸總計：Standards 0／Spec 0；沒有剩餘阻塞finding。

# 人工 IMU 零偏補償驗證（2026-10-08）

對應 implementation #50、confirmed decision #49、V1 spec #32。
平台為 AGX Thor、Ubuntu 24.04／ROS 2 Jazzy；robot_localization 3.8.3。
實機靜止、正負旋轉與 ROS node 重新啟動已完成；最終隔離回歸 103 項通過。

## 實作責任

離線 `calibrate_imu` 只訂閱 `/imu/data_raw`。Operator 確認實體靜止，
工具計算三軸平均零偏與扣除均值後的 sample variance，保存具來源、frame、
units、樣本數與時間的 YAML，不覆寫既有檔案。

Perception 原有 USB adapter 保留 raw；同 frame 固定扣除保存的 SI bias，
發布 `/imu/data`。設定缺失／無效時 raw 可繼續，但 corrected 不發布並診斷 WARN。
不使用 adaptive bias、低速歸零、orientation filter 或自製融合／TF。
原生 EKF 的 IMU 輸入改為 corrected；其其他融合參數及輪端 covariance 未調整。

## 真實標定

AMR 已落地、Operator 確認靜止；標定時未啟動 Control，沒有 Teleop。
由公開 CLI 採集 `/imu/data_raw`：60.0093 秒、10,347 筆。
frame `base_imu_link`、units `rad/s`，UTC `2026-10-08T08:45:42.247776+00:00`。

| 軸 | 保存的 bias (rad/s) | Sample variance ((rad/s)²) |
|---|---:|---:|
| X | 0.000879815090473 | 2.12253251327e-8 |
| Y | -0.000321304972060 | 2.81312755207e-8 |
| Z | -0.000436255721481 | 1.95039476361e-8 |

結果保存在 Perception `config/imu_calibration.yaml`，已審查 frame／來源／
數值／樣本與連續時間；不能證明溫度穩定或跨裝置適用。
檔案明確為本平台實測 commissioning 設定，新裝置或條件改變需人工重新標定。

## 獨立較長靜止觀察

標定程序停止後，以已安裝的 Description、Control、IMU 與 Odometry 入口啟動。
Operator 明確允許 enable 馬達，在原生鍵盤 Teleop 按 k 初始化零速度，
並確認實體靜止；觀測程序沒有速度 publisher。
以下資料未參與標定，排除輪端第一筆之後的前五秒。

區間 monotonic `283774.841019402` 至 `283969.154328647`，194.3133 秒。

| 來源 | 筆數 | Z angular velocity 均值 (rad/s) | 備註 |
|---|---:|---:|---|
| raw IMU | 33,505 | -0.000410357815344 | 保留原始量測 |
| corrected IMU | 33,505 | +0.000025897906137 | 均值絕對值減少約 93.7% |
| wheel odometry | 3,886 | 0 | vx、wz、yaw delta、XY delta 均為零 |
| native EKF | 3,887 | +0.000026170624825 | yaw delta +0.289596°；XY delta 0 m |

raw／corrected 同區間 sample std 都約 `0.0001441515 rad/s`；
固定減均值保留量測變化，沒有 deadband。IMU 最大 receipt gap 約 0.0339 秒；
wheel 約 0.0604 秒；EKF 約 0.0563 秒。觀測到 `odom → base_footprint` 持續更新。

結果支持本次靜止零偏補償改善，**不代表 odom 絕對不漂、全溫度標定或定位精度通過**。
同條件 dispersion 不是完整 bias uncertainty；firmware 開機零偏、溫度與長期變化
仍需後續量測。原先診斷資料與本次不同 window 的均值不同，不寫死歷史均值。

## 軟體回歸與 review

公開 CLI／PTY／ROS topics 與原生 EKF 測試驗證保存／重載、
raw 保留、固定補償、正／負慢速量測及接近零但非零的合法角速度。
錯誤 frame、非有限值、重複 timestamp 與中斷 raw capture 都拒絕保存。
最終隔離完整回歸：6 套件、103 tests、0 errors、0 failures、0 skipped。
雙軸 review 比較基準為 Operator 確認的 1d56bd7：Standards 0 findings；
Spec 的操作檔名衝突及不良資料覆蓋缺口已修正，覆查無新增阻擋 findings。

首次完整回歸有 raw 斷流與 native map service timeout；兩者獨立程序重驗通過。
第二次完整回歸定位新測試的跨 topic 到達順序競態：corrected 新值先到，
raw[-1] 還是前一測試速率。測試改以相同 header.stamp 配對後檢查；
runtime 沒有為此修改。保留失敗記錄，不以重跑通過隱藏限制。

## 正／負落地慢速旋轉

Operator 在旁可立即停止；透過原生鍵盤 Teleop 各按 j／l 約兩秒、按 k 停止。
觀測者不發送速度命令，Operator 分別確認向左／向右並最終停止。
以下 window 使用 native wheel |wz| > 0.04 rad/s 定界，包含起停過程；
均值是本次量測，不是命令值或經標定的尺度／角度驗收。

| 方向 | Window (monotonic) | wheel mean wz | corrected mean wz | EKF mean wz |
|---|---|---:|---:|---:|
| 左轉 | 284023.697040303–284025.695658883 | +0.1669386924 | +0.1742956007 | +0.1767162371 |
| 右轉 | 284102.696395277–284104.640195261 | -0.1664197705 | -0.1746035347 | -0.1753312755 |

單位為 rad/s。raw 同區間均值為 +0.1738593450／-0.1750397904 rad/s，
補償量維持保存的固定 -0.0004362557；真實正負旋轉未被低速 gate／deadband 吞掉。
wheel 與 IMU 差異不被本次 bias correction 當成 geometry calibration 解決。
測試後 native Control successful deactivate／shutdown 且 clean exit。
獨立 FC03 讀回兩輪 status 6（inhibited）、alarm 0、目前及目標 RPM 0；
Operator 確認已停止並退出鍵盤。pal_statistics 有 context-invalid shutdown 訊息，
程序仍正常結束，沒有據此宣稱所有 native shutdown 診斷已消除。

## 重啟重用

所有實機元件停止後，只重啟 IMU ROS node，不啟動 Control。
排除初始五秒，再取得 59.9908 秒、10,346 筆相同 stamp 的 raw／corrected 配對。
逐筆三軸 raw minus corrected 等於保存 bias（數值誤差 < 1e-12 rad/s），
frame 仍為 base_imu_link；沒有重新標定、修改均值或熱載入。
raw Z 均值 -0.000421274855、corrected Z 均值 +0.000014980866 rad/s。

這驗證 **ROS node 停止／重新 launch 的設定重用**，沒有重啟 Jetson 或 IMU 電源。
firmware cold-start 零偏、跨溫度與長期精度尚未驗證；需要時人工重新標定。


最後一輪在移除先前卡住的 pytest context、實機元件全部關閉後完成。
此前第三輪回歸有既有 passive LiDAR SIGINT shutdown 逾時：103 tests 中一項失敗；
單獨該測試三次通過，最後完整回歸也通過。**偶發逾時的根因仍 UNRESOLVED**，
不將清理與隨後通過當成因果證明，也沒有改 LiDAR runtime 或放寬該測試。
已保存失敗及成功 log；#50 的 IMU 修改與硬體驗收完成，不宣稱既有 native
shutdown 的所有時序／DDS 問題都已解決。

## 證據封存

`artifacts/imu-bias-calibration-20261008.tar.gz` 包含實測樣本、標定檔、native logs、
RED／GREEN／完整回歸與臨時唯讀驗證程序；SHA-256 `44519a4189d62fdca17cb5a67bc0c3650d8c63f0db28c35f9f9d0bead7d1e319`。
原始診斷 evidence 另保留，不以本次結果改寫歷史。

後續 [#51 LiDAR／launch 停止驗證](lidar-launch-shutdown-20261008.md) 已獨立定位並修正兩個停止根因；上述 #50 當時的 unresolved 記錄保留為歷史。原生 service response timeout 仍另列限制，不以停止修正宣稱一併解決。

# 核心套件驗收核對（2026-10-08）

對照 #35、#36、#37 的現行 acceptance criteria 與本次對話結果。
本次只整理既有證據，不啟動硬體、不新增驗收要求、不關閉 issue 或移除 dependencies。

## 已完成的近期結果

- 開發容器舊 image 缺少 libmodbus-dev；Dockerfile 原已有依賴。
  重建 image、更新容器後，乾淨與實際 workspace 的四套件建置均成功。
- `643e210`：Compose 加入 IMU／馬達 USB 映射與 serial 群組，IMU 預設設定與
  SIGINT 重複 shutdown 修正；Perception README 改為繁中。
- IMU 實機觀測約173 Hz、frame `base_imu_link`、診斷 OK，當下有效樣本1761、
  invalid_packets0。靜止 gyro 接近零、Z acceleration約9.73 m/s²。
  第二次啟動再次收到樣本，SIGINT 顯示 process finished cleanly。
  此為本次工具輸出觀測，未另封存原始長時間資料，不代表標定或精度驗收。
- Operator 回報 LiDAR 驗證無問題；先前確認完整模型／scan 方向正確。
  未提供本次 shutdown／失聯恢復結果，不能據此覆蓋原生 shutdown crash 紀錄。
- `9cebf81`：Description 與 Control 預設共用硬體設定，保持分別啟動；
  scripts/teleop.sh 僅執行原生鍵盤工具，不啟動模型／Control。
  軟體驗證41計數、0errors/failures/skips，包含CTest wrappers，不是41個實機試驗。
- Operator 回報 Control 靜止資料鏈「驗證OK」，以及架高鍵盤前進、後退、左右旋轉
  都正確。未提供原始輸出／尺度量測或此次每個停止情境，僅記錄其確認範圍。
- `3512fbc`：設定只保留 config/m1.yaml，更新兩個 launch、文件與測試；
  重建成功、10項相關軟體測試通過。保留 Operator 修改的 cmd_vel_timeout=3600秒、
  linear/angular limits=0.50，motor ceiling仍150RPM。
  舊0.3秒timeout與低速profile的測試證據不能直接驗收目前設定的timeout或速度範圍。
- `0a761f6`：reference/m1_parameters 收錄左右輪原始PELB與來源／hash，runtime不讀取。

## #35 — Control（仍 OPEN）

已支持：可重現入口、native responsibility split、有效速度／位置回授，
近期Operator確認的靜止資料鏈與四方向鍵盤操作；歷史有獨立停用／零RPM讀回、
inhibited狀態USB拔插故障診斷與軟體fault/timeout測試。

需核對／完成：

1. 現行 m1.yaml 的 timeout與速度參數已不同於歷史低速驗證，須明確決定適用操作設定，
   再驗證其原生timeout與結束／停用流程；不能把歷史0.3秒結果套到3600秒。
2. 最新手動入口的Teleop退出、Control正常停用與最終狀態需有適用證據。
3. 方向已確認，獨立位移／有效幾何尺度仍未標定；Operator已拒絕進一步精密地面角度確認，
   不自行重新要求該測試。硬體fault/失聯與現有軟體證據的適用性須逐項核對，
   不以即興拔除enabled drive來補證據。

韌體身分依先前Operator同意保留未知，不自行改成現在必須取得的阻擋條件。

## #36 — IMU（仍 OPEN）

已支持：重新設計adapter、標準ROS輸出與frame、協定／換算軟體測試、
實機資料鏈與正常關閉、native source diagnostics。裝置映射缺失時的真實
communication ERROR亦已觀測。

需核對／完成：實機受控旋轉的gyro方向／尺度與時間行為、適用的斷線／恢復操作證據。
Frame與模型安裝確認不等於独立wire-axis/scale驗證。
Bias/covariance標定仍保留後續責任；目前covariance全零表示未知，
不能直接宣稱可作正式EKF融合參數。先前限定commissioning EKF資料鏈的允許不代表標定完成。

## #37 — LiDAR（仍 OPEN）

已支持：雙獨立scan/source、LAST echo、正式FL_1/BR_1 frames、Operator模型／點雲確認、
原生QoS/network參數與近期正常使用確認。

明確未解決：原生SIGINT shutdown曾兩個children exit−6，FL pthread priority assertion、
BR system_error Invalid argument；root cause仍UNRESOLVED。
證據：dual-lidar-independent-live-20261007.md。Parent launch exit0不是children clean exit。
此外須核對來源故障辨識、timeout/reconnect與恢復的適用實機證據；正常scan不替代異常流程。
精密extrinsic calibration與long-run等責任維持既有範圍，不任意擴張本ticket。

## 下一步

先處理 #35 現行操作設定與驗收證據一致性，再完成可執行的前置缺口；
#37原生關閉故障仍是明確待診斷項目。#38仍受#35/#36阻擋，
不宣稱現在可以直接進入完整整合或移除dependencies。

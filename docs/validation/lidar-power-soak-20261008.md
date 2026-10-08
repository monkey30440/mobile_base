# #37：雙 LiDAR 電源循環與 15 分鐘觀察

本輪只完成 LiDAR 元件驗收，不啟動馬達、不修改 runtime、launch 或設定。
使用已驗證映像 `566d8ff74d6b`、Fast DDS、domain 196；隔離容器沒有 USB／馬達裝置映射。
Description 與 Perception 各自 launch，固定 TF 唯一 owner 為原生 RSP。

## 現場操作與恢復

Operator 只能同時切斷兩台 LiDAR 的共用電源，不能分別切電。
先取得雙來源 baseline，再由 Operator 回覆「已斷電」；兩路都停止更新，
原生日誌以 `[picoscan_fl-1]`／`[picoscan_br-2]` 前綴與 IP 表達 TCP 失聯／連線失敗／重連。
保持 Jetson 與網路設備供電，Operator 再回覆「已上電」。

兩個原生 driver 自動恢復，過程沒有重新 launch、重啟容器或 supervisor restart。
資料中斷間隔 FL 46.799 秒、BR 46.834 秒，包含人員切電時間，不是 boot-time 或 recovery SLA。
恢復後透過兩個原生 SOPAS ROS services 唯讀核對 serial：FL `25350157`、BR `25450354`。
此證據是一輪共用電源循環；逐台實體斷電隔離沒有驗證。
先前 [FL-only 資料流中斷測試](lidar-shutdown-fix-20261008.md) 已另行支持 BR 不受該來源 timeout 影響。

## 15 分鐘有界觀察

上電恢復後連續觀察 900 秒；以下統計排除開始 5 秒，涵蓋約 895 秒穩定窗口。
這是本輪觀測結果，不新增 V1 數值驗收要求。

| 項目 | 前左 FL | 右後 BR |
|---|---:|---:|
| 穩定窗口 scan 數 | 22,376 | 22,378 |
| 接收頻率 | 25.001 Hz | 25.003 Hz |
| 最大接收間隔 | 45.7 ms | 57.6 ms |
| 觀察到的 message age | 48.5–73.4 ms | 47.1–71.3 ms |
| 時間戳倒退 | 0 | 0 |
| scan timestamp 可取得模型 TF | 22,376／22,376 | 22,378／22,378 |
| scan frame | `base_lidar_link_FL_1` | `base_lidar_link_BR_1` |

每筆穩定窗口 scan 都有有效 range；沒有穩定期 native ERROR／FATAL，沒有意外程序退出。
結束時只向 launch parent 發送 SIGINT，由 native launch 處理 children 停止；
兩個 children 均 `process has finished cleanly`，Perception／Description parent exit 0。
停止後只剩隔離容器 sleep；保存 evidence 後移除該臨時容器。

## #37 acceptance 對照

1. **雙獨立 scan／frames／geometry evidence**：兩路 native LAST／獨立 scan 未改，
   本輪 TF 與 frame 完整；重用 [Operator 已確認模型／座標系／點雲](v1-flow-recovery-20261007.md) 的靜止驗收。
   不把該確認提升為精密外參標定。
2. **Network／association／namespace／QoS／timestamp**：已提供設定、child argv、實機 capture、
   source serial readback，見 [修正验收](lidar-shutdown-fix-20261008.md) 與本輪原始資料。
3. **Native fault attribution／timeout／reconnect／CRC／parse logs**：FL-only timeout 與此次真實斷電恢復已驗證。
   CRC／parse 日誌能力是固定上游 source evidence：
   [CRC mismatch warning 與 message drop](https://github.com/SICKAG/sick_scan_xd/blob/a562c5d098de21f6284359f4dfea97e93bd2b4d5/driver/src/sick_scansegment_xd/udp_receiver.cpp#L300)、
   [compact／msgpack parse failure](https://github.com/SICKAG/sick_scan_xd/blob/a562c5d098de21f6284359f4dfea97e93bd2b4d5/driver/src/sick_scansegment_xd/msgpack_converter.cpp#L175)。
   launch 的來源 process prefix 保留原生日誌；不新增 generic diagnosed-publisher frequency／timestamp coverage。
   本輪沒有注入損壞封包，不宣稱實機 CRC fault injection 已通過。
4. **獨立來源操作／辨識／失聯排查與 evidence**：公開 Perception entry、來源 identity、
   source-specific 原生失聯原因、software regressions、實機恢復及正常退出均有可追溯證據。
   scan header 不等於 TF publisher，TF 仍由獨立 Description 提供。

因此 #37 的有界 LiDAR 元件交付可完成；精密外參／時間同步標定、長期 drift、量產耐久性、
catch／C API／其他 upstream 執行路徑仍未完整驗證，不當作本 ticket 新增阻擋條件。
15 分鐘不能稱 production long-run；本 ticket 完成不等於 #38、完整 V1 或 Feature Freeze 已驗收。

## Evidence 與 review

[原始資料／logs／觀測與分析腳本／provenance／Operator 操作記錄](artifacts/lidar-power-soak-20261008.tar.gz)。
SHA256：`3d4636135ae9dc3bb273488c512d1a16fd47cbbd1ccee9579d2931a00c0842c9`。
SOPAS access token 已遮蔽；分析只處理 raw capture，不提供產品 runtime monitoring。

### Standards

新增 evidence／文件 review：0 項硬性違規、0 項新增 smell findings。
原始數據、artifact hash、操作範圍及 historical/current 描述一致，沒有阻擋 commit 或元件驗收的項目。

### Spec

0 項 remaining findings；四項 acceptance 皆有相應 evidence，沒有 #37 closure blocker。
保留上述 calibration／量產可靠性／其他執行路徑限制，不擴大本輪驗收。

Review 合計：Standards 0／Spec 0；兩軸均無阻擋項目。

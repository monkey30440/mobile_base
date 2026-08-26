# SYS-003 LiDAR Perception — Minimal Reuse Research

## Scope

本筆記只評估 `SYS-003`：「系統應提供 LiDAR 掃描資料供建圖、定位與導航使用。」

同時窄幅盤點 ROS 2 Jazzy 可用的 LaserScan merge 候選。Merge 並非 SYS-003 的必要前提；本筆記不選演算法、不定 merged output interface，也不改變 independent-source-first 原則。

## Requirement Fragments

1. 系統能從配置的 LiDAR 取得平面掃描量測。
2. 掃描使用 ROS 2 生態系可交換的資料表示，並帶有時間、座標系與量測範圍語意。
3. 前、後 LiDAR 可保留各自的 source identity，供建圖、定位與導航的 downstream design 使用。
4. 實際資料品質、TF、QoS、時序與有效性足以支援各 downstream operation。

## Primary Candidate: `sick_scan_xd` + `sensor_msgs/msg/LaserScan`

| Field | Assessment |
|---|---|
| Candidate Mature Solution | SICK `sick_scan_xd` driver，分別發布每具 picoScan 的 `sensor_msgs/msg/LaserScan` |
| Exact Version / Platform | 本地參考版本 `sick_scan_xd` 3.9.0，revision `a562c5d098de21f6284359f4dfea97e93bd2b4d5`；目標平台 ROS 2 Jazzy / Ubuntu 24.04 |
| Coverage Status | `Fully Covered` at mature-solution capability level |
| Covered Scope | Driver 支援 picoScan100/picoScan150、ROS 2 啟動、LaserScan 發布，以及多裝置使用不同 IP、UDP port、node、topic 與 frame identity；LaserScan 標準訊息承載 timestamp、frame、角度、距離、量測時間與 intensity |
| Known Constraints | 每具裝置需獨立網路與 ROS identity；picoScan full-frame、layer/echo、frame suffix、UDP packet loss 與 scan validity 必須依配置及實機行為確認 |
| Uncovered Gap | `None` for scan-production behavior；專案配置與 downstream integration 尚未 closure |
| Missing Evidence | Jazzy target image 中實際採用的 driver artifact/revision、兩具實機同時運行、topic/frame/QoS、量測有效性、TF 與 Mapping/Localization/Navigation integration |

### Evidence

- ROS 2 Jazzy 的 [`sensor_msgs/msg/LaserScan`](https://docs.ros.org/en/jazzy/p/sensor_msgs/msg/LaserScan.html) 定義單一平面雷射掃描，包含 header/frame、角度範圍與增量、量測時間、有效距離、ranges 與 intensities。這支持 fragment 2，但不證明本專案 driver 或 downstream integration 已成立。
- SICK 官方 [`sick_scan_xd`](https://github.com/SICKAG/sick_scan_xd) 說明 ROS 2、picoScan100/picoScan150、LaserScan，以及同時執行多具 picoScan 時必須使用不同 IP、UDP ports、node names、topics 與 frame IDs。這支持 fragments 1 與 3，但不證明本專案實機品質及 consumers 已整合。
- 本地 `ref/sick_scan_xd/package.xml` 記錄版本 3.9.0；`launch/sick_picoscan.launch` 與 `.launch.py` 提供 picoScan ROS 2 啟動、full-frame/segment LaserScan topic、frame 與 layer filter 設定。本地副本只能證明候選 source/configuration 存在，不能取代 build、runtime 或實機證據。

### Gap Classification

- `Configuration Gap`：兩具 LiDAR 的 IP、UDP port、node、topic、frame、echo/layer 與 QoS 設定。
- `Evidence Gap`：Jazzy build/install、雙裝置 runtime、received-message、TF/semantic、downstream integration 與實機有效性。
- `Custom Behavior Gap`：`None`，目前沒有證據顯示 SYS-003 需要自製 scan driver 或自製 perception framework。

## Narrow LaserScan Merge Candidate Inventory

### Confirmed Jazzy Candidate

ROS 2 Jazzy 已有 released binary 候選 [`dual_laser_merger` 0.3.1](https://docs.ros.org/en/ros2_packages/jazzy/api/dual_laser_merger/)。其 Jazzy API/source 顯示使用兩個 `LaserScan` inputs、approximate-time synchronization、TF、`laser_geometry`/PointCloud2/PCL 處理，再產生合併資料。

適用前提與限制：

- downstream consumer 確實只接受一個 scan，且單一來源不足；
- 兩個來源具有正確 TF、可接受的時間差與相容 QoS；
- 需實測轉換、同步、遮蔽、重疊角度取值、輸出解析度與額外 latency；
- PCL/PointCloud2 中介處理會增加 dependency 與資源成本；
- 套件存在且有 Jazzy binary，不等於已適合本 AMR 的對角安裝、掃描幾何與下游 consumers。

### Decision Boundary at Research Time

- 現階段只記錄 `dual_laser_merger` 為可評估候選，不核准選用。
- 不把 ROS 1 `ira_laser_tools` 視為 Jazzy baseline；ROS Index 的主要條目是 ROS 1-era implementation，不能直接證明 ROS 2 Jazzy 可用。
- 只有 downstream requirement 與 integration evidence 證明需要單一融合 scan 時，才啟動正式選型。
- 選型時仍須比較 consumer 原生多來源能力、同步/遮蔽語意、CPU/latency、failure isolation 與 real-hardware results。

## Architecture Considerations

- 05 應保留每具 LiDAR 的 source identity、frame、validity 與唯一 software ownership。
- Mapping、Localization 與 Navigation 是否能直接訂閱多個 independent sources，必須逐 consumer 查證，不能由 SYS-003 預先假設。
- Scan production 的成熟能力已存在；`Fully Covered` 不代表 project integration 或 real-hardware validation 已完成。
- LaserScan merge 選型是條件式待辦，不是 v0.1 預設資料路徑。

## MVP Change Candidate

`None`。目前不需要簡化 SYS-003；先使用成熟 driver 提供 independent scans，若 downstream 真的需要單一輸入，再評估 merge。

## Concise Conclusion

`SYS-003` 可判定為成熟方案能力層級的 `Fully Covered`：`sick_scan_xd` 3.9.0 候選可為兩具 picoScan 分別提供標準 `LaserScan`。剩餘問題屬 configuration、integration 與 real-hardware evidence gaps，不是 custom behavior gap。研究當時僅將 Jazzy `dual_laser_merger` 0.3.1 列為候選。

## Subsequent Approved Decision

SYS-005 後續確認 RF2O 使用 merged `LaserScan`，並核准 ROS 2 Jazzy `dual_laser_merger` 0.3.1 作為 merge 套件。兩個原始 scans 仍保留；同步、TF、QoS、重採樣、遮蔽、latency、dropout 與實機 evidence 尚待 closure。
> Historical research note: RF2O references describe the superseded candidate baseline. Current Kinematic-ICP consumes `/scan_front`; merged `/scan` remains for perception consumers.

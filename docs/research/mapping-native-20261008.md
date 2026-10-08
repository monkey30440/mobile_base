# V1 Mapping 原生能力研究

日期：2026-10-08。範圍僅 #39 的 Mapping；不新增導航、route graph 或自動地圖品質檢查。

## 版本與證據

容器已安裝 `slam_toolbox 2.8.5`、`nav2_map_server 1.3.13`（ROS 2 Jazzy）。本研究使用官方對應 tags；slam_toolbox tag commit 為 `ec8f7635dea317b531c419f798f87d90a336f32e`（本次 `git ls-remote` 核對）。[slam_toolbox 2.8.5](https://github.com/SteveMacenski/slam_toolbox/tree/2.8.5)、[Nav2 1.3.13](https://github.com/ros-navigation/navigation2/tree/1.3.13)。

## 啟動與責任：CONFIRMED

原生 `online_async_launch.py` 啟動 `async_slam_toolbox_node` LifecycleNode；`autostart=true`、`use_lifecycle_manager=false` 時原生事件執行 configure／activate。因此套件只需包含原生 launch、提供參數，不需要自行撰寫 lifecycle runtime。原生 launch 的 `use_sim_time` 預設為 true，實機必須覆寫 false。[原生 launch](https://github.com/SteveMacenski/slam_toolbox/blob/2.8.5/launch/online_async_launch.py)

原生 source 已宣告主要 defaults：`odom`、`map`、`base_footprint`、解析度 0.05 m、Ceres solver、scan queue 1、`use_map_saver=true`、`enable_interactive_mode=false`。`scan_topic` 預設 `/scan`，本平台需明定 `/lidar/fl/scan`。native sensor-data QoS 收 scan，不需要 scan merge／relay。模型 sensor TF 與 odometry TF 是必要輸入，Mapping 中 slam_toolbox 負責 `map → odom`；activate 成功本身不能证明感測資料及 TF 正常。[參數、scan filter、map→odom](https://github.com/SteveMacenski/slam_toolbox/blob/2.8.5/src/slam_toolbox_common.cpp)

可使用小型 project YAML 明確宣告 V1 frames／scan／mapping mode，其他 tuning 使用已選版本原生 defaults。若選 upstream 範例起始值，例如 map update 5 秒，應記錄它是可調整起始設定；原生程式 default map update 是 10 秒，不能假定範例與 default 完全相同。[原生範例](https://github.com/SteveMacenski/slam_toolbox/blob/2.8.5/config/mapper_params_online_async.yaml)、[原生程式](https://github.com/SteveMacenski/slam_toolbox/blob/2.8.5/src/slam_toolbox_common.cpp)

## 倒裝前左 LiDAR：CONFIRMED 非對稱 scan 的原生 gap

`LaserAssistant::isInverted` 由 base／scan frame TF 判斷 scan 軸是否倒裝，取得 mounting yaw；`makeLaser` 使用感測器 translation 與 yaw 建立 Karto offset。mapping 主路徑 `getLocalizedRangeScan` 呼叫 `scanToReadings`，倒裝時以 reverse iterators 反轉 ranges。URDF roll π、yaw π/4 必須保留真實 geometry。**但這只能證明 ranges 反轉，不能證明非對稱角度範圍正確。**[LaserAssistant](https://github.com/SteveMacenski/slam_toolbox/blob/2.8.5/src/laser_utils.cpp)、[主路徑](https://github.com/SteveMacenski/slam_toolbox/blob/2.8.5/src/slam_toolbox_common.cpp)、[scanToReadings](https://github.com/SteveMacenski/slam_toolbox/blob/2.8.5/include/slam_toolbox/laser_utils.hpp)

另外 `LaserMetadata::invertScan` 在此 tag 使用首項 `ranges[size]` 的可疑迴圈；它由 `ScanHolder::getCorrectedScan` 使用，**不是上述 Mapping 主路徑**。V1 不需要互動 scan editing，保留原生 `enable_interactive_mode=false`；不因無關工具路徑加入 project-owned patch。[互動工具相關函式](https://github.com/SteveMacenski/slam_toolbox/blob/2.8.5/src/laser_utils.cpp)

### 實機非對稱角度所揭露的問題

實際 FL scan：`angle_min=-2.40862894`、`angle_max=2.82301044`、increment 約 `.0043633357`、1200 samples。`makeLaser` 保留原始 angle_min／angle_max，`scanToReadings` 倒裝只反轉 ranges。物理 roll π 后正確有效 bounds 應是 `[-angle_max,-angle_min]`，而不是原始 bounds；目前角度偏差為兩端相加 `.4143815 rad`，約 `23.742°`。因此不能將先前對稱合成 fixture 的通過推論成這台 AMR 已正確。官方 Jazzy 分支檢視仍具有相同 makeLaser 行為。[2.8.5 source](https://github.com/SteveMacenski/slam_toolbox/blob/2.8.5/src/laser_utils.cpp)、[Jazzy source](https://github.com/SteveMacenski/slam_toolbox/blob/jazzy/src/laser_utils.cpp)

SICK 3.9.0 原生 `host_LFPangleRangeFilter` 與 `host_set_LFPangleRangeFilter` 可設定裝置 azimuth sector；這是候選 native 設定途徑，**但需證明實際輸出的離散 sample bounds 對稱、其取樣網格可表示零中心，不能只因指定對稱度數就宣稱解決**。原生 publisher angle_min／max 直接取排序點的首末 azimuth，非套用理想設定邊界。[SICK launch](https://github.com/SICKAG/sick_scan_xd/blob/3.9.0/launch/sick_picoscan.launch)、[publisher](https://github.com/SICKAG/sick_scan_xd/blob/3.9.0/driver/src/sick_scansegment_xd/ros_msgpack_publisher.cpp)

不得修改真實 mounting yaw 來掩蓋 SLAM 偏差，那會破壞其他使用真實 scan TF 的系統。若 native 實際對稱輸出無法滿足，則應明確記錄 native gap、研究 upstream 修正，不能以 runtime 自動補角當已確認架構。

原生設計存在不代表實機品質已驗證。實際安裝角、scan angle bounds／samples、時間戳與 odometry 都影響結果，必須以真实 scan 在 `map` frame 的靜止／移動／重訪對齊驗收。

## 保存 map.pgm／map.yaml：CONFIRMED

直接使用原生 CLI：

```bash
ros2 run nav2_map_server map_saver_cli -t /map -f <已建立目錄>/map --fmt pgm
```

`-f` 是不含副檔名的輸出 prefix，`--fmt pgm` 明確指定圖片格式。預設 trinary 由 native map I/O 輸出 `.pgm` 與 `.yaml`；YAML image 使用圖片 basename。Operator 負責選定／建立可寫目錄；CLI 沒有建立 dataset 目錄的責任。[CLI 參數及 exit code](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_map_server/src/map_saver/main_cli.cpp)、[原生保存](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_map_server/src/map_io.cpp)

CLI 正常成功 exit 0，正常 save failure exit 1，參數或 exception 錯誤回傳 -1（shell 常呈現 255），保留原生原因日誌。MapSaver 預設 transient-local subscription=true、接收 timeout 2 秒；無可接收 map、不可寫圖片等原生失敗不可視為保存完成。不要新增 shell saving wrapper 或每次保存後品質檢查。[CLI](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_map_server/src/map_saver/main_cli.cpp)、[MapSaver](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_map_server/src/map_saver/map_saver.cpp)

替代原生 `/slam_toolbox/save_map` service 亦可用：request `std_msgs/String name`，result 0 success、1 no map received、255 undefined failure。其實作呼叫上述 CLI 並判斷程序結果；因 name 被組入 shell 命令，直接 CLI 比透過 service 更直接地處理 Operator 路徑。[service 定義](https://github.com/SteveMacenski/slam_toolbox/blob/2.8.5/srv/SaveMap.srv)、[service 實作](https://github.com/SteveMacenski/slam_toolbox/blob/2.8.5/src/map_saver.cpp)

原生保存不是 transaction／原子二檔提交協定；map I/O 的 metadata stream 也沒有完整 filesystem durability 承諾。V1 沒有提出這類 contract，因此不額外設計 manifest／rollback／內容驗證。不得把 CLI 的成功宣稱為電源中斷耐久性保證。[map I/O](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_map_server/src/map_io.cpp)

同一原生 map I/O 以三位小數保存 resolution 與 origin X/Y。因此重載驗收
不應要求任意 double origin bitwise 相等；在已選 0.05 m resolution 下，
resolution 可重用，origin X/Y 的每軸差異應不超過原生四捨五入的 0.5 mm。
這是已選原生檔案格式的精度，不是新的實體建圖誤差門檻或校正保證。
實機本次兩軸差異約 0.136／0.220 mm、occupancy 一致，無新增 map I/O patch。
[native to_string_with_precision](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_map_server/src/map_io.cpp)。

## 軟體與實機驗證邊界

- **Software-only verification**：以真實 URDF TF（含 roll π／yaw π/4）加上已知房間的合成 LaserScan／odom TF，啟動正式 Mapping entry；觀察 lifecycle active、`/map`、`map→odom`，檢查已知牆面與轉到 map frame 的 scan endpoints 相符。此為測試 fixture，不是 runtime fake sensor／fake odometry。
- **Software-only verification**：原生 CLI 保存固定二檔、無 map 或不可寫輸出報錯；再用 native map_server 載入保存 YAML，以 native trinary 語意核對 map geometry／occupancy（不可假定任意中間機率原樣 round-trip）。[原生 map I/O 的讀寫模式](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_map_server/src/map_io.cpp)
- **REQUIRES HARDWARE VALIDATION**：Foxglove 同一 `map` frame 顯示實際 `/lidar/fl/scan` 與 `/map`；静止、移動／旋轉、重訪已建區域，確認沒有持續明顯偏移或雙牆，保存／驗收重載結果與現場一致。重載是開發驗收，不是每次 Operator 保存 workflow 的新增檢查。
- **REQUIRES CALIBRATION**：輪距／輪徑、IMU bias／covariance 與量化定位／建圖誤差。既有 commissioning 證據不能取代標定；本輪不杜撰產品誤差門檻。

## 結論

已確認 native async lifecycle 與原生保存／載入能力；但 **倒裝且非對稱 scan 的角度處理存在 confirmed gap**，必須先解決才能宣稱 Mapping 符合 V1。`mobile_base_mapping` 最小 responsibility 為原生 launch composition 與平台 config／操作文件；目前只在 `/tmp` 驗證原生 metadata 修正候選，未修改正式部署。原生 SICK 對稱 sector 會改變裝置輸出與FOV，且實際離散邊界仍需硬體確認；不因避開SLAM缺陷而直接變更已確認的感測器／TF契約。正式補足方式待候選驗證與decision/spec reconciliation。實機 map／scan 對齊與地圖品質仍須以硬體證據完成 #39，不能僅以 lifecycle active 或合成 fixture 宣稱通過。

## 候選最小補足的software proof — 2026-10-08

Confirmed gap限定為原生LaserAssistant倒裝metadata的角度bounds，
不是SLAM演算法、真實modelTF或原生sensorpublisher的ownership。
在/tmp固定2.8.5source只將倒裝local metadata bounds反轉，已通過
真實scan角度的公開ROS建圖／對齊／native保存重載fixture；
詳見[validation](../validation/mapping-package-20261008.md)。
候選沒有新增runtime node、不修改rawscan或真實TF、不縮減FOV。
是否以可重現Dockersource overlay正式交付需decision/spec reconciliation；
目前apt版本與正式Docker均未修改，實機重驗仍待完成。

## 已採用的正式補足 — 2026-10-08

Operator採用固定官方2.8.5source＋最小倒裝bounds修正，Docker可重現建置overlay；
[decision supplement](https://github.com/monkey30440/mobile_base/issues/23#issuecomment-6054136081)。
前段候選狀態是當時software proof，正式實作以本次已採用修訂為準。
Requirement為真實前左scan與map對齊，upstream gap及minimal責任限於
倒裝metadata bounds；不新增Mapping演算法、node、fake TF或感測器視野变更。
sourcecommit與patchhash記錄，正式入口、native保存／重載及現場對齊仍須驗收。

## 後續發現：LaserScan range metadata（CONFIRMED gap）

SICK 3.9.0 `convertPointsToLaserscanMsg` 將 `range_min`／`range_max` 設為該幀所有 ranges 的 extrema，最後減／加 1 mm，minimum 另限制至少 0.05 m。它們因此隨環境改變，而不是 sensor measurement bounds。[publisher source](https://github.com/SICKAG/sick_scan_xd/blob/3.9.0/driver/src/sick_scansegment_xd/ros_msgpack_publisher.cpp)

slam_toolbox `getLaser` 僅第一次遇到該 frame 建立 metadata；`makeLaser` 把首幀 min/max 存入 Karto，並將 `max_laser_range` 上限截至首幀 maximum。Karto scan matching filtered points 排除 cached bounds 以外資料，occupancy `AddScan` 對 `rangeReading <= minRange` 或 `>= maxRange` 直接忽略。因此「25 m 超過 LiDAR 6.8 m」不是可忽略 warning：後續較遠牆面確實不能成為正常有效點，較近點也可能被首幀 minimum 排除。[metadata cache](https://github.com/SteveMacenski/slam_toolbox/blob/2.8.5/src/slam_toolbox_common.cpp)、[metadata creation](https://github.com/SteveMacenski/slam_toolbox/blob/2.8.5/src/laser_utils.cpp)、[Karto Update／AddScan](https://github.com/SteveMacenski/slam_toolbox/blob/2.8.5/lib/karto_sdk/include/karto_sdk/Karto.h)

### 原生升級／參數研究

2026-10-08 官方 GitHub `releases/latest` 回報 stable 仍為 3.9.0（2026-03-17）；master publisher 亦保留上述 extrema 行為，沒有已確認可透過 stable 升級取得正確固定 metadata 的證據。[latest stable](https://github.com/SICKAG/sick_scan_xd/releases/tag/3.9.0)、[master publisher](https://github.com/SICKAG/sick_scan_xd/blob/master/driver/src/sick_scansegment_xd/ros_msgpack_publisher.cpp)

原生 `host_LFPangleRangeFilter` 是角度／beam reduction，不是距離 metadata；custom pointcloud `rangeFilter` 操作輸出點資料，不能使 LaserScan metadata 正確固定。3.9.0 config／launch 未提供可覆寫這條 publisher LaserScan range capability 的原生參數。[config](https://github.com/SICKAG/sick_scan_xd/blob/3.9.0/driver/src/sick_scansegment_xd/config.cpp)、[launch](https://github.com/SICKAG/sick_scan_xd/blob/3.9.0/launch/sick_picoscan.launch)

官方 operating instructions 有裝置 `sWN LFPradialDistanceRangeFilter`，此為輸出距離篩選（enable／DistMin／DistMax，允許設定值到 200000 mm），**不是實際 sensor 最大能力的回報**。即使啟用，publisher 仍取觀測 extrema，不會自然改成 filter endpoints，故不構成此 gap 的原生解決。不要以讀回 filter 最大設定 200 m 當 measurement capability。[SICK operating instructions §13.6.1.4.6.11](https://www.sick.com/media/docs/1/91/691/operating_instructions_picoscan150_2d_lidar_sensors_en_im0106691.pdf)

### 官方硬體界線與識別：range choice 尚 UNRESOLVED

本次下載官方文件實際為 `8028323/1XQ7/2026-09-17`，§11.1 表述工作範圍：Core 0.05–25 m、Prime 0.05–60 m、Pro 0.05–120 m。反射率、ambient light、sensing profile 的 typical scanning range 是另一个概念，不能將宣傳的 75 m 作為所有 picoScan150 的固定 maximum。[官方 operating instructions §11.1](https://www.sick.com/media/docs/1/91/691/operating_instructions_picoscan150_2d_lidar_sensors_en_im0106691.pdf)

官方可用唯讀命令：`sRN OrdNum`（order／part number）、`sRN SerialNumber`、`sRN DeviceIdent`（firmware designation/version）、`sRN DItype`（device family/type）、`sRN LMPscancfg`（scan rate／angular resolution／start-stop angle）。文件示例 `OrdNum=1134610` 是 **picoScan150 Pro-1 範例**，不能當現場 part number。現場既有 Mapping startup log 未包含足以辨別 Core／Prime／Pro 的 OrdNum，故硬體 variant／相對應 maximum 仍需 readback 證據。本研究未找到官方直接回報物理 range capability 的 SOPAS 命令；不能把「未找到」寫成完全不存在。[官方 instructions §13.6.1.4.9.1、.7–.9、§13.6.1.4.3.1](https://www.sick.com/media/docs/1/91/691/operating_instructions_picoscan150_2d_lidar_sensors_en_im0106691.pdf)

最小責任仍應放在 producer：讓 LaserScan `range_min/max` 表達所選硬體及已確認有效輸出範圍，不要讓 SLAM 依這次房間大小猜 sensor capability。沒有原生參數可完整補足的證據；若採 upstream source 修正，應以實際型號／官方 bounds 支持，測試不同場景 consecutive scans metadata 穩定與後续有效近遠點可被使用。此研究不修改 runtime，也不以亂填 ranges／假的 far hit 來強迫 metadata。

### 現場識別與已採用補足：CONFIRMED

兩台實機唯讀 `OrdNum` 都回報 `1134608`，`DeviceIdent` 為 picoScan 2.1.0.0R；
這解除前段 variant／range choice 的 UNRESOLVED 狀態。
[官方 PICS150-01000 Core-1 datasheet](https://www.sick.com/media/pdf/1/81/581/dataSheet_PICS150-01000-Core-1_1134608_en.pdf)
對應工作範圍 0.05–25 m。這是 capability metadata，不宣稱現場 25 m 精度已驗收。

Operator 已採用既有固定 SICK source overlay 的最小補足，並已補入
[decision22](https://github.com/monkey30440/mobile_base/issues/22#issuecomment-6054423656)／spec32。
`laserscan_range_min/max` 預設 0/0 停用；平台明確配置 0.05/25，
不把所有 picoScan 型號硬編碼為 Core。Config 驗證有限、合法且可表示的 float32
上下限；原生 producer 僅覆寫 metadata，實際 ranges、角度、frame、時間戳保持。
不存在新的 relay、點雲處理或 SLAM 演算法 owner。
詳見 [驗證紀錄](../validation/mapping-package-20261008.md)。

### 純旋轉建圖的原生 scan gate：CONFIRMED

固定 2.8.5 的 `shouldProcessScan` 在預設
`check_min_dist_and_heading_precisely=false` 時，以平移距離先排除 scan；
因此不能以只旋轉的新視角直接證明 range 修正的效果。
原生已有 `true` 配置，可在 `minimum_travel_distance` **或**
`minimum_travel_heading` 足夠時處理新 scan。平台選用此原生參數，
其餘門檻沿用 native commissioning defaults，不新增 source 修正。
[官方參數說明](https://github.com/SteveMacenski/slam_toolbox/blob/2.8.5/README.md#configuration)、
[原生 shouldProcessScan](https://github.com/SteveMacenski/slam_toolbox/blob/2.8.5/src/slam_toolbox_common.cpp)。

原生 occupancy grid 另有最小穿越證據數要求，單一新視角不等於已成為 occupied cell；
software fixture 使用連續、重疊的旋轉視角，而非瞬間跳轉或放寬對齊門檻。
同一 native gate／相同幾何，當幀 extrema metadata 的較遠點對齊比例 0，
固定 capability bounds 後比例 1.0，才是本次 range gap 的可區分 differential proof。

### 型號已讀回後的最小 producer 補足候選

現場兩台唯讀 `OrdNum=1134608`、`DeviceIdent=picoScan 2.1.0.0R`；此為本輪 root 收集的硬體證據，應於驗收 archive 保存原始 response。對應官方 `PICS150-01000 Core-1` part 1134608 datasheet 明列工作範圍 0.05–25 m。該目前下載 datasheet 頁首產品家族寫 picoScan100，而型號／part 與現場對應；文件命名差異應保留，不可擅自將現場 firmware identification 改成另一型號。[官方 part-specific datasheet](https://www.sick.com/media/pdf/1/81/581/dataSheet_PICS150-01000-Core-1_1134608_en.pdf)

完整已取得上游 source cache 是 `/tmp/mobile-base-sick-upstream`（git describe：3.9.0）。修正候選在 **原生 producer source** 增加明確 metadata bounds 的 optional configuration，並由已確認 Core-1 平台 profile 提供 0.05／25；不新增 relay／scan transformation，不修改實際 ranges。以下不是已有 upstream 參數，而是需要正式採用／驗證的最小 upstream 修改 seam：

- `include/sick_scansegment_xd/config.h`：兩個 optional metadata fields。
- `driver/src/sick_scansegment_xd/config.cpp`：讀取／驗證這對新參數、預設 disabled；若對 cli overrides 開放，也須涵蓋其現有 optional-argument parsing。
- `include/sick_scansegment_xd/ros_msgpack_publisher.h` 與 `driver/src/sick_scansegment_xd/ros_msgpack_publisher.cpp`：constructor 接收 config；在每份 LaserScan 完成時，以已確認 bounds 覆寫 metadata，保留 ranges／angle／echo／frame／timestamps。
- `launch/sick_picoscan.launch`／平台 LiDAR profile：明確提供此平台 bounds；不得以 `scanner_type == picoScan` 就一律 hardcode 25 m，否則 Prime／Pro 會被錯誤限制。

可命名為 `laserscan_range_min/max`，但名稱是後續 implementation choice，研究不視其為已存在 native option。未選用 metadata override 的 generic multiScan 使用者保留其目前行為，避免在同一差異內猜測其他裝置能力。

### 軟體 native verification 候選

原生 `RosMsgpackPublisher` 公開 `HandleMsgPackData(ScanSegmentParserOutput)`、`SetActive(true)`，能建立小型 C++ fixture 餵解析後的合成 segments，再透過真實 ROS LaserScan subscription 檢查結果；不需替換 converter、mock publisher 或僅測私有函式。兩組近／遠房間資料與 zero／invalid samples 均應保留原始 ranges，metadata 穩定；未配置 override 的 generic profile 必須維持原行為。接著以原生 SLAM 驗首幀較近、後續較遠牆能正常進入 map，驗收 real output correctness，而非只移除 warning。[public publisher seam](https://github.com/SICKAG/sick_scan_xd/blob/3.9.0/include/sick_scansegment_xd/ros_msgpack_publisher.h)、[parser output structure](https://github.com/SICKAG/sick_scan_xd/blob/3.9.0/include/sick_scansegment_xd/scansegment_parser_output.h)

上游另有正式 emulator 流程 `test/scripts/run_linux_ros2_simu_picoscan_reconnect.bash`：SOPAS test server + UDP pcap player + native driver。其依賴的 pcap 不在本次 source cache（scandata 只有 dummy），因此不可宣稱此 emulator 已完成；可取得官方 fixtures 或現場 captured UDP 後執行。不得直接跑上游 script 中廣域 killall 或刪除 ROS logs，應在 isolated domain／ports 選擇必要元件。[上游 emulator 流程](https://github.com/SICKAG/sick_scan_xd/blob/3.9.0/test/scripts/run_linux_ros2_simu_picoscan_reconnect.bash)

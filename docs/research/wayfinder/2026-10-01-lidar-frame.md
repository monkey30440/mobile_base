# 倒裝 LiDAR：native frame、scan 順序與時間語義

研究日期：2026-10-01。對應 [查明倒裝 LiDAR 的 native frame 與 scan 時間處理](https://github.com/monkey30440/mobile_base/issues/17)，供 [robot model、感測與本地狀態估計決策](https://github.com/monkey30440/mobile_base/issues/6) 使用。範圍依 [Wayfinder Notes](https://github.com/monkey30440/mobile_base/issues/1)；本文件只有公開 source 與套件 metadata，不包含 private Xacro、mesh、device dumps 或其 hashes。

## 結論

**對平面、倒裝、對稱完整掃描的 picoScan profile，已有原生消費路徑，沒有證據顯示必須保留共用 `scan_handedness_normalizer`。** 真實右手 sensor frame 的安裝旋轉可由 TF 表達；AMCL 明確支援 upside-down，SLAM Toolbox 2.8.5 會依 TF 判斷倒裝並內部反轉 readings，laser_geometry／costmap／box filter 使用三維 TF。[REP-103][rep]、[AMCL][amcl]、[SLAM inversion][slamlaser]、[SLAM readings][slamread]、[laser_geometry][geometry]

此結論的條件是：`LaserScan.header.frame_id` 真正描述原始量測座標；scan 為正向有序、角度範圍關於零對稱的完整平面掃描；TF、scan metadata 與時間來源一致。它支持後續決策移除 redundant reflection，**不等於現在只刪掉 node 就正確**。現行 normalizer 保持 frame ID 並反射量測，相關 frame／pipeline 必須在後續實作一致收斂。[current normalizer][normalizer]、[current launch][launch]

**兩個獨立限制不能被「native 支援倒裝」掩蓋：** SLAM Toolbox 2.8.5 的反轉路徑不是任意非對稱裁切的通用解；native 支援 TF 也不等於每個 consumer 都對移動中的 scan 做逐束 deskew。actual mounting、axis、profile 及 acquisition timing 仍需後續 V2/V3 證據。[SLAM][slamlaser]、[AMCL][amcl]、[costmap][obstacle]

## 1. 核對版本與 provenance

Repository source 基點為 `8d17bdb6239702d8e7ec9a2cd170b696a6045bef`。重用本 session 已唯讀取得的 stopped dev／existing release image `/var/lib/dpkg/status`，沒有另啟動產品或硬體。metadata 來源及 image 身分記錄見 [native motion inventory](https://github.com/monkey30440/mobile_base/blob/0519298d8f95b7671708c78fbaf16358be623e96/docs/research/wayfinder/2026-10-01-native-motion.md)。相關原始欄位如下：

| 套件 | release Debian version | stopped dev Debian version |
|---|---|---|
| `nav2-amcl` | `1.3.12-1noble.20260614.075224` | `1.3.13-1noble.20260902.211420` |
| `nav2-costmap-2d` | `1.3.12-1noble.20260614.075323` | `1.3.13-1noble.20260903.003455` |
| `slam-toolbox` | `2.8.5-1noble.20260614.104642` | `2.8.5-1noble.20260907.044142` |
| `laser-geometry` | `2.7.2-1noble.20260612.100954` | `2.7.2-1noble.20260903.003154` |
| `sick-scan-xd` | `3.9.0-1noble.20260614.055630` | `3.9.0-1noble.20260902.160847` |
| `laser-filters` | dpkg inventory 無此 package record | dpkg inventory 無此 package record |

套件名稱均有 `ros-jazzy-` 前綴、architecture 為 arm64。這是既有 image/container metadata，不保證機器人選用的 runtime 或 overlay。Dockerfile 雖列 `ros-jazzy-laser-filters`，兩份 package inventory 都沒有它；不能把 Dockerfile 當作已安裝證據。此依賴須在後續 release provenance／V1 installed-package check 確認，不能因此推論原生 filter 不存在。[Dockerfile][docker]

固定 upstream：Nav2 [1.3.12 `6be3614…`][nav12]／[1.3.13 `f4108e5…`][nav13]；SLAM Toolbox [2.8.5 `ec8f763…`][slamtag]；laser_geometry [2.7.2 `a6f54a8…`][geometrytag]；SICK [3.9.0 `a562c5d…`][sicktag]。兩版 Nav2 的 `amcl_node.cpp`、`obstacle_layer.cpp` 本次逐檔比對相同。laser_filters 是 **可用候選** Jazzy release `2.0.10-5`，核對其 release commit `8d84bce…` 的 box filter 與 upstream 2.0.10 相同；不宣稱此 binary 已部署。[ROS distribution][distro]、[release filter][filter]

GitNexus 本 session 已確認 database format 42／40 不相容，dependency graph analysis 不可用；沒有重建共享索引。本次 source research 沒有修改產品 functions 或宣稱執行測試。

## 2. 正確 frame 與 `*_1` 的意義

ROS `LaserScan` 規定角度繞訊息 frame 的 +Z，零度沿 +X；只有在 +Z 向上觀看時才是常說的逆時針。REP-103 要求右手系，但感測器倒裝後，其 local +Z 可以在 base 座標朝下；這不會使 frame 變左手系。[LaserScan message][scanmsg]、[REP-103][rep]

例：真實安裝 `Rz(ψ) Rx(π)` 把 sensor 平面點 `(r cosθ, r sinθ, 0)` 轉成 base 中朝向 `ψ−θ` 的點。這是三維 proper rotation；不需要先把 scan 改造成另一個 Z-up frame。這是幾何推導，不指定本車實測安裝值。

SICK 3.9.0 publisher 設 `frame_id = publish_frame_id + '_' + (layer_idx+1)`；多 echo 同時發布時還可能附 echo suffix。`_1` 是 layer 編號，**不是**「driver 已校正倒裝」或「Z-up」的標誌。picoScan launch 的預設註解也明列 `world_1`。driver-native scan frame 與物理 housing frame 是否重合，仍要依官方 axes 與實際安裝確認；不可以後綴命名猜 TF。[SICK publisher][publisher]、[picoScan launch][sicklaunch]、[SICK frame 說明][sickreadme]

SICK compact parser 以 `x=r cos(azimuth) cos(elevation)`、`y=r sin(azimuth) cos(elevation)`、`z=r sin(elevation)` 建立 points；LaserScan publisher 使用 range／azimuth 資料。預設額外 transform 為零；本次 native-TF 可用性結論不依賴 driver 內再加一份安裝補償。[compact parser][compact]、[picoScan launch][sicklaunch]

## 3. 各 consumer 的實際能力

| Consumer／版本 | Source 行為 | 適用邊界 |
|---|---|---|
| AMCL 1.3.12／1.3.13 | 在 scan stamp，把 `angle_min` 與 `angle_min+angle_increment` 的 orientation 轉到 base，取 yaw 差作有效 increment，再對 readings 計算 bearing。原始碼明寫 upside-down 支援。 | 平面 scan 可由 TF 表達倒裝與 yaw；不需要把 ranges 全域反射。這不是任意非平面 tilt 的三維定位模型。 |
| SLAM Toolbox 2.8.5 | 由 base↔laser TF 判斷 inverted，保存 mounting yaw；正常 mapping 路徑 `scanToReadings()` 用 reverse iterators 反轉 readings。 | `makeLaser()` 原封使用 angle_min/max/increment；所以需下節的對稱掃描條件，不能外推任意 crop／negative-increment profile。 |
| laser_geometry 2.7.2 | 以 `angle_min+i*angle_increment` 投影 XY，再用 quaternion／translation transform。transform overload 可查首尾時間並以點 index 插值。 | 支援倒裝三維旋轉；是否能補償 robot motion 取決於 caller 的 target frame 與時間資料。 |
| Nav2 ObstacleLayer | 先在 scan 自身 frame 投影 cloud，再由 ObservationBuffer 用 TF 轉到 local/global costmap frame；保留 sensor origin 供 raytrace。 | 不要求 scan frame 的 +Z 在 base 朝上；需要有效 TF、height/range/filter 設定。 |
| LaserScanBoxFilter 2.0.10-5 候選 | 以 laser_geometry 將 points 轉到 `box_frame` 判斷 box，用 index 把原 scan 對應 range 設為 NaN，保留原 frame／metadata／index order。 | 可在 `base_link` 做 self-filter，不需要先重排為 Z-up；必須實際安裝並使 TF 可用。 |

來源：[AMCL][amcl]、[SLAM metadata][slamlaser]、[SLAM readings][slamread]、[SLAM mapping caller][slamcommon]、[geometry][geometry]、[ObstacleLayer][obstacle]、[ObservationBuffer][observation]、[BoxFilter][filter]。

### SLAM Toolbox 的重要條件

設原始角度範圍為 `[a,b]`，共 N 束、正 increment `d`，`b=a+(N−1)d`。倒裝後反轉 readings，新 index j 對應的正確 base bearing 是 `ψ−b+j*d`；2.8.5 的 Karto metadata 卻產生 `ψ+a+j*d`。兩者一致需 `a≈−b`。這是從 source 推導的限制；不是 upstream 已驗證所有非對稱情境。[SLAM metadata][slamlaser]、[readings reversal][slamread]、[Karto bearing][karto]

SICK picoScan 原生 template 的完整角度範圍預設為 −138°…+138°，並未由本研究確認 device 當前 profile。**可支援的最小選項**是保持對稱 fullframe scan，只用 NaN 去除 self hits，不裁切 scan 的角度範圍／index sequence；asymmetric crop 不是此 native-fit 結論涵蓋的輸入。後續 startup／consumer metadata acceptance 應檢查支持 profile，actual configuration 仍由 V2 確認。[SICK launch defaults][sicklaunch]、[BoxFilter][filter]

不能只因 ranges 長度正確就宣稱 beams 正確：需 frame identity、finite angle metadata、positive increment、`a+(N−1)d≈b` 及對稱區間彼此一致。這些是 supported-profile 驗證責任，本文沒有新增 validator 或選定容差。

## 4. First-ray time 與保留 native scan order

LaserScan header stamp 是第一束的 acquisition time；`time_increment` 是相鄰束的測量時間間隔。它不是接收時間、publish time，也不是任意重排後仍可照抄的值。[LaserScan definition][scanmsg]

SICK 3.9.0 的 compact parser 取 scan start ticks，經 Software PLL 對到 system time；fullframe collector 保存起始 segment timestamp，組合並排序 segments／azimuth 後傳給 LaserScan publisher。publisher 算 `angle_increment=(max-min)/(N−1)`，只有 `max>min` 才保留該 scan；`time_increment=scan_time/(N*2π/(max-min))` 是由週期與角度跨度估算，LaserScan 並未逐束保留原有 sensor timestamps。[compact timestamp][compact]、[publisher fullframe／metadata][publisher]

因此 upstream 提供了時間生成路徑，但「此設備/profile 的最小角度第一束、acquisition 順序、fullframe start stamp 與估算 dt 一致」仍是 runtime evidence。Software PLL 存在也不等於已測得跨感測器同步誤差界限。[SICK timestamp 說明][sickreadme]、[publisher][publisher]

現行 normalizer 反轉 ranges/intensities 並改角度正負，卻保留 stamp、time_increment、scan_time、frame ID。若原量測 `i` 的時間是 `t0+i*dt`，反轉後 index j 的真實時間為 `t0+(N−1−j)*dt`，現存 metadata 卻描述 `t0+j*dt`；除 dt=0 或特定中點外不同。**這是 source＋訊息契約可確認的時間映射缺口**；本研究沒有量測其實際誤差。保留 native beam order 可避免引入這層額外重排錯誤，不代表 driver acquisition timing 已驗收。[normalizer][normalizer]、[LaserScan contract][scanmsg]

### TF 支援不能冒充完整 deskew

- **AMCL** 以 scan stamp 取 odom pose，scan bearing 計算沒有按 `time_increment` 逐束取 odom。[AMCL][amcl]
- **SLAM Toolbox** 正常 mapping 用 scan stamp 的 odom pose，Karto scan 保存單一 time；`scanToReadings` 只傳 ranges。[async callback][slamasync]、[mapping][slamcommon]
- **laser_geometry** 本身能在首束 `t0` 與末束 `t0+(N−1)dt` 查 target←scan transform，線性／slerp 插值；它假設 scan 期間的運動可由此近似。[geometry][geometry]
- **目前 Nav2 ObstacleLayer caller** 傳 `target_frame=scan.header.frame_id`，然後 ObservationBuffer 才一次轉 cloud 到 costmap frame。因此不能因使用 transformLaserScanToPointCloud 就宣稱此路徑已逐束補償 base 在 odom 中的移動。[ObstacleLayer][obstacle]、[ObservationBuffer][observation]
- **BoxFilter** target 為 base_link；對剛性安裝的 sensor，這是靜態幾何 self-filter，保留原 scan，不對整車世界運動提供獨立 deskew。[BoxFilter][filter]

以上限制不構成保留 handedness normalizer 的理由：該 node 本身沒有 deskew，且會改變索引時間關係。是否需要更強 motion-distortion compensation 應由實際速率、旋轉與觀測誤差決定，不在本研究預設新增 pipeline。

## 5. 可交接結論與尚待證據

**Native reuse disposition：** 在支持 profile 限定為倒裝平面、positive-increment、對稱完整 scan 時，可由真實 sensor TF＋native consumers 承擔 frame 幾何，移除 scan reflection 沒有已發現的必需功能缺口。frame 與量測的語義須一同修正；不批准只改 topic 或只刪 node 的局部變更。此項供 robot-model 決策記錄採用，本文不改 source/config/spec。

normalizer 同時發布 raw-receive freshness diagnostics；刪除 conversion node 不代表診斷責任消失。此監測是另一項責任，應由後續 health/observability 決策安置，不能為了保存它而推論量測反射必須保留。[normalizer diagnostics][normalizer]

| 後續證據層級 | 仍需確認的 observable facts |
|---|---|
| V1 software／deployment | 所選 image／overlay／package version；laser_filters binary 實際可用；正確 frame naming/TF；對稱 profile acceptance；synthetic 倒裝平面幾何於 AMCL、SLAM、costmap、box filter 一致。 |
| V2 connected、chassis raised | 實際 sensor axes／mounting、actual `_1`／echo suffix、fullframe angle interval／beam order／metadata continuity、first-ray time／PLL 收斂、self-filter 的身體遮罩方向；不以輪子轉動證明車體動態精度。 |
| V3 ground in-place rotation | 固定環境幾何在轉動中是否鏡射、旋轉誤差／時間延遲與 motion distortion；確認前後 LiDAR 的同一世界幾何。 |
| 後續 ground short movement | 經前序允許後，再驗證 mapping/localization/costmap 在實際短移動的接受範圍；本研究未選速度或誤差 threshold。 |

Source／metadata research 已完成；**沒有產品 implementation、software runtime test、ROS launch 或 hardware validation**。私有幾何與現場設備資料未上傳；map／其他 decision tickets 由主 agent 統一更新。

## Public primary sources

[rep]: https://github.com/ros-infrastructure/rep/blob/11ca24a41f31480dfb9562ba99f2a5b93d3ebda5/rep-0103.rst
[scanmsg]: https://github.com/ros2/common_interfaces/blob/a941f14bb318d8d904505ed935ccbb97f24a70a4/sensor_msgs/msg/LaserScan.msg
[nav12]: https://github.com/ros-navigation/navigation2/commit/6be3614013ec586051b86c97b919b293281490fe
[nav13]: https://github.com/ros-navigation/navigation2/commit/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501
[slamtag]: https://github.com/SteveMacenski/slam_toolbox/commit/ec8f7635dea317b531c419f798f87d90a336f32e
[geometrytag]: https://github.com/ros-perception/laser_geometry/commit/a6f54a8436cc235160299daf99229d8b1588645e
[sicktag]: https://github.com/SICKAG/sick_scan_xd/commit/a562c5d098de21f6284359f4dfea97e93bd2b4d5
[distro]: https://github.com/ros/rosdistro/blob/6362c48a5abf60d9ae463d45267988944dbe4af9/jazzy/distribution.yaml
[docker]: https://github.com/monkey30440/mobile_base/blob/8d17bdb6239702d8e7ec9a2cd170b696a6045bef/Dockerfile
[normalizer]: https://github.com/monkey30440/mobile_base/blob/8d17bdb6239702d8e7ec9a2cd170b696a6045bef/src/mobile_base_perception/scripts/scan_handedness_normalizer.py
[launch]: https://github.com/monkey30440/mobile_base/blob/8d17bdb6239702d8e7ec9a2cd170b696a6045bef/src/mobile_base_perception/launch/sick_dual_lidar.launch.py
[amcl]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_amcl/src/amcl_node.cpp#L802-L880
[slamlaser]: https://github.com/SteveMacenski/slam_toolbox/blob/ec8f7635dea317b531c419f798f87d90a336f32e/src/laser_utils.cpp#L84-L181
[slamread]: https://github.com/SteveMacenski/slam_toolbox/blob/ec8f7635dea317b531c419f798f87d90a336f32e/include/slam_toolbox/laser_utils.hpp#L36-L57
[slamcommon]: https://github.com/SteveMacenski/slam_toolbox/blob/ec8f7635dea317b531c419f798f87d90a336f32e/src/slam_toolbox_common.cpp#L731-L753
[slamasync]: https://github.com/SteveMacenski/slam_toolbox/blob/ec8f7635dea317b531c419f798f87d90a336f32e/src/slam_toolbox_async.cpp#L34-L61
[karto]: https://github.com/SteveMacenski/slam_toolbox/blob/ec8f7635dea317b531c419f798f87d90a336f32e/lib/karto_sdk/include/karto_sdk/Karto.h#L5650-L5676
[geometry]: https://github.com/ros-perception/laser_geometry/blob/a6f54a8436cc235160299daf99229d8b1588645e/src/laser_geometry.cpp
[obstacle]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_costmap_2d/plugins/obstacle_layer.cpp#L334-L366
[observation]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_costmap_2d/src/observation_buffer.cpp#L83-L167
[filter]: https://github.com/ros2-gbp/laser_filters-release/blob/8d84bce9573ff3b13848bd477d5649aa5fd89e75/include/laser_filters/box_filter.h#L126-L208
[publisher]: https://github.com/SICKAG/sick_scan_xd/blob/a562c5d098de21f6284359f4dfea97e93bd2b4d5/driver/src/sick_scansegment_xd/ros_msgpack_publisher.cpp
[compact]: https://github.com/SICKAG/sick_scan_xd/blob/a562c5d098de21f6284359f4dfea97e93bd2b4d5/driver/src/sick_scansegment_xd/compact_parser.cpp
[sicklaunch]: https://github.com/SICKAG/sick_scan_xd/blob/a562c5d098de21f6284359f4dfea97e93bd2b4d5/launch/sick_picoscan.launch#L8-L25
[sickreadme]: https://github.com/SICKAG/sick_scan_xd/blob/a562c5d098de21f6284359f4dfea97e93bd2b4d5/README.md

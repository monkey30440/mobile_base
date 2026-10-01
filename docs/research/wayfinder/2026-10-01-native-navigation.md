# Native global navigation 與 localization：版本、能力與邊界

研究日期：2026-10-01。對應 [查明 native global navigation 與 localization 能力邊界](https://github.com/monkey30440/mobile_base/issues/4)，上層 [Wayfinder 決策地圖](https://github.com/monkey30440/mobile_base/issues/1)。

本研究只回答 native facts、fit、gaps 與後續問題。使用者本次確認的 mandatory route、局部繞障後必須回路網、無法繞過即停止／失敗、任意 x/y/yaw 與 station→pose、operator-managed V1，以及 map-outside startup 是探索前提。舊 spec、audit、BT、自訂 localization monitor 只是現況證據；本文不批准新 architecture、readiness 狀態模型、recovery policy 或 implementation。

## 1. 結論與版本可信範圍

**現有 Jazzy 套件已包含官方 Route Server、route tracking、corner smoothing 與 AMCL 所需基本介面，不必先假設升級 ROS distro。** 但這些原件沒有自動組成「僅局部偏離、必須回路網、不可繞過就以所需停止證據結束」的產品契約；route planning、route progress、controller completion 與 physical stopped 是不同事實。[官方 Jazzy 回移植][backport]、[Route Server source][route-server]、[controller source][controller]

| 證據層 | 查到的事實 | 不能推論的事 |
|---|---|---|
| Repo baseline `8d17bdb6239702d8e7ec9a2cd170b696a6045bef` | Dockerfile 安裝未 pin 版本的 `ros-jazzy-navigation2`／`nav2-bringup`；repo source 沒有 Nav2 clone/build 步驟 | 下次重建會得到相同版本；base image tag 等於 immutable digest |
| 停止中的既有 dev container `mobile_base` | image `sha256:d8ae0269cc7b1c97c9d20ecc2d98b10110d318bb19d0974b82b2167054892186`，dpkg 與 `nav2_route/package.xml` 為 1.3.13 | 目前機器正在用此版本跑導航；沒有 workspace overlay |
| 既有 `mobile_base:release` image | image `sha256:b29858229cd8feddbe5fa4d7b5ab2e10433599d2612f31f2386e23efb727e7b0`，dpkg 為 1.3.12，包括 `nav2_route` | release 已部署／啟動，或與 dev 相同 |
| Upstream source | 1.3.12=`6be3614013ec586051b86c97b919b293281490fe`；1.3.13=`f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501` | branch HEAD、生成 API 網頁與 installed binary 永遠相同 |

Repo 證據：[Dockerfile][repo-docker]、[release compose][repo-compose]。Local inventory 是本次只讀觀察；dev 以 `docker inspect`、從停止中的既有容器 `docker cp /var/lib/dpkg/status` 與 route `package.xml` 取得。Release inventory 由同一 Wayfinder 的 [native-motion 研究](https://github.com/monkey30440/mobile_base/issues/3) 共享：以臨時、從未啟動的容器讀取同一 dpkg 檔後移除。沒有啟動 ROS、build 或硬體動作；沒有 running containers。這是 package inventory，不是執行中 resolved-prefix／binary attestation。

| `ros-jazzy-*` package | Release image Debian version（arm64） | Dev container Debian version（arm64） |
|---|---|---|
| `nav2-route` | `1.3.12-1noble.20260614.083322` | `1.3.13-1noble.20260903.010339` |
| `nav2-amcl` | `1.3.12-1noble.20260614.075224` | `1.3.13-1noble.20260902.211420` |
| `nav2-bt-navigator` | `1.3.12-1noble.20260614.082455` | `1.3.13-1noble.20260903.005322` |
| `nav2-mppi-controller` | `1.3.12-1noble.20260614.082708` | `1.3.13-1noble.20260903.005819` |
| `nav2-msgs` | `1.3.12-1noble.20260612.162307` | `1.3.13-1noble.20260902.193503` |
| `navigation2` | `1.3.12-1noble.20260615.092426` | `1.3.13-1noble.20260907.041002` |

官方於 **2025-09-09** 將 Route Server 回移植到 Jazzy；1.3.9 tag 已有套件，1.3.12（2026-04-29）與 1.3.13（2026-08-21）均包含。這是 upstream backport，沒有證據顯示本 repo 自行 backport Route Server。[回移植 PR][backport]、[1.3.9 package][route-139]、[1.3.12 release][release12]、[1.3.13 release][release13]

本研究逐檔讀取固定 1.3.13 source，並比對 [1.3.12→1.3.13 changes][compare]：`nav2_route` runtime source、AMCL source、本文所用 BT navigator/action-server implementation 均無差異；controller 有實質差異，已於第 4 節列明。AMCL 的共用 message validation 在 1.3.13 另有 map resolution／尺寸有效性修補；「AMCL source 相同」不等於所有依賴行為均相同。

**文件版本陷阱：** [Jazzy→Kilted guide][migration] 記錄最初加入 Route Server 的歷史，不能推翻後續 Jazzy backport。現在的 [Jazzy Route guide][route-doc]／[route BT walkthrough][route-bt-doc] 也不能單憑網址當作已安裝範例清單；`navigate_on_route_graph_w_recovery.xml` 不在固定 1.3.12／1.3.13 的 [BT directory][bt-dir]。回移植 PR 明列排除 Simple Commander route API；使用 convenience API／較新 BT node 前仍需核對 release，不可把「server 已有」當成整套新版本 API 已有。

## 2. Route planning、tracking 與局部繞障

| 原生能力（1.3.12／1.3.13） | 實際語義與限制 |
|---|---|
| `ComputeRoute` | 請求可用 graph node IDs 或 start／goal poses；`use_start=false` 由 TF 取得起點。Result 有 `Route`、dense `nav_msgs/Path`、planning time、numeric error code；沒有 route execution feedback。它算完即結束，不執行 route operations。[action][compute-route]、[server][route-server] |
| `ComputeAndTrackRoute` | 先規劃，再由 robot pose 追蹤 node／edge 進度並觸發 operations；feedback 有 last／next node、current edge、route、path、operations、rerouted。這個 server 不產生 chassis velocity，仍需要 controller／BT 協調。[action][track-action]、[tracker][tracker] |
| 路網限制 | GeoJSON loader 依 `startid→endid` 加入有向 edge；成本、semantic metadata、dynamic blocked edges、orientation scorer 等可影響 graph search。這些是 edge 選擇／進度規則，不是 robot footprint 的硬性走廊限制。[loader][graph-loader]、[README][route-readme] |
| 任意 pose 對路網的關聯 | GoalIntentExtractor 尋找鄰近 nodes，可用 costmap BFS／line-of-sight 改善可達性選擇，並 prune 起終點；拿不到 costmap 時這個 extractor 會退回 Euclidean nearest-node。這不等於已規劃／驗證任意 pose 與 graph 的 connector。[extractor][extractor] |
| Dense path 與 smoothing | PathConverter 沿 edges 插點；啟用時在轉角插入圓弧，無法平滑的角保留折線。此 converter 沒有 costmap collision／footprint 驗證；平滑本身會離開數學上的 edge 中心線。[converter][converter] |
| Tracker 完成 | 邊界 node 用 radius；中間 node 另用方向 bisector 判通過。它容許非零偏離，終點 node 完成不包含任意 goal yaw／零速，也沒有「離路多久／多遠後必須 fail」的通用限制。[tracker][tracker] |
| `CostmapScorer` | 檢查直線 edge 上離散 costmap cells，可拒絕 collision／off-map edges；沒有 costmap 時不能替 edge 給有效分數。它沒有搜尋離 edge 的繞障 path。[scorer][scorer] |
| Route `CollisionMonitor` operation | 追蹤時檢查前方 edge 中心線。`reroute_on_collision=true` 標 blocked edge 並要求重算 graph route；false 拋 `OperationFailed`。這不是生成局部繞行，也不是獨立 `nav2_collision_monitor` 的 velocity safety filter。[operation][route-collision] |

**Mandatory route 的 fit：** Route Server 可提供受 graph 限制的全域路線；MPPI 可跟隨 path、以局部 costmap 產生避障控制。MPPI 的 PathAlignCritic 在局部 path 被障礙佔用達門檻時會不計 alignment cost，讓避障有空間；PathFollow／其他 critics 仍是最佳化目標。由 source 推論：這支持局部偏離的候選方式，但不保證固定最大偏離、指定 re-entry edge／point、保持 node 順序，或所有可通行障礙都一定找得到解。[MPPI guide][mppi-doc]、[alignment critic][align]、[path handler][path-handler]

**局部繞障與 graph reroute 必須分清：** 當 route 中心線被物體擋住，即使側邊可能繞過，CostmapScorer 仍可能直接拒絕該 edge；CollisionMonitor 也可能先要求 graph reroute／fail。要給 controller 局部繞障機會，這些原生選項如何協作需要產品決策與後續驗證，不能假設把全部 plugins 打開就滿足需求。`CollisionMonitor` 在此版本預設訂閱 local costmap；其實作直接把 edge 座標傳入 costmap `worldToMap`，沒有在該 operation 轉換 route／costmap frames，配置時必須核對座標一致性。[scorer][scorer]、[operation][route-collision]

**停止／無進展：** Controller Server 有 costmap timeout、TF error、NoValidControl、patience 與 progress checker 的失敗路徑；常見異常路徑會發布 zero velocity。`SimpleProgressChecker` 只看一段時間內 XY 位移是否超過半徑；繞圈或朝錯方向移動仍可能通過，因此不能單獨證明回到 mandatory route。[controller][controller]、[progress checker][progress]

原生候選仍有兩類：直接追隨 route dense path，以 controller 處理小範圍避障；或以 graph 提供路線意圖，再針對局部 route segment 使用 free-space planner。Upstream 明確支持這兩類用法，但後者的局部規劃範圍、允許跳過的路網部分與 re-entry 條件不由一般 `ComputePathToPose` 自動保證。本文不選其一。[Route README][route-readme]

**首末段尚未決定：** 支援 arbitrary x/y/yaw 不等於允許任意距離自由行走以接入路網。Off-route start／goal 的允許範圍、合法 connector、同一 edge 起終點／pruning、crossing／loop，以及無合法 connector 時的結果，應交給 [mandatory route 決策](https://github.com/monkey30440/mobile_base/issues/9)。原生 `ConcatenatePaths` 只串接 poses，沒有 frame transform、接縫可行性／碰撞檢查或 route 合規證明。[concatenation][concat]

## 3. AMCL、Initial Pose 與 map-outside startup

**可以 active 而未定位。** AMCL configure／activate 不以「已得到正確 global pose」為完成條件；沒有 map 時 scan callback 等待 map，未知 initial pose 時不發布可用 AMCL pose／map→odom。`set_initial_pose=false` 可等待 operator；true 則 activate 時用參數注入 prior。AMCL 不需要機器物理上先在 map 內才能作為 process 存在，但「機器在 map 外」不能由一個 active state 自動辨識。[AMCL source][amcl]、[AMCL guide][amcl-doc]

| 介面／證據 | 固定版本行為 | 使用界線 |
|---|---|---|
| `initialpose`／`set_initial_pose` | `PoseWithCovarianceStamped` prior；檢查訊息與 global frame，重設粒子分布。Inactive 時保留待 activate 處理；`set_initial_pose=true` 的參數 prior 可先於此路徑。歷史 stamp 嘗試以 odom 積分到現在，TF 失敗可退 identity。 | 送出／service 回應不等於完成 sensor-based localization；frame、timestamp、prior 與 map 身分需要一致。[AMCL][amcl] |
| `reinitialize_global_localization` | Empty service，將粒子重設為 map free-space 上 uniform distribution；設 internal known flag，下一 scan 重新估計。 | 回覆只代表 reset callback 完成；不是已收斂、pose 正確或恢復成功。Callback 本身沒有完整 map／active readiness gate，不能把 service existence 當作可安全 reset 的證明。[AMCL][amcl] |
| `request_nomotion_update` | Empty service 只把 `force_update_` 設 true；後續有效 scan 才使 filter 更新。 | 不啟動 scan、不命令 robot motion、不等待結果；多次回覆不是多次獨立量測證據。[AMCL][amcl] |
| 正常更新 | 有效 scan 需要 scan-frame／base 及 scan timestamp 的 odom transform；符合 `update_min_d`／`update_min_a` 或 forced update 才更新；resampling／初次發布等條件才發布 pose。 | 站定時 `amcl_pose` 不必等速更新；以固定 topic age 直接宣告故障會誤讀 event-driven 行為。[AMCL][amcl] |
| `amcl_pose` stamp／covariance | stamp 為輸入 laser scan stamp；pose 是最高權重 cluster mean，covariance 使用 overall filter covariance。 | covariance 是 filter 分布的不確定性，不是相對真實世界的誤差界，也不是 map 身分／觀測相符證書。[AMCL][amcl] |
| `map→odom` | 以 scan stamp 加 `transform_tolerance` post-date；沒有重新估計的 scan 可重發上次 transform。 | TF 目前可查／stamp 往前不等於新的定位估計，更不等於 pose 正確。[AMCL][amcl] |

**Low covariance ≠ correctness。** 粒子集中可以是錯誤 prior、環境混淆或錯誤 map 下的集中；native PF 的 internal converged 檢查主要看粒子 XY 分散程度。以上「不構成正確性證明」是從 estimator 計算內容作出的證據界線推論，不是本次量測到失定位。沒有證據要求保留現有 custom scan-map evaluator，也沒有證據准許僅靠 covariance 宣告產品 readiness。[PF source][pf]、[AMCL likelihood model][laser-model]

**Reset 的時間界線：** Initial Pose／global reset 不會替外部 consumer 清除既有 TF buffer 或所有先前 pose；reset service response 也沒有 post-reset observation identifier。後續若要求「採用新 prior 後已有足夠新證據才可導航」，需明訂可觀測證據與接受準則；本研究不發明 evaluator、狀態機或自動 recovery 行為。[AMCL source][amcl]

**Operator V1 的 fit（推論）：** 本地 odom／teleop 可以不以 map→odom 為前提，global navigation 則需要 global pose 與相應 map／costmap；因此「在地圖外啟動→teleop 進入→operator Initial Pose→global navigation」在原生依賴上可成立。成功率、operator 判斷方式、開放導航的時機與定位失效後結果仍待 [localization 契約](https://github.com/monkey30440/mobile_base/issues/8) 決定，並與 [本地狀態估計權威](https://github.com/monkey30440/mobile_base/issues/6) 對齊。

## 4. 任意 goal yaw、完成、feedback 與 failure owner

原生 `NavigateToPose` goal 是 pose／BT filename，沒有 named station 欄位；station→pose 仍是 site data 的名稱解析問題，現有 CLI 是一份整合證據，不構成新架構要求。[NavigateToPose action][nav-action]

**Yaw 不會被 action 本身丟掉，但 route path 會使用 edge orientation。** NavigateToPose 轉換完整目標 pose 並存入 goal blackboard；PathConverter 尾 pose yaw 由最後 edge 方向生成，並不複製任意 goal yaw。`GoalPoseOrientationScorer` 可以偏好／限制接近方向，仍不能取代 final pose 的 yaw。NavFn 預設 `use_final_approach_orientation=false` 的 path 尾端保留目標 orientation；開啟後則改用進場方向。[navigator][navigator]、[converter][converter]、[NavFn][navfn]、[route scorers][route-readme]

`SimpleGoalChecker` 檢查 XY／yaw，預設 stateful 可在進入 XY 容差後停止重查 XY；`StoppedGoalChecker` 再以傳入 twist 檢查平移／角速度門檻。Controller Server 對收到的 path **最後 pose** 作 goal check，使用自己的 `odom_topic` subscriber cache；它不從 NavigateToPose 原始 goal 另取 yaw。這個 odom subscriber 預設 topic 是 `odom`，`getTwist()` 沒有 freshness／received gate，goal checker 也沒有 dwell time。故「native success」不等於 fresh measured stop 或 physical stopped。[simple checker][simple-goal]、[stopped checker][stopped]、[controller][controller]、[odom subscriber][odom]

**1.3.12／1.3.13 的重要差異：** 1.3.13 先判 isGoalReached 再 compute command；1.3.12 順序相反。1.3.13 才把 goal-check 時 end-pose transform 失敗轉成 `ControllerTFError`；1.3.12 未檢查該 transform 回傳值。1.3.13 odom getter 加 mutex、MPPI 增 `open_loop`（預設 false），但都沒有補上 stopped freshness／physical evidence 契約。不能把 dev source 修補默認已在 release image 生效。[版本 diff][compare]

| Boundary／owner | 原生 observable result | 產品仍需釐清 |
|---|---|---|
| Action transport admission | inactive `SimpleActionServer` 拒絕 goal；active 時先接受並排程 execution | Accepted 不等於定位／route／chassis permission 全部成立。[simple action server][simple-action] |
| NavigateToPose 初始化 | BT load、取得 current global pose、goal transform 失敗時 callback false，BT action server abort accepted goal；此早退可帶預設 result（error code 0） | 真正 REJECTED、accepted→ABORTED、task failure code 必須分清。Code 0 不能脫離 ROS action status 當成功。[navigator][navigator]、[BT server][bt-server] |
| BT condition／recovery | 可用 native conditions、actions、RecoveryNode、Timeout 與自訂 plugin 組合 | `InitialPoseReceived` 本身只讀 blackboard bool，不訂閱／驗證 AMCL。BT 內 guard 在 accepted execution 後才生效；也不能補救 navigator 在 BT tick 前就因 TF 缺失中止。[condition][initial-condition]、[BT server][bt-server] |
| Route／planner／controller | 各有 action numeric error；route 包含 TF、no graph／route、indeterminant nodes、operation fail；FollowPath 包含 TF、invalid path、patience、no progress、no control、costmap timeout | 低層 fail 不應一律改寫成 localization failure；route planner 失敗也不是 chassis stop 證據。[route action][compute-route]、[tracking action][track-action]、[FollowPath][follow-action] |
| NavigateToPose result 聚合 | BtActionServer 從 `error_code_names` 指定的 blackboard keys 選最低非零碼；此版本不自動聚合 `error_msg` | Condition failure 未寫 key、goal initialization 早退或缺少 key，都可能 abort 且 code 為 0；不是完整 failure ledger。[BT server][bt-server] |
| Feedback | NavigateToPose 有 current pose、elapsed、recovery count；distance／ETA 從 `path_blackboard_id` 指定 path 算，預設 `path`，ETA 依 odom 速度；拿不到 robot pose 則該回合不發布 | 寫入另一 path key 不會自動接上 distance／ETA。Route edge IDs 等不在標準 NavigateToPose feedback 中；FollowPath `speed` 在此實作是輸出 command 的速度，不能當 stop feedback。[navigator][navigator]、[controller][controller] |
| 第二個 task | 同一 action server 支援 pending goal／preemption；NavigateToPose 可接受相同 BT 的替代 goal。NavigatorMuxer 限制同一 BT navigator 裡的不同 navigator plugin | 不等於跨 Navigation、Docking、Teleop、maintenance 的 chassis owner 排他，也不直接實現使用者的拒絕第二 owner。[simple action server][simple-action]、[navigator][navigator]、[muxer][muxer] |

## 5. 沒有 map／TF／global pose 時的 lifecycle 與 costmap

| 元件 | 1.3.12／1.3.13 source 所示行為 | 對 map-outside startup 的含義 |
|---|---|---|
| Map Server | 非空 yaml 載入失敗會 configure 失敗；空 yaml 可 configure／active，待 `load_map`，沒有 map 時不發布 occupancy map | Active 不是 map available。[map server][map-server] |
| AMCL | 可 active 未 initial pose；無 map 不處理 scan；沒有已知 initial pose 不發布定位 pose／TF | Localization process health 可與 global-navigation usability 分離，但狀態命名未定。[AMCL][amcl] |
| Local costmap | `Costmap2DROS::on_activate` 先等其 `global_frame→robot_base_frame`，預設 `initial_transform_timeout=60s`；無 TF 則 activation failure | 設為 odom 且只用本地 obstacle layers 時，不必依賴 map→odom；仍需 odom/base/sensor TF。[costmap][costmap] |
| Global costmap | 相同 activation gate；若 global_frame=map 而 map→base 缺失，會等到 timeout 失敗。之後 `start()` 另等首次 successful pose update，這段沒有相同 timeout | 不能宣稱任何啟動等候都必定在 60 秒內結束；晚來 Initial Pose 不會自動重跑已失敗 lifecycle transition。[costmap][costmap] |
| Static layer／costmap current | 未收到 map 時 static layer 保持 not-current，update 路徑跳過並警告；costmap lifecycle active／已跑一回 update 不保證所有 layers current | map、TF、layer data 不能互相替代。Planner／Controller action 另有 `costmap_update_timeout` 失敗路徑。[static layer][static-layer]、[planner][planner]、[controller][controller] |
| Lifecycle Manager | 按 node list configure，再 activate；任一步失敗 startup false，沒有自動無限重試等待 localization。Bond-loss 可對整個 managed group reset；可設定 respawn reconnection | 分組與 activation 時機會影響本地能力能否獨立存在；bond 表示通訊／process lifecycle，不是 localization correctness。[manager][manager] |
| Route Server | configure 載 graph／plugins；activate action servers 不驗證 localization。Pose-based route／tracking 於執行時取 TF，costmap scorers／operations各自需要資料 | Active route server 不是可導航證明；ID-only planning 與需要 robot pose 的 tracking 依賴不同。[server][route-server]、[extractor][extractor] |

Native support 可構成適當的生命週期分工，但本文不選 staged activation／grouping、central readiness authority 或恢復策略。交接至 [capability lifecycle 與失敗隔離](https://github.com/monkey30440/mobile_base/issues/11)，並由 [health／readiness／observability 分工](https://github.com/monkey30440/mobile_base/issues/14) 決定對外語義。

## 6. 現況整合證據，不能沿用成新契約

以下只指出 baseline 值得後續重查的組合，不提出修補 implementation：

- 既有 BT 用 `ComputeRoute`，並以 planner／ConcatenatePaths 串接 First／Route／Last；沒有 `ComputeAndTrackRoute`，所以 route tracker operations 不因 YAML 配好就執行。`CostmapScorer` 仍會在 ComputeRoute 規劃時生效。[repo BT][repo-bt]、[route server][route-server]
- 既有 Last Mile 若起終位置接近便直接保留 route path；這可能把 route 最後 edge yaw 當 final goal yaw，必須與任意 pose 需求重新核對。[repo BT][repo-bt]、[converter][converter]
- 既有 BT 將執行路徑存 `final_route_path`，而 navigator 未設定 `path_blackboard_id`；原生 feedback 距離／ETA 不會自動看到該 key。[repo BT][repo-bt]、[repo parameters][repo-params]、[navigator][navigator]
- 既有 AMCL `set_initial_pose=true` 且 prior=(0,0,0)，會注入 origin；這不是 operator 初始定位已完成的證據。Existing custom guard／recovery 不能自動成為新 V1 要求。[AMCL config][repo-amcl]、[repo BT][repo-bt]
- 既有 local costmap 在 odom、global costmap 在 map；navigation lifecycle group 同含 controller、planner、route、bt navigator、docking。Controller 的 `odom_topic` 未明列，而 navigator 有 `/odometry/filtered`；不同節點參數不互相繼承。[parameters][repo-params]、[launch][repo-launch]、[odom subscriber][odom]

## 7. 交接問題與驗證界線

| 已有 decision ticket | 研究後可以精確詢問的問題 |
|---|---|
| [mandatory route 與局部繞障](https://github.com/monkey30440/mobile_base/issues/9) | 「在路網上」容許多寬／何種 corner smoothing？是否允許改選其他 graph route？局部 detour 的最大範圍、允許重入點、不得跳過的 node／edge、期限與失敗條件？Off-route start／goal connectors 如何限制？Final yaw／route completion 分別由何結果證明？ |
| [global localization 依賴與恢復](https://github.com/monkey30440/mobile_base/issues/8) | Operator Initial Pose 後哪些 evidence 足以允許 global navigation？map／prior 改變後如何界定新證據？暫無新 `amcl_pose`、missing TF、觀測不相符與 process failure 要如何分別處置？Reset 是否有 V1 必要性，不預設自動 recovery。 |
| [chassis authority 與停止契約](https://github.com/monkey30440/mobile_base/issues/7) | Native action cancel／zero publish 到排他權交接之間，需要什麼 fresh controller/hardware evidence？第二 owner 拒絕如何涵蓋所有入口？ |
| [capability lifecycle 與失敗隔離](https://github.com/monkey30440/mobile_base/issues/11) | 未定位／在 map 外時哪些能力可以啟動，global costmap 等待／activation failure 不應帶走哪些能力？由誰在 operator 建立定位後請求適當 transition？ |
| [mapping 與 site data](https://github.com/monkey30440/mobile_base/issues/12) | Map、route graph、station pose 的身分／版本與合法範圍如何一同驗證？ |
| [operator-managed release](https://github.com/monkey30440/mobile_base/issues/13) | 交付以哪個明確 image/package set 為基準？1.3.12→1.3.13 修補與未 pin apt 要如何納入 release 證據？選新版／backport 僅在具體能力或 bug 需要時評估，不能只憑 latest docs。 |
| [health／readiness／observability](https://github.com/monkey30440/mobile_base/issues/14) | REJECTED、ABORTED、CANCELED、numeric code、operator recovery 與停止證據如何保持來源及用途清楚？標準 NavigateToPose feedback 已足夠哪些需求？ |

**研究完成的範圍：** 已辨識實際可見版本、官方 provenance、native API/source 行為、與使用者意圖的 fit／gap。沒有執行產品 tests、ROS launch、控制器或物理驗證，沒有建立驗證通過紀錄；沒有將 source 推論提升為實機保證。後續測試必須由批准的 acceptance criteria 決定，尤其是 obstacle detour/re-entry、localization correctness、fresh stopped 與 failure isolation；現有 static／topic evidence 不可替代控制器回授或 physical observation。

GitNexus 已嘗試作 exploration：mobile_base index 比 baseline 落後 4 commits，query 又回 DB format 42／40 不相容；未重建共享索引。依賴 impact 無法由 GitNexus 判定，本次以固定 source 查核 native 邊界，沒有修改產品 symbols。

## 固定版本主要來源

除明列文件／歷史版本者，下列 source links 固定於 Nav2 1.3.13 commit；與 1.3.12 的可沿用範圍見第 1 節及 compare。網頁及 GitHub source 均於 2026-10-01 查閱。

[backport]: https://github.com/ros-navigation/navigation2/pull/5517
[release12]: https://github.com/ros-navigation/navigation2/releases/tag/1.3.12
[release13]: https://github.com/ros-navigation/navigation2/releases/tag/1.3.13
[compare]: https://github.com/ros-navigation/navigation2/compare/6be3614013ec586051b86c97b919b293281490fe...f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501
[route-139]: https://github.com/ros-navigation/navigation2/blob/1.3.9/nav2_route/package.xml
[migration]: https://docs.nav2.org/rolling/configuration_and_development/migration_guides/jazzy/Jazzy/
[route-doc]: https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/core_servers/route_server/configuring_route_server/
[route-bt-doc]: https://docs.nav2.org/jazzy/getting_started/nav2_behavior_trees/trees/navigate_on_route_graph_w_recovery/
[amcl-doc]: https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/others/configuring_amcl/
[mppi-doc]: https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/controller_plugins/mppi_controller/configuring_mppic/
[bt-dir]: https://github.com/ros-navigation/navigation2/tree/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_bt_navigator/behavior_trees
[route-server]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_route/src/route_server.cpp
[route-readme]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_route/README.md
[compute-route]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_msgs/action/ComputeRoute.action
[track-action]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_msgs/action/ComputeAndTrackRoute.action
[tracker]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_route/src/route_tracker.cpp
[graph-loader]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_route/src/plugins/graph_file_loaders/geojson_graph_file_loader.cpp
[extractor]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_route/src/goal_intent_extractor.cpp
[converter]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_route/src/path_converter.cpp
[scorer]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_route/src/plugins/edge_cost_functions/costmap_scorer.cpp
[route-collision]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_route/src/plugins/route_operations/collision_monitor.cpp
[align]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_mppi_controller/src/critics/path_align_critic.cpp
[path-handler]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_mppi_controller/src/path_handler.cpp
[concat]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_behavior_tree/plugins/action/concatenate_paths_action.cpp
[progress]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_controller/plugins/simple_progress_checker.cpp
[amcl]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_amcl/src/amcl_node.cpp
[pf]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_amcl/src/pf/pf.c
[laser-model]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_amcl/src/sensors/laser/likelihood_field_model.cpp
[navigator]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_bt_navigator/src/navigators/navigate_to_pose.cpp
[navfn]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_navfn_planner/src/navfn_planner.cpp
[simple-goal]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_controller/plugins/simple_goal_checker.cpp
[stopped]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_controller/plugins/stopped_goal_checker.cpp
[controller]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_controller/src/controller_server.cpp
[odom]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_dwb_controller/nav_2d_utils/include/nav_2d_utils/odom_subscriber.hpp
[simple-action]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_util/include/nav2_util/simple_action_server.hpp
[bt-server]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_behavior_tree/include/nav2_behavior_tree/bt_action_server_impl.hpp
[initial-condition]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_behavior_tree/plugins/condition/initial_pose_received_condition.cpp
[nav-action]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_msgs/action/NavigateToPose.action
[follow-action]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_msgs/action/FollowPath.action
[muxer]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_core/include/nav2_core/behavior_tree_navigator.hpp
[map-server]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_map_server/src/map_server/map_server.cpp
[costmap]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_costmap_2d/src/costmap_2d_ros.cpp
[static-layer]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_costmap_2d/plugins/static_layer.cpp
[planner]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_planner/src/planner_server.cpp
[manager]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_lifecycle_manager/src/lifecycle_manager.cpp
[repo-docker]: https://github.com/monkey30440/mobile_base/blob/8d17bdb6239702d8e7ec9a2cd170b696a6045bef/Dockerfile
[repo-compose]: https://github.com/monkey30440/mobile_base/blob/8d17bdb6239702d8e7ec9a2cd170b696a6045bef/compose.release.yaml
[repo-bt]: https://github.com/monkey30440/mobile_base/blob/8d17bdb6239702d8e7ec9a2cd170b696a6045bef/src/mobile_base_navigation/behavior_trees/route_assisted_nav.xml
[repo-params]: https://github.com/monkey30440/mobile_base/blob/8d17bdb6239702d8e7ec9a2cd170b696a6045bef/src/mobile_base_navigation/config/nav2_params.yaml
[repo-amcl]: https://github.com/monkey30440/mobile_base/blob/8d17bdb6239702d8e7ec9a2cd170b696a6045bef/src/mobile_base_localization/config/amcl_params.yaml
[repo-launch]: https://github.com/monkey30440/mobile_base/blob/8d17bdb6239702d8e7ec9a2cd170b696a6045bef/src/mobile_base_navigation/launch/navigation.launch.py

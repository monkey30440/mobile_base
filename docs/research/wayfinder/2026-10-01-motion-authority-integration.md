# 原生 Actions 的 motion authority 與停止交接接入點

2026-10-01；AFK primary-source research，對應 [查明原生 Actions 的 motion authority 與停止交接接入點][ticket]。只回答可行接入點／限制，不選最終架構、不實作。

## 1. Scope 與 evidence pin

重用 [native motion][motion]、[navigation][navigation]、[docking][docking] 的已安裝版本與來源調查，不重新提取 inventory。此文新增接入點查核以 **Nav2/OpenNav 1.3.13 = `f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501`** 為準；既有 release 1.3.12 不因 dev source 研究自動升級。DDC buffer 路徑採已查4.42.1。

**F**＝固定source事實；**I**＝由source推導的整合限制；**O**＝可選方案，仍需後續決策及軟體／實機驗證。没有執行產品、build或硬體操作。以下「stopped」都指未來契約選定的fresh feedback＋dwell證據，不能等同安全認證或physical body stop。

## 2. 實際存在的 hooks

| 接入點 | F：固定source行為 | I：可以做／不能假裝做的事 |
|---|---|---|
| `SimpleActionServer::handle_goal` | inactive→REJECT，active→ACCEPT_AND_EXECUTE；建構函式把此member直接綁給rclcpp_action，沒有注入application admission callback的參數。[SAS] L100–160 | 真正goal-response拒絕必須在這個接受前邊界加hook，或由外部server持有public endpoint。BT第一個節點太晚。 |
| `handle_accepted`／pending goal | 若current active或worker仍跑，把新goal放pending並設preempt；已有pending會被terminate。`accept_pending_goal`會abort舊current並替換。[SAS] L200–232、363–383 | 原生不辨識「same owner」與「different owner」。goal UUID是goal身分，不是lease owner credential。連第二個同action request也可能影響現行任務。 |
| `BtActionServer::executeCallback` | 先執行`on_goal_received_callback`，false就terminate已接受goal；執行BT、haltAllActions、on_completion、按原BtStatus送terminal。[BT] L294–355 | `goalReceived=false`是accepted→abort，並非GoalResponse REJECT；completion前有接入時點，但不等於已提供通用stop handshake。 |
| Navigator plugin hooks | `goalReceived`、`onPreempt`、`goalCompleted`為實際virtual介面；`onCompletion`先release NavigatorMuxer，再叫goalCompleted；其BtStatus參數是值／const，completion只可改result不能直接重選外層SUCCEEDED/FAILED switch。[Navigator] L286–342 | 自訂navigator可插邏輯但不是純BT配置；muxer只涵蓋BT navigator，沒有Docking/Teleop/maintenance。等待停止逾時時只填error_code仍可能得到SUCCEEDED，需明確terminal策略。 |
| NavigateToPose同server preemption | 同BT的pending goal被接受替換；不同BT走terminatePendingGoal。[Pose] L196–224 | 不能用預設preemption表示「拒絕第二owner並保留舊任務」。若不需要same-owner replace，拒絕busy期間全部新goal是可選較窄政策；仍需接受前hook。 |
| BT cancellation／halt | engine在cancel时`haltTree`後直接回CANCELED，不再tick後續節點；BtActionNode halt有cancel/result timeout，超時只記log仍reset status。[Engine] L58–83；[BTNode] L313–339 | 在Sequence末尾加WaitStopped僅能涵蓋走到該尾端的正常路徑。cancel／exception／timeout不能靠尾端BT完成stop transaction；halt返回不是所有child producer已quiesced的證明。 |
| FollowPath controller terminal | cancel成功時先`terminate_all()`、再`publishZeroVelocity()`；正常完成與catch通常先zero再terminal。zero發布受`publish_zero_velocity`及publisher條件限制。[Controller] L512–517、552–622、771–792 | client收到CANCELED時，zero甚至可能尚未發出；zero publish也不代表gate/DDC/device已消耗。收到parent/child action結果不能直接release owner。 |
| DockRobot server | create SimpleActionServer時completion callback=nullptr。normal success走publishZeroVelocity→succeeded；cancel/preempt走zero→terminate_all；有early return paths。[DockServer] L74–85、202–247、279–359 | 任務state與停止交接必須查server全部出口；既有plugin不能涵蓋接受前、取消、例外與terminal commit。 |
| Dock plugin | NonChargingDock繼承ChargingDock；有configure/activate/deactivate、getRefinedPose、isDocked等，沒有per-task stop-begin／stopped-complete hook；isDocked要求快速返回。[DockPlugin] L30–101 | 不能把isDocked阻塞等待零輪速當stop phase：approach loop仍是控制方，而且可能繼續運動直到該predicate通過。plugin可提供幾何完成條件；server/gate仍需明確的停止階段。 |
| generic completion callback | SAS的completion_callback在execute exception、stop_execution、未完成goal／deactivate逾時等分支被叫；正常succeeded_current不呼叫它。[SAS] L239–278、294–323、500–510 | 不是可直接配置的通用「每任務最後finally」。把它當universal release hook會漏正常結果；terminate callback也不能任意在mutex持鎖區阻塞等待別的callback。 |

## 3. Ownership 與停止transaction的不可省略邊界

以下是需要方案回答的約束，**不是已存在的upstream API**。

1. **准入與grant要具原子性。** 兩個不同action server各查一次「free」再接受會race；接受前需單一atomic reservation，並處理accept失敗／未執行／server消失的rollback。callback不能無界等待或在同executor同步等自己處理的service。[SAS] L146–160、200–232。
2. **Busy包含STOPPING。** 新owner只有在舊producer不能再產生有效命令、gate輸出已歸零且收到fresh stop evidence後才可grant；stop timeout或unknown feedback保留無法grant的狀態。這個判定不能只由ROS action terminal推出，見FollowPath的順序。[Controller] L512–517。
3. **取消request、task terminal、producer quiescence、command invalidation、wheel stopped、body stopped不同。** 已知child cancel timeout會放行BT halt；故必須有可引用的child quiescence／失敗處置，或gate在此後持續拒絕舊producer，不能只等parent action的CANCELED。[BTNode] L313–339。
4. **Lease generation不能在接收時憑空補成安全身分。** TwistStamped沒有owner/token/generation欄位；把raw cmd到gate的時點貼上current generation，可能讓上一任務的晚到資料變成新owner命令。僅queue depth1、topic remap、收到zero或ROS stamp新鮮都不能證明無late command。[DDC] L459–496；I基於message不攜帶task provenance。
5. **可選防護（O）：** 在生產端把命令綁到已接受task/session generation；或證明producer已quiesced、隔離其通道並對buffer執行有順序證據的關閉／重啟barrier，再接受新session。具體選一條可測的路徑；不可只畫lease欄位卻讓所有raw messages自動得到新token。
6. **DDC有native reset primitive但範圍有限。** on_deactivate關subscriber、halt wheel commands、reset local buffers；不能清除其他producer／DDS／gate queue，也不證明車已停。每次交接都deactivate DDC是否值得是方案取捨，不是必需重新造controller。[DDC] L596–604、642–666。
7. **Gate fail-closed不等於process crash立即停車。** live gate可以拒收expired lease並持續zero；gate被kill後無法發zero，DDC需自己的有效command timeout且update持續運行；host/serial失效另依獨立device機制及實機證據。restart不能自動恢復old grant，須先關閉與確認狀態。[motion] §4、7；[platform-evidence]。
8. **維護工具必須納入device排他。** direct serial工具不經ROS velocity gate；應在取得maintenance authority並確認control已quiesced/釋放device後才可開啟，且所有工具遵守同一排他規則。只鎖ROS cmd topic不完整。[motion] §3、7。

## 4. 四種候選接入方案比較

| 方案（O） | 具體接入與最小變更面 | 可滿足範圍／代價與限制 |
|---|---|---|
| BT hooks＋narrow velocity gate | BT acquire/guard/normal stop節點；各motion producer分開輸入；gate唯一DDC writer | 可阻止未授權velocity並組合normal流程；**單獨不完整**：真正action REJECT已太晚，cancel/exception繞過BT尾端，DockPlugin沒stop hook，same-server preemption仍需處理。若加navigator override或server patch，應明列不再是BT-only。 |
| 受限upstream extension＋gate | 在SAS新增可注入接受前admission；由BT/Dock server接入atomic authority；在server已知的normal/failure/cancel出口先quiesce／invalidate command、zero、bounded stopped handshake，再commit terminal；common SAS異常出口要能維持blocked authority | 可保留原生action type/name、原生planner/controller/docking演算法；必須維護pin過的overlay及回歸，不能稱现成parameter。accept前callback、worker-quiescence與terminal policy是不同hook；不要在SAS mutex內做無界stop wait。FollowPath等child出口與bypass也要覆蓋。 |
| 外部native-action proxy＋gate | public NavigateToPose/DockRobot server用標準action types；在public handle_goal原子acquire；將goal/feedback/cancel/result轉交remapped backend；延後public terminal直到stop contract完成 | 不改Nav2/OpenNav核心，代價是每goal前後端UUID關聯、cancel-before-accept、backend crash/reject、feedback、timeout、late result與restart的轉送責任。這是有真實成本的proxy，不能換名字就稱沒有wrapper。backend要被限制為內部入口；namespace/remap本身不是access control。 |
| Operator-held session／authority | 操作者顯式取得session，只啟用所選motion capability；顯式cancel/close session→stop→再選下個；nativeaction可作session內executor | 合乎operator-managed操作面，但**只靠人遵守流程不滿足任意第二owner request的拒絕契約**。若native endpoints仍可自由存取會接受／preempt；仍需admission adapters或部署禁止bypass。改成公開session request而nativeactions只內用是可行不同介面選擇，須由決策票明確批准。 |

可更小的變體（O）：若native task terminal只代表演算法結果、ownership release由獨立gate狀態決定，可保持native result較早到达，但STOPPING期間不grant。此方案**不能**同时聲稱native SUCCEEDED/CANCELED本身保證stopped；若產品要求DockRobot SUCCESS包含姿態＋停止，則需terminal extension或proxy。兩種語义不要混用。

## 5. 內部task與bypass的具體問題

- **FollowPath不是第二chassis owner。** Navigator BT的child FollowPath應在同一navigation authority/session内執行；若每個child都獨立acquire，會把合法子任務當第二owner拒絕。反之把整個controller topic永遠標成navigation，任何直接FollowPath goal都可能挾持現有lease。[Controller] L461–541；I。
- 因此既有FollowPath endpoint及其他真正產生速度的behavior/task入口必須要麼是受限內部API，要麼傳遞／驗證上層session provenance。只包NavigateToPose和DockRobot卻保留任意直呼FollowPath的支援路徑不完整。ROS namespace只能區分名稱，不能作保證；可選deployment ACL、明確限定受信任內部caller，或相同authority-aware child接入，須可驗證。
- **Dock staging會發NavigateToPose child。** fixed source的Navigator helper在取消／逾時等待cancel response，並非完整stopped handshake。[DockNavigator] L75–84。map已要求local near-target docking；若採`navigate_to_staging_pose=false`，可以直接排除該跨task delegation，不必為尚未需要的自動staging造機制。若保留則需明確同一session delegation，不能讓Docking和Navigation互搶owner。
- **same-owner replacement與second-owner rejection不是同題。** native source沒有外部caller owner標識；不能由相同action名稱推出相同owner。最窄候選是busy期間所有新top-level goal一律拒絕，取消並停止後重送；若要同owner seamless replace，需額外定義owner認證、goal replacement及舊generation失效，不能沿用native preemption偷偷形成takeover。
- **Teleop是stream、maintenance可無action。** 它們需顯式session開始／結束與liveness責任；沒有必要為了統一形式另造Navigation Manager／Docking Manager，但必須有同一個共享authority決策點。原生velocity mux的priority不是該決策點。[motion] §7。

## 5.1 FollowPath 的兩階段內部授權可行性（O，source-supported）

**F：** 重用既有dpkg snapshots可確認兩套環境的`rclcpp_action`都是28.1.16；其`SendGoalOptions`只有goal response／feedback／result callbacks，`async_send_goal`內部產生UUID，公開選項沒有指定UUID欄位。接受後goal handle帶exact UUID。[Client] L352–377、431–471。native BT client目前在取得handle後繼續tick，沒有authority registration；這是需要新增的窄client integration。[BTNode] L370–438。

**可行順序：** public NavigateToPose／DockRobot仍需在真正GoalResponse ACCEPT之前取得atomic reservation；internal FollowPath可以先transport ACCEPT，motion execution保持`awaiting authorization`。BT client拿到handle後，透過內部registration提交parent lease/generation、exact child UUID、用途／授權範圍；server驗證該parent仍有效，才將此child轉成可執行current或合法同parent path update。這保留標準FollowPath action schema，不需要為pre-generated UUID修改rclcpp。

**必需的隔離：** awaiting-auth handles必須在有容量與時間上限的獨立集合，不能提前進SAS的current/pending slots或設preempt_requested；否則controller的`updateGlobalPath`已會accept pending並修改controller/path。[SAS] L200–232；[Controller] L724–767。只在`computeControl`第一行等待授權不夠，因existing-task preemption另有路徑。

無parent授權、錯UUID、過期generation、registration timeout及等待中取消，都只終止該candidate；不得reset現行controller、改path、cancel現行child或publish zero。接受了transport不代表motion admitted；這個語義只限受控internal child API，不可偷換public「第二owner要REJECT」要求。

**可用native primitive：** rclcpp server有`ACCEPT_AND_DEFER`與goal_handle.execute。[Server] L44–52；[GoalHandle] L217–239。但Nav2 SAS沒有現成deferred authorization模式，仍需接入；且deferred goal的abort/cancel合法state transition需處理。更窄候選是transport ACCEPT_AND_EXECUTE但只在server的授權等待狀態，不呼叫control算法；逾時可合法abort該executing handle。兩者都是要實作／測試的方案，非現有parameter。

**誰可registration：** 只有已取得parent lease的受支援內部caller可註冊child；產品CLI／maintenance不得取得或複用他人context。若環境不要求惡意DDS防護，可將此定為內部產品API並讓所有支持工具走有檢查的入口；不能聲稱namespace本身提供隔離。真正security boundary另需ACL，非本研究擴張要求。

**actual-publisher tagging可防晚到stream（O）：** ControllerServer `publishVelocity`及所有zero／cleanup，DockServer各control／reset／undock／zero publish點，都應使用該已授權task的immutable context，然後交給唯一gate；不是在接收raw Twist時查「目前owner」後重新貼標。[Controller] L771–792；[DockServer] L465、533、667、681、714–718。跨async計算也攜帶啟動時context，不能在送出時讀已換成新task的mutable全域context。gate檢查generation/session；舊nonzero與舊zero都丟棄，避免舊cleanup煞停新owner。gate本身發的stopzero由其正在停止的authority狀態產生。

這條候選的最小實質變更面因此是：public接受前hook、BT child accepted-handle registration、FollowPath候選隔離／授權promotion、native速度發布的task context、server terminal/quiescence hook與共享gate。planner/controller/docking算法及public Action types可保留；不需要通用manager或複製Nav2算法，但也不能宣稱只是launch/remap。

## 6. 決策交接與驗證清單

決策票需要選：public action是否必須真正GoalResponse REJECT；是否所有busy newgoal皆拒絕；native terminal是否包含stopped；upstream overlay或proxy的維護取捨；command provenance/barrier與internal-only API如何落實。以上每項已有可行選項，不留成「implementation自己找hook」。

後續software scenarios應覆蓋：兩種top-level goal同時到達只grant一個；busy同server goal不影響舊任務；cancel-before-backend-accept；FollowPath cancel terminal先於zero；child timeout／late result；Docking成功/失敗/取消/例外各出口；延遲舊cmd在新generation到達；gate/server重啟closed；lease expiry後不grant未知停止狀態；maintenance直開device被排他；internal FollowPath bypass。軟體測試不得代替controller/hardware feedback或body-stop實測。

GitNexus延用map已確認的DBformat不相容限制：dependency analysis未由圖譜完成。本研究只讀固定upstream與既有研究，不改main，不選production timeout／physical threshold，不新增硬體驗收主張。

## Sources

[ticket]: https://github.com/monkey30440/mobile_base/issues/16
[motion]: https://github.com/monkey30440/mobile_base/blob/0519298d8f95b7671708c78fbaf16358be623e96/docs/research/wayfinder/2026-10-01-native-motion.md
[navigation]: https://github.com/monkey30440/mobile_base/blob/2b97f17c0e1dccb304984d2f904c2ff597dff2a4/docs/research/wayfinder/2026-10-01-native-navigation.md
[docking]: https://github.com/monkey30440/mobile_base/blob/694afd36c1a3d8c7feb25085bebb5bee83ea37a6/docs/research/wayfinder/2026-10-01-native-docking.md
[platform-evidence]: https://github.com/monkey30440/mobile_base/issues/2#issuecomment-5929647474
[SAS]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_util/include/nav2_util/simple_action_server.hpp
[BT]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_behavior_tree/include/nav2_behavior_tree/bt_action_server_impl.hpp
[Navigator]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_core/include/nav2_core/behavior_tree_navigator.hpp
[Pose]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_bt_navigator/src/navigators/navigate_to_pose.cpp
[Engine]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_behavior_tree/src/behavior_tree_engine.cpp
[BTNode]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_behavior_tree/include/nav2_behavior_tree/bt_action_node.hpp
[Controller]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_controller/src/controller_server.cpp
[DockServer]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_docking/opennav_docking/src/docking_server.cpp
[DockPlugin]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_docking/opennav_docking_core/include/opennav_docking_core/non_charging_dock.hpp
[DockNavigator]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_docking/opennav_docking/src/navigator.cpp
[DDC]: https://github.com/ros-controls/ros2_controllers/blob/aacd842600a09d556b983ac3d53a0983e9ebcbb1/diff_drive_controller/src/diff_drive_controller.cpp

[Client]: https://github.com/ros2/rclcpp/blob/566076f19510f104126815e39eddf3d1ac81c2b6/rclcpp_action/include/rclcpp_action/client.hpp
[Server]: https://github.com/ros2/rclcpp/blob/566076f19510f104126815e39eddf3d1ac81c2b6/rclcpp_action/include/rclcpp_action/server.hpp
[GoalHandle]: https://github.com/ros2/rclcpp/blob/566076f19510f104126815e39eddf3d1ac81c2b6/rclcpp_action/include/rclcpp_action/server_goal_handle.hpp

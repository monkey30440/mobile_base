# Native local docking：Jazzy 1.3.12／1.3.13 能力邊界

研究日期：2026-10-01。對應 [查明 native local docking 能力邊界](https://github.com/monkey30440/mobile_base/issues/5)；範圍依 [Wayfinder 全系統決策地圖](https://github.com/monkey30440/mobile_base/issues/1) 的 Notes。

本研究是 reuse／gap 證據，不批准架構、介面、參數或 implementation。產品前提是 explicit near-target task、外部 Vision observation、mobile_base 負責物理對準及結果；充電、影像處理與 mission orchestration 不在範圍。現行 source/config/test 是現況證據，不構成新架構約束。[產品前提][map]

## 結論

- **Native framework 可用於不充電、無 dock instance database 的 local docking。** `DockRobot` direct-pose goal、`NonChargingDock`／`SimpleNonChargingDock` 以及 `odom` fixed frame 都已存在。關閉 staging navigation 是 caller flag；不等於 server 已驗證 near-target 起點。[Action][action]、[plugin API][noncharging]、[database][db]、[server][server]
- **預設 plugin 不是完整「精準 position＋yaw＋已停止」完成契約。** position 模式只比 XY 距離；stall 模式只比指定 joints 的平均速度與 effort。server 在 plugin 完成後發布零速度並立刻回成功，沒有停止確認。[SimpleNonChargingDock][simple]、[server completion][server]
- **Local frame 不必然需要 AMCL；目前 launch 的 lifecycle 分組卻把 docking 與 global navigation 綁在一起。** collision checking 另需要 local costmap／footprint／TF，不能只移動 docking lifecycle 就推論已獨立。[controller][controller]、[current launch][launch]、[lifecycle manager][lifecycle]
- **Native action 的 cancel／preemption 不提供跨 capability 的 chassis ownership 交接。** same-server goal replacement 與另一 capability 取得 owner 是不同議題；前者語義尚待決定。本研究只確認沒有 Nav／Dock／Teleop／maintenance 的共同 owner 或 physical-stop handoff 保證。[SimpleActionServer][sas]、[current launch][launch]
- **現有 release 與 dev 是不同版本。** release 1.3.12 的未知 direct `dock_type` 路徑有 null dereference 風險；1.3.13 已補驗證。這是 source inspection，不是 crash reproduction。[1.3.12][server]、[1.3.13][server13]

## 1. 版本、來源與證據強度

Repository 固定基點：`8d17bdb6239702d8e7ec9a2cd170b696a6045bef`。Dockerfile 安裝未鎖版的 `ros-jazzy-navigation2`／`ros-jazzy-nav2-bringup`；`navigation2` metapackage 依賴 `opennav_docking`／core／BT。release compose 使用可變的 `mobile_base:release` tag。[Dockerfile][docker]、[metapackage][meta]、[release compose][compose]

本 session 的唯讀 Docker inventory／package database observation：沒有運行中的容器；現存 `mobile_base` 開發容器為 stopped。讀取既存 dev 的 `/var/lib/dpkg/status`；另一 native-motion research agent 從 never-started temporary container 讀取 release image 同一檔案後移除 temporary container。以下記錄是本機既存資產，不代表機器人當下選用哪個 runtime。

| 證據 | 現存 release image | 現存 stopped dev container |
|---|---|---|
| Image ID | `sha256:b29858229cd8feddbe5fa4d7b5ab2e10433599d2612f31f2386e23efb727e7b0` | `sha256:d8ae0269cc7b1c97c9d20ecc2d98b10110d318bb19d0974b82b2167054892186` |
| `ros-jazzy-opennav-docking` | `1.3.12-1noble.20260614.103430` | `1.3.13-1noble.20260903.010126` |
| `ros-jazzy-opennav-docking-core` | `1.3.12-1noble.20260614.103147` | `1.3.13-1noble.20260902.211504` |
| `ros-jazzy-nav2-msgs` | `1.3.12-1noble.20260612.162307` | `1.3.13-1noble.20260902.193503` |
| `ros-jazzy-nav2-util` | `1.3.12-1noble.20260614.074750` | `1.3.13-1noble.20260902.195022` |
| `ros-jazzy-navigation2` | `1.3.12-1noble.20260615.092426` | `1.3.13-1noble.20260907.041002` |
| Architecture／status | `arm64`／`install ok installed` | `arm64`／`install ok installed` |

Primary observation 方法：`docker ps -a`、限定欄位的 `docker inspect`、package database copy；沒有啟動產品、建置、ROS launch 或硬體操作。原始 package observation 位於本 session `/tmp/wayfinder-native-motion-{release-,}dpkg-status`；上表將相關欄位保存在研究資產內。這不是 binary checksum／overlay／實際執行程序的完整 provenance attestation。

上游 source 固定為官方 tag [1.3.12／`6be3614…`][tag12] 與 [1.3.13／`f4108e5…`][tag13]。ROS distribution metadata revision `6362c48…` 列出 navigation2 release `1.3.13-1`，含 docking packages；它證明套件歸屬，不能回推舊映像版本。[rosdistro][distro]

本文未特別標版時以 **1.3.12** source 為 citation；逐檔比對確認 Action、SimpleNonChargingDock、PoseFilter、Navigator、DockDatabase、NonChargingDock、SimpleActionServer、costmap subscribers/checker、lifecycle manager 在兩個 tag 相同。相關 server 差異只有 `generateGoalDock` 的 plugin null guard；controller 1.3.13 新增 rotate-to-heading helper／參數，`approachDock` 仍呼叫原本 `computeVelocityCommand`，沒有因此新增 yaw success criterion。[server][server]、[server 1.3.13][server13]、[controller 1.3.13][controller13]

GitNexus 已嘗試 `list_repos`／`query`：索引落後 4 commits，query 因 storage version 42／40 不相容失敗；dependency graph analysis **未完成**。本研究直接核對 source；沒有修改產品 symbol，亦未重建共享索引。

## 2. Goal、staging 與 database：能力不等於 caller 契約

| 項目 | Native 行為 | 留給 caller／後續決策的邊界 |
|---|---|---|
| Direct target | `use_dock_id=false` 使用 `dock_pose` 與 plugin `dock_type`；唯一 plugin 時 type 可空。 | Action 仍需有效 frame、pose、plugin；不必建立 dock instances。 |
| Database | 未設定 `docks`／`dock_database` 時 configure 可成功；至少一個 dock plugin 必須可載入。 | 「不用 database」是不用 persistent dock instances，framework 內部仍有 plugin registry／DockDatabase utility。 |
| Staging flag | `navigate_to_staging_pose` 預設 true。false 分支直接跳過 `goToPose`，與 tolerance 是 OR 條件。 | false **不會拒絕遠離 staging 的起點**；near-target feasibility 不是 native admission guarantee。 |
| Staging TF | 即使 flag false，server 仍先取得 staging pose 與該 frame 內的 robot pose。 | 無效 TF 仍可失敗；不能把 flag 解讀成完全不使用 staging 資料。 |
| Staging enabled | 超過 `dock_prestaging_tolerance` 才呼叫 `NavigateToPose`；`max_staging_time` 控制此段導航。 | 這條路徑帶入 global navigation 的實際依賴；時間不是整個 docking timeout。 |
| Retry | `max_retries>0` 可在 approach/detection/control 失敗後用 docking controller 回 staging 再試。 | false staging flag 不禁用 retry retreat；現行 config 是 `max_retries=0`。 |

來源：[DockRobot defaults][action]、[DockDatabase][db]、[server staging/retry][server]、[Navigator][navigator]、[current parameters][params]。

官方 Jazzy configuration page 仍有「需要 docks 或 dock_database」的 note，但兩版 `getDockInstances()` 在兩者缺省時明確 warn 並 return true；direct goal 的 source 路徑才是本文「可無 dock instances」結論依據。[文件][docs]、[source][db]

Direct goal 的 `header.stamp` 不會保存在生成的 `Dock`；server 稍後以 time zero（latest TF）把初始估計轉到 fixed frame。因此 goal timestamp **不是** observation freshness contract；外部 stream 的 stamp 是另一條檢查路徑。[generateGoalDock／initial transform][server]

1.3.12 的未知 `dock_type` 可使 `findDockPlugin` 回 null，下一步 dereference `dock->plugin`；一般 exception handler 不保證攔住此類 process fault。1.3.13 在建立 Dock 前 throw `DockNotValid`，可回 `DOCK_NOT_VALID=902`。因此不能把較新版的有序錯誤回報當成 release 1.3.12 保證。[registry lookup][db]、[1.3.12 direct goal][server]、[1.3.13 guard][server13]

## 3. 外部 observation：時間、TF、filter、offset

`SimpleNonChargingDock` 以 depth 1 的 `PoseStamped` subscription 接收 `detected_dock_pose`，callback 保存最後到達訊息；它不讀 images。`getRefinedPose(..., id)` 的 id 參數未使用。stream 沒有 task ID、tag identity、covariance、confidence 或「lost target」欄位；需要辨認哪個物件／哪次任務時，不能從現有 message 自動取得。[plugin implementation][simple]

| 檢查／處理 | 已有機制 | 沒有因此保證的事 |
|---|---|---|
| Freshness | 比較 ROS `now - header.stamp > external_detection_timeout`。 | 不要求 observation 晚於本次 goal；沒有 future-stamp、單調性、sequence 或 numeric-validity 的明確 admission checks。future stamp 若不需跨 frame TF，可能通過 age comparison。 |
| TF | 不同 frame 時，先等待 observation stamp 的 TF（最多 0.2 s），再轉入 server fixed frame。 | 依賴 producer clock 與 TF history 一致；同 frame 分支不執行這個 transform check。 |
| Update | initial perception 等待至 `initial_perception_timeout`；approach 每圈取 refined pose，false 變 `FAILED_TO_DETECT_DOCK`，可能觸發 retry。 | 「有新訊息」不等於「本次拍攝的新觀察」；相同 timestamp 的樣本仍可重複處理。 |
| Filtering | 位置 exponential filter、orientation slerp；sample gap 超 timeout 或 frame 改變時 reset。`coef<=0` 直接取新值，其餘位置式為 `(1-coef)*old + coef*new`。 | 不做 outlier／identity rejection；相同 stamp 可再次濾波。沒有每次 goal 自動重建 filter 的程式路徑。 |
| Orientation／offset | observation 先轉 fixed frame、filter，再合成配置的 rotation、移除 roll/pitch；依所得 yaw 旋轉 x/y translation，z 設 0。 | offset 不是任意 camera extrinsic 的替代；不是直接在未旋轉 optical axes 加 x/y。 |

來源：[SimpleNonChargingDock][simple]、[PoseFilter][filter]、[initial perception/approach][server]。

現行 config 的 `translation_x=-0.7` 與零 rotation 明確標成待實機核對；freshness=2 s、filter coefficient=0.1 也只是現況。camera/target axes、sensor→base TF、目標位置代表 tag 還是期望 base pose、拍攝時間戳與可接受延遲都尚未成為外部契約。這些事實不能由成功收到 PoseStamped 或靜態座標圖消除。[current config][params]、[產品前提][map]

## 4. Non-charging completion 與 plugin seam

`NonChargingDock` 是正式 plugin API：`isCharger()` 固定 false；仍提供 lifecycle hooks、`getStagingPose`、`getRefinedPose`、`isDocked`。server 的非充電分支跳過 charging wait；不需要假造 battery status 來成功。plugin loader 的 base type 仍名為 `ChargingDock`，不表示實際必須充電。[API][noncharging]、[loader][db]、[server][server]

| 候選完成證據 | SimpleNonChargingDock／framework 實際意義 |
|---|---|
| XY position | `hypot(base.x-dock.x, base.y-dock.y) < docking_threshold`；預設 0.05 m。這是 TF／估計座標條件。 |
| Yaw | `isDocked()` 不比較 yaw；`undock_angular_tolerance` 用於 undock／retry staging，不是 dock final yaw tolerance。 |
| Stopped | position 模式不讀 velocity；server 的零指令沒有 feedback confirmation、dwell 或 stop deadline。 |
| Stall | 選用 joint-state 模式時，比指定 wheels 平均 absolute velocity／effort；不是 body stopped，也不證明已對正目標。 |
| Success race | approach 先 `isDocked()`，再 cancel/preemption，再刷新 observation；因此成功分支可使用上一筆 pose，且在同圈先於 cancel/freshness check。 |

來源：[completion plugin][simple]、[approach／undock][server]。

**Extension fit：** plugin 能界定 refined target 與「已 docked」判定，適合評估 target policy／position-yaw criterion 的擴充範圍；這是既有 seam，尚未批准自訂 plugin。[NonChargingDock interface][noncharging]

**Extension limit（source-derived inference）：** 不能只把「已停止一段時間」加進 `isDocked()` 就宣稱完成 stop handshake。當它回 false，server 仍跑 approach controller；target 又被向前延伸 0.25 m，沒有 pose-reached→zero→等待新 stop evidence 的獨立 hook。plugin API 也沒有跨 capability lease／release callback。是否需要 plugin、caller coordination、限定 upstream extension 或其他方案，要由後續契約決策評估；本文不選擇。[approach loop][server]、[plugin API][noncharging]

## 5. Local dependencies、costmap 與 lifecycle

Native local approach 的必要資料是 base↔fixed TF、可轉入 fixed frame 的 initial target／observation，以及所選 collision checking inputs。預設 fixed=`odom`、base=`base_link`；docking server 沒有直接訂閱 AMCL 或要求 `map` frame。Navigator client 在 lifecycle activate 建立，但只有 staging navigation 分支呼叫 `NavigateToPose`。因此「local docking 必須 global-localized」不是 framework 的固有要求。[server][server]、[Navigator][navigator]

目前 controller 計算使用 target pose／TF，不從 odometry topic 讀 measured twist；`odom` 在此首先是 frame，不能由名字推論已有速度 freshness 或 stopped check。[controller][controller]、[plugin completion][simple]

| Collision／lifecycle 面向 | 原生保證與限制 |
|---|---|
| Collision enabled | 訂閱 `local_costmap/costmap_raw` 與 `local_costmap/published_footprint`，投影 trajectory 後 footprint collision check；沒有建立自己的 costmap。 |
| TF／frame | projected poses 轉到 fixed frame 後，XY/yaw 直接送 checker。必須讓該 frame 的數值語義與 costmap 一致；沒有額外把 projected pose 轉到 costmap header frame 的步驟。 |
| Missing data | 未收到 costmap、無可用 footprint／TF、越界或 checker 錯誤可回 collision false，導致 control failure。 |
| Stale data | CostmapSubscriber 保存已接收 map；此路徑沒有明確 map-age deadline／`Costmap2DROS::isCurrent()` gate。收到過 map 不等於持續更新。footprint TF 可另行失敗。 |
| Dock exclusion | `dock_collision_threshold` 排除靠近 controller target 的部分 trajectory；該 target 已向前延伸 0.25 m，不能直接把 exclusion 解讀為相對原始 tag 的半徑。 |
| Collision disabled | 不讀 collision checker，但 controller 仍查 base↔fixed TF 並產生 trajectory；不是無 TF 模式。 |

來源：[controller][controller]、[costmap subscriber][costmap]、[topic collision checker][checker]、[footprint subscriber][footprint]。

官方 Jazzy 文件建議不需實體接觸時將 collision exclusion threshold 設為 0；現行配置仍是 0.3。這是待契約評估的差異，本文不改參數，也不認定該檢查足以涵蓋實際碰撞風險。[Jazzy configuration][docs]、[current parameters][params]

現行 local costmap 是 `odom` rolling window；native controller server 擁有／configure／activate／deactivate 該 costmap。現行 launch 把 controller、planner、route、BT navigator、docking 放同一 lifecycle manager；manager 的 managed-node bond failure 會 reset 同組 nodes。**推論：** local docking 的數學路徑雖不需要 AMCL，現行啟停／故障隔離仍與 global group 耦合；拆組是否足夠還取決於 local costmap 的持續供應與 readiness。[current config][params]、[ControllerServer][navcontroller]、[launch][launch]、[LifecycleManager][lifecycle]

## 6. Cancel、failure、success 與 command release

| 路徑 | Source 可支持的結果 | 不能升級成的保證 |
|---|---|---|
| 普通 noncharging success | approach true→waitForCharge 立即 true→publishZeroVelocity→`succeeded_current`。 | 結果送出前已 physical stopped、已停止 dwell、已釋放 chassis owner。 |
| Approach／retry cancel | control loop 看到 cancel 後返回，server 發零並 `terminate_all`。 | 固定時間內一定停車；callback／TF 等待會影響反應時間。 |
| Initial perception cancel | perception function 返回，後續 approach 才處理；若 `isDocked` 先成立，存在 success-vs-cancel ordering race。 | cancel request accepted 必定產生 canceled terminal。 |
| Staging cancel | Navigator 發 `NavigateToPose` cancel、至多等待 cancel future 1 s，throw `FailedToStage`；server catch 發零並 terminate。 | 已等到 nested navigation 的 terminal result 或其 publisher 完全靜止。 |
| Detected failure | catch 分成 DB／invalid dock／stage／detect／control／charge／unknown，發零，terminate current。 | process crash／kill／middleware 失敗仍必定送達零；所有原因都有 error text。 |
| Entry early return | server inactive，或一進入就已 cancel，直接返回／terminate；這些路徑不呼叫 publishZeroVelocity。 | 每一種 terminal 一律經過相同 stop sequence。 |
| Lifecycle deactivation | 先停 action server，再 deactivate plugin／Navigator／velocity publisher。SimpleActionServer 可先 terminate handle 再繼續等待 execute callback 返回。 | terminal status 本身等同 command quiescence。 |

來源：[DockingServer][server]、[Navigator cancel][navigator]、[SimpleActionServer deactivate/terminate][sas]。

`terminate()` 對 canceling handle 回 CANCELED，否則 ABORTED；`DockRobot.Result.success` 的 message default 是 true，但 server 正常開始會設 false，某些 default-result termination 路徑未沿用它。因此 consumer 應閱讀 action terminal status 及 payload，而不能只看 bool。Action 有 `error_msg` 欄位，但這兩版 docking catch 主要寫 code/log，不能假設都有非空字串。[Action][action]、[server][server]、[SimpleActionServer][sas]

同一 DockRobot server active 時，SimpleActionServer 接受新 goal、放 pending slot、觸發 preemption；不提供 busy-reject policy。這是 **same-owner goal semantics**，尚未決定是否允許。另一方面，dock／undock 的 mutex 只保護該 server 執行，無法約束其他 navigation／teleop publishers；現行 launch 甚至把 controller 與 docking 都 remap 到同一 chassis cmd topic。**跨 capability 排他與 cancel＋stop 後 owner change** 是使用者已要求、native docking 尚未提供的契約。[SimpleActionServer][sas]、[server mutex][server]、[current remapping][launch]、[產品前提][map]

`publishZeroVelocity()` 只建立帶 `now()` timestamp 的 zero TwistStamped；TwistPublisher 依 `enable_stamped_cmd_vel` 選 Twist 或 TwistStamped（Jazzy 此 wrapper 預設 false；現行配置 true）。node/publisher 在 task 完成後仍可 active；零指令不會撤銷另一 publisher 的輸出權。[zero publication][server]、[TwistPublisher][twist]、[config][params]

## 7. 現有證據可重用到哪裡

現存 `test_apriltag_docking_integration.py` 用 native server、synthetic TF、10 Hz fresh observation、direct pose／no staging／zero retries，等待 accepted→feedback→canceled；collision checking 關閉。它沒有 assert 成功時 yaw／position、停止 dwell、zero command 到 controller、實體停止、obstacle handling 或 release ownership。本文只讀測試內容，沒有重新執行；既有 pass record 即使可重用，也只能支持原本觀察範圍。[test source][test]

本研究完成的是 **source／metadata validation**；沒有新增 software runtime validation 或 hardware validation。下列仍需日後獲准的契約與驗證，不能以 reference implementation 或參數值當成實測結論：

1. 實際 release selection、binary／overlay provenance；把所選版本與可重現 image 對應起來。
2. 目標座標定義、sensor extrinsic、target axes／offset sign、拍攝 stamp／clock sync、可接受 observation age 與失鎖行為。
3. 可接受的起始距離／角度／視野範圍，位置與朝向的可達精度，以及 filter／控制／底盤停止延遲的共同影響。
4. 在 success／cancel／failure 與目標遺失時，控制器 feedback、body motion 與 ownership handoff 的真實序列；zero command 或 wheels stopped 不自動證明 body stopped。
5. local costmap、footprint、obstacle source 停更／TF 異常下的實際反應；以及 near-target collision exclusion 的可接受性。

上述未定項分別交由 [Vision docking frame 與完成契約](https://github.com/monkey30440/mobile_base/issues/10)、[單一 chassis authority 與停止契約](https://github.com/monkey30440/mobile_base/issues/7)、[capability lifecycle 與失敗隔離](https://github.com/monkey30440/mobile_base/issues/11)、[operator-managed release 契約](https://github.com/monkey30440/mobile_base/issues/13) 決定；本 research ticket 可在能力／限制問題回答後結束，不代表這些契約已被 agent 代答。

## Primary sources

以下 source links 固定 commit；官方 rendered docs 只作輔助，遇到 branch／cache 差異以指定 source 為準。

[map]: https://github.com/monkey30440/mobile_base/issues/1
[tag12]: https://github.com/ros-navigation/navigation2/commit/6be3614013ec586051b86c97b919b293281490fe
[tag13]: https://github.com/ros-navigation/navigation2/commit/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501
[distro]: https://github.com/ros/rosdistro/blob/6362c48a5abf60d9ae463d45267988944dbe4af9/jazzy/distribution.yaml#L6893-L6953
[docker]: https://github.com/monkey30440/mobile_base/blob/8d17bdb6239702d8e7ec9a2cd170b696a6045bef/Dockerfile
[compose]: https://github.com/monkey30440/mobile_base/blob/8d17bdb6239702d8e7ec9a2cd170b696a6045bef/compose.release.yaml
[launch]: https://github.com/monkey30440/mobile_base/blob/8d17bdb6239702d8e7ec9a2cd170b696a6045bef/src/mobile_base_navigation/launch/navigation.launch.py
[params]: https://github.com/monkey30440/mobile_base/blob/8d17bdb6239702d8e7ec9a2cd170b696a6045bef/src/mobile_base_navigation/config/nav2_params.yaml#L161-L295
[test]: https://github.com/monkey30440/mobile_base/blob/8d17bdb6239702d8e7ec9a2cd170b696a6045bef/src/mobile_base_navigation/test/test_apriltag_docking_integration.py
[meta]: https://github.com/ros-navigation/navigation2/blob/6be3614013ec586051b86c97b919b293281490fe/navigation2/package.xml
[action]: https://github.com/ros-navigation/navigation2/blob/6be3614013ec586051b86c97b919b293281490fe/nav2_msgs/action/DockRobot.action
[server]: https://github.com/ros-navigation/navigation2/blob/6be3614013ec586051b86c97b919b293281490fe/nav2_docking/opennav_docking/src/docking_server.cpp
[server13]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_docking/opennav_docking/src/docking_server.cpp#L374-L394
[simple]: https://github.com/ros-navigation/navigation2/blob/6be3614013ec586051b86c97b919b293281490fe/nav2_docking/opennav_docking/src/simple_non_charging_dock.cpp
[noncharging]: https://github.com/ros-navigation/navigation2/blob/6be3614013ec586051b86c97b919b293281490fe/nav2_docking/opennav_docking_core/include/opennav_docking_core/non_charging_dock.hpp
[filter]: https://github.com/ros-navigation/navigation2/blob/6be3614013ec586051b86c97b919b293281490fe/nav2_docking/opennav_docking/src/pose_filter.cpp
[db]: https://github.com/ros-navigation/navigation2/blob/6be3614013ec586051b86c97b919b293281490fe/nav2_docking/opennav_docking/src/dock_database.cpp
[navigator]: https://github.com/ros-navigation/navigation2/blob/6be3614013ec586051b86c97b919b293281490fe/nav2_docking/opennav_docking/src/navigator.cpp
[controller]: https://github.com/ros-navigation/navigation2/blob/6be3614013ec586051b86c97b919b293281490fe/nav2_docking/opennav_docking/src/controller.cpp
[controller13]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_docking/opennav_docking/src/controller.cpp
[sas]: https://github.com/ros-navigation/navigation2/blob/6be3614013ec586051b86c97b919b293281490fe/nav2_util/include/nav2_util/simple_action_server.hpp
[costmap]: https://github.com/ros-navigation/navigation2/blob/6be3614013ec586051b86c97b919b293281490fe/nav2_costmap_2d/src/costmap_subscriber.cpp
[checker]: https://github.com/ros-navigation/navigation2/blob/6be3614013ec586051b86c97b919b293281490fe/nav2_costmap_2d/src/costmap_topic_collision_checker.cpp
[footprint]: https://github.com/ros-navigation/navigation2/blob/6be3614013ec586051b86c97b919b293281490fe/nav2_costmap_2d/src/footprint_subscriber.cpp
[lifecycle]: https://github.com/ros-navigation/navigation2/blob/6be3614013ec586051b86c97b919b293281490fe/nav2_lifecycle_manager/src/lifecycle_manager.cpp
[navcontroller]: https://github.com/ros-navigation/navigation2/blob/6be3614013ec586051b86c97b919b293281490fe/nav2_controller/src/controller_server.cpp
[twist]: https://github.com/ros-navigation/navigation2/blob/6be3614013ec586051b86c97b919b293281490fe/nav2_util/include/nav2_util/twist_publisher.hpp
[docs]: https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/core_servers/configuring_docking_server/

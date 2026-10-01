# Native 底盤與本地運動能力邊界研究

研究日期：2026-10-01。範圍：ROS 2 Jazzy、現存 development container／release image 的套件 metadata、對應 upstream release source，以及 repository commit `8d17bdb6239702d8e7ec9a2cd170b696a6045bef`。

研究票：[查明 native 底盤與本地運動能力邊界](https://github.com/monkey30440/mobile_base/issues/3)。上位意圖：[Wayfinder — mobile_base 最小完整 AMR 系統的全系統決策地圖](https://github.com/monkey30440/mobile_base/issues/1)。

本文件是 fact／fit／gap／options 的研究證據，不是 Architecture、Subsystem Design、implementation plan 或批准的停止契約。舊 spec、現行程式、舊 READY 設計及 implementation plan 不被提升為新設計的要求。

## 1. 調查結論與證據分級

- **已確認的 native fit：** ros2_control 有 hardware/controller lifecycle 與 command-interface claim；DDC 有 differential-drive conversion、wheel-feedback odometry、limits、command-age timeout；JSB/RSP 有 joint state／robot kinematic TF；robot_localization 有本地感測融合與可配置 TF authority。[C48-resource] [D42] [JS42] [RSP] [RL-doc]
- **已確認的邊界：** controller interface claim 不是多個 `cmd_vel` publisher 的 task ownership。twist_mux 的 priority/timeout/lock、topic_tools 的選路服務，也沒有完整提供「第二位 owner 被拒絕，保留既有任務；取消及停止交接後才切換」的契約。[C48-resource] [D42] [Mux] [Mux-handles] [Topic-mux]
- **版本不可混用：** 本機 development 的 ros2_control/DDC 為 4.48.0/4.42.1，現存 release image 為 4.45.2/4.40.1；DDC `timeout=0` 確有語義差异。兩個集合均不能只寫成「Jazzy 行為」。見 §2、§4。[D40] [D42]
- **停止證據不可跳級：** zero command、controller inactive、hardware inactive、M1 stop/disable response、wheel feedback zero、physical stopped 是不同觀察；native API 沒有把它們自動等價化。見 §7。[D42] [C48-hardware] [M1-hardware] [M1-driver]
- 下文 **F** 表示指定版本的 source/API 事實；**O** 表示本次只讀環境觀察；**I** 表示 source 推論、尚未 runtime 驗證；**U** 表示未解的 runtime／硬體事實。沒有 build、ROS launch、hardware transaction 或 physical test。

## 2. 實際可觀察版本與 provenance

### 2.1 環境觀察（O，2026-10-01）

`docker ps` 沒有 running container。既有 `mobile_base` development container 停止中，狀態 `Exited (137)`；這不代表可推論停止原因或車體狀態。

| 對象 | 精確身分 |
|---|---|
| Existing development container | `764664f480074dfeef753aa3d8cfd035cf653165c1fa66a6a5d56e78e65ad8d3` |
| Container creation time | `2026-09-17T01:22:25.18239142Z` |
| Development image | `sha256:d8ae0269cc7b1c97c9d20ecc2d98b10110d318bb19d0974b82b2167054892186` |
| Existing `mobile_base:release` image | `sha256:b29858229cd8feddbe5fa4d7b5ab2e10433599d2612f31f2386e23efb727e7b0` |
| Release image creation / RepoDigests | `2026-09-07T11:05:21.465861056+08:00` / `[]` |

Development metadata 由 `docker cp mobile_base:/var/lib/dpkg/status ...` 讀取。Release metadata 由上述 image ID 建立暫存、**從未 start**、無 devices／bind mounts、entrypoint `/bin/false` 的 container，copy 同一檔後只移除該暫存 container。暫存 ID `a8c42d5e68caf61575b52178e253b67359d6dc446ad593dc7f3c49fb174c5181`，已移除。

下表是 dpkg 的 `install ok installed` 記錄（arm64），不是 apt candidate，也不是由 Dockerfile 猜測的版本。原始 metadata 的 SHA-256：development `6bef6f5d07d2849100940e711412e1014e89244f7657f3dac7c50fb429643d63`；release `3b77943f4f1d7f2aa143bbbec4bb033eaddf7008f9b9d17978af8862cc507517`。

| Debian package | Development container | Release image |
|---|---|---|
| ros-jazzy-controller-manager | 4.48.0-1noble.20260904.013127 | 4.45.2-1noble.20260612.162541 |
| ros-jazzy-hardware-interface | 4.48.0-1noble.20260904.011033 | 4.45.2-1noble.20260612.124024 |
| ros-jazzy-diff-drive-controller | 4.42.1-1noble.20260904.012156 | 4.40.1-1noble.20260614.101845 |
| ros-jazzy-joint-state-broadcaster | 4.42.1-1noble.20260904.013606 | 4.40.1-1noble.20260612.131137 |
| ros-jazzy-robot-state-publisher | 3.3.3-3noble.20260124.193510 | 3.3.3-3noble.20260124.193510 |
| ros-jazzy-robot-localization | 3.8.3-1noble.20260902.170723 | 3.8.3-1noble.20260614.073224 |
| ros-jazzy-nav2-controller | 1.3.13-1noble.20260903.005511 | 1.3.12-1noble.20260614.102844 |
| ros-jazzy-nav2-velocity-smoother | 1.3.13-1noble.20260902.211442 | 1.3.12-1noble.20260614.103113 |
| ros-jazzy-opennav-docking | 1.3.13-1noble.20260903.010126 | 1.3.12-1noble.20260614.103430 |
| ros-jazzy-launch | 99.0.0-0noble | 99.0.0-0noble |
| libmodbus5 | 3.1.10-1ubuntu1 | 3.1.10-1ubuntu1 |
| ros-jazzy-twist-mux / ros-jazzy-topic-tools | 未在 dpkg 登記 | 未在 dpkg 登記 |

**U：** image 存在及 package metadata 不能證明此刻實際部署選哪個 image、是否有 overlay／local patch、執行時參數、或 binary 與 workspace source 一致。本次沒有 runtime，所以不宣稱已驗證整條 live graph。

**F：** current [Dockerfile] 未對 ROS apt packages 指定版本，也未用 base image digest；base image tag 是 `nvcr.io/nvidia/isaac/ros:isaac_ros_740c8500df2685ab1f4a4e53852601df-arm64-jetpack`。`compose.release.yaml` 使用可變 tag `mobile_base:release`。因此未來 rebuild 不能靠檔案本身重建本表的 exact dependency set。[Dockerfile] [Compose-release]

### 2.2 本研究的 upstream source pin

| 元件／release | 對應 commit（tag 查得，2026-10-01） |
|---|---|
| ros2_control 4.45.2 | `4324cabf03a1371951f0a039d239fcf09f563e54` |
| ros2_control 4.48.0 | `cdbc1127521074c2c5d19b4af2b73591e69d762b` |
| ros2_controllers 4.40.1 | `31015e0aa7ce9d0853a88d5fc2fe50f0e583ba5c` |
| ros2_controllers 4.42.1 | `aacd842600a09d556b983ac3d53a0983e9ebcbb1` |
| robot_state_publisher 3.3.3 | `e0f77e62457ae01f8dbf3b5c4cc62d15fa36dfad` |
| robot_localization 3.8.3 | `9596c40abd26cd10f80ee1a1325176bc38b4e0bf` |
| twist_mux 4.5.0（候選、未安裝） | `136394c1bf35b69fea5847ce00d75a1f44c8ab42` |

下文固定版本 source 連結優先於會持續變動的 Jazzy docs。ROS distribution registry 當日列 twist_mux `4.5.0-1`、topic_tools `1.3.4-1`；registry 指向的 `rolling` source branch 不代表應採用 rolling tip。[Registry] [Mux] [Topic-mux]

## 3. ros2_control lifecycle 與資源排他

**F（4.45.2 與 4.48.0）：** `HardwareComponent::read()` 在 INACTIVE 或 ACTIVE 都會觸發 plugin read；`write()` 只在 ACTIVE 觸發，sensor 不 write。UNCONFIGURED 等不需動作的狀態直接返回。因此「inactive 不會 read」錯誤；「這兩版 inactive 仍會呼叫 plugin write」也錯誤。[C45-hardware] [C48-hardware]

**來源衝突：** 4.48.0 的 lifecycle 文件仍留有「all command interfaces ... will be written」的舊 note；exact code 已採 ACTIVE-only write。本研究依兩個已安裝版本的程式路徑判讀，不把文件那段 note 當有效 binary 保證。[C48-lifecycle] [C48-hardware]

**F（4.48.0；相關 4.45.2 路徑亦檢查）：** controller manager 可指定 hardware 初始 unconfigured／inactive；未列入者走 activation。ResourceManager 對 command interface 做 claim，已被 claim 的介面再次 claim 會拋錯；state interface 可以被 broadcaster／controller 讀取。controller/hardware read/write error 的管理路徑會轉錯誤處理並停用相關 controller；成功進入 lifecycle state 是 callback/framework 的結果，不是外部 stop sensor 的結果。[C48-manager] [C48-resource] [C45-resource]

**I：** 同一 manager 中兩個 controller 爭同一 wheel command interface 可由 native resource claim 防止；兩個 ROS publisher 向**同一個** DDC topic 寫入則仍是同一 controller 的輸入，不會觸發第二個 resource claim。另一 process 直接開 serial 更不在該 ResourceManager 的所有權範圍。[C48-resource] [D42] [M1-driver]

**現行整合 gap（I，repo base）：** `M1Hardware::on_configure()` 成功後仍 `is_active_=false` 且 `has_valid_state_=false`；`read()` 遇 inactive 直接 ERROR。native INACTIVE read 因而與 plugin 假設不一致。這是 source-level 相容性問題，尚未用 fake hardware/native ResourceManager runtime 重現，不在本票修正。[M1-hardware] [C48-hardware]

**現行整合 gap（F/I）：** `on_deactivate()` 發送 `JG 0`、等待固定時間、發送 `SVOFF`；即使 stop/disable 失敗仍 best-effort 後返回 SUCCESS。註解的 zero-RPM confirmation delay 實際沒有「輪速達零」判定；不能由 successful lifecycle transition 宣稱 servo confirmed disabled 或 physical stopped。[M1-hardware]

可供後續決定的原生切分：hardware lifecycle 管連線／資源／device enable 邊界，controller lifecycle 管演算法與 command interface，任務准入／取消／交接另有未覆蓋責任。這是 API 能力分類，不指定新 module 或中央 manager。[C48-hardware] [C48-resource] [Actions]

## 4. DDC 訊息、時間、timeout 與 odometry

**F（4.40.1、4.42.1）：** topic input 是 `geometry_msgs/msg/TwistStamped`，`~/cmd_vel`；只取 `linear.x`、`angular.z`；body twist 轉左右輪 velocity interfaces。這兩份 parameter schema 均無 `use_stamped_vel`。現行 YAML 的 `use_stamped_vel: true` 不能作為這兩版的 type-selection 契約；parameter override 是否被容許保留也不等於會控制行為。[D40] [D42] [D40-params] [D42-params] [Control-config]

**F：** 非 chained mode 的 callback 僅在 subscriber active 時接收；zero header stamp 會被改成 node `now()`；以 `now - source_stamp` 過濾太舊命令。future stamp 的負 age 可通過這段條件，沒有來源 identity、lease 或 future-skew 上限檢查。[D40] [D42]

| command-age 行為 | 4.40.1（release image） | 4.42.1（development） |
|---|---|---|
| 正值 timeout | update 時計算 `time - header.stamp > timeout`，超過後 reference 置零 | 同樣按來源 stamp 的 age 判定 |
| `timeout=0` | callback 特例接受訊息，但 update 仍判 `age > 0` 並置零 | callback 與 update 都將 0 視為禁用 timeout |
| timeout 後 | 零 reference 仍通過 speed limiter，再換算輪命令 | 相同；不等於立即實體煞停 |
| invalid finite check | 非 finite 值不更新 reference；不是「收到 invalid 立即停」 | 相同 |

以上直接比較 [D40] 與 [D42]；`0.5 s` 是兩版 parameter default，**不是本研究批准的產品值**。current source YAML 是 `3600.0 s`（一小時），不是該 default。這是現況與 gap，不推論操作者有意要求一小時殘留速度。[D40-params] [D42-params] [Control-config]

**F/I：** timeout 依賴 controller update 繼續執行及適當時鐘前進；controller manager/process crash 不會讓已停止執行的 timeout callback 幫設備煞停。ROS time、source stamp、future stamp／clock jump 與上下游重打 timestamp 都會改變可接受 age；本研究未驗證部署 clock 同步與 pause/jump 情境。[D42]

**F：** DDC 支援 chained reference interfaces。subscriber 的 command-age timeout 在 `update_reference_from_subscribers()`，不能假定 chained caller 也自動套用同一 topic timeout；upstream controller 所供 reference 的失效責任需另核實。[D42]

**F：** `on_deactivate()` 關閉 subscriber、`halt()` 對輪 command interfaces 寫 0、reset buffers；這是軟體 command handle 更新，不是硬體確認回覆。`cmd_vel_out`（啟用時）是受限命令，不是速度量測。[D42]

**F：** `open_loop=false` 時由 position/velocity feedback 算 odometry；`open_loop=true` 使用 command 推算。wheel geometry multipliers 是 calibration 支援，不是自動校準。DDC odom／TF 的 stamp 是 controller update `time`；輪速 rolling window 平均也不是 raw M1 RPM。[D42] [D42-params] [D-odom]

**現況（F）：** 30 Hz control、position feedback、closed-loop odometry、nominal radius 0.080 m／separation 0.5545 m、DDC `enable_odom_tf=false`。這些是 source 設定，沒有本票的硬體校準或動態接受證據。[Control-config]

## 5. JSB spawner success 與啟動證據

**F（controller_manager 4.45.2/4.48.0）：** spawner 預設 load → configure → activate；load/configure/activation service 回覆失敗會返回非零。`--inactive`、`--load-only` 會改變 exit 0 所代表的完成範圍。即使成功，exit 0 也只是該次流程結束，不能證明往後 controller 持續 active、feedback fresh 或底盤 physical stopped。[Spawner45] [Spawner48]

**F（JSB 4.40.1/4.42.1）：** activation 可以在 joint data 初始化失敗時返回 ERROR；它本身不負責 DDC 的准入。`update()` 的 JointState/DynamicJointState stamp 是 update `time`，沒有替硬體證明 acquisition time。[JS40] [JS42]

**現行 gap（F/I）：** `base_control.launch.py` 使用 `OnProcessExit(target_action=JSB spawner, on_exit=[DDC spawner])`，沒有 returncode 判斷。因此它只保證「JSB spawner process 先退出」，不能稱為「JSB 成功後才啟動 DDC」。[Base-launch] [Launch-exit] [Launch-event]

此判讀也核對 development container 實際 Python files：`on_process_exit.py`、`process_exited.py` 與 upstream launch 3.4.5 對應檔 byte-identical；雖 Debian package 標 99.0.0，這兩檔語義已直接檢查。SHA-256 依序為 `69e8ecebdf75e961f335da47245495c2510ddf5c68b866a167f025980660efff`、`dd810dc3c95b978954f03ed3347622793f2bacb33ac17295d0248ef2540f1675`。（O）

可用的 native evidence 是 spawner returncode、controller/hardware state 查詢、實際 state topic；需選哪些作啟動完成條件仍留 HITL。JSB-first 在此是目前 launch sequencing，不能由此推出它必然是 DDC 演算法的硬依賴。[Spawner48] [C48-manager] [D42]

## 6. 本地 feedback 時間與 TF authority

**F（repo base）：** M1 `MotorState`／`ExchangeResult` 沒有 device sample timestamp。active `write()` 進行 FC17 command+feedback exchange 並 cache state；下一次 `read()` 消耗該 cache，把 raw position/RPM 轉成 joint state；`read()` 並非當下再 poll。`has_valid_state_` 防止重複消耗同一 cache，但未匯出 per-sample acquisition timestamp。[M1-types] [M1-hardware] [M1-driver]

**F/I：** diagnostics 的 `motor_state_time` 是處理 successful response 後取 host steady clock；DiagnosticArray header 是 publish 時的 ROS now。driver transaction timing 是 host syscall/receive timing。它们不能倒推出 device 何時採樣、兩馬達是否同步 latch，或全部延遲上界。[M1-hardware] [M1-driver]

**I：** 所以 fresh JSB/DDC header 最多先證明 host 的發布/更新時點。經過「previous exchange cache → next read → DDC update」的輪回授不會因 stamp 更新而變成新 acquisition。若後續契約需要 fresh stopped feedback，必須說清 freshness 源自哪一層；本票不選 threshold。[JS42] [D42] [M1-hardware]

**F（RSP 3.3.3）：** URDF fixed joints 在 `/tf_static` 發布；movable joints 由 JointState position 轉成 `/tf`，使用輸入 JointState stamp。RSP 計算機構樹，不融合車體 odometry，也不從 wheel geometry 自動取得 `odom→base` 的行進量。[RSP] [RSP-code]

**F（robot_localization 3.8.3）：** `world_frame=odom` 時可發布 `odom→base_link_frame`；`world_frame=map` 模式則發布 `map→odom` 並要求其他來源供應 `odom→base`。`publish_tf` 可關閉；`base_link_output_frame` 可覆寫 child frame。這些是單一 TF 邊分工的原生開關；不是會自動偵測並阻止其他 publisher 重複發布的鎖。[RL-doc] [RL-code]

**F（3.8.3）：** filter 收到至少一筆輸入後才開始；`sensor_timeout` 後會繼續 predict，沒有 fresh correction 也可產生新的估計。output stamp 取 filter time，timeout prediction 會推進該時間；TF stamp 再加 `transform_time_offset`。因此 filtered odom/TF 持續更新不等於 wheel／IMU 仍健康或機器已物理停止。[RL-doc] [RL-code]

**現況（F）：** EKF 配置 `two_d_mode=true`、50 Hz、`sensor_timeout=0.1`、`world_frame=odom`、`base_link_frame=base_footprint`、`publish_tf=true`；融合 wheel `vx` **與 vy**（註解寫 only vx，但布林矩陣亦選 vy），以及 IMU `wz`。DDC TF 關閉，這是目前本地 TF 指派的 source 證據，不是本次重設架構的批准答案。[EKF-config] [Control-config]

**U：** hardware sign／encoder ratio／wheel radius & separation、IMU mount/bias、device clock/latency、covariance tuning、TF effective launch/namespace、ground slip 尚需各自證據。已知 left ID2/right ID1 是硬體身分；不把可調 calibration multiplier 當改動身分的許可。[Map]

## 7. 多來源 motion arbitration 與停止語義

**F（twist_mux 4.5.0，Jazzy candidate）：** 支援整體選用 Twist 或 TwistStamped；優先權 0–255、各 input timeout、Bool lock threshold。highest unmasked input 的 callback 才 forward；不是 `request owner` API。timeout 用 mux 的 ROS `now()` 與收到 callback 時記錄的時間差，**不檢查 TwistStamped header age**，forward 時保留原訊息。[Mux] [Mux-handles]

**F/I：** 高優先權來源開始送資料會勝出；目前來源過期後，仍送資料的較低優先權來源可勝出。lock 以 priority threshold 遮蔽較低優先權，並非每個 source 的 ownership token；lock timeout 到期視為 locked。鎖住所有輸入或全體 silence 不會自動產生 zero/cancel/stop confirmation；selected callback 是資料輸出路徑，diagnostic timer 不是停車器。[Mux] [Mux-handles]

**I：** 因此直接用「keyboard 高優先權」與 user 已確認的 second-owner rejection 相衝突；就算 equal priorities 或運用 locks，也未補足保持舊任務、明確拒絕新 task、取消結果、停止證據、再授權等語義。並非宣稱 mux 不可重用，而是不能把它稱為完整契約。[Map] [Mux] [Mux-handles]

**F（topic_tools 1.3.4，Jazzy candidate）：** generic mux 提供 select/list/add/delete，能選指定 topic 或 none；沒有自動高優先權 takeover。其 source 仍沒有 owner lease、任務 cancellation 或 stop feedback；default initial topic 為第一個 input，選 none 也只停止 forwarding。它是明確選路的候選 primitive，完整契約仍須外部負責。[Topic-mux]

**F（Nav2 velocity_smoother 1.3.13 作限定對照）：** 有 command smoothing、limits、command timeout 與 OPEN_LOOP/CLOSED_LOOP feedback 模式；timeout 把 command 轉零並依 limiter減速。source 的 `stopped_` 不代表 body sensor 確認，且它沒有 multi-task ownership/cancel API。此段只查 1.3.13，未把該細節套用至 release 1.3.12。[Smoother13]

**F（ROS 2 actions）：** goal admission 可接受／拒絕；cancel request 被接受後進入 CANCELING，與最終 CANCELED 及實體停止不同。任一 native task 的結果語義仍要查該 server；action protocol 不會替 chassis 寫出物理停止保證。[Actions]

| 必须分清的觀察 | 能支持的結論 | 不能單獨支持的結論 |
|---|---|---|
| 第二個 task/owner request 被拒絕 | 新請求未取得有效權利（若准入層確實實施） | 舊任务已取消或車已停 |
| 撤銷 command route／resource claim | 該路徑之後不再有效寫入 | 舊 controller／device 已消耗最後命令 |
| cancel accepted / CANCELED | server 接受取消 / server 到終態 | 車體物理停止；特定 server 的 stop 需另查 |
| zero Twist / zero wheel handle | 零速意圖或軟體 reference | 限速器、serial、driver 已完成；輪速為零 |
| DDC inactive | deactivation callback 已完成、handle 置零 | M1 收到 stop；servo disable；physical stop |
| hardware inactive | plugin transition 返回成功 | current M1 best-effort stop/disable 一定成功 |
| M1 JG0/SVOFF response | 成功的 protocol transaction 與回覆欄位 | 尚未核實的 motor state／減速距離／body stop |
| device watchdog register read | 某裝置參數讀回 | 斷線時保護有效、有效 deadline 或安全等級 |
| fresh actual RPM / wheel feedback 接近零 | 指定感測時間與解析度下的輪回授 | 無滑移／外力／底盤滑動；獨立 physical observation |
| physical stopped 觀察 | 該試驗條件下車體停住 | 所有載重、地面、故障情況都已證明 |

表中 native 範圍見 [D42] [C48-hardware] [Actions]，current M1 的 protocol/state 行為見 [M1-hardware] [M1-driver] [M1-types]。最後兩列的差異是量測對象的推論，不宣稱已完成物理測試。

**U：** M1 device watchdog effective RAM settings、fault action、firmware 行為、Servo-off 是否自由滑行/制動、停止距離與時間，本研究沒有第一方硬體試驗佐證。主機 libmodbus response timeout、DDC timeout 或成功讀 register 都不能代替 watchdog 實驗；不得新增未證實的 hardware guarantee。[M1-driver] [Map]

## 8. 可交付後續 HITL 的 fit/gap/options

| 後續要決定的責任 | 已有 native fit | 未被 native primitive 自動覆蓋的 gap／候選方向 |
|---|---|---|
| robot model / local TF | URDF+RSP、DDC/EKF TF switches | 校準及每條 TF 邊的唯一 publisher；可比較 DDC-only local odom 與 EKF fusion，依實際 accuracy requirement 決定 |
| hardware/controller lifecycle | ros2_control lifecycle、resource claim、spawner/service results | current M1 inactive-read 相容性、失敗回報與可觀察 device 狀態；不預設增加 central health authority |
| command stream exclusivity | twist_mux priorities/locks；topic_tools explicit select；controller interface claims | second-owner rejection、task preservation、取消及 stop handoff；可比較 native selector + 窄協調責任、窄 exclusive gate、或 controller resource switching + task coordination，均不得聲稱 selector 本身已完成契約 |
| command silence / process failure | DDC positive command-age timeout；可選 upstream smoother timeout | 未驗證時鐘/latency、pipeline re-stamp、host crash 與 device watchdog 的獨立邊界；未選數值或新增 lease API |
| stop evidence | command/state topics、lifecycle/service/action results、M1 returned RPM/status | fresh acquisition provenance、wheel/body stop 分級、deadline/failure disposition；哪些層足夠解除交接仍由 HITL 決定 |

候選是責任配置的比較素材；本研究不選 final arbitration、modules、states、interfaces、topic names、lease protocol 或新 manager。尤其不能把舊計畫的 takeover、READY 或數值直接帶入本次決策。[Map]

提供給 [決定 robot model、感測與本地狀態估計的單一權威](https://github.com/monkey30440/mobile_base/issues/6) 與 [決定單一 chassis authority 與停止契約](https://github.com/monkey30440/mobile_base/issues/7) 的問題：

1. 哪些 local odom／TF 性質需要 wheel+IMU fusion，哪些只是 current configuration？各資料的時間、frame、calibration 證據由誰保有？
2. 已確認「第二位 owner 必須拒絕」的前提下，所有 Navigation／Docking／Teleop／maintenance 入口如何納入同一准入責任？native selector 之外真正需要補的最小協調是什麼？
3. 取消舊任務、阻斷舊命令、停止確認各自以什麼 evidence 完成；哪種 evidence 不明時不能 grant 新 owner？先定要求，再選 primitive。
4. operator-managed V1 可接受哪些人工復原步驟？不要從 lifecycle failure 自動推導需要自動重啟／自動模式切換。
5. 下一階段選用哪個 exact image/package set 作基線，並如何消除 current plugin/native lifecycle 假設差異？

## 9. 研究完成範圍與未驗證項目

完成：兩個實存套件集合的只讀 inventory、固定 upstream source 比較、current repo source 核對、primary evidence 連結、native fit/gap 與決策問題。研究問題已有可用答案；未驗證項目有明確界線，因此可結束研究票而不替 HITL 選答案。

未做：build、unit/integration test、ROS launch、硬體 read/write、真車校準、有效 clock/QoS/frame graph、串列 second-opener 實驗、斷線/watchdog/stop/ground observation。沒有新增軟體或硬體驗證聲稱。

GitNexus 已嘗試：`mobile_base` index 為 `00c3319630216dfbc3ce349e0e5c12d22661c91c`，比調查 base 落後 4 commits；query 因 LadybugDB file version 42／engine storage version 40 不相容而不可用。dependency impact **未由 GitNexus 確定**；本研究以 exact source 核對，未重建 index 或修改既有 symbols。

## 第一方來源

[Map]: https://github.com/monkey30440/mobile_base/issues/1
[Dockerfile]: https://github.com/monkey30440/mobile_base/blob/8d17bdb6239702d8e7ec9a2cd170b696a6045bef/Dockerfile
[Compose-release]: https://github.com/monkey30440/mobile_base/blob/8d17bdb6239702d8e7ec9a2cd170b696a6045bef/compose.release.yaml
[Control-config]: https://github.com/monkey30440/mobile_base/blob/8d17bdb6239702d8e7ec9a2cd170b696a6045bef/src/mobile_base_control/config/base_control_params.yaml
[Base-launch]: https://github.com/monkey30440/mobile_base/blob/8d17bdb6239702d8e7ec9a2cd170b696a6045bef/src/mobile_base_control/launch/base_control.launch.py
[EKF-config]: https://github.com/monkey30440/mobile_base/blob/8d17bdb6239702d8e7ec9a2cd170b696a6045bef/src/mobile_base_state_estimation/config/ekf.yaml
[M1-hardware]: https://github.com/monkey30440/mobile_base/blob/8d17bdb6239702d8e7ec9a2cd170b696a6045bef/src/mobile_base_control/src/m1_hardware.cpp
[M1-driver]: https://github.com/monkey30440/mobile_base/blob/8d17bdb6239702d8e7ec9a2cd170b696a6045bef/src/mobile_base_control/src/m1_driver.cpp
[M1-types]: https://github.com/monkey30440/mobile_base/blob/8d17bdb6239702d8e7ec9a2cd170b696a6045bef/src/mobile_base_control/include/mobile_base_control/m1_driver.hpp
[C45-hardware]: https://github.com/ros-controls/ros2_control/blob/4324cabf03a1371951f0a039d239fcf09f563e54/hardware_interface/src/hardware_component.cpp
[C48-hardware]: https://github.com/ros-controls/ros2_control/blob/cdbc1127521074c2c5d19b4af2b73591e69d762b/hardware_interface/src/hardware_component.cpp
[C48-lifecycle]: https://github.com/ros-controls/ros2_control/blob/cdbc1127521074c2c5d19b4af2b73591e69d762b/hardware_interface/doc/lifecycle_of_a_hardware_component.rst
[C45-resource]: https://github.com/ros-controls/ros2_control/blob/4324cabf03a1371951f0a039d239fcf09f563e54/hardware_interface/src/resource_manager.cpp
[C48-resource]: https://github.com/ros-controls/ros2_control/blob/cdbc1127521074c2c5d19b4af2b73591e69d762b/hardware_interface/src/resource_manager.cpp
[C48-manager]: https://github.com/ros-controls/ros2_control/blob/cdbc1127521074c2c5d19b4af2b73591e69d762b/controller_manager/src/controller_manager.cpp
[D40]: https://github.com/ros-controls/ros2_controllers/blob/31015e0aa7ce9d0853a88d5fc2fe50f0e583ba5c/diff_drive_controller/src/diff_drive_controller.cpp
[D42]: https://github.com/ros-controls/ros2_controllers/blob/aacd842600a09d556b983ac3d53a0983e9ebcbb1/diff_drive_controller/src/diff_drive_controller.cpp
[D40-params]: https://github.com/ros-controls/ros2_controllers/blob/31015e0aa7ce9d0853a88d5fc2fe50f0e583ba5c/diff_drive_controller/src/diff_drive_controller_parameter.yaml
[D42-params]: https://github.com/ros-controls/ros2_controllers/blob/aacd842600a09d556b983ac3d53a0983e9ebcbb1/diff_drive_controller/src/diff_drive_controller_parameter.yaml
[D-odom]: https://github.com/ros-controls/ros2_controllers/blob/aacd842600a09d556b983ac3d53a0983e9ebcbb1/diff_drive_controller/src/odometry.cpp
[JS40]: https://github.com/ros-controls/ros2_controllers/blob/31015e0aa7ce9d0853a88d5fc2fe50f0e583ba5c/joint_state_broadcaster/src/joint_state_broadcaster.cpp
[JS42]: https://github.com/ros-controls/ros2_controllers/blob/aacd842600a09d556b983ac3d53a0983e9ebcbb1/joint_state_broadcaster/src/joint_state_broadcaster.cpp
[Spawner45]: https://github.com/ros-controls/ros2_control/blob/4324cabf03a1371951f0a039d239fcf09f563e54/controller_manager/controller_manager/spawner.py
[Spawner48]: https://github.com/ros-controls/ros2_control/blob/cdbc1127521074c2c5d19b4af2b73591e69d762b/controller_manager/controller_manager/spawner.py
[Launch-exit]: https://github.com/ros2/launch/blob/9ce0a0861270d651a596c83b62acd1bc076f2dc0/launch/launch/event_handlers/on_process_exit.py
[Launch-event]: https://github.com/ros2/launch/blob/9ce0a0861270d651a596c83b62acd1bc076f2dc0/launch/launch/events/process/process_exited.py
[RSP]: https://github.com/ros/robot_state_publisher/blob/e0f77e62457ae01f8dbf3b5c4cc62d15fa36dfad/README.md
[RSP-code]: https://github.com/ros/robot_state_publisher/blob/e0f77e62457ae01f8dbf3b5c4cc62d15fa36dfad/src/robot_state_publisher.cpp
[RL-doc]: https://github.com/cra-ros-pkg/robot_localization/blob/9596c40abd26cd10f80ee1a1325176bc38b4e0bf/doc/state_estimation_nodes.rst
[RL-code]: https://github.com/cra-ros-pkg/robot_localization/blob/9596c40abd26cd10f80ee1a1325176bc38b4e0bf/src/ros_filter.cpp
[Mux]: https://github.com/ros-teleop/twist_mux/blob/136394c1bf35b69fea5847ce00d75a1f44c8ab42/src/twist_mux.cpp
[Mux-handles]: https://github.com/ros-teleop/twist_mux/blob/136394c1bf35b69fea5847ce00d75a1f44c8ab42/include/twist_mux/topic_handle.hpp
[Topic-mux]: https://github.com/ros-tooling/topic_tools/blob/462af78b06ad8baafc27ce09cb3dfee96421cfab/topic_tools/src/mux_node.cpp
[Smoother13]: https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_velocity_smoother/src/velocity_smoother.cpp
[Actions]: https://design.ros2.org/articles/actions.html
[Registry]: https://github.com/ros/rosdistro/blob/6362c48a5abf60d9ae463d45267988944dbe4af9/jazzy/distribution.yaml

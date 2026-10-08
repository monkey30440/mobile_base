# Dual picoScan shutdown：Jazzy middleware 原生研究

研究日期：2026-10-08。範圍限於既有 `sick_scan_xd` 啟停／service churn 造成的偶發 SIGINT 關閉逾時；本研究未啟動硬體、未修改 runtime，也未做套件升級。主 agent 負責相同重現條件的差異驗證。

## 最終研究結論與驗證邊界

**CONFIRMED**：本次 SIGINT 關閉 **timeout** 的起始根因是 launch 保留的同步 Python `KeyboardInterrupt` 在 asyncio `call_soon` 排程 callback 時中斷執行，導致 event consumer 的喚醒遺失；native Shutdown event 雖已排入，卻沒有 consumer 繼續執行，因此 driver 根本尚未收到 launch 發送的停止訊號。此因果鏈已有不含 LiDAR／DDS 的自然重現，以及在相同 callback 排程邊界的 deterministic injection 紅綠證據。它不是已確認的 Fast DDS shutdown deadlock。[Python 官方 asyncio interruption 說明](https://docs.python.org/3.12/library/asyncio-runner.html#handling-keyboard-interruption)、[目前原生 launch run loop](https://github.com/ros2/launch/blob/3.4.8/launch/launch/launch_service.py)。

**CONFIRMED**：保留原生 `AsyncSafeSignalManager`／wakeup fd 的 async shutdown 路徑，只在 launch 執行期間避免同步預設 SIGINT handler 擲出 KeyboardInterrupt，可令 deterministic regression 由 timeout 轉為 child 正常結束；原始雙 driver probe 已通過 120 cases。**REQUIRES HARDWARE VALIDATION**：實體雙光達完整 shutdown／重啟仍須由主 agent 的 validation 完成。候選 image 原定 600-case 壓力測試未全部通過：前 142 輪、426 cases 通過後，第 142 輪 case 0 的右後 native driver SIGSEGV。Parent 已正確轉發 SIGINT，前左乾淨退出；這是另一 native failure，不能宣告完整 shutdown 可靠性已完成。追蹤：[issue #51](https://github.com/monkey30440/mobile_base/issues/51)。

**CONFIRMED（第二根因）**：壓力測試的 native SIGSEGV 已由真實 SIGINT／GDB 與 deterministic receiver initialization seam 定位為 stop 發生在 scan UDP receiver 配置前，inner init loop 因 shutdown flag 為真而跳過，後續仍解參考 null `udp_receiver`。其最小原生 guard 正在候選 image 建置／驗證，尚不宣告硬體或所有 upstream shutdown 路徑通過。先前 middleware stacks 是同時存在的 startup／service churn 觀察，沒有證明它們導致 launch timeout。Fast DDS-only 更新與 Fast DDS＋rclcpp 更新皆未消除這個 timeout 重現。

**CONFIRMED（native-first）**：最新 Jazzy launch 3.4.12 的相關兩個 source 檔仍與本機 3.4.8 相同，未找到可直接採用的 upstream 同步 interruption 修正。下列 middleware 版本研究保留作為排除過程，不能再解讀成目前推薦升級來修 timeout。

## 歷史診斷：本機 middleware 觀察與責任鏈

本次主 agent 捕捉的原始 backtraces 位於 `/tmp/lidar-shutdown-native-evidence/pytest-15/test_native_children_exit_clea2/59479-backtrace.txt` 與 `59480-backtrace.txt`。**CONFIRMED（本機 trace）**：FL 背景 service 建立進入 `rmw_create_service → DataReader::enable → PDP::addReaderProxyData` 並等待 mutex；DDS discovery 接收執行緒另在 `StatefulReader::matched_writer_is_matched` 等待 mutex。BR executor 則在 `__rmw_destroy_service` 等待，而背景仍在建立 `SickScanExitSrv`。這是 middleware service／discovery 路徑阻塞的證據，不是 ROS launch parent 本身忙迴圈的證據。

**CONFIRMED（原生 source）**：RMW 8.4.4 建立與銷毀 service 均取得同一 participant 的 `entity_creation_mutex_`。因此 destroy 等待可能是另一執行緒持有 entity lock、卡在 Fast DDS 建立 reader 的連鎖結果。這是 source 支持的可能因果鏈；**UNRESOLVED**：沒有逐一 mutex owner／完整 lock cycle 證據前，不把 RMW destroy 稱為起始根因。[create service 8.4.4](https://github.com/ros2/rmw_fastrtps/blob/8.4.4/rmw_fastrtps_cpp/src/rmw_service.cpp)、[destroy service 8.4.4](https://github.com/ros2/rmw_fastrtps/blob/8.4.4/rmw_fastrtps_shared_cpp/src/rmw_service.cpp)。

**CONFIRMED**：Fast DDS 2.14.6 `PDP::addReaderProxyData` 取得 PDP recursive mutex；`StatefulReader::matched_writer_is_matched` 取得 reader mutex。僅有兩個等待 stack 不足以證明 ABBA 鎖序，也不能由函式同名判定任何舊 deadlock issue 即為本案。[PDP 2.14.6](https://github.com/eProsima/Fast-DDS/blob/v2.14.6/src/cpp/rtps/builtin/discovery/participant/PDP.cpp)、[StatefulReader 2.14.6](https://github.com/eProsima/Fast-DDS/blob/v2.14.6/src/cpp/rtps/reader/StatefulReader.cpp)。

## rclcpp 28.1.16 → 28.1.22

| 原生變更 | 支持的事實 | 與本案關係 |
| --- | --- | --- |
| 28.1.22／PR #3239 | `GraphListener::start_if_not_started` 在未持有 `shutdown_mutex_` 時註冊 Context shutdown callback，以避免 GraphListener 與 Context 的 lock order inversion；PR 明示 ABI compatible backport。 | 候選 shutdown 修正，但本次 native signal thread 在 `wait_for_signal`，沒有捕捉到相同 GraphListener／Context cycle；根因對應仍 UNRESOLVED。 |
| 28.1.22／PR #3225 | 防止同 thread 的 reentrant Context shutdown 重跑程序，並捕捉 deferred signal thread shutdown exceptions；thread-local tracking 避免修改 Context class layout。新增 reentrant 與 concurrent shutdown tests。 | 能確認修正存在，不能推導為 service discovery mutex 的修正。 |
| 28.1.17–21 | 包含 callback group race、allocator、tests、EventsCBGExecutor 等變更。 | 不是「只有 shutdown 修正」的二進位差異；若一次更新整組只能先證明 package-set 差異。 |

逐項來源：[3239 pinned merge](https://github.com/ros2/rclcpp/commit/efb669e2e9ba319fc1d9237360f9dfd9e3e06a91)、[3239 PR／ABI 宣告](https://github.com/ros2/rclcpp/pull/3239)、[3225 pinned merge／tests](https://github.com/ros2/rclcpp/commit/a5eded93e738223b7be485e34f29466fd1c2c4b6)、[完整 28.1.22 changelog](https://github.com/ros2/rclcpp/blob/28.1.22/rclcpp/CHANGELOG.rst)。官方 issue #2946 的 TSan reproducer 與 #3232 的 Nav2 bond reproducer 都呈現 GraphListener／Context 鎖序反轉；它們可驗證該原生 bug 的存在，不能替代本 AMR driver 的紅綠證據。[2946](https://github.com/ros2/rclcpp/issues/2946)、[3232](https://github.com/ros2/rclcpp/issues/3232)。

## Fast DDS 2.14.6 → 2.14.7

**CONFIRMED**：2.14.7 release 包含 matched callbacks、participant attributes、writer QoS 的 data race 修正，以及 datasharing infinite loop、SHM port-open crash 等其他修正。這些不是同一個問題；尤其 datasharing／SHM 修正不能由目前 UDP discovery stack 直接認定相關。[官方 release](https://github.com/eProsima/Fast-DDS/releases/tag/v2.14.7)、[完整 tag 比較](https://github.com/eProsima/Fast-DDS/compare/v2.14.6...v2.14.7)。

- **CONFIRMED**：#6382 的內部 DataReaderImpl／DataWriterImpl matched callbacks 加 mutex，避免同時更新 matching status；PR 有反覆執行才能穩定揭露的 regression test，並標記 API／ABI 相容。它還調整 EDP listener 指標讀取。**UNRESOLVED**：這不是明示 PDP／StatefulReader ABBA 修正。[pinned commit](https://github.com/eProsima/Fast-DDS/commit/35fd9c5b91b9e9977a4e82d6a876b201c6f24c95)、[PR 6382](https://github.com/eProsima/Fast-DDS/pull/6382)。
- **CONFIRMED**：#6389 將內部 participant attributes 的並發讀寫改為受保護的 copy／constant／mutable access；為保留 API，保留原 getter。PR 標記 backport API／ABI 相容。**UNRESOLVED**：原生 source 中 PDP 路徑有變動，但這仍不足以宣告它修好本次 mutex 等待。[pinned commit](https://github.com/eProsima/Fast-DDS/commit/1f2cf710d446a41ea31eeb08f4c2ed3beb09086f)、[PR 6389](https://github.com/eProsima/Fast-DDS/pull/6389)。
- **CONFIRMED**：#6424 處理 DataWriterImpl QoS 存取 race；不能將 writer QoS race 與 service reader 建立卡住視為同一 root cause。[pinned commit](https://github.com/eProsima/Fast-DDS/commit/f9a94f213312173bb15450aafcae541b3c18d340)。

## RMW 8.4.4、launch 與 binary 安全邊界

**CONFIRMED**：RMW cpp／shared cpp 的 8.4.4 changelog 只列移除 buildtool export dependency；同 upstream 8.4.4 不同 Debian rebuild 日期，不是 source 修復版本號的證據。必須另核實 Debian source／patch 差異，不能用日期較新推論 service deadlock 被修好。[cpp changelog](https://github.com/ros2/rmw_fastrtps/blob/8.4.4/rmw_fastrtps_cpp/CHANGELOG.rst)、[shared changelog](https://github.com/ros2/rmw_fastrtps/blob/8.4.4/rmw_fastrtps_shared_cpp/CHANGELOG.rst)。

**CONFIRMED（主 agent inventory）**：目前 native runtime 為 Fast DDS 2.14.6／rclcpp 28.1.16；APT candidate 為 2.14.7／28.1.22。launch Debian 版本 `99.0.0-0noble` 來自 base image，不能假定等於官方 Jazzy release tag。**UNRESOLVED**：本研究沒有證明 NVIDIA 特製 launch 與官方 candidate 的 source／ABI 一致；故不建議在沒有比較下把 launch 一併降版或替換。

**CONFIRMED**：上列兩個 rclcpp shutdown backports 與兩個 Fast DDS race backports提供相容性設計依据。**UNRESOLVED**：個別 PR 的 ABI 宣告不能等同整個 Docker binary overlay、所有 NVIDIA 自帶 ROS 套件與 source overlays 已驗證相容。建議驗證時先保存 package inventory、使用 APT dependency resolver 查實際變更集合，保留回復 baseline 的方式；檢查 overlay 實際載入之 shared libraries，重新建置 project／既有 native overlays，跑完整 package regressions。

## 歷史 middleware 差異驗證順序（已由新根因取代）

1. 保存目前失敗重現與 backtraces；相同 loopback startup／service churn／SIGINT 時點、domain、driver overlay，基準需能重現失敗。
2. 優先分開 rclcpp 與 Fast DDS 版本變因；APT 若要求相依套件一起更新，記錄 resolver 輸出並以「套件集合差異」報告，勿假裝單一 PR 證據。
3. 用相同 detector 判斷 native child 自行退出與沒有殘留，而非只看 parent return code。重複壓力場景及正常已啟動情境；若仍逾時，捕捉新的 native stack 比對是否相同阻塞。
4. 僅當軟體紅綠通過後再做實際雙光達 startup／穩定 scan／graceful shutdown／重啟驗收；不動馬達。
5. 無論候選 pass 或 fail，都保留證據邊界。未證明具體 code root cause 前不得稱某 PR 已確定修正；也沒有證據要求切換 Cyclone DDS。

本研究沒有新增 architecture decision，也不變更現有 Fast DDS／native SICK ownership；是否採用更新原生套件，由差異驗證結果與既有 V1 原則決定。

## 補充：executor collection 與 launch signal routing

**CONFIRMED（主 agent 差異測試回報）**：只將 Fast DDS 2.14.6 更新為 2.14.7 的相同無硬體 probe，首輪三個 cases 中一個仍 timeout。這排除「只升 Fast DDS 即可解決目前重現」；不排除 Fast DDS 仍有參與，也不能僅由失敗比例推論頻率不變。rclcpp 28.1.22 的組合試驗另行執行，結果應由 validation report 保存；此研究不預先宣告它有效。

**CONFIRMED**：rclcpp 28.1.16 的 `CallbackGroup::collect_all_ptrs` 持有 group mutex，暫時從 weak service pointer 建立 shared pointer 並呼叫 collection callback。當該暫時 shared pointer 是最後 owner，其離開 scope 可以在 executor collection 路徑觸發 service destructor。這能解釋 executor `wait_for_work` 進入 `rmw_destroy_service` 的合理所有權路徑，不需要假設使用者正呼叫 service callback。**UNRESOLVED**：要宣告完整跨層 deadlock，仍須確認對向 thread 持有與等待的鎖，不能只由 destructor 出現在 stack 推論。[callback group 28.1.16](https://github.com/ros2/rclcpp/blob/28.1.16/rclcpp/src/rclcpp/callback_group.cpp)、[executor collection 28.1.16](https://github.com/ros2/rclcpp/blob/28.1.16/rclcpp/src/rclcpp/executors/executor_entities_collection.cpp)。

**CONFIRMED**：28.1.18 收錄 #3060，僅替 `CallbackGroup::size()` 讀取 vectors 增加 mutex；不會把 service destructor 移出 `collect_all_ptrs`。直接比較 28.1.16／28.1.22 的 executor entities collection 檔案，沒有 source 差異；因此不能把 rclcpp 版本更新描述成「已移除 executor service GC 死鎖」。[pinned #3060](https://github.com/ros2/rclcpp/commit/ea3229d463d31df2fbaf48badf33c1ca3e774f55)、[callback group 28.1.22](https://github.com/ros2/rclcpp/blob/28.1.22/rclcpp/src/rclcpp/callback_group.cpp)、[executor collection 28.1.22](https://github.com/ros2/rclcpp/blob/28.1.22/rclcpp/src/rclcpp/executors/executor_entities_collection.cpp)。

**CONFIRMED（本機 source 比較）**：本機保存的 `/tmp/ros-launch-execute-local.py` 與官方 launch **3.4.8** 的 `execute_local.py` 完全相同。原生 signal event 使用 subprocess transport `send_signal`；shutdown 產生對應 child 的 SIGINT event。因此，單 launch parent 收到停止訊號後將 SIGINT 傳給 children，至少在這個檔案是官方行為，不是已確認的 NVIDIA 特製 patch。**UNRESOLVED**：一個檔案相同不證明整個 Debian `99.0.0-0noble` 的來源、所有檔案與官方 package 都相同；本研究未找到官方 NVIDIA 證據宣告此版本含單 parent SIGINT 特製 patch。[官方 pinned launch 3.4.8 execute_local](https://github.com/ros2/launch/blob/3.4.8/launch/launch/actions/execute_local.py)。

## 中途診斷：Shutdown event 已排入但未消費（後續已定位排程中斷）

後續主 agent 臨時 instrumentation 提供更直接的證據：失敗時 `LaunchService._shutdown` 執行，`force_sync=True`，event queue 長度由 0 變 1，但未進入 `__process_event(Shutdown)`、也未呼叫 `ExecuteLocal._shutdown_process`。**CONFIRMED（本次 probe）**：關閉流程在 launch event consumption 前中斷，尚未發送原生 driver 停止訊號。因此先前 middleware 卡鎖 stacks 只能證明同時存在的 native startup／service 阻塞，不能再作為本次 graceful-shutdown timeout 的已確認根因；signal thread 等待訊號正與尚未送出 SIGINT 一致。

**CONFIRMED（主 agent 更新後 probe）**：Fast DDS 2.14.7 加 rclcpp 28.1.22 仍可失敗。不得將繼續升級 middleware 視為已確認解法；診斷應轉向 launch queue consumer／asyncio。

官方 launch #473（2020）曾報告相同表面行為：Shutdown 排入後沒有喚醒 loop，直到 child 有 output 才消費。該 issue 已關閉；相關修正分成 #475 noninteractive SIGINT forwarding 與 #476 將 signals 透過 `signal.set_wakeup_fd` 交由 loop 處理，兩者不是同一責任。[issue 473](https://github.com/ros2/launch/issues/473)、[475 pinned merge](https://github.com/ros2/launch/commit/55ca523ff0053e1c7932debaa7366e33180c23a6)、[476 pinned merge](https://github.com/ros2/launch/commit/3d77b5d326cfcbf800be7e99cccb798cd468dada)。

**CONFIRMED（本機完整檔案比對）**：本機 `launch_service.py` SHA256 `7d587a8269131ae9b2e950460a52c87e95fd4bce083faa1fcc1f76bf8468a756`；`utilities/signal_management.py` SHA256 `ca50327f0619e76f63dc864e2b582e8b2cf432419ac0a23a9efe6ac9e1fc46e2`，均與官方 launch **3.4.8** 完全相同。後者已含 #476 的 `AsyncSafeSignalManager`，以 socketpair 與 `set_wakeup_fd` 註冊 loop reader。因而本案不是已證明「缺少 #476」；#473 是診斷線索而非可以直接再套一次的修正。[3.4.8 LaunchService](https://github.com/ros2/launch/blob/3.4.8/launch/launch/launch_service.py)、[3.4.8 signal manager](https://github.com/ros2/launch/blob/3.4.8/launch/launch/utilities/signal_management.py)。

原生 3.4.8 run loop 每次重建 context queue，持續等待 `_process_one_event()` task 與 entity futures；`emit_event_sync` 只做 queue `put_nowait`。下一個最小診斷應記錄實際 queue identity、queue getters futures／loop、event task 正在等待哪個 future、以及 signal callback 執行中的 running loop；確認 handler 把 event 放進目前 consumer 所等待的 queue，並確認 event task 是否困在先前 event 的非完成 coroutine。這些是當時原生 source 所定位的觀測點；後續最小重現已完成（見末節）。**當時 UNRESOLVED**：尚未量測前，不推定 Python asyncio 本身壞掉、consumer queue 錯置或特定 dependency patch。[3.4.8 LaunchContext](https://github.com/ros2/launch/blob/3.4.8/launch/launch/launch_context.py)、[3.4.8 run loop](https://github.com/ros2/launch/blob/3.4.8/launch/launch/launch_service.py)。

## 同步 KeyboardInterrupt 與最新 Jazzy 原生能力

**CONFIRMED（官方 Python 文件）**：Python 3.12 asyncio Runner 文件明確說明預設 SIGINT 產生的同步 `KeyboardInterrupt` 能中斷 asyncio internals，使程序退出卡住；Runner 的解法是在執行期間安裝自訂 handler，先取消 main task 而非直接任意插入 KeyboardInterrupt。這支持調查同步 signal handler 與 launch 自己的 async signal path 同時存在的風險，不等同直接使用 Runner 即可保留 launch shutdown semantics。[Python 3.12 Runner Keyboard Interruption](https://docs.python.org/3.12/library/asyncio-runner.html#handling-keyboard-interruption)。

**CONFIRMED（source 比較）**：截至本研究讀取的最新 Jazzy tag **3.4.12（2026-09-18）**，`launch_service.py`、`utilities/signal_management.py` 與 3.4.8 完全相同；近期 changelog 是 pytest／substitution／文件等變更，不含同步 KeyboardInterrupt suppression 修正。因此未找到「升級 Jazzy launch 可直接取得這項修正」的原生 release 證據。[3.4.12 changelog](https://github.com/ros2/launch/blob/3.4.12/launch/CHANGELOG.rst)、[3.4.12 LaunchService](https://github.com/ros2/launch/blob/3.4.12/launch/launch/launch_service.py)、[3.4.12 signal manager](https://github.com/ros2/launch/blob/3.4.12/launch/launch/utilities/signal_management.py)。

官方 #712 的後續 signal acquisition 修法針對 SIGTERM／SIGQUIT 預設 OS disposition 與 wakeup fd 問題；最新 rolling source 對既有 callable Python handler 仍會 chain，而不是一律 suppress `default_int_handler`。因此它不是主 agent 的「暫時 no-op 同步 SIGINT、保留 wakeup fd／async handler」probe 的現成等價方案。[PR 712](https://github.com/ros2/launch/pull/712)、[pinned rolling signal manager](https://github.com/ros2/launch/blob/466d861cea6a2dd8163161ae0fe2abbd628725ee/launch/launch/utilities/signal_management.py)。

## 最小重現與正式 regression 證據

以下由主 agent 執行；本 research agent 唯讀核對自然失敗 log，未修改 runtime。

1. **CONFIRMED：自然 software-only red。** 不載入 LiDAR、DDS 或 SICK，只啟動兩個 Python child 各輸出 1000 行 startup 訊息後等待停止，於第 59 輪自然 timeout。`/tmp/lidar-quiet-minimized-evidence/59.log` 捕捉 `KeyboardInterrupt` 位於 Python 3.12 `base_events.call_soon`；隨後 launch 已收到 SIGINT，但 `queue=4`、`getters=[]`、`ready=[]`，存活 tasks 僅 run_async 與兩個 ExecuteLocal，event consumer 已遺失。這個 red 排除「必須 LiDAR／DDS 才會發生」假設。
2. **CONFIRMED：deterministic causal red／green。** 在 `_process_one_event.task_wakeup` 的 `call_soon` 排程邊界注入同步 SIGINT：原生版本 4 秒 timeout；暫時避免同步 default handler 插入 KeyboardInterrupt、保留 AsyncSafeSignalManager 原生 event routing，則 exit 0、child 清理完成。這是排程邊界的因果對照，並非延長 timeout 或 kill fallback。
3. **CONFIRMED：repository regression。** `docker/test` 的同一 regression 在原始 source red（4.09 秒），在隔離的 native source 修正 green。完整命令、image／source hashes 及 log 由 #51 validation 保存，不能僅引用本研究文字替代可重跑證據。
4. **CONFIRMED：原始雙 driver probe。** 單一同步 handler 變因的原始雙 LiDAR software probe 共 120 cases 通過；不是實體感測器驗收，也不是所有可能 failure 的無限期保證。
5. **FAILED（另一 native SIGSEGV）**：正式候選 image 原定 600 cases；前 142 輪、426 cases 全部通過，第 142 輪 case 0 BR 以 -11 結束。`/tmp/lidar-fixed-launch-native-crash-evidence/pytest-142/test_native_children_exit_clea0/shutdown.log` 顯示 parent 向兩個 driver 送 SIGINT、FL clean、BR SIGSEGV。Launch event consumption 修正的壓力測試因此揭露另一 native lifecycle 問題，完整可靠性尚未驗收。

Python 官方文件提供機制依據，原生 LaunchService `run()` 在外層捕捉 KeyboardInterrupt 後繼續 run loop，卻不能恢復已在 callback 排程中遺失的工作。`AsyncSafeSignalManager` 已有 async signal reader，因此最小責任是保留該路徑、避免同一 SIGINT 同時以同步 exception 任意中斷 asyncio internals；不需更換 RMW、修改 SICK scanner 邏輯或增設 project-owned shutdown supervisor。[Python Runner](https://docs.python.org/3.12/library/asyncio-runner.html#handling-keyboard-interruption)、[原生 LaunchService run](https://github.com/ros2/launch/blob/3.4.8/launch/launch/launch_service.py)、[原生 async signal manager](https://github.com/ros2/launch/blob/3.4.8/launch/launch/utilities/signal_management.py)。

## 歷史候選：SICK 3.9.0 lifecycle 研究（join race 並非本次已確認根因）

**CONFIRMED（source ownership）**：SICK 3.9.0 的 `stopScannerAndExit()` 本身已呼叫 `joinGenericLaser()`；main 在 `rosSpin()` 返回後再呼叫 stop／join。`joinGenericLaser()` 直接檢查 process-global raw pointer `s_generic_laser_thread`、join、delete、寫回 0，沒有 mutex 或單一 owner guard。現有 downstream patch 的 Context pre-shutdown callback 也呼叫 `requestScannerShutdown() → stopScannerAndExit(true)`，因此 stop／join 可以由 deferred signal thread 與 main cleanup 兩條路徑進入。**UNRESOLVED**：這是已確認的多路 lifecycle 入口與缺乏同步，尚未有 GDB 證明這次 -11 恰為 concurrent delete／join；不得先宣告該假設就是 root cause。[SICK 3.9.0 caller](https://github.com/SICKAG/sick_scan_xd/blob/3.9.0/driver/src/sick_generic_caller.cpp)、[SICK 3.9.0 stop／join](https://github.com/SICKAG/sick_scan_xd/blob/3.9.0/driver/src/sick_generic_laser.cpp)、本 repo `docker/patches/sick-scan-xd-shutdown.patch`。

**CONFIRMED**：scansegment 用自己的 `MsgPackThreads` 擁有背景 thread；`start()` 建立 thread，`join()` joinable 後 join，`stop()` 設 run flag 並選擇 join／delete，destructor 再 `stop(true)`。背景 runThreadCb 反覆建立 SOPAS services、等待資料、通訊失聯時清理後 reconnect。GenericLaser 的外層 thread 與 MsgPackThreads 內層 thread ownership 必須分開：只看到「join」不能判定是哪一層、哪個 object 已被刪除。[3.9.0 scansegment thread lifecycle](https://github.com/SICKAG/sick_scan_xd/blob/3.9.0/driver/src/sick_scansegment_xd/scansegment_threads.cpp)。

**CONFIRMED**：既有 patch 的 atomic shutdown flag 可讓原生 `rosOk()` 條件停止背景 loop，但不會自動保護其他 global pointers 或讓重複 stop／join 原子化；startup 的 `startGenericLaser()` 還會初始化相關 globals。是否有 startup／shutdown 交錯也是應由 GDB 與時序證據判定的候選，不能用 flag 是 atomic 就宣告全部生命周期安全。[3.9.0 GenericLaser](https://github.com/SICKAG/sick_scan_xd/blob/3.9.0/driver/src/sick_generic_laser.cpp)、[3.9.0 ROS wrapper](https://github.com/SICKAG/sick_scan_xd/blob/3.9.0/include/sick_scan/sick_ros_wrapper.h)、本 repo shutdown patch。

**CONFIRMED（upstream scope）**：官方 #550 描述 scansegment FIFO Pop／join shutdown hang；#552 提供 asynchronous unblocking 與 optional ROS 2 Lifecycle，目前 PR **未 merge**，head `78c9c4a44f2c203648d5fe764f69f2295866d88c`。SICK 官方留言表示 3.9 已 release，相關變更在 `feature/optional-lifecycle-support` 評估，預計 3.10 或相近 release。因此不能稱其為已發行的 stable native 修復，也不能把該 FIFO hang 當本次 -11 的證據。V1 不因這個 open PR 預先加入整套 Lifecycle 功能。[issue 550](https://github.com/SICKAG/sick_scan_xd/issues/550)、[PR 552](https://github.com/SICKAG/sick_scan_xd/pull/552)、[pinned PR head](https://github.com/SICKAG/sick_scan_xd/commit/78c9c4a44f2c203648d5fe764f69f2295866d88c)、[官方 release planning 回覆](https://github.com/SICKAG/sick_scan_xd/pull/552#issuecomment-4129639638)。

上述 stop／join 候選保留為 source 觀察，後續 GDB 已定位不同 root cause（見下節）；不依該候選提前移除既有 pre-shutdown 策略，也不宣稱所有其他 lifecycle races 已排除。

## 第二根因已確認：stop-before-UDP-allocation null receiver

**CONFIRMED（自然實際 native GDB）**：`/tmp/lidar-native-crash-gdb-evidence/049-fl.log` 以真實 SIGINT 自然重現 `MsgPackThreads::runThreadCb` SIGSEGV。faulting static PC `0x3957ec`（function + `0xa1c`）為 `ldr x3,[x25,#64]`，x25 對應 `udp_receiver` pointer；當時 stop callback 正在 join、main 仍在 spin，因此本次 fault 不需要假設兩個 main／callback 同時 delete GenericLaser thread。

**CONFIRMED（可重現因果 seam）**：`/tmp/lidar-stop-init-red.log` 在 native `notifyLogMessageListener` 的「sick_scansegment_xd initializing...」位置設定相同 shutdown flag，重現同一 PC 且 x25=0。原生 outer run loop 已進入，但在配置 `udp_receiver` 前 shutdown flag 變真；inner init loop 的 `rosOk()` 條件跳過整個配置，程式卻繼續建立 converter 並呼叫 `udp_receiver->Fifo()`。這是 stop／init 邊界的 null dereference，不是已證明的重複 join race。[SICK 3.9.0 receiver init 與 converter 建立](https://github.com/SICKAG/sick_scan_xd/blob/3.9.0/driver/src/sick_scansegment_xd/scansegment_threads.cpp)、[ROS wrapper 的 shutdown flag 條件](https://github.com/SICKAG/sick_scan_xd/blob/3.9.0/include/sick_scan/sick_ros_wrapper.h)。

**CONFIRMED（upstream gap）**：已選穩定 3.9.0 缺少 scan UDP init loop 後的 null guard；查詢官方 default branch 此檔最新變更 `9f366dbdba4a45050445ebd62c35291a24dc28f5`，同樣直接接到 IMU init／converter 後續流程，沒有該 guard。官方最近 release 仍為 3.9.0；#552 未 merge 的 Lifecycle／FIFO 改動也不提供「已發行 stable exact fix」證據。這只確認本次所需 native receiver guard 的 gap，不宣稱所有 branches／所有未發行 commits 都沒有任何替代方案。[pinned default-branch source](https://github.com/SICKAG/sick_scan_xd/blob/9f366dbdba4a45050445ebd62c35291a24dc28f5/driver/src/sick_scansegment_xd/scansegment_threads.cpp)、[官方 3.9.0 release](https://github.com/SICKAG/sick_scan_xd/releases/tag/3.9.0)、[未合併 PR 552](https://github.com/SICKAG/sick_scan_xd/pull/552)。

**CONFIRMED（formal regression red）**：repository `docker/test/test_native_receiver_shutdown.py` 保留真 SIGINT 與 context shutdown，原始 native source RED（exit 255、1.46 秒）。最小候選為 UDP scan receiver init loop 之後、IMU init 之前的七行 null guard：尚無 receiver 或後續資源配置時直接結束 run loop；正常已配置路徑不變。**驗證中**：候選 Docker image 正建置；green、完整 software pressure、雙光達實機結果需由 #51 validation 報告完成。不要將候選 build 開始誤報為修正已驗收。

此根因修正不覆蓋所有 SICK upstream 路徑：GenericLaser globals、其他 scan families、FIFO／Lifecycle、任意重連與任意 signal 重入均無全域正確性證明；本輪保持 minimal responsibility，只修已定位的 null receiver 邊界。

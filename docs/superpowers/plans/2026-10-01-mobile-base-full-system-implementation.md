# mobile_base Full-System Implementation — Work Items

## 1. Planning skills used

本文件是 **ONE IMPLEMENTATION RUN 的待審計畫**，不是另一輪 subsystem architecture audit，也不是 implementation evidence。日期：2026-10-01；檢查基準：`00c3319630216dfbc3ce349e0e5c12d22661c91c`。本輪沒有 build、test、ROS launch、硬體操作或產品檔案修改。

| 已安裝並讀取的 skill | 本輪用途 |
|---|---|
| `superpowers:using-superpowers` | 確認 skills 與使用者指令的優先順序；只啟用本輪規劃需要的流程。 |
| `superpowers:writing-plans` | 將已批准 scope 轉成有檔案、相依性、驗收與驗證的 executable work items；依該 skill 慣例存放於 `docs/superpowers/plans/`。 |
| `superpowers:dispatching-parallel-agents` | 平行唯讀檢查 Control/TF、Navigation/Docking、Deployment/Observability，主代理統一整合跨系統契約。 |
| `superpowers:verification-before-completion` | 區分已讀取的 source evidence、未執行的 V1、未取得的 physical evidence；最後只核對 planning artifact 與工作樹。 |
| `gitnexus-exploring` | 嘗試透過既有索引追查程式，再以精確 source inspection 核對；工具限制見下。 |

Skills 的分拆多份計畫、每項人工 review、frequent commits、執行交接選項，均由本輪明確指令覆蓋。不重新進行 brainstorming 或 frozen architecture 設計；不使用 worktree、TDD 執行、implementation 或 branch finishing skills。本文件中的測試均為**未來執行內容**。

證據入口：`spec/README.md` → `spec/01_USE_CASES.md`、`02_CAPABILITIES.md`、`03_REQUIREMENTS.md`、`04_SYSTEMS.md`，以及 `operator/*.md`、production source/config/launch/tests。現行描述性文件中的舊 architecture 必須依本輪已批准 final model 修正，不得反過來限制 final model。

GitNexus `list_repos` 可讀且 mobile_base index 對應上述 commit，但 query 回報 LadybugDB database version **42** / runtime storage version **40** 不相容。因此**dependency impact 本輪無法由 GitNexus 確定**；沒有重建或改寫索引。下列相依性來自 source inspection，不能冒稱圖譜已驗證。未來執行前恢復相容工具，既有 symbol 修改前跑 impact，HIGH/CRITICAL 先報告，修改後跑 affected-scope / detect_changes；不在 WI 間插入人工批准。

歷史檔案 `ChatGPT-[重要!!!] 確認移動底座責任-20261001-0903.md` 唯讀且豁免清理。其 SHA-256 為 `c4a2a5a72da51ba05128d083cf53aa4193d5ba624ae9ff628607150ac39e4858`。它包含先前討論，但末段仍在開始 audit，沒有 GAP-001～GAP-022 synthesis registry。本輪 user instructions 是 final frozen scope 的直接權威；原始 GAP 對照缺件由 Q5 處理，不捏造編號。

## 2. One-shot implementation rule

ChatGPT 一次解決 §23 所有問題並批准**完整本檔**後，Codex 接收一個 implementation prompt，先讀完整計畫，再依 §9 執行 **WI-001～WI-027 全部工作**，完成 source/config/launch/interfaces/tests/spec/operator docs/dead dependencies，接著完整 V1 → 修正失敗 → 重跑受影響驗證與整合總檢 → V1 PASS → 一份 final implementation report。

WI 是同一次執行的工作單位，不是 implementation phases。不得 `WI → user review → 下一 WI`，不得只交付 Localization 或 Phase A，不得留下「稍後決定 architecture」「等批准再繼續」的 implementation 子步驟。§23 的未決問題須在 implementation prompt 發出前，將決定寫回本檔並刪除未選分支。依賴順序中的測試與內部 code review 不構成人工 approval gate。

可因**已證明的外部 blocker**中止並提交具體證據；一般編譯、測試、設定或整合錯誤必須在同一 run 修復，不得以另一 implementation round 代替。不得自動操作硬體。V2～V4 是 V1 後另行授權的實機驗證，絕不是尚未完成的預定軟體 implementation phases。

## 3. Approved final architecture summary

共同推導順序：**Requirement → Capability → Responsibility → native ROS 2 / Nav2 / OpenNav capability → true gap → necessary custom design**。MVP、YAGNI、single authority、明確 ownership/state semantics、native first；不加 patch architecture 或跨責任 manager。

| Capability / 責任 | Final owner / native core | 需落地的整合邊界 |
|---|---|---|
| Robot Description / TF | RSP + private geometry/control Xacro | 唯一固定 TF；感測器 frame、driver TF 關閉、可追溯 private assets。 |
| Control | DDC → ros2_control → M1Hardware → M1Driver/libmodbus | 唯一 command owner、admission/stop、ID2 left / ID1 right、命令/通訊逾時各自負責。 |
| Local State Estimation | wheel feedback/DDC + IIM-42652 gyro Z → robot_localization EKF | fuse wheel vx、vy=0 constraint、gyro yaw-rate；`/odometry/filtered` 與唯一 odom TF。 |
| Localization | AMCL estimator + sole Localization Evaluator | availability + covariance + odometry-relative consistency + persistence；Bool readiness 與同一 diagnostics snapshot。 |
| EstablishLocalization | cancelable task + native AMCL reset/no-motion update + Nav2 Spin | 空 goal、最小 failure category、內部 epoch 協調；不重複 readiness policy。 |
| Navigation | native NavigateToPose / BT Navigator / Route Server / Navfn / MPPI | ready admission、只針對 localization loss 的 bounded recovery、First/Route/Last 正確串接。 |
| Station | 既有 one-shot adapter | Station ID → validated pose → native NavigateToPose。 |
| Mapping | keyboard Teleop + SLAM Toolbox + native map saver/readback | coherent site dataset，顯式 save；不新增 exploration 或 site business orchestration。 |
| Docking | native OpenNav DockRobot + external Vision pose | local-only、position+yaw+software-observed stop；native extension 邊界由 Q3 定案。 |
| Diagnostics | component producers + native diagnostic_aggregator | operator grouping / disappearance；沒有中央 health decision。 |
| Observability | outbound telemetry/log adapters | timestamp/expiry/bounds；backend failure 不影響核心。 |
| Deployment | Mapping / Navigation profiles + native lifecycle managers | common base、local infrastructure、global Navigation、Docking 正確隔離；artifact provenance。 |

Canonical TF 不變：`map → odom → base_footprint → base_link → sensors / wheels / fixed frames`。`map→odom` 由 Navigation 的 AMCL 或 Mapping 的 SLAM Toolbox 二擇一；`odom→base_footprint` 只由 EKF；其餘固定 robot/sensor edges 由 RSP。

Readiness publisher：`/localization/ready`、`std_msgs/msg/Bool`、Reliable / Transient Local / KeepLast(1)，startup false、transition publish、periodic heartbeat。`true` 只表示現在可依赖 global localization；不是 ground-truth proof、不是全系統 ready。`/localization/lost`、`/localization/quality` 最終完全移除。

## 4. Scope boundaries

- 本輪只新增此 Markdown。未來 run 才改產品與文件；保留所有原始 unrelated/untracked/ignored assets，不 commit/push/reset/clean/checkout/restore。
- mobile_base 負責 description/TF、hardware integration、motion control、local estimation、Localization、Mapping、Navigation、local Docking、health evidence、selected observability、bringup/deployment。
- Mission/Task business orchestration、Patrol、Vision/image/AprilTag processing、charging schedule、fleet/site business semantics 不屬於產品。原生動作之 task integration 不得擴張成 business orchestrator。
- Current code = implementation evidence。Keep native core 不代表保留已確認 defect；本文件不以現行錯誤反改批准 architecture。
- 軟體停止證據須明確分辨：admitted、canceled、zero sent、controller stopped、M1 stop request、servo disabled、device watchdog、E-stop/STO、physical wheels stopped。命令與 feedback 不得混用。
- 靜態可證明的錯誤要修；硬體 acquisition timing、encoder/limits/calibration 等只排入 §16～20，不用猜測數值冒充證據。
- private Xacro 本機**存在但被 gitignore 排除**：`mobile_base.urdf.xacro`、`mobile_base_geometry.xacro`、`mobile_base_ros2_control.xacro`。允許未來在既有 private 資產交付流程中修正 interface mismatch 並記錄 checksum；不得複製進公開 repo。沒有必要 geometry 改動就 KEEP。
- package-level gtest/pytest/ament/launch_testing 與既有 Docker workflow 是唯一 V1 infrastructure；合成 ROS fixtures 是非硬體測試，不是宣稱 full simulation supported。

## 5. Gap traceability matrix

`F-xxx` 是本檔的**可核對 finding anchor**，不是擅自重新編號既有 GAP。括號 `§n` 指本轮 user prompt 的章節。Implementation 包含 source/tests；Config 包含 launch/BT；Deployment 包含 packaging；Verification-only 不產生猜測性修正。

| Gap / finding | Work Item(s) | Implementation / Config / Deployment / Verification-only | Final disposition |
|---|---|---|---|
| GAP-003 EstablishLocalization 缺失、native reset epoch 未整合（§29–34） | WI-009–011 | Implementation / Config | 空 goal Action、native behavior、sole evaluator；同一 run 完成。 |
| GAP-001、GAP-002 | §23 Q5；以下 F rows 為內容追溯 | 未取得原始編號對照 | Review 補 alias 或批准 F registry 為完整 scope；不得猜配。 |
| GAP-004、GAP-005、GAP-006、GAP-007、GAP-008、GAP-009 | §23 Q5；以下 F rows | 未取得原始編號對照 | 同上，沒有宣稱這些 GAP 已關閉。 |
| GAP-010、GAP-011、GAP-012、GAP-013、GAP-014、GAP-015 | §23 Q5；以下 F rows | 未取得原始編號對照 | 同上。 |
| GAP-016、GAP-017、GAP-018、GAP-019、GAP-020、GAP-021、GAP-022 | §23 Q5；以下 F rows | 未取得原始編號對照 | 同上。 |
| F-001 scope、TF ownership、actual LiDAR *_1 inventory（§5–6,77–80） | WI-001,025 | Config / Implementation | canonical chain KEEP；修 interface/docs drift；實際安裝姿態 V2/V3。 |
| F-002 inactive read ERROR（§11） | WI-003 | Implementation | lifecycle-correct inactive feedback，無非零 write。 |
| F-003 sorted-ID / joint-index coupling（§12） | WI-002 | Implementation | semantic wheel identity，ID2-left / ID1-right。 |
| F-004 SYS-030 admission / independent stop attempts（§9） | WI-003,005–006 | Implementation / Config | software checks 與 bounded stop feedback；physical truth V2–V4。 |
| F-005 no exclusive command ownership、tool transport conflict（§8） | WI-004–005,010–011,016–017 | Implementation / Config | Q1 定案，所有 ingress 接入；無繞過路徑。 |
| F-006 3600 s DDC timeout（§10） | WI-006 | Config | finite candidate 0.5 s；V4 calibration。 |
| F-007 watchdog register mismatch、Modbus timing（§13） | WI-004 | Implementation / Config / Verification-only | 修 clear mismatch；host timeout 不冒稱 device watchdog。 |
| F-008 JSB exit failure still spawns DDC（§14） | WI-006 | Implementation | success-only chain + failure tests。 |
| F-009 controller odom default、EKF vx-only docs/tests（§15–17） | WI-007,013,025 | Config / Implementation | explicit filtered odom、vx+vy=0，sole EKF authority。 |
| F-010 measurement vs receive timestamps（§18） | WI-001,008–010,017,020 | Implementation / Verification-only | 保留 source stamps，無效不換 now；unknown acquisition latency 留 backlog。 |
| F-011 frozen readiness evidence 未實作（§19–26,60） | WI-008–009 | Implementation / Config | covariance + temporal consistency + persistence + epochs + stationary/moving semantics。 |
| F-012 scan-map/lost architecture obsolete（§27–28,77–79） | WI-008–011,025–026 | Implementation / Config | 全面移除，沒有 optional/debug compatibility。 |
| F-013 navigation admission、freshness、failure-owner recovery（§35–40） | WI-011,018 | Implementation / Config | no-ready 不開始 global navigation；只有 mid-task dependency loss 可 bounded recover。 |
| F-014 final yaw 被 distance skip 丟失（§42） | WI-012–013 | Implementation / Config | endpoint retains full canonical pose。 |
| F-015 path frame/continuity/join contract（§43） | WI-012 | Implementation | native planner/concatenation 周邊最小驗證。 |
| F-016 feedback path key、route errors（§44–45） | WI-013 | Config / Implementation | native path key + Jazzy supported error ports。 |
| F-017 station late goal acceptance / cancel race（§46） | WI-014 | Implementation | stale goal cannot escape cancellation。 |
| F-018 save root/collision/partial-save/site dataset（§47–49,75–76） | WI-015,023–024 | Implementation / Deployment | atomic unique dataset、shared root、required map/route fail-fast。 |
| F-019 local DockRobot flags/frames/lifecycle（§50–53） | WI-016,018 | Implementation / Config | local-only action、Vision frame contract、local infrastructure isolation。 |
| F-020 dock yaw/stopped/cancel/authority terminal gaps（§54–55） | WI-005,017 | Implementation / Verification-only | Q3 selected native extension；actual precision 另測。 |
| F-021 aggregator absence/producer alignment/disappearance（§56–61） | WI-009,019 | Config / Implementation | native aggregator；task results 仍為 task results。 |
| F-022 telemetry stale cache、bounds、deploy startup/storage（§62–63） | WI-020–021 | Implementation / Deployment | original timestamps + expiry，bounded outbound only。 |
| F-023 map-outside/lifecycle coupling/failure isolation（§64–68） | WI-011,016,018 | Config / Implementation | Q2 native activation policy；base/Teleop unaffected。 |
| F-024 fake mock、unsupported sim-time（§69–70） | WI-022 | Config / Implementation | production rejects unsupported true；test fixtures scoped separately。 |
| F-025 source/image/package/private/site provenance（§71,73–74） | WI-023–024 | Deployment | Q4 release policy + content identity。 |
| F-026 stale same-tag image（§72） | WI-024 | Deployment | provided artifact always verified/loaded/selected。 |
| F-027 whole-repo cleanup、dead tests/deps、claims（§77–80） | WI-025–026 | Implementation / Config | current docs match final model，history exempt。 |
| F-028 V1 plus V2/V3/V4 evidence separation（§82,89–95） | WI-027; §16–20 | Implementation / Verification-only | one-run V1；physical escalation separately gated。 |
| F-029 repo-specific evidence: zero-byte ignored maps/template; test_route path outside test tree; missing m1_settings link | WI-015,023–027 | Implementation / Deployment | invalid site samples not shipped as operational assets；hermetic test fixtures；remove broken claims。 |

SYS trace：Control SYS-022/026–030/034；TF/Sensors SYS-003–005/023；Localization SYS-007/010/045；Navigation SYS-008/011/013–020/025/032/033；Mapping SYS-001/002/006/024；Docking SYS-044；Diagnostics/Observability SYS-004/035–038/042。各 WI 再指定直接 owner，避免把任務失敗變成 health policy。

## 6. Obsolete / superseded inventory

以下路徑皆相對 repo root。`src/` 下名稱來自本輪讀取；新增檔名見 §12。沒有可證實的外部 lost/quality compatibility contract。此結論只涵蓋本 repo 與提供的契約，不能冒稱搜尋了外部 deployment；若 review 提出具體 consumer 契約，須先在 Q5 review 一併定案，不由 implementation 留殼。

| File / symbol / interface / config | Current purpose | Final architecture disposition | Action |
|---|---|---|---|
| localization `src/localization_monitor.cpp`, `src/localization_monitor_main.cpp`, `include/.../localization_monitor.hpp` | scan-map distance field、quality/lost detector/publishers | 由 readiness evaluator/node/task 取代 | REMOVE |
| `ScanMapQualityEvaluator{,Config}`、`LocalizationLostDetector{,Config}`、`LocalizationHealthState` | 舊 scan-map quality policy | 無獨立 requirement | REMOVE |
| localization `config/localization_monitor.yaml` | match_dist_m、occupied_threshold、min_valid_beams、beam_stride、lost/recover ratios/holds | 無 final consumer | REMOVE |
| localization `test/test_localization_monitor.cpp` | 舊 quality/detector assertions | 用新 readiness cases 取代 | REMOVE |
| `/localization/quality`, `/localization/lost` | old Float32 / inverted Bool | final interface 只剩 ready | REMOVE |
| navigation `is_localization_healthy_condition.{cpp,hpp}`、`wait_for_localization_healthy_node.{cpp,hpp}` 及兩個同名 tests | lost topic BT consumers | new ready guard + Establish action BT | REMOVE |
| `localization_monitor_lib`、monitor executable、兩個 healthy BT libraries 的 CMake/export | 舊 build/install entry | 換新 targets，乾淨 install 無殘留 | REMOVE |
| localization OpenCV include/find/link/package dependency、Float32 include | scan-map-only dependency | 若 repo search 無其他責任就移除該 package 的依賴 | REMOVE |
| localization `amcl_params.yaml` | native AMCL，set_initial_pose=true + zero pose | native AMCL KEEP；startup 未知 global pose 不造假 | MODIFY |
| `localization.launch.py` + monitor_params_file argument | 啟動舊 monitor | readiness config + same-capability task；刪 monitor arg | MODIFY |
| `route_assisted_nav.xml` whole-subtree RecoveryNode / `/amcl/reinitialize_global_localization` | all errors lead to reset | readiness-specific recovery + resolved native task integration | MODIFY |
| BT distance-only last-mile skip、`final_route_path` | route concatenation/following | full endpoint + common `{path}` feedback wiring | MODIFY |
| native Route Server/Navfn/MPPI/ConcatenatePaths/DDC/EKF/AMCL/SLAM | mature core | 不重寫 | KEEP |
| `nav2_params.yaml` odom/default error list/local dock config | mixed nav+docking settings | explicit authoritative odom/error codes/local lifecycle settings | MODIFY |
| `test_behavior_tree_runtime.cpp` private `maps/test_site` path / stub-only claims | BT factory + route tests | tracked fixtures + actual plugin integration；證據分級 | MODIFY |
| `navigate_to_station_app.*` pending-goal cancellation | native semantic adapter | race fix only | MODIFY |
| M1 fixed positions in state vectors / joint[0]/joint[1] fallback | accidental ID ordering | ID→wheel mapping | MODIFY |
| M1 inactive read ERROR / activate/deactivate assumptions | lifecycle and stop | native lifecycle + feedback checks | MODIFY |
| `m1_latency_check_main.cpp` `0x0511` watchdog read | wrong parameter register | documented watchdog register + specific test | MODIFY |
| M1 diagnostic/maintenance tools | required direct hardware verification | shared transport exclusion；保留硬體檢查用途 | MODIFY |
| DDC `cmd_vel_timeout: 3600` | effectively disabled command-loss protection | bounded 0.5 s candidate | MODIFY |
| `OnProcessExit` JSB→DDC unconditional continuation | spawner sequence | inspect returncode==0 | MODIFY |
| description ignored root/control Xacro | legitimate private robot input | 補 feedback state interfaces、移除假mock分支；維持private delivery/provenance | MODIFY |
| description ignored geometry Xacro + meshes | legitimate private robot geometry | canonical ownership KEEP；不猜測geometry校準 | KEEP |
| `base_lidar_link_FL`, `base_lidar_link_BR`, corresponding `*_1` frames | private description fixed frames | static inventory KEEP；actual emitted scan frame V2 | VERIFICATION ONLY |
| `scan_handedness_normalizer.py` + laser filters | deployed perception pipeline/diagnostics | 有獨立責任，不能因 scan-map removal 一起刪除 | KEEP |
| `ekf.yaml` vx + vy constraint; vx-only comments/tests | local motion authority | preserve configuration，修註解/test；print_diagnostics native enabled | MODIFY |
| `save_map.sh`, `site_resolution.py` | save/resolver roots differ、route optional | coherent dataset + fail-fast | MODIFY |
| ignored `maps/template/*` zero-byte files | release sample source | 不能當有效 site；不改 user assets，修 exporter 拒絕輸入 | VERIFICATION ONLY |
| docking `SimpleNonChargingDock` configured plugin + local-only caller flags | position-only success、flags not server guarantee | Q3 native extension + product enforcement | MODIFY |
| shared navigation lifecycle group including docking | global dependency couples local task | separate true dependency groups | MODIFY |
| absent native diagnostic_aggregator / EKF disabled diagnostic output | incomplete operator view | add aggregator、enable native evidence | MODIFY |
| observability latest caches/receive-now timestamps/fluent-bit root | resends stale data; deployment not integrated | expiry/source time/bounds/output contract | MODIFY |
| public mock=true → serial "mock" | misleading real plugin selection | fail-fast unsupported option + remove private fake branch in private delivery | MODIFY |
| public use_sim_time help/partial forwarding | implies unsupported full simulation | production true rejected; deterministic clock tests separate | MODIFY |
| `scripts/export_release.sh` generated start.sh same-tag skip | stale artifact selection | verified artifact identity and unconditional supplied-image load | MODIFY |
| `spec/*.md`, `operator/*.md` obsolete states/TF/stop/Initial Pose/observability claims | current descriptions | current baseline rewrite only in future run | MODIFY |
| historical ChatGPT file / past execution logs | historical evidence | immutable，not executable authority | KEEP |

沒有 KEEP TEMPORARILY / REMOVE LATER 的最終交付項。內部 migration 可短暫共存於同一 run 的工作樹，WI-026 與 V1 要確認最後移除。

## 7. Interface migration matrix

| Existing interface | Final interface | Consumers | Migration action | Removal point |
|---|---|---|---|---|
| `/localization/lost` Bool | `/localization/ready` Bool | Navigation guard/wait/BT、tests/docs | invert semantics；false/missing/silence fail closed；不保留 alias | WI-011 consumers 完成後 WI-026 刪 publisher/type references |
| `/localization/quality` Float32 | 無；evaluator diagnostics evidence | 舊 monitor tests/docs（未找到 production consumer） | remove score/calculation/thresholds | WI-008/009 + WI-026 |
| 尚未實作 `/localization/ready` | frozen Reliable/TL/Last1 Bool publisher | Navigation、Establish task、依 frame 需要的 Docking path | startup false + transition + heartbeat；consumer monotonic silence timeout | WI-009 加入，WI-011/017 integration |
| `/amcl_pose` | 同一 native PoseWithCovarianceStamped | evaluator | 使用 observation stamp、current epoch、distinct samples；不成為 public readiness policy | KEEP |
| `/initialpose`, `/map` | same external native messages | Localization capability + native AMCL | invalidate epoch/history；Q7決定Initial Pose有序套用與無reset觀測；map接納同epoch規則 | KEEP external API；WI-009/010 internal migration |
| wrong `/amcl/reinitialize_global_localization` | namespace-resolved native `reinitialize_global_localization`，root launch 為 `/reinitialize_global_localization` | Establish task only | remove scattered BT reset；call internal epoch barrier before native request | WI-010/011 |
| no EstablishLocalization action | `/establish_localization`, `mobile_base_interfaces/action/EstablishLocalization` | external task caller、Nav2 recovery BT | empty Goal，terminal status，3 failure categories，phase feedback | WI-010 |
| DDC raw odometry / assumed `/odom` | DDC raw remains；consumer motion `/odometry/filtered` | EKF input vs Controller/BT/Docking output consumers | explicit `odom_topic` supported configuration；不新增 `/odom` producer | WI-007/013/017 |
| shared controller cmd_vel ingress | source-specific nav/dock/teleop/observation ingress → Q1 exclusive gate → sole DDC TwistStamped input | all motion producers/tools | preserve native message type；no direct teleop/docking bypass | WI-005/006/010/016 |
| native NavigateToPose | same action | generic caller/station | BT admission + bounded localization-only recovery；native terminal result | KEEP，WI-011–014 |
| native DockRobot | same action | local explicit docking caller | enforce local goal flags、frames、fresh Vision + terminal stop，no replacement action | KEEP，WI-016–017 |
| `navigate_to_station` CLI adapter | same station ID → native NavigateToPose | operator/upstream app | late response cancellation fix，no new mission action | KEEP，WI-014 |
| `/diagnostics` | `/diagnostics` plus native `/diagnostics_agg` | operator/observability | component evidence grouped/stale；ready 不從 aggregator 反推 | WI-019 |
| telemetry/latest + Fluent Bit outputs | same outbound protocols with explicit source/receive time, expiry, bounded buffer | backend | stale samples expire，不重寫成新量測；startup opt-in/isolated | WI-020/021 |
| implicit save `${repo}/maps` vs resolver env root | shared `MOBILE_BASE_MAPS_DIR` root + explicit dataset path | map save、Navigation/site、release | single precedence + atomic immutable dataset identity | WI-015 |
| same release tag treated as identity | verified archive/image ID + manifest | generated start script/operator | load supplied archive，compare loaded image content，verify selected container image | WI-023/024 |

## 8. Work Items

共同規則：每項先增加/調整能辨識需求違反的既有 package test，再實作及執行相應 container suite；不可把 test 改成接受 defect。每項的 **Physical verification dependency** 不阻止已批准 software implementation 與 V1 完成，但禁止把它標記 hardware-validated。Q 分支須在 run 前確定。

### WI-001 — Canonical TF、感測器 frame 與 timestamp provenance

- **ID / Subsystem / Purpose:** WI-001；Description / Perception；保留唯一 TF 與誠實時間語義。
- **Approved requirement / gap addressed:** SYS-003/004/005/023；F-001/F-010。
- **Files/components likely affected:** description/perception launch、description `urdf/README.md`、`meshes/README.md`、perception `scripts/scan_handedness_normalizer.py`、`tdk_ros2_imu/tdk_imu_node.py`；現有 description、perception、IMU、bringup `test_tf_authority.py` / `test_perception_dataflow.py`。
- **Exact planned changes:** [ ] inventory private root/control/geometry Xacro 與 sensor frames；已見 `base_lidar_link_FL/BR` 及兩個 `*_1` fixed children，driver `publish_frame_id` 與實際 emitted header 分開記錄。[ ] 保留 RSP 固定 TF、SICK `tf_publish_rate=0`、DDC odom TF disabled、EKF dynamic TF。[ ] source stamp 存在即保留；IMU 59-byte packet 沒有 device time，明確標為 host receive/publish-time estimate，保留 monotonic receipt age；不得宣稱 acquisition timestamp。[ ] Scan normalizer 針對反轉後 first-ray stamp、signed time_increment、scan_time 保持同一 ray-time 對應，不用 now() 修補 invalid stamp；實際 driver timing 未知時保留原始資訊並標記限制，不猜 latency。[ ] future/zero/out-of-order measurement-time inputs 由 consumer fail closed/ignore，不能把 cached sample 刷新為新量測。
- **Removal/migration implications:** 修正把 TF 最新時間當 localization quality、frame 名稱或 mount 先驗當實機證明的 comments/docs；保留獨立 scan normalization/filtering。
- **Dependencies:** 無；與 WI-022 production time contract 一致。
- **Acceptance criteria:** canonical ownership 無重複 publisher；static frame inventory 包含 *_1；timestamp provenance 對 IMU/LiDAR/M1/Vision 都有 evidence class；未新增 driver/TF authority。
- **V1 software verification:** 現有 TF/dataflow tests + timestamp zero/future、buffered IMU packets、scan reversal ray-time mapping fixtures；private Xacro 可用時在 container expand/URDF parse，不執行硬體 node。缺 private inputs 要明確 blocker，不能以 skip 當 full V1 PASS。
- **Physical verification dependency:** V2 actual scan headers/TF/device clocks；V3 mounting/sign/latency；production covariance 校準。
- **Out of scope:** 校正 geometry、重寫 vendor driver、推測實體 sensor axes 或 acquisition latency。

### WI-002 — M1 ID-to-wheel identity 與 measured-feedback validity

- **ID / Subsystem / Purpose:** WI-002；Control；消除排序偶合並維持 measured-only wheel state。
- **Approved requirement / gap addressed:** SYS-022/029；F-003。
- **Files/components likely affected:** `m1_driver.{cpp,hpp}`、`m1_hardware.{cpp,hpp}`、`m1_diagnostics.cpp`、使用 state vector 的 `m1_*_check_core.cpp`；`test_m1_driver.cpp`、`test_m1_hardware.cpp` 及 tool tests。
- **Exact planned changes:** [ ] 以 explicit motor_id 查找 state，wheel interface 以 joint name/side 對應，固定 left=2/right=1；URDF declaration order 不決定 side。[ ] reject duplicate/missing/unexpected required IDs；每次 activation/read/exchange/diagnostic 使用同一 identity contract。[ ] protocol 必要的 on-wire ordering 可保留，但不得成為 semantic identity。[ ] 明確 cache sample generation/receipt age、paired feedback validity；讀取失敗不能沿用舊數值冒充本 cycle valid，不用 command 值替代。
- **Removal/migration implications:** 移除 `states[0]=right/states[1]=left` 及 joint[0]/joint[1] fallback；有独立 protocol 用途的 sorting KEEP。
- **Dependencies:** 無；WI-003/004 使用此 mapping。
- **Acceptance criteria:** 同一 physical fact 在 joint/state vector 任意排列下輸出相同 left/right；fault/stale 狀態可觀測且 motion 不被 admission。
- **V1 software verification:** existing hooks 注入兩種排列、missing/duplicate ID、one-wheel fault、stale sample、negative/invalid decoding；DDC mocked measured-feedback integration 不使用命令當 feedback。
- **Physical verification dependency:** V2 real ID/status wiring；V3/V4 signs/scale/wrap/gear ratio。
- **Out of scope:** 改 Left/Right hardware IDs、重新選 encoder conversion 或 calibration。

### WI-003 — ros2_control lifecycle 與 SYS-030 admission / stop

- **ID / Subsystem / Purpose:** WI-003；M1 hardware；inactive 可合法讀取，active motion 有有效 admission，停用逐項嘗試停止。
- **Approved requirement / gap addressed:** SYS-026/029/030；F-002/F-004。
- **Files/components likely affected:** `src/mobile_base_control/src/m1_hardware.cpp`、header、既有 `test_m1_hardware.cpp`、driver stop/disable helpers。
- **Exact planned changes:** [ ] INACTIVE read 不因 inactive 本身 ERROR；只回報實際 feedback/connection 故障，read 不 enable 或下非零 command；inactive write 不造成 motion。[ ] activate 前確認兩輪 fresh measured stopped、communication/alarms 正常，enable 後比對 vendor-defined ready state；未知 status 不採「不是6就可動」。[ ] 共享既有 lifecycle 內的 bounded stop procedure：撤 admission、zero/stop、poll valid RPM evidence、嘗試 disable、記錄各結果；任何一步失敗仍嘗試剩餘安全動作。[ ] 套用 deactivate/error/shutdown/cleanup 相關路徑；拿掉固定 sleep 20ms 當 stop proof、無条件 SUCCESS/log。[ ] 暴露 controller/M1 state 和 stop-evidence availability 給 WI-005，不新增 physical safety guarantee。
- **Removal/migration implications:** 更新 `ReadWithoutValidStateFails` 等混淆 inactive 與 fault 的 tests；使用或移除未生效 `stop_poll_max_attempts`，不保留死參數。
- **Dependencies:** WI-002。
- **Acceptance criteria:** valid INACTIVE read cycle 不觸發 error teardown；moving/unknown/stale feedback 拒絕非零 admission；每種 stop fault 都仍嘗試 disable；失敗不回報已確認停止。
- **V1 software verification:** real ResourceManager + mocked hardware configure/inactive/activate/deactivate cycles；alarm/moving precheck、enable failure、stop failure、poll timeout、disable failure/cleanup 狀態 assertions。只證明 software sequence。
- **Physical verification dependency:** V2 lifecycle/feedback，V3 controlled stop/servo，V4 physical stopping；E-stop/STO independent。
- **Out of scope:** safety certification、device watchdog 保證、以 zero command 推論 physical stopped。

WI-003→WI-005 的具體 feedback contract：M1Hardware 透過既有 ros2_control state interfaces 暴露每個 wheel 的 `velocity`、`feedback_valid`（0/1）、`feedback_stamp`（最近成功讀取的 host ROS time seconds）、`drive_ready`（0/1）、`faulted`（0/1）；native JSB 的 `/dynamic_joint_states`（`control_msgs/msg/DynamicJointState`）按 joint/interface **名稱**輸出。freshness 必須同時檢查該 sample stamp 與 consumer monotonic receipt age，JSB 重複 publish 舊數值不能刷新 measured evidence。controller availability 來自 native controller_manager state，具 bounded refresh/expiry。handoff grant 要求兩輪 fresh measured stop、無 fault、drive ready 與適當 controller state；**fresh EKF predicted output alone 不足以授權**。private control Xacro 加必要 state-interface declarations，保持 private，manifest 記錄新 hash。V1 加「EKF仍更新但 wheel feedback已過期」拒絕grant測試。INACTIVE 沒有 active exchange 時，不可把預期缺少新 sample 當硬體 ERROR；允許 read-only measurement，或回報 callback OK 並把 measurement availability 標為 invalid，絕不製造零速量測或偷偷 enable。

### WI-004 — M1 transport exclusivity、watchdog register 與 host timeout

- **ID / Subsystem / Purpose:** WI-004；Driver / maintenance；避免同時開啟 transport 並修正可證明的通訊錯誤。
- **Approved requirement / gap addressed:** SYS-026/027/030；F-005/F-007。
- **Files/components likely affected:** `m1_driver.*`、`m1_latency_check_main.cpp`、所有 direct M1 tools 的 connect/config path、control tests/launch response-time params。
- **Exact planned changes:** [ ] 在共用 driver transport open 層加入以實際 serial device identity 為基準的 OS exclusivity；所有 production/maintenance/read-only tool 都適用，alias path 不能繞過。[ ] second opener 在 I/O/servo 前失敗，disconnect/process exit 釋放；維護前需 normal runtime revoke/cancel/stop/disable/release。[ ] vendor COMM table 05-17 watchdog EEPROM `0x0510` / RAM `0x4110`，`0x0511` 是 05-18 error-count；修工具常數/標籤/tests，effective runtime protection 同時觀察 05-21 RAM `0x4114`，不自動寫 EEPROM。[ ] response timeout 與 byte timeout 顯式設定並檢查 return；加完整 transaction deadline/overrun fail-closed handling（含 partial response、inter-slave delay）。[ ] 不把 50ms 解釋成 30Hz 的 33.3ms loop 可保證完成；保存 deadline/timeout/loop-period 關係與 overrun diagnostics，實測前不任意調小至「剛好符合」。
- **Removal/migration implications:** 刪錯寄存器 assertion、隱含 timeout、允許共享 transport 的工具說明；保留既有 FC17/timing/dynamic 檢查工具。
- **Dependencies:** WI-002/003。
- **Acceptance criteria:** 同裝置雙開拒絕；有界 timeout 路徑不留下 motion permission；工具正確分辨 ROS command loss、host Modbus timeout、device watchdog、E-stop/STO。
- **V1 software verification:** existing pseudo-TTY / fake transport tests：aliases/second open/crash release、no-first-byte/partial-byte/never-complete response、deadline overrun、both ID registers、timeout configuration failure。
- **Physical verification dependency:** V2 transaction timing/effective registers；V3/V4 authorized comm-loss/reconnect/watchdog behavior；不可由 register read 推論 protection 有效。
- **Out of scope:** 隨意修改 device watchdog、EEPROM、serial real-time architecture 或新增異步 driver framework。

### WI-005 — 唯一 motion-command authority 與 handoff

- **ID / Subsystem / Purpose:** WI-005；Control admission；實現 at most one effective owner，涵蓋所有 velocity producers。
- **Approved requirement / gap addressed:** SYS-022/025/026/027/030/034/044/045；F-004/F-005；**Q1 先決**。
- **Files/components likely affected:** control 新 `motion_authority.*` / node / config / tests；interfaces（Q1 推薦方案）；navigation/behavior/docking launch remaps、`scripts/teleop_keyboard.sh`、operator commands、bringup stop-chain tests。
- **Exact planned changes:** [ ] 依 Q1 定案加入最小 exclusive gate，DDC 下游唯一 publisher；來源分成 `/motion/navigation/cmd_vel`、`/motion/docking/cmd_vel`、`/motion/teleop/cmd_vel`、`/motion/localization_observation/cmd_vel`，native Twist/TwistStamped 的轉接只在已知來源邊界進行。[ ] startup/restart owner=none；serial maintenance 不可與 runtime 共存。[ ] acquire/handoff 必須 revoke → cancel/terminate old execution → explicit stop → fresh stopped feedback/controller state confirmation → grant；timeout/fault 留 none，不能自動降級到另一仍在發布的來源。[ ] steady-clock lease expiry、source silence、controller unavailable 都 revoke；source stamp invalid/stale/future 或 pre-grant queued commands 不接納。[ ] native cancel target 按 execution scope：external takeover 終止原任務；Navigation 內部 localization recovery 只 halt/cancel FollowPath，保留 parent goal，temporary grant 給 observation；不能把自己的 NavigateToPose 一起取消。[ ] terminal/cancel 任務要先 relinquish，晚到 callback 無法重新拿舊 authority；stop-evidence unknown 不 grant。[ ] observer/evaluator 從不發 motion command。
- **Removal/migration implications:** 移除 direct DDC remaps 和舊 tests 的無 mux/直連 assertion；所有已聲明來源接入，沒有 compatibility bypass。
- **Dependencies:** WI-002–004；Q1；上層 adapter integration 在 WI-010/011/016/017，最後 WI-027 證明閉合。
- **Acceptance criteria:** competing commands 不能混入；非 owner 不能影響輸出；source/gate crash 由 gate/DDC timeout 各層 fail closed；fresh wheel feedback 與 EKF stop evidence 明確分級。
- **V1 software verification:** concurrent requests、continuing canceled publisher、late/pre-grant messages、expired lease、owner death/restart、gate crash + native DDC timeout、missing/stale/nonzero stopped feedback、internal recovery handoff、transport second opener；assert output/action cancel/order，不只測 YAML。
- **Physical verification dependency:** V2 wiring/no unexpected command，V3 handoff/in-place stop，V4 physical command-loss stop；controller crash/device watchdog 不由 V1 保證實體停止。
- **Out of scope:** Navigation/Docking/AMR Manager、business scheduling、custom kinematics、safety-rated stop。

WI-005 same-source fence：內部 source adapter 將 command 包成 `MotionCommand`（source_id、lease_id、`geometry_msgs/TwistStamped command`），DDC 仍只接原生 TwistStamped。gate 比對當次 lease，舊 tagged command 即使帶新時間戳也拒絕。native raw stream 在新 lease 前須已確認舊 execution terminal、撤舊 adapter generation、清 queued callbacks/commands，並設 grant measurement-stamp barrier；不能把晚到的舊 raw command 隨手貼上新 token。pending/cancel outcome 未知時禁止同 source regrant，cleanup client 持續處理 late handle。V1 必測 same-source cancel→new goal→old fresh-stamped callback、cancel ACK 但無 terminal、舊 Spin late acceptance；Q1 要批准此完整 fence，不能只批准「加 mux」。

### WI-006 — DDC timeout 與成功後才啟動 controller chain

- **ID / Subsystem / Purpose:** WI-006；Control launch；correct startup + bounded command-loss protection。
- **Approved requirement / gap addressed:** SYS-027/030；F-006/F-008。
- **Files/components likely affected:** `base_control_params.yaml`、`base_control.launch.py`、bringup `mobile_base.launch.py`、`test_base_control_launch.py`、`test_motion_command_stop_chain.py`。
- **Exact planned changes:** [ ] 用既有 tests 已要求的 `cmd_vel_timeout=0.5` 秒作 **UNVERIFIED / REQUIRES CALIBRATION** candidate，透過 single parameter source 配置且驗證正有限值，不保留 3600。[ ] JSB spawner process exit callback 必須 returncode==0 才建立 DDC spawner；failure/timeout/shutdown 不繼續啟動 motion。[ ] 將 error 留在 local control evidence，避免 unconditional continuation；DDC stamp/type/remap 與 WI-005 一致。
- **Removal/migration implications:** 刪 `#0.5` 模糊註解與無條件 OnProcessExit chain；operator 說明 timeout 是 command-loss protection。
- **Dependencies:** WI-005 command ingress contract；可先寫 spawner tests。
- **Acceptance criteria:** failed JSB 不啟動 DDC；停止 valid input 後 native controller timeout 生效；不聲稱 0.5s physical stop。
- **V1 software verification:** returncode 0/nonzero/timeout/shutdown launch_testing；native DDC + supported test hardware 發一筆非零後不再發，確認 command 被歸零；無串口/真馬達。
- **Physical verification dependency:** V2 controller lifecycle；V4 delay/deceleration/stopping calibration。
- **Out of scope:** 改寫 DDC、硬體急停設計。

### WI-007 — EKF authoritative odometry 與 consumer wiring

- **ID / Subsystem / Purpose:** WI-007；State Estimation / Navigation；保留唯一 local-motion authority。
- **Approved requirement / gap addressed:** SYS-005/015/016；F-009。
- **Files/components likely affected:** state_estimation `config/ekf.yaml`、test/launch；navigation `nav2_params.yaml`；bringup feedback chain tests；spec State Estimation 段落。
- **Exact planned changes:** [ ] preserve DDC measured raw wheel odom、EKF `vx + vy=0` constraint + gyro yaw-rate；update vx-only test/comments。[ ] `controller_server.ros__parameters.odom_topic: /odometry/filtered` 明確設定（bt_navigator 現在已有不代表 controller 已有）；Docking/observation stop consumers 也指定該來源。[ ] `enable_odom_tf=false` on DDC、EKF 唯一 `odom→base_footprint`；不新增 `/odom` publisher。[ ] covariance 保持候選/現有 config，沒有校準證據不改名為 calibrated。
- **Removal/migration implications:** 移除 `/odom` 隱含權威與 `vx only` drift；不刪 native odometry producer。
- **Dependencies:** WI-001/002。
- **Acceptance criteria:** resolved runtime controller subscription 指向 filtered odom；fusion masks 和 docs/test 相符。
- **V1 software verification:** load evaluated YAML/remaps，non-hardware controller 用 synthetic `/odometry/filtered`；只向 `/odom` 注入資料不能滿足 authoritative stop gate；TF duplicate-publisher static checks。
- **Physical verification dependency:** V2 topic/TF/receipt，V3 yaw agreement，V4 translation scale/covariance。
- **Out of scope:** custom EKF、新 local-motion authority、猜 IMU bias/scale。

### WI-008 — Frozen Localization Evaluator 純 evidence core

- **ID / Subsystem / Purpose:** WI-008；Localization；實作批准 evidence model，完整取代 scan-map policy。
- **Approved requirement / gap addressed:** SYS-010/045；F-011/F-012。
- **Files/components likely affected:** 新 `localization_evaluator.{hpp,cpp}`、`test_localization_evaluator.cpp`；替換 monitor core build target。
- **Exact planned changes:** [ ] 單一純 evaluator snapshot 包含 readiness/reasons/covariance/residual/persistence/epoch，不計算 scan endpoints 或 map matching。[ ] availability 包含 current map/reference、fresh localization scan、valid authoritative local motion、observation-time TF、current-epoch AMCL pose。[ ] AMCL covariance valid/finite/nonnegative、planar covariance structure 合理且低於 configured limits 才有資格 READY；高 uncertainty 是 veto，低 covariance 不是充分證據。[ ] 以 AMCL pose 得 G1/G2、observation-time EKF TF 得 O1/O2，算 `G2_expected=G1*(O1^-1*O2)`、`Residual=G2_expected^-1*G2`，檢查 planar norm 與 wrapped yaw；正常運動/正常 drift correction 不應因 global pose 改變而失敗。[ ] consistency 只評單次觀測；NOT_READY→READY 另需 N 個 strictly newer/distinct stamps + good persistence duration；timer/replayed sample 不增加 count。[ ] 已 READY stationary 時，依持續有效 dependencies 與 unreviewed-motion allowance 有界 reuse；不因 AMCL 靜止時沒新 publish 自動判死。累積移動超 allowance 開始 update-response deadline，逾期撤 ready；用 path travel/absolute yaw accumulation 避免來回移動淨位移為零繞過。[ ] 不跨 epoch 或異常 clock jump 搬用 anchors；無法觀測 motion 就 NOT_READY。
- **Removal/migration implications:** 移除 scan-map core/thresholds/detector tests，不將其保留成 debug evidence。
- **Dependencies:** WI-007 data contract。
- **Acceptance criteria:** 必須同時滿足四類 evidence；單筆 low covariance 或持續 tick 永遠無法從 startup 變 READY；正常 motion、yaw wrap、drift correction 正確。
- **V1 software verification:** deterministic sequences：straight/arc/rotation、±π wrap、small drift correction、large incompatible jump、NaN/negative/high covariance、duplicate/out-of-order/future observations、moving beyond allowance/no update、stationary reuse、round-trip travel、dependency death、epoch reset。人工數學 expected residual 與 evaluator 比對。
- **Physical verification dependency:** V3/V4 residual/covariance/persistence/update cadence calibration；不能由 software sequences 證明定位真實正確。
- **Out of scope:** scan-map quality、custom localization filter、global pose 必須不動的檢查。

### WI-009 — Readiness ROS node、epoch、QoS 與同源 Diagnostics

- **ID / Subsystem / Purpose:** WI-009；Localization；唯一可依賴的 ready authority 與可解釋 evidence。
- **Approved requirement / gap addressed:** SYS-010/035/045；F-010–012/F-021；GAP-003 reset coordination 邊界。
- **Files/components likely affected:** 新 `localization_node.{hpp,cpp}` / main、`localization_readiness.yaml`、node/launch tests；localization launch/CMake/package。
- **Exact planned changes:** [ ] bind `/map`、`/scan_front`、`/amcl_pose`、`/initialpose`、authoritative EKF TF/odom，原始 measurement stamp 與 monotonic receipt time 分開保存。[ ] create ready publisher frozen QoS，初始化第一件事 false；publish transition + wall heartbeat，timer 只重評 availability/expiry，不製造 AMCL observations。[ ] startup new internal epoch；initialpose 和 accepted new map 立即 false、epoch++、clear anchors/covariance/count/history；duplicate delivery 同一 map 不自行假造新版本。[ ] reset coordination 與 WI-010 在同一 capability process serialized callback/internal API，`begin_epoch(reason)` 先 invalidation，再 native reset；reset in-flight 不得恢復 READY，response watermark 後才接納新 observation；late result/callback 帶內部 generation，不能污染下一 task/epoch。[ ] reject pre-start/pre-invalidation durable AMCL sample 與 zero/future stamp，不用 now 替代。沒有 public epoch/service/map DB。[ ] diagnostics 從**同一 snapshot、同一 thresholds**產生 ready/epoch/AMCL validity/covariance/residual/unreviewed motion/persistence/dependencies/reasons；Bool 不足以判明 AMCL process 是否死亡，diagnostics 不冒稱死因。
- **Removal/migration implications:** new executable/config 替換 monitor；WI-026 最後刪舊 publishers；保留只讀 native AMCL estimator。
- **Dependencies:** WI-008；本項定義 internal `begin_epoch`/pending-primitive barrier，供後續 WI-010 使用；Q7 prior integration先批准。
- **Acceptance criteria:** only one ready publisher；startup/epoch immediately false；有明確 lease/heartbeat silence 契約供 consumer fail closed；operator evidence 與 ready 永遠同源。
- **V1 software verification:** real ROS QoS late join、startup false、transition/heartbeat、publisher death、AMCL durable old sample、map/initialpose races、TF unavailable at observation time、clock rollback、reset completion delay、diagnostic snapshot equality。consumer 對 retained true 先視為 provisional，必須收到後續 live heartbeat 才 admission；測試 publisher 已死時 retained true 不能授權。
- **Physical verification dependency:** V2 actual QoS/TF/interfaces；V3/V4 ready false-positive/false-revoke calibration。
- **Out of scope:** public reset manager、invalidation-hold API、額外 quality policy或四態 public readiness。

### WI-010 — EstablishLocalization Action 與 native reset / Spin

- **ID / Subsystem / Purpose:** WI-010；Localization task；在同一 full-system run 關閉 GAP-003。
- **Approved requirement / gap addressed:** SYS-010/045；GAP-003、F-005/F-010/F-013。
- **Files/components likely affected:** 新 `src/mobile_base_interfaces/action/EstablishLocalization.action` 與 interface package；localization `establish_localization_task.{hpp,cpp}`、tests；launch/config；navigation behavior_server configuration。
- **Exact planned changes:** [ ] repo 無既有 action definition；新增最小 ROS 2 Action：空 Goal；Result `uint16 error_code`，`NONE=0`、`GLOBAL_LOCALIZATION_FAILED=1`、`OBSERVATION_MOTION_FAILED=2`、`LOCALIZATION_NOT_ESTABLISHED=3`；Feedback `uint8 phase`，INITIALIZING/OBSERVING/EVALUATING。無 Pose、success bool、caller spin/threshold/map。[ ] task 與 observer 邏輯分離，共同 node 僅為內部 epoch 原子化；task 可呼 internal invalidation，evaluator 不發 motion。[ ] 正常 Initial Pose 流程不呼此 action；explicit Establish 才用已定 policy：確認 native dependencies/map → invalidate epoch → native reset response → no-motion update 取得觀測 → bounded native Spin（需要更多觀測時）→ wait same evaluator ready。[ ] 使用 namespace-resolved native service，root 為 `/reinitialize_global_localization`；禁止四處 direct resets。[ ] Spin 使用 local odom/costmap/collision checks，透過 WI-005 temporary owner；ready 達成或 cancel 時 cancel Spin、stop/confirm/release 後才 terminal。[ ] 全部等待非阻塞且 bounded；reset/Spin goal response 遲到、cancel race/new epoch 都有 generation fencing；global reset 失敗留 NOT_READY。避免發生 ready 但 Spin 尚有 authority 就 success。
- **Removal/migration implications:** BT direct ReinitializeGlobalLocalization + old healthy wait 刪除；不新增另一 readiness service/pose channel。
- **Dependencies:** WI-005,007–009；本項 package integration fixture 提供 native local behaviors/costmap，WI-018 才完成 canonical deployment wiring，沒有循環 implementation prerequisite。
- **Acceptance criteria:** native primitive success 不等於 localization established；Action terminal success 必須 same epoch READY 且 observation motion 已停止/released；失敗 category 有限且 caller 可分辨。
- **V1 software verification:** empty-goal interface generation、phase/result、native namespace endpoint、reset unavailable/timeout、Spin failure、ready timeout、cancel before reset reply/before Spin acceptance/during Spin/at ready；每一 race terminal exactly once 且無 late motion。
- **Physical verification dependency:** V2 interfaces only；V3 明確授權的 in-place observation；V4 moving readiness；reset 不是 ground-truth proof。
- **Out of scope:** blocking service task、自寫旋轉控制、particle-filter reset algorithm、arbitrary external native reset support。

WI-010 unresolved native primitive contract：generation fencing 不能撤回已送出的 AMCL service request。Action 本身可在 deadline 回傳 failure/canceled，但 node 仍保留 reset/Spin cleanup state 與 client；reset outcome 未知期間維持 NOT_READY，禁止新的 reset/Spin/同來源 grant。native response 確認後重新建立 observation watermark，late accepted Spin handle 必須取消並確認 terminal；不能丟棄 future 後接新任務。若原 native server 永遠無回應，保持 capability unavailable，明確 controlled native lifecycle restart 才能解除，不自動猜成功。V1 包含 timeout→新 task request被拒→old reset reply/Spin acceptance→cleanup→全新 epoch/evidence。

WI-009/010 的正常 Initial Pose 路徑另有 **Q7 先決**：explicit Establish Action 仍是主動重建任務；Initial Pose bootstrap 不呼 Global Localization、不 Spin、不冒用 Action success。由既有 task layer 的小型 internal operation 套用 native prior 並取得 distinct native observations，evaluator 僅觀察。確切推薦流程見 Q7；tests 加 stationary prior、multiple fresh scans、native service callback reorder、new prior/map during bootstrap、timeout及late reply。bootstrap bounded候選10s，超時留NOT_READY與diagnostic reason，不無限retry。

### WI-011 — Navigation admission、ready migration 與有界 recovery

- **ID / Subsystem / Purpose:** WI-011；Navigation；保留 native NavigateToPose，按 failure owner 處理。
- **Approved requirement / gap addressed:** SYS-010/015/017/025/045；F-012/F-013；**Q6 admission integration 先決**。
- **Files/components likely affected:** new ready-condition / Establish action BT plugins、必要的 native navigator admission plugin（Q6）；`route_assisted_nav.xml`、navigation launch/CMake/config；existing healthy/BT tests。
- **Exact planned changes:** [ ] all internal consumers 用 ready=true permission；false/missing/silence stale 一律不信賴 global localization，不讀 diagnostics/covariance。[ ] consumer QoS compatible with frozen publisher；retained initial true 不作新的 live-authority 證據，需後續 heartbeat，steady-clock timeout，restart/new writer fail closed。[ ] 新 goal/preemption 每次重新 admission；NOT_READY 不呼 planner/FollowPath/Establish，native task 拒絕/失敗原因明確。[ ] mid-navigation ready loss：立即 halt/cancel FollowPath、WI-005 stop handoff、一次 bounded EstablishLocalization、success 後 clear old path/error/pose cache，保留原目標並重新 route/first/last plan；失敗 abort 原 goal，沒有無限 retry。[ ] route/planner/controller/goal-invalid failure 不走 localization recovery；依 native result/recovery owner 回報。[ ] Q6 限制任意 `goal.behavior_tree` 繞過 gate；不新增 wrapper action。
- **Removal/migration implications:** migrate every lost subscriber、remove healthy/lost node exports/tests；old all-failure reset branch entirely removed。
- **Dependencies:** WI-005,009–010；Q6 與已批准 Q2 startup contract；WI-018 在後續完成 deployment composition。
- **Acceptance criteria:** direct/station navigation 都遵循同一 ready gate；只有已開始 task 的 readiness loss 觸發 recovery；new goal 不繼承前 goal admitted/retry state。
- **V1 software verification:** real production BT factory/plugins + synthetic native actions；initial false/missing/stale/retained true、loss during FollowPath、one reset only、failed retry、goal preemption、cancel during recovery、arbitrary BT override、route/planner/controller failure 不 reset、old callback 不 resume。
- **Physical verification dependency:** V3 observation ownership；V4 short navigation/cancel/recovery；實體 map-outside workflow。
- **Out of scope:** always-localize-before-navigation、自訂 Navigation Action/Manager、generic Spin recovery。

### WI-012 — First/Route/Last path joining 與 final yaw

- **ID / Subsystem / Purpose:** WI-012；Route integration；correct project path contract without replacing native planners。
- **Approved requirement / gap addressed:** SYS-011/013/018–020/016；F-014/F-015。
- **Files/components likely affected:** `route_assisted_nav.xml`、new small path-contract BT adapter/header/test；`test_behavior_tree_runtime.cpp`、tracked route fixture。
- **Exact planned changes:** [ ] retain native ComputeRoute、Navfn、MPPI、ConcatenatePaths；在其輸入/輸出周邊驗證有效 finite poses/quaternions、map frame 一致、segment join 位姿連續，不做另一 planner。[ ] transform only when actual required TF at relevant stamp available；既定 native map paths 若混 frame 就明確 failure，不能改 header 假裝 transform。[ ] consecutive duplicate junction 可移除但不能丟 requested final orientation；不可用 append goal 方式補上沒有規劃/碰撞檢查的 gap。[ ] Last Mile 只在完整 endpoint 已滿足 position+yaw 契約時省略；同 XY 不同 yaw/short-distance 仍把 canonical goal orientation 傳給 FollowPath/goal checker；必要時 native connector 即使很短仍產生。[ ] empty/one-pose routes、First Mile omitted、Last Mile omitted 都有明確 semantics；route failure 不 fallback 到自訂/全自由空間路網外導航。
- **Removal/migration implications:** remove distance-only skip 的錯誤期待；替換測試中不連續 segment append 被當正確的 assertion。
- **Dependencies:** WI-011 BT structure；可先獨立寫 path-contract tests。
- **Acceptance criteria:** final executed path 終點保留 validated canonical pose/yaw；frame/continuity failure 在 FollowPath 前攔截。
- **V1 software verification:** first/last needed/skip matrix、same XY different yaw、±π yaw、single/empty path、mixed frames、TF absent、duplicate joins、gap beyond tolerance；載入實際 native ConcatenatePaths plugin。
- **Physical verification dependency:** V4 low-speed short goal/final yaw；route operational constraints 實場證據另列。
- **Out of scope:** custom Route Server/Navfn、road-network business semantics、未批准 route fallback。

WI-012 endpoint 與容差規則：上文「完整 endpoint 已滿足契約」在 connector skip 處指**數值上重合**（position/yaw epsilon 1e-6，非 production goal tolerance）。Last Mile planner 明確 `tolerance=0.0`、`use_final_approach_orientation=false`，使用 native Navfn 的 canonical goal，不接受其 nearby-best-pose fallback 取代原 goal。path-contract node 必須確認最終 pose 與原始 canonical goal 一致；不能只落在一般到站容差內就替換 goal。FollowPath 的 goal checker 因而對準同一 canonical target。V1 加 route-end 偏0.2m + robot同向偏0.25m、以及 Navfn nearby endpoint 的反例：不能把0.45m誤差判成功；不可追加未規劃直線 segment 來蒙混過關。

### WI-013 — Native Navigation feedback、failure codes 與 fresh stopped goal

- **ID / Subsystem / Purpose:** WI-013；Navigation result；成功/失敗/feedback 指向真正執行中的 path 與有效 motion evidence。
- **Approved requirement / gap addressed:** SYS-015/016/017/025；F-009/F-014/F-016。
- **Files/components likely affected:** `nav2_params.yaml`、BT XML、new `fresh_stopped_goal_checker.{hpp,cpp}` plugin/test、navigation build/plugin export/BT runtime tests。
- **Exact planned changes:** [ ] use native standard blackboard `{path}` throughout final path / FollowPath / navigator feedback，移除 final_route_path 漂移。[ ] Jazzy `error_code_names` 加 `compute_route_error_code`，每個 goal/reset clear own error fields；保留 native supported numeric results，localization category 在 integration node 傳成有限 error field；不假設 rolling error_msg ports。[ ] native StoppedGoalChecker 繼續負責 pose/yaw/velocity predicate；最小 derived/wrapping GoalChecker 加 `/odometry/filtered` sample stamp/receipt freshness prerequisite，default zero/cached stale twist 不能成功；同樣接受 configured candidate thresholds。[ ] task terminal 與 authority release 協調：所有路徑停止 pending command ownership，再 native result；不得以 feedback/cache 的零值稱 physical stopped。
- **Removal/migration implications:** 刪 stale final_route_path diagram/keys、route error 遺失、native checker 等同 physical proof 的敘述。
- **Dependencies:** WI-005,007,011–012。
- **Acceptance criteria:** known synthetic path 的 distance_remaining/ETA 來自 active path；route no-route 有非零可追溯 result；missing/stale/nonzero odom 或 yaw 錯不能 success。
- **V1 software verification:** real navigator/GoalChecker plugin loading；path 更新的 feedback、route/planner/controller error propagation、new goal 無舊 error、fresh zero vs missing/stale/nonzero odom、yaw incorrect、cancel/terminal race。
- **Physical verification dependency:** V4 requested yaw/stopped goal；controller feedback 不替代 physical stopped。
- **Out of scope:** giant error taxonomy、new Navigation API、自寫 controller。

### WI-014 — Station adapter late-acceptance / cancel race

- **ID / Subsystem / Purpose:** WI-014；Station semantic adapter；不讓晚接受 goal 成為 orphan task。
- **Approved requirement / gap addressed:** SYS-008/017/025/032/033；F-017。
- **Files/components likely affected:** `navigate_to_station_app.{cpp,hpp}`、`test_navigate_to_station.cpp`、target admission tests、operator Navigation。
- **Exact planned changes:** [ ] preserve station lookup/pose validation/native NavigateToPose。[ ] pending request/goal handle/terminal callback 使用 single request generation，cancel requested 後遲來 handle 立即 cancel **owned goal**，不 cancel-all unrelated clients。[ ] goal acceptance 尚未確定時不能先銷毀 client 並宣稱已取消；正常 cancellation deadline 逾期要回報 cancel-pending/failure evidence，保留有限記憶體的 client/event handling 直到 owned goal resolution/cancel terminal；不讓 bounded process exit 假裝保証無 orphan。[ ] terminal race deterministic，result/cancel 各最多處理一次；task 已在 server 終止時不重新送 goal。
- **Removal/migration implications:** 移除 timeout-return=successful cancellation 的假設；CLI contract 說明 unresolved pending request 時 process 仍保留 ownership/cancellation handling，無新增 daemon/mission logic。
- **Dependencies:** WI-011 readiness admission；WI-015 station dataset identity。
- **Acceptance criteria:** acceptance 晚於原 cancellation timeout 仍被取消；不影響別人的 native goal；無錯誤 success/duplicate result。
- **V1 software verification:** delayed acceptance 超過 timeout、never-accept/pending then server shutdown、late reject、cancel reject、ACK without result、success/cancel 同時、unrelated goal；驗證 owned native goal 最終無執行殘留。
- **Physical verification dependency:** V4 取消的車體反應由 shared ownership/stop test 覆蓋。
- **Out of scope:** Patrol、station navigation action wrapper、mission retries。

### WI-015 — Atomic map save 與 coherent site dataset

- **ID / Subsystem / Purpose:** WI-015；Mapping / site integration；可讀回的地圖與未來 Navigation 使用同一 storage contract。
- **Approved requirement / gap addressed:** SYS-001/002/006/007/013/019/024/032/033；F-018/F-029。
- **Files/components likely affected:** bringup `scripts/save_map.sh`、`launch/site_resolution.py`、`mobile_base.launch.py`、`test_save_map.py`、`test_canonical_bringup.py`；mapping MapIO tests/readback；release exporter；station asset resolver。
- **Exact planned changes:** [ ] save/resolver 共用 root precedence：explicit `MOBILE_BASE_MAPS_DIR` → explicitly configured repository maps → declared workspace default；設定了無效 root 必須 error，不能 silent fallback。[ ] 每次 save exclusive unique staging directory，同秒/並行不碰撞；native map_saver 寫 map pair，native MapIO readback 通過後 atomic rename 成 final dataset；failure trap 只刪自己新建的 partial directory，不碰既有 maps。[ ] dataset ID 為 directory identity + manifest content hashes；Mapping 產生 map pair，route graph/stations 是離線補入的同 dataset assets，不自動製造 route/catalog。Map Package save 可成功但 route-required Navigation 尚不可用，兩者不得混稱 ready。[ ] Navigation 選取完整 resource set：map+route required，stations 只有 station target required，docking DB 不要求。presence/nonempty/readability 先 fail-fast，schema/geometry 交 native parser；明確 override 保留但將實際 tuple/path/hashes 記為本次 selection，不能默默混兩個 site。[ ] station adapter 使用同一選定 dataset；新 map 不繼承舊 route/catalog 為「已相容」。manifest 只識別資產，不宣稱幾何相容。[ ] 零 byte ignored template 不當 operational sample 打包；使用 tracked synthetic fixtures 測試而不修改 user site assets。
- **Removal/migration implications:** remove map-only Navigation acceptance、mkdir-p second timestamp collision、failed partial output；保留 explicit save/native SLAM。
- **Dependencies:** 無；WI-023 manifest 共用 dataset identity，不重複造 registry。
- **Acceptance criteria:** output complete/readbackable、unique、root deterministic；missing/empty route 在啟用 global capability 前 clear error；Generic Pose 無 station catalog 仍合法。
- **V1 software verification:** existing shell fake-native boundary + real MapIO fixture：same timestamp/concurrent save、saver partial/error、readback error、unwritable root、prior dataset unchanged、missing/empty route、invalid map image path、explicit pair、station-only missing catalog；不啟動真 sensors。
- **Physical verification dependency:** V2 storage permissions；實場 Mapping/map usefulness另保留受控驗證；V1 不證明 SLAM map quality。
- **Out of scope:** site business database、automatic route annotation、map-route geometric compatibility algorithm、autonomous exploration。

WI-015 station selection 的具體接口：site manifest 記錄 selected map/route/station paths 與 hashes；canonical Navigation launch 以 read-only parameters `mobile_base.site_manifest_path`、`mobile_base.site_manifest_sha256` 傳给既有 `bt_navigator`，Q6 plugin 宣告並固定本次 selection。Station adapter 透過既有 ROS parameter service 讀取這兩個值，按 manifest 取 catalog 並核 hash；既有 explicit `--catalog` 只允許與 selected catalog 相符，否則拒絕。Generic Pose 不依赖 stations。這是當次 deployment asset identity，沒有新 ROS manager/service type、map version DB 或幾何 compatibility algorithm。V1 加 running site A + CLI catalog B、manifest/hash changed、parameter unavailable、同 dataset valid case。WI-014 先依此已定契約寫 fixture，WI-015 的 storage helper先完成，actual navigator接入在WI-011/014。

### WI-016 — Native local DockRobot contract 與 Vision/frame admission

- **ID / Subsystem / Purpose:** WI-016；Docking；明確 local-only，無 global nav 仍可提供 local capability。
- **Approved requirement / gap addressed:** SYS-044；F-019；Q3 server extension 邊界。
- **Files/components likely affected:** navigation 中現有 docking YAML/test 移到清楚 local section/new `docking.launch.py`；native plugin config + local noncharging extension；operator/docs；native DockRobot goal admission integration。
- **Exact planned changes:** [ ] formal API 保留 OpenNav DockRobot；explicit near-target task、external pose updates 只是 observation，不自動觸發。[ ] server/product admission enforce `navigate_to_staging_pose=false`、pose-based target/no required DB、允許 configured local dock type；不能只靠 caller example flag 聲稱 server guarantee。[ ] local pose 使用 odom/base/sensor frames 與 observation-time TF；map-frame goal/observation 必須 fresh global ready 或明確拒絕不支援的 frame，chosen MVP local-only contract 採**拒絕 map-frame input**，不偷偷 transform 用 stale map TF。[ ] invalid stamp/NaN/TF unavailable/stale Vision/local costmap unavailable → bounded failure/stop；保留 source timestamp，不 retimestamp。[ ] local costmap/footprint/controller/odom 是 explicit dependencies；依 WI-018 分組。[ ] output remap 至 docking source，native task cancel/terminal 接 WI-005 authority release。
- **Removal/migration implications:** 刪 server guarantee=caller flag 的錯誤 docs；test 名 `apriltag_docking_integration` 改為 `local_docking_integration`，不引入 image/tag processing。
- **Dependencies:** WI-001,005,007；Q2 已批准 local group contract、Q3；本項使用 local native fixture，WI-018 後續接 canonical launch。
- **Acceptance criteria:** 沒有 map/AMCL/NavigateToPose server 時 local DockRobot 可啟動；server 拒絕 long-range staging/map input；pose topic alone 無 motion。
- **V1 software verification:** actual native action with synthetic Vision/TF/odom/local costmap，assert goal flags、freshness、pose-only no motion、no global dependencies、unknown type/database request、cancel output；保留 collision checking的可控 fixture，不能以 disable collision 的 fixture 宣稱 production protection。
- **Physical verification dependency:** V2 Vision frame/clock/offset wiring；V4 後專門 docking trial 校準。
- **Out of scope:** long-distance go-to-dock、Docking Manager、自訂 Dock Action、AprilTag/image pipeline、charging workflow。

### WI-017 — Docking pose/yaw → stop → terminal handshake

- **ID / Subsystem / Purpose:** WI-017；Docking completion；滿足 SYS-044，而非 distance-only success。
- **Approved requirement / gap addressed:** SYS-030/044；F-020；**Q3 先決**。
- **Files/components likely affected:** new `local_non_charging_dock.{hpp,cpp}` plugin/config/tests；Q3 選定的 pinned native OpenNav extension/patch；command authority adapter；local docking integration test。
- **Exact planned changes:** [ ] native plugin 檢查 target-relative position + wrapped yaw；必要 offset 由 config 定義並標 calibration。[ ] native server task sequence 增加 pose reached → explicit zero/stop handoff → bounded fresh authoritative local velocity stop evidence → release authority → native SUCCEEDED。[ ] cannot merely put stopped in isDocked：目前 server 在 false 時持續 approach，並將 target 投影到 dock 後方；plugin 不能 blocking wait 或另發競爭 cmd_vel。[ ] fresh nonzero/stale/missing odom 不 success；M1/controller failure 阻止 completion；stop timeout native failure。[ ] cancellation 在 pose arrival/stop wait/late callbacks 有明確優先處理，cancel 已接受時不得再走 success；同樣 bounded best-effort stop/release。[ ] 詳細 stop evidence 留 diagnostics/log；不宣稱 physical wheels stopped。
- **Removal/migration implications:** replace native distance-only noncharging completion integration；保留 DockRobot API/feedback/terminal semantics，native extension 不複製成另一 server/manager。
- **Dependencies:** WI-003,005,007,016；Q3。
- **Acceptance criteria:** position-only、wrong yaw、moving/stale velocity 都不能 success；成功前已 software-confirmed stop/released；native task terminal 不漏 authority。
- **V1 software verification:** real native server + extension with synthetic fixture：position/yaw matrix、nonzero then fresh zero、stale/missing samples、stop timeout、cancel-at-success、cancel during stop、failed primitive；assert command stream/order/terminal status，而非只看 action accepted。
- **Physical verification dependency:** V4 之後獨立 Vision/dock hardware test：precision/yaw/physical stopped/cancel；硬體未備則不標 validated。
- **Out of scope:** custom docking controller/framework、充電判定、physical stop certification。

### WI-018 — Native lifecycle groups 與 map-outside deployment

- **ID / Subsystem / Purpose:** WI-018；Bringup；global failure 不移除 local recovery capabilities。
- **Approved requirement / gap addressed:** SYS-007/010/014/030/034/044/045；F-019/F-023；**Q2 先決**。
- **Files/components likely affected:** bringup `mobile_base.launch.py`、navigation/localization launch/YAML、new local behaviors/docking launch；launch tests/operator procedures。
- **Exact planned changes:** [ ] common base（RSP/control/sensors/EKF/Teleop/diagnostics）不依賴 global lifecycle；localization manager 管 map_server+AMCL，startup unknown pose 正常。[ ] Q2 推薦：local motion group = controller_server + 其唯一 embedded odom local_costmap + native behavior_server/Spin；docking own lifecycle group 依賴這些 local resources；global group = planner/global_costmap、route、bt_navigator。[ ] native managers 管 configure/activate/deactivate/bonds；沒有自寫 lifecycle manager，沒有 duplicate local costmap。[ ] global `autostart=false`，操作員在可用 map TF 後用 native lifecycle startup/resume；任務仍由 ready gate 判斷；不以假 initial zero pose 讓 activation 通過。[ ] READY false 不自動拆掉正執行 recovery 所需 local/global infrastructure；route/planner failure不 kill base、Teleop、EKF、local Docking。[ ] `set_initial_pose=false` 為 unknown-start baseline，允許 operator initialpose 正常先建立 ready；沒有強制 reset。[ ] malformed required site assets 是 capability configuration failure，與 unknown pose 不同；error 不透過全 launch shutdown 任意關掉 base。
- **Removal/migration implications:** 移除 docking 放同 global group、default zero pose、無限 TF wait/self-retry 的錯誤假設；Mapping 不起 AMCL/global Nav。
- **Dependencies:** WI-006/007/009/011/015/016/022；Q2。
- **Acceptance criteria:** 無 map→base 或 TF 延遲超原生 timeout 時 common/local resources 仍可用；明確 native startup 後 global capability 可啟用；一個 map→odom authority。
- **V1 software verification:** evaluated lifecycle node_names + real managers with fake TF/native local resource fixture：no map TF、late TF、valid TF but ready=false、global server activation/bond failure、explicit startup、Docking without global nav；inspect actual local costmap publisher ownership。
- **Physical verification dependency:** V2 actual startup/device failure isolation；V3/V4 map-outside manual entry + Initial Pose workflow。
- **Out of scope:** Runtime Mode Manager、READY 持續控制 lifecycle 的新 coordinator、automatic profile switching。

### WI-019 — Native diagnostic_aggregator 與 producer alignment

- **ID / Subsystem / Purpose:** WI-019；Diagnostics；統一顯示與 disappearance，不建立決策引擎。
- **Approved requirement / gap addressed:** SYS-004/026/029/035；F-021。
- **Files/components likely affected:** bringup 新 `config/diagnostics.yaml`、`launch/diagnostics.launch.py`、package/Docker dependencies/tests；EKF `print_diagnostics`；既有 producer config。
- **Exact planned changes:** [ ] native diagnostic_aggregator 分組 drivetrain、IMU、front/rear LiDAR、ros2_control/controller_manager、EKF、Localization、Nav lifecycle、Docking capability evidence。[ ] match actual identities：`Drive System`/`m1`、`IMU`/`tdk_imu`、`Front LiDAR`、`Rear LiDAR`；native names 在 qualified image 確認。[ ] expected never-seen/missing/stale 由 native GenericAnalyzer expected/name/timeout 配置，不忽略 disappear，也不把 missing 當正常。[ ] enable native EKF diagnostics；其他已有 native status 直接接入；若 native lifecycle 缺 operator diagnostic bridge，最小 adapter 只轉 lifecycle/bond state，沒有新 health algorithm。[ ] localization 接 WI-009 same snapshot；idle/canceled/task failure 不統一升為 component ERROR。
- **Removal/migration implications:** 刪 disabled diagnostic output 或死去仍顯示 cached OK 的敘述；raw `/diagnostics` 保留，新增 `/diagnostics_agg`。
- **Dependencies:** WI-003/009/018；producer身份來自 WI-001。
- **Acceptance criteria:** expected producer never seen/死亡有可見 stale/missing；producer ERROR/WARN/STALE 保留；沒有 `/system/ready` 或 aggregator control dependency。
- **V1 software verification:** actual native aggregator + synthetic diagnostic producers：正常、warning/error、never seen、publisher death、復原、unknown group；existing IMU 100ms/LiDAR 200ms tests 重用並區分這是 receipt freshness。
- **Physical verification dependency:** V2 device diagnostics/names；backend人工呈現另驗，不作 motion authority。
- **Out of scope:** central SystemMonitor、重做 heartbeat framework、每次 Action failure 轉 health ERROR。

### WI-020 — Telemetry source time、cache expiry 與 bounds

- **ID / Subsystem / Purpose:** WI-020；Observability；停止無限重送舊 latest 當 current。
- **Approved requirement / gap addressed:** SYS-035/037/038/042；F-010/F-022。
- **Files/components likely affected:** observability `telemetry.py`、`observability_adapter_node.py`、`influx.py` 必要部分、node/telemetry/influx tests/config。
- **Exact planned changes:** [ ] 每個 selected metric 保存 source timestamp、timestamp_origin、source identity、monotonic received/updated time；來源沒有 stamp 明確標 receive。[ ] finite validated per-profile TTL，expiry 後移除 current cache 值；repeated sampling 不刷新 source/receipt age，invalid update 不延長舊值生命。[ ] preserve bounded queue/background sender、有限 selected metric profile、bounded flush/shutdown；network failure 不無限重試累積或阻塞 ROS callbacks。[ ] 斷線重送可用历史記錄須保留其時間，不能 now-stamp；queue drop/expiry statistics 作 outbound evidence，不回控核心。
- **Removal/migration implications:** remove indefinite latest resampling與 misleading batching/docs；不擴張 raw data profile。
- **Dependencies:** WI-001 timestamp terminology，WI-019 selected diagnostics。
- **Acceptance criteria:** stale value 不呈現為 current；source stamp/identity 無損；backend failure 時 cache/queue/workers 有界。
- **V1 software verification:** injected clock boundary before/at/after TTL、source stamp invalid/old、unchanged cache、resume updates、queue overflow、outage/retry/shutdown；復用既有 Influx error tests。
- **Physical verification dependency:** §20 runtime soak/backend outage CPU/RAM、clock accuracy；V1 deterministic bounds不是實機 load proof。
- **Out of scope:** 新 backend、raw images/scans recording、observability 參與 readiness/command control。

### WI-021 — Observability startup、storage/output deployment contract

- **ID / Subsystem / Purpose:** WI-021；Observability / Deployment；讓現有 outbound 功能在 release 中可正確啟用。
- **Approved requirement / gap addressed:** SYS-036–038/042；F-022。
- **Files/components likely affected:** existing observability launch、`fluent-bit.conf`、`.env.example`、`compose.release.yaml`、exporter env template、operator Release；environment/fluent-bit tests。
- **Exact planned changes:** [ ] 明確 documented opt-in startup telemetry + Fluent Bit；complete endpoint/identity/output env contract，secrets 保持 env/外部配置。[ ] ROS logs source root 與 Fluent Bit tail input/volume 一致；files rotation/backpressure/buffer limits 跟現有 outbound scope 一致，不留下無界 disk spool。[ ] missing backend/config 報 observability 狀態但不成為 core startup/health dependency；exit/restart 不串到 base/global managers。[ ] exporter/config/help 只描述實際 batching/flush 與 resources。
- **Removal/migration implications:** remove dead env vars、unused log paths、觀察 container alive=robot ready 的錯誤說明。
- **Dependencies:** WI-020；本項先完成 outbound deployment contract，WI-023/024 後續負責 release assembly。
- **Acceptance criteria:** exported deployment 可以啟用現有 outbound components；token 不出現在 manifest/logs；core不依賴 backend。
- **V1 software verification:** existing env/Fluent Bit tests + native config parse/dry-run、temporary log fixture輸出、backend unreachable、bounded buffer/shutdown；不得 contact production backend。
- **Physical verification dependency:** runtime log path permission/network/backend retention、resource soak；V2 host wiring，專門 outage case。
- **Out of scope:** server retention平台擴建、核心 runtime控制、mandatory cloud startup。

### WI-022 — Honest mock / time-mode API

- **ID / Subsystem / Purpose:** WI-022；Bringup / Description；公開參數不能宣称不存在的 stack。
- **Approved requirement / gap addressed:** SYS-023/030；F-024。
- **Files/components likely affected:** public bringup/base_control/description/navigation/localization/mapping launches，相關 tests；private root Xacro delivery；operator/spec。
- **Exact planned changes:** [ ] 採最小 approved-allowed policy：production `use_mock_hardware=true` 立即 clear error，before Xacro/hardware/sensors；保留 false-only argument 作明確拒絕契約，help 直接標 unsupported。[ ] 去除 private asset「mock → real M1 serial mock」分支的部署誤導；公開 repo 不加入私有檔。[ ] production `use_sim_time=true` 同樣在 public entrypoint fail-fast，real-only profile一致；native nodes/test fixture 可內部注入受控 clock 做 deterministic tests，不承諾 Gazebo或模擬感測器。[ ] parser驗證完整 bool 值，拒絕 unsupported平台；測試不用 mock=true 冒稱硬體 mock 已載入。
- **Removal/migration implications:** remove unused forwarding/unsupported simulation claims；保留 false-only legacy flags 的理由是避免 ROS launch 默默忽略 user intent，非假功能。
- **Dependencies:** WI-001；public mode contract 在本項先完成，後續 WI-018 使用它組合 launch groups。
- **Acceptance criteria:** public true/invalid mode 在任何 device open前失敗；help/test/docs 真實；real supported default不改 clock authority。
- **V1 software verification:** evaluated launch substitutions（不是 source string only）、true/false/invalid 值、所有 public entrypoint、no serial/sensor spawn on rejection；controlled-clock unit fixture 無 production mock label。
- **Physical verification dependency:** V2 device paths/time sync；此 WI 不需要模擬/physical movement。
- **Out of scope:** native mock平台/full simulation stack；無獨立 requirement 不新增 mock architecture，所以不另列 review question。

### WI-023 — Minimal release / private / site provenance

- **ID / Subsystem / Purpose:** WI-023；Deployment；識別真正執行的 source/image/assets。
- **Approved requirement / gap addressed:** cross-system deployment provenance；F-025/F-029。
- **Files/components likely affected:** `Dockerfile`、`scripts/export_release.sh`、new `scripts/release_manifest.py`、compose/operator docs、bringup release-manifest tests。
- **Exact planned changes:** [ ] 產生 machine-readable release manifest：source commit + dirty flag + build-context content checksum，base image resolved digest、output image ID/digest、build timestamp/target arch、ROS/Nav2/ros2_control/OpenNav/Route/diagnostics/libmodbus package versions，以及 Q3 source patch/base revision/hash。[ ] private Xacro/mesh assets 提供清單/hash與外部 revision（有則記），不拷貝 proprietary內容入 public tracking、不輸出 secrets。[ ] selected dataset ID/map/route/station path+content hash，explicit override tuple同樣記錄。[ ] manifest 內 build identity 與 runtime asset identity 分開，startup 可核對 bind-mounted inputs；不能以 git commit 忽略 ignored inputs或dirty worktree。[ ] build artifact與sidecar mutual association使用image ID/manifest checksum避免 self-referential image digest；保留現有 release bundle workflow。
- **Removal/migration implications:** no anonymous same-tag release；零-byte template不是 valid source asset；缺 required private inputs 報錯，不重建 proprietary geometry。
- **Dependencies:** WI-015/022、Q3 qualified native asset contract、Q4；manifest先完成，後續WI-024使用。
- **Acceptance criteria:** 給定 bundle/selected site可指出 exact source/image/native versions/private/site identities；不需 giant package manager。
- **V1 software verification:** deterministic manifest schema/field/hash tests，dirty context、missing/changed private asset、same site path different content、native overlay version、no credential fields；container檢查實際 image metadata。
- **Physical verification dependency:** V2 deployed manifest vs actual devices/site matching；不等於硬體性能驗證。
- **Out of scope:** 把 private assets變 public、fleet inventory或package管理平台。

### WI-024 — Supplied artifact selection 與 dependency qualification policy

- **ID / Subsystem / Purpose:** WI-024；Release；同 tag 舊 image 不得遮蔽 supplied new artifact。
- **Approved requirement / gap addressed:** F-025/F-026；**Q4 先決**。
- **Files/components likely affected:** `scripts/export_release.sh` 內 generated `start.sh`、Dockerfile/compose.release.yaml、release script tests、operator Release。
- **Exact planned changes:** [ ] generated startup 驗 archive/checksum/manifest，無論 local同tag是否存在都 load supplied artifact，load/check失敗停止，不 fallback舊 image。[ ] 核對 load 後 tag解析的 image ID與manifest expected一致；部署 recreate 使用該 identity，之後 `container.Image`再比對，不以 tag string當證據。[ ] Q4 推薦 immutable qualified release artifact + digest/base lock + installed package inventory：每次不同 resolved native set視新 release，完整 V1重資格後才發；不假定 apt latest相同、不任意鎖 developer機版本。[ ] explicitly install所需 diagnostic_aggregator/native behavior及Q3 overlay，必要 package/API absence fail build/preflight，不能 silently substitute自訂核心。[ ] patch版本與Jazzy native binary set一起qualification。
- **Removal/migration implications:** remove `if image inspect tag succeeds then skip load`；只改generator，不手改ignored release/start.sh。
- **Dependencies:** WI-019/021/023；Q3/Q4。
- **Acceptance criteria:** same-tag-old image scenario 確實選中 supplied bytes；versions/provenance 完整；load fail不啟動。
- **V1 software verification:** fake Docker script tests涵蓋same-tag、load error/hash mismatch/wrong image/container mismatch；另於無device/no-ROS測試容器完成一次real build/export/load/image identity查核；不啟動robot release服務。
- **Physical verification dependency:** V2 target arch/runtime/device permissions；software image identity可在V1證明。
- **Out of scope:** 自建apt mirror（除非Q4明選）、新release management platform、push/publish/deploy至硬體。

WI-023/024 release output preservation：現有 exporter 開頭 `rm -rf release` 必須移除。build/export 先寫 unique sibling staging bundle，artifact/manifest/config checks 全成功才 publish 到新的 versioned output directory；若明確指定 destination 已存在，拒絕覆蓋並保留原資料。失敗只清自己的 staging，不刪既有 `release/.env`、maps 或image bundle；generated defaults不覆寫使用者 secrets/config。V1 驗failed build/save/promotion、existing user site/.env、concurrent export及prior bundle可用性。修 source generator，不修改本次已有 ignored release directory。

### WI-025 — Current baseline specs / operator docs 同步清理

- **ID / Subsystem / Purpose:** WI-025；System boundary / Documentation；文件與批准final architecture及完成結果一致。
- **Approved requirement / gap addressed:** F-001/F-009/F-012/F-013/F-018–027/F-029；全scope traceability。
- **Files/components likely affected:** `spec/README.md`、`01_USE_CASES.md`、`02_CAPABILITIES.md`、`03_REQUIREMENTS.md`（僅批准的observable semantics/trace allocation）、`04_SYSTEMS.md`、`operator/RELEASE.md`、`MAPPING.md`、`NAVIGATION.md`、description readmes、package comments。
- **Exact planned changes:** [ ] requirement/capability/interface/implementation/evidence依各文件責任更新，README仍唯一入口；Requirements不塞內部演算法。[ ] current architecture重寫ready/evaluator/Establish、ownership/stop levels、TF/EKF、route goals/feedback/failure owners、local Docking/native extension、lifecycle map-outside、dataset/provenance/observability。[ ] UC/CAP刪零Initial Pose normal baseline、no-valid-gate、global-ready universally required by local docking、map-outside不能Teleop矛盾。[ ] operator commands使用新ingress/authority、native global startup、explicit map save/site/root、local docking flags/frame contract；maintenance transport release流程。[ ] 移除不存在`m1_settings/README.md`連結、舊phase設計、錯service、mock/sim過度宣稱；source test「physically verified」無可重用record不得當證據。[ ] 新verification guide/evidence index依WI-027只存程序/結果指標，current document不留historical架構副本。
- **Removal/migration implications:** active docs中scan-map/lost/four-state policy全部移除；historical ChatGPT檔保留不編輯；本planning migration記錄屬計畫，不是runtime接口文件。
- **Dependencies:** WI-001–024 完成；可隨owned code同步修文，最後完整一致性檢查。
- **Acceptance criteria:** docs能對應全部final public interfaces/ownership/limits/verification class；無新manager/business scope；implemented/software-validated/hardware-validated清楚。
- **V1 software verification:** targeted repo search/link檢查、manual cross-document trace review；逐項對照本scope矩陣，不把未跑V2～V4寫成PASS。
- **Physical verification dependency:** 全hardware backlog保留UNVERIFIED，不影響文件清理完成。
- **Out of scope:** 重跑architecture audit、改歷史檔、產生多份互相矛盾的architecture authority。

### WI-026 — Legacy source/config/tests/dependency removal closure

- **ID / Subsystem / Purpose:** WI-026；Whole repo cleanup；確保最終沒有被架構取代的可執行殘留。
- **Approved requirement / gap addressed:** F-012/F-027；§6/7 inventory。
- **Files/components likely affected:** §10 exact removals；localization/navigation CMake/package/install/export；全repo search命中項。
- **Exact planned changes:** [ ] readiness authority先完成→所有Navigation consumer遷移→核對internal lost/quality consumers為零→刪兩topic publisher/interface、old detector/quality/map-matching source/tests/YAML。[ ] remove old headers/executable/libraries/plugin list/launch args/params/dependencies；不註解、不停用test、不保留optional debug。[ ] 檢查unused OpenCV與Float32，只移除無獨立consumer的依賴；keep scan filters/vendor capabilities。[ ] dead compatibility helper（例如wheel conversion wrapper）只在restored GitNexus+source確認沒有獨立使用後移除。[ ] clean generated installation選用新的colcon build/install base，確保old plugin檔不因舊install殘留仍可load；不動user runtime資產或git clean。
- **Removal/migration implications:** final沒有lost/quality publisher/subscriber、no old four-state/scan thresholds/current docs claims；沒有暫時兼容交付。
- **Dependencies:** WI-008–014/025；其他WI dependency updates完成。
- **Acceptance criteria:** exact removal list與build/export/config一致；新乾淨install無old targets；所有remaining search hits都有合法history/planning/negative-test理由。
- **V1 software verification:** legacy-reference掃描、CMake/package dependency/install artifact檢查、plugin factory只列final plugins；negative contract test裡的被禁字串可存在但不得作publisher/consumer。完整clean-basebuild承接WI-027。
- **Physical verification dependency:** 無新增；external compatibility若出現具體契約必須已在review解決。
- **Out of scope:** 大規模非必要refactor、移除有獨立責任的診斷/感測器/maintenance工具。

### WI-027 — Complete V1 closure、證據與後續 physical procedures

- **ID / Subsystem / Purpose:** WI-027；Testing / integration；一次run以完整software evidence收尾。
- **Approved requirement / gap addressed:** F-028/F-029；所有WI acceptance。
- **Files/components likely affected:** 現有package test registrations、必要新增測試（§12）、`operator/VERIFICATION.md`、spec入口verification link；generated `evidence/` / log output依既有ignore策略。
- **Exact planned changes:** [ ] 依§15確認可重用approved evidence的revision/config/environment/scope/class，只重跑被改動的observable behavior；本次全部changed packages完整suite一次整合執行。[ ] 修各packageformat/lint/build/gtest/pytest/launch/integration/config/BT/plugin/QoS/interface/release failures，rerun affected+完整必要整合直到PASS或已證external blocker。[ ] portable test route用tracked `test/test_data/test_route_graph.geojson`，不依ignored `maps/test_site`；new package/extension全部納入colcon；static/mock/native process/physical evidence分級。[ ] final報告列每WI完成、command/exit code/result/log/artifact identity、reuse依據、remainingcalibration/hardware backlog；§16–20轉成可操作procedures，不runhardware。[ ] restore GitNexus impact/detect_changes查範圍，review diff/status保留原unrelated變更。
- **Removal/migration implications:** remove obsolete assertions/test registration/skip-as-pass；不以只測小段替代whole-systemV1。
- **Dependencies:** WI-001–026全部。
- **Acceptance criteria:** §15 applicable V1全部PASS、無未選架構分支、無legacyruntime、no hardware operations；證據可供ChatGPTreview完整diff。
- **V1 software verification:** 本項就是§15完整執行與修復迴圈；不重複每個SYS同一證據。
- **Physical verification dependency:** V2需V1 PASS+ChatGPT implementation review acceptable，之後V3→V4逐級；此run不標Feature Freeze。
- **Out of scope:** V2～V4自動執行、commit/push、硬體測試或部署、另一預定implementation階段。

## 9. Ordered execution sequence

**前置 review 只發生一次：**解決 Q1～Q7、寫回選定契約/檔案、批准整份 plan，再發 ONE implementation prompt。以下箭頭全是同一 run 內的依賴順序，不包含任何人工 approval。

1. 保存 original status、read complete approved plan、核對 source revision/privates/site inputs/container/native versions、恢復可用 GitNexus。把新 interface package skeleton 隨 WI-005 建立，Establish action 隨 WI-010 加入。
2. **WI-001 → WI-022 → WI-002 → WI-003 → WI-004 → WI-005 → WI-006 → WI-007 → WI-015**：TF/time contract、honest runtime options、control correctness、ownership、odometry、site storage。
3. **WI-008 → WI-009 → WI-010 → WI-011 → WI-012 → WI-013 → WI-014**：evaluator、authority、Establish、consumer migration、route/results/station。WI-010 的 local native resources 先由其非硬體 fixture 驗證，canonical deployment composition 在 WI-018 統一接好；這不是另一 implementation phase。
4. **WI-016 → WI-017 → WI-018 → WI-019 → WI-020 → WI-021 → WI-023 → WI-024**：native Docking extension、failure groups、diagnostics、outbound observability、qualified release。
5. **WI-025 → WI-026 → WI-027**：完成全部 current docs、legacy/dependency removal、完整 V1；fix→rerun直到 PASS/外部blocker，交一份report。

每個 item 寫具體測試/最小修改/受影響test；同 package 可在一個既有 colcon invocation 覆蓋多WI，不為每個traceability row重複驗證。跨WI的production wiring與failure injection在WI-027整合確認。不得把「單項測試通過」當作one-shot已結束。

## 10. Files expected to be removed

以下是最終 source tree 的確定刪除；全檔只服務obsolete architecture：

```text
src/mobile_base_localization/include/mobile_base_localization/localization_monitor.hpp
src/mobile_base_localization/src/localization_monitor.cpp
src/mobile_base_localization/src/localization_monitor_main.cpp
src/mobile_base_localization/config/localization_monitor.yaml
src/mobile_base_localization/test/test_localization_monitor.cpp
src/mobile_base_navigation/include/mobile_base_navigation/is_localization_healthy_condition.hpp
src/mobile_base_navigation/include/mobile_base_navigation/wait_for_localization_healthy_node.hpp
src/mobile_base_navigation/src/is_localization_healthy_condition.cpp
src/mobile_base_navigation/src/wait_for_localization_healthy_node.cpp
src/mobile_base_navigation/test/test_is_localization_healthy_condition.cpp
src/mobile_base_navigation/test/test_wait_for_localization_healthy_node.cpp
```

`src/mobile_base_navigation/test/test_apriltag_docking_integration.py` 以 `test_local_docking_integration.py` 取代並保留有用integration fixture；其旧檔名不留空殼。symbol移除：ScanMapQualityEvaluator、LocalizationLostDetector、old health enum、matching-distance/occupied/beam-stride/ratio/hold-only設定。舊 launch args、plugin exports、libraries在原檔刪除，不一定整檔刪除。

不刪私有Xacro/mesh、user maps、ignored release/.env、native cores、sensor normalizer/filters、有效maintenance工具或歷史ChatGPT檔。

## 11. Files expected to be modified

| Path / group | Planned owner WIs |
|---|---|
| `src/mobile_base_control/src/m1_driver.cpp`, `m1_hardware.cpp`, `m1_diagnostics.cpp`; matching headers | WI-002–005 |
| control `src/m1_*_check_core.cpp`, `m1_latency_check_main.cpp` and direct-transport tool entrypoints | WI-002–004 |
| control `config/base_control_params.yaml`, `launch/base_control.launch.py`, `CMakeLists.txt`, `package.xml`, `m1_hardware_plugins.xml` only if export changes needed | WI-003–006,022 |
| existing control gtests and `test_base_control_launch.py` | WI-002–006 |
| description `launch/robot_description.launch.py`, existing tests, `urdf/README.md`, `meshes/README.md` | WI-001/022/023 |
| private `urdf/mobile_base.urdf.xacro`, `mobile_base_ros2_control.xacro` only when needed for rejected mock / new mandatory config | WI-022/003/004；走private asset delivery，public git不加入 |
| perception `launch/sick_dual_lidar.launch.py`, `scripts/scan_handedness_normalizer.py`, associated tests；IMU node/protocol tests | WI-001/019 only where actual contract mismatch |
| state_estimation `config/ekf.yaml`, `launch/ekf.launch.py`, `test/test_ekf_launch_syntax.py` | WI-007/019/022 |
| localization `config/amcl_params.yaml`, `launch/localization.launch.py`, `test/test_localization_launch.py`, CMake/package | WI-008–010/018/022/026 |
| navigation `config/nav2_params.yaml`, `behavior_trees/route_assisted_nav.xml`, `launch/navigation.launch.py`, CMake/package | WI-005/007/010–013/016–018/022/026 |
| navigation `navigate_to_station_app.{cpp,hpp}`, `target_admission.*` only needed selection contract, tests | WI-014/015 |
| navigation `test_behavior_tree_runtime.cpp`, `test_navigation_launch.py`, existing route/station fixtures | WI-011–015/018/027 |
| mapping launch/config tests/readback only where time/site contract needs changes | WI-015/022；SLAM config不是新設計 |
| bringup `launch/mobile_base.launch.py`, `site_resolution.py`, `scripts/save_map.sh`, CMake/package and existing integration tests | WI-005/006/015/018/019/022/027 |
| observability `telemetry.py`, node, `influx.py` if bounds change, existing launch/config/setup/tests | WI-020/021 |
| `Dockerfile`, `compose.yaml` only supported config consistency, `compose.release.yaml`, `.env.example`, `scripts/export_release.sh`, `scripts/teleop_keyboard.sh` | WI-005/019/021–024 |
| `spec/README.md`, `spec/01_USE_CASES.md` through `04_SYSTEMS.md`, `operator/RELEASE.md`, `MAPPING.md`, `NAVIGATION.md` | WI-025/027 |

這是預期範圍清單，不是允許無關refactor。所有符號變更遵循impact流程；新增需要的CMake/package/test wiring隨所属WI一起完成。

## 12. Files expected to be added

推薦方案的具體檔案如下；Q1/Q3/Q6 若選替代方案，**review結束前**在本節替換為批准的確切清單，不能留給implementation選。

| New path | Responsibility / WI |
|---|---|
| `src/mobile_base_interfaces/{CMakeLists.txt,package.xml}` | 最小ROSIDL interfaces，沒有node；WI-005/010 |
| `src/mobile_base_interfaces/action/EstablishLocalization.action` | 空goal/最小result/phase；WI-010 |
| `src/mobile_base_interfaces/srv/MotionAuthority.srv`（Q1） | internal request/renew/release lease，不作business API；WI-005 |
| `src/mobile_base_interfaces/msg/MotionAuthorityState.msg`（Q1） | owner/lease/handoff state/cause，software evidence；WI-005 |
| `src/mobile_base_interfaces/msg/MotionCommand.msg`（Q1） | internal source/lease-tagged TwistStamped envelope；DDC native input不變；WI-005 |
| `src/mobile_base_control/include/mobile_base_control/motion_authority.hpp`, `src/motion_authority.cpp`, `src/motion_authority_main.cpp`, `config/motion_authority.yaml` | minimal exclusive gate；WI-005 |
| control `include/mobile_base_control/motion_source_adapter.hpp`, `src/motion_source_adapter.cpp`, `src/teleop_authority_main.cpp`（Q1） | lease/generation source binding與Teleop ownership；Native task-specific cancel hooks仍由所屬BT/navigator/docking extension實作 |
| `src/mobile_base_control/test/test_motion_authority.cpp`, `test/test_motion_authority_launch.py` | owner/lease/cancel/stop/output/crash tests；WI-005 |
| `src/mobile_base_localization/include/mobile_base_localization/{localization_evaluator,localization_node,establish_localization_task}.hpp` | 純evidence、ROS binding、active task各自責任；WI-008–010 |
| localization `src/{localization_evaluator,localization_node,localization_main,establish_localization_task}.cpp`, `config/localization_readiness.yaml` | frozen model與native task integration；WI-008–010 |
| localization `test/test_localization_evaluator.cpp`, `test/test_localization_node.cpp`, `test/test_establish_localization.cpp` | pure math/epochs/QoS/native task races；WI-008–010 |
| navigation `include/mobile_base_navigation/{is_localization_ready_condition,establish_localization_bt_node,path_contract_node,fresh_stopped_goal_checker}.hpp` + matching `src/*.cpp` | ready/Action/path contract/native checker adapters；WI-011–013 |
| navigation `src/mobile_base_navigator.cpp`, `include/mobile_base_navigation/mobile_base_navigator.hpp`, `navigator_plugins.xml`（Q6） | native NavigateToPose navigator extension，goal admission only；WI-011 |
| navigation `goal_checker_plugins.xml`, `test/test_is_localization_ready.cpp`, `test/test_establish_localization_bt.cpp`, `test/test_path_contract.cpp`, `test/test_fresh_stopped_goal_checker.cpp`, `test/test_navigation_admission.cpp` | exported native plugins / tests；WI-011–013 |
| navigation `launch/docking.launch.py`, `launch/local_motion.launch.py`, `config/local_docking.yaml` | native local lifecycle resources，非new manager；WI-016–018 |
| navigation `include/mobile_base_navigation/local_non_charging_dock.hpp`, `src/local_non_charging_dock.cpp`, `docking_plugins.xml`, `test/test_local_non_charging_dock.cpp`, `test/test_local_docking_integration.py` | native plugin extension + tests；WI-016–017 |
| `third_party/opennav_docking/source.repos`, `third_party/opennav_docking/terminal_contract.patch`, `third_party/opennav_docking/README.md`（Q3） | exact qualified upstream revision/最小native extension/license與適用範圍；source在Docker build取得，非複製新server |
| bringup `config/diagnostics.yaml`, `launch/diagnostics.launch.py`, `test/test_diagnostics_aggregation.py`, `test/test_capability_lifecycle.py` | native aggregation/lifecycle integration；WI-018/019 |
| bringup `test/test_release_scripts.py`, `test/test_release_manifest.py`, `test/test_final_contracts.py` | 非硬體release/cleanup contracts；WI-023–027 |
| `scripts/release_manifest.py` | minimal release/dataset manifest generation/check；WI-015/023 |
| `operator/VERIFICATION.md` | V1 evidence index、V2/V3/V4程序、evidence-class rules；WI-027 |

generated release manifest、site manifest、V1 logs/results/bundle 是runtime/build輸出，不把它們變成第二architecture文件。基於已有package增加檔案；不新建 diagnostics、manager、simulation packages。

## 13. Dependency cleanup plan

1. localization 移除 OpenCV find/link/includes/`libopencv-dev` package dependency；清除 Float32/scan-map-only code。保留 nav_msgs/sensor_msgs/geometry_msgs/std_msgs/tf2/AMCL/map server；新增 rclcpp_action、diagnostic_msgs、std_srvs、ROSIDL interface package等實際consumer需要的依賴。
2. navigation 刪 old healthy libraries/export/plugin list；保留 native Route/Navfn/MPPI/BT Navigator/OpenNav。新增 native `nav2_behaviors`、所需goal-checker/navigator/pluginlib dependencies與shared interface package。Jazzy exact package/API以qualified image為準，缺少required core即external preflight/build blocker，不能猜Rolling API。
3. bringup/image 加 native diagnostic_aggregator；reuse producer diagnostics，不再造 parallel health stack。Q1若採minimal exclusive gate則**不加twist_mux**；若改採mux方案，review先補required lock coordinator與version contract。不能把priority mux當完整handoff。
4. Q3 native source overlay只覆蓋批准的OpenNav package/version，既有Nav2 action/messages保持native兼容；Docker build與manifest明確upstream SHA/patch hash，避免兩份不同版本server同時進環境。
5. 移除不用的test dependencies、old parameters/launch arguments、wrong absolute plugin/test fixture paths；用ament index/target exports查package resources。
6. 系統image裡可能因其他native packages仍需OpenCV，不因此強行apt purge。只移除本project對obsolete architecture的直接依賴。
7. source、package.xml、CMake/install/export、XML/YAML、fresh install artifact逐層對齊；unused dependency必須確認無独立requirement再刪。

## 14. Documentation/spec cleanup

| Current authority location | Required final update |
|---|---|
| `spec/README.md` | 保留入口/文件責任；把「as-built wins」限定於描述現況，不能推翻批准requirements/final design；列V-Model/Hardware First/MVP/Progressive Verification/DDD/Current Baseline/SSOT/Organic Growth/Avoid Premature Structure原則及verification入口。 |
| `01_USE_CASES.md`, `02_CAPABILITIES.md` | unknown-start、Teleop into map、Initial Pose或明確Establish、READY再導航；local Docking可獨立；station/map assets契約；無default zero pose/no-valid-gate。 |
| `03_REQUIREMENTS.md` | 維持observable requirements，補既已批准readiness/command exclusivity/local completion與allocation；不把candidate thresholds變normative production calibration，不更動未批准需求。 |
| `04_SYSTEMS.md` | 移除Phase2B scan-map/lost架構段、wrong AMCL endpoint、old四態敘述；寫入final interfaces、ownership、native extensions、failure groups、time provenance、dataset/release。 |
| `operator/MAPPING.md` | exclusive Teleop、save root/output ID/readback/partial cleanup、map-only不是route-ready site、maintenance不可並開。 |
| `operator/NAVIGATION.md` | Initial Pose正常流程、explicit native global startup（Q2）、fresh ready admission、bounded mid-task recovery、station selection、native result/stop evidence等級、local Docking契約。 |
| `operator/RELEASE.md` | package/image/private/site身份、supplied artifact load、real/mock/time限制、observability startup、device path/permissions前提、不要將container啟動稱為系統ready。 |
| `operator/VERIFICATION.md` | observable criterion→evidence key→revision/config/environment/class/result/limitations；V1/2/3/4不同門檻，未完成hardware不freeze。 |

「移除legacy references」指active source/config/docs中的現行語義；本planning清單、明確negative regression tests與immutable historical record可保留被禁字串作辨識。不得為了讓grep零命中去改歷史檔，或把active殘留藏進大範圍allowlist。

## 15. V1 software verification plan

**全部在ONE implementation run內執行。** 本輪尚未執行任何一項V1。沒有可直接宣稱覆蓋本次final architecture的已批准測試記錄；舊log只證明曾使用colcon機制，不能作本次PASS。

環境入口沿用root `Dockerfile` dev/release targets、既有colcon/CMake/ament/pytest/gtest。host目前沒有可讀的 `/opt/ros/jazzy`/colcon；需qualified Docker environment。不要為了V1啟動带真device mappings的robot runtime；以**同一dev image**啟動無`--device`、無privileged、无host-network的software test container，使用loopback DDS和fake sensor/action/serial fixtures。既有compose exec只可對已確認隔離硬體的test container使用。不是另建simulation stack或parallel test runner。

**V1 preflight**：native package version與exported plugin/Action/BT ports核對Jazzy qualified set；private Xacro/mesh完整、site測試使用trackedfixtures；Q1/Q3/Q4/Q6已定案；GitNexus可用。若外部tool/native依賴或privateinput缺少，留下具體command/error，不以skip通過。

| Verification block | Scope / assertions | Evidence required |
|---|---|---|
| format/lint | existing ament linters、Python lint/doc checks、C++風格；shell `bash -n`與既有lint mechanism | colcon test結果 + lint輸出；不添加只為湊數的平行工具 |
| compile/build | 所有src packages，包括interfaces、BT/GoalChecker/navigator/dock plugin與Q3native extension；乾淨build/install base | build exit0 + package summary + image/version manifest |
| Control | WI-002–006，ResourceManager、DDC、pseudo-TTY、exclusive gate、lifecycle/timeout | deterministic tests與native integration；不得run `m1_*_check`接真serial |
| TF/time/estimation | WI-001/007/022，description parse、actual evaluated params、timestamp semantics | static/fixture evidence明確標記，不claimphysicalTF/clock |
| Localization | WI-008–010，math、distinct observations、stationary/moving、epochs、QoS、task races | pure unit + ROS node/action integration；old reset cannot restore permission |
| Navigation/Route | production XML + actual registered BT plugins，ready admission/recovery、final yaw/path/feedback/errors、fresh stopped gate、station cancel | factory loading + synthetic native action endpoints + selected native servers；stub-only不證明endpoint/API |
| Docking/local lifecycle | actual OpenNav native server+qualified extension/local plugin、no map dependence、local flags、Vision expiry、stop-before-terminal/cancel | command trace + action terminal + lifecycle; genuine native integration with synthetic evidence |
| Mapping/site | native MapIO readback、save atomic/error/concurrency、map/route/station identity | test files/hashes、assert prior user datasets untouched |
| Diagnostics | real diagnostic_aggregator names/never-seen/stale/recovery + native producers config | actual `/diagnostics_agg` output under synthetic publisher death |
| Observability | timestamp/TTL、backpressure/bounded caches/queues/shutdown、Fluent Bit config/output、backend unavailable | deterministic queue/cache limits與software fixture；production resource soak另列 |
| Release | exporter staged output、same-tag old image、archive/load/image/container mismatch、provenance/private/site identity | script tests + real artifact/image verification under no-device container |
| Cleanup | removed files/targets/dependencies、legacy references/launch args、fresh install plugins、docs link/trace | source/search result與每個合法exception理由；沒有disabled dead tests |
| Final scope | GitNexus affected scope/detect_changes、git diff/status、全部WI checklist | complete diff、original unrelated preserved、one final report |

未來標準命令（在隔離的既有dev image container內；此处只是計畫）：

```bash
source /opt/ros/jazzy/setup.bash
cd /workspaces/mobile_base
colcon --log-base log/v1 build --build-base build/v1 --install-base install/v1 \
  --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
source install/v1/setup.bash
colcon --log-base log/v1 test --build-base build/v1 --install-base install/v1 \
  --event-handlers console_direct+
colcon test-result --test-result-base build/v1 --verbose
bash -n scripts/export_release.sh scripts/teleop_keyboard.sh \
  src/mobile_base_bringup/scripts/save_map.sh
```

Build/test每個command成功才執行後續依賴步驟；新build base是為避免obsolete install殘留，仍用既有colcon infrastructure，不刪既有build/log。Q3 overlay依批准Dockerfile整合，版本測試不可只連到apt舊library。

legacy inspection範例（implementation時執行、逐命中分類）：

```bash
rg -n 'ScanMapQualityEvaluator|LocalizationLostDetector|/localization/(lost|quality)|match_dist_m|occupied_threshold|beam_stride|lost_ratio|recover_ratio|lost_hold_s|recover_hold_s|/amcl/reinitialize_global_localization' src spec operator scripts
rg -n 'final_route_path|vx only|vx-only|localization-valid|Phase 2B|m1_settings|3600|use_mock_hardware|use_sim_time|DEGRADED|UNINITIALIZED|LOCALIZING' src spec operator scripts
git diff --check
git diff --stat
git status --short
```

第一個search之production references應為零（明確negative assertions可有字串）；第二個逐項證明final intentional semantics，不能單看exit1/0判PASS。四態詞彙若是其他native lifecycle state不能誤刪。額外查 Navigation/Docking Manager、SystemMonitor、`/system/ready`沒有新增；查 final installed tree/executables/plugin exports不含obsolete targets。

**Evidence reuse**：每份證據記錄observable criterion、source/config SHA、environment/image/package版本、scope、class、pass/failure、log path；相同證據可被多SYS/WI引用，不重跑、不升級證據強度。變更了實作/配置/時鐘/target環境或acceptance criterion才重新驗證affected部分。V1必須有完整 final software coverage，不能沿用修改前PASS。

**Closure**：任何software failure先修正→相關suite→必要full integration回歸；沒有硬體不構成省略software suite的理由。只有被證明的外部blocker才能收尾為V1未通過，列出blocked commands/affected WIs/仍未驗證範圍，不能稱V1 PASS或Feature Freeze。成功時一份report交ChatGPT檢查complete diff+V1 evidence。

## 16. V2 raised-AMR verification plan

Prerequisite：**V1 PASS + ChatGPT implementation review acceptable + 另行授權硬體操作**。AMR chassis raised、輪子離地，明確操作者/stop control；不由implementation自動開始。

| Test / owner | Observable criterion | Evidence / limitation |
|---|---|---|
| device discovery/provenance | real serial aliases、permissions、network、firmware/IDs、deployed manifest/private/site一致 | hardware configuration record；無猜測device capability |
| controller lifecycle | JSB→DDC成功順序、inactive read、nonzero admission前停止/ready回授、故障可觀測 | controller/M1 state、fresh feedback；依授權可做raised-wheel wiring，非body motion proof |
| sensor/TF/time | actual IMU/LiDAR headers（含 *_1）、唯一TF、source vs receive時間、EKF input/output | raw topic/TF與clock evidence，physical mounting仍需V3 |
| Localization interfaces | AMCL actual reset/no-motion endpoints、ready QoS/false startup/heartbeat、diagnostics同源 | interface evidence；不作consistency/calibration PASS |
| ownership/tool isolation | competing declared producers、lease revoke、non-owner無effective output、serial second opener失敗、無unexpected command | controller-level command/feedback證據；操作前明確允許的command scope |
| local/global deployment | unknown map pose正常NOT_READY，local infrastructure/Teleop仍可用，global failure隔離 | native lifecycle states與可用接口，不做導航 |

**Raised wheel odometry motion ≠ real body motion。** V2不驗Localization temporal-consistency calibration、Navigation quality、physical stopping distance或Docking precision。任何failed/unexpected command停止升級、record evidence、分析後再決定；不得直接進V3。

## 17. V3 ground in-place rotation verification plan

Prerequisite：**V2 PASS**、另行明確授權、clear area、E-stop available、controlled low-speed in-place rotation。沒有預設NavigateToPose；需要該action的特定測試須另行批准。

- 對比實際wheel/body rotation、IMU yaw sign/mount/bias、EKF yaw rate/TF、LaserScan orientation/timestamps與AMCL observations。
- 驗證covariance、temporal consistency在normal rotation與normal correction的分佈；stationary distinct-observation/persistence/Initial Pose epoch、READY transitions、authority silence與motion-update allowance。
- 在已授權條件測Teleop↔Establish native Spin ownership、cancel、explicit stop、fresh wheel/local-motion evidence與physical observation分開记录。
- 地圖外/尚無initialpose保持NOT_READY；robot/capability可用不是假READY。沒有map到TF的情況不得讓global task自動啟動。
- stop/servo/通信異常實驗只依documented controlled procedure與當次授權範圍，不為了測timeout自行拔線/解除保護。

每個case記revision/image、candidate parameters、topic/TF/time、物理觀察與預期/實測；不能用V2raised-wheel軌跡代替。fail即停止升級，未釐清前不進V4。

## 18. V4 ground short-distance verification plan

Prerequisite：**V3 PASS**、另行授權、low speed/short distance/clear area/E-stop immediately accessible。

- wheel scale/sign/encoder wrap、body displacement與EKF local motion一致；量測正反向短距離和受控轉向，不先提高速度範圍。
- Localization moving semantics：跨AMCL update門檻、normal drift corrections、unreviewed motion與response allowance、false READY revoke/false acceptance、Initial Pose後重新累積evidence。
- ROS command loss、controller timeout與實體stop delay/distance；區分owner revoke、zero publish、controller/M1 state、servo disable、physical stopped；device watchdog獨立實驗才能有結論。
- 適當時測native NavigateToPose短距離same/near XY+different yaw、route connector、fresh stopped result、cancel/preemption、localization loss bounded recovery，不把任意route/planner錯誤當reset理由。
- operator map-outside Teleop→Initial Pose/必要Establish→READY→native global activation/navigation完整受控流程。

Docking physical precision不是短距離Navigation的附帶PASS。若Vision/dock hardware可用，V4後新增**獨立controlled docking case**，測axes/offset/time、pose freshness、position+yaw tolerances、approach/terminal stop/cancel；無硬體就保留VERIFY。失敗停止升級與擴大範圍。

## 19. Calibration backlog

Architecture/implementation由approved plan決定；以下只是讓software可測/可啟動的configuration candidates。全部標 **UNVERIFIED / REQUIRES CALIBRATION**，數字不構成production calibration evidence。

| Parameters / units | Candidate configuration policy | Acceptance evidence / phase |
|---|---|---|
| `cmd_vel_timeout` seconds | 0.5（現有contract tests已有此期待）；一份產品來源，finite positive | V2 controller timeout，V4physical stopping |
| ownership source/lease timeout、handoff stop timeout | candidate source lease 0.5s，fresh feedback 0.2s，handoff deadline 2s；源週期與DDC timeout關係需檢查 | V1 expiry/order；V2/V3/V4grant/stop調整 |
| M1 host response/byte/transaction deadline | 現有50ms是unverified input；30Hz=33.3ms不可保證；實作明確deadline/overrun rejection，不任意調短冒充可行 | V2 actual FC17 loop percentile/worst-case；不滿足則record blocker再分析 |
| covariance variances x/y/yaw | new candidate `max_xy_variance=0.25 m²`, `max_yaw_variance=0.12 rad²`；validate finite/nonnegative/planar covariance validity | V3/V4ground scenarios；低值不證ground truth |
| consistency residual | candidate translation 0.20m、wrapped yaw 0.20rad；normal correction容忍 | V3rotation/V4translation實測分佈 |
| persistence | candidate `min_distinct_observations=3`, `good_persistence_s=1.0`；availability/high covariance/invalid evidence立即veto，重新ready再累積 | V1 distinct-stamp；V3/V4false transitions |
| unreviewed motion/update response | candidate accumulated translation 0.15m / yaw0.15rad、update response1.0s；與AMCL update_min_d/a=0.1搭配review；stationary不強制固定AMCL頻率 | V3/V4moving/stationary；round trip也計入motion |
| dependency freshness / heartbeat | ready heartbeat0.2s、consumer authority timeout1.0s；scan freshness0.5s、EKF feedback0.2s、TF lookup bound0.1s 為initial candidates | V2QoS/time，V3/V4latency；measurement/receipt分開 |
| Establish task budget / observation behavior | overall30s、native Spin最多一圈2π、單次observation20s 為initial candidates；cancel必須有界，unknown primitive outcome保持quarantine | V1 time/cancel；V3 controlled observation efficacy |
| goal/dock stop/yaw/position | Navigation保留現有candidate thresholds並標未校準；Docking新增candidate yaw0.10rad、linear stopped0.02m/s、angular stopped0.05rad/s、stop dwell0.3s/stop deadline2s | V4navigation；dedicatedDocking precision case |
| Vision age / TF | candidate pose timeout0.5s，完整保留source stamp | V2clock/frame；dedicatedDocking latency |
| telemetry TTL / diagnostics disappearance | selected telemetry TTL5s initial candidate；existing IMU100ms/LiDAR200ms receipt semantics保持；aggregator timeout以每producerperiod設定（通常≥3publish intervals） | V1expiry；runtimeoutage/resource soak |
| wheel covariance、IMU covariance/bias、motion limits/acceleration/deceleration | existing候選保持；沒有可靠實測不改成calibrated | V3/V4及指定calibration procedures |

候選數值集中對應的YAML/參數表，tests引用契約而不另建一份policy；diagnostics與ready不得各自配置不同threshold。review可調整candidate值但不得省略未校準標記。

## 20. Hardware/runtime VERIFY backlog

| VERIFY item | Earliest useful phase | Required evidence / closure rule |
|---|---|---|
| M1 ID/firmware/gear/encoder scale/sign/wrap | V2 identity，V3/V4physical motion | actual register+wheel/body measurements；unitconversion tests不代替 |
| reconnect、deactivate/crash/comm-loss stop | V2interfaces，V3/V4controlled cases | controller/M1/physical停機時間分開；未做physical觀察不稱safe stopvalidated |
| device watchdog有效settings/protective behavior | V2readback，受控V3/V4failure injection | both IDs、effective RAM、alarm action、實體反應；host timeout與DDC timeout不是此證據 |
| E-stop/STO存在、接線與rating | V2documents/inspection + independently approved validation | manual/installation/safety record；不得從ROS行為推論 |
| sensor acquisition latency / clock synchronization | V2timing，V3/V4motion correlation | IMU無device timestamp限制、LiDARdriverclock、M1poll time、Visionclock都列provenance |
| IMU mounting/sign/bias/covariance | V3，必要V4 | controlled body motion vs measured axes；靜態URDF不證安裝正確 |
| actual LiDAR frames / *_1 / handedness | V2headers/TF，V3physical scan alignment | driveremittedframe、normalizeroutput、RSPchain；不憑name猜 |
| Localization thresholds / consistency / persistence / stationary / moving | V3/V4 | normal/abnormal ground sequences，誤撤/誤准率；raised-wheel不可當calibration |
| map-outside deployment flow | V2infrastructure，V3/V4actual operation | base/Teleop依然可用、unknownpose NOT_READY、InitialPose→ready→globalactivation |
| navigation terminal/cancel/preemption | V4 | original goal pose/yaw、freshlocal velocity、controller與physical stopped證據 |
| Vision docking axes/offset/clock、precision/terminalstop | V2interface + V4後dedicatedcase | externalVisionactual measurements；無hardware保留open，不假稱navigation已覆蓋 |
| backend outage / bounded resources / retention | softwareV1 + dedicatedruntime soak | targetCPU/RAM/disk/network、corecontinuity、backendquery/retention單獨證明 |
| device permissions/network/containerGPU/arch paths | V2 | installedreleaseactualdevices，不能只查compose文本 |
| map quality / route usability / catalog accuracy | controlledMapping/sitevalidation，V4appropriate | nativeparse!=actualsitegeometrycorrect；人工資產準備仍需證據 |
| full production covariance/limits tuning | V3/V4extended calibration | limitselection/risk/evidence責任明確，不在one-shot猜測完成 |

V1 PASS不自動關閉本表任何physical item。V2 PASS→V3、V3 PASS→V4；failure均停止更高風險phase、record、分析，重新授權後才繼續。

## 21. Explicitly deferred / not-needed items

不建立任何implementation WI來實作：Navigation Manager、Docking Manager、AMR Manager、central SystemMonitor、`/system/ready`、custom differential-drive kinematics、custom EKF/global-localization/Route Server/Dock Action、Runtime Mode Manager、full simulation/Gazebo、multi-robot、charging schedule/workflow expansion、dock database、autonomous exploration、與EstablishLocalization無關的automatic Spin recovery、site business logic、fleet/Patrol/Mission business orchestration、Vision/image/AprilTag processing。

不保存scan-map architecture作debug/optional/future evidence。Q3 native extension僅為已批准的local DockRobot admission/terminal gap；Q1 control gate僅為必需motion ownership；Q6 native navigator extension僅為必需admission，不藉此引入上述manager或task wrapper。

## 22. Risks / blockers

| Risk / evidence | Required handling before / during execution |
|---|---|
| Missing原始GAP-001～022 registry | Q5 review補對照或明確採用本檔完整F registry；不能宣稱未知GAP都closed。 |
| GitNexus incompatibleDB42/runtime40 | futurepreflight恢復相容工具再symbol edits；若工具仍不能使用，reportdependencyimpactundetermined及externalblocker，不能靜默猜。 |
| Native APIs online≠deployed package | 使用officialJazzy evidence作規劃，futurequalifiedimage確認Route/helper/Spin/noncharging/navigatorports；Q4鎖qualifiedartifact；不因發現缺核心就自寫替代。 |
| Q1 ownership mechanism尚未批准 | 會影響task/source/stop integration，必須review選定、接口定稿後run；freshEKF不替代measuredwheelstop，同source的latecommand不能只靠Boolgrant。 |
| Native docking plugin alone不足 | Q3先批准可維護的nativeextension；不能以改isDocked又阻塞等stop的方式實作。 |
| Globalcostmap TF wait有界/manager啟動一次 | Q2不能依賴無限wait或未證明自動retry；localdependencies保持獨立。 |
| NativeAMCL/Spin request timeout可能late執行 | taskterminal與primitivecleanup分開：uncertainoutcomequarantine、保持NOT_READY/不重grant、latehandlemustcancel，避免generation-only假保護。 |
| Boolready無source stamp | retainedtrue不可立即當livepermission；heartbeat/steadyexpiry/firstliveconfirmationtests必需；沒有publicepochAPI。 |
| Initial Pose stationary觀測與post-prior因果順序 | Q7定案native prior/no-motion bootstrap；服務完成不當READY，無新distinct observations保持NOT_READY。 |
| Privateassets本機有，但未tracked/未必在build輸入 | manifest識別與容器可用性明確；保持private；missing需要外部供應，不能生成假geometry或skip驗收。 |
| 現有zero-bytetemplate與ignoredsite資料 | validate/exportfailfast，不替user填假site，不刪原始資產。 |
| Existingrelease/.env/site包含用户資料 | exporter不得rm-rf destination；新bundle先staging，安全promote/refuse覆蓋。 |
| Stop evidence等級與candidate thresholds | software可測sequence但物理值未校準；完整V1仍不叫hardwarevalidated/FeatureFreeze。 |
| Scope大且packages交叉 | 全部WI必須同run完成，integrationtests覆蓋跨boundary；不能僅交單subsystem自稱完成。 |

已查primarynative evidence（每項只支撐所列事實，未宣稱installedbinary已驗）：

- [Jazzy AMCL source](https://raw.githubusercontent.com/ros-navigation/navigation2/jazzy/nav2_amcl/src/amcl_node.cpp)：relative reset service、amcl_pose measurement stamp、event-driven publication與initial-pose控制；本計畫依此把reset集中在task內。
- [Jazzy hardware lifecycle](https://control.ros.org/jazzy/doc/ros2_control/hardware_interface/doc/lifecycle_of_a_hardware_component.html)：inactive state可有feedback read。[libmodbus response timeout](https://libmodbus.org/reference/modbus_set_response_timeout/) 與 [byte timeout](https://libmodbus.org/reference/modbus_set_byte_timeout/)：兩者不同，不能把response setting當整個loopbudget。
- [Jazzy joint_state_broadcaster](https://control.ros.org/jazzy/doc/ros2_controllers/joint_state_broadcaster/doc/userdoc.html) 原生 `/dynamic_joint_states` 可包含按 joint/interface name 描述的自訂 state interfaces；本計畫以此傳 measured-feedback validity/time，沒有另一套 drivetrain diagnostics-as-control parser。
- [Jazzy distribution registry](https://raw.githubusercontent.com/ros/rosdistro/master/jazzy/distribution.yaml)列twist_mux4.5.0-1；[upstream mux](https://raw.githubusercontent.com/ros-teleop/twist_mux/rolling/src/twist_mux.cpp)與[topic handles](https://raw.githubusercontent.com/ros-teleop/twist_mux/rolling/include/twist_mux/topic_handle.hpp)提供priority/timeout/locks，未實作本產品的cancel-and-confirm-stop契約。Registry指向rollingsource，但本計畫不把rollingtip當installedrelease。
- [Jazzy native navigator](https://raw.githubusercontent.com/ros-navigation/navigation2/jazzy/nav2_bt_navigator/src/navigators/navigate_to_pose.cpp)、[ComputeRoute ports](https://api.nav2.org/nav2-jazzy/html/compute__route__action_8hpp_source.html)、[ConcatenatePaths](https://api.nav2.org/nav2-jazzy/html/concatenate__paths__action_8cpp_source.html)：standardpathkey、numericrouteerror、直接append；產品周邊contract需自己補齊。
- [Jazzy odom subscriber](https://raw.githubusercontent.com/ros-navigation/navigation2/jazzy/nav2_dwb_controller/nav_2d_utils/include/nav_2d_utils/odom_subscriber.hpp)與[StoppedGoalChecker](https://raw.githubusercontent.com/ros-navigation/navigation2/jazzy/nav2_controller/plugins/stopped_goal_checker.cpp)：defaulttopic/cachedtwist不足以證明freshstopped；因此WI-007/013分別補wiring與freshness。
- [Jazzy costmap activation](https://raw.githubusercontent.com/ros-navigation/navigation2/jazzy/nav2_costmap_2d/src/costmap_2d_ros.cpp)、[native lifecycle manager](https://raw.githubusercontent.com/ros-navigation/navigation2/jazzy/nav2_lifecycle_manager/src/lifecycle_manager.cpp)、[controller local costmap](https://raw.githubusercontent.com/ros-navigation/navigation2/jazzy/nav2_controller/src/controller_server.cpp)：initialTFwait有timeout、startup非無限retry、controller擁有embeddedlocalcostmap。
- [Jazzy noncharging plugin](https://raw.githubusercontent.com/ros-navigation/navigation2/jazzy/nav2_docking/opennav_docking/src/simple_non_charging_dock.cpp)與[native docking server](https://raw.githubusercontent.com/ros-navigation/navigation2/jazzy/nav2_docking/opennav_docking/src/docking_server.cpp)：distance-onlycompletion、approach持續命令直到到位、zero後直接native success，需Q3最小extension。

## 23. Questions for ChatGPT review

只有下列七項要在ONE IMPLEMENTATION RUN **之前**定案。每項批准選項後更新本檔的關聯WI/接口/新增檔案與驗收；不同選項不得留給執行代理二選一。mock/time policy已依最小scope採明確reject，不重開架構題；hardwarecalibration不是implementation前架構問題。

### Q1 — Exact motion-command ownership mechanism

- **Decision required:** 選定exclusiveauthority/handoff的實體機制與internallease接口。
- **Why implementation cannot safely choose it:** plain twist_mux只按priority/timeout/locks選訊息；不會canceloldexecution、explicitstop/confirm/grant。controllerchaining也不自帶taskhandoff。選擇改變全部cmd_vel/taskintegration，原synthesis沒有批准concretemechanism。
- **Available options:** A. maturetwist_mux + minimallease/handoffadapter + source gating，完整證明不能fallback/bypass；B. 單一minimalexclusivecommandgate，reuse nativeActioncancel/DDC/controllerstatus，不再加redundantprioritymux。
- **Recommended option based on current evidence:** **B**。truegap是exclusiveownership與handoff，現有成熟mux不能消除此customresponsibility。gate放mobile_base_control，不是Manager。固定sourceIDs navigation/docking/teleop/localization_observation；`MotionAuthority.srv` request含operation（request/renew/release）、source_id、lease_id（request=0）、client_request_id；response為requestaccepted、lease_id、currentstate、minimalreason。request先回accepted/pending，不blocking等physicalstop；`MotionAuthorityState` reliablevolatilelast1 heartbeat給owner/state/generation/reason，只有GRANTED且token符合才effective。states NONE/REVOKING/STOPPING/GRANTED/FAULT；steadylease0.5scandidate，stopdeadline2s。每次grant清buffer並設source-stampwatermark；uncertainoldActionoutcome不grant同source新lease。nativeendpoints cancellation由固定sourceadapter負責並回報terminal，不把不同task都cancel-all。外部Takeover終止oldtask；internalrecovery只暫停FollowPath。此protocol不當publicmissionAPI。
- **Files/subsystems affected:** WI-003–006/010–011/016–017，control gate、interfaces、全部source remaps/Teleop/task adapters、diagnostics/tests/operator。

### Q2 — Global lifecycle activation 與 local costmap ownership

- **Decision required:** map-outside部署下，globalgroup由誰在何時啟動；明確localcostmap保留在哪個nativegroup。
- **Why implementation cannot safely choose it:** nativeglobalcostmap預設initialTFtimeout60s，nativeautostart一次失敗不保證後來自行成功。持續綁READY會干擾mid-goalrecovery。只拆dockingserver仍可能依賴globalgroup內controllercostmap。
- **Available options:** A. independentlocalcontroller/costmap/behaviors、dockinggroup、nativeglobalmanager `autostart=false`，operator呼nativeManageLifecycleNodes啟動；B. 相同groups但新增最小one-timeTFavailabilityactivationobserver；另建standalonelocalcostmap只在證明不能重用embedded時才選，須同步定topic/instanceownership。
- **Recommended option based on current evidence:** **A，reuse controller-owned embedded local costmap**。map_server/AMCL+Evaluator啟動，localcontroller/Spin/Dock獨立；operatorInitialPose/Establish後透過`/lifecycle_manager_navigation/manage_nodes` nativeSTARTUP（或已知配置狀態的RESUME）啟動globalplanner/route/BT。READY只管taskdependency，false不自動deactivateinfrastructure。將此額外operatorstep寫入MVP產品流程；沒有manager/autoobserver。
- **Files/subsystems affected:** WI-010/011/016/018/025，launchgroups、node_names、localcostmaptopics、operator流程與startupfailuretests。

### Q3 — OpenNav local admission / stopped-terminal extension boundary

- **Decision required:** 批准實現local-onlygoalflags、freshpose/yaw與stop-before-terminal的nativeextension方式。
- **Why implementation cannot safely choose it:** nativeSimpleNonChargingDock只看XY；isDocked=false時server繼續approach，plugin-only等待stopped會卡住或繼續推進。nativecallerflag也不等於server強制local-only。複製另一DockingServer或競爭發cmd_vel會違反frozenboundary。
- **Available options:** A. qualified/pinnedupstreamOpenNav最小sourceoverlay/patch，保留nativeDockRobot/actionserver/core，nativeplugin擴position/yaw，server補goaladmission及cancelablestopconfirmationhook；B. 若review已有具體已發布native版本/extensionhook符合完全相同契約，批准該exactversion/API替代A，附可驗證證據。僅維持distance-only不滿足需求，不能列成合格選項。
- **Recommended option based on current evidence:** **A**。patch限定localgoalflag/framecheck、taskauthorityhook、pose reached→zero→freshstopdwell→release→terminal，以及cancelrace；不要forkplanner/controller或改nativeAction定義。source.repos固定qualifiedJazzycommit、patchhash/licensing，Docker唯一overlay版本；entry與terminal都要nativeintegrationtests。review批准後由releasepreflight記錄exactSHA，不以unqualifiedrollingtipbuild。
- **Files/subsystems affected:** WI-016/017/023/024，nativeOpenNavpackageoverlay、localplugin/launch、Docker/provenance、DockRobottests。

### Q4 — Reproducible-enough release dependency policy

- **Decision required:** release以immutablequalifiedartifact為復現單位，或要求rebuild也從固定apt快照完全復現。
- **Why implementation cannot safely choose it:** 現行Dockerfile的Jazzyaptpackages未pin；選snapshot/mirror或artifact-lock會改release維運責任，沒有已批准lockpolicy；不能從developer機任選版本。
- **Available options:** A. immutableimagearchive+imageID/digest、base digest、source/patch鎖、完整installedpackageinventory；resolveddependencyset每變動視新release重新V1qualification；B. A再加維護apt snapshot/repository及完整versionlock以支援可重建依賴集合。
- **Recommended option based on current evidence:** **A**，符合現有export/loadbundle流程與MVP。保留qualifiedartifact即可精確部署同版本；清楚區別deploymentreproducibility與bit-for-bitrebuild。不允許舊tag遮蔽新artifact；native組合以完整V1而非隨意aptpin定案。
- **Files/subsystems affected:** WI-023/024、Dockerfile/exporter/compose/manifest/operator Release；Q3overlay同樣列身份。

### Q5 — 原始 GAP registry 與完整批准 scope 的對照權威

- **Decision required:** 提供GAP-001～022原始finding→ID對照並在§5補alias，或明確批准本輪user101章+F-001～029作完整execution scope registry（GAP-003已知alias保留）。若存在具體external `/localization/lost` consumer契約，同時提出並在run前定案。
- **Why implementation cannot safely choose it:** repo/source/spec及提供historicalfile未找到registry；只知道本輪明確提到GAP-003。捏造其餘21個ID會產生虛假traceability；未檢查外部repo不能保證無externalcontract。
- **Available options:** A. 補原synthesisregistry並只做對照完整性核對；B. 明確採本輪詳列finalscope與Fregistry為批准execution清單，不假配舊ID。
- **Recommended option based on current evidence:** **A若原表可取得，否則B**。無論選哪項，所有本輪已批准softwarechanges已以Frows/WIs覆蓋；不得因此重做subsystemaudit或重開frozenLocalization。若原表揭露額外已批准項，必須在此同一plan審查中補齊後才開始run。
- **Files/subsystems affected:** 本planning§5與最终traceability/evidence；有externalcontract才改interface清理決定，無證據不保留compatibility。

### Q6 — Native NavigateToPose admission integration surface

- **Decision required:** 如何確保directnativegoals/preemption/BToverride都不能繞過ready與requiredproductionBT契約。
- **Why implementation cannot safely choose it:** defaultBTrootguard能保護預設tree，但nativeNavigateToPose goal有`behavior_tree`欄位；任意XML可能沒有guard。需求保留nativeAction，不能默默加wrapper或只保護stationcaller。
- **Available options:** A. 最小nativeNavigatorplugin延伸既有NavigateToPoseNavigator，在goalReceived等supportednativehook做freshready及productionBTallowlist，之後委派nativebehavior；B. 全部taskadmission放BT，對外正式限定onlyapprovedBT並另提供可證明的server-sideoverride拒絕機制（review須明定，不能只有文件口頭限制）。
- **Recommended option based on current evidence:** **A**。同名同type nativeNavigateToPoseaction不變；接受空behavior_tree（用shippedtree）或canonicalshippedtreepath，拒絕其他path；每次新goal/preemption檢查livefreshready、clearper-goalrecoverystate。plugin只做admission/選定dataset參數與nativehandoff，不接管planner/controller/actionalgorithm；mid-taskrecovery由WI-011productionBT。低階FollowPath/Spin的motion仍受WI-005，不能透過直接呼叫internalnativeaction繞過owner。
- **Files/subsystems affected:** WI-011/013/014/015，navigatorplugin/export/config、BT/contracts、site-manifestreadonlyparameters、nativeadmissiontests/operatordocs。

### Q7 — Normal Initial Pose 的有序套用與 stationary observations

- **Decision required:** 正常 Initial Pose 如何在不 global reset / Spin 的情況取得多筆 distinct AMCL observations，並確保 post-prior evidence 的因果順序。
- **Why implementation cannot safely choose it:** native AMCL stationary 不承諾持續發布新 pose；單次 prior 後只有一筆 observation，不能滿足 frozen N-sample persistence。Evaluator 與 AMCL 各自直接訂閱 `/initialpose` 也無跨 node callback ordering guarantee。不能靠 timer 重算同筆 pose 或默默 force global reset 解決。
- **Available options:** A. Localization task layer 內做 bounded native prior/no-motion bootstrap，public `/initialpose` 保持原訊息，內部有序套用；B. 明確要求 operator 在 Initial Pose 後提供足夠 Teleop observation motion/native no-motion requests，另批准具有同等因果順序的 prior integration。B 必須更新產品正常流程，不能僅說等 AMCL 自己多發幾筆。
- **Recommended option based on current evidence:** **A**。capability 先 receive/validate prior → `begin_epoch`/publish false → native `nav2_msgs/srv/SetInitialPose`（root `/set_initial_pose`）套用一次 → 確認 native AMCL active、request completed，建立 observation watermark → bounded `request_nomotion_update`（root `/request_nomotion_update`）搭配 fresh scans → evaluator 以新 stamps 累積 evidence。原 native AMCL `initialpose` subscriber remap到 capability-private endpoint，避免同一外部 prior direct+forward double apply；不新增 public epoch/reset manager。service ACK 不是 readiness proof，也不把 inactive/invalid prior被忽略的ACK當套用成功。新prior/map或uncertainpending native request用既有quarantine規則；bootstrap不產生motion、不偷偷reset或取得velocityowner。Action以外的正常流程只有ready/diagnostics，不新增重複task result。
- **Files/subsystems affected:** WI-009/010/018/025；existing localization node/task/launch/config及native interface tests，不另加manager/package。Q7屬先前未具體選定的integration，不重開frozen evidence model。

## 24. Planning verdict

**READY FOR CHATGPT REVIEW**

Work items：**27**。Questions for ChatGPT review：**7**。此verdict表示本檔已把完整software scope、removal/migration、one-run dependency sequence、V1及gatedV2/V3/V4整理成可審清單；**不表示implementation已批准、V1已執行或硬體已驗證**。ChatGPT解決七項問題、將final選擇合入此同一檔並批准後，Codex可用ONEimplementationprompt执行全部WI與V1。沒有預定的WI間人工approval或第二implementationphase。

# 04 Reuse Assessment Checklist

本清單只用於追蹤 `04_reuse_assessment.md` 的討論、盤點與稽核進度，不是 requirement、reuse coverage 或 architecture 的 normative source。

`01_use_cases.md`、`02_capabilities.md` 與 `03_requirements.md` 已定案；04 必須保持每個 `SYS-xxx` 的原始語意，只評估 exact-version 成熟方案的 coverage、constraints、evidence 與 minimum gaps，不得新增、刪除、弱化或重新解釋 requirement。

若盤點發現 01–03 可能存在缺漏或矛盾，必須停止受影響項目的 assessment、標記為上游阻塞並提出問題；未取得核准前不得修改 01–03，也不得由 04 靜默補造 product intent。

`05_architecture.md`、`06_subsystem.md` 與 `07_backlog.md` 應待 04 完成並核准後，再依序重新審視。

## Status

- `[ ]` 待討論：尚未形成或核准 assessment conclusion。
- `[~]` 討論中：目前唯一正在處理的議題。
- `[x]` 已完成：內容已討論、核准、寫入並完成相應檢查。
- `[-]` 不適用／延後：已有明確理由與重新啟動條件，不得用來跳過 baseline requirement。
- `[!]` 上游阻塞：發現 01–03 可能缺漏或矛盾，必須先取得上游處理決定。

一次只能有一個 `[~]` 議題。取得核准前，不得預先寫入後續 requirement 的 candidate、coverage 或 gap conclusion。

## Progress

- 總議題：40
- 已完成：30
- 上游阻塞：0
- 討論中：0
- 待討論：10
- 目前進度：30 / 40

## A. Common Reuse-assessment Rules

- [x] 1. Authority, scope, and downstream boundary
  - 完成條件：確認 01–03→04→05 authority、04 可做與禁止的決定，以及上游問題的停止與回退規則。
- [x] 2. Coverage status and assessment-record format
  - 完成條件：確認每個 SYS 的固定 record，以及 `Fully Covered`、`Partially Covered`、`Not Covered`、`Needs Verification` 與 `Not Applicable` 的使用方式。
- [x] 3. Exact-version and evidence-source rule
  - 完成條件：定義官方文件、vendor baseline、source、runtime、integration、real-hardware 與 assumption 的證據層級、版本與引用方式。
- [x] 4. Candidate comparison and minimum-gap rule
  - 完成條件：定義多候選比較、configuration／composition coverage、constraint 與 minimum custom gap 的記錄方式，不提前設計 subsystem internal implementation。
- [x] 5. Assessment order and per-requirement completion rule
  - 完成條件：確認依成熟方案領域盤點但每個 SYS 獨立定案，以及 requirement record 的 Definition of Done。

## B. Requirement-by-requirement Assessment

### Robot Description

- [x] 6. SYS-023 Robot Description
  - 完成條件：完成機器人幾何、座標系與關節定義之成熟方案 coverage record。

### Perception and Odometry

- [x] 7. SYS-003 LiDAR Perception
  - 完成條件：完成 LiDAR 掃描供建圖、定位與導航使用之成熟方案 coverage record；維持 independent-source-first，並確認 RF2O 的單一 merged-scan dependency 由 ROS 2 Jazzy `dual_laser_merger` 0.3.1 覆蓋，其配置與實機 evidence 留待後續 closure。
- [x] 8. SYS-004 IMU Perception
  - 完成條件：完成 IMU 量測供定位使用之成熟方案 coverage record。
- [x] 9. SYS-005 System Odometry
  - 完成條件：完成 wheel odometry、`dual_laser_merger` 0.3.1 所產生之 merged-LaserScan-derived RF2O odometry 與 IMU 產生平面里程、唯一 `odom -> base_footprint` publication，以及輸入異常或逾時時沿用 `robot_localization` 原生 fusion／prediction 行為之成熟方案 coverage record。

### Motion and Drive

- [x] 10. SYS-022 Base Motion Control
  - 完成條件：完成 ROS 2 Jazzy `ros2_control + diff_drive_controller` 對 `TwistStamped` 速度命令、差速輪運動學、wheel velocity command interfaces 與底盤移動之成熟方案 coverage record。
- [x] 11. SYS-026 Base Fault Handling
  - 完成條件：完成 hardware interface 回傳 `ERROR` 時，由 ROS 2 Jazzy ros2_control 停止使用該硬體介面的 controllers，並使managed error state可被觀察之成熟方案 coverage record。
- [x] 12. SYS-027 Motion-command Timeout
  - 完成條件：完成 ROS 2 Jazzy `diff_drive_controller` 在 non-chained `TwistStamped` input、非零 `cmd_vel_timeout` 條件下的 command-age timeout 與停止命令之成熟方案 coverage record；保留 limiter profile、hardware delivery 與實體停止時間／距離之整合及實機 evidence obligations。
- [x] 13. SYS-028 Base Motion Limits
  - 完成條件：完成 AMR 直線／旋轉速度與相應加速／減速 operational limits 之成熟方案 coverage record；wheel speed 與 motor RPM limits 視為由 system-level limits 推導的後續 architecture／subsystem configuration，不作為 SYS-028 的獨立 requirement fragments。
- [x] 14. SYS-029 Base State Feedback
  - 完成條件：完成 measured wheel position／velocity、validity 與禁止 command substitution 之成熟方案 coverage record。
- [x] 15. SYS-030 Safe Base Enable and Stop
  - 完成條件：完成 enable prerequisites、stop confirmation、driver disable 與 independent safety-action attempts 之成熟方案 coverage record。

### Mapping

- [x] 16. SYS-001 Map Creation
  - 完成條件：完成 ROS 2 Jazzy `slam_toolbox` 2.8.5-1 online asynchronous mapping 對lifecycle configure／activate初始化、失敗diagnostics與二維Occupancy Grid建立之成熟方案coverage record；以ACTIVE作為可處理資料狀態，不追加runtime input readiness／首筆scan gate，並保留selected scan、TF／odometry整合、exclusive`map -> odom` ownership、部署參數與實機map-fitness evidence obligations。
- [x] 17. SYS-002 Map Storage
  - 完成條件：完成 ROS 2 Jazzy `nav2_map_server` 1.3.12-1 `map_saver_cli`／lifecycle `SaveMap` 將 authoritative Occupancy Grid 儲存為 per-site `map.pgm`、`map.yaml`，並以 boolean／process result 與原生 logs 回報儲存失敗及原因之成熟方案 coverage record；保留固定 basename／format、persistent writable filesystem、overwrite與partial residue之配置及evidence obligations，且將儲存後 read-back 明確留給 SYS-024，不混入Route Graph、Station Catalog或Navigation startup load。
- [x] 18. SYS-006 Continuous Map Update
  - 完成條件：完成 ROS 2 Jazzy `slam_toolbox` 2.8.5-1 online asynchronous mapping 對有效scan與scan-stamped odometry之measurement acceptance、pose-graph更新、週期性Occupancy Grid刷新，以及input暫時不可用時保留既有地圖並等待後續有效資料之成熟方案 coverage record；保留TF／QoS、acceptance parameters、active map subscriber、使用者完成／終止時的lifecycle stop ordering及真機cadence／drop／恢復／map progression evidence obligations，且不要求每筆raw scan一對一更新、雙LiDAR merge或自訂input-health／automatic-termination元件。
- [x] 19. SYS-007 Map Load
  - 完成條件：完成 ROS 2 Jazzy Navigation2 1.3.12-1 `localization_launch.py map:=...`、lifecycle `map_server`／manager與AMCL之startup Map Package載入、Occupancy Grid發布及載入失敗阻止navigation-ready之成熟方案coverage record；不納入runtime `LoadMap`／hot switch，並保留target version、實際Map Package、lifecycle／map QoS與failure evidence obligations。
- [x] 20. SYS-024 Map Package Read-back
  - 完成條件：完成 ROS 2 Jazzy Navigation2 `nav2_map_server` 1.3.12-1 public MapIO `loadMapFromYaml()` 對儲存後Map Package之YAML／image解析、Occupancy Grid conversion、標準`LOAD_MAP_STATUS`與原生失敗原因logs之成熟方案coverage record；採標準parser結果而不追加non-empty／quality validation，保留target version、成功與各failure status、path identity及無`/map` side effect之evidence obligations。

### Target, Resource, and Localization

- [x] 21. SYS-008 Navigation Target
  - 完成條件：重新確認 Station／Goal Pose external target forms、最小terminal-facing discriminator，以及分別交由SYS-032／SYS-009形成canonical `PoseStamped`之coverage record；保留terminal syntax、欄位保真及admission boundary之evidence obligations。
- [x] 22. SYS-009 Goal Pose Normalization
  - 完成條件：完成v0.1 `nav_goal pose --x <m> --y <m> --yaw-deg <deg>`至canonical `PoseStamped`之成熟型別／tf2 coverage與最小terminal normalization adapter record；保留absolute semantics、degrees-to-radians／quaternion、global frame／timestamp、missing／unparseable reason及SYS-033 handoff之evidence obligations。
- [x] 23. SYS-032 Station Target Resolution
  - 完成條件：完成standard `PoseStamped`／通用parser可重用範圍、Nav2缺少Station semantics所需最小exact-match Station resolver，以及empty／unknown／unresolvable rejection reason之coverage record；保留人工確認Catalog、schema／parser、ID comparison、resolved-pose field preservation與SYS-033 handoff之evidence obligations。
- [x] 24. SYS-033 Canonical Goal Pose Validation
  - 完成條件：完成standard finite／tf2 validation primitives、Nav2提交後部分防線與最小pre-navigation combined validator／gate之coverage record；保留quaternion tolerance、TF timeout、frame／timestamp policy、failure reasons、valid-pose field preservation與invalid target不得下送之evidence obligations。
- [x] 25. SYS-010 Map Localization
  - 完成條件：完成ROS 2 Jazzy Navigation2 AMCL 1.3.12-1對loaded map／LaserScan／odom-TF定位、standard pose、exclusive`map -> odom`及RViz Initial Pose之原生coverage record；不追加localization-valid／admission／loss policy，並保留frames／QoS／parameters、人工操作與實機定位evidence obligations。
### Navigation Execution

- [x] 26. SYS-011 Path Planning
  - 完成條件：完成Navigation2 Jazzy Planner Server 1.3.12-1對current pose／active-stage goal、有效非空path、失敗時不開始tracking及原生規劃結果之coverage record；跨stage continuity、route alternatives、tracking、stop與fallback classification分別保留於SYS-013、SYS-015、SYS-017、SYS-018～021，不重複計入SYS-011。
- [x] 27. SYS-014 Obstacle Avoidance
  - 完成條件：完成Navigation2 Jazzy 1.3.12-1 layered global/local costmaps、collision-aware planner/controller、Planner/Controller Server、standard BT與核准納入之`nav2_collision_monitor`對障礙物資訊、occupied-space avoidance、native failure及zero-velocity stop attempt的coverage record；保留sensor freshness、costmap/footprint、Collision Monitor zones/timeouts、cmd_vel chain及physical-stop實機evidence obligations。
- [x] 28. SYS-015 Path Tracking
  - 完成條件：完成Navigation2 Jazzy 1.3.12-1 Controller Server、`FollowPath`、selected controller、Progress Checker與standard BT對active-stage path tracking、continue/failure判定、zero-velocity stop attempt及原生結果之coverage record；保留controller/progress configuration與實機tracking evidence，並要求SYS-018～020後續assessment承接stage transition及First Mile／On Route／Last Mile continuity。
- [x] 29. SYS-016 Goal Completion
  - 完成條件：完成Navigation2 Jazzy 1.3.12-1 Controller Server、`FollowPath`、`StoppedGoalChecker`與standard NavigateToPose BT對final target XY／yaw及odometry-derived translational／rotational stopped predicate之coverage record；保留goal/stop thresholds、`stateful`、odom minimum thresholds、final endpoint preservation與實機success-chain evidence obligations。
- [x] 30. SYS-017 Navigation Result
  - 完成條件：完成ROS 2 action與Navigation2 Jazzy 1.3.12-1 `NavigateToPose`／BT Navigator對`SUCCEEDED`／`ABORTED`／`CANCELED`、child native error-code aggregation及可取得原生failure result之coverage record；不建立stage-aware taxonomy，並保留cancel completion、error propagation與terminal呈現evidence obligations。
- [ ] 31. SYS-025 Navigation Cancellation
  - 完成條件：完成 active navigation cancellation、termination 與 cancel result 之成熟方案 coverage record。

### Route-assisted Strategy

- [ ] 32. SYS-013 Route-preferred Navigation Strategy
  - 完成條件：完成 Route Graph 優先、route-assisted movement 與禁止不必要完整 free-space movement 之成熟方案 coverage record。
- [ ] 33. SYS-018 First Mile
  - 完成條件：完成 current pose 至 route entry 的 safe connection 與 not-required semantics 之成熟方案 coverage record。
- [ ] 34. SYS-019 On Route Navigation
  - 完成條件：完成 Route Graph connectivity、direction、availability constraints 與 route execution 之成熟方案 coverage record。
- [ ] 35. SYS-020 Last Mile
  - 完成條件：完成 route exit 至 Canonical Goal Pose 的 safe connection 與 not-required semantics 之成熟方案 coverage record。
- [ ] 36. SYS-021 Reserved Free-space Fallback Boundary
  - 完成條件：完成 eligibility、v0.1 unavailable behavior、failure-boundary exclusions 與 future-extension coverage record。

## C. Final Reuse-assessment Audit

- [ ] 37. SYS coverage completeness
  - 完成條件：31 個唯一 SYS requirements 各有一份已核准 coverage record，沒有遺漏、重複或被 group conclusion 取代。
- [ ] 38. Evidence, version, and source consistency
  - 完成條件：candidate、exact version／platform、官方或實證來源、適用範圍與尚缺 evidence 一致且可追溯。
- [ ] 39. Minimum-gap and prohibited-content audit
  - 完成條件：每個 partial／not-covered gap 都直接對應 requirement fragment；04 未新增 requirement、architecture owner、subsystem 或 custom implementation design。
- [ ] 40. 04→05 handoff and final baseline review
  - 完成條件：coverage、constraints、minimum gaps、candidate comparison 與 unresolved verification obligations 可供 05 做 architecture decision，且 04 已完成整體一致性審查與核准。

## Per-requirement Definition of Done

每個第 6–36 項 requirement 只有在下列條件全部成立時才可標記完成：

- Requirement ID 與 Required Behavior／Constraint 保持 03 原始語意。
- Candidate Mature Solution 或 `none` 明確。
- Exact Version／Platform 明確；尚無法確認時標記 `Needs Verification`。
- Coverage Status 已核准。
- Covered Scope 與 Known Constraints 明確。
- Uncovered Gap 明確；完全覆蓋時記錄 `none`。
- Evidence Type、Source、驗證範圍與尚缺層級明確。
- Architecture Consideration 只提出交給 05 的 constraint 或 choice，不先配置 owner 或設計 internal component。
- 多個候選方案未被混合成無法追溯的單一結論。
- 內容已取得使用者核准、寫入 `04_reuse_assessment.md` 並完成相應檢查。

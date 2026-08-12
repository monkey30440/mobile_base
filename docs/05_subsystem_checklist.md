# 05 Subsystem Design Refactoring Checklist

本清單只用於追蹤 `05_subsystem.md` 的討論、重構與整合稽核進度，不是 subsystem design 的 normative input。

`04_architecture.md` 是 05 的 normative design input。若 05 發現 04 缺漏、矛盾或無法實現，必須標記為上游阻塞並回到 01–04 處理，不得在 05 靜默改寫 architecture responsibility 或 system-wide contract。

## Status

- `[ ]` 待討論：尚未形成或核准設計。
- `[~]` 討論中：目前唯一正在處理的議題。
- `[x]` 已完成：內容已討論、核准、寫入並完成相應檢查。
- `[-]` 延後：已明確決定不屬於目前 baseline。
- `[!]` 上游阻塞：05 發現 01–04 缺漏或矛盾，必須先完成上游修正。

一次只能有一個 `[~]` 議題。取得核准前，不得預先寫入後續 subsystem 的未決設計。

## Progress

- 總議題：31
- 已完成：3
- 待討論：28
- 目前進度：3 / 31

## A. Common Subsystem-design Rules

- [x] 1. Authority, scope, and downstream boundary
  - 完成條件：確認 04→05→implementation→verification authority，以及發現上游問題時的停止與回退規則。
- [x] 2. Uniform subsystem section template
  - 完成條件：確認每個 subsystem 的固定章節、必要內容及禁止內容。
- [x] 3. Design status and evidence labels
  - 完成條件：定義 Approved、Candidate、Needs Official Verification、Needs Integration Test、Needs Real-hardware Validation 與 Deferred 的使用方式。
- [ ] 4. Mature-solution and minimal-custom-code rule
  - 完成條件：定義 exact-version 官方能力查證、configuration／composition 優先順序及 custom-gap justification。
- [ ] 5. Interface and configuration ownership rule
  - 完成條件：定義 producer／consumer、authoritative publisher、frame、QoS、parameter、configuration 與 lifecycle ownership 的記錄方式。
- [ ] 6. Verification model
  - 完成條件：區分 source、build、interface、runtime、integration、real-hardware 與 safety evidence，並定義每個 subsystem 的 verification section。

## B. Subsystem Design

- [ ] 7. Robot Description
  - 完成條件：承接 geometry、joint、static-frame 與 readiness responsibility，定義 internal design、interfaces、configuration 與 verification。
- [ ] 8. Drive Hardware Interface
  - 完成條件：承接唯一 hardware access、command／feedback、configuration validation、fault、enable／stop／disable 與實機驗證責任。
- [ ] 9. Motion Control
  - 完成條件：承接 authorized vehicle command、differential-drive conversion、limits、timeout、wheel odometry 與 stopped-state responsibility。
- [ ] 10. LiDAR Perception
  - 完成條件：承接各 LiDAR source、measurement validity、frame、device state 與 independent-source-first contract；非必要不融合。
- [ ] 11. IMU Perception
  - 完成條件：承接 IMU communication、unit／axis／time／frame semantics、validity、calibration boundary 與 diagnostics。
- [ ] 12. State Estimation
  - 完成條件：承接 system planar odometry、validity 與 `odom → base_footprint`；auxiliary odometry 只在 evidence 支持時納入。
- [ ] 13. Mapping
  - 完成條件：承接 Occupancy Grid、Mapping Mode `map → odom`、input validity、candidate map 與 authoritative Mapping Result aggregation。
- [ ] 14. Navigation Resource Management
  - 完成條件：承接 resource-set selection、loading、validation、identity、readiness、Map Package storage／reload 與 package-operation result。
- [ ] 15. Navigation Target Resolution
  - 完成條件：承接 Station ID／Absolute Goal Pose validation、normalization、Canonical Goal Pose 與 target failure boundary。
- [ ] 16. Map Localization
  - 完成條件：承接 initial pose provision、known-map pose estimation、localization validity 與 Navigation Mode `map → odom`。
- [ ] 17. Navigation
  - 完成條件：承接單一 execution、route-preferred strategy、First Mile／On Route／Last Mile、reserved fallback boundary、planning／control、arrival、cancel 與 result。
- [ ] 18. System Operation Coordination
  - 完成條件：承接 deployment-time flow selection、lifecycle ordering、prerequisite checks、mode activation 與 command-authority assignment，避免建立未必要的 custom coordinator。

## C. Cross-subsystem Integration Audit

- [ ] 19. Vehicle command and command-authority chain
  - 完成條件：Manual／Navigation command、authority assignment、enforcement、wheel command 與 hardware command producer／consumer 完整配對。
- [ ] 20. Drive feedback, wheel odometry, and system odometry chain
  - 完成條件：motor feedback→measured wheel state→wheel odometry→system planar odometry 的 owner、interface、frame、time 與 validity 一致。
- [ ] 21. Coordinate-frame and joint-state chain
  - 完成條件：static／dynamic TF 與 measured joint state 各有唯一 publisher，Mapping／Localization mode 不產生衝突。
- [ ] 22. Perception data chain
  - 完成條件：各 scan／IMU source 到 Mapping、Localization、Navigation／State Estimation 的 interface、QoS、frame、time 與 validity contract 閉合。
- [ ] 23. Mapping integrated flow
  - 完成條件：startup、teleoperation、map update、authority revocation、safe stop、Map Package storage／reload 與唯一 Mapping Result 可實際串接。
- [ ] 24. Localization initialization and validity flow
  - 完成條件：Map ready→initial pose when required→convergence→localization valid→Navigation acceptance 的介面與 readiness gate 閉合。
- [ ] 25. Navigation resource, target, and execution flow
  - 完成條件：resource identity、target normalization、route-assisted stages、cancel、arrival 與 result interfaces 完整閉合。
- [ ] 26. Lifecycle, startup, shutdown, and mode flow
  - 完成條件：dependency ordering、readiness、authority transition、shutdown 與 fault state 能由具體 runtime composition 實現。
- [ ] 27. Failure, diagnostics, and safe-stop flow
  - 完成條件：primary failure、secondary safety failure、safe-stop evidence、fault propagation 與 physical E-stop boundary 可追溯且不互相覆蓋。
- [ ] 28. Container deployment contract and implementation handoff
  - 完成條件：05 定義 runtime components、device access、volumes、network、privileges／capabilities、environment configuration、health／readiness、startup ordering 與 shutdown obligations；實際 `Dockerfile`、Compose services 與 image build design 留待 implementation，且可追溯回上述 contracts。

## D. Final Subsystem-design Audit

- [ ] 29. 04→05 traceability completeness
  - 完成條件：04 的每個 subsystem responsibility、requirement allocation、cross-subsystem relationship、operational flow 與 system-wide contract 都有 05 實現責任或明確 handoff。
- [ ] 30. Obsolete-design and over-design audit
  - 完成條件：移除舊 subsystem、重複 owner、premature framework、未核准 future feature 及僅因歷史 implementation 存在的設計。
- [ ] 31. Final consistency and baseline review
  - 完成條件：package／component、interface、configuration、lifecycle、failure、verification、diagram 與 traceability 一致；Design Baseline 與尚未完成的 integration／real-hardware evidence 明確分離。

## Per-subsystem Definition of Done

每個第 7–18 項 subsystem 只有在下列條件全部成立時才可標記完成：

- 04 的 purpose、responsibilities、requirement allocation 與 excluded responsibilities 已承接。
- Boundary、inputs、outputs、dependencies 與 authoritative interfaces 清楚。
- Internal components 各自有單一責任與存在理由。
- 成熟 solution 已依 exact version 的官方資料查證。
- Configuration／composition 優先，custom code 只涵蓋已證明的最小缺口。
- Package／component、ROS interface、frame、QoS、lifecycle 與 parameter ownership 清楚。
- Failure detection、diagnostics、degraded／invalid behavior 與 safe-stop contribution 清楚。
- Verification items 能證明實際 responsibility，不以 process／topic 存在冒充有效性。
- Approved、Candidate、待驗證與 Deferred decision 明確分離。
- 與已完成 subsystem 的 producer／consumer contracts 一致。

## Deferred Decisions

- LaserScan merge algorithm：未定；只有 consumer requirement 與整合 evidence 證明必須融合時才討論。
- Free-space Fallback implementation：v0.1 不實作，只保留 eligibility 與 failure boundary。
- Runtime dynamic mode switching：v0.1 不要求。
- Automatic localization、fixed startup pose 與 last-pose persistence：不屬於 v0.1。
- Dynamic resource switching、resource versioning、checksum、rollback、remote deployment 與 resource database：不屬於 v0.1。

## Follow-up Documentation Work

- 01–03 各自補一份精簡的維護 checklist，用於後續新增或修改時追蹤審核狀態，不回填成當時逐項審查的歷史證據，也不重複 `design_baseline/write_from_use_case_to_architecture.md` 的撰寫規範。
- 原則上於 05 重構完成後建立；若 05 提前發現 01–03 的上游缺漏或矛盾，則提早建立並啟動相應 checklist。

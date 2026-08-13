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
- 已完成：0
- 上游阻塞：0
- 待討論：40
- 目前進度：0 / 40

## A. Common Reuse-assessment Rules

- [ ] 1. Authority, scope, and downstream boundary
  - 完成條件：確認 01–03→04→05 authority、04 可做與禁止的決定，以及上游問題的停止與回退規則。
- [ ] 2. Coverage status and assessment-record format
  - 完成條件：確認每個 SYS 的固定 record，以及 `Fully Covered`、`Partially Covered`、`Not Covered`、`Needs Verification` 與 `Not Applicable` 的使用方式。
- [ ] 3. Exact-version and evidence-source rule
  - 完成條件：定義官方文件、vendor baseline、source、runtime、integration、real-hardware 與 assumption 的證據層級、版本與引用方式。
- [ ] 4. Candidate comparison and minimum-gap rule
  - 完成條件：定義多候選比較、configuration／composition coverage、constraint 與 minimum custom gap 的記錄方式，不提前設計 subsystem internal implementation。
- [ ] 5. Assessment order and per-requirement completion rule
  - 完成條件：確認依成熟方案領域盤點但每個 SYS 獨立定案，以及 requirement record 的 Definition of Done。

## B. Requirement-by-requirement Assessment

### Robot Description

- [ ] 6. SYS-023 Robot Description
  - 完成條件：完成機器人幾何、座標系與關節定義之成熟方案 coverage record。

### Perception and Odometry

- [ ] 7. SYS-003 LiDAR Perception
  - 完成條件：完成 LiDAR 掃描供建圖、定位與導航使用之成熟方案 coverage record。
- [ ] 8. SYS-004 IMU Perception
  - 完成條件：完成 IMU 量測供定位使用之成熟方案 coverage record。
- [ ] 9. SYS-005 System Odometry
  - 完成條件：完成平面里程供定位、建圖與導航使用之成熟方案 coverage record。

### Motion and Drive

- [ ] 10. SYS-022 Base Motion Control
  - 完成條件：完成速度命令、差速輪運動學與底盤移動之成熟方案 coverage record。
- [ ] 11. SYS-026 Base Fault Handling
  - 完成條件：完成通訊、driver alarm、feedback failure、停止嘗試與故障回報之成熟方案 coverage record。
- [ ] 12. SYS-027 Motion-command Timeout
  - 完成條件：完成有效速度命令 timeout 與停止行為之成熟方案 coverage record。
- [ ] 13. SYS-028 Base Motion Limits
  - 完成條件：完成輪速、馬達 RPM 與 operational limits 之成熟方案 coverage record。
- [ ] 14. SYS-029 Base State Feedback
  - 完成條件：完成 measured wheel position／velocity、validity 與禁止 command substitution 之成熟方案 coverage record。
- [ ] 15. SYS-030 Safe Base Enable and Stop
  - 完成條件：完成 enable prerequisites、stop confirmation、driver disable 與 independent safety-action attempts 之成熟方案 coverage record。
- [ ] 16. SYS-031 Base Configuration Validation
  - 完成條件：完成 motor mapping、direction、gear ratio、position scale 與 operational-limit validation 之成熟方案 coverage record。

### Mapping

- [ ] 17. SYS-001 Map Creation
  - 完成條件：完成二維 Occupancy Grid 建立之成熟方案 coverage record。
- [ ] 18. SYS-002 Map Storage
  - 完成條件：完成建圖結果儲存為 Map Package 之成熟方案 coverage record。
- [ ] 19. SYS-006 Continuous Map Update
  - 完成條件：完成有效感知與里程輸入下持續更新 Occupancy Grid 之成熟方案 coverage record。
- [ ] 20. SYS-007 Map Reload
  - 完成條件：完成 Map Package 重載並供定位與導航使用之成熟方案 coverage record。
- [ ] 21. SYS-024 Mapping Result
  - 完成條件：完成 Map Package 可重載成功條件、失敗原因與結果回報之成熟方案 coverage record。

### Target, Resource, and Localization

- [ ] 22. SYS-008 Navigation Target
  - 完成條件：完成 Station 與 Goal Pose target forms 之成熟方案 coverage record。
- [ ] 23. SYS-009 Navigation Target Validation and Resolution
  - 完成條件：完成 target validation、Station resolution、Goal Pose acceptance 與 rejection reason 之成熟方案 coverage record。
- [ ] 24. SYS-010 Map Localization
  - 完成條件：完成 map pose、manual initial pose、localization validity、navigation gate 與 localization-loss behavior 之成熟方案 coverage record。
- [ ] 25. SYS-012 Navigation Resource Validation
  - 完成條件：完成 Map Package、Route Graph、Navigation configuration、Station Catalog 的 existence、validity 與 compatibility coverage record。

### Navigation Execution

- [ ] 26. SYS-011 Path Planning
  - 完成條件：完成 active-stage planning、movement continuity、route-assisted alternatives 與 failure boundary 之成熟方案 coverage record。
- [ ] 27. SYS-014 Obstacle Avoidance
  - 完成條件：完成障礙物資訊、occupied-space avoidance、unsafe-navigation stop 與 failure reporting 之成熟方案 coverage record。
- [ ] 28. SYS-015 Path Tracking
  - 完成條件：完成 active-stage tracking、transition monitoring、route-assisted alternatives 與 evidence-bound acceptance conditions 之成熟方案 coverage record。
- [ ] 29. SYS-016 Goal Completion
  - 完成條件：完成 position、orientation、stopped-state success gate 與 evidence-bound thresholds 之成熟方案 coverage record。
- [ ] 30. SYS-017 Navigation Result
  - 完成條件：完成 success／failure／cancel result 及各 navigation failure boundary differentiation 之成熟方案 coverage record。
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

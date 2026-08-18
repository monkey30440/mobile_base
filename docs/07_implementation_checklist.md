# 07 Implementation Checklist

本清單追蹤 `mobile_base` v0.1 從 [`06_subsystem.md`](./06_subsystem.md) Design Baseline 到實作、漸進驗證與 Feature Freeze 的進度。它不是新的需求或架構來源；若實作發現 01–06 矛盾，必須停止受影響項目並回到最早的權威層修正。

一次只允許一個 `[~]` 項目。每一項只有在對應 artifacts、traceability 與要求的證據都寫入 [`07_implementation.md`](./07_implementation.md) 後才能標記 `[x]`。

## Status

- `[ ]` 待實作：尚未開始，或現有局部 code 尚未達到本項完整完成條件。
- `[~]` 進行中：目前唯一正在實作／驗證的項目。
- `[x]` 已完成：artifact、build/test/evidence 與 07 紀錄均完成。
- `[!]` 上游阻塞：發現 01–06 缺漏、矛盾或未核准決策，停止實作並回退處理。
- `[-]` 延後：已有核准理由與重新啟動條件；不得用來略過 v0.1 requirement。

## Progress

- 總項目：27
- 已完成：9
- 進行中：0
- 待實作：18
- 上游阻塞：0
- 目前進度：9 / 27 (33%)；第 9 項 `S1 Robot Description` 依原始 DoD 完成 Xacro/URDF、joint/frame naming、robot_state_publisher、模型語法、TF tree 與實體幾何量測證據並正式結案 `[x]`；下一步為第 10 項 `S2 LiDAR acquisition and scan baseline`（待實作 `[ ]`）。

---

## A. Implementation Governance and Evidence Rules

- [x] 1. Docker development and validation baseline
  - 完成條件：`Dockerfile` 與 `compose.yaml` 的責任、binary dependencies、workspace mount、host network、NVIDIA runtime、serial passthrough、明確排除項與既有驗證證據已寫入 07。
- [x] 2. External source dependency build closure
  - 完成條件：`rf2o_laser_odometry` 與 `tdk_ros2_imu` 可在目前 container baseline 完成 rosdep、colcon build 並被 ROS 2 找到；相容性修正與證據邊界已記錄。
- [x] 3. Per-item implementation record template
  - 完成條件：後續每項固定記錄 requirement/subsystem trace、artifacts、mature/custom boundary、interfaces/config、failure handling、build/test/hardware evidence、known limits 與 freeze status。
- [x] 4. Verification evidence storage convention
  - 完成條件：確立 command、target、timestamp、版本、原始輸出／log path、PASS/FAIL 與 evidence boundary 的保存規則；禁止只寫口頭「已測過」。
- [x] 5. Build and test command baseline
  - 完成條件：固定 container 內 rosdep、colcon build、package test、result inspection 與 selective rebuild 流程，並確認不依賴未記錄的 running-container 手動修改。
- [x] 6. Runtime and hardware safety preflight
  - 完成條件：在任何輪端輸出前確認 target device identity、M1 設定、E-stop/STO/架車條件、速度／時間上限、watchdog、停止命令及故障後人工復歸流程。

## B. Critical Hardware Vertical Slice

- [x] 7. S7 `M1Driver` transport vertical slice
  - 追溯：S7；GAP-05、GAP-06 的底層依賴；SYS-026、SYS-029、SYS-030。
  - 完成條件：依 06 baseline 實作 libmodbus RTU connection、雙 M1 read/write、timeout/error mapping、enable/disable/stop primitive；先以無運動 read path 與故障注入驗證，再進入受控輸出。
- [x] 8. S7 `M1Hardware` ros2_control integration
  - 追溯：SYS-022、SYS-026、SYS-027、SYS-028、SYS-029、SYS-030；GAP-05、GAP-06。
  - 完成條件：SystemInterface lifecycle、command/state interfaces、真實 wheel feedback validity、禁止 command substitution、diff-drive controller、timeout 與 safe-stop chain 完成 unit/interface/integration/real-hardware evidence。

## C. Subsystem Implementation

- [x] 9. S1 Robot Description
  - 追溯：SYS-023。
  - 完成條件：Xacro/URDF、joint/frame naming、robot_state_publisher、模型語法、TF tree 與實體幾何量測證據符合 06。
- [ ] 10. S2 LiDAR acquisition and scan baseline
  - 追溯：SYS-003。
  - 完成條件：兩具 `sick_scan_xd` source 各自取得有效 LaserScan、frame/QoS/timestamp 可驗證；只有 06 核准的 downstream dependency 才使用 `dual_laser_merger`，不得以 merged output 取代兩個 authoritative raw sources。
- [ ] 11. S2 TDK IMU runtime integration
  - 追溯：SYS-004。
  - 完成條件：現有 `tdk_ros2_imu` parser/node/test 在 target container 重跑通過，`/dev/ttyACM0`、message fields、units、frame、QoS、rate、timestamp、斷線／壞封包與實機靜態／動態量測均有證據。
- [ ] 12. S2 RF2O and selected scan integration
  - 追溯：SYS-003、SYS-005。
  - 完成條件：RF2O 只消費核准的 selected/merged scan，輸出 odometry 的 frame、rate、covariance、TF ownership 與異常行為經整合和實機驗證；不得成為 `odom -> base_footprint` 第二發布者。
- [ ] 13. S3 State Estimation
  - 追溯：SYS-005。
  - 完成條件：EKF 融合 S7 wheel odometry、S2 IMU、S2 RF2O；唯一 `odom -> base_footprint` owner、covariance、input timeout/異常與實機 odometry 表現符合 06。
- [ ] 14. S4 Mapping and MapIO
  - 追溯：SYS-001、SYS-002、SYS-006、SYS-007、SYS-024。
  - 完成條件：Mapping Mode、slam_toolbox、唯一 `map -> odom` ownership、地圖建立／更新／儲存／read-back 與失敗路徑完成整合及實機證據。
- [ ] 15. S5 Localization
  - 追溯：SYS-010。
  - 完成條件：Navigation Mode map load、AMCL、RViz Initial Pose、唯一 `map -> odom` ownership、定位輸出與目標場域誤差／失敗 evidence 符合 06。
- [ ] 16. S6 Target Admission thin gaps
  - 追溯：GAP-01→SYS-008、GAP-02→SYS-009、GAP-03→SYS-032、GAP-04→SYS-033。
  - 完成條件：terminal target form、Goal Pose normalization、Station exact-match resolution、canonical PoseStamped validation 形成單一薄 boundary；invalid target 不下送 Nav2，failure reasons 與 unit/interface tests 完整。
- [ ] 17. S6 Route-assisted Navigation execution
  - 追溯：SYS-011、SYS-013、SYS-014、SYS-015、SYS-016、SYS-017、SYS-018、SYS-019、SYS-020、SYS-021、SYS-025。
  - 完成條件：Nav2 Route Server、Planner、Costmap/Collision Monitor、Controller、StoppedGoalChecker、BT 三階段、native result/cancel 與禁用 free-space fallback 的整合和實機 evidence 完整。

## D. Cross-subsystem Integration Closure

- [ ] 18. TF and frame authority closure
  - 完成條件：S1 static TF、S3 `odom -> base_footprint`、S4/S5 互斥 `map -> odom` 無斷鏈、重複 owner 或 frame mismatch。
- [ ] 19. Perception data-flow closure
  - 完成條件：兩個 raw LiDAR、selected scan、IMU 與 RF2O 的 producer/consumer、QoS、frame、timestamp、rate、freshness 與 failure propagation 可觀察且符合 06。
- [ ] 20. Motion-command and physical-stop closure
  - 完成條件：S6 command→S7 safety gate→diff drive→M1，以及 Task Cancel、Command Timeout、Hardware Safe Stop 三層停止均量測到實體停止結果。
- [ ] 21. Feedback and odometry closure
  - 完成條件：M1 encoder→S7 validity→S3 EKF→S4/S5/S6 的資料鏈、延遲、掉線、禁止假回授與恢復行為完整驗證。
- [ ] 22. Operational-mode and lifecycle closure
  - 完成條件：Mapping/Navigation mode 的啟動順序、lifecycle transitions、互斥 `map -> odom` authority、停機與部分啟動失敗均可重現。

## E. Use-case Verification and Feature Freeze

- [ ] 23. UC-001 Mapping end-to-end acceptance
  - 完成條件：使用者啟動建圖、受控移動、持續更新、停止、儲存及 read-back 的成功與主要失敗流程通過實機驗收。
- [ ] 24. UC-002 Navigation end-to-end acceptance
  - 完成條件：Station/Goal Pose 輸入、admission、localization、First Mile→On Route→Last Mile、障礙處理、停妥成功、失敗與取消流程通過實機驗收。
- [ ] 25. Requirement and custom-gap traceability audit
  - 完成條件：31 個唯一 `SYS-xxx` 與 GAP-01～GAP-06 均有 implementation artifact、test/evidence 與 owner；無遺漏、錯號或未核准新增行為。
- [ ] 26. Reproducibility and clean-environment audit
  - 完成條件：從乾淨 image/workspace 依文件重建、測試與啟動，不依賴未提交檔案、舊 build cache 或 running-container 手動安裝。
- [ ] 27. v0.1 Feature Freeze review
  - 完成條件：UC-001、UC-002、31 個 requirements、6 個 custom gaps 與所有必要實機 evidence 已通過；未完成項有核准的上游變更或明確不屬 v0.1，才能標記 Feature Frozen。

## Per-item Definition of Done

每個 implementation item 只有在下列條件全部成立時才能標記 `[x]`：

- 實作未改寫 01–06 的產品語意、責任邊界或 canonical interfaces。
- 變更前已依 `AGENTS.md` 對所有將修改的 function/class/method 完成 GitNexus upstream impact analysis；HIGH/CRITICAL 已先警告並取得處理決定。
- Artifact path、package/version、parameters 與 mature/custom boundary 已記錄。
- Build 與適合該層級的 unit/interface/integration tests 通過，原始結果可追溯。
- 06 要求 real-hardware validation 時，已在 target Jetson/AMR 上取得證據；模擬或 topic 存在不能代替實機結果。
- Failure、timeout、cancel、device loss 或 invalid input 等適用負向路徑已驗證。
- `07_implementation.md` 已更新目前狀態、證據邊界、known limits 與下一個 dependency。
- 若要提交，已執行 `gitnexus_detect_changes()`、`git diff --check` 與相關測試，確認影響範圍符合預期。

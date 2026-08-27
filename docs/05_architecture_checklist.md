> [!WARNING]
> **HISTORICAL / NON-AUTHORITATIVE**
>
> This document is retained for historical traceability only. It does not define the current system architecture, requirements, operational procedure, or verification authority. Use `docs/README.md` to locate the current canonical documentation.

# 05 Architecture Checklist

本清單用於追蹤並確認 `mobile_base` v0.1 系統架構（`05_architecture.md`）之決策完整性、跨系統契約閉合性與需求追溯性。

## Progress

- 總項目：25
- 已完成：25
- 待討論：0
- 目前進度：25 / 25

---

## A. 架構邊界與基本原則 (Architecture Scope & Baseline)

- [x] 1. 架構職權與範圍界定 (Authority & Boundaries)
  - 完成條件：確立 05 僅定義責任領域、成熟方案配置、跨系統資料／控制流、TF 擁有權與安全邊界；禁止過早決定 class/function、node 名稱、topic/action schema、QoS 與演算法細節（保留至 06）。
- [x] 2. 上游基準與可行性證據約束 (Normative Inputs & Evidence Traceability)
  - 完成條件：確認以 `01_use_cases.md`、`02_capabilities.md`、`03_requirements.md` 為唯一 normative 基準；以 `04_reuse_assessment.md` 為 exact-version 方案配置依據，不發明上游未定義需求。

---

## B. 7 大 Subsystem 劃分與責任定義 (System Decomposition)

- [x] 3. S1 Robot Description
  - 完成條件：定義機器人靜態幾何、關節與固定 TF 關係的單一擁有權；明確排除 runtime pose、odom TF 與動態運動狀態。
- [x] 4. S2 Perception
  - 完成條件：定義 LiDAR（LaserScan）與 IMU 標準感測資料的取得與提供責任；明確排除地圖計算、位姿推算與路徑決策責任。
- [x] 5. S3 State Estimation
  - 完成條件：定義前 LiDAR + encoder wheel prior → Kinematic-ICP → `/lidar_odometry` → EKF + IMU yaw rate 的平面里程估測，以及 `odom → base_footprint` TF 唯一擁有權；明確與 Localization 分離。
- [x] 6. S4 Mapping
  - 完成條件：定義二維 Occupancy Grid 之建立、即時更新、Map Package 儲存、讀回驗證與載入責任；明確排除導航路網與站點管理。
- [x] 7. S5 Localization
  - 完成條件：定義基於已載入地圖、感知與里程估測機器人位姿，以及發布權威 `map → odom` TF 的責任；明確排除建圖與導航決策。
- [x] 8. S6 Navigation
  - 完成條件：定義接收外部目標、正規化／解析、目標驗證、路網導航策略、階段執行（First Mile / On Route / Last Mile）、到站判定與結果回報的完整任務擁有權。
- [x] 9. S7 Base Control
  - 完成條件：定義差速底盤速度控制執行、建圖期間外部手動速度命令執行（SYS-034）、命令逾時保護、運動極限約束、馬達回授有效性驗證與硬體安全啟停／故障處理責任。

---

## C. 場域資源與操作模式 (Resources & Operational Modes)

- [x] 10. 場域資源模型收斂 (Navigation Resources)
  - 完成條件：確立場域資源僅包含人工建立之 `Map Package`、`Route Graph` 與 `Station Catalog`；移除產品層 `Navigation Configuration`（回歸各模組部署參數）。
- [x] 11. 資源載入擁有權 (Resource Loading Responsibility)
  - 完成條件：明確 Map Package 由 S4 Mapping 載入；Route Graph 與 Station Catalog（條件式）由 S6 Navigation 載入；不設立額外 Resource Manager。
- [x] 12. 互斥操作模式 (Operational Modes & Mode Boundaries)
  - 完成條件：確立 Mapping Mode（SLAM 擁有 `map → odom`、teleop 為唯一運動命令來源）與 Navigation Mode（Localization 擁有 `map → odom`、S6 為唯一運動命令來源）互斥；共用底層感知、狀態估測與底盤控制。

---

## D. 跨系統資料流、控制流與核心契約 (Cross-Subsystem Contracts)

- [x] 13. 座標框架與 TF Tree 唯一權威 (TF Authority Contract)
  - 完成條件：確認 `map → odom`（Localization / 建圖時 Mapping）、`odom → base_footprint`（State Estimation）、`base_footprint → base_link → sensors`（Robot Description）無重疊發布者。
- [x] 14. 速度命令與執行權限鏈 (Velocity Command Chain Contract)
  - 完成條件：Navigation（導航模式）或外部 teleop（建圖模式）僅提出期望運動意圖（`TwistStamped`）；Base Control 擁有最終安全執行、否決權（Safety Gate）、運動極限定界與逾時保護；各模式單一來源故無需 command mux。
- [x] 15. 系統停止與安全語意分離 (Stop & Safety Semantics Contract)
  - 完成條件：清楚分離 Navigation Task Stop（S6 任務完成/終止與零意圖）、Manual Movement Stop（外部 teleop 主動停止發布零速）、Command Timeout（S7 逾時保護停止）與 Hardware Safe Stop（S7 硬體安全狀態與馬達停用）。
- [x] 16. 環境障礙物資訊邊界 (Obstacle Information Contract)
  - 完成條件：Perception 負責提供標準量測；Nav2 Costmaps / Collision Handling 負責障礙物解讀與代價計算；Navigation 擁有避障行為責任。

---

## E. 導航編排與 MVP 決策 (Navigation Orchestration & MVP Strategy)

- [x] 17. 三階段導航編排 (Stage Execution & Transition)
  - 完成條件：定義 First Mile → On Route → Last Mile → Goal Completion 責任鏈；規範零長度連接階段之合法略過行為。
- [x] 18. MVP 重新選路策略 (MVP Route Reselection)
  - 完成條件：路網受阻或階段失敗時，以當前最新位姿與原目標重新執行既有路網選路；不發明複雜重路由引擎。
- [x] 19. Fallback 邊界與終止語意 (Reserved Fallback & Termination Boundary)
  - 完成條件：保留 4 種 Fallback eligibility 語意作為未來擴充點；v0.1 在路網用盡時直接終止並回報 `NO_ROUTE_ASSISTED_SOLUTION`，不執行 free-space 導航。
- [x] 20. 到站判定與結果統一收斂 (Goal Completion & Unified Navigation Result)
  - 完成條件：僅在 Canonical Goal Pose 之位置、朝向與底盤停止皆滿足時判定 Success；統一收斂為 Success、Failure、Canceled 三種結果。

---

## F. 6 個 Custom Gaps 與需求閉合稽核 (Gaps Placement & Traceability Audit)

- [x] 21. Navigation Target Gaps (SYS-008, SYS-009, SYS-032, SYS-033) 落位
  - 完成條件：4 個目標辨識、正規化、站點解析與目標驗證薄轉接層明確配置於 S6 Navigation Target Admission。
- [x] 22. Base Control Gaps (SYS-029, SYS-030) 落位
  - 完成條件：馬達回授有效性檢查（禁止以命令值冒充）與安全啟停邏輯明確配置於 S7 Base Control。
- [x] 23. 32 項系統需求完整覆蓋 (Requirement Ownership Allocation)
  - 完成條件：逐項審核 SYS-001 ～ SYS-034（共 32 項，排除未啟用編號），確認 100% 具有明確且唯一的 Subsystem Owner。
- [x] 24. 成熟方案配置審核 (Mature Solution Placement Audit)
  - 完成條件：確認 Nav2、ros2_control、slam_toolbox、AMCL、robot_localization、teleop_twist_keyboard 等成熟元件正確落位於各責任領域，非包裝為混淆子系統。
- [x] 25. 架構簡化與無洩漏審核 (Architecture Simplification & Non-leakage Audit)
  - 完成條件：確認 7 個 Subsystem 無冗餘切分或不當合併；確認未引入 06 Subsystem Detailed Design 細節。

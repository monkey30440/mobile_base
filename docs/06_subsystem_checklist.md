# 06 Subsystem Design Checklist

本清單用於追蹤 `mobile_base` v0.1 子系統詳細設計（`06_subsystem.md`）的討論、重構與跨系統整合稽核進度。

`05_architecture.md` 為本設計的唯一 Normative Design Input。

## Status

- `[ ]` 待討論：尚未形成或核准設計。
- `[~]` 討論中：目前正在處理的項目。
- `[x]` 已完成：內容已討論、核准、寫入並完成檢查。
- `[!]` 上游阻塞：發現 01–05 缺漏或矛盾，必須先回退修正上游。

---

## Progress

- 總項目：22
- 已完成：22
- 討論中：0
- 待討論：0
- 目前進度：22 / 22 (100%)

---

## A. 通用設計規則與標準模板 (Common Design Rules & Templates)

- [x] 1. 架構職權與下游邊界 (Authority & Downstream Boundary)
  - 完成條件：確立 05 $\rightarrow$ 06 $\rightarrow$ Implementation $\rightarrow$ Verification 單向權威鏈；06 定義 Node、Component、Interface、QoS、Parameter 與 Failure 規格，但不展開 function/class 內部程式碼與底層暫存器協議。
- [x] 2. 統一子系統 6 大章節模板 (Standard 6-Part Specification Template)
  - 完成條件：確認每個 Subsystem 必須包含 Purpose & Boundary、Internal Components、ROS 2 Interfaces、Parameters & Configurations、Failure & Diagnostics、Verification Obligations。
- [x] 3. 介面命名、QoS 與生命週期約定 (Interface, QoS & Lifecycle Conventions)
  - 完成條件：規範標準 Topic/Service/Action 命名慣例、SensorData vs Reliable QoS 使用準則、以及 Nav2 / ros2_control 之 Lifecycle 狀態轉換。
- [x] 4. 驗證分級模型 (Verification Model)
  - 完成條件：區分單元測試 (Unit Test)、節點介面測試 (Interface Test)、子系統整合測試 (Integration Test) 與實機驗收 (Real-hardware Validation)。

---

## B. 7 大 Subsystem 細部設計 (依依賴鏈順序展開)

- [x] 5. S1 Robot Description Subsystem Design
  - 完成條件：定義 URDF/Xacro 結構、關節名稱（`driving_wheel_joint_L`, `driving_wheel_joint_R`）、`base_footprint` $\rightarrow$ `base_link` $\rightarrow$ `sensor_links` 靜態 TF、`robot_state_publisher` 節點配置與幾何驗證（承接 SYS-023）。
- [x] 6. S2 Perception Subsystem Design
  - 完成條件：定義 LiDAR 驅動節點（發布 `sensor_msgs/msg/LaserScan`，`frame_id: base_lidar_link_FL/BR`）、`dual_laser_merger` 360° 融合節點（發布 `/scan`，`frame_id: base_link`）、IMU 驅動節點（發布 `sensor_msgs/msg/Imu`，`frame_id: base_imu_link`）、QoS 與資料有效性檢核（承接 SYS-003, SYS-004）。
- [x] 7. S7 Base Control Subsystem Design
  - 完成條件：定義 `ros2_control` 架構、`diff_drive_controller`（綁定 S1 關節名稱、`TwistStamped` 介面、速度極限與逾時保護）、Mapping 外部 `teleop_twist_keyboard` 配置與 CLI 規格、M1 專用 Hardware Interface、GAP-05 回授有效性檢查（禁止冒充）與 GAP-06 安全啟停邏輯（承接 SYS-022, SYS-026, SYS-027, SYS-028, SYS-029, SYS-030, SYS-034）。
- [x] 8. S3 State Estimation Subsystem Design
  - 完成條件：定義 Kinematic-ICP（前 LiDAR + S7 wheel odometry prior）與 `robot_localization` EKF（`/lidar_odometry` x/y/yaw + IMU yaw rate）、`odom → base_footprint` 動態 TF 發布權限、協方差矩陣配置與異常容錯（承接 SYS-005）。
- [x] 9. S4 Mapping Subsystem Design
  - 完成條件：定義 `slam_toolbox` Online Async SLAM 節點（訂閱 S2 LaserScan + S3 Odom）、Mapping Mode 下 `map → odom` TF 發布、`nav2_map_server` MapIO 服務（儲存、讀回驗證、載入地圖）（承接 SYS-001, SYS-002, SYS-006, SYS-007, SYS-024）。
- [x] 10. S5 Localization Subsystem Design
  - 完成條件：定義 `nav2_amcl` 節點（訂閱已載入地圖、S2 LaserScan、S3 Odom）、Navigation Mode 下 `map → odom` 唯一發布權限、接收 RViz Initial Pose 初始化（承接 SYS-010）。
- [x] 11. S6 Navigation Subsystem Design
  - 完成條件：定義 Target Admission 模組（GAP-01→SYS-008 目標識別、GAP-02→SYS-009 Goal Pose 正規化、GAP-03→SYS-032 Station 解析、GAP-04→SYS-033 Canonical Goal 驗證）、Nav2 Route Server、BT Navigator（三階段編排 SYS-018 First Mile／SYS-019 On Route／SYS-020 Last Mile、SYS-013 route-preferred 重選路與 SYS-021 Fallback 終止）、Planner（SYS-011）、Costmap（SYS-014）、Controller（SYS-015）、StoppedGoalChecker（SYS-016）、原生結果收斂（SYS-017）與導航取消（SYS-025）。

---

## C. 跨子系統整合鏈稽核 (Cross-Subsystem Integration Audit)

- [x] 12. 座標框架與 TF Tree 鏈稽核 (TF Tree Chain Audit)
  - 完成條件：確認靜態 TF（S1）與動態 TF（S3 的 `odom→base_footprint`、S5/S4 的 `map→odom`）無任何多重發布或斷鏈。
- [x] 13. 速度命令與安全防護鏈稽核 (Velocity Command & Safety Chain Audit)
  - 完成條件：S6 期望命令或 Mapping 外部 Teleop $\rightarrow$ S7 Safety Gate $\rightarrow$ S7 Diff-Drive $\rightarrow$ M1 馬達驅動之命令鏈完全閉合，格式統一為 `TwistStamped`。
- [x] 14. 狀態回授與里程融合鏈稽核 (Wheel Feedback & Odometry Chain Audit)
  - 完成條件：M1 編碼器 $\rightarrow$ S7 有效性檢查 $\rightarrow$ S3 EKF 融合 $\rightarrow$ S4/S5/S6 之資料鏈完全閉合。
- [x] 15. 感知資料鏈稽核 (Perception Data Chain Audit)
  - 完成條件：S2 LiDAR/IMU $\rightarrow$ S3, S4, S5, S6 之 Topic、Message Type、Frame ID 與 QoS 完全匹配。
- [x] 16. 建圖端到端流程稽核 (Mapping Integrated Flow Audit - UC-001)
  - 完成條件：手動遙控巡覽移動、即時建圖、地圖儲存與讀回驗證流程閉合，停止鍵與閒置逾時不中斷 Mapping session。
- [x] 17. 導航端到端流程稽核 (Navigation Integrated Flow Audit - UC-002)
  - 完成條件：目標接收 $\rightarrow$ 驗證 $\rightarrow$ 三階段移動 $\rightarrow$ 停妥到站之端到端流程閉合。
- [x] 18. 系統停止與故障安全處置稽核 (Stop & Safety Audit)
  - 完成條件：Navigation Task Stop、Manual Movement Stop、Command Timeout、Hardware Safe Stop 在各 Subsystem 內部機制對應無誤。
- [x] 19. 操作模式與生命週期啟動依賴稽核 (Operational Modes & Lifecycle Audit)
  - 完成條件：Mapping Mode 與 Navigation Mode 互斥啟動依賴與命令單一性保證（無需 command mux）。

---

## D. 最終一致性與基線審查 (Final Baseline Audit)

- [x] 20. 05 $\rightarrow$ 06 需求與客製缺口完整覆蓋 (Traceability Completeness)
  - 完成條件：32 項 SYS 需求（SYS-001 ～ SYS-034）與 6 個 Custom Gaps 均在 06 有具體 Node / Component 承接。
- [x] 21. 無過度設計與無未授權實作洩漏審查 (No Overdesign & Leakage Audit)
  - 完成條件：無多餘未核准框架，無實作層私自新增之行為。
- [x] 22. `06_subsystem.md` 最終定案與核准 (Final Approval)
  - 完成條件：全文件一致性審核通過，正式定案為下游實作依據。

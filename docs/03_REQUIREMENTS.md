# System Requirements

本文件定義 `mobile_base` v0.1 之可觀察功能需求、安全需求與操作限制。

Requirement 描述系統必須滿足之可觀察行為、限制與驗證邊界，不描述系統實作方式。

---

# UC-001 建立地圖

## SYS-001 建立地圖

系統應建立可供定位與導航使用之二維 Occupancy Grid 地圖；建圖功能無法完成初始化並進入可處理建圖資料之狀態時，系統應回報失敗及原因。

---

## SYS-002 儲存地圖

系統應將建圖結果儲存為 Map Package；無法儲存 Map Package 時，系統應回報失敗及原因。

---

## SYS-006 持續更新地圖

建圖進行期間，系統應於取得新的有效感知與里程資料後更新目前二維 Occupancy Grid；資料暫時不可用時，系統應保留目前地圖並等待後續有效資料，直到使用者完成或終止建圖。

---

## SYS-007 載入地圖

系統應於 Navigation Mode 啟動期間載入所選定之 Map Package，並提供其中的二維 Occupancy Grid 給地圖定位與導航功能使用；Map Package 無法載入時，系統不得進入 navigation-ready 狀態，並應回報原因。

---

## SYS-024 Map Package Read-back

系統應於 Map Package 儲存後，確認其中的地圖可重新解析為二維 Occupancy Grid；無法解析時，系統應依標準解析結果回報失敗及原因。

---

## SYS-034 手動移動控制

建圖期間，系統應接受使用者提供之手動速度命令以控制 AMR 移動巡覽環境；該移動控制應遵守既有底盤運動控制、運動限制、命令逾時與安全啟停需求。未提供手動速度命令或命令停止時，建圖程序不應因此終止。

---

# UC-002 導航至指定目標

## SYS-008 Navigation Target

系統應支援以下 Navigation Target：

- Station
- Goal Pose

---

## SYS-009 Goal Pose Normalization

系統應接受使用者透過終端提交以公尺表示之絕對 `x`、`y`，以及以度表示之 `yaw-deg` Goal Pose，並將其正規化為目前導航全域座標框架中的 canonical `geometry_msgs/msg/PoseStamped`；系統應保留其絕對位置與方向語意，將 `yaw-deg` 轉換為 quaternion，並依操作規則設定 frame 與 timestamp。必要欄位缺失或無法解析時，系統應拒絕該目標並回報原因。

---

## SYS-032 Station Target Resolution

系統應使用目前場域之 Station Catalog，將使用者提交的 Station ID 解析為該 Station 預先定義之 canonical `geometry_msgs/msg/PoseStamped`；Station ID 為空、找不到對應 Station 或無法解析時，系統應拒絕該目標並回報原因。

---

## SYS-033 Canonical Goal Pose Validation

系統應於導航開始前驗證 canonical `geometry_msgs/msg/PoseStamped`。其位置與方向數值應為有限值、座標框架不得為空且應可轉換至目前導航使用之全域座標框架、方向 quaternion 應有效；驗證失敗時，系統應拒絕該目標並回報原因。只有通過驗證的 canonical `PoseStamped` 才可提供給後續導航流程。

---

## SYS-010 地圖定位

系統應根據已載入地圖與可用的感知及里程資料估測 AMR 位姿，並提供標準定位 pose 與 `map → odom` transform，供導航功能使用。當 AMR 開機位置無法可靠得知時，系統應接受使用者提供目前地圖中的 approximate initial pose，作為定位初始化輸入。

---

## SYS-011 路徑規劃

系統應使用目前位姿與 active navigation stage 的目標，透過 Navigation2 產生有效且非空的路徑。無法產生路徑時，系統不得開始該 stage 的路徑追蹤，並應回報 Navigation2 原生規劃失敗結果。

---

## SYS-013 Route-preferred Navigation Strategy

系統應根據目前位姿、Canonical Goal Pose 與有效 Route Graph 建立可安全執行的 route-assisted movement，並優先使用適用的 Route Graph 範圍。存在有效且可安全執行的 route-assisted solution 時，系統不得選擇完整 free-space movement。

---

## SYS-014 障礙物避讓

導航期間，系統應使用有效之環境障礙物資訊，避免規劃或執行穿越已判定占用區域之運動；無法維持可安全執行之導航時，系統應嘗試使底盤停止並回報失敗。

---

## SYS-015 路徑追蹤

系統應透過 Navigation2 `FollowPath` 控制 AMR 追蹤目前 active navigation stage 的有效路徑，並使用設定的 controller 與 progress checker 判定能否繼續追蹤。無法繼續追蹤時，系統應停止該 stage 的路徑追蹤、嘗試使底盤停止，並回報 Navigation2 原生追蹤失敗結果。追蹤接受條件應經整合及實機驗證。

---

## SYS-016 到站判定

系統僅應在 AMR 目前位姿符合解析後 Navigation Target 所設定之位置與朝向接受條件，且底盤已停止時，判定導航成功。位置、朝向與停止判定門檻應經整合及實機驗證。

---

## SYS-017 導航結果

系統應透過 Navigation2 原生導航結果回報導航成功、失敗或取消；導航失敗時應回報可取得的 Navigation2 原生失敗結果。

---

## SYS-018 First Mile

目前位姿不在選定 route entry 時，系統應規劃並執行由目前位姿至該 entry 的安全連接；目前位姿已位於適用的 route entry 時，First Mile 應視為不需要執行，不得因此判定導航失敗。

---

## SYS-019 On Route Navigation

系統應沿選定 Route Graph route 由 route entry 移動至 route exit，並遵守 Route Graph 所定義的 connectivity、direction 與 availability constraints。

---

## SYS-020 Last Mile

選定 route exit 未直接到達 Canonical Goal Pose 時，系統應規劃並執行由該 exit 至 Canonical Goal Pose 的安全連接；Canonical Goal Pose 已位於適用的 route exit 時，Last Mile 應視為不需要執行，不得因此判定導航失敗。

---

## SYS-021 Reserved Free-space Fallback Boundary

系統應保留下列 Free-space Fallback eligibility，以供後續版本擴充：

- Current Pose 無法連接任何可用 route entry。
- Active、valid Route Graph 無法提供通往 Canonical Goal Pose 方向的可用 route。
- On Route movement 因目前環境阻塞而無法維持，且重新選擇 Route Graph route 仍失敗。
- 所有可用 route-assisted candidates 均無法由 route exit 透過 Last Mile 安全連接 Canonical Goal Pose。

v0.1 不得執行 Free-space Fallback。符合上述任一 eligibility 且已無可用 route-assisted solution 時，系統應終止導航、嘗試使底盤停止，並回報 Free-space Fallback unavailable。Navigation Resource、Navigation Target 或 localization 的缺失、無效或不相容仍屬其各自 failure boundary，不構成 fallback eligibility。

---

## SYS-025 導航取消

系統應接受使用者對進行中導航任務提出之取消要求，終止該導航任務，並回報取消結果。

---

## SYS-044 AprilTag 視覺停靠 / Direct AprilTag Docking

Navigation Mode 應提供基於視覺標記之 AprilTag Direct Docking 能力。

系統應提供 `/apriltag_dock`（`std_srvs/srv/Trigger`）服務作為單次停靠之觸發介面。外部視覺感知系統（Upper Body）應提供標記相對於基座之位姿 `/detected_dock_pose`（`geometry_msgs/msg/PoseStamped`，`frame_id: "base_link"`），其中 position 與 orientation 均應有效。

底盤導航系統（Lower Body）應接收該標記位姿，透過停靠外掛設定之外參轉換計算目標停靠位姿（使 AMR 最終停於標記前約 70 cm，其實體轉換符號與旋轉偏移待實機標定驗證），並直接執行閉迴路停靠控制，不執行 `NavigateToPose` 預備站點導航。

停靠運動期間發布之速度命令應遵守 S7 既有底盤運動限制（SYS-028）、命令逾時停止（SYS-027）與時間戳格式（`TwistStamped`），並使用既有 Local Costmap 進行障礙物防撞判定。當視覺感知逾時、停靠控制逾時或 Nav2 停靠失敗時，系統應終止該次停靠、嘗試使底盤停止並回報失敗結果。

---

# UC-003 觀察與診斷 AMR 運行

## SYS-035 AMR 運行資訊觀察

系統應提供主要 AMR 與 ROS Runtime Information，供 Actor 查看及人工診斷；可提供的資訊應涵蓋與 Perception、State Estimation / Localization、Mapping / Navigation、Control、Hardware Communication 及 Host / Runtime 相關的選定運行資訊。缺少任一資訊時，系統不得據此推論相關 subsystem 正常。

---

## SYS-036 Logs 與運行事件歷史

系統應將 AMR 產生之選定診斷 Logs 與運行 Events 傳送至 Server；Server 應保存所收到的 Logs 與 Events，並支援依基本時間範圍及來源查詢。

---

## SYS-037 關鍵時間序列 Telemetry

系統應將選定的關鍵時間序列 Telemetry 由 AMR 傳送至 Server；Server 應保存所收到的關鍵 Telemetry，並支援依時間範圍查詢。Telemetry profile 由後續設計與實作配置決定，本需求不要求保存所有 ROS Topics 或完整高頻 Raw Payload。

---

## SYS-038 基本時間關聯

系統應為傳送至 Server 的 Logs、Events 與關鍵 Telemetry 保留可用 timestamp 及 source identity；Server 應支援 Actor 依共同時間範圍進行基本關聯。

---

## SYS-042 Observability Failure Isolation

Observability Component Failure、Network Unavailable 或 Server Unavailable 不得成為 Navigation、Localization、Control 或 Safety 運行的必要依賴。AMR 端 Observability Buffer 應為 bounded；Buffer 容量耗盡時，系統應丟棄最舊的 Observability Data、保留較新的 Observability Data，並維持既有 AMR 核心功能運行。

---

# Shared Requirements

## SYS-003 LiDAR 感知

系統應提供 LiDAR 掃描資料供建圖、定位與導航使用。

---

## SYS-004 IMU 感知

系統應提供 IMU 量測資料供定位使用。

---

## SYS-005 系統里程

系統應以實體前 LiDAR `/scan_front` 與 encoder wheel odometry `/diff_drive_controller/odom` 供 Kinematic-ICP 產生 `/lidar_odometry`，再由 EKF 融合其平面位姿（x、y、yaw）與 `/imu/data_raw` yaw rate，產生可供定位、建圖與導航使用之 `/odometry/filtered`，並由 EKF 唯一發布 `odom → base_footprint`；輸入異常或逾時時，系統得依各成熟方案的原生行為處理有效量測或 prediction。

---

## SYS-022 底盤運動控制

系統應接收底盤速度命令，並依差速輪運動學控制底盤完成移動。

---

## SYS-023 機器人描述

系統應提供機器人幾何、座標系與關節定義，供感知、定位、建圖與導航使用。

---

## SYS-026 底盤故障處理

當底盤 hardware interface 回傳 `ERROR` 時，系統應停止使用該硬體介面的 controller，並使其錯誤狀態可被觀察。

---

## SYS-027 運動命令逾時

底盤執行運動期間，若系統未在設定之逾時時間內收到有效的新速度命令，應使底盤停止；逾時值與停止行為應經整合及實機驗證。

---

## SYS-028 底盤運動限制

系統應將 AMR 的直線與旋轉速度，以及相應的加速與減速，限制於設定之 operational limits；限制值應依操作需求選定，並於部署前完成整合及實機驗證。

---

## SYS-029 底盤狀態回授

系統應提供由馬達驅動器有效回授所取得之左右輪位置與速度狀態，供里程估測、控制與診斷使用；無有效回授時，系統不得以命令值取代量測狀態，並應將狀態視為不可用或故障。

---

## SYS-030 底盤安全啟停

系統僅應在底盤通訊正常、無馬達驅動器警報、輪端為停止狀態且驅動器已確認可運動後接受非零運動命令。底盤停用或系統關閉時，系統應嘗試使底盤停止、確認停止狀態並停用馬達驅動；任一安全動作失敗不得阻止其餘安全動作之嘗試。狀態轉換等待時間與停止確認條件應經實機驗證。

---

## Traceability

| Requirement | Use Case | Capability |
|---|---|---|
| SYS-001 | UC-001 | CAP-001 |
| SYS-002 | UC-001 | CAP-001 |
| SYS-003 | UC-001 | CAP-001 |
| SYS-004 | UC-001 | CAP-001 |
| SYS-005 | UC-001 | CAP-001 |
| SYS-006 | UC-001 | CAP-001 |
| SYS-007 | UC-001 | CAP-001 |
| SYS-022 | UC-001 | CAP-001 |
| SYS-026 | UC-001 | CAP-001 |
| SYS-027 | UC-001 | CAP-001 |
| SYS-028 | UC-001 | CAP-001 |
| SYS-029 | UC-001 | CAP-001 |
| SYS-030 | UC-001 | CAP-001 |
| SYS-023 | UC-001 | CAP-001 |
| SYS-024 | UC-001 | CAP-001 |
| SYS-034 | UC-001 | CAP-001 |
| SYS-008 | UC-002 | CAP-002 |
| SYS-009 | UC-002 | CAP-002 |
| SYS-032 | UC-002 | CAP-002 |
| SYS-033 | UC-002 | CAP-002 |
| SYS-010 | UC-002 | CAP-002 |
| SYS-011 | UC-002 | CAP-002 |
| SYS-013 | UC-002 | CAP-002 |
| SYS-014 | UC-002 | CAP-002 |
| SYS-015 | UC-002 | CAP-002 |
| SYS-016 | UC-002 | CAP-002 |
| SYS-017 | UC-002 | CAP-002 |
| SYS-018 | UC-002 | CAP-002 |
| SYS-019 | UC-002 | CAP-002 |
| SYS-020 | UC-002 | CAP-002 |
| SYS-021 | UC-002 | CAP-002 |
| SYS-025 | UC-002 | CAP-002 |
| SYS-044 | UC-002 | CAP-002 |
| SYS-003 | UC-002 | CAP-002 |
| SYS-004 | UC-002 | CAP-002 |
| SYS-005 | UC-002 | CAP-002 |
| SYS-022 | UC-002 | CAP-002 |
| SYS-023 | UC-002 | CAP-002 |
| SYS-026 | UC-002 | CAP-002 |
| SYS-027 | UC-002 | CAP-002 |
| SYS-028 | UC-002 | CAP-002 |
| SYS-029 | UC-002 | CAP-002 |
| SYS-030 | UC-002 | CAP-002 |
| SYS-035 | UC-003 | CAP-003 |
| SYS-036 | UC-003 | CAP-003 |
| SYS-037 | UC-003 | CAP-003 |
| SYS-038 | UC-003 | CAP-003 |
| SYS-042 | UC-003 | CAP-003 |

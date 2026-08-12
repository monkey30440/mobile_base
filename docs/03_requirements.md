# System Requirements

本文件定義 `mobile_base` v0.1 之可觀察功能需求、安全需求與操作限制。

Requirement 描述系統必須滿足之可觀察行為、限制與驗證邊界，不描述系統實作方式。

---

# UC-001 建立地圖

## SYS-001 建立地圖

系統應建立可供定位與導航使用之二維 Occupancy Grid 地圖。

---

## SYS-002 儲存地圖

系統應儲存建圖結果為 Map Package。

---

## SYS-006 持續更新地圖

建圖進行期間，系統應於取得新的有效感知與里程資料後更新目前二維 Occupancy Grid，直到建圖完成或終止。

---

## SYS-007 載入地圖

系統應能重新載入已儲存之 Map Package，並使其中的地圖可供定位與導航使用。

---

## SYS-024 建圖結果回報

系統應於成功建立並儲存可重新載入之 Map Package 時回報成功；無法開始建圖、無法繼續建圖或無法儲存 Map Package 時，應回報失敗及原因。

---

# UC-002 導航至指定目標

## SYS-008 Navigation Target

系統應支援以下 Navigation Target：

- Station
- Goal Pose

---

## SYS-009 Navigation Target 驗證與解析

系統應驗證使用者提交之 Navigation Target。有效 Station ID 應解析為其預先定義之導航目標；有效 Goal Pose 應直接作為導航目標；無效 Navigation Target 應拒絕並回報原因。

---

## SYS-010 地圖定位

系統應根據已載入地圖估測 AMR 位姿並提供定位有效狀態。當 AMR 開機位置無法由系統可靠得知時，系統應接受使用者提供目前地圖中的 approximate initial pose，作為定位初始化輸入。提供 initial pose 或定位 process active 不得視為定位已有效；無有效定位時，系統不得接受或開始導航。導航期間定位失效時，系統應終止導航、嘗試使底盤停止並回報失敗。

---

## SYS-011 路徑規劃

系統應為目前 active navigation stage 規劃可安全執行的有效路徑，並維持由目前位姿至 Canonical Goal Pose 的完整 movement continuity。無法產生或維持目前 stage 的有效路徑時，系統不得開始或繼續該 stage，並應先用盡可用的 route-assisted alternatives；無可用策略時應嘗試使底盤停止並回報失敗，符合 SYS-021 eligibility 時應將原因辨識為 Free-space Fallback unavailable。

---

## SYS-012 Navigation Resource Validation

系統開始導航前，應驗證目前 Map Package、Route Graph、Navigation configuration，以及 Station Target 所需的 Station Catalog 均存在、有效且彼此相容。任一必要資源缺失、無效或不相容時，系統不得開始導航，應回報原因，且不得將此情況視為 free-space fallback。

---

## SYS-013 Route-preferred Navigation Strategy

系統應根據目前位姿、Canonical Goal Pose 與有效 Route Graph 建立可安全執行的 route-assisted movement，並優先使用適用的 Route Graph 範圍。存在有效且可安全執行的 route-assisted solution 時，系統不得選擇完整 free-space movement。

---

## SYS-014 障礙物避讓

導航期間，系統應使用有效之環境障礙物資訊，避免規劃或執行穿越已判定占用區域之運動；無法維持可安全執行之導航時，系統應嘗試使底盤停止並回報失敗。

---

## SYS-015 路徑追蹤

系統應控制 AMR 追蹤目前 active navigation stage 的有效路徑，並監控 path tracking 與 stage transition；無法在設定之接受條件內繼續追蹤或安全完成 stage transition 時，系統應先用盡可用的 route-assisted alternatives；無可用策略時應嘗試使底盤停止並回報失敗，符合 SYS-021 eligibility 時應將原因辨識為 Free-space Fallback unavailable。路徑偏差、transition 與失效判定條件應經整合及實機驗證。

---

## SYS-016 到站判定

系統僅應在 AMR 目前位姿符合解析後 Navigation Target 所設定之位置與朝向接受條件，且底盤已停止時，判定導航成功。位置、朝向與停止判定門檻應經整合及實機驗證。

---

## SYS-017 導航結果

系統應回報導航成功、失敗或取消；導航失敗時應回報原因，並應能區分 Navigation Resource Validation、First Mile、On Route、Last Mile、Free-space Fallback unavailable，以及其他 navigation execution failure boundary。

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

v0.1 不得執行 Free-space Fallback。符合上述任一 eligibility 且已無可用 route-assisted solution 時，系統應終止導航、嘗試使底盤停止，並回報 Free-space Fallback unavailable。Navigation Resource、Navigation Target、Navigation Configuration 或 localization 的缺失、無效或不相容仍屬其各自 failure boundary，不構成 fallback eligibility。

---

## SYS-025 導航取消

系統應接受使用者對進行中導航任務提出之取消要求，終止該導航任務，並回報取消結果。

---

# Shared Requirements

## SYS-003 LiDAR 感知

系統應提供 LiDAR 掃描資料供建圖、定位與導航使用。

---

## SYS-004 IMU 感知

系統應提供 IMU 量測資料供定位使用。

---

## SYS-005 系統里程

系統應提供可供定位、建圖與導航使用之平面里程資訊。

---

## SYS-022 底盤運動控制

系統應接收底盤速度命令，並依差速輪運動學控制底盤完成移動。

---

## SYS-023 機器人描述

系統應提供機器人幾何、座標系與關節定義，供感知、定位、建圖與導航使用。

---

## SYS-026 底盤故障處理

系統偵測到底盤通訊失敗、馬達驅動器警報或無效／缺失之底盤回授時，應停止接受持續運動輸出、嘗試使底盤停止，並回報故障；實際停止結果與復原行為應經實機驗證。

---

## SYS-027 運動命令逾時

底盤執行運動期間，若系統未在設定之逾時時間內收到有效的新速度命令，應使底盤停止；逾時值與停止行為應經整合及實機驗證。

---

## SYS-028 底盤運動限制

系統應將輪端速度命令及其對應之馬達 RPM 限制於設定之 operational limits；限制值應依機器人層級速度與安全需求選定，並於部署前完成整合及實機驗證。

---

## SYS-029 底盤狀態回授

系統應提供由馬達驅動器有效回授所取得之左右輪位置與速度狀態，供里程估測、控制與診斷使用；無有效回授時，系統不得以命令值取代量測狀態，並應將狀態視為不可用或故障。

---

## SYS-030 底盤安全啟停

系統僅應在底盤通訊正常、無馬達驅動器警報、輪端為停止狀態且驅動器已確認可運動後接受非零運動命令。底盤停用或系統關閉時，系統應嘗試使底盤停止、確認停止狀態並停用馬達驅動；任一安全動作失敗不得阻止其餘安全動作之嘗試。狀態轉換等待時間與停止確認條件應經實機驗證。

---

## SYS-031 底盤配置驗證

系統應於底盤啟用前驗證左右馬達驅動器對應、馬達方向、齒輪比、馬達位置尺度及 operational limit 等必要部署參數；參數缺失、無效或與已核准之實機配置不一致時，系統不得啟用底盤運動並應回報原因。

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
| SYS-031 | UC-001 | CAP-001 |
| SYS-023 | UC-001 | CAP-001 |
| SYS-024 | UC-001 | CAP-001 |
| SYS-008 | UC-002 | CAP-002 |
| SYS-009 | UC-002 | CAP-002 |
| SYS-010 | UC-002 | CAP-002 |
| SYS-011 | UC-002 | CAP-002 |
| SYS-012 | UC-002 | CAP-002 |
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
| SYS-031 | UC-002 | CAP-002 |

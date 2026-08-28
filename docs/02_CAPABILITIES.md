# Capabilities

本文件定義 `mobile_base` v0.1 對外提供之系統能力。

Capability 描述系統可提供之功能，不描述內部設計與實作方式。

---

# CAP-001 建立可重複使用之地圖

## 目的

建立可供定位與導航使用之二維 Occupancy Grid 地圖。

---

## 系統能力

系統應提供下列能力：

- 建立二維 Occupancy Grid。
- 接收使用者手動移動命令控制 AMR 移動以巡覽環境。
- 持續更新建圖結果。
- 儲存地圖。
- 重新載入已建立之地圖。
- 管理 Map Package。
- 回報建圖與 Map Package 儲存結果。

---

## 輸入

- 使用者開始建圖。
- 使用者手動移動命令。

---

## 輸出

- Map Package（包含 `map.pgm` 與 `map.yaml`，成功時）
- Map Creation Result
  - Success
  - Failure

---

## 使用情境

適用於：

- 新場域建置。
- 地圖更新。
- 地圖重新建立。

---

## 對應 Use Case

| Use Case |
|---|
| UC-001 |

---

# CAP-002 自主導航至指定目標

## 目的

使 AMR 自主導航至使用者指定之導航目標。

---

## 系統能力

系統應提供下列能力：

- 接收 Navigation Target。
- 驗證 Navigation Target。
- 將 Navigation Target 解析為 Canonical Goal Pose。
- 使用使用者從場域資料夾選定之 Map Package（建圖產物）與人工建立之 Route Graph。
- 使用 Station Target 時，使用同一場域資料夾中人工建立之 Station Catalog。
- 在開機位置無法可靠得知時，接受使用者提供的 approximate initial pose，供地圖定位初始化。
- 透過標準定位 pose 與 `map → odom` transform 提供地圖定位結果。
- 根據目前位姿、Canonical Goal Pose 與 Route Graph 建立 route-preferred movement strategy。
- 執行 First Mile，將 AMR 由目前位姿銜接至適用的 route entry。
- 執行 On Route movement，沿選定 Route Graph route 移動。
- 執行 Last Mile，將 AMR 由 route exit 銜接至 Canonical Goal Pose。
- 在 route-assisted movement 無法成立或無法安全繼續時，辨識並回報保留的 Free-space Fallback eligibility；v0.1 不執行 fallback movement。
- 監控 navigation stage、stage transition 與整體導航進度。
- 自主避障。
- 自主追蹤路徑。
- 自主抵達導航目標。
- 取消進行中的導航。
- 回報導航結果。

---

## Navigation Target

系統支援下列導航目標。

| Target Type | 說明 |
|---|---|
| Station | 使用 Station ID 指定預先定義站點 |
| Pose | 使用 Goal Pose 指定任意導航位置與朝向 |

---

## 輸入

Navigation Target：

```text
Navigation Target
├── Station ID
└── Goal Pose
```

Navigation Resources：

```text
Navigation Resources（場域資料夾）
├── Map Package（map.pgm 與 map.yaml，UC-001 建圖產物）
├── Route Graph（route_graph.geojson，人工離線標註建立）
└── Station Catalog（stations.yaml，人工離線編輯建立，Station Target 使用）
```

v0.1 由使用者選定場域資料夾，並確認其中的 Map Package（建圖產物）以及人工建立之 Route Graph 與 Station Catalog；系統不提供跨資源 identity／compatibility admission。任一成熟元件無法載入其資源時，沿用該元件的原生失敗與原因回報，且不得將此情況視為 free-space fallback 條件。

Localization Initialization：

```text
Approximate Initial Pose, when required
├── x
├── y
└── yaw
```

Approximate Initial Pose 只用於啟動地圖定位，不是 Navigation Target；v0.1 透過 RViz `2D Pose Estimate` 提供，系統不另行定義 localization-valid 或收斂 gate。

---

## Navigation Strategy

系統的移動原則為 route-preferred：可安全使用 Route Graph 時，應優先沿 Route Graph 移動，不得任意選擇完整 free-space movement。

Route-assisted movement 由以下階段組成：

```text
Current Pose
    │
    ├── First Mile（需要時）
    ▼
Route Entry
    │
    ├── On Route
    ▼
Route Exit
    │
    ├── Last Mile（需要時）
    ▼
Canonical Goal Pose
```

架構保留 Free-space Fallback eligibility：Current Pose 無法連接任何可用 route entry、有效 Route Graph 無法提供通往目標方向的可用 route、On Route movement 受阻且 route reselection 失敗，或所有可用 route-assisted candidates 均無法由 route exit 安全連接目標。v0.1 不執行 Free-space Fallback；符合 eligibility 且已無可用 route-assisted solution 時，系統應終止導航、嘗試使底盤停止並回報 Free-space Fallback unavailable。

---

## 輸出

Navigation Result：

- Success
- Failure
- Canceled

---

## 使用情境

適用於：

- 前往固定站點。
- 前往任意工作位置。
- 前往設備。
- 前往充電站。
- 前往維修位置。

---

## 對應 Use Case

| Use Case |
|---|
| UC-002 |

---

# CAP-003 觀察與診斷 AMR 運行

## 目的

提供 AMR 當前與歷史運行資訊，使操作員或維護／開發人員能依共同時間軸查看與關聯主要子系統狀態、Logs、Events 與 Telemetry，縮小異常可能涉及的子系統範圍，並了解資料完整性與診斷限制。

---

## 系統能力

系統應提供下列能力：

- 提供 AMR 與主要 ROS Subsystem 的當前及歷史運行狀態。
- 提供 ROS Logs 與 Events 的歷史查詢。
- 提供關鍵 Telemetry 的時間序列觀察。
- 依共同時間軸關聯 Navigation、Localization、Perception、Control、Hardware 與 Host 資訊。
- 保存支援歷史診斷所需的運行資料。
- 標示資料來源、可用時間範圍、完整性、資料缺口與時間對齊限制。
- 實際 AMR 無法連接時，使用已保存的真實運行資料進行 best-effort 離線診斷。
- 資料允許時，支援有限 Replay，並標示其與實機運行之差異及限制。

---

## 能力邊界

- 不建立地圖；Map Creation 屬於 CAP-001。
- 不接受或執行 Navigation Target；Navigation Execution 屬於 CAP-002。
- 不控制 Navigation、Localization、Control 或 Safety 行為。
- 不進行 Autonomous Recovery。
- 不輸出自動 Root-cause Conclusion。
- 不承諾 hardware-equivalent 或 real-time-equivalent Replay。
- Replay 為離線診斷手段，不是獨立 Capability。
- 共同時間軸 Correlation 與資料完整性為本 Capability 的必要性質，不構成其他獨立 Capability。

---

## 輸入

- Actor 選定的目前運行期間或歷史時間範圍。
- AMR 與主要 ROS Subsystem 運行狀態。
- Logs 與 Events。
- Telemetry。
- Hardware 與 Host 運行狀態。
- 已保存的真實運行資料。
- 支援時間關聯與資料來源識別的必要資訊。

---

## 輸出

- 指定時間範圍內的 AMR 與主要 ROS Subsystem 運行狀態。
- 可查詢的 Logs 與 Events。
- 關鍵 Telemetry 時間序列。
- 跨來源共同時間軸資訊。
- 協助 Actor 縮小問題可能所屬子系統範圍的診斷資訊。
- 資料完整性、資料缺口、時間對齊限制及離線分析限制。
- Best-effort Offline Diagnosis Result（具備可用的已保存真實運行資料時）。

---

## 使用情境

適用於：

- 確認 AMR 是否正常運行。
- 調查 Mapping、Localization、Navigation、Control 或 Hardware Communication 異常。
- 查詢與分析過去已發生的運行事件。
- 實際 AMR 無法連接時，使用已保存的真實運行資料進行離線診斷。

---

## 對應 Use Case

| Use Case |
|---|
| UC-003 |

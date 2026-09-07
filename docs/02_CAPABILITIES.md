# Capabilities

本文件定義 `mobile_base` 對外提供之系統能力。

Capability 描述系統可提供之功能，不描述內部設計與實作方式。

---

# CAP-001 建立可重複使用之地圖

## 目的

建立可供定位與導航使用的二維佔據網格（Occupancy Grid）地圖。

Map Package 是可儲存及重新載入的地圖產物，可供 CAP-002 的定位與導航使用。

---

## 系統能力

系統應提供下列能力：

- 建立二維 Occupancy Grid。
- 接收使用者手動移動命令控制 AMR 移動以巡覽環境。
- 持續更新建圖結果。
- 將建圖結果儲存為 Map Package。
- 重新載入已建立的 Map Package。
- 回報建圖與 Map Package 儲存結果。

---

## 輸入

- 使用者開始建圖。
- 使用者手動移動命令。
- 已建立的 Map Package（重新載入時）。

---

## 輸出

- 產物：成功時產生 Map Package，包含 `map.pgm` 與 `map.yaml`。
- 結果：回報建圖與 Map Package 儲存成功（Success）或失敗（Failure）。

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

接受使用者指定的導航目標（Navigation Target），利用已準備的場域資料與定位資訊，使 AMR 自主導航至指定目標。

---

## 系統能力

系統應提供下列能力：

- 接收 Navigation Target。
- 驗證 Navigation Target。
- 將不同形式的 Navigation Target 解析與驗證為統一的導航目標位置與朝向（Canonical Goal Pose）。
- 使用選定場域的 Map Package 提供地圖，並使用人工建立的 Route Graph 作為偏好的導航路網。
- 使用 Station Target 時，透過同一場域資料夾中人工建立的 Station Catalog，將 Station ID 對應至位置與朝向。
- 使用預設初始位置與朝向啟動地圖定位；預設不適用時，接受使用者提供的近似位置與朝向覆寫。
- 提供 AMR 在地圖中的位置與朝向，作為導航的位置基準。
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

## 輸入

### Navigation Target

Navigation Target 是使用者希望 AMR 前往的目標描述，支援下列兩種形式。

| Target Type | 說明 |
|---|---|
| Station Target | 使用 Station ID 指定預先定義站點 |
| Pose Target | 使用 Goal Pose 指定任意導航位置與朝向 |

### Navigation Resources

使用者在啟動 Navigation 前選定場域資料夾，並人工確認下列必要資料已準備完成。

| 場域資料 | 角色與準備方式 |
|---|---|
| Map Package（`map.pgm`、`map.yaml`） | UC-001 的建圖產物，提供定位與導航所需地圖 |
| Route Graph（`route_graph.geojson`） | 人工離線標註建立，提供偏好的導航路網 |
| Station Catalog（`stations.yaml`） | 人工離線編輯建立，將 Station ID 對應至位置與朝向；僅 Station Target 需要 |

上述資料放在同一場域資料夾中。資源載入設計參見 [04_SYSTEMS.md §5.2](./04_SYSTEMS.md#52-資源責任與載入架構)。

> 既有系統邊界：系統不提供跨資源 identity／compatibility admission。

任一成熟元件無法載入其資源時，沿用該元件的原生失敗與原因回報，且不得將此情況視為 free-space fallback 條件。

### Localization Initialization

初始定位（Initial Localization）以初始位置與朝向作為地圖定位的起點，不是指定要前往的 Navigation Target。

系統使用部署設定的預設初始位置與朝向。當預設與實際開機位置不符時，使用者可提供近似位置與朝向覆寫（Approximate Initial Pose Override）。

定位介面與初始化設定參見 [04_SYSTEMS.md §4.5](./04_SYSTEMS.md#45-s5-localization)；使用者覆寫操作參見 [01_USE_CASES.md 的初始位置覆寫](./01_USE_CASES.md#初始位置覆寫)。

> 既有行為邊界：系統不另行定義 localization-valid 或收斂 gate。

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

提供 AMR 當前與歷史運行資訊，使操作員或維護／開發人員能查看 Logs、Events 與關鍵 Telemetry，依 timestamp、source 與共同時間範圍進行基本關聯，並人工縮小異常可能涉及的子系統範圍。

---

## 系統能力

系統應提供下列能力：

- 提供 AMR 與主要 ROS Runtime Information 供 Actor 查看。
- 將選定的 Logs 與運行 Events 傳送至 Server，供 Server 保存及歷史查詢。
- 將選定的關鍵 Telemetry 傳送至 Server，供 Server 保存及依時間範圍查詢。
- 為 Logs、Events 與關鍵 Telemetry 保留 timestamp 與 source identity。
- 支援 Actor 依共同時間範圍進行基本人工關聯。
- 提供 Actor 人工縮小異常可能所屬子系統範圍所需的資訊。

---

## 能力邊界

- 不建立地圖；Map Creation 屬於 CAP-001。
- 不接受或執行 Navigation Target；Navigation Execution 屬於 CAP-002。
- 不控制 Navigation、Localization、Control 或 Safety 行為。
- 不保證 Observability 資料傳送成功。
- Observability 或 Server 無法使用不得影響 Navigation、Localization、Control 或 Safety 運行。

---

## 輸入

- Actor 選定的目前運行期間或歷史時間範圍。
- AMR 與主要 ROS Runtime Information。
- Logs 與 Events。
- 關鍵 Telemetry。
- Timestamp 與 source identity。

---

## 輸出

- 指定時間範圍內可用的 AMR 與主要 ROS Runtime Information。
- 可查詢的 Logs 與 Events。
- 關鍵 Telemetry 時間序列。
- 支援基本共同時間範圍關聯的 timestamp 與 source identity。
- 協助 Actor 人工縮小問題可能所屬子系統範圍的資訊。

---

## 使用情境

適用於：

- 確認 AMR 是否正常運行。
- 調查 Mapping、Localization、Navigation、Control 或 Hardware Communication 異常。
- 查詢過去的 Logs、Events 與關鍵 Telemetry。

---

## 對應 Use Case

| Use Case |
|---|
| UC-003 |

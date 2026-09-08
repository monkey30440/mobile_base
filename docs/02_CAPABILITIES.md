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
- 根據目前位姿、Canonical Goal Pose 與 Route Graph 建立 route-assisted navigation strategy。
- 執行 First Mile，將 AMR 由目前位姿銜接至適用的 route entry。
- 執行 On Route movement，沿選定 Route Graph route 移動。
- 執行 Last Mile，將 AMR 由 route exit 銜接至 Canonical Goal Pose。
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

任一成熟元件無法載入其資源時，沿用該元件的原生失敗與原因回報，Navigation 無法正常開始或完成。

### Localization Initialization

初始定位（Initial Localization）以初始位置與朝向作為地圖定位的起點，不是指定要前往的 Navigation Target。

系統使用部署設定的預設初始位置與朝向。當預設與實際開機位置不符時，使用者可提供近似位置與朝向覆寫（Approximate Initial Pose Override）。

定位介面與初始化設定參見 [04_SYSTEMS.md §4.5](./04_SYSTEMS.md#45-s5-localization)；使用者覆寫操作參見 [01_USE_CASES.md 的初始位置覆寫](./01_USE_CASES.md#初始位置覆寫)。

> 既有行為邊界：系統不另行定義 localization-valid 或收斂 gate。

### Navigation Cancel Request

使用者在導航進行中可發出取消請求（Navigation Cancel Request），要求終止目前導航任務。

---

## Navigation Strategy

系統以 Route Graph 為主要導航依據（route-preferred），建立由 Route Graph 輔助的導航策略（route-assisted navigation strategy）。

系統使用當前位置（Current Pose）與目標位置朝向（Canonical Goal Pose），結合 Route Graph 規劃導航路徑。Route-assisted navigation 由以下三階段共同形成通往目標的導航路徑：

- **First Mile**：若目前位置不在 Route Graph 上，使用一般路徑規劃將 AMR 由當前位置銜接至適用的 Route Graph route entry（起點）。
- **On Route**：AMR 沿 Route Graph 計算出的選定 route 移動。
- **Last Mile**：從 Route Graph route exit（終點）使用一般路徑規劃銜接至 Canonical Goal Pose。

```text
Current Pose
    │
    ├── First Mile（銜接至 route entry）
    ▼
Route Entry
    │
    ├── On Route（沿 Route Graph 移動）
    ▼
Route Exit
    │
    ├── Last Mile（銜接至 Canonical Goal Pose）
    ▼
Canonical Goal Pose
```

First Mile 與 Last Mile 使用一般路徑規劃銜接路網與起訖點，為正常 route-assisted navigation 的組成部分。

三段路徑共同形成完整的導航路徑並由系統執行。若 route 無法建立、必要銜接路徑無法建立、路徑執行失敗或整體導航策略無法完成，系統終止導航並回報 Navigation Failure。

---

## 輸出

系統完成或終止導航任務時，回報導航結果（Navigation Result）：

- **Success**：AMR 已自主完成導航並抵達指定的 Navigation Target（對 Station Target 而言代表抵達站點目標位置與朝向，不代表對接 docking 完成）。
- **Failure**：導航未能完成（如路網或銜接路徑無法建立、執行受阻或整體策略無法完成）。
- **Canceled**：收到使用者取消請求後，系統停止目前導航流程並終止任務。

---

## 使用情境

適用於：

- 指定預先定義站點（Station Target）進行自主導航。
- 指定任意位置與朝向（Pose Target）進行自主導航。
- 必要時提供初始定位覆寫以啟動導航定位基準。
- 導航進行中依需求取消導航任務。
- 系統自主執行路徑追蹤與避障，並回報導航結果。

---

## 對應 Use Case

| Use Case |
|---|
| UC-002 |

---

# CAP-003 觀察與診斷 AMR 運行

## 目的

提供 AMR 當前與歷史運行資訊，協助操作員或維護／開發人員查看 Logs、Events 與關鍵 Telemetry，依時間戳（Timestamp）與來源（Source）在共同時間範圍內進行基本人工關聯，以協助人工縮小異常可能涉及的子系統範圍。

---

## 系統能力

系統應提供下列能力：

- 收集並提供 AMR 與主要 ROS Runtime Information。
- 支援將選定的 Logs 與 Events 傳送至保存端以供歷史查詢。
- 支援將選定的關鍵 Telemetry 傳送至保存端以供依時間範圍查詢。
- 為 Logs、Events 與關鍵 Telemetry 保留時間戳（Timestamp）與來源識別（Source Identity）。
- 支援使用者在共同時間範圍內查詢歷史資料並進行基本人工關聯。
- 提供支援使用者人工縮小異常可能所屬子系統範圍所需的運行資訊。

---

## 能力邊界

- 不建立地圖；Map Creation 屬於 CAP-001。
- 不接受或執行 Navigation Target；Navigation Execution 屬於 CAP-002。
- 不控制 Navigation、Localization、Control 或 Safety 行為。
- 不保證 Observability 資料傳送成功，亦不保證自動診斷出根本原因（Root Cause）。
- Observability 或保存／查詢端無法使用不得影響 Navigation、Localization、Control 或 Safety 核心功能運行。

---

## 輸入

### 查詢輸入（Query Input）

使用者查詢時提供的條件：

- 使用者選定的目前運行期間或歷史時間範圍。

### 被觀察運行資料（Observed Runtime Data）

AMR 運行時產生並由系統處理的資訊：

- AMR 與主要 ROS Runtime Information。
- 日誌（Logs）與事件（Events）。
- 關鍵量測資料（Telemetry）。
- 資料的時間戳（Timestamp）與來源識別（Source Identity）。

---

## 輸出

系統提供支援人工觀察與診斷的運行資訊：

- 指定時間範圍內可用的 AMR 與主要 ROS Runtime Information。
- 可查詢的 Logs 與 Events。
- 可查詢的關鍵 Telemetry 時間序列。
- 支援在共同時間範圍內進行人工關聯的時間戳與來源資訊。

---

## 使用情境

適用於：

- 確認 AMR 目前或過去是否正常運行。
- 在指定時間範圍內查詢 Logs、Events 與 Telemetry。
- 利用時間戳與來源資訊，人工關聯建圖、定位、導航、控制或硬體通訊之異常事件。
- 協助操作員或維護人員人工縮小問題可能所屬的子系統範圍。

---

## 對應 Use Case

| Use Case |
|---|
| UC-003 |

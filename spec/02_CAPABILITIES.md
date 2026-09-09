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

- 接收 Navigation Target（支援 Generic Pose Target 與 Station Target）。
- 對 Generic Pose Target，直接以標準導航介面接收外部提供之 Canonical Goal Pose 進行導航，不要求系統額外建立自訂轉接。
- 對 Station Target，使用選定場域之 Station Catalog 將 Station ID 解析為 Canonical Goal Pose，經必要驗證後進入導航。
- 使用選定場域的 Map Package 提供地圖，並使用人工建立的 Route Graph 作為偏好的導航路網。
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

Navigation Target 是使用者希望 AMR 前往的目標描述，支援下列兩種形式：

| Target Type | 說明與介面契約 |
|---|---|
| Generic Pose Target | 由外部直接提供符合標準導航介面之 Canonical Goal Pose（包含目標位置與朝向），直接作為導航目標使用，不要求系統額外建立自訂轉接 |
| Station Target | 使用 Station ID 指定預先定義站點，由系統透過場域 Station Catalog 解析為 Canonical Goal Pose，並於通過驗證後進入導航 |

### Navigation Resources

使用者在啟動 Navigation 前選定場域資料夾，並人工確認下列必要資料已準備完成。

| 場域資料 | 角色與準備方式 |
|---|---|
| Map Package（`map.pgm`、`map.yaml`） | UC-001 的建圖產物，提供定位與導航所需地圖 |
| Route Graph（`route_graph.geojson`） | 人工離線標註建立，提供偏好的導航路網 |
| Station Catalog（`stations.yaml`） | 人工離線編輯建立，將 Station ID 對應至位置與朝向；僅 Station Target 需要 |

上述資料放在同一場域資料夾中。資源載入設計參見 [`04_SYSTEMS.md` 的 System References → Production Resources](./04_SYSTEMS.md#112-production-resources)。

> 既有系統邊界：系統不提供跨資源 identity／compatibility admission。

任一成熟元件無法載入其資源時，沿用該元件的原生失敗與原因回報，Navigation 無法正常開始或完成。

### Localization Initialization

初始定位（Initial Localization）以初始位置與朝向作為地圖定位的起點，不是指定要前往的 Navigation Target。

系統使用部署設定的預設初始位置與朝向。當預設與實際開機位置不符時，使用者可提供近似位置與朝向覆寫（Approximate Initial Pose Override）。

定位介面與初始化設定參見 [`04_SYSTEMS.md` 的 Localization](./04_SYSTEMS.md#5-localization)；使用者覆寫操作參見 [01_USE_CASES.md 的初始位置覆寫](./01_USE_CASES.md#初始位置覆寫)。

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
- 指定任意位置與朝向（Generic Pose Target）進行自主導航。
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

---

# CAP-004 精準停靠

## 目的

接收外部任務控制端之停靠要求與外部系統提供之停靠目標資訊，控制 AMR 在目標鄰近範圍內自主完成局部精準接近、對準與停止，並回報停靠結果。

---

## 系統能力

系統應提供下列能力：

- 接收外部任務控制端提出之停靠要求。
- 接收外部系統提供之停靠目標資訊，並確認其可供使用。
- 根據停靠目標資訊控制 AMR 執行目標鄰近範圍內的精準接近與對準。
- 停靠期間持續使用外部更新之目標資訊調整停靠運動，並提供執行狀態。
- 無法安全繼續、目標資訊失效或無法在允許時間內完成時，終止停靠、使 AMR 停止並回報失敗。
- 接收外部任務控制端提出之取消要求，終止停靠、使 AMR 停止並回報取消。
- 達成預定停靠條件時使 AMR 停止，並回報停靠成功。

---

## 能力邊界

- 不負責場域長距離導航或路網規劃；全域導航屬於 CAP-002。
- 不負責產生停靠目標感知或位姿資訊；目標資訊由外部系統提供。
- 不負責充電連接確認或充電管理。
- 不管理場域停靠站點資料庫或上層任務排程。

---

## 輸入

### 停靠任務控制

- 停靠要求（Docking Request）：外部任務控制端發起停靠任務之明確要求。
- 停靠取消請求（Docking Cancel Request）：外部任務控制端要求中斷進行中停靠任務之請求。

### 停靠目標資訊

由外部系統提供，描述停靠目標相對於 AMR 的空間位置與朝向，供停靠接近與對準使用。停靠期間可持續更新。

---

## 輸出

系統完成或終止停靠任務時，回報停靠結果（Docking Result）：

- **Success**：AMR 抵達預定停靠相對位置與朝向容差範圍，停止，並回報成功（不代表充電流程或電氣連接完成）。
- **Failure**：停靠未能完成（如外部停靠目標資訊不可用或中斷、逼近過程受阻或超時未收斂）。
- **Canceled**：收到外部取消請求後，系統停止停靠並終止任務。

---

## 與其他 Capability 的關係

CAP-002 與 CAP-004 為並列且獨立之系統能力。在運作流程上，系統可先由 CAP-002 將 AMR 導航至停靠目標鄰近範圍，再由 CAP-004 執行精準停靠；但 CAP-004 不要求 CAP-002 必須先執行。CAP-002 的 Station Target 不等於停靠目標（Docking Target），且 Navigation Success 亦不代表停靠完成。

---

## 使用情境

適用於：

- 接收停靠要求，對指定停靠目標執行精準接近與對準。
- 在目標鄰近範圍內完成精準終端對準與停靠。
- 停靠進行中依外部要求取消任務。

---

## 對應 Use Case

| Use Case |
|---|
| UC-004 |

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
- 持續更新建圖結果。
- 儲存地圖。
- 重新載入已建立之地圖。
- 管理 Map Package。
- 回報建圖與 Map Package 儲存結果。

---

## 輸入

- 使用者開始建圖。

---

## 輸出

- Map Package（成功時）
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
- 載入並驗證與目前 Map Package 相容的 Route Graph。
- 載入並驗證 Station Target 所需的 Station Catalog。
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
Navigation Resources
├── Map Package
├── Route Graph
└── Station Catalog（Station Target 使用）
```

Route Graph 與 Station Catalog 必須與目前 Map Package 相容。缺失、無效或不相容的 Navigation Resource 屬於 configuration failure，不構成 free-space fallback 條件。

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

# Use Cases

本文件定義 `mobile_base` v0.1 使用者可操作之系統功能。

Use Case 描述使用者可完成之工作流程，不描述內部演算法或系統實作。

---

# UC-001 建立地圖

## 目的

建立可供定位與導航使用之二維 Occupancy Grid 地圖。

---

## 參與者

- 使用者

---

## 前置條件

- AMR 已完成啟動並可由使用者操作。
- 系統已具備執行建圖所需之功能。

---

## 觸發條件

使用者開始建圖。

---

## 基本流程

1. 使用者啟動 Mapping。
2. 系統開始建立 Occupancy Grid。
3. 使用者操作 AMR 巡覽環境。
4. 系統持續更新地圖。
5. 使用者完成環境巡覽。
6. 系統儲存 Map Package。

---

## Failure Flow

- 前置條件不成立時，系統不開始建圖並回報原因。
- 建圖期間無法繼續時，系統終止建圖並回報失敗。
- Map Package 無法儲存時，系統回報失敗，且不得回報已建立可重新載入之 Map Package。

---

## 完成條件

建立完整且可重新載入之 Map Package。

---

## 使用系統能力

| Capability |
|---|
| CAP-001 |

---

# UC-002 導航至指定目標

## 目的

使 AMR 自主導航至使用者指定之導航目標。

---

## 參與者

- 使用者

---

## Navigation Target

系統支援下列導航目標。

| Target Type | 說明 |
|---|---|
| Station | 使用 Station ID 指定預先定義之站點 |
| Pose | 使用 Goal Pose 指定任意可導航位置與朝向 |

---

## 前置條件

- AMR 已完成啟動。
- 已載入可供導航使用之 Map Package。
- 已載入與目前 Map Package 相容且有效之 Route Graph。
- Station Target 所需之 Station Catalog 已載入、有效且與目前 Map Package 相容。
- AMR 已在目前地圖中完成定位，且系統可接受導航任務。

---

## 觸發條件

使用者提交 Navigation Target。

---

## 基本流程

1. 使用者指定 Navigation Target。
2. 系統驗證 Navigation Target 與導航所需資源，並將 Navigation Target 解析為 Canonical Goal Pose。
3. 系統根據目前位姿、Canonical Goal Pose 與 Route Graph 建立 route-preferred movement strategy。
4. 若目前位姿不在選定 route entry，系統執行 First Mile 銜接該 entry。
5. 系統沿選定 Route Graph 執行 On Route movement。
6. 若選定 route exit 未直接到達 Canonical Goal Pose，系統執行 Last Mile 銜接目標。
7. 系統持續監控 navigation stage 與整體導航進度。
8. 系統抵達 Navigation Target、停止並回報導航結果。

---

## Alternative Flow

### Station Target

使用者提供 Station ID。系統確認該 Station 存在，並將其解析為導航目標。

---

### Pose Target

使用者提供 Goal Pose。系統確認該 Pose 可作為導航目標後，使用該 Pose 執行導航。

---

### Zero-length Connection Stage

若目前位姿已位於適用的 route entry，First Mile 可省略。若 Canonical Goal Pose 已位於適用的 route exit，Last Mile 可省略。

---

### Reserved Free-space Fallback Boundary

系統應優先使用可安全執行的 route-assisted movement。架構保留下列 Free-space Fallback eligibility，以供後續版本擴充：

- Current Pose 無法連接任何可用 route entry。
- Active、valid Route Graph 無法提供通往 Canonical Goal Pose 方向的可用 route。
- On Route movement 因目前環境阻塞而無法維持，且重新選擇 Route Graph route 仍失敗。
- 所有可用 route-assisted candidates 均無法由 route exit 透過 Last Mile 安全連接 Canonical Goal Pose。

存在有效且可安全執行的 route-assisted solution 時，系統不得任意選擇完整 free-space movement。v0.1 不執行 Free-space Fallback；符合上述任一 eligibility 且已無可用 route-assisted solution 時，系統應終止導航、嘗試使底盤停止，並回報 Free-space Fallback unavailable。

---

## Failure / Cancellation Flow

- Station ID 不存在或 Goal Pose 無效時，系統拒絕導航任務並回報原因。
- Route Graph 缺失、無效或與目前 Map Package 不相容時，系統拒絕導航任務並回報原因，不得將此情況視為 free-space fallback。
- Station Target 所需之 Station Catalog 缺失、無效或與目前 Map Package 不相容時，系統拒絕導航任務並回報原因，不得將此情況視為 free-space fallback。
- Navigation configuration 無效時，系統拒絕導航任務並回報原因，不得將此情況視為 free-space fallback。
- First Mile、On Route 或 Last Mile 無法安全執行時，系統應先用盡可用的 route-assisted alternatives。
- 符合保留的 Free-space Fallback eligibility 但已無可用 route-assisted solution 時，v0.1 應終止導航、嘗試使底盤停止，並回報 Free-space Fallback unavailable。
- 系統無法繼續導航時，系統終止導航任務並回報失敗。
- 使用者取消導航時，系統終止導航任務並回報取消結果。

---

## 完成條件

- AMR 抵達使用者指定之 Navigation Target。
- 系統回報導航成功。

---

## 使用系統能力

| Capability |
|---|
| CAP-002 |

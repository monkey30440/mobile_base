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
- AMR 已在目前地圖中完成定位，且系統可接受導航任務。

---

## 觸發條件

使用者提交 Navigation Target。

---

## 基本流程

1. 使用者指定 Navigation Target。
2. 系統驗證並解析 Navigation Target。
3. 系統開始自主導航。
4. 系統持續監控導航進度。
5. 系統抵達 Navigation Target 並回報導航結果。

---

## Alternative Flow

### Station Target

使用者提供 Station ID。系統確認該 Station 存在，並將其解析為導航目標。

---

### Pose Target

使用者提供 Goal Pose。系統確認該 Pose 可作為導航目標後，使用該 Pose 執行導航。

---

## Failure / Cancellation Flow

- Station ID 不存在或 Goal Pose 無效時，系統拒絕導航任務並回報原因。
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

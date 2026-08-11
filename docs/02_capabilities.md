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
- 即時更新建圖結果。
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
- 解析 Navigation Target。
- 自主規劃導航。
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

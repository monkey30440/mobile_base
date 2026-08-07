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

- AMR 已完成啟動。
- 系統已完成 Hardware Bring-up。
- LiDAR、IMU 與底盤運作正常。
- Mapping 模式已啟動。

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

## 完成條件

建立完整且可重新載入之 Map Package。

---

## 使用系統能力

| Capability |
|---|
| CAP-001 |

---

## 涉及子系統

| Subsystem |
|---|
| SUB-001 Base Control |
| SUB-002 LiDAR Perception |
| SUB-003 IMU Perception |
| SUB-004 Differential Drive Controller |
| SUB-005 RF2O Odometry |
| SUB-006 Robot Localization EKF |
| SUB-007 SLAM Toolbox |
| SUB-008 Map Management |
| SUB-012 Robot Description |

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
- 已載入 Map Package。
- 系統已完成定位。
- Navigation 已完成初始化。

---

## 觸發條件

使用者提交 Navigation Target。

---

## 基本流程

1. 使用者指定 Navigation Target。
2. 系統驗證 Navigation Target。
3. 系統解析 Navigation Target。
4. 系統產生 Goal Pose。
5. 系統取得 AMR Current Pose。
6. 系統依 Current Pose、Goal Pose 與 Route Graph 決定導航策略。
7. 可利用 Route Graph 時，優先沿 Route Graph 導航。
8. Route Graph 無法涵蓋之區段，以自由空間導航完成。
9. 系統持續規劃與控制 AMR。
10. 系統判定 AMR 抵達 Goal Pose。
11. 系統回報導航結果。

---

## Alternative Flow

### Station Target

```text
Station ID
      │
      ▼
Target Resolver
      │
      ▼
Goal Pose
```

Station ID 經解析後產生 Goal Pose。

---

### Pose Target

```text
Goal Pose
      │
      ▼
Target Resolver
      │
      ▼
Goal Pose
```

Goal Pose 直接作為導航目標。

---

## Navigation Strategy

Navigation 負責決定是否利用 Route Graph。

系統遵循下列原則：

- 可合理利用 Route Graph 時，優先使用 Route Graph。
- Current Pose 不在 Route Graph 上時，可使用 First Mile 銜接路網。
- Goal Pose 不在 Route Graph 上時，可使用 Last Mile 離開路網。
- Route Graph 不適用時，使用自由空間導航。

Navigation Strategy 為 Navigation 內部行為，不受 Navigation Target 類型限制。

---

## 完成條件

- AMR 抵達指定 Goal Pose。
- AMR 達到指定位置與朝向。
- 系統回報導航成功。

---

## 使用系統能力

| Capability |
|---|
| CAP-002 |

---

## 涉及子系統

| Subsystem |
|---|
| SUB-001 Base Control |
| SUB-002 LiDAR Perception |
| SUB-003 IMU Perception |
| SUB-004 Differential Drive Controller |
| SUB-005 RF2O Odometry |
| SUB-006 Robot Localization EKF |
| SUB-008 Map Management |
| SUB-009 Task Interface |
| SUB-010 Target Resolution |
| SUB-011 Navigation |
| SUB-012 Robot Description |
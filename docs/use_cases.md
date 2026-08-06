# Use Cases

本文件定義 `mobile_base` 系統之使用情境（Use Case），作為系統能力、需求與設計之起點。

---

# UC-001 建立可重複使用之地圖

## 目的

使使用者能建立二維環境地圖，並儲存為可供後續定位與導航使用之地圖。

---

## 參與者

- 使用者

---

## 前置條件

- 系統已完成啟動。
- LiDAR、IMU、Wheel Odometry 運作正常。
- AMR 位於欲建圖環境。

---

## 觸發條件

使用者開始建圖。

---

## 基本流程

1. 使用者啟動建圖功能。
2. 系統開始接收感測器資料。
3. 使用者操作 AMR 移動。
4. 系統持續建立 Occupancy Grid 地圖。
5. 使用者完成環境巡覽。
6. 使用者儲存地圖。
7. 系統完成地圖儲存。

---

## 完成條件

- 地圖成功建立。
- 地圖成功儲存。
- 地圖可供後續定位與導航使用。

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
| SUB-004 Wheel Odometry |
| SUB-005 RF2O Odometry |
| SUB-006 Robot Localization EKF |
| SUB-007 SLAM Toolbox |
| SUB-008 Map Management |

---

# UC-002 導航至指定路網站點

## 目的

使使用者能指定路網站點，AMR 自主沿 Route Graph 移動至目標站點。

---

## 參與者

- 使用者

---

## 前置條件

- 系統已完成啟動。
- 已載入指定 Map Package。
- 已載入 Route Graph。
- 已完成定位。
- Navigation 系統已完成初始化。

---

## 觸發條件

使用者提交目標站點。

---

## 基本流程

1. 使用者指定目標站點。
2. 系統驗證目標站點。
3. 系統取得 AMR 目前位姿。
4. 系統計算 Route。
5. 系統完成目前位置與 Route Graph 的銜接。
6. 系統沿 Route Graph 導航。
7. 系統判定 AMR 抵達目標站點。
8. 系統回報任務完成。

---

## 完成條件

- AMR 抵達指定站點。
- AMR 達到站點指定朝向。
- 系統回報導航完成。

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
| SUB-004 Wheel Odometry |
| SUB-005 RF2O Odometry |
| SUB-006 Robot Localization EKF |
| SUB-008 Map Management |
| SUB-009 Task Interface |
| SUB-010 Route Graph Management |
| SUB-011 Navigation |

---

# UC-003 導航至任意指定 Pose

## 目的

使使用者能指定地圖中任意可通行之目標 Pose，AMR 自主規劃導航路徑並移動至指定位置與朝向。

---

## 參與者

- 使用者

---

## 前置條件

- 系統已完成啟動。
- 已載入指定 Map Package。
- AMR 已完成定位。
- Navigation 系統已完成初始化。

---

## 觸發條件

使用者提交目標 Pose。

---

## 基本流程

1. 使用者指定目標 Pose。
2. 系統驗證目標 Pose。
3. 系統取得 AMR 目前位姿。
4. 系統產生導航路徑。
5. 系統控制 AMR 沿路徑移動。
6. 系統判定 AMR 抵達目標 Pose。
7. 系統回報任務完成。

---

## 完成條件

- AMR 抵達指定位置。
- AMR 達到指定朝向。
- 系統回報導航完成。

---

## 使用系統能力

| Capability |
|---|
| CAP-003 |

---

## 涉及子系統

| Subsystem |
|---|
| SUB-001 Base Control |
| SUB-002 LiDAR Perception |
| SUB-003 IMU Perception |
| SUB-004 Wheel Odometry |
| SUB-005 RF2O Odometry |
| SUB-006 Robot Localization EKF |
| SUB-008 Map Management |
| SUB-009 Task Interface |
| SUB-011 Navigation |

---

## 備註

UC-003 與 UC-002 共用相同導航架構。

UC-002 使用 Route Graph 完成站點導航。

UC-003 直接以 Goal Pose 作為導航目標，不使用 Route Graph 與 Station Mapping，由 Nav2 完成路徑規劃、導航與到站判定。
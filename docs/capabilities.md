# Capabilities

本文件定義 mobile_base 各項系統能力（Capability），作為 Use Case 與 System Requirements 間之橋接。

---

# CAP-001 建立可重複使用之地圖

## 目的

使 AMR 能建立二維環境地圖，並儲存為可供後續定位與導航重複使用之地圖。

---

## 對應 Use Case

| Use Case |
|---|
| UC-001 |

---

## 能力描述

系統透過 LiDAR、IMU 與 Wheel Odometry 建立 AMR 運動估測，利用 SLAM 建立 Occupancy Grid 地圖，並將地圖儲存供後續載入使用。

---

## 驗收標準

- 系統可建立二維 Occupancy Grid 地圖。
- 系統可持續更新建圖結果。
- 系統可儲存地圖。
- 系統可重新載入地圖。
- 載入後地圖內容與儲存前一致。

---

## 驗證方式

於實機完成建圖，儲存地圖後重新載入，確認地圖可供後續定位與導航使用。

---

## Traceability

| Capability | Use Case |
|---|---|
| CAP-001 | UC-001 |

---

# CAP-002 導航至指定路網站點

## 目的

使 AMR 能由目前位置自主移動至使用者指定之路網站點。

---

## 對應 Use Case

| Use Case |
|---|
| UC-002 |

---

## 能力描述

系統取得 AMR 目前位姿，接收使用者指定之目標站點，依既有地圖與路網產生導航路徑，並控制 AMR 抵達目標站點。

AMR 目前位置與路網之銜接方式由 Navigation 子系統依實際位置自動決定。

---

## 驗收標準

- 系統可取得 AMR 目前位姿。
- 系統可接收有效目標站點。
- 系統可載入地圖與路網。
- 系統可解析目標站點。
- 系統可依地圖與路網產生導航路徑。
- 系統可完成站點導航。
- AMR 可抵達指定目標站點。
- 系統可回報任務完成。

---

## 驗證方式

於實機由不同初始位置執行路網站點移動任務，確認系統可自動完成導航並抵達指定站點。

---

## Traceability

| Capability | Use Case |
|---|---|
| CAP-002 | UC-002 |

---

# CAP-003 導航至任意指定 Pose

## 目的

使 AMR 能由目前位置自主移動至使用者指定之任意 Pose。

---

## 對應 Use Case

| Use Case |
|---|
| UC-003 |

---

## 能力描述

系統取得 AMR 目前位姿，接收使用者指定之目標 Pose，依既有地圖產生導航路徑，並控制 AMR 抵達指定位置與朝向。

Navigation 子系統依目前位姿與目標 Pose 的相對位置，自動組合 First Mile、On Route 與 Last Mile 導航策略。

---

## 驗收標準

- 系統可取得 AMR 目前位姿。
- 系統可接收有效目標 Pose。
- 系統可依地圖產生導航路徑。
- 系統可完成 Pose 導航。
- AMR 可抵達指定位置與朝向。
- 系統可回報任務完成。

---

## 驗證方式

於實機指定不同目標 Pose 執行導航任務，確認 AMR 可自主抵達指定位置與朝向。

---

## Traceability

| Capability | Use Case |
|---|---|
| CAP-003 | UC-003 |

# CAP-003 Navigate to Arbitrary Pose

## 目的

使 AMR 能夠導航至地圖中任意指定之 Goal Pose，並於可通行區域內自主規劃路徑、避開障礙物，最後抵達指定位置與朝向。

---

## 對應 Use Case

| Use Case |
|---|
| UC-003 |

---

## 功能描述

系統接收使用者指定之 Goal Pose，利用目前定位結果與地圖資訊，自主規劃導航路徑，控制 AMR 移動至目標位置。

Goal Pose 可位於地圖中任意可通行位置，不需事先建立 Route Graph 或 Station Mapping。

---

## 前置條件

- 已完成系統啟動。
- 已載入 Map Package。
- AMCL 已完成定位。
- Nav2 已完成初始化。
- Goal Pose 位於可導航區域。

---

## 輸入

| 項目 | 說明 |
|---|---|
| Goal Pose | 使用者指定之目標位置與朝向 |

---

## 輸出

| 項目 | 說明 |
|---|---|
| Navigation Status | 導航執行狀態 |
| Navigation Result | 任務完成結果 |

---

## 系統能力

系統應具備下列能力：

1. 接收 Goal Pose。
2. 驗證 Goal Pose。
3. 取得 AMR 目前位姿。
4. 規劃至 Goal Pose 的導航路徑。
5. 即時避開環境障礙物。
6. 控制 AMR 沿規劃路徑移動。
7. 判定 AMR 抵達 Goal Pose。
8. 回報導航結果。

---

## 系統流程

```text
Goal Pose
     │
     ▼
Validate Goal
     │
     ▼
Get Current Pose
     │
     ▼
Global Path Planning
     │
     ▼
Path Following
     │
     ▼
Obstacle Avoidance
     │
     ▼
Goal Checking
     │
     ▼
Navigation Result
```

---

## 採用成熟方案

初版優先採用 Nav2 Navigation Stack：

- AMCL
- Planner Server
- Controller Server
- BT Navigator
- Global Costmap
- Local Costmap
- Goal Checker
- Progress Checker
- Lifecycle Manager

不使用：

- Route Graph
- Route Server
- Station Mapping

---

## 與 UC-002 差異

| 項目 | UC-002 | UC-003 |
|---|---|---|
| Navigation Target | Station ID | Goal Pose |
| Route Graph | 使用 | 不使用 |
| Station Mapping | 使用 | 不使用 |
| Route Server | 使用 | 不使用 |
| Global Planner | Route Graph | Nav2 Planner |
| Navigation | Nav2 | Nav2 |

---

## 對應子系統

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

## 驗證項目

| 驗證項目 | 完成條件 |
|---|---|
| Goal Pose | 可接收任意 Goal Pose |
| Goal Validation | 可驗證 Goal Pose 合法性 |
| Path Planning | 可產生導航路徑 |
| Path Following | AMR 可沿路徑移動 |
| Obstacle Avoidance | 可避開靜態與動態障礙物 |
| Goal Arrival | 可抵達指定位置與朝向 |
| Navigation Result | 可回報導航完成結果 |
| Repeated Navigation | 可重複執行多次 Goal Pose 導航 |

---

## Traceability

| Use Case | Capability |
|---|---|
| UC-003 | CAP-003 |
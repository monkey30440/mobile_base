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

---

## 輸入

- 使用者開始建圖。

---

## 輸出

- Map Package

```text
maps/
└── <map_name>/
    ├── map.pgm
    ├── map.yaml
    ├── route_graph.geojson
    └── stations.yaml
```

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

## 對應 Subsystem

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
- 回報導航結果。

---

## Navigation Target

系統支援下列導航目標。

| Target Type | 說明 |
|---|---|
| Station | 使用 Station ID 指定預先定義站點 |
| Pose | 使用 Goal Pose 指定任意導航位置與朝向 |

---

## Navigation

Navigation 根據目前位姿、導航目標與環境資訊，自主決定導航策略。

系統應：

- 可利用 Route Graph 時優先使用 Route Graph。
- 必要時使用自由空間導航。
- 支援 First Mile。
- 支援 On Route Navigation。
- 支援 Last Mile。

Navigation Strategy 為系統內部行為。

Navigation Target 不限制 Navigation Strategy。

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

## 對應 Subsystem

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
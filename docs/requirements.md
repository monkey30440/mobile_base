# Requirements

本文件定義 `mobile_base` 系統需求（System Requirements），作為系統設計、實作與驗證依據。

---

# UC-001 建立可重複使用之地圖

## SYS-001 建圖

系統應建立二維 Occupancy Grid 地圖。

---

## SYS-002 底盤控制

系統應控制差速底盤完成移動。

---

## SYS-003 LiDAR 感知

系統應取得 LiDAR 掃描資料。

---

## SYS-004 IMU 感知

系統應取得 IMU 量測資料。

---

## SYS-005 里程估測

系統應提供可供定位、建圖與導航使用之平面里程資訊。

---

## SYS-006 地圖發布

系統應發布建立完成之 Occupancy Grid 地圖。

---

## SYS-007 地圖儲存

系統應儲存 Occupancy Grid 地圖。

---

## SYS-008 地圖載入

系統應載入指定 Occupancy Grid 地圖。

---

## SYS-009 地圖管理

系統應管理 Map Package。

---

# UC-002 導航至指定路網站點

## SYS-010 Route Graph

系統應載入指定 Map Package 之 Route Graph。

---

## SYS-011 Navigation

系統應提供自主導航能力。

---

## SYS-012 Navigation Task

系統應接收路網站點導航任務。

---

## SYS-013 Station Mapping

系統應提供 Station ID 與 Route Node ID 對應。

---

## SYS-014 Route Navigation

系統應沿 Route Graph 導航至指定站點。

---

## SYS-015 Path Execution

系統應控制 AMR 沿導航路徑移動。

---

## SYS-016 Goal Checking

系統應判定 AMR 已抵達目標站點。

---

## SYS-017 Navigation Result

系統應回報導航任務完成或失敗結果。

---

# UC-003 導航至任意指定 Pose

## SYS-018 Goal Pose

系統應接收使用者指定之 Goal Pose。

---

## SYS-019 Goal Validation

系統應驗證 Goal Pose 是否可導航。

---

## SYS-020 Pose Planning

系統應規劃至 Goal Pose 的導航路徑。

---

## SYS-021 Pose Navigation

系統應自主導航至 Goal Pose。

---

## SYS-022 Goal Pose Checking

系統應判定 AMR 已抵達 Goal Pose。

---

## SYS-023 Goal Pose Result

系統應回報 Goal Pose 導航任務完成或失敗結果。

---

# Requirement Traceability

| Requirement | Use Case | Capability |
|---|---|---|
| SYS-001 | UC-001 | CAP-001 |
| SYS-002 | UC-001 | CAP-001 |
| SYS-003 | UC-001 | CAP-001 |
| SYS-004 | UC-001 | CAP-001 |
| SYS-005 | UC-001 | CAP-001 |
| SYS-006 | UC-001 | CAP-001 |
| SYS-007 | UC-001 | CAP-001 |
| SYS-008 | UC-001 | CAP-001 |
| SYS-009 | UC-001 | CAP-001 |
| SYS-010 | UC-002 | CAP-002 |
| SYS-011 | UC-002 | CAP-002 |
| SYS-012 | UC-002 | CAP-002 |
| SYS-013 | UC-002 | CAP-002 |
| SYS-014 | UC-002 | CAP-002 |
| SYS-015 | UC-002 | CAP-002 |
| SYS-016 | UC-002 | CAP-002 |
| SYS-017 | UC-002 | CAP-002 |
| SYS-018 | UC-003 | CAP-003 |
| SYS-019 | UC-003 | CAP-003 |
| SYS-020 | UC-003 | CAP-003 |
| SYS-021 | UC-003 | CAP-003 |
| SYS-022 | UC-003 | CAP-003 |
| SYS-023 | UC-003 | CAP-003 |
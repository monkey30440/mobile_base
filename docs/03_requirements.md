# System Requirements

本文件定義 `mobile_base` v0.1 之功能需求。

Requirement 描述系統必須滿足之能力，不描述系統實作方式。

---

# UC-001 建立地圖

## SYS-001 建立地圖

系統應建立可供定位與導航使用之二維 Occupancy Grid 地圖。

---

## SYS-002 儲存地圖

系統應儲存建圖結果為 Map Package。

---

## SYS-003 LiDAR 感知

系統應提供 LiDAR 掃描資料供建圖、定位與導航使用。

---

## SYS-004 IMU 感知

系統應提供 IMU 量測資料供定位使用。

---

## SYS-005 系統里程

系統應提供可供定位、建圖與導航使用之平面里程資訊。

---

## SYS-006 即時建圖

系統應支援即時更新二維地圖。

---

## SYS-007 地圖管理

系統應支援地圖儲存與重新載入。

---

# UC-002 導航至指定目標

## SYS-008 Navigation Target

系統應支援以下 Navigation Target：

- Station
- Goal Pose

---

## SYS-009 Navigation Target Processing

系統應能接受並處理 Navigation Target。

---

## SYS-010 地圖定位

系統應根據已載入地圖估測 AMR 位姿。

---

## SYS-011 路徑規劃

系統應規劃由目前位姿至導航目標之可行路徑。

---

## SYS-012 Route Graph Navigation

系統應於適用時支援利用 Route Graph 導航。

---

## SYS-013 自由空間導航

系統應於 Route Graph 不適用時支援自由空間導航。

---

## SYS-014 障礙物避讓

系統應於導航期間考量環境障礙物。

---

## SYS-015 路徑追蹤

系統應沿規劃路徑控制 AMR 移動。

---

## SYS-016 到站判定

系統應判定 AMR 是否已抵達導航目標。

---

## SYS-017 導航結果

系統應回報導航完成或失敗。

---

## SYS-018 Navigation Strategy

系統應依目前位姿、導航目標與 Route Graph 自主選擇適當導航策略。

---

## SYS-019 Route-assisted Navigation

系統於可合理利用 Route Graph 時，應優先沿 Route Graph 導航。

---

## SYS-020 First Mile

系統應支援由目前位姿銜接 Route Graph。

---

## SYS-021 Last Mile

系統應支援由 Route Graph 銜接導航目標。

---

## Traceability

| Requirement | Use Case | Capability |
|---|---|---|
| SYS-001 | UC-001 | CAP-001 |
| SYS-002 | UC-001 | CAP-001 |
| SYS-003 | UC-001 | CAP-001 |
| SYS-004 | UC-001 | CAP-001 |
| SYS-005 | UC-001 | CAP-001 |
| SYS-006 | UC-001 | CAP-001 |
| SYS-007 | UC-001 | CAP-001 |
| SYS-008 | UC-002 | CAP-002 |
| SYS-009 | UC-002 | CAP-002 |
| SYS-010 | UC-002 | CAP-002 |
| SYS-011 | UC-002 | CAP-002 |
| SYS-012 | UC-002 | CAP-002 |
| SYS-013 | UC-002 | CAP-002 |
| SYS-014 | UC-002 | CAP-002 |
| SYS-015 | UC-002 | CAP-002 |
| SYS-016 | UC-002 | CAP-002 |
| SYS-017 | UC-002 | CAP-002 |
| SYS-018 | UC-002 | CAP-002 |
| SYS-019 | UC-002 | CAP-002 |
| SYS-020 | UC-002 | CAP-002 |
| SYS-021 | UC-002 | CAP-002 |
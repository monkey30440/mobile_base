# System Requirements

## CAP-001 建立可重複使用之地圖

### SYS-001 建圖模式

系統提供建圖模式，供使用者執行環境建圖。

**Traceability**

- CAP-001

---

### SYS-002 手動控制

系統提供鍵盤控制介面，供使用者控制 AMR 移動。

**Traceability**

- CAP-001

---

### SYS-003 雷射資料

系統接收 LiDAR 掃描資料，作為建圖輸入。

**Traceability**

- CAP-001

---

### SYS-004 IMU 資料

系統接收 IMU 資料，作為建圖輸入。

**Traceability**

- CAP-001

---

### SYS-005 底盤里程資訊

系統提供 AMR 運動資訊，作為建圖輸入。

**Traceability**

- CAP-001

---

### SYS-006 地圖建立

系統建立 Occupancy Grid 地圖。

**Traceability**

- CAP-001

---

### SYS-007 地圖儲存

系統提供地圖儲存功能，產生：

- `map.yaml`
- `map.pgm`

**Traceability**

- CAP-001

---

### SYS-008 地圖重用

系統提供已建立地圖，供定位與導航使用。

**Traceability**

- CAP-001

## CAP-002 導航至指定路網站點

### SYS-009 地圖載入

系統載入 UC-001 建立之二維地圖，作為定位與導航基準。

**Traceability**

- CAP-002

---

### SYS-010 路網載入

系統載入路網站點與連線資料，供站點查詢與路徑規劃使用。

**Traceability**

- CAP-002

---

### SYS-011 AMR 定位

系統提供 AMR 於地圖座標系中的目前位姿。

**Traceability**

- CAP-002

---

### SYS-012 目標站點輸入

系統提供終端介面，供使用者指定目標站點。

**Traceability**

- CAP-002

---

### SYS-013 站點解析

系統將目標站點轉換為對應之地圖位姿與路網節點。

**Traceability**

- CAP-002

---

### SYS-014 導航路徑產生

系統依 AMR 目前位姿、目標站點、地圖與路網資料產生可執行之移動路徑。

路徑可由 First Mile、On Route 與 Last Mile 導航區段組成。

**Traceability**

- CAP-002

---

### SYS-015 自主移動

系統依移動路徑控制 AMR 完成平面移動與轉向。

**Traceability**

- CAP-002

---

### SYS-016 目標站點抵達

系統判定 AMR 位姿符合目標站點之位置與朝向允收範圍。

**Traceability**

- CAP-002

---

### SYS-017 任務狀態

系統提供路網站點移動任務之執行狀態與完成結果。

**Traceability**

- CAP-002
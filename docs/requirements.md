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
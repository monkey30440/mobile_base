# System Architecture

## CAP-001 建立可重複使用之地圖

### 架構目標

系統整合底盤控制、環境感知、運動估測與建圖功能，支援使用者以鍵盤控制 AMR 完成二維地圖建立與儲存。

---

### 系統組成

| 子系統 | 職責 | 對應需求 |
|---|---|---|
| 操作介面 | 接收鍵盤操作並產生速度命令 | SYS-001、SYS-002 |
| 底盤控制 | 執行速度命令並提供底盤運動資訊 | SYS-005 |
| LiDAR 感知 | 提供環境雷射掃描資料 | SYS-003 |
| IMU 感知 | 提供角速度與線性加速度資料 | SYS-004 |
| 運動估測 | 整合底盤、LiDAR 與 IMU 資訊，提供連續運動估測 | SYS-003、SYS-004、SYS-005 |
| 建圖 | 依雷射掃描與運動估測建立 Occupancy Grid | SYS-001、SYS-006 |
| 地圖儲存 | 將建圖成果儲存為地圖設定檔與影像檔 | SYS-007、SYS-008 |

---

### 邏輯架構

```mermaid
flowchart LR
    User[使用者]
    Teleop[操作介面]
    Base[底盤控制]
    LiDAR[LiDAR 感知]
    IMU[IMU 感知]
    Motion[運動估測]
    SLAM[建圖]
    Storage[地圖儲存]

    User --> Teleop
    Teleop -->|速度命令| Base

    Base -->|底盤運動資訊| Motion
    LiDAR -->|雷射掃描| Motion
    IMU -->|慣性資料| Motion

    LiDAR -->|雷射掃描| SLAM
    Motion -->|運動估測| SLAM

    SLAM -->|Occupancy Grid| Storage
    Storage -->|map.yaml / map.pgm| MapFiles[地圖檔案]
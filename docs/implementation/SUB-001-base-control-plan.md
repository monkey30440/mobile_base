# SUB-001 Base Control — Implementation Plan

`SUB-001 Base Control` 之實作計畫。

正式規格以 `../05_subsystem.md` § SUB-001 為 Single Source of Truth，本文件不重複定義需求或介面。

| Requirement | Subsystem |
|---|---|
| SYS-022 | SUB-001 |

---

## 範圍

實作 ros2_control `hardware_interface::SystemInterface` 插件，涵蓋：

- RS-485 Multi-drive 2.0 通訊。
- 驅動器組態驗證與激磁生命週期。
- 編碼器解碼、turns 繞回處理、輪端單位換算。
- 匯出輪端 state／command interfaces。
- 驅動器診斷發布。

不涵蓋：差速運動學與里程（SUB-004，`diff_drive_controller` 組態）、
LiDAR / IMU 感知（SUB-002 / SUB-003）。

前提：開發／執行環境已完成（見 `dev-environment-plan.md`）。

---

## 已驗證之通訊協議

下列參數於 2026-08-07 以 Python 原型於實機驗證，**與實作語言無關，可直接沿用**：

| 項目 | 值 |
|---|---|
| Port / 框架 | `/dev/ttyUSB0`，230400 8N1（FTDI FT232） |
| Driver ID | 右輪 = 1，左輪 = 2 |
| 個別驅動器存取 | FC03 讀 / FC06 寫 |
| 群組讀寫 | FC17h，群組位址 `0x65` |
| FC17h 定址 | R_ADDR `0xF003` / R_CNT 16、W_ADDR `0xF803` / W_CNT 4 |
| 回應排列 | driver-major，每驅動器 8 words（7 資料 + Error_Check） |
| Read index | 0=狀態 1=警報 2=轉速 5=位置(turns) 6=位置(pulse) |
| Write index | 8=Multi-Drive Lite 指令 9=速度（signed RPM） |
| 控制字 | NET-IN `0x1400`，SERVO-EN=bit7、FREE=bit6 |
| 驅動器組態 | `02-14`=0、`01-06`=2500、`09-26`=0、`05-03`=2（兩顆一致） |
| 過速警報門檻 | `05-04`=4300 RPM；無載全轉速 `01-04`=4188 RPM |
| 單次交易耗時 | 約 10~15 ms（FT232 latency timer 主導） |

### 已釐清之關鍵行為

- **Encoder 位置格式**：`02-14 = 0` 為 Index(turns) + pulse，
  正確解碼為 `turns × (01-06 × 4) + pulse`；
  既有專案 `ref/base_motor_controller` 假設 `02-14 = 1`（32-bit 步數）而解碼錯誤。
- **turns 繞回**：signed 16-bit，`05-03 = 2` 關閉 Overflow 保護故靜默繞回，
  約 823 m（0.5 m/s 約 27 分鐘）觸發，必須由軟體累加處理。
- **關閉安全**：解除激磁須逐顆獨立重試；
  中斷於交易途中會使半雙工匯流排失去同步，關閉前須排空緩衝。
- **轉速上限**：`max_motor_rpm` 應設 4000（= 4188 × 95%），
  低於物理極限與過速警報門檻。

---

## 架構決策：採用 ros2_control

原 Python 實作（`src/base_control`，2026-08-07 完成並於架高驗證通過）
自行實作了差速運動學、控制迴圈與 `/cmd_vel` 介面。

依 Mature Solution First 原則改採 ros2_control：

| 項目 | 原實作 | ros2_control |
|---|---|---|
| 差速運動學 | 自訂 `kinematics.py` | `diff_drive_controller` |
| 里程積分 | 待 SUB-004 自訂 | `diff_drive_controller` |
| 控制迴圈排程 | 自訂 timer | `controller_manager` |
| 輪端狀態發布 | 自訂 `/wheel_states` | `joint_state_broadcaster` |
| Vehicle Geometry | SUB-001 與 SUB-004 各自宣告 | 集中於 `diff_drive_controller` |
| M1 協議 | 自訂 | **維持自訂**（框架未涵蓋） |

效益：消除參數重複、移除自訂運動學與里程程式碼、取得速度限制與
odometry covariance 等既有能力。

代價：hardware interface 須以 C++ 實作（ros2_control 無穩定 Python 支援）。

---

## 實作策略

### Stage A — 前置驗證（已完成 2026-08-07）

base image 未預裝 ros2_control（僅 `pluginlib`），已確認可經 apt 取得：

- [x] `ros-jazzy-ros2-control` 4.45.2、`ros-jazzy-ros2-controllers` 4.40.1 安裝成功。
- [x] `controller_manager`、`hardware_interface`、`controller_interface`、
      `diff_drive_controller`、`joint_state_broadcaster` 皆可見。
- [x] C++ 開發標頭與 CMake config 齊備
      （`system_interface.hpp`、`hardware_info.hpp`、`hardware_interfaceConfig.cmake`）。
- [x] `Dockerfile` 更新後 `docker compose build` 通過，全新容器驗證元件可用。

**架構決策成立，可繼續 Stage B。**

#### Stage A 之驗證缺口（2026-08-07 於 Stage C 發現）

上述驗證僅確認套件「可安裝、可見、可編譯」，**未確認 `ros2_control_node` 可實際執行**。

Stage C 實機測試時 `ros2_control_node` 於載入插件前即以 exit 127 死亡：

```text
symbol lookup error: libpal_statistics_msgs__rosidl_typesupport_fastrtps_cpp.so:
undefined symbol: _ZN8eprosima7fastcdr3Cdr9serializeEj
```

根因為 base image 之 ROS 快照（2026-01）與 packages.ros.org（2026-06）
相差約 5 個月，共 197 個 ros-jazzy 套件版本落後，
其中 Fast-CDR、Fast-DDS、rmw、rosidl 等通訊層不一致。

處置見「Stage C 之環境對齊」。

**教訓**：外部相依之驗證須包含「實際執行」，
僅確認安裝與編譯不足以證明可用。


### Stage B — SUB-012 Robot Description

ros2_control 需要 URDF 提供 joint 定義與硬體介面描述。
本階段實作 **SUB-012 Robot Description**（規格見 `05_subsystem.md`）。

來源：`ref/FIH_AMR_ROBOT_V2.0_0731`（完整人形 AMR，84 links）。
meshes 可直接沿用，URDF 須裁剪並調整。

- [x] 建立 `mobile_base_description` 套件，複製所需 meshes（84 → 24 個）。
- [x] 裁剪 URDF：84 → 25 links（移除軀幹、雙臂、雙手、頭部共 60 links）。
- [x] 補上 `base_footprint`（z = 0.256 m，由輪心 0.176 + 輪半徑 0.08 推得）。
- [x] 被動關節（caster ×16、懸吊 ×2）改為 `fixed`，僅驅動輪維持 `continuous`。
- [x] 加入 `<ros2_control>` 區段，宣告 `base_control/BaseControlHardware`。
- [x] `robot_state_publisher` 發布完整 TF tree，零錯誤零警告。

驗證結果（2026-08-07）：

- `check_urdf`：單一樹，root `base_footprint`，25 links 無斷點。
- `/tf_static` 22 筆；送入 `/joint_states` 後 `/tf` 出現兩個驅動輪轉換。
- xacro 於 `use_ros2_control` true／false 皆可解析。

#### 命名處置

URDF 既有名稱不予改動，改由規格配合 URDF：

| 項目 | 採用（來源 URDF） | 原規格 |
|---|---|---|
| LiDAR frame | `base_lidar_link_FL` / `_BR` | ~~front/rear_laser_frame~~ |
| IMU frame | `base_imu_link` | ~~imu_link~~ |
| 輪關節 | `driving_wheel_joint_L` / `_R` | ~~left/right_wheel_joint~~ |

Topic 名稱不在此限，採 `/scan_front_left`、`/scan_back_right`。

`base_footprint` 為新增連桿（來源 URDF 未定義），不涉及更名。

LiDAR 對角安裝（前左、後右）已確認並全面回寫規格。
URDF 幾何推算輪距 0.5545 m，與 Baseline 0.555 m 相符。

### Stage C — Hardware Interface 插件

依已驗證之協議以 C++ 實作：

1. Modbus Transport：以 **libmodbus** 實作 RS-485 通訊。
2. Driver Interface：寄存器語意、組態驗證、激磁、警報。
3. Encoder Decoder：turns 繞回累加、輪端單位換算。
4. `SystemInterface` 實作：`on_init` / `on_configure` / `on_activate` /
   `on_deactivate` / `read` / `write`，並以 pluginlib 匯出。
5. Diagnostics：`/driver/status`。

### Stage D — 控制器組態（SUB-004）

- [ ] `diff_drive_controller` 參數檔（wheel_radius、wheel_separation、
      速度限制、`enable_odom_tf: false`、odometry remap 至 `/wheel_odom`）。
- [ ] `joint_state_broadcaster` 組態。
- [ ] Launch 整合。

### Stage E — 實機驗證

依 `05_subsystem.md` SUB-001 與 SUB-004 驗證項目逐項確認。

---

## 舊實作處置

`src/base_control`（Python）於 Stage C 完成並通過驗證後移除。
在此之前保留，作為協議行為之對照基準。

`src/stage1_md2_probe.py` 保留為維護工具（唯讀診斷用途）。

---

## 已決事項

0. **Modbus 實作採 libmodbus**（`libmodbus-dev` 3.1.10，apt 可取得）。
   已驗證涵蓋所需 API：`modbus_new_rtu`、`modbus_set_slave`、
   `modbus_write_and_read_registers`（FC17h，`write_addr` 與 `read_addr` 可分開指定）、
   `modbus_read_registers`、`modbus_write_register`、`modbus_set_response_timeout`。
   理由：CRC、RTU 框間延遲與 partial read 為易錯處，
   Python 版已於此踩過一次（中斷造成半雙工失去同步），改用成熟實作。

1. **Encoder 解碼**：維持驅動器出廠預設 `02-14 = 0`，軟體解碼為
   `turns × (01-06 × 4) + pulse`。驅動器端不做持久化設定。
   啟動時驗證 `02-14` 與 `01-06`，不符即回報組態錯誤。
2. **turns 繞回**：採「原始值 + 累計補償量」而非逐次累加差值，
   使偶發異常讀值僅造成單次尖峰而不永久污染位置。
3. **max_motor_rpm**：4000。
4. **子系統劃分**：SUB-001 為 hardware interface，
   SUB-004 更名為 Differential Drive Controller 並持有 Vehicle Geometry。

---

## 待決事項

- **警報回復機制**：目前僅偵測警報並停止送命令，無回復出口。
  建議提供 alarm reset service，否則任何暫態警報須重啟。
  驗證方式：暫時寫入 `05-04` RAM 位址 `0x4103` 降低過速門檻以誘發 alarm 12，
  測畢寫回或斷電還原（RAM 位址不持久，不違反「不做持久化設定」原則）。
- **`/cmd_vel` 訊息型別**：`diff_drive_controller` 於 Jazzy 之
  `TwistStamped` 與 `Twist` 設定，須與 Nav2 輸出對齊。
- **Vehicle Parameters 實機量測**：目前沿用 Baseline 值，未量測。

---

## 狀態

- [x] Design Baseline reviewed（ros2_control 架構已回寫規格）
- [x] Stage A 前置驗證（2026-08-07）
- [x] Stage B SUB-012 Robot Description（2026-08-07）
- [ ] Stage C Hardware Interface
- [ ] Stage D 控制器組態
- [ ] Stage E 實機驗證
- [ ] Feature Freeze

---

## 完成後之文件更新

- [ ] `05_subsystem.md`：標記 SUB-001 / SUB-004 驗證項目結果。
- [ ] `README.md`：更新里程碑與 Repository 樹狀圖。
- [ ] 實作發現與規格不符時，先修正 `05_subsystem.md` 再繼續實作。

# SUB-001 Base Control — Implementation Plan

`SUB-001 Base Control` 之實作計畫。

正式規格以 `../05_subsystem.md` § SUB-001 為 Single Source of Truth，本文件不重複定義需求或介面。

| Requirement | Subsystem |
|---|---|
| SYS-022 | SUB-001 |

---

## 範圍

涵蓋：

- 接收 `/cmd_vel` 並執行差速輪運動學計算。
- 透過 RS-485 / Modbus Multi-drive 2.0 控制左右輪驅動器。
- 讀取左右輪回授並發布 `/wheel_states`、`/driver/status`。

不涵蓋（另開計畫）：Wheel Odometry 計算（SUB-004）、LiDAR / IMU 感知（SUB-002 / SUB-003）。

前提：開發／執行環境已完成（見 `dev-environment-plan.md`）。

---

## 已驗證之通訊協議

2026-08-07 於實機（車輛架高）完成 Stage 1，下列參數皆為實測確認：

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
| 驅動器組態 | `02-14`=0、`01-06`=2500、`09-26`=0（兩顆一致） |

Vehicle Parameters（Wheel Radius、Wheel Separation、Gear Ratio）仍為既有 Baseline 推定值，待 Stage 3 實機量測。

---

## 與既有 Baseline 之差異

**Encoder 位置解碼**：既有實作 `ref/base_motor_controller` 以 `s32_from_hi_lo(hi, lo) = hi<<16 | lo` 組合 Read index 5/6，此解碼對目前驅動器組態不成立。

實機量測：index 6 於 10000 歸零、index 5 同時 +1，`hi<<16|lo` 每圈產生約 +57000 之不連續跳變。手冊參數 `02-14 位置命令格式` 說明：

- `0`（目前值）：Index(turns) + pulse，-32768~+32767 turns、0~10000 pulse
- `1`：Step(上位) + Step(下位)，32-bit 連續步數

即既有實作假設 `02-14 = 1`，而兩顆驅動器實際皆為預設值 `0`。正確解碼為 `turns × 10000 + pulse`，經 6 圈連續量測驗證跨圈無不連續。

此差異直接影響 SUB-004 Wheel Odometry，處置方式見下方「待決事項」。

---

## 實作策略

採風險優先之分階段實作，每階段完成並驗證後才進入下一階段。前一階段否證假設時，先修正 `05_subsystem.md` 規格再繼續。

### Stage 1 — 通訊驗證（已完成）

以拋棄式腳本 `src/stage1_md2_probe.py` 於實機驗證，不建立 package 結構。

結果：

- FC03 唯讀：兩顆驅動器皆回應，alarm=0。
- FC17h 群組讀寫：定址與 Register Map 確認，單次交易約 10~12 ms。
- 單輪轉動：左右輪各自獨立轉動，命令 60 RPM、回授 57~61 RPM，另一輪維持 0。
- Encoder 解碼方式修正（見「與既有 Baseline 之差異」）。

腳本於 Stage 2 完成後刪除。

### Stage 2 — `base_control` package（已完成）

依 `05_subsystem.md`「軟體組成」建立 `src/base_control`（ament_python）：

| 模組 | 職責 |
|---|---|
| `md2_transport.py` | Modbus RTU 封包、CRC、序列埠收發 |
| `driver_interface.py` | 驅動器暫存器語意、組態驗證、激磁、警報 |
| `kinematics.py` | 車體 ↔ 輪端 ↔ 馬達端換算、方向修正、轉速限制 |
| `params.py` | ROS 參數宣告與驗證 |
| `node.py` | ROS node、控制迴圈、Diagnostics |

不建立自定義訊息型別，`/wheel_states` 用 `sensor_msgs/JointState`、
`/driver/status` 用 `diagnostic_msgs/DiagnosticArray`。

實機驗證結果（2026-08-07，車輛架高）：

- 啟動時由 `01-06` 推導每馬達轉 10000 counts，組態驗證通過。
- 控制迴圈穩定 50 Hz（設定 20 ms），單次交易約 15.5 ms。
- 運動學換算與手算相符：直行 0.5 m/s → 1194 RPM（理論 1193.66）；
  超速時兩輪等比縮放，輪速比 2.4256（期望 2.4261）。
- 直行 0.05 m/s：左右輪回授 0.618~0.628 rad/s（理論 0.625）。
- 原地旋轉 0.2 rad/s：左 −0.691、右 +0.681~0.691 rad/s（理論 ±0.694）。
- `/cmd_vel` 逾時自動停止；節點關閉時停止並解除激磁，驅動器回到 `WAIT/INHIBIT`。

### Stage 3 — 實機驗證與參數確認

- 完成下方驗證計畫全部項目。
- 以實機量測確認 Vehicle Parameters，取代 Baseline 推定值。

---

## 已決事項

1. **Encoder 解碼**：維持驅動器出廠預設 `02-14 = 0`，由軟體解碼為 `turns × 10000 + pulse`。
   驅動器端不做任何持久化設定，行為完全由 repo 決定，更換驅動器可直接使用。
   啟動時須讀取 `02-14` 與 `01-06` 驗證：`02-14` 非 0 則視為組態錯誤並回報；
   每轉步數由 `01-06 × 4` 推導，不寫死 10000，避免更換不同解析度編碼器時產生無聲誤差。

2. **FTDI latency timer**：不調整。Stage 2 實測控制迴圈於 20 ms（50 Hz）穩定運作，
   單次交易約 15.5 ms，佔週期約 78%，滿足目前需求。
   若後續需高於 50 Hz，再評估調整
   `/sys/bus/usb-serial/devices/ttyUSB0/latency_timer`。

未驗證項目（Stage 2/3 處理）：encoder 反向轉動、turns 於 ±32768 之溢位行為、警報處理路徑。

---

## 驗證計畫

對應 `05_subsystem.md` SUB-001「驗證項目」：

- [x] Driver 通訊：可建立 RS-485 通訊
- [x] Driver 控制：左右輪可獨立控制
- [ ] 差速控制：AMR 可完成直行與原地旋轉
      — 輪端行為已驗證（架高），落地實際行駛待 Stage 3
- [x] Wheel Feedback：可持續取得左右輪回授（50 Hz）
- [x] `/cmd_vel`：底盤可正確執行速度命令
- [ ] 長時間運轉：建圖與導航期間持續穩定運作

---

## 狀態

- [x] Design Baseline reviewed（`05_subsystem.md` SUB-001、SYS-022）
- [x] Stage 1 通訊驗證（2026-08-07）
- [x] Stage 2 `base_control` package（2026-08-07，架高驗證）
- [ ] Stage 3 落地實機驗證與 Vehicle Parameters 量測
- [ ] Feature Freeze

---

## 完成後之文件更新

- [ ] `05_subsystem.md`：標記 SUB-001 驗證項目結果；Vehicle / Driver Parameters 以實機值取代 Baseline 推定值。
- [ ] `README.md`：更新里程碑與 Repository 樹狀圖（`src/` 結構）。
- [ ] 實作發現與規格不符時，先修正 `05_subsystem.md` 再繼續實作。

# SUB-001 Base Control — Implementation Plan

本文件為 `SUB-001 Base Control` 之實作計畫，非正式規格文件。

正式規格以 `../05_subsystem.md`（SUB-001 章節）為 Single Source of Truth，本文件僅記錄「如何實作」與實作進度，不重複定義需求或介面。

---

## Traceability

| Requirement | Subsystem | 本計畫 |
|---|---|---|
| SYS-022 | SUB-001 | 本文件 |

對應規格：`docs/05_subsystem.md` § SUB-001 Base Control。

---

## 範圍 (Scope)

本次實作僅涵蓋 SUB-001 自身職責：

- 接收 `/cmd_vel` 並執行差速輪運動學計算。
- 透過 RS-485 / Modbus Multi-drive 2.0 控制左右輪驅動器。
- 讀取左右輪回授並發布 `/wheel_states`、`/driver/status`。

不包含（屬其他 SUB，另開計畫）：

- Wheel Odometry 計算（SUB-004）。
- LiDAR / IMU 感知（SUB-002 / SUB-003）。

---

## 現況 (Current State)

- `src/` 尚無任何 ROS 2 package。
- `Dockerfile`、`compose.yaml` 為空檔案，開發／執行環境尚未定義。
- 硬體依 05_subsystem.md 系統邊界：Jetson AGX Orin、DEXMART M1C-N016RE ×2、RS-485、Modbus Multi-drive 2.0、`/dev/ttyUSB0`。

---

## 實作項目 (Planned Work Items)

依 05_subsystem.md「軟體組成」規劃之 `base_control` package：

1. ROS 2 package 骨架（`base_control`）。
2. Modbus Transport：RS-485 通訊、Modbus Multi-drive 2.0 協議串接。
3. Driver Interface：左右輪驅動器控制與狀態讀取。
4. Differential Kinematics：`/cmd_vel` → 左右輪目標速度、左右輪回授 → 運動資訊。
5. Parameter Manager：Vehicle Parameters（Wheel Radius / Wheel Separation / Gear Ratio）、Driver Parameters。
6. Diagnostics：`/driver/status` 發布。
7. Launch 設定。

---

## 待實機確認事項 (Open Items)

沿用 05_subsystem.md 已標註之未定事項，實作時不得假設，須於 Hardware Bring-up 後確認：

- Driver Register、Control Word、Status Word（依 DEXMART 官方文件初版設定）。
- Vehicle Parameters（Wheel Radius、Wheel Separation、Gear Ratio）：初版沿用既有 Baseline。
- Driver Parameters（Baud Rate、Control Mode、Encoder Resolution、Maximum Motor RPM、Acceleration、Deceleration、Torque Limit）。

---

## 驗證計畫 (Verification Plan)

對應 05_subsystem.md SUB-001「驗證項目」表，逐項於 Hardware Verification 階段勾選：

- [ ] Driver 通訊：可建立 RS-485 通訊
- [ ] Driver 控制：左右輪可獨立控制
- [ ] 差速控制：AMR 可完成直行與原地旋轉
- [ ] Wheel Feedback：可持續取得左右輪回授
- [ ] `/cmd_vel`：底盤可正確執行速度命令
- [ ] 長時間運轉：建圖與導航期間持續穩定運作

---

## 狀態 (Status)

- [x] Design Baseline reviewed（05_subsystem.md SUB-001、SYS-022 已確認）
- [ ] Implementation
- [ ] Hardware Verification
- [ ] Feature Freeze

---

## 完成後之文件更新清單 (Closure Checklist)

實作與驗證完成、進入 Feature Freeze 前，須回寫下列文件以完成閉環，之後本計畫文件可歸檔或刪除：

- [ ] `05_subsystem.md`：SUB-001「驗證項目」逐項標記已驗證結果；若 Vehicle Parameters／Driver Parameters 由 Baseline 值改為實機量測值，更新「系統參數」。
- [ ] `README.md`：里程碑表更新 CAP-001 進度；若新增 `src/` 結構，更新 Repository 樹狀圖。
- [ ] 若實作過程發現 05_subsystem.md 規格與實際硬體行為不符，先修正規格（Design Baseline），再繼續實作，不得讓程式碼與文件各自為政。

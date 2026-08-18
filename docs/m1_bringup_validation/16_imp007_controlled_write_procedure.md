# IMP-007 Controlled Write Validation Procedure

本文件定義 `docs/07_implementation_checklist.md` 第 7 項 S7 `M1Driver` transport vertical slice 的 Level 3（零速意圖控制寫入）與 Level 4（受控短時運動）驗證規範、安全限制與程序。

> [!CAUTION]
> **SAFETY GATE: ALL REAL-HARDWARE WRITE/CONTROL OPERATIONS REQUIRE EXECUTION-TIME OPERATOR AUTHORIZATION**
> 本程序中所有帶有 `--execute` 標籤的真實硬體指令，**嚴禁在未經操作人員當下明確授權與在場監控的情況下執行**。

---

## 1. Process-Crash Hazard 與 Level 4 BLOCKED 宣告

### 1.1 Process-Crash Hazard 分析
- `m1_control_check` 內的運動持續時間計時器（Duration timer）與運動結束後的自動停機流程（`stop()` → `read_state()` → `disable()`）**完全運行於 Host Process 空間，並非獨立於 Process 的硬體安全保證**。
- **危險情境**：若 `m1_control_check` 在發出非零 `JG` 速度命令後發生 Process Crash、`SIGKILL`、Segmentation Fault、Host 斷網或 Hang，**後續的軟體 `stop()` 與 `disable()` 流程將完全無法執行**，M1 驅動器將持續以最後接收之速度命令運轉，直到外力介入。
- **目前基線現狀**：目前 repository 尚未完成並核准任何獨立於 Host Process 運動命令迴圈之硬體 Fail-safe 機制（例如經完整時序量測與觸發驗證之 M1 通訊 Watchdog 或認證安全控制器）。

### 1.2 Level 4 狀態宣告：BLOCKED
基於上述 Process-Crash Hazard，**Level 4 Bounded Exchange Motion 實機驗證目前標記為 `BLOCKED`**，直到至少有一個獨立於 motion loop 的 fail-safe 停機機制獲得權威證據與實測證明為止。

---

## 2. Level 3 術語定義與語意邊界

Level 3 涉及的寫入操作（`enable`, `stop`, `disable`）統稱為 **Zero-Speed-Intent Control Write（零速意圖控制寫入）**，不得稱為「保證無運動寫入（no-motion write）」：

- **`enable()` (SVON `0x0006`)**：
  - **語意**：向驅動器發送使能命令，將驅動器狀態轉入 Servo-On。
  - **物理影響**：馬達將產生保持阻抗（Holding Torque），雖未下發旋轉速度，但已改變驅動器動力輸出狀態。
- **`stop()` (JG `0x0001` with 0 RPM)**：
  - **語意**：向驅動器下發 0 RPM 速度命令。
  - **語意邊界**：僅表達「零速命令意圖」，**絕非經認證之安全停機（Certified Safety Stop）**；若通訊中斷或驅動器異常，不保證物理煞停。
- **`disable()` (SVOFF `0x0007`)**：
  - **語意**：向驅動器發送釋放使能命令。
  - **物理影響**：驅動器釋放激磁，馬達進入自由滑行（Coasting）狀態，其物理阻尼與慣性需在實機驗證。

---

## 3. M1 Communication Watchdog 規格與四層狀態審查

為確保任何通訊防護宣告具備精確可審查之追溯性，此處將 M1 通訊 Watchdog 依據權威手冊章節、實機觀測、實體行為驗證與安全認證四層狀態嚴格區分（**本次僅作技術架構審查與文件化，未對實機寫入任何參數**）：

### 3.1 Authoritative Manual Sources
1. **通訊手冊 (Communication Manual)**：
   - **文件名稱**：*M1 驅動器通訊說明書 (Model: M1)*
   - **文件編號**：`SS-01-S0647`（檔案標記 `UM-01-S0686`）
   - **版本 / 發行日期**：Revision `1.1`，`3 February 2025`
   - **發行者**：創盟電子工業股份有限公司 (DEXMART Technology Corporation)
   - **總頁數**：45 頁
2. **使用手冊 (User Manual)**：
   - **文件名稱**：*M1系列直流無刷馬達驅動器使用手冊 (Model: M1)*
   - **文件編號**：`UM-01-S0701`
   - **發行者**：創盟電子工業股份有限公司
   - **總頁數**：23 頁

---

### 3.2 四層狀態分析表 (4-Tier Status Matrix)

| 項目 | 暫存器 (EEP/RAM) | A. Manual-Defined 官方定義 (附 exact section & page) | B. Current-Device 實機現況 (Observed) | C. Hardware-Verified 行為驗證 | D. Safety Qualification 安全認證 |
|---|---|---|---|---|---|
| **通訊逾時時間** | `05-17` (`0510h` / `4110h`) | **手冊定義**：單位 ms，範圍 0–65535，預設 0（無效/無監視）。當間隔時間超過設定值時啟動通訊異常保護。<br>**出處**：`SS-01-S0647` Rev 1.1 §2 (Tb1, p.2), §3.4.4 (p.19)。生效模式 C（執行 Configuration 後反映）。 | **`0` (DISABLED)** 於 ID1 與 ID2（依 `logs/manual/config.txt` 與 Level 2 實機唯讀掃描）。 | **UNVERIFIED** (IMP-007 未執行實機 watchdog trip 驗證)。 | **NOT ESTABLISHED** (非 certified safety function / STO)。 |
| **通訊錯誤門檻** | `05-18` (`0511h` / `4111h`) | **手冊定義**：單位 次，範圍 0–10，預設 0（無效）。RS485 通訊異常超過此設定值啟動通訊異常保護。<br>**出處**：`SS-01-S0647` Rev 1.1 §3.4.4 (p.19)。生效模式 C。 | **`0`** 於 ID1 與 ID2。 | **UNVERIFIED**。 | **NOT ESTABLISHED**。 |
| **通訊保護行為** | `05-21` (`0514h` / `4114h`) | **手冊定義**：預設 0。<br>`0`: 報警停機；<br>`1`: 遠端(虛擬)I/O 狀態清除；<br>`2`: 報警停機 + 遠端(虛擬)I/O 狀態清除。<br>**出處**：`SS-01-S0647` Rev 1.1 §3.4.4 (p.19)。生效模式 C。 | **`0`** 於 ID1 與 ID2。 | **UNVERIFIED**。 | **NOT ESTABLISHED**。 |
| **參數重新計算與生效 (Configuration)** | `0A27h` | **手冊定義**：維修/維護命令寄存器，寫入 `1` 執行 Configuration 指令，使模式 C 參數生效。<br>**出處**：`SS-01-S0647` Rev 1.1 §3.2 (p.9)。*(註：手冊中無 10-39 暫存器，生效指令為 0A27h)*。 | 未在 IMP-007 執行寫入。 | **UNVERIFIED**。 | **NOT ESTABLISHED**。 |
| **報警代碼 (通訊逾時)** | 報警位址 `0003h` | **手冊定義**：錯誤碼 `21`，保護功能名稱「通訊指令錯誤」，說明「RS232 或 RS485 通訊逾時」。<br>**出處**：`SS-01-S0647` Rev 1.1 §A1 (p.45) 與 `UM-01-S0701` §7 (p.23)。*(註：非臆測之 Er.140，官方標準錯誤碼為 21)*。 | 目前狀態正常（Alarm = 0）。 | **UNVERIFIED** (歷史測試曾觀察到 Alarm 21，但未建立 IMP-007 baseline)。 | **NOT ESTABLISHED**。 |
| **遠端虛擬 I/O 清除 (NET-IN)** | `1400h` | **手冊定義**：Bit 7 為 `NET-X7`，功能對應 `SERVO-EN` (Function 14)。當 `05-21=1/2` 觸發時清除虛擬 I/O，使馬達失能。<br>**出處**：`SS-01-S0647` Rev 1.1 §3.1 (p.8), §3.4.5 (p.20)。 | 正常運作下為 `0x0000` (Servo-Off)。 | **UNVERIFIED**。 | **NOT ESTABLISHED**。 |
| **解除報警 (Alarm Reset)** | `0A00h` | **手冊定義**：寫入 `1` 執行報警解除。手冊註明若驅動器處於可運轉狀態無法解除，且部分故障需斷電重啟。<br>**出處**：`SS-01-S0647` Rev 1.1 §3.2 (p.8), §A1 (p.44)。 | 未在 IMP-007 執行寫入。 | **UNVERIFIED** (歷史測試曾觀察到通訊逾時報警後無法僅藉軟體 0A00h 清除，需重啟電源)。 | **NOT ESTABLISHED**。 |

---

## 4. Best-Effort Cleanup 語意邊界

- 在 `m1_control_check` 執行過程中（包括 `--op exchange`），若任一週期發生通訊逾時或錯誤，Harness 將嘗試發送 `stop()` 與 `disable()`。
- **語意邊界**：此清理程序屬於 **Best-Effort（盡力而為）**。
- **嚴格宣告**：若發生通訊中斷，軟體清理指令本身可能無法成功送達驅動器。**Best-Effort Cleanup 絕對不能保證馬達已處於安全狀態**；當清理失敗時，Harness 將輸出嚴重警告，操作人員必須立即採取實體斷電處置。

---

## 5. Physical Preflight Checklist (依 §6.3 規範)

在執行任何 Level 3 指令前，操作人員必須在現場逐項確認下列條件：

- [ ] **Target Device 唯一性確認**：確認 `/dev/ttyUSB0` 為唯一的 M1 RS-485 轉接器，ID 1 為右輪，ID 2 為左輪。
- [ ] **實體斷電路徑待命**：物理電源隔離／緊急停止開關（E-Stop / Power Isolation Switch）必須事前確認處於可立即操作狀態；測試全程操作人員必須在場且手部可直接觸及開關，不預設任何固定反應時間安全上限。
- [ ] **車體架高脫離地面**：驅動輪必須完全懸空架高，確認輪胎旋轉時不會造成車體移動或接觸任何物體。
- [ ] **受控區域淨空**：車體周圍無雜物與非測試人員。
- [ ] **通訊健全性已驗證**：已完成 Level 2 唯讀測試（FC03 `read_state` 正確且無 Alarm）。

---

## 6. Step-by-step Execution Sequence

### Step 0: Command Preview (Dry-Run)
```bash
./install/mobile_base_control/lib/mobile_base_control/m1_control_check --dry-run --op enable
./install/mobile_base_control/lib/mobile_base_control/m1_control_check --dry-run --op stop
./install/mobile_base_control/lib/mobile_base_control/m1_control_check --dry-run --op disable
```

---

### Step 1: Pre-operation State Read (Level 2 Baseline)
```bash
./install/mobile_base_control/lib/mobile_base_control/m1_control_check --execute --op read
```
- **Expected State Before**：Status = 6 (WAIT/INHIBIT), Alarm = 0, RPM = 0.
- **Abort Condition**：Alarm != 0 或通訊逾時。

---

### Step 2: Servo Enable (Level 3 Zero-Speed-Intent Control Write)
> **REQUIRES EXECUTION-TIME OPERATOR AUTHORIZATION**
```bash
./install/mobile_base_control/lib/mobile_base_control/m1_control_check --execute --op enable
```
- **Expected State Before**：Status = 6, Alarm = 0.
- **Expected Observation**：
  - 驅動器接收 Multi-drive 2.0 FC17 (SVON `0x0006`)。
  - 馬達鎖定（產生保持阻抗），但無旋轉運動，回授 RPM = 0。
  - Status 轉為使能狀態（Status & 0x0001 != 0），Alarm = 0。
- **Abort Condition**：馬達產生非預期旋轉、發出異音、Alarm != 0 或通訊失敗。
- **Emergency Stop Path**：立即手動切斷實體電源。

---

### Step 3: Stop Primitive (Level 3 Zero-Speed-Intent Control Write)
> **REQUIRES EXECUTION-TIME OPERATOR AUTHORIZATION**
```bash
./install/mobile_base_control/lib/mobile_base_control/m1_control_check --execute --op stop
```
- **Expected State Before**：Servo Enabled.
- **Expected Observation**：
  - 驅動器接收 Multi-drive 2.0 FC17 (JG `0x0001` with 0 RPM)。
  - 回授 Actual RPM = 0。
- **Abort Condition**：通訊失敗或 Alarm != 0。

---

### Step 4: Servo Disable (Level 3 Zero-Speed-Intent Control Write)
> **REQUIRES EXECUTION-TIME OPERATOR AUTHORIZATION**
```bash
./install/mobile_base_control/lib/mobile_base_control/m1_control_check --execute --op disable
```
- **Expected State Before**：Servo Enabled / Stopped.
- **Expected Observation**：
  - 驅動器接收 Multi-drive 2.0 FC17 (SVOFF `0x0007`)。
  - 馬達釋放鎖定（無保持扭矩，輪胎可手動輕易轉動）。
  - Status 回復至 6 (WAIT/INHIBIT)。

---

### Step 5: Bounded Exchange Motion (Level 4 Motion) — [BLOCKED]
> 🛑 **STATUS: BLOCKED**
> **REASON**: 缺少獨立於 Process 之外的 Fail-Safe Stop 保證機制（M1 通訊 Watchdog 尚未完成實體閉環驗證且非認證安全功能）。本步驟嚴禁在實機執行。

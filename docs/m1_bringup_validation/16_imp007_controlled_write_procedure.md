# IMP-007 Controlled Write Validation Procedure

本文件定義關閉 `docs/07_implementation_checklist.md` 第 7 項 S7 `M1Driver` transport vertical slice 所需執行的 Level 3（使能與停機）與 Level 4（受控短時運動）實機驗證程序。

> [!CAUTION]
> **SAFETY GATE: ALL REAL-HARDWARE WRITE/CONTROL OPERATIONS REQUIRE EXECUTION-TIME OPERATOR AUTHORIZATION**
> 本程序中所有帶有 `--execute` 標籤的真實硬體指令，**嚴禁在未經操作人員當下明確授權與在場監控的情況下執行**。

---

## 1. Physical Preflight Checklist (依 §6.3 規範)

在執行任何 Level 3 / Level 4 指令前，操作人員必須在現場逐項確認下列條件：

- [ ] **Target Device 唯一性確認**：確認 `/dev/ttyUSB0` 為唯一的 M1 RS-485 轉接器，ID 1 為右輪，ID 2 為左輪。
- [ ] **實體斷電路徑待命**：操作人員手邊備妥實體電源切斷開關，並預先確認可在任何異常時於 1 秒內物理斷電。
- [ ] **車體架高脫離地面**：驅動輪必須完全懸空架高，確認輪胎旋轉時不會造成車體移動或接觸任何物體。
- [ ] **受控區域淨空**：車體周圍無雜物與非測試人員。
- [ ] **通訊健全性已驗證**：已完成 Level 2 唯讀測試（FC03 `read_state` 正確且無 Alarm）。

---

## 2. Validation Executable Interface

- **執行檔路徑**：`./install/mobile_base_control/lib/mobile_base_control/m1_control_check`
- **參數說明**：
  - `--op <read|enable|stop|disable|exchange>`：指定驗證操作（必填，無預設值）。
  - `--device <path>`：串列埠裝置（預設 `/dev/ttyUSB0`）。
  - `--baud <int>`：通訊速率（預設 `230400`）。
  - `--timeout-ms <int>`：單次交易逾時（預設 `100` ms）。
  - `--driver-a <id>`：驅動器 A ID（預設 `1`，右輪）。
  - `--driver-b <id>`：驅動器 B ID（預設 `2`，左輪）。
  - `--rpm <int>`：目標轉速（`--op exchange` 必填，由 operator 提供）。
  - `--duration-ms <int>`：運動持續時間（`--op exchange` 必填，由 operator 提供）。
  - `--dry-run`：預覽指令序列，不開啟 serial port、不執行任何硬體寫入。
  - `--execute`：安全確認標籤；真實硬體執行時必填。

---

## 3. Step-by-step Controlled Execution Sequence

### Step 0: Command Preview (Dry-Run)
在執行真實寫入前，先使用 `--dry-run` 確認參數與指令序列無誤：
```bash
./install/mobile_base_control/lib/mobile_base_control/m1_control_check --dry-run --op enable
./install/mobile_base_control/lib/mobile_base_control/m1_control_check --dry-run --op exchange --rpm <VALIDATED_RPM> --duration-ms <VALIDATED_MS>
```

---

### Step 1: Pre-operation State Read (Level 2 Baseline)
確認馬達處於 Servo-Off 狀態且無 Alarm：
```bash
./install/mobile_base_control/lib/mobile_base_control/m1_control_check --execute --op read
```
- **Expected State Before**：Status = 6 (WAIT/INHIBIT), Alarm = 0, RPM = 0.
- **Abort Condition**：Alarm != 0 或通訊逾時。

---

### Step 2: Servo Enable Primitive (Level 3 No-Motion Write)
> **REQUIRES EXECUTION-TIME OPERATOR AUTHORIZATION**
```bash
./install/mobile_base_control/lib/mobile_base_control/m1_control_check --execute --op enable
```
- **Expected State Before**：Status = 6, Alarm = 0.
- **Expected Observation**：
  - 驅動器接收 Multi-drive 2.0 FC17 (SVON `0x0006`)。
  - 馬達鎖定（產生保持阻抗），但**無旋轉運動**，回授 RPM = 0。
  - Status 轉為使能狀態（Status & 0x0001 != 0），Alarm = 0。
- **Abort Condition**：馬達產生非預期旋轉、發出異音、Alarm != 0 或通訊失敗。
- **Emergency Stop Path**：立即手動切斷電源或執行 Step 3 / 4。

---

### Step 3: Stop Primitive Verification (Level 3 No-Motion Write)
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

### Step 4: Servo Disable Primitive (Level 3 No-Motion Write)
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

### Step 5: Bounded Exchange Motion Verification (Level 4 Short-Duration Motion)
> **REQUIRES EXECUTION-TIME OPERATOR AUTHORIZATION**
> **PRECONDITION: Operator must explicitly define `<VALIDATED_LOW_SPEED_RPM>` and `<VALIDATED_SHORT_DURATION_MS>`**
```bash
./install/mobile_base_control/lib/mobile_base_control/m1_control_check --execute --op exchange --rpm <VALIDATED_LOW_SPEED_RPM> --duration-ms <VALIDATED_SHORT_DURATION_MS>
```
- **Execution Flow**：
  1. 依 20 Hz 週期下發 FC17 (ID1: `+rpm`, ID2: `-rpm`)，持續 `<duration_ms>`。
  2. 時間到達後自動調用 `stop()` 下發 0 RPM。
  3. 自動調用 `read_state()` 讀取停止後最終狀態與 position steps。
  4. 自動調用 `disable()` 釋放馬達。
- **Expected Observation**：
  - 架空輪胎以指定低速平穩旋轉，方向一致（ID1 與 ID2 反向對應前進方向）。
  - 到達指定時間後精確停止並釋放使能。
  - 無超速、無抖動、無通訊丟包、Alarm = 0。
- **Abort Condition**：任何單一週期通訊失敗、Alarm != 0 或輪胎旋轉方向異常 -> 程式立即中斷並發送 stop primitive。
- **Emergency Stop Path**：實體電源開關物理切斷。

---

## 4. Verification Evidence Capture

執行通過後，輸出必須依 §4 / §5 規範擷取為 raw evidence 檔案：
- **路徑**：`docs/verification/IMP-007/<YYYY-MM-DD>T<HHmmss>_hw_m1_controlled_write.txt`
- **Metadata**：包含 IMP-007、Layer `hardware`、Timestamp、Version SHA、測試條件（架高、RPM、持續時間）、觀察結果、已證明與尚未證明邊界。

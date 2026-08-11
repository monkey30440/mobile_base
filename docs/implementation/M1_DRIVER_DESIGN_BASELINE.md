# M1Driver Design Baseline

> Status: **M1Driver stage design baseline**  
> Date: 2026-08-11  
> Scope: `SUB-001 Drive Hardware Interface` 之第二層 **M1Driver**  
> Target: DEXMART M1 ×2, RS-485, Modbus Multi-drive 2.0, ROS 2 Jazzy / ros2_control

---

## 1. 目的

本文件定案三層架構中的第二層 `M1Driver`：

```text
M1Hardware
    ↓  MotorCommand / MotorState
M1Driver                 ← 本文件
    ↓  raw bytes
SerialTransport
    ↓
RS-485
    ↓
M1 ID1 / ID2
```

`M1Driver` 的責任是：

- 理解 DEXMART M1 與 Modbus / Multi-drive 2.0 協議。
- 將馬達端命令轉為合法封包。
- 驗證回應封包是否合法。
- 將回應解析為 M1 原生馬達狀態。
- 提供 Servo lifecycle 命令。
- 提供少量 Standard Modbus register access 給 configuration / maintenance。

`M1Driver` **不負責**：

- ROS 2 / ros2_control lifecycle。
- wheel rad/s ↔ motor RPM 的 gear ratio / sign 換算。
- wheel position [rad] 換算。
- int32 position rollover 後的長期連續位置累加。
- 左輪 / 右輪語意。
- 差速運動學、odometry、wheel radius、wheel separation。
- Serial device 的實際 byte I/O 細節。

---

## 2. 架構原則

### 2.1 Runtime control 優先使用 Multi-drive 2.0

正常 ros2_control runtime 主線定案如下：

```text
read_state()
    → Multi-drive 2.0 FC03

enable()
    → Multi-drive 2.0 FC17 + SVON + simultaneous state read

exchange()
    → Multi-drive 2.0 FC17 + JG/RPM + simultaneous state read

stop()
    → Multi-drive 2.0 FC17 + JG/0 + simultaneous state read

disable()
    → Multi-drive 2.0 FC17 + SVOFF + simultaneous state read
```

原則不是「所有事情都硬用 FC17」，而是：

> **Runtime 優先使用 Multi-drive 2.0；在 Multi-drive 2.0 中依操作語意選 FC03 / FC17。**

因此純讀取使用 Multi-drive 2.0 FC03；需要同時下達 command 與取得 state 時使用 FC17。

### 2.2 Standard Modbus 僅保留 configuration / maintenance

以下類型不屬於正常 control loop：

- `01-06` Encoder resolution
- `02-14` Position format
- `05-17 / 05-18 / 05-21` communication watchdog configuration
- `09-19 / 09-20 / 09-26` communication / mapping configuration
- `0x1400` NET-IN
- 其他 M1 parameter/register access

這些使用 Standard Modbus register access，不混入正常 ros2_control runtime。

---

## 3. 已驗證硬體基準

目前實機基準：

| 項目 | 已驗證值 |
|---|---:|
| Serial device | `/dev/ttyUSB0` |
| UART | 230400, 8N1 |
| Right motor driver | ID1 |
| Left motor driver | ID2 |
| `09-26` Multi-drive 2.0 mapping | `0` |
| Position format `02-14` | `1` |
| Encoder resolution `01-06` | `2500 pulse/rev` |
| Effective motor counts/rev | `10000` |
| Gear ratio | `20.0:1` — verified on both sides |
| Right native sign | `-1` relative to ROS forward |
| Left native sign | `+1` relative to ROS forward |

### 3.1 Position format

正式 baseline 採用：

```text
02-14 = 1
```

Multi-drive feedback `Data5 + Data6` 解析為 **signed int32 position_steps**。

已實測：

- ID1 `+80 RPM` → position step 正向增加。
- ID1 `-80 RPM` → position step 反向減少。
- ID2 `+80 RPM` → position step 正向增加。
- ID2 `-80 RPM` → position step 反向減少。
- 高低 word 跨 `0xFFFF ↔ 0x0000` 時 signed int32 解碼正確。

`M1Driver` 僅解析 raw signed int32；跨整個 int32 lifetime rollover 的 unwrap 由 `M1Hardware::PositionTracker` 處理。

---

## 4. Runtime Multi-drive 2.0 資料模型

### 4.1 Read Data

MVP 使用：

| Multi-drive Read Data | 意義 | MotorState |
|---|---|---|
| Data0 | Motor status | `status` |
| Data1 | Alarm | `alarm` |
| Data2 | Actual RPM | `actual_rpm` |
| Data5 | Position high word | `position_steps` high |
| Data6 | Position low word | `position_steps` low |

Data3 / Data4（Bus voltage / current）目前不進控制主資料模型；未來 diagnostics 有需求再加入。

### 4.2 Write Data

目前 `09-26 = 0`，Runtime command 使用已驗證的 Write Data8 / Data9 mapping：

```text
Write Data8 = Multi-drive Lite command
Write Data9 = command Data1
```

MVP command：

```text
JG     → signed target RPM
SVON   → data = 0
SVOFF  → data = 0
```

`ALM-RST`、`NULL`、其他命令目前不納入 MVP runtime API。

---

## 5. 公開資料結構

建議最小資料模型：

```cpp
struct MotorCommand
{
  int driver_id;
  int16_t target_rpm;
};

struct MotorState
{
  int driver_id;
  int16_t actual_rpm;
  int32_t position_steps;
  uint16_t status;
  uint16_t alarm;
};

struct ExchangeResult
{
  std::array<MotorState, 2> states;
};
```

規則：

- `M1Driver` 不知道 `left/right`。
- 每筆 state 必須帶 `driver_id`。
- `M1Hardware` 才負責 `ID1 → right`、`ID2 → left` 的 mapping。
- RPM 在 protocol boundary 使用 integer；浮點 rad/s、gear ratio、sign、rounding/clamping 由 `M1Hardware` 完成。

---

## 6. M1Driver Runtime Public API

MVP 建議 API：

```cpp
class M1Driver
{
public:
  Result<void> connect();
  Result<void> disconnect();

  Result<ExchangeResult> read_state(int driver_a, int driver_b);

  Result<ExchangeResult> enable(int driver_a, int driver_b);

  Result<ExchangeResult> exchange(
      const MotorCommand& command_a,
      const MotorCommand& command_b);

  Result<ExchangeResult> stop(int driver_a, int driver_b);

  Result<ExchangeResult> disable(int driver_a, int driver_b);

  // Configuration / maintenance only
  Result<uint16_t> read_register(int driver_id, uint16_t address);
  Result<void> write_register(
      int driver_id,
      uint16_t address,
      uint16_t value);
};
```

### 6.1 `read_state()`

用途：純讀取兩顆 M1 狀態。

```text
Multi-drive 2.0 FC03
→ one request
→ driver bitmap selects both drivers
→ read Data0~Data6
→ ExchangeResult
```

已實機驗證一包可同時讀 ID1 + ID2，且與 Standard Modbus reference 的 status / alarm / rpm / position 語意一致。

### 6.2 `enable()`

```text
Multi-drive 2.0 FC17
Write Data8/9:
  ID1/ID2 = SVON, 0
Read Data0~6 simultaneously
```

`enable()` 回傳合法的 immediate `ExchangeResult`，但：

> **transaction success 不等於 Servo state 已完成轉換。**

實測 immediate response 仍可能是 `status=6`，後續 poll 才變 `status=0`。

因此 lifecycle transition success 判斷由 `M1Hardware` 做有限次 `read_state()` poll。

### 6.3 `exchange()`

正常 ACTIVE control loop 唯一的 motor motion transaction：

```text
Multi-drive 2.0 FC17
Write:
  each driver = JG + signed RPM
Read:
  Data0~6 for both drivers
```

`M1Hardware::write()` 呼叫一次 `exchange()`，並保存回傳的 `latest_motor_state`。

### 6.4 `stop()`

`stop()` 是 convenience API，本質仍使用同一個 FC17 command path：

```text
ID1 = JG 0
ID2 = JG 0
+
simultaneous state read
```

實測送出 JG 0 後第一筆回應可能仍帶上一瞬間非零 RPM，因此上層 deactivate policy 必須有限次確認 RPM 已接近 0。

### 6.5 `disable()`

```text
Multi-drive 2.0 FC17
ID1/ID2 = SVOFF, 0
+
simultaneous state read
```

與 `enable()` 相同，immediate response 不保證 lifecycle state 已完成轉換；實測後續 poll 才由 `status=0` 轉為 `status=6`。

---

## 7. Internal Helper 設計

### 7.1 Generic Runtime FC17 command builder

不要為 JG / SVON / SVOFF 各自重寫一套 FC17 builder。

內部使用單一 generic builder：

```cpp
build_command_request(commands)
```

概念輸入：

```text
(driver_id, command_code, data)
(driver_id, command_code, data)
```

應用：

```text
exchange() → JG + RPM
stop()     → JG + 0
enable()   → SVON + 0
disable()  → SVOFF + 0
```

### 7.2 FC03 read path

```text
build_state_read_request()
→ transport.write()
→ transport.read()
→ validate_state_read_response()
→ parse_motor_states()
```

### 7.3 FC17 command path

```text
build_command_request()
→ transport.write()
→ transport.read()
→ validate_command_response()
→ parse_motor_states()
```

### 7.4 Shared parser

FC03 與 FC17 最終都應共用同一套 `parse_motor_states()`，避免 RPM / signed position 在兩條路徑出現不同解碼實作。

```text
Data0 → uint16 status
Data1 → uint16 alarm
Data2 → signed int16 actual_rpm
Data5 + Data6 → signed int32 position_steps
```

---

## 8. Response Validation

MVP validator 至少驗證：

- Group/slave identifier。
- Function code。
- Modbus exception response。
- Byte count。
- Total response length。
- CRC16。
- Driver block count / order 與 request 一致。

Validator **不判斷**：

- `alarm != 0` 是否允許繼續控制。
- `status` 是否符合 lifecycle 期待。
- RPM 是否符合 ROS command。
- position rollover。

上述屬於 `M1Hardware` policy。

---

## 9. Error Model

MVP 不只回 `bool`，也不建立複雜 exception hierarchy。

```cpp
enum class ErrorCode
{
  NONE,

  // Transport-originated
  PORT_OPEN_FAILED,
  IO_ERROR,
  TIMEOUT,
  SHORT_READ,

  // Protocol-originated
  BAD_CRC,
  BAD_FUNCTION,
  BAD_LENGTH,
  INVALID_RESPONSE,
  MODBUS_EXCEPTION,
};
```

使用：

```cpp
template<typename T>
struct Result
{
  bool ok;
  ErrorCode error;
  T value;
};
```

重要規則：

```text
合法 FC03 / FC17 response
但 MotorState.alarm != 0
```

仍屬於：

```text
Result.ok = true
```

因為 protocol transaction 成功；是否進入 ros2_control ERROR 由 `M1Hardware` 決定。

---

## 10. M1Hardware 與 M1Driver 的界線

### M1Hardware 負責

- `rad/s → RPM`。
- gear ratio `20.0`。
- left/right native sign。
- operational RPM clamp。
- RPM rounding。
- `position_steps → PositionTracker → continuous int64 steps`。
- step → wheel rad。
- M1 alarm/status 對 ros2_control lifecycle 的 policy。
- enable/disable transition polling policy。
- 保存 A2 架構的 `latest_motor_state`。

### M1Driver 負責

- M1 Driver bitmap。
- Multi-drive 2.0 address / frame layout。
- FC03 / FC17。
- JG / SVON / SVOFF protocol encoding。
- signed RPM encode/decode。
- signed int32 position decode。
- Modbus CRC / response validation。
- Standard register access。

### SerialTransport 負責

待下一階段定案：

- serial open/close。
- raw bytes write/read。
- per-transaction read timeout execution。
- I/O / timeout / short-read error reporting。

它不知道 M1、FC17、RPM、CRC 或 Driver ID。

---

## 11. ros2_control A2 integration（已定案，不因本次修正改變）

```text
CONTROL CYCLE N

M1Hardware::read()
    ↓
consume latest_motor_state
    ↓
position / velocity → ROS joint states
    ↓
controller update
    ↓
M1Hardware::write()
    ↓
wheel rad/s → integer motor RPM
    ↓
M1Driver::exchange()
    ↓
FC17 JG/RPM + state
    ↓
save latest_motor_state

CONTROL CYCLE N+1
    ↓
read() consumes that state
```

因此正常 ACTIVE control cycle 僅有 **一次 RS-485 FC17 transaction**。

---

## 12. 已完成的實機驗證證據

### 12.1 Runtime feedback / JG

已驗證：

- ID1 = right wheel。
- ID2 = left wheel。
- FC17 可一包控制兩顆 Driver。
- 可讓一顆運轉、另一顆保持 0 RPM。
- signed RPM feedback 正確。
- position feedback 正確。
- JG 0 可停止。
- alarm 維持 0。

### 12.2 Mechanical / conversion

已驗證：

- Gear ratio `20:1`：左右各以約 20 motor rev 對應約 1 wheel rev。
- Left native sign = `+1`。
- Right native sign = `-1`。
- `10000 motor steps/rev`。
- `200000 motor steps/wheel rev`。
- format-1 signed int32 position packing / conversion unit tests PASS。

### 12.3 Multi-drive 2.0 FC03 — 2026-08-11 PASS

Read-only 實測：

```text
one Multi-drive 2.0 FC03 request
→ ID1 + ID2 state
```

與 Standard Modbus reference 比較：

```text
ID1 status/alarm/rpm/position: PASS
ID2 status/alarm/rpm/position: PASS
```

因此 `M1Driver::read_state()` 正式採 Multi-drive 2.0 FC03。

### 12.4 Multi-drive 2.0 lifecycle — 2026-08-11 PASS

實測：

```text
status 6 / rpm 0
    ↓ FC17 SVON
poll → status 0 / rpm 0
    ↓ FC17 JG 0
status 0 / rpm 0
    ↓ FC17 SVOFF
poll → status 6 / rpm 0
```

兩顆 Driver 全程 `alarm=0`。

因此 runtime `enable()/disable()` 正式採 Multi-drive 2.0 FC17 SVON/SVOFF，不再以 NET-IN 作為正常 lifecycle 主線。

NET-IN 路徑保留為 bring-up / maintenance / emergency test fallback，不是 production runtime 正常路徑。

---

## 13. Timing evidence 與目前未定案事項

目前 FC17 timing 實測：

| Test | mean | p95 | p99 | max |
|---|---:|---:|---:|---:|
| requested 50 Hz | 17.317 ms | 23.867 ms | 24.019 ms | 24.050 ms |
| requested 30 Hz | 16.555 ms | 23.328 ms | 24.130 ms | 24.387 ms |

結論：

- 50 Hz 的 20 ms budget 已被實測最大 transaction time 超過，不採為目前 baseline。
- 30 Hz 是合理候選，但尚未把完整 `controller_manager + M1Hardware + diagnostics` overhead 納入。
- **controller update rate 尚未在 M1Driver 階段定案。**
- **Serial read timeout 尚未定案。**

這兩項留到 SerialTransport / 三層整合後，以實機 timing/jitter 再決定。

### Transport backend 與既有 libmodbus 決策

既有 `SUB-001-base-control-plan.md` 曾定案以 **libmodbus** 實作 Modbus transport；本次三層設計則將邏輯邊界定為：

```text
M1Driver       = M1 / Multi-drive 2.0 protocol semantics
SerialTransport = serial I/O / timeout
```

兩者在概念上不衝突，但若直接讓 libmodbus 負責 CRC、RTU framing、FC03/FC17 transaction，實作邊界就不再是「純 raw-byte SerialTransport」。

因此本次 **不重新推翻 libmodbus 決策，也不在 M1Driver 階段硬定其放置位置**。下一個 SerialTransport 階段必須先做一個小決策：

- 保留純 raw-byte `SerialTransport`，M1Driver 自己建立/驗證 Modbus frame；或
- 建立以 libmodbus 為 backend 的 transport / protocol adapter，讓成熟函式庫負責 RTU framing/CRC，但仍維持 M1Driver 對 Multi-drive 2.0 address、command mapping、MotorState 語意的所有權。

這個決策不改變本文件已定案的 M1Driver public API、MotorState、runtime protocol choice 或 ros2_control A2 flow。

### Watchdog

目前 `05-17=100 ms / 05-18=3 / 05-21=2` 曾出現 Alarm 21，但既有 watchdog 測試在預定 silence window 之前就已進 alarm，故不能證明「設計的 silence window 正確觸發 watchdog」。

因此：

- Register write：已驗證。
- Alarm 21 與通信 timeout protection 有實機證據。
- 精確 watchdog trip/recovery policy：**未定案**。

watchdog 不納入本次 M1Driver baseline 的 production safety claim。

---

## 14. Unit Test Baseline

### Parser

至少包含：

- positive int16 RPM。
- negative int16 RPM。
- positive int32 position。
- negative int32 position。
- two-driver block mapping/order。
- signed boundary values：
  - RPM `+32767 / -32768`
  - position `+2147483647 / -2147483648`

### Response validator

至少包含：

- valid response。
- bad CRC。
- wrong function code。
- wrong group/slave identifier。
- wrong byte count。
- wrong total length。
- Modbus exception response。

### Request builder

至少包含：

- two valid driver IDs。
- driver bitmap。
- JG positive/negative/zero RPM encoding。
- SVON / SVOFF command encoding。
- duplicate ID reject。
- out-of-range ID reject。
- CRC fixture。

### Integration without hardware

以 fake/mock `SerialTransport` 驗證：

```text
request build
→ write
→ simulated response
→ validate
→ parse
→ ExchangeResult
```

---

## 15. 明確不做的 MVP 功能

本階段不增加：

- automatic reconnect state machine。
- protocol retry loop。
- background communication thread。
- alarm automatic reset。
- degraded mode。
- arbitrary 1~8 driver generic fleet abstraction。
- FC10 runtime path（目前無必要 use case）。
- FC17 NULL runtime path。
- diagnostics 的 Bus voltage/current 擴充。

這些有明確需求再加入，不提前抽象。

---

## 16. 對既有 repo 文件的回寫影響

目前 `docs/implementation/SUB-001-base-control-plan.md` 與 `docs/05_subsystem.md` 有部分已被新實機證據取代，後續實作前應修正：

### 必須更新

1. `02-14`：

```text
舊：0 = Index(turns) + pulse
新：1 = signed int32 steps，已實機驗證左右正反方向
```

2. Encoder rollover：

```text
舊：signed 16-bit turns rollover
新：signed int32 position_steps rollover
```

3. Gear ratio：

```text
舊：20.0 尚未實機驗證
新：20.0 已左右實機驗證
```

4. Runtime Servo lifecycle：

```text
舊：NET-IN / SERVO-EN 為正常 lifecycle 路徑
新：Multi-drive 2.0 FC17 SVON/SVOFF 為正常 lifecycle 路徑
    NET-IN 僅保留 bring-up / maintenance fallback
```

5. Multi-drive 2.0 read：

```text
read_state() → Multi-drive 2.0 FC03，一包讀 ID1+ID2，已實機 PASS
```

6. FC17 timing：

```text
舊：約 10~15 ms
新：實測分布約 8.6~24.4 ms；50 Hz 已不適合作為 baseline
```

### 本文件不改動

- 三層架構。
- ros2_control A2 read/write 設計。
- wheel radius / separation 所屬 SUB-004 的邊界。
- PositionTracker 屬於 M1Hardware。

---

## 17. M1Driver 階段正式定案

M1Driver MVP baseline：

```text
M1Driver
│
├── Runtime / Multi-drive 2.0
│   │
│   ├── read_state()
│   │      └── FC03 → state for two drivers
│   │
│   ├── enable()
│   │      └── FC17 SVON + state
│   │
│   ├── exchange()
│   │      └── FC17 JG/RPM + state
│   │
│   ├── stop()
│   │      └── FC17 JG/0 + state
│   │
│   └── disable()
│          └── FC17 SVOFF + state
│
├── Protocol helpers
│   ├── request builders
│   ├── response validators
│   ├── CRC
│   └── shared MotorState parser
│
└── Configuration / maintenance
    ├── read_register()
    └── write_register()
        └── Standard Modbus
```

### Exit criteria — M1Driver stage

- [x] Runtime protocol choice defined。
- [x] Multi-drive 2.0 FC03 read path hardware verified。
- [x] Multi-drive 2.0 FC17 JG/RPM hardware verified。
- [x] Multi-drive 2.0 FC17 JG0 stop hardware verified。
- [x] Multi-drive 2.0 FC17 SVON hardware verified。
- [x] Multi-drive 2.0 FC17 SVOFF hardware verified。
- [x] signed int32 format-1 position hardware verified。
- [x] Public API boundary defined。
- [x] Error ownership defined。
- [x] Unit-test scope defined。
- [ ] C++ implementation — next implementation phase。

**M1Driver design stage: COMPLETE.**

下一階段：**SerialTransport MVP design**，之後才將三層串接並開始 C++ implementation。

---

## 18. Evidence / Reference Files

官方文件：

- `ref/M1-COMM_UM-01-S0686.pdf`
- `ref/M1-UserManual_UM-01-S0701.pdf`

Bring-up / verification：

- `docs/m1_bringup_validation/`
- `right_80rpm_safe.txt`
- `left_80rpm_safe.txt`
- `gear_ratio_right.txt`
- `gear_ratio_left.txt`
- `conversion_format1.txt`
- `format1_right.txt`
- `format1_left.txt`
- `fc17_timing_50hz.txt`
- `fc17_timing_30hz.txt`
- Multi-drive 2.0 FC03 state test — PASS, 2026-08-11
- Multi-drive 2.0 lifecycle SVON/JG0/SVOFF test — PASS, 2026-08-11

---


# M1 / Multi-drive 2.0 從零驗證 Checklist

原則：**前一階段沒 PASS，就不要進下一階段。** 不修改既有 ros2_control 程式來「配合結果」，先證明硬體與協議本身。

## A. 安全與實體接線

- [ ] 驅動輪架空，第一次測試不讓車體接地行走。
- [ ] E-stop / STO 可以人工立即觸發。
- [ ] M1 主電源規格與馬達規格已人工確認。
- [ ] RS485 A 對 A、B 對 B，兩顆 M1 共地/參考地依實機接線完成。
- [ ] 線路終端、線長與干擾問題已檢查。
- [ ] CN6 的 RS485_A / RS485_B 接線位置再次核對。

紀錄：

```text
日期：
測試者：
USB-RS485 型號：
左驅動器序號/標籤：
右驅動器序號/標籤：
```

## B. Linux serial preflight

執行：

```bash
bash scripts/00_preflight.sh
```

- [ ] `/dev/ttyUSB*` 或 `/dev/ttyACM*` 可見。
- [ ] 目前帳號有裝置讀寫權限。
- [ ] 沒有 ModemManager / 其他程序搶占該 port。
- [ ] `python3-serial` 可 import。

## C. 從零找出 baud 與 Driver ID

執行：

```bash
python3 scripts/01_scan_bus.py --port /dev/ttyUSB0
```

腳本只使用**標準 Modbus FC03 讀取**，不會下馬達命令。

- [ ] 找到第一顆 Driver ID。
- [ ] 找到第二顆 Driver ID。
- [ ] 兩顆 Driver ID 不相同。
- [ ] 找到實際 baud。
- [ ] 同一 baud 下兩顆都能穩定重複回應。

實測：

```text
baud =
right_driver_id =
left_driver_id =
```

> 不要先假設 ID=1/2 或 baud=230400/115200；以這一步結果為準。

## D. 讀取並記錄 M1 組態

執行：

```bash
python3 scripts/02_read_config.py --port /dev/ttyUSB0 --baud <baud> --ids <id1,id2> | tee logs/config.txt
```

至少確認：

- [ ] `01-01` Motor/Sensor type。
- [ ] `01-04` no-load max RPM。
- [ ] `01-06` encoder resolution，左右相同且非 0。
- [ ] `01-10` Drive Enable 設定。
- [ ] `01-11` Control Mode。
- [ ] `02-14` Position format。
- [ ] `05-03` encoder feedback overflow protection behavior。
- [ ] `05-17` RS485 timeout。
- [ ] `05-18` RS485 error count。
- [ ] `05-21` communication-failure action。
- [ ] `09-18` RS485 protocol = Modbus RTU。
- [ ] `09-19` Driver ID 與掃描結果一致。
- [ ] `09-20` Baud 設定與掃描結果一致。
- [ ] `09-21` RTU C3.5。
- [ ] `09-26` Multi-drive 2.0 mapping 值記錄完成。

**這一步只讀，不改參數。** 如果值不符合預期，先記錄，再人工決定是否修改。

## E. Multi-drive 2.0 Read-only 驗證

執行：

```bash
python3 scripts/03_md2_read.py --port /dev/ttyUSB0 --baud <baud> --ids <id1,id2> --samples 20 --hz 10 | tee logs/md2_read.txt
```

此腳本使用 Multi-drive 2.0 的 FC03 群組讀取，不下運轉命令。

- [ ] Group address / bitmask 能同時選到兩顆 Driver。
- [ ] Read Data0 Motor Status 合理。
- [ ] Read Data1 Alarm = 0（若非 0，停止後續測試）。
- [ ] Read Data2 Current RPM 靜止時接近 0。
- [ ] Read Data3 Bus voltage 合理。
- [ ] Read Data4 Output current 靜止時合理。
- [ ] Read Data5/6 Position 讀值穩定。
- [ ] 連續 20 次沒有 CRC / timeout / frame 錯誤。

## F. 單顆馬達低速驗證

第一次務必架空輪子。

右輪測試：

```bash
python3 scripts/04_motor_test.py \
  --port /dev/ttyUSB0 --baud <baud> --ids <right_id,left_id> \
  --right-rpm 80 --left-rpm 0 --seconds 1 \
  --arm I_UNDERSTAND | tee logs/right_80rpm.txt
```

左輪測試：

```bash
python3 scripts/04_motor_test.py \
  --port /dev/ttyUSB0 --baud <baud> --ids <right_id,left_id> \
  --right-rpm 0 --left-rpm 80 --seconds 1 \
  --arm I_UNDERSTAND | tee logs/left_80rpm.txt
```

- [ ] 右輪只有右輪動。
- [ ] 左輪只有左輪動。
- [ ] 測試結束後兩輪確實停止。
- [ ] RPM feedback 符號與實際方向一致。
- [ ] Position 增減方向與 RPM 符號一致。
- [ ] Alarm 仍為 0。

若「ROS 正方向」與馬達的正方向不同，**只記錄 sign，不要在這一步改 Driver**：

```text
right_motor_sign =
left_motor_sign =
right_feedback_sign =
left_feedback_sign =
```

## G. 20:1 減速比驗證

已知 nominal gear ratio = 20.0，但要實測。

方法：在輪子做明顯記號，手動/低速使馬達位置回授增加約 20 motor rev，觀察輪子是否約 1 rev。

- [ ] 20 motor rev ≈ 1 wheel rev。
- [ ] 左右兩邊一致。

紀錄：

```text
right measured gear ratio =
left measured gear ratio =
```

## H. 輪徑與輪距實測

目前基準：

```text
wheel_radius = 0.08 m
wheel_separation = 0.5545 m
```

- [ ] 輪胎負載後實際 rolling radius 已量測。
- [ ] 左右驅動輪中心距已量測。
- [ ] 記錄量具與測量方法。

實測：

```text
wheel_radius =
wheel_separation =
```

## I. ros2_control 前置條件

只有 A~H 完成後才開始寫/驗證 ros2_control Hardware Interface。

應具備的已驗證資訊：

- [ ] serial port
- [ ] baud
- [ ] driver IDs
- [ ] 8N1 / protocol
- [ ] Multi-drive 2.0 address / bitmask
- [ ] FC17 write mapping
- [ ] FC17 read mapping
- [ ] encoder resolution
- [ ] position format
- [ ] gear ratio
- [ ] command sign
- [ ] feedback sign
- [ ] safe motor RPM limit
- [ ] communication timeout behavior

## J. 測試證據

每次測試後至少保存：

- [ ] `record_session.sh` 的 session folder。
- [ ] `02_read_config.py` 輸出。
- [ ] `03_md2_read.py` 輸出。
- [ ] 左右輪各一次 motor-test log。
- [ ] 異常時完整錯誤訊息，不只截最後一行。
- [ ] checklist 勾選與人工觀察結果。

# M1 Bring-up Validation（從零驗證）

這個資料夾的目的不是驗證既有實作，而是**從硬體與官方通訊文件開始重新驗證**：

1. 找到 RS-485 裝置與正確 baud / driver ID。
2. 用標準 Modbus RTU FC03 讀取 M1 組態，確認兩顆驅動器的基本條件。
3. 用 Multi-drive 2.0 FC03 只讀方式驗證群組定址與回授格式。
4. 最後才使用 Multi-drive 2.0 FC17，以低速短時間方式測試左右馬達。
5. 每一步都產生 log，方便之後寫 ros2_control Hardware Interface 時保留證據。

> **安全**：第一次執行馬達測試時，請把驅動輪架空、確保 E-stop/STO 可立即動作，旁邊不要有人或物。`04_motor_test.py` 必須明確輸入 `--arm I_UNDERSTAND` 才會送出運轉命令，而且預設只跑 80 RPM / 1 秒。

## 已知車體資料

- wheel separation: `0.5545 m`
- wheel radius: `0.08 m`
- gear ratio: `20.0`

這三個值**不代表已驗證**；本 checklist 會另外驗證方向與實際里程。

## 依賴

Ubuntu / ROS 2 主機上執行：

```bash
sudo apt update
sudo apt install -y python3-serial
```

確認：

```bash
python3 -c "import serial; print(serial.__version__)"
```

## 建議執行順序

```bash
cd docs/m1_bringup_validation

bash scripts/00_preflight.sh
python3 scripts/01_scan_bus.py --port /dev/ttyUSB0
python3 scripts/02_read_config.py --port /dev/ttyUSB0 --baud <掃描到的baud> --ids <ID1,ID2>
python3 scripts/03_md2_read.py --port /dev/ttyUSB0 --baud <baud> --ids <ID1,ID2>

# 到這裡全部 PASS，再進行馬達測試
python3 scripts/04_motor_test.py --port /dev/ttyUSB0 --baud <baud> --ids <右ID,左ID> --right-rpm 80 --left-rpm 0 --seconds 1 --arm I_UNDERSTAND
python3 scripts/04_motor_test.py --port /dev/ttyUSB0 --baud <baud> --ids <右ID,左ID> --right-rpm 0 --left-rpm 80 --seconds 1 --arm I_UNDERSTAND
```

每次完整測試可用：

```bash
bash scripts/record_session.sh
```

它會建立 `logs/YYYYMMDD_HHMMSS/`，把環境、USB/serial、ROS 狀態等資訊存起來。

詳細完成條件請看 [CHECKLIST.md](CHECKLIST.md)。

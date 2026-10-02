# HandBoard IMU V1 Quick Guide

## 硬體接線

只需要一條 **USB-C 線** 連接板子與電腦即可。

```
電腦 USB-A/C ──── USB-C ──── HandBoard IMU V1
```

> 上電後綠色 LED 亮起代表板子正常運作。

---

## 確認 COM Port

### Windows

1. 連接 USB-C
2. 開啟 **裝置管理員** → **連接埠 (COM 和 LPT)**
3. 找到 **STM32 Virtual COM Port (COMx)**

```
確認範例：
STM32 Virtual COM Port (COM14)
```

> 若沒有出現，需安裝 STM32 Virtual COM Port 驅動程式：
> https://www.st.com/en/development-tools/stsw-stm32102.html

### Linux

```bash
# 列出所有串口裝置
ls /dev/tty*

# 板子連接後通常出現
/dev/ttyACM0
# 或
/dev/ttyUSB0

# 確認裝置出現
dmesg | grep tty
```

> 若出現權限問題，執行：
> ```bash
> sudo usermod -a -G dialout $USER
> ```
> 重新登入後生效。

---

## 資料格式

板子上電約 2 秒校正完成後，開始透過 USB 持續輸出 Binary 封包。

### 封包結構

總長度：**59 bytes**

| 位置 | 內容 | 資料型別 | 單位 |
|------|------|---------|------|
| byte[0] | Header1 | uint8 | 固定 0xAA |
| byte[1] | Header2 | uint8 | 固定 0x55 |
| byte[2~5] | Accel X | float32 (Little-Endian) | g |
| byte[6~9] | Accel Y | float32 (Little-Endian) | g |
| byte[10~13] | Accel Z | float32 (Little-Endian) | g |
| byte[14~17] | Accel Roll | float32 (Little-Endian) | deg |
| byte[18~21] | Accel Pitch | float32 (Little-Endian) | deg |
| byte[22~25] | Gyro X | float32 (Little-Endian) | dps |
| byte[26~29] | Gyro Y | float32 (Little-Endian) | dps |
| byte[30~33] | Gyro Z | float32 (Little-Endian) | dps |
| byte[34~37] | Gyro Roll | float32 (Little-Endian) | deg |
| byte[38~41] | Gyro Pitch | float32 (Little-Endian) | deg |
| byte[42~45] | Gyro Yaw | float32 (Little-Endian) | deg |
| byte[46~49] | Fusion Roll | float32 (Little-Endian) | deg |
| byte[50~53] | Fusion Pitch | float32 (Little-Endian) | deg |
| byte[54~57] | Fusion Yaw | float32 (Little-Endian) | deg |
| byte[58] | Checksum | uint8 | XOR of byte[0~57] |

### 資料說明

| 資料 | 說明 |
|------|------|
| Accel X/Y/Z | 加速度計原始值，單位 g（1g = 9.81 m/s²） |
| Accel Roll/Pitch | 由加速度計算出的傾斜角度 |
| Gyro X/Y/Z | 陀螺儀原始值，單位 dps（degrees per second） |
| Gyro Roll/Pitch/Yaw | 由陀螺儀積分計算出的角度，長期會漂移 |
| Fusion Roll/Pitch/Yaw | Kalman Filter 融合後的角度，**建議使用此數據** |

> ⚠️ 所有角度均以**上電時的板子姿態為零點**，上電後移動的角度變化量。

> ⚠️ Yaw 軸因無磁力計，長時間使用會緩慢漂移，僅供短期參考。

---

## IMU 座標系

IIM-42652 座標系定義（晶片正面朝上）：

- **X 軸**：文字朝自己，指向晶片右側，正方向向右
- **Y 軸**：文字朝自己，指向晶片上方，正方向向上
- **Z 軸**：垂直晶片表面，正方向朝上（遠離桌面方向）

板子平放靜止時：
- Accel Z ≈ +1.0g（Z 軸感受重力）
- Accel X ≈ 0g
- Accel Y ≈ 0g

---

## Python 快速解封包範例

```python
import serial
import struct

ser = serial.Serial('COM14', 115200)

PACKET_LEN = 59

try:
    while True:
        # 找 Header
        byte = ser.read(1)
        if byte[0] != 0xAA:
            continue
        byte2 = ser.read(1)
        if byte2[0] != 0x55:
            continue

        # 讀剩餘 57 bytes
        rest = ser.read(PACKET_LEN - 2)
        if len(rest) != PACKET_LEN - 2:
            continue

        packet = bytes([0xAA, 0x55]) + rest

        # 驗證 checksum
        checksum = 0
        for b in packet[:-1]:
            checksum ^= b
        if checksum != packet[-1]:
            continue

        # 解析封包
        values = struct.unpack('<ffffffffffffff', packet[2:58])

        ax, ay, az                   = values[0],  values[1],  values[2]
        accel_r, accel_p             = values[3],  values[4]
        gx, gy, gz                   = values[5],  values[6],  values[7]
        gyro_r, gyro_p, gyro_y       = values[8],  values[9],  values[10]
        fusion_r, fusion_p, fusion_y = values[11], values[12], values[13]

        print(f"[Accel] X:{ax:.3f}g Y:{ay:.3f}g Z:{az:.3f}g | "
              f"R:{accel_r:.2f}deg P:{accel_p:.2f}deg")
        print(f"[Gyro]  X:{gx:.3f}dps Y:{gy:.3f}dps Z:{gz:.3f}dps | "
              f"R:{gyro_r:.2f}deg P:{gyro_p:.2f}deg Y:{gyro_y:.2f}deg")
        print(f"[Fusion] R:{fusion_r:.2f}deg P:{fusion_p:.2f}deg "
              f"Y:{fusion_y:.2f}deg")
        print("---")

except KeyboardInterrupt:
    print("\n程式結束")

finally:
    ser.close()
    print("串口已關閉")
```

---

*HandBoard IMU V1 — 2026*

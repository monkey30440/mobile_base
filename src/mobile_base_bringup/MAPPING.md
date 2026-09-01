# 建圖操作指南

## 用途

`mobile_base_bringup` 的建圖模式（Mapping Mode）會啟動實機建圖所需的底盤控制、感測感知、里程估測與 SLAM Toolbox 即時建圖系統。

> **安全提醒**：啟動 Mapping Mode 本身不會命令底盤移動；操作員必須在第二個終端明確啟動鍵盤遙控。

---

## 啟動建圖模式

### 標準啟動方式 (Canonical Entry Point)

```bash
ros2 launch mobile_base_bringup mobile_base.launch.py mode:=mapping
```

若需啟用 Foxglove 視覺化工具：

```bash
ros2 launch mobile_base_bringup mobile_base.launch.py mode:=mapping use_foxglove:=true
```

> **進階與相容操作**：亦可使用相容 launch 入口 `ros2 launch mobile_base_bringup mapping.launch.py`。

---

## 啟動鍵盤遙控

確認建圖模式啟動且周遭環境安全後，開啟第二個已載入環境的容器終端執行：

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard \
  --ros-args \
  -p stamped:=true \
  -p speed:=0.10 \
  -r cmd_vel:=/diff_drive_controller/cmd_vel
```

### 操作按鍵

| 按鍵 | 動作 |
|---|---|
| `i` | 前進 |
| `,` | 後退 |
| `j` | 原地左轉 |
| `l` | 原地右轉 |
| `k` | **主動停止 (強制歸零速度)** |

---

## 建圖操作要領

1. **緩慢等速移動**：起步與轉向保持平緩，維持預設低速（0.1 m/s）。
2. **完整覆蓋環境**：沿環境周邊平順移動，使光達完整掃描固定幾何特徵。
3. **多視角閉環**：從不同視角重複經過具辨識特徵之區域，輔助 SLAM 閉環校正。
4. **存圖前煞停**：儲存地圖前請務必按下 `k`，確認 AMR 完全靜止。

---

## 儲存並驗證地圖

AMR 完全停止後，**保持建圖模式終端持續運行**，開啟第三個容器終端執行：

```bash
ros2 run mobile_base_bringup save_map.sh
```

### 產出與自動驗證

腳本會依當前時間自動建立時間戳目錄（例如 `maps/20260820_143012/`），儲存 `map.yaml` 與 `map.pgm`，並自動呼叫讀回檢驗工具：

```text
STATUS: LOAD_MAP_SUCCESS
RESOLUTION: 0.05
WIDTH: <數值>
HEIGHT: <數值>
DATA_SIZE: <數值>
```

若終端顯示 `STATUS: LOAD_MAP_SUCCESS`，即表示地圖已成功儲存並通過反序列化與幾何結構檢驗。

---

## 關閉流程與安全

1. **停止移動**：於鍵盤遙控終端按下 `k`，確認 AMR 完全停止。
2. **結束遙控**：於鍵盤遙控終端按下 `Ctrl-C` 結束程序。
3. **確認存圖**：確認地圖已完成儲存與驗證。
4. **關閉建圖模式**：於建圖 launch 終端按下 `Ctrl-C` 停止所有建圖節點。
5. **緊急停止**：`Ctrl-C` 僅為軟體層級停止；現場緊急狀況請立即按下 AMR 實體 E-stop / STO 按鈕。

---

## 故障排除

### 1. 找不到 `/map` 或地圖未更新

```bash
ros2 topic list | grep '^/map$'
ros2 lifecycle get /async_slam_toolbox_node
ros2 topic hz /scan_front
```
- 確認 `async_slam_toolbox_node` 處於 Active 狀態。
- 確認前雷達 `/scan_front` 正常以 25 Hz 發布。

### 2. 找不到雷達掃描資料 (`/scan_front` / `/scan_rear`)

```bash
ros2 topic hz /scan_front
ros2 topic hz /scan_rear
ros2 node list | grep -E 'lidar'
```
- 檢查 SICK 光達實體電源與網路連線狀態。

### 3. AMR 未回應鍵盤遙控

```bash
ros2 topic echo /diff_drive_controller/cmd_vel --once
ros2 control list_controllers
```
- 確認鍵盤遙控終端具備輸入焦點（未被其他視窗攔截）。
- 確認 `diff_drive_controller` 處於 `active` 狀態且硬體使能正常。
- 確認實體 E-stop / STO 未被觸發。

### 4. 儲存地圖逾時或讀回失敗

```bash
ros2 topic echo /map --once
ros2 run mobile_base_mapping validate_map_readback maps/<timestamp>/map.yaml
```
- 確認建圖模式仍在運行且 `/map` 仍有發布。
- 檢查確切時間戳記目錄路徑下的 `map.yaml` 與 `map.pgm` 檔案。

### 5. Foxglove 無法連線

```bash
ros2 node list | grep foxglove
```
- 確認啟動建圖模式時有帶入 `use_foxglove:=true`。

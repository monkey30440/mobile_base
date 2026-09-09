# Mapping

## Start

Mapping 啟動後，AMR 不會自行移動。以下 ROS commands 均在 `mobile_base` container 中執行。

```bash
docker compose exec mobile_base bash
```

```bash
ros2 launch mobile_base_bringup mobile_base.launch.py \
  mode:=mapping \
  use_foxglove:=true
```

## Build the Map

開啟另一個 host terminal，進入同一 container：

```bash
docker compose exec mobile_base bash
```

啟動鍵盤遙控：

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard \
  --ros-args \
  -p stamped:=true \
  -p speed:=0.20 \
  -p turn:=0.20 \
  -r cmd_vel:=/diff_drive_controller/cmd_vel
```

- `i`：前進
- `,`：後退
- `j` / `l`：轉向
- `k`：停止

緩慢移動並覆蓋需要建圖的場域。儲存前先按 `k`，確認 AMR 已停止。

## Save the Map

保持 Mapping 運行，開啟另一個 host terminal 並進入同一 container：

```bash
docker compose exec mobile_base bash
```

```bash
ros2 run mobile_base_bringup save_map.sh
```

腳本成功時會回報地圖已儲存並驗證。輸出位於：

```text
maps/<timestamp>/
├── map.yaml
└── map.pgm
```

## Stop

1. 在 teleop terminal 按 `k`，確認 AMR 停止。
2. 在 teleop terminal 按 `Ctrl-C`。
3. 在 Mapping terminal 按 `Ctrl-C`。

緊急狀況請使用實體 E-stop / STO。

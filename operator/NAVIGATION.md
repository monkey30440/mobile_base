# Navigation

## Start

Navigation 啟動後不會自行移動；AMR 會在收到 navigation target 後才開始移動。

以下 ROS commands 在 `mobile_base` Compose service 中執行。進入 container：

```bash
docker compose exec mobile_base bash
```

啟動 Navigation：

```bash
ros2 launch mobile_base_bringup mobile_base.launch.py \
  mode:=navigation \
  site:=<site> \
  use_foxglove:=true  
```

`<site>` 表示操作者選定的場域。

## Initialize

正常情況可直接使用預設 initial pose。只有 AMR 實際位置與預設 initial pose 不一致時，才需要執行此步。

在另一個 host terminal 進入 container：

```bash
docker compose exec mobile_base bash
```

啟動 RViz2：

```bash
rviz2
```

使用 RViz2 的 `2D Pose Estimate`，在地圖上設定 AMR 目前的大約位置與朝向。

## Navigate

### Pose

如果 Initialize 階段已啟動 RViz2，直接使用現有 RViz2。否則，在另一個 host terminal 進入 container：

```bash
docker compose exec mobile_base bash
```

啟動 RViz2：

```bash
rviz2
```

1. 將 `Global Options → Fixed Frame` 設為 `map`。
2. 選擇 `2D Goal Pose`。
3. 在地圖上按住並拖曳，指定目標位置與朝向。

若已知目標在 `map` frame 中的座標與朝向，可直接執行：

```bash
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose "{
  pose: {
    header: {frame_id: map},
    pose: {
      position: {x: <x>, y: <y>, z: 0.0},
      orientation: {
        x: 0.0,
        y: 0.0,
        z: <sin_yaw_over_2>,
        w: <cos_yaw_over_2>
      }
    }
  },
  behavior_tree: ''
}"
```

- `<x>` / `<y>`：`map` frame 座標，單位 m。
- `yaw`：目標朝向，單位 rad。
- `<sin_yaw_over_2>` = `sin(yaw / 2)`。
- `<cos_yaw_over_2>` = `cos(yaw / 2)`。

### Station

在另一個 host terminal 進入 container：

```bash
docker compose exec mobile_base bash
```

依 Station ID 執行導航：

```bash
ros2 run mobile_base_navigation navigate_to_station \
  --station <station_id> \
  --catalog maps/<site>/stations.yaml
```

- `<station_id>`：目標 Station ID。
- `<site>`：與 Navigation 啟動時相同的場域。
- 最終結果為 `NAV_SUCCEEDED`、`NAV_ABORTED` 或 `NAV_CANCELED`。
- 若要取消進行中的 station navigation，在此 terminal 按 `Ctrl-C`。

## Stop

1. 如果 station navigation 正在執行，在 station terminal 按 `Ctrl-C` 取消。
2. 在 Navigation launch terminal 按 `Ctrl-C` 停止 Navigation。
3. 緊急狀況使用實體 E-stop / STO。

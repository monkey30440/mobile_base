# Release

[Documentation Index](../spec/README.md)

## Build

目前 M1 position-feedback scale 尚未驗證，production activation 會在 Servo-On 前失敗；此 image 不可視為已恢復可運動版本。已確認資料與解除阻擋所需實機驗證見 [M1 evidence](../m1_settings/README.md)。

此次更新亦修改 private `mobile_base.urdf.xacro` 與 `mobile_base_ros2_control.xacro`，移除 `motor_steps_per_rev` argument、macro input 與 hardware parameter。這兩個 assets 依 repository policy 不由 Git 追蹤；建置環境必須同步更新其 private copies，再建置 image。舊參數若仍傳入 M1Hardware，初始化會明確拒絕。

在 repository root 執行；此命令不需提供額外 arguments：

```bash
./scripts/export_release.sh
```

完成後會在 repository root 產生：

```text
release/
├── mobile_base_image.tar.gz
├── compose.yaml
├── .env
├── start.sh
└── maps/
    └── template/    # repository 存在 maps/template/ 時才會包含
```

## Deploy

將完整的 `release/` directory 傳到 target machine。Target machine 需要：

- Docker
- Docker Compose plugin（`docker compose`）
- NVIDIA Container Runtime
- ARM64 / JetPack-compatible environment
- `/dev/ttyUSB0`
- `/dev/ttyACM0`

部署前設定 `release/.env`，並將實際場域使用的 resources 放入：

```text
release/maps/<site>/
```

## Start

在 target machine 執行：

```bash
cd release
docker compose down
gzip -dc mobile_base_image.tar.gz | docker load
docker compose up -d
```

這會停止舊 deployment、載入本次 artifact 中的 `mobile_base:release`，再以新 image 啟動 `mobile_base` container。

完成後，container 處於可進入的 idle / ready state。Mapping 與 Navigation 尚未啟動。

## Operate

從 `release/` directory 進入 `mobile_base` service：

```bash
docker compose exec mobile_base bash
```

Interactive shell 會載入 ROS 2 與 installed workspace environment，一般不需手動執行 `source install/setup.bash`。

接續操作請參考：

- [Mapping](./MAPPING.md)
- [Navigation](./NAVIGATION.md)

## Stop

若 Mapping 或 Navigation task 仍在執行，先依各自 guide 停止 task。接著從 `release/` directory 執行：

```bash
docker compose down
```

這會停止 release deployment 及 container。

# Release and Deployment

## 1. 文件目的與範圍

本文件說明開發者如何從 repository 建立、匯出 release，以及部署端如何使用 release package，負責 Docker development、release build、export 與 deployment 操作流程。

本文件不重複定義產品需求或系統架構；文件權責以 [文件索引](./README.md) 為準。Mapping 與 Navigation 實際操作分別依循 [MAPPING.md](../src/mobile_base_bringup/MAPPING.md) 與 [NAVIGATION.md](../src/mobile_base_bringup/NAVIGATION.md)。

## 2. Docker Multi-stage Architecture

單一 [Dockerfile](../Dockerfile) 的 stage 繼承關係如下；另外，release 從 builder 取得安裝結果。

```text
base
├── dev
├── builder
└── release
```

### base

提供共用 runtime 基礎與 release 執行所需 dependencies，包括 ROS 套件、硬體通訊函式庫與 Fluent Bit；工作目錄為 `/workspaces/mobile_base`。

### dev

日常開發環境，`FROM base`，額外安裝 RViz2 與 ping 工具。[compose.yaml](../compose.yaml) 使用 `build.target: dev`，將 repository 掛載至 `/workspaces/mobile_base`，可修改 `src`、執行 `colcon build`、載入 `install/setup.bash` 並使用 `ros2 launch`。

### builder

正式 release build 階段，`FROM base`，不是日常開發 container。以 `COPY src /ws/src` 取得程式，在 `/ws` 載入 ROS 環境後執行：

```bash
colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release
```

### release

`FROM base`，只從 builder 複製 `/ws/install` 至 `/workspaces/mobile_base/install`。

release workspace 不包含 repository 的 `src/` 目錄，但本專案含 `ament_python` packages，以及 Python launch / installed Python files，因此 `install/` 中仍可能存在可閱讀的 Python source。

設計目標是不交付完整 development workspace、`build/` 與 repository `src/` tree，降低交付內容並分離開發與 runtime 環境；此設計不保證所有程式都變成不可閱讀的 binary。

## 3. Development Workflow

在 repository root 確認 `.env` 與裝置配置後執行：

```bash
docker compose up -d
docker exec -it mobile_base bash
```

`compose.yaml` 的 `build.target` 為 `dev`。在 container 的 `/workspaces/mobile_base` 內執行：

```bash
colcon build
source install/setup.bash
```

接著依 [MAPPING.md](../src/mobile_base_bringup/MAPPING.md) 或 [NAVIGATION.md](../src/mobile_base_bringup/NAVIGATION.md) 操作。開發與 release Compose 均使用 container 名稱 `mobile_base`，同一主機切換環境時須避免名稱衝突。

## 4. Build Release Image

在 repository root 可直接執行：

```bash
docker build \
  --target release \
  -t mobile_base:release \
  .
```

```text
Dockerfile → base → builder 編譯 src → /ws/install
           → release（FROM base，COPY builder 的 install）
           → mobile_base:release
```

安裝結果由 builder 的 release build 產生，不使用開發 workspace 的既有 `install/`；Docker 可重用有效的 build cache。

## 5. Export Release Package

在 repository root 執行 [scripts/export_release.sh](../scripts/export_release.sh)：

```bash
./scripts/export_release.sh
```

腳本依序：

1. 刪除 repository root 下的 `release/`，重新建立 `release/maps/`。
2. 使用 `--target release` build `mobile_base:release`。
3. 以 `docker save` 加上 `gzip` 輸出 image 壓縮檔。
4. 複製 `compose.release.yaml` 為 `release/compose.yaml`。
5. 若 `maps/template` 目錄存在，將其複製至 `release/maps/`。
6. 輸出預設 `release/.env`。
7. 建立 `release/start.sh` 並設定可執行權限。

```text
release/
├── mobile_base_image.tar.gz
├── compose.yaml
├── .env
├── start.sh
└── maps/
    └── template/   # 若 repository 的 maps/template 存在
```

`release/` 是可重建的產出目錄；再次匯出前須保存其中需要保留的現場配置與資料。腳本僅複製地圖 template，不會匯出其他場域目錄，也不會將本指南複製進 package。

## 6. Deployment Prerequisites

依 [compose.release.yaml](../compose.release.yaml) 與產生的 `start.sh`，部署端需具備：

- Docker 與 Docker Compose（`docker compose` 命令）。
- 可執行 `start.sh` 的 Bash 與解壓 image 所需的 `gzip`。
- 可供 Compose 使用的 NVIDIA runtime（`runtime: nvidia`）。
- 支援目前 `network_mode: host` 的執行環境。
- 可供 container 使用的 `/dev/ttyUSB0` 與 `/dev/ttyACM0` serial devices。
- package 內的 `.env` 與 `maps/` 資料配置。
- 若需要 GUI，須確認 X11 `DISPLAY` 與 `/tmp/.X11-unix` 掛載可用。

本節不另訂 repository 未定義的部署端 OS 版本或硬體規格。

## 7. Deployment Configuration

腳本產生的 `release/.env` 預設內容為：

```dotenv
DISPLAY=:0
ROS_DOMAIN_ID=0
TOPIC_NAMESPACE=
MOBILE_BASE_INFLUXDB_TOKEN=
```

部署前應依現場顯示環境、ROS domain、namespace 與 Observability 配置確認這些值。

`maps/` 是外部掛載資料，由 `./maps` 掛載至 `/workspaces/mobile_base/maps`，不包進 release image 的 `install/`。部署時須準備實際場域資料；內容與操作依 [NAVIGATION.md](../src/mobile_base_bringup/NAVIGATION.md) 與 [MAPPING.md](../src/mobile_base_bringup/MAPPING.md)。

## 8. Starting the Release

將 release package 放到部署端後執行：

```bash
cd release
./start.sh
```

`start.sh` 依序：

1. 切換至 `start.sh` 所在目錄。
2. 以 `docker image inspect mobile_base:release` 檢查本機 image。
3. 若 image 不存在，執行 `gzip -dc mobile_base_image.tar.gz | docker load`。
4. 執行 `docker compose up -d`。

> **Warning**：目前 `start.sh` 若發現本機已有同名 `mobile_base:release` image，不會自動重新載入 `mobile_base_image.tar.gz`。部署新版 release 時，若主機已有舊的同名 image，必須先確認或更新 image，避免實際啟動舊版本。

## 9. Runtime Container

package 的 `compose.yaml` 來自 `compose.release.yaml`，目前設定如下：

| 設定 | 行為 |
|---|---|
| `image: mobile_base:release` | 使用既有 image，不 build source |
| volumes | 不 mount repository；掛載 `./maps` 與 X11 socket |
| `runtime: nvidia` | 使用 NVIDIA runtime |
| `network_mode: host` | 使用 host network |
| devices | 對應掛載 `/dev/ttyUSB0`、`/dev/ttyACM0` |
| `working_dir: /workspaces/mobile_base` | runtime 工作目錄 |
| `command: sleep infinity` | 保持 container 運行 |

`docker compose up -d` 只啟動並維持 container，目前不會自動執行 Mapping 或 Navigation launch。進入 container：

```bash
docker exec -it mobile_base bash
```

Dockerfile 在 Bash 啟動設定中載入 ROS 與 `/workspaces/mobile_base/install/setup.bash`。實際操作依 [MAPPING.md](../src/mobile_base_bringup/MAPPING.md) 與 [NAVIGATION.md](../src/mobile_base_bringup/NAVIGATION.md)。

## 10. Updating a Deployed Release

開發端更新 code 後，重新執行 `./scripts/export_release.sh`，取得新的 release package。

部署端依序：

1. 依操作指南結束現有任務並確認 AMR 停止，再停止現有 container。
2. 保留現場 `.env` 與 `maps/`，準備新的 package。
3. 確保新 package 的 image 被載入為 `mobile_base:release`；不可依賴 `start.sh` 自動替換已有的同名 image。
4. 再啟動 Compose，確認 container 使用新 image，並進行功能驗證。

目前 image tag 固定為 `mobile_base:release`。

## 11. Verification Checklist

以下為操作 checklist，不表示項目已自動執行或全部通過。Build／container 檢查不能取代實機功能驗證。

### Development

- [ ] `compose.yaml` 的 `build.target` 為 `dev`。
- [ ] dev container 可正常啟動。

### Release build

- [ ] `--target release` build 成功。
- [ ] `mobile_base:release` image 存在。

### Export

- [ ] `release/mobile_base_image.tar.gz` 存在。
- [ ] `release/compose.yaml` 存在。
- [ ] `release/.env` 存在。
- [ ] `release/start.sh` 存在且可執行。

### Deployment

- [ ] 正確版本的 image 已載入，container 使用該 image。
- [ ] container 正常運行。
- [ ] serial devices 可用。
- [ ] 現場 `.env` 與 `maps/` 已確認。
- [ ] 依 [MAPPING.md](../src/mobile_base_bringup/MAPPING.md) / [NAVIGATION.md](../src/mobile_base_bringup/NAVIGATION.md) 進行功能驗證。

## 12. Source Distribution Boundary

release stage 沒有 COPY repository 的 `src/` tree，也不複製 builder 的 `build/`；它繼承 `base` 並取得 ROS 2 安裝結果 `install/`。

`install/` 不代表所有內容都是 opaque binary。C/C++ packages 通常主要交付編譯後 artifacts；`ament_python` packages、Python launch files 與其他 installed Python files 仍可能以可閱讀形式存在。此邊界用於縮減交付 workspace 並分離開發與 runtime，不構成程式碼保密或防逆向工程保證。

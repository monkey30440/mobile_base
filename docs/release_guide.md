# mobile_base 客戶端 Release 打包與部署指南

本指南說明如何產出交付給客戶的二進位發布包。
所有原始碼均透過多階段編譯被封裝為二進位檔，客戶端完全無法存取源碼與 Dockerfile。

目錄結構規範：

```text
release/
└── YYYYMMDD_HHMMSS/
    ├── mobile_base_release_YYYYMMDD_HHMMSS/       (交付資料夾)
    │   ├── mobile_base_image.tar.gz               (二進位 Docker 映像檔)
    │   ├── compose.yaml                           (客戶端 Compose 設定)
    │   ├── .env                                   (環境變數)
    │   ├── maps/                                  (地圖與站點範本)
    │   └── start.sh                               (客戶端一鍵啟動腳本)
    └── mobile_base_release_YYYYMMDD_HHMMSS.tar.gz (單一交付壓縮檔)
```

---

## 開發端核心檔案（保留於本機專案庫，不交付給客戶）

1. [`Dockerfile.release`](../Dockerfile.release) - 多階段編譯 Dockerfile（只留二進位檔 install/）
2. [`compose.release.yaml`](../compose.release.yaml) - 客戶端 Compose 設定範本
3. [`scripts/export_release.sh`](../scripts/export_release.sh) - 一鍵打包與產出發布包腳本

---

## 檔案 1：Dockerfile.release

位於專案根目錄 [`Dockerfile.release`](../Dockerfile.release)：

```dockerfile
# ==========================================
# 階段 1：編譯建置環境 (Builder Stage)
# ==========================================
FROM mobile_base-mobile_base:latest AS builder

WORKDIR /ws

# 複製原始碼進編譯階段
COPY src /ws/src

# 執行 Release 編譯並移除偵錯符號 (Strip debug symbols) 以縮小體積並保護原始碼
RUN bash -c "source /opt/ros/jazzy/setup.bash && \
    colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release && \
    find /ws/install -type f -name '*.so*' -exec strip --strip-unneeded {} + 2>/dev/null || true; \
    find /ws/install/lib -type f -executable -exec strip --strip-unneeded {} + 2>/dev/null || true"

# ==========================================
# 階段 2：客戶端發布環境 (Release Stage)
# ==========================================
FROM mobile_base-mobile_base:latest AS runner

WORKDIR /workspaces/mobile_base

# ★ 關鍵：只複製編譯完成的 install 目錄，完全不包含 src 與 build 原始碼！
COPY --from=builder /ws/install /workspaces/mobile_base/install

# 設定環境變數自動載入
RUN echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc \
    && echo "source /workspaces/mobile_base/install/setup.bash" >> ~/.bashrc

CMD ["bash"]
```

---

## 檔案 2：compose.release.yaml

位於專案根目錄 [`compose.release.yaml`](../compose.release.yaml)：

```yaml
services:
  mobile_base:
    image: mobile_base:release
    container_name: mobile_base
    runtime: nvidia
    network_mode: host

    env_file:
      - .env

    environment:
      - DISPLAY=${DISPLAY}
      - ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0}
      - TOPIC_NAMESPACE=${TOPIC_NAMESPACE:-}

    volumes:
      # 僅掛載地圖目錄（讓客戶端能存放現場掃描出的地圖與站點檔案）
      - ./maps:/workspaces/mobile_base/maps
      - /tmp/.X11-unix:/tmp/.X11-unix:rw

    devices:
      - /dev/ttyUSB0:/dev/ttyUSB0
      - /dev/ttyACM0:/dev/ttyACM0

    working_dir: /workspaces/mobile_base
    stdin_open: true
    tty: true
    restart: unless-stopped
    command: sleep infinity
```

---

## 檔案 3：scripts/export_release.sh (一鍵打包腳本)

位於 [`scripts/export_release.sh`](../scripts/export_release.sh)：

```bash
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${WORKSPACE_ROOT}"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
RELEASE_BASE="${WORKSPACE_ROOT}/release/${TIMESTAMP}"
PKG_NAME="mobile_base_release_${TIMESTAMP}"
OUTPUT_DIR="${RELEASE_BASE}/${PKG_NAME}"
IMAGE_TAG="mobile_base:release"

echo "=================================================="
echo " 🚀 開始打包 mobile_base 發布版本"
echo " 專案目錄：${WORKSPACE_ROOT}"
echo " 產出目標：${OUTPUT_DIR}"
echo "=================================================="

# 1. 建立輸出資料夾
rm -rf "${OUTPUT_DIR}"
mkdir -p "${OUTPUT_DIR}/maps"

# 2. 建置 Release Docker Image (Multi-stage)
echo "[1/4] 🔨 建置二進位 Docker 映像檔 (${IMAGE_TAG})..."
docker build -f Dockerfile.release -t ${IMAGE_TAG} .

# 3. 導出 Docker 映像檔為壓縮包
echo "[2/4] 📦 匯出 Docker 映像檔至交付目錄 (可能需要數分鐘)..."
docker save ${IMAGE_TAG} | gzip > "${OUTPUT_DIR}/mobile_base_image.tar.gz"

# 4. 複製部署設定、地圖範本與產生客戶端啟動腳本
echo "[3/4] 📋 準備客戶端設定檔與啟動腳本 (不包含原始碼與 Dockerfile)..."
cp compose.release.yaml "${OUTPUT_DIR}/compose.yaml"
cp -r maps/template "${OUTPUT_DIR}/maps/"

# 產生預設 .env 範本
cat << 'EOF' > "${OUTPUT_DIR}/.env"
DISPLAY=:0
ROS_DOMAIN_ID=0
TOPIC_NAMESPACE=
EOF

# 產生客戶端一鍵安裝與啟動腳本
cat << 'EOF' > "${OUTPUT_DIR}/start.sh"
#!/bin/bash
set -e

echo "=== [mobile_base] 客戶端系統啟動 ==="

# 檢查映像檔是否已載入，若無則載入
if ! docker image inspect mobile_base:release >/dev/null 2>&1; then
    if [ -f mobile_base_image.tar.gz ]; then
        echo "--> 首次運行，正在載入 Docker 映像檔 (請稍候)..."
        docker load < mobile_base_image.tar.gz
    else
        echo "錯誤：找不到 mobile_base_image.tar.gz 映像檔！"
        exit 1
    fi
fi

# 啟動容器服務
echo "--> 啟動 mobile_base 服務容器..."
docker compose up -d

echo "✅ mobile_base 容器已成功在背景運行！"
echo "您可以透過以下指令進入容器或執行建圖/導航："
echo "  docker exec -it mobile_base bash"
EOF
chmod +x "${OUTPUT_DIR}/start.sh"

# 5. 打包為單一交付壓縮檔
echo "[4/4] 🗜️  壓縮為單一交付檔..."
tar -czvf "${RELEASE_BASE}/${PKG_NAME}.tar.gz" -C "${RELEASE_BASE}" "${PKG_NAME}"

echo "=================================================="
echo "🎉 打包完成！"
echo "交付資料夾：${OUTPUT_DIR}"
echo "交付壓縮檔：${RELEASE_BASE}/${PKG_NAME}.tar.gz"
echo "=================================================="
```

---

## 客戶端使用流程

將 `release/YYYYMMDD_HHMMSS/mobile_base_release_YYYYMMDD_HHMMSS.tar.gz` 交付給客戶：

1. 解壓縮：
   ```bash
   tar -xzvf mobile_base_release_*.tar.gz
   cd mobile_base_release_*
   ```

2. 一鍵啟動：
   ```bash
   ./start.sh
   ```

3. 操作建圖與導航：
   ```bash
   docker exec -it mobile_base bash
   # 進入後即可依 src/mobile_base_bringup/MAPPING.md / src/mobile_base_bringup/NAVIGATION.md 操作
   ```

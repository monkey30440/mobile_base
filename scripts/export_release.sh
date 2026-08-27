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

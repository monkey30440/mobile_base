#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RELEASE_DIR="${ROOT_DIR}/release"
IMAGE_NAME="mobile_base:release"

rm -rf "${RELEASE_DIR}"
mkdir -p "${RELEASE_DIR}/maps"

docker build \
  --target release \
  -t "${IMAGE_NAME}" \
  "${ROOT_DIR}"

docker save "${IMAGE_NAME}" | gzip > "${RELEASE_DIR}/mobile_base_image.tar.gz"

cp "${ROOT_DIR}/compose.release.yaml" "${RELEASE_DIR}/compose.yaml"

if [ -d "${ROOT_DIR}/maps/template" ]; then
  cp -a "${ROOT_DIR}/maps/template" "${RELEASE_DIR}/maps/"
fi

cat > "${RELEASE_DIR}/.env" <<'ENVEOF'
DISPLAY=:0
ROS_DOMAIN_ID=0
TOPIC_NAMESPACE=
MOBILE_BASE_INFLUXDB_TOKEN=
ENVEOF

cat > "${RELEASE_DIR}/start.sh" <<'STARTEOF'
#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if ! docker image inspect mobile_base:release >/dev/null 2>&1; then
  echo "Loading mobile_base:release image..."
  gzip -dc mobile_base_image.tar.gz | docker load
fi

docker compose up -d
STARTEOF

chmod +x "${RELEASE_DIR}/start.sh"

echo
echo "Release created at:"
echo "${RELEASE_DIR}"

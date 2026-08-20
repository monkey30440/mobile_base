#!/usr/bin/env bash

set -euo pipefail

if [[ -n "${MOBILE_BASE_REPOSITORY_ROOT:-}" ]]; then
  repository_root="${MOBILE_BASE_REPOSITORY_ROOT}"
elif [[ -d /workspaces/mobile_base ]]; then
  repository_root=/workspaces/mobile_base
else
  repository_root="$(git -C "${PWD}" rev-parse --show-toplevel)"
fi

timestamp="$(date +%Y%m%d_%H%M%S)"
map_directory="${repository_root}/maps/${timestamp}"
map_basename="${map_directory}/map"
map_yaml="${map_basename}.yaml"

mkdir -p "${map_directory}"

ros2 run nav2_map_server map_saver_cli \
  -t /map \
  -f "${map_basename}" \
  --fmt pgm \
  --mode trinary \
  --occ 0.65 \
  --free 0.25 \
  --ros-args \
  -p map_subscribe_transient_local:=true \
  -p save_map_timeout:=10.0

if [[ ! -f "${map_yaml}" || ! -f "${map_basename}.pgm" ]]; then
  echo "Map saver returned without creating map.yaml and map.pgm" >&2
  exit 1
fi

ros2 run mobile_base_mapping validate_map_readback "${map_yaml}"

echo "Map saved and validated: ${map_directory}"

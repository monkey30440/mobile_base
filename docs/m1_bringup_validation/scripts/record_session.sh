#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="$ROOT/logs/$STAMP"
mkdir -p "$OUT"

echo "$OUT"
{
  echo "date: $(date -Is)"
  echo "host: $(hostname)"
  echo "kernel: $(uname -a)"
  echo "user: $(id)"
  echo "pwd: $(pwd)"
  echo "git: $(git rev-parse --short HEAD 2>/dev/null || echo no-git)"
} > "$OUT/environment.txt"

ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null > "$OUT/serial_devices.txt" || true
for d in /dev/ttyUSB* /dev/ttyACM*; do
  [ -e "$d" ] || continue
  udevadm info -q property -n "$d" 2>/dev/null >> "$OUT/udev.txt" || true
done

dmesg --color=never 2>/dev/null | tail -n 300 > "$OUT/dmesg_tail.txt" || true
python3 - <<'PY' > "$OUT/python.txt" 2>&1
import sys
print(sys.version)
try:
 import serial; print('pyserial',serial.__version__)
except Exception as e: print('pyserial error',e)
PY

if command -v ros2 >/dev/null 2>&1; then
  ros2 --help >/dev/null 2>&1 || true
  ros2 control list_controllers > "$OUT/ros2_controllers.txt" 2>&1 || true
  ros2 control list_hardware_interfaces > "$OUT/ros2_hw_interfaces.txt" 2>&1 || true
  ros2 topic list > "$OUT/ros2_topics.txt" 2>&1 || true
  timeout 3 ros2 topic echo --once /joint_states > "$OUT/joint_states_once.txt" 2>&1 || true
  timeout 3 ros2 topic echo --once /driver/status > "$OUT/driver_status_once.txt" 2>&1 || true
fi

echo "Session recorded to: $OUT"
echo "Add your config/md2/motor-test outputs into this folder with tee."

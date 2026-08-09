#!/usr/bin/env bash
set -u

echo "== M1 bring-up preflight =="
echo "time: $(date -Is)"
echo "user: $(id)"
echo

echo "[serial devices]"
ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || echo "NO ttyUSB/ttyACM FOUND"
echo

echo "[groups]"
groups
echo

echo "[possible serial owners]"
for d in /dev/ttyUSB* /dev/ttyACM*; do
  [ -e "$d" ] || continue
  echo "-- $d"
  fuser "$d" 2>/dev/null || true
  udevadm info -q property -n "$d" 2>/dev/null | grep -E 'ID_VENDOR|ID_MODEL|ID_SERIAL' || true
done
echo

echo "[python / pyserial]"
python3 --version
python3 - <<'PY'
try:
    import serial
    print('pyserial:', serial.__version__)
except Exception as e:
    print('pyserial missing:', e)
    print('install: sudo apt install python3-serial')
PY

echo
echo "[kernel recent USB/tty messages]"
dmesg --color=never 2>/dev/null | grep -Ei 'ttyUSB|ttyACM|usb.*serial' | tail -n 30 || true

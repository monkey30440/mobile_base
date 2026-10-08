#!/usr/bin/env bash
# 執行前須先啟動 Description 與 Control。
exec ros2 run teleop_twist_keyboard teleop_twist_keyboard \
  --ros-args \
  -p stamped:=true \
  -p speed:=0.20 \
  -p turn:=0.20 \
  -r cmd_vel:=/base_controller/cmd_vel

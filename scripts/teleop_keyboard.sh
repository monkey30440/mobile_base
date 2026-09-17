#!/bin/bash

ros2 run teleop_twist_keyboard teleop_twist_keyboard \
  --ros-args \
  -p stamped:=true \
  -p speed:=0.20 \
  -p turn:=0.20 \
  -r cmd_vel:=/diff_drive_controller/cmd_vel
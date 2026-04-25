#!/usr/bin/env bash
set -euo pipefail

echo "[carla_teleop] Starting keyboard teleop on /cmd_vel"
echo "[carla_teleop] Use i/k for forward/back, j/l for turn, q/z to scale"

exec ros2 run teleop_twist_keyboard teleop_twist_keyboard \
  --ros-args \
  -r cmd_vel:=/cmd_vel

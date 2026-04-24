#!/usr/bin/env bash
set -euo pipefail

WORLD_PATH="${1:?Usage: run_headless.sh <world_usd_path>}"

echo "WORLD PATH IS ${WORLD_PATH}"

# export inside container
export ROS_DISTRO=jazzy
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export FASTRTPS_DEFAULT_PROFILES_FILE=/dds-cfg/fastdds.xml
export LD_LIBRARY_PATH=${LD_LIBRARY_PATH:-}:/isaac-sim/exts/isaacsim.ros2.bridge/jazzy/lib

# run isaac backend
cd /isaac-sim
./runheadless.sh --exec "/start_realisation.py ${WORLD_PATH}"

#!/usr/bin/env bash
set -euo pipefail

export ROS_DISTRO=jazzy
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export FASTRTPS_DEFAULT_PROFILES_FILE=infra/dds-cfg/fastdds.xml

ros2 run teleop_twist_keyboard teleop_twist_keyboard

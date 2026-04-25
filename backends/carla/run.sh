#!/usr/bin/env bash
set -euo pipefail

MAP_NAME="${1:?Usage: run.sh <map_name> [rendering_mode]}"
RENDERING_MODE="${2:-gui}"

case "$RENDERING_MODE" in
  gui)
    RENDER_FLAGS="-opengl -nosound"
   ;;
  offscreen)
    RENDER_FLAGS="-RenderOffScreen -nosound"
    ;;
  no_rendering)
    RENDER_FLAGS="-nullrhi -nosound"
    ;;
  *)
    echo "Unknown rendering mode: $RENDERING_MODE" >&2
    exit 1
    ;;
esac

DISPLAY_ARGS=(
  -e DISPLAY="${DISPLAY:-}"
  -e XDG_RUNTIME_DIR=/tmp
  -e SDL_VIDEODRIVER=x11
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw
)

docker run --rm \
  --name carla-sim \
  --device nvidia.com/gpu=all \
  --net=host \
  -e NVIDIA_VISIBLE_DEVICES=all \
  -e NVIDIA_DRIVER_CAPABILITIES=graphics,utility,display,video,compute \
  -e VK_ICD_FILENAMES=/run/opengl-driver/share/vulkan/icd.d/nvidia_icd.x86_64.json \
  -v /run/opengl-driver:/run/opengl-driver:ro \
  "${DISPLAY_ARGS[@]}" \
  carlasim/carla:0.9.16 \
  bash CarlaUE4.sh $RENDER_FLAGS --ros2

#!/usr/bin/env bash
set -euo pipefail

WORLD_PATH="${1:?Usage: run.sh <world_usd_path>}"

docker run \
  --name isaac-sim \
  --entrypoint bash --rm \
  --device nvidia.com/gpu=all \
  --network host \
  -e ACCEPT_EULA=Y   -e OMNI_ENV_PRIVACY_CONSENT=Y   -e NVIDIA_DRIVER_CAPABILITIES=all \
  -u 1234:1234 \
  -v $PWD/infra/dds-cfg:/dds-cfg \
  -v ~/docker/isaac-sim/cache/main:/isaac-sim/.cache:rw \
  -v ~/docker/isaac-sim/cache/computecache:/isaac-sim/.nv/ComputeCache:rw \
  -v ~/docker/isaac-sim/logs:/isaac-sim/.nvidia-omniverse/logs:rw \
  -v ~/docker/isaac-sim/config:/isaac-sim/.nvidia-omniverse/config:rw \
  -v ~/docker/isaac-sim/data:/isaac-sim/.local/share/ov/data:rw \
  -v ~/docker/isaac-sim/pkg:/isaac-sim/.local/share/ov/pkg:rw \
  -v $PWD/scenarios/warehouse_teleop/isaac/worlds:/worlds \
  -v $PWD/scenarios/warehouse_teleop/isaac/graphs:/graphs \
  -v $PWD/backends/isaac/run_headless.sh:/run_headless.sh:ro \
  -v $PWD/backends/isaac/start_realisation.py:/start_realisation.py:ro \
  nvcr.io/nvidia/isaac-sim:5.1.0 \
  /run_headless.sh "$WORLD_PATH"


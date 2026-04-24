# Simulation Platform (WIP)

## Overview

This repository is an experimental but increasingly structured **robotics simulation platform** designed to:

- Support multiple simulation backends (e.g. Isaac Sim, Gazebo)
- Keep the **ROS 2 application layer stable and reusable**
- Enable **controlled experiments** (degradation, sweeps, reproducibility)
- Remain **declarative and portable** via Nix + Docker

This is both:
- a **practical engineering system** for demos (AMR, AV, etc.)
- a **research platform** supporting PhD work on system architecture, abstraction, and integration

---

## Core Idea

Separate the system into clean layers:

- **Backends** → physics + world + observation realisation  
- **Contracts** → stable interfaces (ROS topics, semantics)  
- **Application layer (ROS)** → control, perception, planning  
- **Frontend** → visualisation only  

---

## Key Architecture Concepts

### Contract-First Design

Everything declares:
- what it **provides**
- what it **requires**

---

### Observation Model (Sensors)

#### Observation Affordances (World)
- geometry
- reflectivity
- lighting
- dynamics

#### Observation Realisation (Backend)
- RTX lidar (Isaac)
- ray sensors (Gazebo)
- cameras, IMU

#### Observation Contracts
- `/scan`
- `/image_raw`
- `/imu`
- `/odom`

#### Observation Transforms (ROS layer)
- SLAM
- perception
- filtering
- degradation

---

## Technologies

- ROS 2 (Jazzy)
- Docker
- Nix (nix-ros-overlay)
- Isaac Sim
- Gazebo

---

## What We Got Working

- Isaac Sim headless in Docker
- ROS 2 external (host/container)
- ROS bridge functional
- `/cmd_vel` driving robot
- DDS communication fixed

---

## Critical DDS Fix

### Problem
Topics visible but no data flow.

### Cause
Fast DDS default = shared memory (breaks across Docker boundary)

### Solution

```bash
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export FASTRTPS_DEFAULT_PROFILES_FILE=~/.ros/fastdds.xml
```

Example XML:

```xml
<profiles>
  <transport_descriptors>
    <transport_descriptor>
      <transport_id>udp_transport</transport_id>
      <type>UDPv4</type>
    </transport_descriptor>
  </transport_descriptors>
  <participant profile_name="participant_profile" is_default_profile="true">
    <rtps>
      <useBuiltinTransports>false</useBuiltinTransports>
      <userTransports>
        <transport_id>udp_transport</transport_id>
      </userTransports>
    </rtps>
  </participant>
</profiles>
```

---

## Key Insight

This is an example of **abstraction leakage**:

- ROS appears transparent
- DDS transport assumptions break in Docker
- system “looks connected” but isn’t

---

## Current Status

- Isaac realisation works end-to-end via `sim-platform`
- Nix devshell provides ROS 2 Jazzy app/runtime environment
- Runtime resolves experiment → app → realisation → backend
- Backend readiness and cleanup are handled by the runtime
- CARLA feasibility spike confirms server/client workflow and NixOS graphics requirements

## Next Steps

1. Harden Isaac AMR teleop realisation
2. Add odometry and `/clock`
3. Add CARLA backend spike as second-domain realisation
4. Introduce first degradation experiment

---

## Status

Work in progress → moving from PoC to structured platform

---

## Philosophy

Simulation =  
backend-native execution + contract-governed interfaces + ROS application logic

## Notes

### CARLA on NixOS / Docker

CARLA may require the host NVIDIA graphics stack to be mounted into the container:

- mount `/run/opengl-driver`
- set `VK_ICD_FILENAMES=/run/opengl-driver/share/vulkan/icd.d/nvidia_icd.x86_64.json`
- set `NVIDIA_DRIVER_CAPABILITIES=graphics,utility,display,video,compute`

Without this, CARLA may fall back to lavapipe/software Vulkan, causing freezes and very slow client calls.

Command dump:

```
docker run --rm -it \
  --name carla-sim \
  --device nvidia.com/gpu=all \
  --net=host \
  -e DISPLAY=$DISPLAY \
  -e XDG_RUNTIME_DIR=/tmp \
  -e SDL_VIDEODRIVER=x11 \
  -e NVIDIA_VISIBLE_DEVICES=all \
  -e NVIDIA_DRIVER_CAPABILITIES=all \
  -e NVIDIA_VISIBLE_DEVICES=all \
  -e NVIDIA_DRIVER_CAPABILITIES=graphics,utility,display,video,compute \
  -e VK_ICD_FILENAMES=/run/opengl-driver/share/vulkan/icd.d/nvidia_icd.x86_64.json \
  -v /run/opengl-driver:/run/opengl-driver:ro -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  carlasim/carla:0.9.16 \
  bash CarlaUE4.sh -nosound

```

^^ runs carla with gui on wayland + NVIDIA desktop

### NVIDIA Isaac

You can run view and interact with the running isaac server instance using the streaming client, available for download from the relevant NVIDIA webpage as an appimage.


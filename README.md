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

- **Backends** → physics + world + observation realization  
- **Contracts** → stable interfaces (ROS topics, semantics)  
- **Application layer (ROS)** → control, perception, planning  
- **Frontend** → visualization only  

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

#### Observation Realization (Backend)
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

## Next Steps

1. AMR teleop on both Gazebo + Isaac  
2. Add odometry + lidar  
3. Introduce degradation experiments  
4. Expand backend support  

---

## Status

Work in progress → moving from PoC to structured platform

---

## Philosophy

Simulation =  
backend-native execution + contract-governed interfaces + ROS application logic


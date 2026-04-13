# Simulation Platform Architecture v0.1

## 1. Purpose

This platform supports robotics experiments across heterogeneous simulation backends without binding research logic to any one simulator.

Goals:
- build and run realistic demos quickly
- stable ROS application layer
- backend modularity
- reproducible experiments
- support for degradation and parameter sweeps

---

## 2. Design Principles

**Contract-first**

All major components declare what they provide and what they require. Composition is based on explicit compatibility, not tribal knowledge.

**Backend-native where it matters**

Worlds, assets, and simulator-specific machinery stay native to each backend unless there is a real reason to unify them.

**Stable seams over maximum abstraction**

Only interfaces that are meaningfully reusable get standardized. Everything else stays local to adapters.

**ROS as application surface**

Control, planning, perception, evaluation, and most experiment logic live in the ROS layer, not in the simulator.

**Thin frontend**

The frontend is for viewing and operating the system, not for owning behavior.

**Reproducibility by default**

The application layer should remain declarative and portable through Nix. Simulation infrastructure should remain containerized and composable.

---

## 3. System Model

The platform is composed of four layers.

### Backend Layer

A backend owns the simulation engine and all machinery needed to realize a scenario in that engine.

Examples:

- Gazebo
- Isaac Sim
- CARLA
- AirSim

A backend is responsible for:

- physics stepping
- sensor generation
- robot embodiment in simulation
- world execution
- backend-specific bridge/adaptation into ROS-facing interfaces

A backend is not responsible for:

- experiment logic
- research controllers
- planning algorithms
- evaluation metrics.

### Scenario Layer

A scenario defines the semantic shape of an experiment.

A scenario is not a full universal world representation. It is a backend-agnostic description of:

- the task
- environment class
- required capabilities
- initial conditions
- success/failure criteria
- degradation knobs
- and experiment metadata

A backend then realizes that scenario using native assets and configuration.

### Application Layer

The application layer is the main development surface.

It contains:

- controllers
- planners
- perception
- evaluation
- telemetry
- experiment runners
- degradation injectors
- and orchestration logic that is not simulator-specific

This layer talks in ROS interfaces and should depend on contracts, not specific simulators.

### View Layer

The view layer exposes state to humans.

Examples:

- Foxglove
- RViz
- Isaac streaming client
- web dashboards

It should observe and operate, but not contain essential domain logic.

---

## 4. Core Entities

### 4.1 Backend

A backend is an implementation of simulator-specific execution.

A backend declares:

- supported domains
- supported robot contracts
- supported sensor families
- lifecycle features
- timing/clock support
- bridge support
- exclusions and constraints

Example shape:

```yaml
backend:
  name: isaac
  supports:
    domains: [amr, perception]
    robot_contracts: [differential_drive]
    sensors: [lidar, rgb_camera, imu]
    features: [sim_clock, ros2_bridge, streaming]
  excludes:
    domains: [av_fullstack]
```

### 4.2 Scenario

A scenario defines a taskful experimental setting.

Example shape:

```yaml
scenario:
  name: warehouse_teleop
  domain: amr
  environment_class: warehouse_small
  requires:
    robot_contracts: [differential_drive]
    features: [sim_clock]
  optional:
    sensors: [lidar]
  initial_conditions:
    robot_spawn: [x, y, yaw]
  success_criteria:
    type: manual_operation
```

### 4.3 Robot

A robot is defined by contracts, not only by assets.

It declares:

- structural contract
- interface contract
- behavioral contract
- optional capabilities

Example shape:

```yaml
robot:
  name: turtlebot_like
  provides:
    structure: [mobile_base, differential_drive]
    interfaces:
      commands: [/cmd_vel]
      observations: [/odom, /tf]
      optional: [/scan]
    behavior:
      resettable: true
      sim_clock_aware: true
```

### 4.4 Experiment

An experiment is a runnable composition of:

- one backend
- one scenario realization
- one robot realization
- one application stack
- and zero or more perturbations

---

## 5. Observation Model (Sensors)

### 5.1 Observation Affordances (World / Backend Layer)

Backends expose what observations are physically possible:

- geometry visibility
- material properties (reflectivity)
- lighting conditions
- dynamics

These are not sensors themselves, but what the world *affords* sensing.

---

### 5.2 Observation Realization (Backend Adapters)

Backend-native implementations:

- lidar raycasting / RTX lidar
- camera rendering
- IMU physics
- radar simulation

This is equivalent to platform-specific “device drivers”.

---

### 5.3 Observation Contracts (Shared Layer)

Stable ROS-facing interfaces:

- `/scan` (LaserScan)
- `/image_raw`
- `/imu`
- `/odom`

Define:
- message types
- timing semantics
- coordinate frames
- lifecycle behavior

---

### 5.4 Observation Transforms (Application Layer)

All higher-level processing:

- SLAM
- perception
- filtering
- fusion
- degradation injection

---

### 5.5 Key Principle

Backends provide affordances and realization.
Contracts standardize access.
Applications consume and transform observations.

---

## 6. Contracts

Contracts are the central architectural device.

There are three main contract types.

### 6.1 Structural contracts

These describe embodiment and topology.

Examples:

- `differential_drive`
- ackermann
- quadrotor
- manipulator
- humanoid

These determine which controllers and planners are meaningful.

### 6.2 Interface contracts

These describe how components interact.

Examples:

- subscribes to `/cmd_vel`
- publishes /odom
- publishes /tf
- optional /scan
- supports reset
- supports pause/resume
- provides sim clock

These are the primary seams across which reuse happens.

### 6.3 Behavioral contracts

These describe expected runtime semantics.

Examples:

- command topic consumed while simulation is running
- observations timestamped against sim clock
- reset returns system to defined initial state
- odometry semantics stable enough for downstream consumers
- supports deterministic replay under fixed seed where possible

Behavioral contracts matter because identical topic names do not guarantee equivalent semantics.

---

## 7. Compatibility Model

Composition should be governed by explicit compatibility checks.

A composition is valid when:

- the backend supports the scenario’s domain
- the robot satisfies the scenario’s required structural contract
- the backend supports that robot contract
- required interfaces are available
- required lifecycle features are available
- and no exclusion rules are triggered

There are three useful relationship types.

### Compatible

A component can be composed with another component under current requirements.

### Exclusive

A component cannot coexist with another component in the same composition.

Example:

a backend that does not support a required domain,
a robot lacking the required embodiment contract.

### Conditional

A component is compatible only if additional features are enabled.

Example:

lidar-supported scenario only if the backend and robot realization both provide lidar.

---

## 8. Backend Adapter Model

Each backend should be implemented as an adapter around native simulator machinery.

A backend adapter is responsible for:

- launching the simulator
- realizing a scenario in backend-native form
- instantiating backend-native robot assets
- exposing required ROS interfaces
- managing simulator-specific lifecycle
- normalizing simulator-specific quirks behind contracts

Examples:

- Isaac adapter handles ROS bridge env, DDS profile setup, USD stage loading, action graph setup
- Gazebo adapter handles world files, plugins, ROS bridge plugins, and launch wiring

>The adapter is where simulator weirdness belongs.

---

## 9. Scenario Realization Model

A scenario has two levels:

### Semantic scenario

Backend-agnostic description of task and requirements.

### Backend realization

A native implementation of that scenario for a given backend.

Examples:

- `warehouse_teleop` as semantic scenario
- `warehouse_teleop@isaac` as USD stage plus backend-specific hooks
- `warehouse_teleop@gazebo` as SDF world plus plugins

This avoids forcing a universal world format too early while still preserving cross-backend comparability.

---

## 10. Robot Realization Model

Likewise, a robot has:

- a semantic contract identity
- and one or more backend realizations

Example:

- `turtlebot_like` as semantic robot contract
- `turtlebot_like@isaac`
- `turtlebot_like@gazebo`

A backend realization may differ in asset representation and internal machinery, but must satisfy the same exposed contract.

---

## 11. Event Model

This system should be thought of as event-driven rather than static MVC.

Important events include:

- simulation started
- simulation paused
- simulation reset
- robot spawned
- command received
- sensor published
- degradation injected
- experiment completed
- experiment failed

This matters because many important semantics are temporal:

- when commands take effect
- when resets happen
- how clock is propagated
- whether observations are valid before or after initialization

The architecture should model these events explicitly where useful.

---

## 12. First Vertical Slice

The first slice should stay small.

### Slice: AMR teleop

This slice exists to prove the architecture, not to maximize features.

**Scenario**
- `warehouse_teleop`

**Robot contract**
- `differential_drive`

Required interfaces
- `/cmd_vel`
- `/odom`
- `/tf`
- `/clock`

**Optional interfaces**
- `/scan`

**Backends**
- Gazebo
- Isaac

**Success criterion**

The same ROS teleop application can drive a robot in both backends using the same command interface.

This is the right first proof because it validates:

- backend modularity
- ROS application stability
- scenario realization
- robot contract realization
- simulator/ROS bridge correctness

---

## 13. Repository Structure

Proposed structure:

```
backends/
  gazebo/
  isaac/

scenarios/
  warehouse_teleop/
    scenario.yaml
    gazebo/
    isaac/

robots/
  turtlebot_like/
    robot.yaml
    gazebo/
    isaac/

apps/
  amr_teleop/
  amr_nav/
  experiment_runner/

experiments/
  teleop_smoke/
  backend_comparison/
  degradation_trials/

infra/
  docker/
  nix/
  scripts/
```

### Meaning of each directory

`backends/`
contains simulator-specific launcher and adapter logic.

`scenarios/`
contains semantic scenario definitions and backend realizations.

`robots/`
contains semantic robot contracts and backend realizations.

`apps/`
contains ROS application logic intended to remain backend-agnostic.

`experiments/`
contains runnable compositions and sweep definitions.

`infra/`
contains reproducibility and orchestration machinery.

---

## 14. Immediate Implementation Plan

### Step 1

Write the first contract files:

- scenario.yaml for `warehouse_teleop`
- robot.yaml for `turtlebot_like`
- backend.yaml for gazebo
- backend.yaml for isaac

### Step 2

Build one shared ROS app:

- `amr_teleop`

This should assume only:

- /`cmd_vel`
- /`clock`
- optionally `/odom` and `/tf`

### Step 3

Implement two backend realizations:

- `warehouse_teleop@gazebo`
- `warehouse_teleop@isaac`

### Step 4

Prove the same teleop flow works against both.

### Step 5

Add one observational contract:

- odometry first,
- lidar second.

### Step 6

Introduce one controlled perturbation:

- latency,
- dropout,
- or command degradation.

That turns the platform from a demo harness into an experimental system.

---

## 15. Non-Goals for v0.1

To keep this manageable, v0.1 should explicitly not attempt:

- universal geometry/world translation
- universal robot asset conversion
- full backend interchangeability across all domains
- generic orchestration for every simulator category
- large-scale plugin ecosystems

The point of v0.1 is to establish stable architectural seams through one strong vertical slice.

---

## 16. Architectural Thesis

This platform treats simulation not as a monolithic application but as a composition of:

- backend-native world execution
- contract-governed robot and scenario semantics
- ROS-based application logic
- and thin observational frontends

The platform should preserve backend specificity where necessary while standardizing only those interfaces and semantics that are valuable to keep stable across experiments.

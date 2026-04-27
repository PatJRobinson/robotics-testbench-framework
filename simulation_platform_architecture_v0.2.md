# Simulation Platform Architecture v0.2

## 1. Purpose

This platform supports robotics experiments across heterogeneous simulation backends without binding research logic to any one simulator.

Goals:

- build and run realistic demos quickly
- stable ROS application layer
- backend modularity
- reproducible experiments
- explicit handling of integration complexity
- support for degradation and parameter sweeps

---

## 2. Design Principles

**Contract-first**

All components declare what they provide and require using named contracts. Composition is governed by explicit compatibility, not implicit knowledge.

**Backend-native where it matters**

Worlds, assets, and simulator machinery remain native unless there is a clear benefit to unification.

**Stable seams over maximum abstraction**

Only stabilise interfaces that enable reuse. Do not prematurely generalise backend-specific details.

**ROS as application surface**

Control, planning, perception, and evaluation live in the ROS layer.

**Explicit integration over hidden abstraction**

Differences between backends are not erased. They are surfaced through contracts, bindings, and adapters.

**Thin frontend**

View systems observe and operate, but do not own domain logic.

**Reproducibility by default**

Application logic is declarative and portable (Nix). Simulation infrastructure remains containerised and composable.

---

## 3. System Model

### Backend Layer

Owns simulation execution:

- physics
- sensors
- embodiment
- world stepping
- native interfaces

Backends expose capabilities via **scenario realisations**.

---

### Scenario Layer

Defines the semantic shape of an experiment:

- task
- environment class
- required capabilities
- success criteria
- initial conditions

A scenario is not a world file. It is a **semantic contract**.

---

### Application Layer

Primary development surface:

- controllers
- planners
- perception
- evaluation
- orchestration

Consumes contracts via ROS.

---

### View Layer

Human-facing observation/control:

- RViz
- Foxglove
- Isaac client
- CARLA GUI

Two types:

Attachable clients (ROS-based)  
Backend-native GUIs (non-attachable)

---

## 4. Core Concepts

### 4.1 Contracts

A contract is a **named expectation** about semantics and representation.

Examples:

`differential_drive_cmd_vel`
`ackermann_vehicle_control`
`rgb_camera`
`sim_clock`

A contract defines:

- meaning (semantics)
- expected representation class (e.g. Twist, Image)
- usage expectations

A contract does **not** imply identical backend implementations.

---

### 4.2 Bindings

A binding is how a realisation exposes a contract.

Example:

```
contract: differential_drive_cmd_vel  
binding:  
  type: ros_topic  
  name: /cmd_vel  
  messageType: geometry_msgs/msg/Twist
```

Bindings define:

- transport (ROS topic, Python API, etc.)
- concrete identifiers (topic names, endpoints)
- message types

---

### 4.3 Binding Configuration

Bindings may be partially configurable.

```
binding:  
  type: ros_topic  
  messageType: geometry_msgs/msg/Twist  
  defaultName: /cmd_vel  
  configurable:  
    - name
```

Applications provide:

```
bindingConfig:  
  name: /robot1/cmd_vel
```

Rule:

Realisations define binding capability.  
Apps specify binding preferences.  
Runtime resolves final binding.

---

### 4.4 Adapters

Adapters mediate between contracts and bindings.

Two kinds:

#### Binding (conformance) adapters

backend-native → contract representation

Examples:

- CARLA camera → ROS Image
- Isaac lidar → PointCloud2

#### Semantic adapters

contract A → contract B

Examples:

- `/cmd_vel` → CARLA VehicleControl

Adapters make integration assumptions explicit.

---

## 5. Realisation Model

A **realisation** binds:

- a scenario
- a backend
- a platform
- a set of provided contracts

It may consist of multiple processes:

backend server  
scenario client  
adapter processes

A realisation declares:

provides:  
  commands:  
  observations:  
  platforms:  
  adapters:

Each provided contract includes its binding.

A realisation is the unit of execution.

---

## 6. Observation Model

### 6.1 Affordances (Backend)

What can be sensed:

- geometry
- lighting
- dynamics

---

### 6.2 Realisation (Backend-native)

How sensors are implemented:

- raycasting
- rendering
- physics-based simulation

---

### 6.3 Contracts

Stable observation surfaces:

`rgb_camera`
`odometry`
`imu`
`sim_clock`

---

### 6.4 Transformations

Application-level processing:

- SLAM
- perception
- filtering
- degradation

---

### 6.5 Principle

Backends produce data  
Realisations expose contracts  
Applications consume contracts

---

## 7. Compatibility Model

Composition is valid when:

- required contracts are provided
- adapters satisfy missing contracts
- platform contracts match
- backend constraints are respected

Relationship types:

compatible  
exclusive  
conditional

---

## 8. Adapter Model

Adapters are first-class architectural elements.

They:

- normalise representations
- translate semantics
- expose limitations

Example:

`/cmd_vel` → VehicleControl is approximate, not equivalent

Adapters should declare:

```
kind: binding | semantic  
provides: ...  
consumes: ...  
limitations: ...
```

---

## 9. Scenario Realisation Model

Two levels:

### Semantic scenario

Backend-agnostic definition

### Realisation

Backend-native implementation

Examples:

`warehouse_teleop@isaac`
`urban_teleop@carla`

---

## 10. Platform Model

Platforms are defined by contracts:

`differential_drive`
`ackermann_vehicle`

A realisation provides platform contracts.

---

## 11. Event Model

System is event-driven:

- simulation started
- actor spawned
- command applied
- sensor published
- experiment completed

Temporal semantics matter.

---

## 12. Current Vertical Slices

### AMR (Isaac / Gazebo)

- differential drive
- `/cmd_vel`
- `/odom`
- `/tf`

### CARLA (Urban driving)

- Ackermann vehicle
- RGB camera
- `/clock`
- semantic adapter for `/cmd_vel`

This second slice introduces:

non-equivalent control semantics  
backend-native ROS exposure  
adapter-mediated compatibility

---

## 13. Repository Structure

Unchanged (see v0.1), but interpretation refined:

realisations = contract-binding implementations  
apps = contract consumers

---

## 14. Updated Implementation Direction

Next steps:

1. Make contracts explicit in YAML
2. Introduce binding + bindingConfig model
3. Add runtime compatibility checks
4. Record contract resolution in run metadata
5. Refine observation contracts
6. Add degradation via adapters

---

## 15. Non-Goals (v0.2)

Still excluded:

- universal world representation
- universal robot assets
- full simulator interchangeability
- strict contract schemas (yet)

---

## 16. Architectural Thesis

This platform treats simulation as a composition of:

- backend-native execution
- realisation-level contract binding
- explicit adapter-mediated integration
- ROS-based application logic

Contracts do not eliminate differences between simulators.

They make those differences **explicit, inspectable, and composable**.

---

## Key Evolution from v0.1

v0.1: interface-centric  
v0.2: contract + binding + adapter-centric

This shift enables:

- honest cross-backend comparison
- explicit handling of semantic mismatch
- controlled abstraction instead of hidden coupling

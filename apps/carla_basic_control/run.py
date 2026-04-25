#!/usr/bin/env python3

import time
import carla


ROLE_NAME = "sim_platform_ego"


def find_ego(world):
    for actor in world.get_actors():
        if actor.attributes.get("role_name") == ROLE_NAME:
            return actor
    return None


actors = []

def main():
    print("[app] connecting to CARLA")

    client = carla.Client("localhost", 2000)
    client.set_timeout(10.0)

    world = client.get_world()

    bp_lib = world.get_blueprint_library()

    vehicle_bp = bp_lib.filter("vehicle.*")[0]
    vehicle_bp.set_attribute("role_name", "sim_platform_ego")

    spawn_point = world.get_map().get_spawn_points()[0]
    vehicle = world.spawn_actor(vehicle_bp, spawn_point)
    actors.append(vehicle)

    print("[app] searching for ego vehicle")
    ego = None

    for _ in range(20):
        ego = find_ego(world)
        if ego:
            break
        time.sleep(0.5)

    if ego is None:
        raise RuntimeError("Ego vehicle not found")

    print(f"[app] found ego id={ego.id}")

    start_loc = ego.get_location()
    print(f"[app] start location: {start_loc}")

    print("[app] applying control")
    ego.apply_control(carla.VehicleControl(throttle=0.4, steer=0.0))

    time.sleep(3)

    end_loc = ego.get_location()
    print(f"[app] end location: {end_loc}")

    dx = end_loc.x - start_loc.x
    dy = end_loc.y - start_loc.y

    print(f"[app] delta: dx={dx:.2f}, dy={dy:.2f}")

    if abs(dx) < 0.1 and abs(dy) < 0.1:
        raise RuntimeError("Vehicle did not move")

    print("[app] success: vehicle moved")

if __name__ == "__main__":
    main()

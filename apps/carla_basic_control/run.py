#!/usr/bin/env python3

import math
import time
import carla

ROLE_NAME = "sim_platform_ego"


def find_ego(world, role_name=ROLE_NAME, timeout=20.0):
    start = time.time()

    while time.time() - start < timeout:
        for actor in world.get_actors().filter("vehicle.*"):
            if actor.attributes.get("role_name") == role_name:
                return actor

        print(f"[app] waiting for ego role_name={role_name}")
        time.sleep(0.5)

    raise RuntimeError(f"Ego vehicle not found: role_name={role_name}")


def dist_xy(a, b):
    return math.hypot(b.x - a.x, b.y - a.y)

def update_spectator(world, ego):
    transform = ego.get_transform()

    spectator = world.get_spectator()
    spectator.set_transform(
        carla.Transform(
            transform.location + carla.Location(x=-0.0, z=4.0),
            carla.Rotation(pitch=-20.0, yaw=transform.rotation.yaw),
        )
    )

def main():
    print("[app] connecting to CARLA")
    client = carla.Client("localhost", 2000)
    client.set_timeout(10.0)

    world = client.get_world()

    print("[app] finding ego vehicle")
    ego = find_ego(world)

    update_spectator(world, ego)

    start = ego.get_location()
    print(f"[app] start: x={start.x:.2f}, y={start.y:.2f}, z={start.z:.2f}")

    print("[app] applying throttle")
    ego.apply_control(carla.VehicleControl(throttle=0.45, steer=0.0, brake=0.0))

    time.sleep(5.0)

    ego.apply_control(carla.VehicleControl(throttle=0.0, brake=1.0))

    end = ego.get_location()
    moved = dist_xy(start, end)

    print(f"[app] end:   x={end.x:.2f}, y={end.y:.2f}, z={end.z:.2f}")
    print(f"[app] moved: {moved:.2f} m")

    if moved < 0.5:
        raise RuntimeError(f"Vehicle did not move enough: {moved:.2f} m")

    print("[app] success")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3

import argparse
import signal
import sys
import time

import carla


STOP = False


def handle_stop(signum, frame):
    global STOP
    STOP = True


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=2000)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--map", default="Town01")
    parser.add_argument("--role-name", default="sim_platform_ego")
    parser.add_argument("--fixed-delta-seconds", type=float, default=0.05)
    parser.add_argument("--tick-rate-print", type=int, default=100)
    return parser.parse_args()


def destroy_existing_actors(world, role_name):
    destroyed = 0

    for actor in world.get_actors():
        if actor.attributes.get("role_name") == role_name:
            actor.destroy()
            destroyed += 1

    return destroyed

def update_spectator(world, ego):
    transform = ego.get_transform()

    spectator = world.get_spectator()
    spectator.set_transform(
        carla.Transform(
            transform.location + carla.Location(x=-0.0, y=-8.0, z=4.0),
            carla.Rotation(pitch=-20.0, yaw=transform.rotation.yaw),
        )
    )

def spawn_ego_vehicle(world, role_name):
    bp_lib = world.get_blueprint_library()

    vehicle_bp = bp_lib.find("vehicle.lincoln.mkz_2020")
    vehicle_bp.set_attribute("ros_name", "ego")

    if vehicle_bp.has_attribute("role_name"):
        vehicle_bp.set_attribute("role_name", role_name)

    spawn_points = world.get_map().get_spawn_points()

    for spawn_point in spawn_points:
        vehicle = world.try_spawn_actor(vehicle_bp, spawn_point)

        if vehicle is not None:
            print(f"[carla-realisation] spawned vehicle ros_name={vehicle_bp.get_attribute('ros_name').as_str()}")
            print([name for name in dir(vehicle) if "ros" in name.lower()])

            if hasattr(vehicle, "enable_for_ros"):
                print("[carla-realisation] enabling vehicle for ROS")
                vehicle.enable_for_ros()
            else:
                print("[carla-realisation] vehicle has no enable_for_ros()")

            return vehicle

    raise RuntimeError("Could not spawn ego vehicle at any map spawn point")

def spawn_rgb_camera(world, vehicle):
    bp_lib = world.get_blueprint_library()

    bp = bp_lib.filter("sensor.camera.rgb")[0]
    bp.set_attribute("ros_name", "rgb")
    bp.set_attribute("role_name", "rgb")
    bp.set_attribute("image_size_x", "600")
    bp.set_attribute("image_size_y", "400")
    bp.set_attribute("fov", "90")

    transform = carla.Transform(
        location=carla.Location(x=-4.5, y=0.0, z=2.5),
        rotation=carla.Rotation(roll=0.0, pitch=20.0, yaw=0.0),
    )

    camera = world.spawn_actor(bp, transform, attach_to=vehicle)
    camera.enable_for_ros()

    print("[carla-realisation] spawned ROS RGB camera")
    return camera

def main():
    signal.signal(signal.SIGINT, handle_stop)
    signal.signal(signal.SIGTERM, handle_stop)

    args = parse_args()

    print("[carla-realisation] connecting to CARLA")
    client = carla.Client(args.host, args.port)
    client.set_timeout(args.timeout)

    print(f"[carla-realisation] loading map: {args.map}")
    world = client.load_world(args.map)

    print("[carla-realisation] configuring synchronous mode")
    settings = world.get_settings()
    settings.synchronous_mode = True
    settings.fixed_delta_seconds = args.fixed_delta_seconds
    world.apply_settings(settings)

    actors = []

    try:
        print(f"[carla-realisation] cleaning old actors role_name={args.role_name}")
        destroyed = destroy_existing_actors(world, args.role_name)
        print(f"[carla-realisation] destroyed old actors: {destroyed}")

        print("[carla-realisation] spawning ego vehicle")
        ego = spawn_ego_vehicle(world, args.role_name)
        actors.append(ego)
        print(f"[carla-realisation] spawned ego id={ego.id}")

        print("[carla-realisation] spawning rgb camera")
        camera = spawn_rgb_camera(world, ego)
        actors.append(camera)
        print(f"[carla-realisation] spawned rgb id={camera.id}")

        print("[carla-realisation] ready")

        tick = 0
        while not STOP:
            world.tick()
            tick += 1

            update_spectator(world, ego)

            if tick % args.tick_rate_print == 0:
                loc = ego.get_location()
                print(
                    f"[carla-realisation] tick={tick} "
                    f"ego=({loc.x:.2f}, {loc.y:.2f}, {loc.z:.2f})",
                    flush=True,
                )

    finally:
        print("[carla-realisation] cleaning up")
        for actor in actors:
            if actor.is_alive:
                actor.destroy()

        try:
            settings = world.get_settings()
            settings.synchronous_mode = False
            settings.fixed_delta_seconds = None
            world.apply_settings(settings)
        except Exception as e:
            print(f"[carla-realisation] failed to restore settings: {e}")

        print("[carla-realisation] stopped")


if __name__ == "__main__":
    main()

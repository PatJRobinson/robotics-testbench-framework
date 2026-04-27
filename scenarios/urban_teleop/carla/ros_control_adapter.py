#!/usr/bin/env python3

import math
import signal
import threading
import time

import carla
import rclpy
from geometry_msgs.msg import Twist

from rclpy.executors import ExternalShutdownException

ROLE_NAME = "sim_platform_ego"


class CarlaCmdVelAdapter:
    def __init__(self):
        rclpy.init()

        self.node = rclpy.create_node("carla_cmd_vel_adapter")
        self.node.create_subscription(Twist, "/cmd_vel", self.on_cmd_vel, 10)

        self.client = carla.Client("localhost", 2000)
        self.client.set_timeout(10.0)
        self.world = self.client.get_world()

        self.vehicle = self.wait_for_vehicle(ROLE_NAME)

        self.last_cmd_time = time.time()
        self.timeout_seconds = 0.5
        self.stop_requested = False

        self.node.get_logger().info(
            f"CARLA cmd_vel adapter ready for role_name={ROLE_NAME}"
        )

    def wait_for_vehicle(self, role_name: str, timeout: float = 30.0):
        start = time.time()

        while time.time() - start < timeout:
            for actor in self.world.get_actors().filter("vehicle.*"):
                if actor.attributes.get("role_name") == role_name:
                    self.node.get_logger().info(f"Found ego vehicle id={actor.id}")
                    return actor

            self.node.get_logger().info(f"Waiting for vehicle role_name={role_name}")
            time.sleep(0.5)

        raise RuntimeError(f"Timed out waiting for vehicle role_name={role_name}")

    def on_cmd_vel(self, msg: Twist):
        self.last_cmd_time = time.time()

        throttle = max(0.0, min(float(msg.linear.x), 1.0))
        brake = max(0.0, min(float(-msg.linear.x), 1.0))
        steer = max(-1.0, min(float(msg.angular.z), 1.0))

        control = carla.VehicleControl(
            throttle=throttle,
            steer=steer,
            brake=brake,
            hand_brake=False,
            reverse=False,
        )

        self.vehicle.apply_control(control)

        self.node.get_logger().info(
            f"cmd_vel -> throttle={throttle:.2f} brake={brake:.2f} steer={steer:.2f}"
        )

    def watchdog_loop(self):
        while not self.stop_requested:
            if time.time() - self.last_cmd_time > self.timeout_seconds:
                self.vehicle.apply_control(
                    carla.VehicleControl(throttle=0.0, brake=1.0, steer=0.0)
                )

            time.sleep(0.1)

    def run(self):
        watchdog = threading.Thread(target=self.watchdog_loop, daemon=True)
        watchdog.start()

        try:
            rclpy.spin(self.node)
        except ExternalShutdownException:
            pass
        finally:
            self.stop_requested = True
            self.vehicle.apply_control(
                carla.VehicleControl(throttle=0.0, brake=1.0, steer=0.0)
            )
            self.node.destroy_node()
            rclpy.shutdown()


def main():
    adapter = CarlaCmdVelAdapter()
    adapter.run()


if __name__ == "__main__":
    main()

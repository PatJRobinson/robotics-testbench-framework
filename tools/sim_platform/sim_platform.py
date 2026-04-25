#! /usr/bin/env nix-shell
#! nix-shell -i python3 -p python3 python3Packages.pyyaml

import argparse
import subprocess
from pathlib import Path
import time
import yaml
import os
import sys

root_env = os.environ.get("SIM_PLATFORM_ROOT")

if root_env is None:
    raise RuntimeError(
        "SIM_PLATFORM_ROOT is not set. Run inside nix develop or set it to the project root."
    )

ROOT = Path(root_env).resolve()
RUNS_DIR = Path(os.environ.get("SIM_PLATFORM_RUNS_DIR", ROOT / "runs")).resolve()

def load_yaml(path: Path) -> dict:
    with path.open("r") as f:
        return yaml.safe_load(f)


def find_experiment(name: str) -> Path:
    path = ROOT / "experiments" / name / "experiment.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Experiment not found: {path}")
    return path


def find_app(name: str) -> Path:
    path = ROOT / "apps" / name / "app.yaml"
    if not path.exists():
        raise FileNotFoundError(f"App not found: {path}")
    return path


def find_realisation(name: str) -> Path:
    # e.g. warehouse_teleop@isaac
    scenario, backend = name.split("@", 1)
    path = ROOT / "scenarios" / scenario / backend / "realisation.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Realisation not found: {path}")
    return path


def resolve_experiment(name: str) -> dict:
    exp_path = find_experiment(name)
    exp = load_yaml(exp_path)

    spec = exp["spec"]
    app_ref = spec["appRef"]
    realisation_ref = spec["realisationRef"]

    app_path = find_app(app_ref)
    realisation_path = find_realisation(realisation_ref)

    app = load_yaml(app_path)
    realisation = load_yaml(realisation_path)

    return {
        "experiment_name": name,
        "experiment_path": str(exp_path.relative_to(ROOT)),
        "app_ref": app_ref,
        "app_path": str(app_path.relative_to(ROOT)),
        "app_runtime": app["spec"]["runtime"],
        "realisation_ref": realisation_ref,
        "realisation_path": str(realisation_path.relative_to(ROOT)),
        "backend_ref": realisation["spec"]["backendRef"],
        "backend_launch": realisation["spec"]["runtime"]["launch"]["command"],
        "cmd_args": realisation["spec"]["runtime"]["launch"].get("args", []),
        "readiness": realisation["spec"]["runtime"].get("readiness", {}),
        "scenario_readiness": realisation["spec"]["runtime"].get("scenarioReadiness", {}),
        "container_name": realisation["spec"]["runtime"]["containerName"],
        "processes": realisation["spec"]["runtime"].get("processes", []),
    }


def print_plan(plan: dict) -> None:
    print("Resolved experiment:")
    for key, value in plan.items():
        print(f"  {key}: {value}")


def wait_for_topic(topic: str, timeout: float = 120.0) -> None:
    print(f"\n[sim-platform] Waiting for topic: {topic}")

    start = time.time()

    while True:
        try:
            result = subprocess.run(
                ["ros2", "topic", "list"],
                capture_output=True,
                text=True,
                check=True,
            )

            topics = result.stdout.splitlines()

            if topic in topics:
                print(f"[sim-platform] Found topic: {topic}")
                return

        except Exception as e:
            print(f"[sim-platform] readiness check failed: {e}")

        if time.time() - start > timeout:
            raise RuntimeError(f"Timeout waiting for topic: {topic}")

        time.sleep(1.0)

def wait_for_carla_rpc(host: str, port: int, timeout: float = 120.0) -> None:
    import time
    import carla

    print(f"[sim-platform] Waiting for CARLA RPC at {host}:{port}")

    start = time.time()

    while True:
        try:
            client = carla.Client(host, port)
            client.set_timeout(5.0)
            world = client.get_world()
            print(f"[sim-platform] CARLA ready: {world.get_map().name}")
            return
        except Exception as e:
            if time.time() - start > timeout:
                raise RuntimeError(
                    f"Timed out waiting for CARLA RPC at {host}:{port}: {e}"
                )

            time.sleep(1.0)

def wait_for_carla_actor(role_name: str, timeout: float = 60.0):
    import carla

    print(f"[sim-platform] Waiting for CARLA actor: {role_name}")

    client = carla.Client("localhost", 2000)
    client.set_timeout(5.0)

    start = time.time()

    while True:
        try:
            world = client.get_world()

            for actor in world.get_actors():
                if actor.attributes.get("role_name") == role_name:
                    print(f"[sim-platform] Actor ready: {role_name}")
                    return

        except Exception as e:
            print(f"[sim-platform] actor check failed: {e}")

        if time.time() - start > timeout:
            raise RuntimeError(f"Timeout waiting for actor: {role_name}")

        time.sleep(0.5)

def wait_for_readiness(readiness: dict) -> None:
    if not readiness:
        return

    readiness_type = readiness["type"]
    timeout = readiness.get("timeoutSeconds", 120)

    if readiness_type == "ros_topic":
        topic = readiness.get("topic")
        if topic:
            wait_for_topic(topic)

    elif readiness_type == "carla_rpc":
        wait_for_carla_rpc(
            readiness.get("host", "localhost"),
            int(readiness.get("port", 2000)),
            timeout=timeout,
        )

    else:
        raise ValueError(f"Unknown readiness type: {readiness_type}")

def wait_for_scenario_readiness(scenario_readiness: dict):
    if scenario_readiness and scenario_readiness["type"] == "carla_actor":
        wait_for_carla_actor(
            scenario_readiness["roleName"],
            timeout=scenario_readiness.get("timeoutSeconds", 60),
        )

def start_process(name: str, command: list[str], log_dir: Path) -> subprocess.Popen:
    log_path = log_dir / f"{name}.log"
    log_file = log_path.open("w")

    print(f"[sim-platform] Starting {name}: {' '.join(command)}")
    print(f"[sim-platform] {name} logs: {log_path}")

    return subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )

def assert_processes_alive(processes: list[subprocess.Popen], names: list[str]) -> None:
    for name, proc in zip(names, processes):
        code = proc.poll()
        if code is not None:
            raise RuntimeError(f"Process exited early: {name} exit_code={code}")

def get_app_command(app_rt: dict) -> list[str]:
    runtime_type = app_rt["type"]
    app_cmd = ROOT / app_rt["entrypoint"]

    if runtime_type == "python":
        return [sys.executable, str(app_cmd)]

    if runtime_type in ("shell", "bash", "nix_host", "ros2_node"):
        return ["bash", str(app_cmd)]

    raise ValueError(f"Unknown app runtime type: {runtime_type}")

def run_experiment(name: str) -> None:
    succeeded = False

    plan = resolve_experiment(name)
    print_plan(plan)

    run_dir = RUNS_DIR / plan["experiment_name"]
    run_dir.mkdir(parents=True, exist_ok=True)

    app_cmd = get_app_command(plan["app_runtime"])

    processes = []
    process_names = []

    backend_cmd = ROOT / plan["backend_launch"]

    backend_proc = start_process(
        "backend",
        ["bash", str(backend_cmd), *plan["cmd_args"]],
        run_dir,
    )
    processes.append(backend_proc)
    process_names.append("backend")

    try:
        wait_for_readiness(plan["readiness"])
        assert_processes_alive(processes, process_names)

        for proc_spec in plan["processes"]:
            entrypoint = ROOT / proc_spec["entrypoint"]
            args = proc_spec.get("args", [])

            ptype = proc_spec.get("type", "<missing>")
            if ptype == "python":
                proc = start_process(
                    proc_spec["name"],
                    ["python", str(entrypoint), *args],
                    run_dir,
                )
                processes.append(proc)
                process_names.append(proc_spec["name"])
            else:
                raise ValueError(f"Unknown process type: {ptype}")

        assert_processes_alive(processes, process_names)

        wait_for_scenario_readiness(plan.get("scenario_readiness"))

        assert_processes_alive(processes, process_names)

        print("\nStarting app:")
        print(f"  {' '.join(app_cmd)}")

        app_proc = start_process("app", app_cmd, run_dir)
        processes.append(app_proc)
        process_names.append("app")

        app_exit = app_proc.wait()

        if app_exit != 0:
            raise RuntimeError(f"App exited with non-zero code: {app_exit}")

        succeeded = True
        print("[sim-platform] experiment succeeded")

    finally:
        print("\nStopping processes...")
        for proc in reversed(processes):
            if proc.poll() is None:
                proc.terminate()

        subprocess.run(
            ["docker", "rm", "-f", plan["container_name"]],
            cwd=ROOT,
            check=False,
        )

        if not succeeded:
            print("[sim-platform] experiment failed")

def main() -> None:
    parser = argparse.ArgumentParser(prog="sim-platform")
    sub = parser.add_subparsers(dest="command", required=True)

    resolve = sub.add_parser("resolve")
    resolve.add_argument("kind", choices=["experiment"])
    resolve.add_argument("name")

    run = sub.add_parser("run")
    run.add_argument("kind", choices=["experiment"])
    run.add_argument("name")

    args = parser.parse_args()

    if args.command == "resolve":
        plan = resolve_experiment(args.name)
        print_plan(plan)

    elif args.command == "run":
        run_experiment(args.name)


if __name__ == "__main__":
    main()

#! /usr/bin/env nix-shell
#! nix-shell -i python3 -p python3 python3Packages.pyyaml

import argparse
import subprocess
from pathlib import Path
import time
import yaml
import os

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
        "app_entrypoint": app["spec"]["runtime"]["entrypoint"],
        "realisation_ref": realisation_ref,
        "realisation_path": str(realisation_path.relative_to(ROOT)),
        "backend_ref": realisation["spec"]["backendRef"],
        "backend_launch": realisation["spec"]["runtime"]["launch"]["command"],
        "cmd_args": realisation["spec"]["runtime"]["launch"].get("args", []),
        "readiness": realisation["spec"]["runtime"].get("readiness", {}),
        "container_name": realisation["spec"]["runtime"]["containerName"],
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

def run_experiment(name: str) -> None:
    plan = resolve_experiment(name)
    print_plan(plan)

    backend_cmd = ROOT / plan["backend_launch"]
    app_cmd = ROOT / plan["app_entrypoint"]

    print("\nStarting backend:")
    print(f"  {backend_cmd}")

    log_path = ROOT / "runs" / plan["experiment_name"] / "backend.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    log_file = log_path.open("w")

    cmd_args = plan["cmd_args"]
    print(f"Running process with command {backend_cmd} {cmd_args}")

    backend_proc = subprocess.Popen(
        ["bash", str(backend_cmd), *plan["cmd_args"]],
        cwd=ROOT,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )

    try:
        wait_for_readiness(plan["readiness"])

        print(f"[sim-platform] Backend logs: {log_path}")

        print("\nStarting app:")
        print(f"  {app_cmd}")
        subprocess.run([str(app_cmd)], cwd=ROOT, check=True)

    finally:
        print("\nStopping backend...")
        backend_proc.terminate()

        subprocess.run(
          ["docker", "rm", "-f", plan["container_name"]],
          cwd=ROOT,
          check=False,
        )

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

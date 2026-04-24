#! /usr/bin/env nix-shell
#! nix-shell -i python3 -p python3 python3Packages.pyyaml

import argparse
import subprocess
from pathlib import Path
import time
import yaml


ROOT = Path(__file__).resolve().parents[2]


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
        "world_path": realisation["spec"]["native"]["world"]["containerPath"],
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

        except Exception:
            pass

        if time.time() - start > timeout:
            raise RuntimeError(f"Timeout waiting for topic: {topic}")

        time.sleep(1.0)

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

    backend_proc = subprocess.Popen(
        ["bash", str(backend_cmd), plan["world_path"]],
        cwd=ROOT,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )

    try:
        topic = plan["readiness"].get("topic")

        if topic:
            wait_for_topic("/cmd_vel")

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

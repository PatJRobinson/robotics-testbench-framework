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
SCHEMAS = {
    "App": ROOT / "schemas" / "app.schema.json",
    "Realisation": ROOT / "schemas" / "realisation.schema.json",
    "Contract": ROOT / "schemas" / "contract.schema.json",
}

def load_yaml(path: Path) -> dict:
    with path.open("r") as f:
        return yaml.safe_load(f)

def validate_yaml_file(path: Path) -> None:
    import json
    import jsonschema

    doc = load_yaml(path)
    kind = doc.get("kind")

    if kind not in SCHEMAS:
        print(f"[sim-platform] No schema for kind={kind}: {path}")
        return

    schema = json.loads(SCHEMAS[kind].read_text())
    jsonschema.validate(instance=doc, schema=schema)

    print(f"[sim-platform] Schema valid: {path}")

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

def contract_names(entries: list[dict]) -> set[str]:
    return {
        entry["contract"]
        for entry in entries or []
        if isinstance(entry, dict) and "contract" in entry
    }


def provided_contracts(realisation: dict) -> dict[str, set[str]]:
    provides = realisation["spec"].get("provides", {})

    provided = {
        "platforms": contract_names(provides.get("platforms", [])),
        "commands": contract_names(provides.get("commands", [])),
        "observations": contract_names(provides.get("observations", [])),
    }

    for adapter in provides.get("adapters", []):
        adapter_provides = adapter.get("provides", {})
        provided["commands"] |= contract_names(adapter_provides.get("commands", []))
        provided["observations"] |= contract_names(adapter_provides.get("observations", []))
        provided["platforms"] |= contract_names(adapter_provides.get("platforms", []))

    return provided


def required_contracts(app: dict) -> dict[str, set[str]]:
    requires = app["spec"].get("requires", {})

    return {
        "platforms": contract_names(requires.get("platforms", [])),
        "commands": contract_names(requires.get("commands", [])),
        "observations": contract_names(requires.get("observations", [])),
    }

def validate_contracts(app: dict, realisation: dict) -> None:
    required = required_contracts(app)
    provided = provided_contracts(realisation)

    missing = {
        kind: sorted(required[kind] - provided[kind])
        for kind in required
        if required[kind] - provided[kind]
    }

    if missing:
        lines = ["Contract validation failed:"]
        for kind, names in missing.items():
            lines.append(f"  missing {kind}: {', '.join(names)}")
        lines.append("")
        lines.append(f"  required: {required}")
        lines.append(f"  provided: {provided}")
        raise RuntimeError("\n".join(lines))

    print("[sim-platform] Contract validation passed")

def find_contract_entries(entries: list[dict], contract: str) -> list[dict]:
    return [
        entry for entry in entries or []
        if isinstance(entry, dict) and entry.get("contract") == contract
    ]


def realisation_contract_entries(realisation: dict, kind: str) -> list[dict]:
    provides = realisation["spec"].get("provides", {})
    entries = list(provides.get(kind, []) or [])

    for adapter in provides.get("adapters", []) or []:
        adapter_provides = adapter.get("provides", {})
        entries.extend(adapter_provides.get(kind, []) or [])

    return entries


def validate_binding_config(app: dict, realisation: dict) -> list[dict]:
    resolved = []

    requires = app["spec"].get("requires", {})

    for kind in ("commands", "observations", "platforms"):
        for required in requires.get(kind, []) or []:
            contract = required.get("contract")
            if not contract:
                continue

            binding_config = required.get("bindingConfig", {})
            candidates = find_contract_entries(
                realisation_contract_entries(realisation, kind),
                contract,
            )

            if not candidates:
                continue  # contract validation already handles this

            provided = candidates[0]
            binding = provided.get("binding", {})
            configurable = set(binding.get("configurable", []) or [])

            unsupported = set(binding_config.keys()) - configurable
            if unsupported:
                raise RuntimeError(
                    f"Binding config validation failed for {kind}:{contract}. "
                    f"Unsupported config fields: {sorted(unsupported)}. "
                    f"Configurable fields: {sorted(configurable)}"
                )

            resolved.append({
                "kind": kind,
                "contract": contract,
                "binding": binding,
                "bindingConfig": binding_config,
                "resolved": resolve_binding(binding, binding_config),
            })

    print("[sim-platform] Binding config validation passed")
    return resolved

def write_run_metadata(plan: dict, run_dir: Path) -> None:
    metadata = {
        "experiment": plan["experiment_name"],
        "app": plan["app_ref"],
        "realisation": plan["realisation_ref"],
        "backend": plan["backend_ref"],
        "contracts": plan.get("contracts", {}),
    }

    metadata_path = run_dir / "metadata.yaml"
    with metadata_path.open("w") as f:
        yaml.safe_dump(metadata, f, sort_keys=False)

    print(f"[sim-platform] Run metadata: {metadata_path}")

def satisfaction_trace(app: dict, realisation: dict) -> list[dict]:
    requires = app["spec"].get("requires", {})
    provides = realisation["spec"].get("provides", {})

    trace = []

    for kind in ("platforms", "commands", "observations"):
        direct_entries = provides.get(kind, []) or []

        adapter_entries = []
        for adapter in provides.get("adapters", []) or []:
            adapter_provides = adapter.get("provides", {})
            for entry in adapter_provides.get(kind, []) or []:
                adapter_entries.append((adapter, entry))

        for required in requires.get(kind, []) or []:
            contract = required.get("contract")
            if not contract:
                continue

            direct_match = next(
                (entry for entry in direct_entries if entry.get("contract") == contract),
                None,
            )

            if direct_match:
                trace.append({
                    "kind": kind,
                    "contract": contract,
                    "satisfiedBy": "direct",
                    "provider": "realisation",
                })
                continue

            adapter_match = next(
                (
                    (adapter, entry)
                    for adapter, entry in adapter_entries
                    if entry.get("contract") == contract
                ),
                None,
            )

            if adapter_match:
                adapter, _entry = adapter_match
                trace.append({
                    "kind": kind,
                    "contract": contract,
                    "satisfiedBy": "adapter",
                    "adapter": adapter.get("name"),
                    "adapterKind": adapter.get("kind"),
                })

    return trace

def resolve_binding(binding: dict, binding_config: dict) -> dict:
    resolved = {}

    if "defaultName" in binding:
        resolved["name"] = binding["defaultName"]

    if "defaultTopics" in binding:
        resolved["topics"] = binding["defaultTopics"]

    resolved.update(binding_config or {})

    return resolved

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

    validate_contracts(app, realisation)
    resolved_bindings = validate_binding_config(app, realisation)

    required = required_contracts(app)
    provided = provided_contracts(realisation)

    trace = satisfaction_trace(app, realisation)

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
        "contracts": {
            "required": {k: sorted(v) for k, v in required.items()},
            "provided": {k: sorted(v) for k, v in provided.items()},
            "satisfactionTrace": trace,
            "resolvedBindings": resolved_bindings,
        },
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

    write_run_metadata(plan, run_dir)

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
            elif ptype == "ros_python":
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

        interactive = plan["app_runtime"].get("interactive", False)

        if interactive:
            app_exit = subprocess.run(app_cmd, cwd=ROOT).returncode
        else:
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

def print_explanation(plan: dict) -> None:
    contracts = plan["contracts"]
    trace = contracts.get("satisfactionTrace", [])
    bindings = contracts.get("resolvedBindings", [])

    print(f"Experiment: {plan['experiment_name']}")
    print(f"App: {plan['app_ref']}")
    print(f"Realisation: {plan['realisation_ref']}")
    print(f"Backend: {plan['backend_ref']}")
    print()

    for kind in ("platforms", "commands", "observations"):
        entries = [t for t in trace if t["kind"] == kind]
        if not entries:
            continue

        print(f"Required {kind}:")
        for entry in entries:
            contract = entry["contract"]
            print(f"- {contract}")

            if entry["satisfiedBy"] == "direct":
                print("  satisfied: direct")
            elif entry["satisfiedBy"] == "adapter":
                print(f"  satisfied: adapter {entry.get('adapter')}")
                print(f"  adapter kind: {entry.get('adapterKind')}")

            binding = next(
                (
                    b for b in bindings
                    if b["kind"] == kind and b["contract"] == contract
                ),
                None,
            )

            if binding:
                resolved = binding.get("resolved", {})
                if "name" in resolved:
                    print(f"  resolved binding: {resolved['name']}")
                elif "topics" in resolved:
                    print("  resolved topics:")
                    for topic_name, topic in resolved["topics"].items():
                        print(f"    {topic_name}: {topic}")

        print()

def explain_experiment(name: str):
    plan = resolve_experiment(name)
    print_explanation(plan)

def main() -> None:
    parser = argparse.ArgumentParser(prog="sim-platform")
    sub = parser.add_subparsers(dest="command", required=True)

    resolve = sub.add_parser("resolve")
    resolve.add_argument("kind", choices=["experiment"])
    resolve.add_argument("name")

    run = sub.add_parser("run")
    run.add_argument("kind", choices=["experiment"])
    run.add_argument("name")

    validate = sub.add_parser("validate")
    validate.add_argument("paths", nargs="*")

    explain_parser = sub.add_parser("explain")
    explain_parser.add_argument("kind", choices=["experiment"])
    explain_parser.add_argument("name")

    args = parser.parse_args()

    if args.command == "resolve":
        plan = resolve_experiment(args.name)
        print_plan(plan)

    elif args.command == "run":
        run_experiment(args.name)

    elif args.command == "validate":
        paths = [Path(p) for p in args.paths]

        if not paths:
            paths = list((ROOT / "apps").glob("*/app.yaml")) \
            + list((ROOT / "scenarios").rglob("realisation.yaml")) \
            + list((ROOT / "contracts").rglob("*.yaml"))

        for path in paths:
            validate_yaml_file(path)

    elif args.command == "explain":
        explain_experiment(args.name)

if __name__ == "__main__":
    main()

from tools.sim_platform.sim_platform import (
    print_explanation,
    resolve_experiment,
)

def test_direct_satisfaction_trace_for_isaac():
    plan = resolve_experiment("teleop_smoke")

    trace = plan["contracts"]["satisfactionTrace"]

    entry = next(
        e for e in trace
        if e["kind"] == "commands"
        and e["contract"] == "differential_drive_cmd_vel"
    )

    assert entry["satisfiedBy"] == "direct"


def test_adapter_satisfaction_trace_for_carla():
    plan = resolve_experiment("carla_teleop")

    trace = plan["contracts"]["satisfactionTrace"]

    entry = next(
        e for e in trace
        if e["kind"] == "commands"
        and e["contract"] == "differential_drive_cmd_vel"
    )

    assert entry["satisfiedBy"] == "adapter"
    assert entry["adapter"] == "cmd_vel_to_vehicle_control"
    assert entry["adapterKind"] == "semantic"


def test_binding_resolution_records_final_name():
    plan = resolve_experiment("carla_teleop")

    bindings = plan["contracts"]["resolvedBindings"]

    entry = next(
        b for b in bindings
        if b["kind"] == "commands"
        and b["contract"] == "differential_drive_cmd_vel"
    )

    assert entry["binding"]["defaultName"] == "/cmd_vel"
    assert entry["bindingConfig"] == {"name": "/cmd_vel"}
    assert entry["resolved"] == {"name": "/cmd_vel"}


def test_explain_output_includes_adapter_and_binding(capsys):
    plan = resolve_experiment("carla_teleop")

    print_explanation(plan)

    out = capsys.readouterr().out

    assert "Experiment: carla_teleop" in out
    assert "App: carla_teleop" in out
    assert "Realisation: urban_teleop@carla" in out
    assert "Backend: carla" in out
    assert "differential_drive_cmd_vel" in out
    assert "satisfied: adapter cmd_vel_to_vehicle_control" in out
    assert "adapter kind: semantic" in out
    assert "resolved binding: /cmd_vel" in out


def test_explain_output_shows_direct_satisfaction(capsys):
    plan = resolve_experiment("teleop_smoke")

    print_explanation(plan)

    out = capsys.readouterr().out

    assert "Experiment: teleop_smoke" in out
    assert "App: amr_teleop" in out
    assert "Realisation: warehouse_teleop@isaac" in out
    assert "differential_drive_cmd_vel" in out
    assert "satisfied: direct" in out

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import ValidationError, validate


ROOT = Path(__file__).resolve().parents[1]


def load_schema(name: str) -> dict:
    return json.loads((ROOT / "schemas" / name).read_text())


def assert_valid(instance: dict, schema_name: str) -> None:
    validate(instance=instance, schema=load_schema(schema_name))


def assert_invalid(instance: dict, schema_name: str) -> None:
    with pytest.raises(ValidationError):
        validate(instance=instance, schema=load_schema(schema_name))

def test_valid_app_schema_passes():
    app = yaml.safe_load((ROOT / "apps" / "carla_teleop" / "app.yaml").read_text())
    assert_valid(app, "app.schema.json")


def test_app_bare_platform_contract_fails():
    app = yaml.safe_load((ROOT / "apps" / "carla_teleop" / "app.yaml").read_text())
    app["spec"]["requires"]["platforms"] = ["ackermann_vehicle"]

    assert_invalid(app, "app.schema.json")


def test_app_invalid_interactive_type_fails():
    app = yaml.safe_load((ROOT / "apps" / "carla_teleop" / "app.yaml").read_text())
    app["spec"]["runtime"]["interactive"] = "true"

    assert_invalid(app, "app.schema.json")

def test_valid_realisation_schema_passes():
    realisation = yaml.safe_load(
        (ROOT / "scenarios" / "urban_teleop" / "carla" / "realisation.yaml").read_text()
    )

    assert_valid(realisation, "realisation.schema.json")


def test_realisation_bare_platform_contract_fails():
    realisation = yaml.safe_load(
        (ROOT / "scenarios" / "urban_teleop" / "carla" / "realisation.yaml").read_text()
    )

    realisation["spec"]["provides"]["platforms"] = ["ackermann_vehicle"]

    assert_invalid(realisation, "realisation.schema.json")


def test_realisation_invalid_adapter_kind_fails():
    realisation = yaml.safe_load(
        (ROOT / "scenarios" / "urban_teleop" / "carla" / "realisation.yaml").read_text()
    )

    realisation["spec"]["provides"]["adapters"][0]["kind"] = "magic"

    assert_invalid(realisation, "realisation.schema.json")


def test_realisation_invalid_process_type_fails():
    realisation = yaml.safe_load(
        (ROOT / "scenarios" / "urban_teleop" / "carla" / "realisation.yaml").read_text()
    )

    realisation["spec"]["runtime"]["processes"][0]["type"] = "weird_python"

    assert_invalid(realisation, "realisation.schema.json")

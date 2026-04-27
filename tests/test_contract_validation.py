import pytest

from tools.sim_platform.sim_platform import validate_contracts


def test_direct_command_contract_passes():
    app = {
        "spec": {
            "requires": {
                "commands": [{"contract": "differential_drive_cmd_vel"}],
            }
        }
    }

    realisation = {
        "spec": {
            "provides": {
                "commands": [{"contract": "differential_drive_cmd_vel"}],
            }
        }
    }

    validate_contracts(app, realisation)


def test_adapter_command_contract_passes():
    app = {
        "spec": {
            "requires": {
                "commands": [{"contract": "differential_drive_cmd_vel"}],
            }
        }
    }

    realisation = {
        "spec": {
            "provides": {
                "commands": [{"contract": "ackermann_vehicle_control"}],
                "adapters": [
                    {
                        "provides": {
                            "commands": [
                                {"contract": "differential_drive_cmd_vel"}
                            ]
                        }
                    }
                ],
            }
        }
    }

    validate_contracts(app, realisation)


def test_missing_command_contract_fails():
    app = {
        "spec": {
            "requires": {
                "commands": [{"contract": "differential_drive_cmd_vel"}],
            }
        }
    }

    realisation = {
        "spec": {
            "provides": {
                "commands": [{"contract": "ackermann_vehicle_control"}],
            }
        }
    }

    with pytest.raises(RuntimeError, match="missing commands"):
        validate_contracts(app, realisation)


def test_missing_platform_contract_fails():
    app = {
        "spec": {
            "requires": {
                "platforms": [{"contract": "ackermann_vehicle"}],
            }
        }
    }

    realisation = {
        "spec": {
            "provides": {
                "platforms": [{"contract": "differential_drive_robot"}],
            }
        }
    }

    with pytest.raises(RuntimeError, match="missing platforms"):
        validate_contracts(app, realisation)

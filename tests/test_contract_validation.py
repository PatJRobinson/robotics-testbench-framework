import pytest

from tools.sim_platform.sim_platform import (
    validate_contracts,
    validate_binding_config,
    write_run_metadata,
)


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

def test_binding_config_passes_for_configurable_field():
    app = {
        "spec": {
            "requires": {
                "commands": [
                    {
                        "contract": "differential_drive_cmd_vel",
                        "bindingConfig": {"name": "/cmd_vel"},
                    }
                ]
            }
        }
    }

    realisation = {
        "spec": {
            "provides": {
                "commands": [
                    {
                        "contract": "differential_drive_cmd_vel",
                        "binding": {
                            "type": "ros_topic",
                            "defaultName": "/cmd_vel",
                            "configurable": ["name"],
                        },
                    }
                ]
            }
        }
    }

    resolved = validate_binding_config(app, realisation)

    assert resolved == [
        {
            "kind": "commands",
            "contract": "differential_drive_cmd_vel",
            "binding": {
                "type": "ros_topic",
                "defaultName": "/cmd_vel",
                "configurable": ["name"],
            },
            "bindingConfig": {"name": "/cmd_vel"},
        }
    ]

def test_binding_config_fails_for_non_configurable_field():
    app = {
        "spec": {
            "requires": {
                "commands": [
                    {
                        "contract": "differential_drive_cmd_vel",
                        "bindingConfig": {
                            "name": "/cmd_vel",
                            "messageType": "geometry_msgs/msg/Twist",
                        },
                    }
                ]
            }
        }
    }

    realisation = {
        "spec": {
            "provides": {
                "commands": [
                    {
                        "contract": "differential_drive_cmd_vel",
                        "binding": {
                            "type": "ros_topic",
                            "defaultName": "/cmd_vel",
                            "configurable": ["name"],
                        },
                    }
                ]
            }
        }
    }

    with pytest.raises(RuntimeError, match="Unsupported config fields"):
        validate_binding_config(app, realisation)

def test_binding_config_passes_for_adapter_provided_contract():
    app = {
        "spec": {
            "requires": {
                "commands": [
                    {
                        "contract": "differential_drive_cmd_vel",
                        "bindingConfig": {"name": "/cmd_vel"},
                    }
                ]
            }
        }
    }

    realisation = {
        "spec": {
            "provides": {
                "commands": [
                    {
                        "contract": "ackermann_vehicle_control",
                        "binding": {
                            "type": "carla_python_api",
                            "target": "carla.VehicleControl",
                            "configurable": [],
                        },
                    }
                ],
                "adapters": [
                    {
                        "name": "cmd_vel_to_vehicle_control",
                        "provides": {
                            "commands": [
                                {
                                    "contract": "differential_drive_cmd_vel",
                                    "binding": {
                                        "type": "ros_topic",
                                        "defaultName": "/cmd_vel",
                                        "configurable": ["name"],
                                    },
                                }
                            ]
                        },
                    }
                ],
            }
        }
    }

    resolved = validate_binding_config(app, realisation)

    assert resolved[0]["contract"] == "differential_drive_cmd_vel"
    assert resolved[0]["bindingConfig"] == {"name": "/cmd_vel"}

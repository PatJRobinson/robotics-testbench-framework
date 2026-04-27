{
  description = "Robotics testbench framework: ROS 2 Jazzy + Nix + Docker simulation backends";

  inputs = {
    nix-ros-overlay.url = "github:lopsided98/nix-ros-overlay/master";
    nixpkgs.follows = "nix-ros-overlay/nixpkgs";
    flake-utils.url = "github:numtide/flake-utils";
  };

  nixConfig = {
    extra-substituters = ["https://ros.cachix.org"];
    extra-trusted-public-keys = [
      "ros.cachix.org-1:dSyZxI8geDCJrwgvCOHDoAfOm5sV1wCPjBkKL+38Rvo="
    ];
  };

  outputs = {
    self,
    nixpkgs,
    nix-ros-overlay,
    flake-utils,
  }:
    flake-utils.lib.eachDefaultSystem (system: let
      pkgs = import nixpkgs {
        inherit system;
        config = {
          allowUnfree = true;
          permittedInsecurePackages = [
            "freeimage-3.18.0-unstable-2024-04-18"
          ];
        };
        overlays = [nix-ros-overlay.overlays.default];
      };

      ros = pkgs.rosPackages.jazzy;

      rosEnv = ros.buildEnv {
        paths = [
          ros.ros-core
          ros.ros-base
          ros.desktop

          # App dependency for apps/amr_teleop/run.sh
          ros.teleop-twist-keyboard
        ];
      };

      carla = import ./infra/nix/carla-python.nix {inherit pkgs;};

      python = pkgs.python312.withPackages (ps: [
        ps.pyyaml
        ps.pytest
        carla.carlaPythonPkg
      ]);

      simPlatform = pkgs.writeShellApplication {
        name = "sim-platform";
        runtimeInputs = [
          python
          pkgs.docker
          rosEnv
        ];
        text = ''
          export LD_LIBRARY_PATH="${carla.carlaLibPath}:''${LD_LIBRARY_PATH:-}"
          exec ${python}/bin/python ${self}/tools/sim_platform/sim_platform.py "$@"
        '';
      };
    in {
      devShells.default = pkgs.mkShell {
        name = "robotics-testbench-framework";

        packages = [
          rosEnv

          simPlatform

          python

          pkgs.docker
          pkgs.git
        ];

        shellHook = ''
          export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
          export FASTRTPS_DEFAULT_PROFILES_FILE="$PWD/infra/dds-cfg/fastdds.xml"
          export SIM_PLATFORM_ROOT="$PWD"
          export SIM_PLATFORM_RUNS_DIR="$PWD/runs"
          export PYTHONPATH="$PWD" PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests

          generate_env_file() {
            env | grep -E '^(PATH|LD_LIBRARY_PATH|PYTHONPATH|AMENT|COLCON|ROS_|RMW|GZ_|FASTRTPS_)=' \
              | sed 's/^/export /' \
              > .env.sh
          }

          generate_env_file

          echo ""
          echo "Robotics Testbench Framework"
          echo "----------------------------------------------"
          echo "ROS_DISTRO=$ROS_DISTRO"
          echo "RMW_IMPLEMENTATION=$RMW_IMPLEMENTATION"
          echo "FASTRTPS_DEFAULT_PROFILES_FILE=$FASTRTPS_DEFAULT_PROFILES_FILE"
          echo ""
          echo "Try:"
          echo "  sim-platform resolve experiment teleop_smoke"
          echo "  sim-platform run experiment teleop_smoke"
          echo ""
        '';
      };

      checks.contract-validation =
        pkgs.runCommand "contract-validation-tests" {
          nativeBuildInputs = [
            python
          ];
        } ''
          export PYTHONPATH="${self}"
          export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
          export SIM_PLATFORM_ROOT="$PWD"
          export SIM_PLATFORM_RUNS_DIR="$PWD/runs"

          cd ${self}
          pytest tests

          touch $out
        '';
    });
}

{
  description = "ROS 2 jazzy devShell + Minimal Headless Gazebo Sim Garden (Docker) + Foxglove-ready";

  inputs = {
    #nixpkgs.url = "nixpkgs/nixos-unstable";
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
    in {
      devShells.default = pkgs.mkShell {
        name = "ros2-jazzy-sim";

        packages = [
          # ROS 2 base stack
          (ros.buildEnv {
            paths = [
              ros.ros-core
              ros.ros-base
              ros.desktop
            ];
          })

          pkgs.docker
          pkgs.git
        ];

        shellHook = ''

          # generate a script to source inside docker to
          # share host environment
          generate_env_file() {
            env | grep -E '^(PATH|LD_LIBRARY_PATH|PYTHONPATH|AMENT|COLCON|ROS_|RMW|GZ_)=' \
              | sed 's/^/export /' \
              > .env.sh
          }
          generate_env_file

          export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
          export FASTRTPS_DEFAULT_PROFILES_FILE=infra/dds-cfg/fastdds.xml

          echo ""
          echo "ROS 2 jazzy DevShell"
          echo "----------------------------------------------"
          echo ""

        '';
      };
    });
}

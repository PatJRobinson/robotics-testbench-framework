{pkgs}: let
  pyPkgs = pkgs.python312Packages;

  carlaLibPath = pkgs.lib.makeLibraryPath [
    pkgs.zlib
    pkgs.stdenv.cc.cc.lib
  ];

  carlaPythonPkg = pyPkgs.buildPythonPackage rec {
    pname = "carla";
    version = "0.9.16";
    format = "wheel";

    src = pkgs.fetchPypi {
      inherit pname version format;
      dist = "cp312";
      python = "cp312";
      abi = "cp312";
      platform = "manylinux_2_31_x86_64";
      hash = "sha256-wyOnsfitOsgc+sefXZbJysivptCnaPov/6RrszaUXE8=";
    };

    nativeBuildInputs = [
      pkgs.autoPatchelfHook
      pkgs.patchelf
    ];

    buildInputs = [
      pkgs.zlib
      pkgs.stdenv.cc.cc.lib
    ];

    postInstall = ''
      libDir=$(dirname $(find $out -name 'libwebp-*.so*' | head -n1))

      for so in $(find $out -name '*.so'); do
        patchelf --set-rpath "$libDir:${pkgs.zlib}/lib:${pkgs.stdenv.cc.cc.lib}/lib" "$so" || true
      done
    '';

    doCheck = false;
  };

  python = pkgs.python312.withPackages (ps: [
    ps.pyyaml
    carlaPythonPkg
  ]);
in {
  inherit carlaPythonPkg python carlaLibPath;
}

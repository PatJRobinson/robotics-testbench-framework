{pkgs}: let
  carlaLibPath = pkgs.lib.makeLibraryPath [
    pkgs.zlib
    pkgs.stdenv.cc.cc.lib
  ];

  carlaPythonPkg = pkgs.python311Packages.buildPythonPackage rec {
    pname = "carla";
    version = "0.9.16";
    format = "wheel";

    src = pkgs.fetchPypi {
      inherit pname version format;
      dist = "cp311";
      python = "cp311";
      abi = "cp311";
      platform = "manylinux_2_31_x86_64";
      hash = "sha256-nKHgeTpfRTN1qLyT2F1DzFYpszQrr+EKuOux70+xEdw=";
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
      libDir=$(dirname $(find $out -name 'libwebp-702eed9c.so.6.0.2' | head -n1))

      for so in $(find $out -name '*.so'); do
        patchelf --set-rpath "$libDir:${pkgs.zlib}/lib:${pkgs.stdenv.cc.cc.lib}/lib" "$so" || true
      done
    '';

    doCheck = false;
  };

  python = pkgs.python311.withPackages (ps: [
    carlaPythonPkg
  ]);
in {
  inherit carlaPythonPkg python carlaLibPath;
}

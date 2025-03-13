{
  mkShell,
  lib,
  linuxHeaders,
  python3
}:
mkShell {
  strictDeps = true;

  # Python analytics dependencies
  packages = [
      linuxHeaders
    (python3.withPackages (python-pkgs: with python-pkgs; [
      wcwidth
    ]))
  ];

  nativeBuildInputs = [];

  buildInputs = [];

  shellHook = ''
    export PYTHONPATH=$PWD:$PYTHONPATH
  '';

  C_INCLUDE_PATH = "${linuxHeaders}/include";
}

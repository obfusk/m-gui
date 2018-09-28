{ pkgs ? import <nixpkgs> {} }:

let
  _mmm = import (builtins.fetchGit {
    url = "https://github.com/obfusk/m.git";
    rev = "e4ff278e3461d77d54469cf49cce8fe3814f7489";           # TODO
    ref = "e4ff278-tag-you-are-it";                             # TODO
  }) {};
in pkgs.python3Packages.buildPythonApplication rec {
  pname                 = "mmm-gui";
  version               = "0.1.1";
  src                   = builtins.path {
    name                = "m-gui";
    path                = ./.;
    filter              = pkgs.lib.cleanSourceFilter;
  };
  buildInputs           = [ pkgs.pandoc ];
  preConfigure          = "make README.rst";
  nativeBuildInputs     = [ pkgs.wrapGAppsHook ];
  propagatedBuildInputs = with pkgs; with pkgs.python3Packages; [
    _mmm pygobject3 gobjectIntrospection gtk3 gnome3.vte
  ];
  meta                  = {
    description         = "minimalistic media manager - gui";
    homepage            = "https://github.com/obfusk/m-gui";
    license             = pkgs.stdenv.lib.licenses.gpl3Plus;
  };
}

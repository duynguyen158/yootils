let
    nixpkgs = fetchTarball "https://github.com/NixOS/nixpkgs/tarball/nixos-24.11";
    pkgs = import nixpkgs { config = {}; overlays = []; };
    
    # When the latest version of uv is available on https://search.nixos.org/packages,
    # we can remove this snippet (and the uvx shell hook below) and just install uv like this:
    # packages = with pkgs; [ uv ];
    uv = pkgs.stdenv.mkDerivation {
        pname = "uv";
        version = "0.5.7"; # Update this to the version you want

        src = pkgs.fetchurl {
            url = "https://github.com/astral-sh/uv/releases/download/${uv.version}/uv-aarch64-apple-darwin.tar.gz";
            sha256 = "sha256-uMqyWrLsBxTbs0F5+UjCeqSrMHvlTgYo6eHu8dImT58=";  # You'll get the correct hash from the error
        };

        installPhase = ''
            mkdir -p $out/bin
            cp uv $out/bin/
            chmod +x $out/bin/uv
        '';
    };
in
pkgs.mkShellNoCC {
    packages = with pkgs; [
        uv
    ];
    
    shellHook = ''
        # Create a wrapper script for uvx
        mkdir -p $PWD/.local/bin
        echo '#!/bin/sh' > $PWD/.local/bin/uvx
        echo 'uv tool run "$@"' >> $PWD/.local/bin/uvx
        chmod +x $PWD/.local/bin/uvx
        export PATH=$PWD/.local/bin:$PATH
    '';
}
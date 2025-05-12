let
    nixpkgs = fetchTarball "https://github.com/NixOS/nixpkgs/tarball/nixos-unstable";
    pkgs = import nixpkgs { config = { allowUnfree = true; }; overlays = []; };
in
pkgs.mkShellNoCC {
    packages = with pkgs; [
        uv
    ];
}
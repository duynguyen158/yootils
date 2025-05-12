# yootils

Stuff I often need. [Also born out of work at the NYT](https://github.com/Rich-Harris/yootils).

## Usage
This package is available on PyPI. Run
```zsh
pip install yootils
```

to install utilities without any extra external dependencies. To install utilities that require external dependencies, such as those for GCP authentication, inside `yootils/google`, add an extra, e.g.,

```zsh
pip install 'yootils[google]'
```

## Development
This project uses [uv](https://docs.astral.sh/uv/) to manage Python dependencies.

Frequently used commands or groups of commands are defined as `Makefile` recipes. Run `make help` to see a list of available recipes.

### Setting up system dependencies
Run `direnv allow` to enable direnv for this project, if you haven't already.

Edit the list of system dependencies in `shell.nix`. When you're ready, `cd` again into the project directory. All system dependencies will be installed in a sealed environment specific to your project. This environment will unload if you `cd` out of the project directory, and reload if you `cd` back in. Any changes you make to `shell.nix`, including adding or removing dependencies from the declared `packages` list automatically sync to your environment every time you hit Enter on the command line.

The [Nix package repository](https://search.nixos.org/packages) is a good place to search for packages you can install (use the `unstable` channel). If a package isn't available, you can try building it from scratch directly within `shell.nix`. Here's an example of how to install Vespa
```nix
let
    nixpkgs = fetchTarball "https://github.com/NixOS/nixpkgs/tarball/nixos-unstable";
    pkgs = import nixpkgs { 
        config = {
            allowUnfree = true;
        }; 
        overlays = []; 
    };
    
    # Install vespa-cli from source since it isn't available on nixpkgs
    # Then you can reference vespa-cli below
    vespa-cli = pkgs.stdenv.mkDerivation {
        name = "vespa-cli";
        version = "8.489.59";
        src = pkgs.fetchurl {
            url = "https://github.com/vespa-engine/vespa/releases/download/v8.489.59/vespa-cli_8.489.59_darwin_arm64.tar.gz";
            sha256 = "sha256-lyRR50CTi4eBYz5zhfFfp/lhFHonb2ruVUOsnJaKaHo=";
        };
        unpackPhase = "tar -xzf $src";
        installPhase = ''
            mkdir -p $out/bin
            cp vespa-cli_8.489.59_darwin_arm64/bin/vespa $out/bin/vespa
        '';
        buildPhase = " : "; # No build needed, it's precompiled
    };
in
pkgs.mkShellNoCC {
    packages = with pkgs; [
        vespa-cli # References the vespa-cli derivation created above
    ];
}
```

### Setting up project dependencies
It's literally as easy as
```zsh
make install
```

### Running tests
Run
```zsh
make test
```
to run all unit and (if available) integration tests.

### Code formatting
Applies to Python and (if applicable) Terraform code.
```zsh
make format
```

We use [Ruff](https://docs.astral.sh/ruff/) as the formatter for Python. Rules are specified in `pyproject.toml`.

### Code linting
Here, "linting" refers to the process of static-type checking in Python and (if applicable) validation of Terraform configurations.
```zsh
make lint
```

We use [Pyright](https://github.com/microsoft/pyright) as the Python static type checker. Rules are also specified in `pyproject.toml`.

## Deployment
This package is automatically deployed to PyPI when pull request to the `main` branch is merged and the version number is bumped, via GitHub Actions.

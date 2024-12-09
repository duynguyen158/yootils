# yootils

Stuff I often need. [Also born out of work at the NYT](https://github.com/Rich-Harris/yootils).

## Usage
This package is available on PyPI.
```zsh
pip install yootils
```

## Development
This project uses [uv](https://docs.astral.sh/uv/) as the package and project manager.

### Setting up
If you use Nix and `direnv`, you can add the following to your `.envrc`:
```zsh
use nix
```
and then run `direnv allow`. The next time you enter the directory, the environment (including system dependencies such as uv) will be installed automatically in a hermetically sealed environment.

Refer to the Makefile recipes for a list of supported commands, including formatting and type-checking code.

## Deployment
This package is automatically deployed to PyPI when pull request to the `main` branch is merged and the version number is bumped, via GitHub Actions.

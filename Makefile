# GENERAL
.PHONY: all help

all: help
	@echo "Please specify a target."

help: # Show help for each of the Makefile recipes
	@grep -E '^[a-zA-Z0-9 -]+:.*#'  Makefile | sort | while read -r l; do printf "\033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done

# SETUP
.PHONY: install

install: # Install the project dependencies
	uv sync --all-groups --all-extras
	uv tool install ruff --upgrade
	uv tool install pyright --upgrade

# DEVELOPMENT
.PHONY: format lint test

format: # Format the code
	uv tool run ruff format
	uv tool run ruff check --fix

lint: # Lint the code
	uv tool run pyright

test: # Run the tests
	@PYTHON_MAJOR_MINOR_VERSION=$(shell uv run python -V | grep -oE "[0-9]+\.[0-9]+") \
	    uv run pytest --cov=yootils/ --cov-report term-missing tests/

# RELEASE
.PHONY: bump-% show-version

bump-patch: # Bump the patch version
	uv version --bump patch

bump-minor: # Bump the minor version
	uv version --bump minor

bump-major: # Bump the major version
	uv version --bump major

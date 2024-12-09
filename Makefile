# GENERAL
.PHONY: all help

all: help
	@echo "Please specify a target."

help: # Show help for each of the Makefile recipes
	@grep -E '^[a-zA-Z0-9 -]+:.*#'  Makefile | sort | while read -r l; do printf "\033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done

# SETUP
.PHONY: install

install: # Install the project dependencies
	uv sync

# DEVELOPMENT
.PHONY: format lint test

format: # Format the code
	uvx ruff format
	uvx ruff check --fix

lint: # Lint the code
	uvx pyright

test: # Run the tests
	uv run pytest --cov=yootils/ tests/

# RELEASE
.PHONY: bump-% release show-version

show-version: # Show the current version
	@eval $(shell uvx bumpver show -n --environ) && echo $$PEP440_VERSION

bump-patch: # Bump the patch version
	uvx bumpver update --patch

bump-minor: # Bump the minor version
	uvx bumpver update --minor

bump-major: # Bump the major version
	uvx bumpver update --major

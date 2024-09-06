# GENERAL
.PHONY: all help

# VARIABLES
VERSION = $(shell poetry version -s)

all: help
	@echo "Please specify a target."

help: # Show help for each of the Makefile recipes
	@grep -E '^[a-zA-Z0-9 -]+:.*#'  Makefile | sort | while read -r l; do printf "\033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done

# SETUP
.PHONY: install

install: # Install the project dependencies
	poetry install --no-root

# DEVELOPMENT
.PHONY: format lint test

format: # Format the code
	pre-commit run --all-files

lint: # Lint the code
	mypy

test: # Run the tests
	pytest --cov=yootils/ tests/
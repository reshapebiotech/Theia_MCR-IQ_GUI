# Project tasks. Run `just` to list them.

set shell := ["bash", "-euo", "pipefail", "-c"]

default:
    @just --list --unsorted

# Create or update the virtual environment with all dependency groups
sync:
    uv sync --all-groups

# Start the GUI
gui *args:
    uv run theia-mcr-gui {{args}}

# Run a CLI command, e.g. `just cli ports` or `just cli --lens TL410_R6 focus rel 100`
cli *args:
    uv run theia-mcr {{args}}

# Lint with ruff
lint:
    uv run ruff check

# Format the code in place
fmt:
    uv run ruff format

# Check formatting without changing files
fmt-check:
    uv run ruff format --check

# Type-check with ty
typecheck:
    uv run ty check

# Run the test suite
test *args:
    uv run pytest {{args}}

# Everything CI runs: lint, format check, type check, tests
check: lint fmt-check typecheck test

# Fix what ruff can fix, then format
fix:
    uv run ruff check --fix
    uv run ruff format

# Install the git hooks
hooks:
    uv run pre-commit install --install-hooks
    uv run pre-commit install --hook-type pre-push

# Run every pre-commit hook against all files
hooks-run:
    uv run pre-commit run --all-files --hook-stage manual

# Build the wheel and sdist into dist/
build:
    uv build

# Remove build, cache and test artifacts (keeps .venv and .theia-mcr)
clean:
    rm -rf dist build .pytest_cache .ruff_cache
    find . -name __pycache__ -type d -prune -exec rm -rf {} +

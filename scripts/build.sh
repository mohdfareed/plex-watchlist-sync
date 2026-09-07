#!/bin/sh
set -eu

# Apply safe fixes and formatting only to our application, not the legacy copy.
uv run --locked ruff check --fix app
uv run --locked ruff format app

# Build the wheel and source distribution after the checks succeed.
uv build

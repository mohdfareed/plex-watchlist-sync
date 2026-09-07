#!/bin/sh
set -eu

# Build and run in the foreground; Ctrl+C stops the worker.
exec docker compose -f docker/compose.yaml up --build

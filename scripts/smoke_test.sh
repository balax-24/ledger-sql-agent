#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Activate backend virtual environment if it exists
if [ -d "$ROOT_DIR/backend/.venv" ]; then
    PYTHON_EXEC="$ROOT_DIR/backend/.venv/bin/python"
else
    PYTHON_EXEC="python3"
fi

"$PYTHON_EXEC" "$SCRIPT_DIR/smoke_test.py"

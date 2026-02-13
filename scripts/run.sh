#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"

echo "Stooq - Running Main Script"
echo "========================================"

# Run core logic
"$VENV_PYTHON" "$PROJECT_DIR/src/main.py" "$@"

#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${1:-dist}"

# Activate the venv relative to this script, if it exists
if [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
else
    echo "Warning: venv not found at $SCRIPT_DIR/venv, using system/active Python" >&2
fi

mkdir -p "$OUTPUT_DIR"

pyinstaller \
--onefile \
--name mng \
--console \
--distpath "$OUTPUT_DIR" \
main.py

chmod +x "$OUTPUT_DIR/mng"

echo "Built mng → $OUTPUT_DIR/mng"
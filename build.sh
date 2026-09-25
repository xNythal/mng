#!/bin/bash

set -e

OUTPUT_DIR="${1:-dist}"

mkdir -p "$OUTPUT_DIR"

pyinstaller \
    --onefile \
    --name mng \
    --console \
    --distpath "$OUTPUT_DIR" \
    main.py

chmod +x "$OUTPUT_DIR/mng"

echo "Built mng → $OUTPUT_DIR/mng"
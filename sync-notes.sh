#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
DOWNLOAD_DIR="$SCRIPT_DIR/supernote"

uv run python "$SCRIPT_DIR/main.py" "$DOWNLOAD_DIR"
echo "DONE"

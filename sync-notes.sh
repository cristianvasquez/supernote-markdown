#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
DOWNLOAD_DIR="$SCRIPT_DIR/supernote"

# Check if --extract-images flag is passed
if [[ "$1" == "--extract-images" ]]; then
    echo "Running sync with image extraction enabled..."
    uv run python "$SCRIPT_DIR/main.py" "$DOWNLOAD_DIR" --extract-images
else
    echo "Running sync (notes only). Use --extract-images to enable image extraction."
    uv run python "$SCRIPT_DIR/main.py" "$DOWNLOAD_DIR"
fi

echo "DONE"

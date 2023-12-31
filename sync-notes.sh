#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
DOWNLOAD_DIR="$SCRIPT_DIR/supernote"

# Activate the virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Run the Python script
python "$SCRIPT_DIR/main.py" "$DOWNLOAD_DIR"

# Deactivate the virtual environment
deactivate

# Sync obsidian vault

OBSIDIAN_DIR="/home/cvasquez/obsidian/workspace/supernote"

# Execute rsync with mirror sync options

echo "Sync $DOWNLOAD_DIR into $OBSIDIAN_DIR"
rsync -av --delete "$DOWNLOAD_DIR/" "$OBSIDIAN_DIR/"

echo "Mirror sync completed"

echo "DONE"

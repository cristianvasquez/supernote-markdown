#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# Activate the virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Run the Python script
python "$SCRIPT_DIR/main.py"

# Deactivate the virtual environment (optional)
deactivate

# Sync obsidian vault

# Define source and target directories
source_dir="$SCRIPT_DIR/supernote"
target_dir="/home/cvasquez/obsidian/workspace/supernote"

# Execute rsync with mirror sync options
rsync -av --delete "$source_dir/" "$target_dir/"

echo "Mirror sync completed"

echo "DONE"

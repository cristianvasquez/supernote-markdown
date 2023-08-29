#!/bin/bash

# Get the absolute path of the script's directory
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Define source and target directories
source_dir="$script_dir/supernote"
target_dir="/home/cvasquez/obsidian/workspace/supernote"

# Execute rsync with mirror sync options
rsync -av --delete "$source_dir/" "$target_dir/"

echo "Mirror sync completed"

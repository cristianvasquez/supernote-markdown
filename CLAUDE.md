# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Supernote Sync (supernote-sync) is a Python-based tool that processes Supernote `.note` files in two modes: syncing from Google Drive with intelligent incremental updates, or processing individual files locally. It extracts images in SVG or PNG format with folder structure preservation.

## Development Commands

### Environment Setup
```bash
# Install dependencies (requires uv package manager)
uv sync
```

### Usage Modes

#### Google Drive Sync Mode
```bash
# Sync notes only (no image extraction)
./sync-notes.sh
# or
uv run python main.py ./supernote

# Sync with image extraction (SVG format)
./sync-notes.sh --extract-images
# or  
uv run python main.py ./supernote --extract-images
```

**Note**: The `sync-notes.sh` script currently uses a hardcoded path `/home/cvasquez/supernote-notes` instead of the documented `./supernote` path.

#### Single File Processing Mode
```bash
# Extract images from a single .note file (SVG format, default)
uv run python main.py output_directory/ --single-file path/to/file.note

# Extract as PNG format
uv run python main.py output_directory/ --single-file path/to/file.note --format png

# Extract as SVG format (explicit)
uv run python main.py output_directory/ --single-file path/to/file.note --format svg
```

## Architecture Overview

### Core Components

**`main.py`** - Unified processing engine with two operational modes:

**Google Drive Sync Mode:**
- Handles Google Drive OAuth authentication (`credentials.json` → `token.json`)
- Implements MD5-based change detection (file ID + modification time + size)
- Preserves Google Drive folder structure in local `supernote/notes/` directory
- Manages sync state in `sync_state.json` for incremental updates
- Moves deleted files to timestamped `.deleted/` directory
- Extracts images to SVG format when `--extract-images` flag is used

**Single File Processing Mode:**
- Processes individual `.note` files without Google Drive integration
- Supports both SVG and PNG output formats via `--format` option
- Uses simple page numbering (page_01.svg, page_02.svg, etc.)
- No sync state management needed

### File Organization
```
supernote/
├── notes/           # .note files (preserving Drive folder structure)
├── images/          # Extracted SVG images (with --extract-images)
├── sync_state.json  # Synchronization metadata
└── .deleted/        # Archived deleted files with timestamps
```

### Key Dependencies
- **Google APIs**: Authentication and Drive access (sync mode only)
- **supernotelib**: Proprietary `.note` format parsing with SVG and PNG conversion support
- **pillow**: Image processing for PNG format output
- **tqdm**: Progress bars for user feedback
- **uv**: Modern Python package manager (required)

## Important Notes

### Google Drive API Setup (Sync Mode Only)
Required for Google Drive sync mode:
1. Google Cloud Console project with Drive API enabled
2. `credentials.json` file in project root  
3. OAuth flow completion (opens browser automatically)

### Dependency Management
- Uses `uv` package manager exclusively
- No OCR dependencies to keep the package lightweight
- Clean dependency tree focused on core functionality

### Image Format Support
- **SVG**: Vector format preserving handwriting stroke quality (default for sync mode)
- **PNG**: Raster format for broader compatibility (available in single-file mode)
- Format selection via `--format` option in single-file mode

### Sync Behavior (Google Drive Mode)
- Only downloads changed/new files (efficient for large collections)
- Maintains exact Google Drive folder hierarchy locally
- Handles interruptions gracefully via persistent sync state
- Intelligent change detection prevents unnecessary re-downloads

## Development Workflow

The application now has a single entry point (`main.py`) with two distinct modes. When modifying sync logic, test with small subsets first. For single-file processing, test with various .note files to ensure format compatibility.

### Exploration Scripts

Several standalone exploration scripts are available in the root directory for analyzing Supernote collections:
- `advanced_note_explorer.py` - Advanced note structure analysis
- `analyze_collection.py` - Collection-wide analysis
- `explore_note_structure.py` - Basic note structure exploration
- `extract_all_structure.py` - Extract complete structure data
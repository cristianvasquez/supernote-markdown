# Supernote MCP Server

MCP (Model Context Protocol) server providing Supernote file operations through a standardized interface.

## Features

- **Split Notes**: Split a Supernote file into two separate files at any page
- **Merge Notes**: Combine two Supernote files into a single file  
- **Extract Images**: Export all pages as SVG or PNG images
- **Extract Titles**: Export title/anchor regions as PNG images
- **Analyze Collection**: Generate summary reports of note collections

## Prerequisites

- Node.js (for MCP server)
- Python 3 with `supernotelib` package
- MCP-compatible client (Claude Desktop, etc.)

## Installation

1. Install dependencies:
```bash
pnpm install
```

2. Install Python dependencies:
```bash
pip install supernotelib
```

## MCP Client Configuration

Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "supernote": {
      "command": "node",
      "args": ["/path/to/supernote-mcp/src/server.js"]
    }
  }
}
```

## Available Tools

### split_note
Split a Supernote file at a specific page.

**Parameters:**
- `input_file`: Path to input .note file
- `split_page`: Page number to split at (1-based)
- `output_file1`: Path for first part
- `output_file2`: Path for second part
- `policy`: Parser policy ("strict" or "loose")

### merge_notes
Merge two Supernote files into one.

**Parameters:**
- `input_file1`: First .note file
- `input_file2`: Second .note file  
- `output_file`: Path for merged output
- `policy`: Parser policy ("strict" or "loose")

### extract_images
Extract all pages as image files.

**Parameters:**
- `input_file`: Path to input .note file
- `output_dir`: Directory for extracted images
- `format`: Image format ("svg" or "png")
- `policy`: Parser policy ("strict" or "loose")

### extract_titles
Extract title/anchor regions as PNG images.

**Parameters:**
- `input_file`: Path to input .note file
- `output_dir`: Directory for extracted titles
- `invert`: Invert colors (boolean)
- `policy`: Parser policy ("strict" or "loose")

### analyze_collection
Analyze a collection of Supernote files.

**Parameters:**
- `directory`: Directory containing .note files
- `output_file`: Output markdown file path

## Direct Script Usage

You can also run the Python scripts directly:

```bash
# Split a note
python split_note.py input.note 5 part1.note part2.note

# Merge notes  
python merge_note.py note1.note note2.note merged.note

# Extract images
python extract_images.py input.note ./images --format png

# Extract titles
python extract_titles.py input.note ./titles --invert

# Analyze collection
python analyze_collection.py ./notes --output analysis.md
```

## Development

Run in development mode with auto-restart:
```bash
pnpm run dev
```
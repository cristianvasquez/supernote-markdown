# Supernote Sync

Python script that downloads Supernote `.note` files from Google Drive and converts them to Markdown files with SVG images for each page.

## Features

- Downloads all `.note` files from Google Drive
- Converts each note page to SVG format
- Generates Markdown files with YAML frontmatter
- Creates an index file linking all notes
- Progress bars for downloads and conversions
- Obsidian-compatible output format

## Installation

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

1. Install uv if you haven't already:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Clone the repository and install dependencies:
   ```bash
   git clone <your-repo-url>
   cd supernote-sync
   uv sync
   ```

## Setup

### Google Drive API Configuration

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Drive API
4. Create credentials (OAuth 2.0 Client ID for Desktop Application)
5. Download the credentials and save as `credentials.json` in the project root

## Usage

### Direct execution
```bash
uv run python main.py <target_directory>
```

### Using the sync script
```bash
./sync-notes.sh
```

The sync script downloads notes to `./supernote/` and can optionally sync to an Obsidian vault.

## Output Structure

```
target_directory/
├── images/           # SVG files (one per note page)
├── notes/           # Markdown files
└── index.md         # Index linking all notes
```

### Example Note Output

```markdown
---
alias: My Note.note
file_size: 892.49KB
last_modified: 2023-07-25T23:44:57.496Z
---

# My Note.note

![[file_id_0.svg|My Note.note page-1]] ![[file_id_1.svg|My Note.note page-2]]
```

### Index File

The generated `index.md` contains links to all converted notes:

```markdown
# Notes Index

## [[My Note.note file_id.md|My Note.note]]

## [[Another Note.note file_id2.md|Another Note.note]]
```

## Dependencies

- `google-auth` - Google authentication
- `google-auth-oauthlib` - OAuth2 flow
- `google-auth-httplib2` - HTTP library for Google APIs  
- `google-api-python-client` - Google Drive API client
- `supernotelib` - Supernote file processing
- `tqdm` - Progress bars

## Authentication Flow

On first run, the script will:
1. Open your browser for Google OAuth consent
2. Save authentication tokens to `token.json`
3. Use saved tokens for subsequent runs

## Obsidian Integration

To sync with Obsidian, uncomment and configure the rsync section in `sync-notes.sh`:

```bash
OBSIDIAN_DIR="/path/to/your/obsidian/vault/supernote"
rsync -av --delete "$DOWNLOAD_DIR/" "$OBSIDIAN_DIR/"
```

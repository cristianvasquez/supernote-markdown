from __future__ import print_function

import io
import os
import tempfile
import shutil
import json
import hashlib
from datetime import datetime
import argparse

import supernotelib as sn
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from tqdm import tqdm

POLICY = 'strict'
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


def get_size_format(b, factor=1024, suffix="B"):
    """Scale bytes to its proper byte format"""
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if b < factor:
            return f"{b:.2f}{unit}{suffix}"
        b /= factor
    return f"{b:.2f}Y{suffix}"


def get_google_drive_service():
    """Initialize and return Google Drive service"""
    script_dir = os.path.dirname(os.path.realpath(__file__))
    token_path = os.path.join(script_dir, 'token.json')
    credentials_path = os.path.join(script_dir, 'credentials.json')

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    return build('drive', 'v3', credentials=creds)


def load_sync_state(target_directory):
    """Load the synchronization state from sync_state.json"""
    sync_state_file = os.path.join(target_directory, 'sync_state.json')
    if os.path.exists(sync_state_file):
        with open(sync_state_file, 'r') as f:
            return json.load(f)
    return {}


def save_sync_state(target_directory, sync_state):
    """Save the synchronization state to sync_state.json"""
    sync_state_file = os.path.join(target_directory, 'sync_state.json')
    with open(sync_state_file, 'w') as f:
        json.dump(sync_state, f, indent=2)


def get_file_hash(file_id, modified_time, size):
    """Generate a hash for a file based on its ID, modification time, and size"""
    hash_input = f"{file_id}_{modified_time}_{size}"
    return hashlib.md5(hash_input.encode()).hexdigest()


def get_content_hash(file_path, chunk_size=8192):
    """Calculate MD5 hash of file content"""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        print(f"Warning: Could not calculate content hash for {file_path}: {e}")
        return None


def get_folder_path(file_parents, service, folder_cache=None):
    """Resolve the full folder path for a file from Google Drive"""
    if folder_cache is None:
        folder_cache = {}

    if not file_parents:
        return ""

    parent_id = file_parents[0]  # Use the first parent

    # Check cache first
    if parent_id in folder_cache:
        return folder_cache[parent_id]

    try:
        # Get parent folder info
        parent = service.files().get(fileId=parent_id, fields="name, parents").execute()
        parent_name = parent.get('name', '')
        parent_parents = parent.get('parents', [])

        # Recursively build the path
        parent_path = get_folder_path(parent_parents, service, folder_cache)

        if parent_path:
            full_path = os.path.join(parent_path, parent_name)
        else:
            full_path = parent_name

        # Cache the result
        folder_cache[parent_id] = full_path
        return full_path

    except Exception as e:
        print(f"Warning: Could not resolve folder path for parent {parent_id}: {e}")
        folder_cache[parent_id] = ""
        return ""


def download_file(file_id, file_size, file_path, service, chunk_size=1024 * 1024):
    """Download a file from Google Drive directly to disk with accurate progress"""
    request = service.files().get_media(fileId=file_id)

    with open(file_path, 'wb') as f, tqdm(
        total=file_size, unit='B', unit_scale=True, unit_divisor=1024,
        desc=f"Downloading {os.path.basename(file_path)}"
    ) as pbar:
        downloader = MediaIoBaseDownload(f, request, chunksize=chunk_size)
        done = False
        prev_bytes = 0

        while not done:
            status, done = downloader.next_chunk()
            if status:
                current = status.resumable_progress
                pbar.update(current - prev_bytes)
                prev_bytes = current



def cleanup_extractions_for_file(relative_path, target_directory):
    """Delete existing extractions for a file that has been updated"""
    # Remove file extension to get base name for extraction directories
    note_name = os.path.basename(relative_path).replace('.note', '')
    folder_path = os.path.dirname(relative_path)

    # Cleanup images directory
    images_dir = os.path.join(target_directory, 'images')
    if folder_path:
        image_extraction_dir = os.path.join(images_dir, folder_path, note_name)
    else:
        image_extraction_dir = os.path.join(images_dir, note_name)

    if os.path.exists(image_extraction_dir):
        shutil.rmtree(image_extraction_dir)
        print(f"Cleaned up old images: {image_extraction_dir}")

    # Cleanup titles directory
    titles_dir = os.path.join(target_directory, 'titles')
    if folder_path:
        title_extraction_dir = os.path.join(titles_dir, folder_path, note_name)
    else:
        title_extraction_dir = os.path.join(titles_dir, note_name)

    if os.path.exists(title_extraction_dir):
        shutil.rmtree(title_extraction_dir)
        print(f"Cleaned up old titles: {title_extraction_dir}")


def move_to_deleted(file_path, target_directory):
    """Move a file to the .deleted directory"""
    deleted_dir = os.path.join(target_directory, '.deleted')
    os.makedirs(deleted_dir, exist_ok=True)

    filename = os.path.basename(file_path)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    deleted_path = os.path.join(deleted_dir, f"{timestamp}_{filename}")

    if os.path.exists(file_path):
        shutil.move(file_path, deleted_path)
        print(f"Moved deleted file to: {deleted_path}")


def cleanup_deleted_files(sync_state, current_files, target_directory):
    """Handle files that were deleted from Google Drive"""
    deleted_files = set(sync_state.keys()) - current_files

    for deleted_file_id in deleted_files:
        deleted_file_info = sync_state[deleted_file_id]
        relative_path = deleted_file_info.get('relative_path', deleted_file_info['name'])
        print(f"File deleted from Google Drive: {relative_path}")

        # Move note file to .deleted directory
        notes_dir = os.path.join(target_directory, 'notes')
        note_path = os.path.join(notes_dir, relative_path)
        move_to_deleted(note_path, target_directory)

        # Clean up any existing extractions for this file
        cleanup_extractions_for_file(relative_path, target_directory)

        # Remove from sync state
        del sync_state[deleted_file_id]

    return len(deleted_files)


def setup_directories(target_directory):
    """Create necessary directories"""
    notes_output_dir = os.path.join(target_directory, 'notes')
    os.makedirs(notes_output_dir, exist_ok=True)

    return notes_output_dir


def should_download_file(file_id, file_info, sync_state, notes_output_dir, folder_path, note_file_name):
    """Determine if a file needs to be downloaded"""
    # Get the expected local path
    if folder_path:
        target_folder = os.path.join(notes_output_dir, folder_path)
        note_output_path = os.path.join(target_folder, note_file_name)
    else:
        note_output_path = os.path.join(notes_output_dir, note_file_name)

    # If file doesn't exist locally, download it
    if not os.path.exists(note_output_path):
        return True, "File does not exist locally"

    # If we don't have sync state for this file, download it
    if file_id not in sync_state:
        return True, "No sync state found"

    sync_info = sync_state[file_id]

    # Check if the file has been modified on Google Drive
    if (sync_info.get('modified_time') != file_info['modified_time'] or
        sync_info.get('size') != file_info['size']):
        return True, "File modified on Google Drive"

    # If we have a content hash stored, verify it matches
    if 'content_hash' in sync_info:
        local_content_hash = get_content_hash(note_output_path)
        if local_content_hash != sync_info['content_hash']:
            return True, "Local file content differs"

    # File is up to date
    return False, "File is up to date"


def process_note_file(file, sync_state, current_files, temp_dir, notes_output_dir, target_directory, service, folder_cache):
    """Process a single note file from Google Drive"""
    file_id = file["id"]
    file_size = int(file["size"])
    modified_time = file["modifiedTime"]
    note_file_name = file["name"]
    file_parents = file.get("parents", [])

    current_files.add(file_id)

    # Get folder path
    folder_path = get_folder_path(file_parents, service, folder_cache)
    relative_path = os.path.join(folder_path, note_file_name) if folder_path else note_file_name

    # Prepare file info for comparison
    file_info = {
        'size': file_size,
        'modified_time': modified_time
    }

    # Check if we need to download this file
    should_download, reason = should_download_file(
        file_id, file_info, sync_state, notes_output_dir, folder_path, note_file_name
    )

    if not should_download:
        # File is up to date, just update the sync state with current info
        existing_info = sync_state.get(file_id, {})
        sync_state[file_id] = {
            'hash': get_file_hash(file_id, modified_time, file_size),
            'content_hash': existing_info.get('content_hash'),  # Preserve existing content hash
            'name': note_file_name,
            'size': file_size,
            'modified_time': modified_time,
            'folder_path': folder_path,
            'relative_path': relative_path,
            'last_synced': existing_info.get('last_synced', datetime.now().isoformat())
        }

        save_sync_state(target_directory, sync_state)
        print(f"Skipping unchanged file: {relative_path}")
        return False

    print(f"Processing file: {relative_path} (Reason: {reason})")

    # If file has changed, clean up old extractions
    if file_id in sync_state:
        cleanup_extractions_for_file(relative_path, target_directory)

    # Download the note file
    note_temp_path = os.path.join(temp_dir, file_id)
    download_file(file_id, file_size, note_temp_path, service)

    # Create directory structure and copy note file
    if folder_path:
        target_folder = os.path.join(notes_output_dir, folder_path)
        os.makedirs(target_folder, exist_ok=True)
        note_output_path = os.path.join(target_folder, note_file_name)
    else:
        note_output_path = os.path.join(notes_output_dir, note_file_name)

    shutil.copy2(note_temp_path, note_output_path)

    # Calculate content hash of the downloaded file
    content_hash = get_content_hash(note_output_path)

    # Update sync state
    sync_state[file_id] = {
        'hash': get_file_hash(file_id, modified_time, file_size),
        'content_hash': content_hash,
        'name': note_file_name,
        'size': file_size,
        'modified_time': modified_time,
        'folder_path': folder_path,
        'relative_path': relative_path,
        'last_synced': datetime.now().isoformat()
    }

    # Save immediately
    save_sync_state(target_directory, sync_state)

    return True


def sync_notes(target_directory):
    """Main synchronization function"""
    service = get_google_drive_service()
    query = "mimeType != 'application/vnd.google-apps.folder' and name contains '.note' and trashed = false"

    # Load previous sync state
    sync_state = load_sync_state(target_directory)
    current_files = set()
    folder_cache = {}  # Cache for folder path resolution

    # Setup directories
    notes_output_dir = setup_directories(target_directory)

    files_processed = 0
    files_skipped = 0

    with tempfile.TemporaryDirectory() as temp_dir:
        # Get files from Google Drive
        page_token = None

        while True:
            response = service.files().list(
                q=query,
                spaces="drive",
                fields="nextPageToken, files(id, name, mimeType, size, parents, modifiedTime)",
                pageToken=page_token
            ).execute()

            for file in response.get("files", []):
                note_file_name = file["name"]

                if "size" in file and note_file_name.endswith(".note"):
                    processed = process_note_file(
                        file, sync_state, current_files, temp_dir,
                        notes_output_dir, target_directory, service, folder_cache
                    )

                    if processed:
                        files_processed += 1
                    else:
                        files_skipped += 1

            page_token = response.get('nextPageToken', None)
            if not page_token:
                break

        # Handle deleted files
        deleted_count = cleanup_deleted_files(sync_state, current_files, target_directory)

        # Save updated sync state
        save_sync_state(target_directory, sync_state)

        # Print summary
        print(f"\nSync completed:")
        print(f"  Files processed: {files_processed}")
        print(f"  Files skipped (unchanged): {files_skipped}")
        print(f"  Files deleted: {deleted_count}")


def process_single_file(note_file_path, output_dir, format='svg'):
    """Process a single .note file and extract images"""
    if not os.path.exists(note_file_path):
        print(f"Error: Note file not found: {note_file_path}")
        return 1

    os.makedirs(output_dir, exist_ok=True)

    print(f"Processing: {note_file_path}")
    print(f"Output directory: {output_dir}")
    print(f"Format: {format.upper()}")

    # Import and use extract_images function from extract_images.py
    from extract_images import extract_images
    success = extract_images(note_file_path, output_dir, format)

    if success:
        print(f"\nExtraction completed! Images saved to: {output_dir}")
        return 0
    else:
        return 1


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Sync Supernote files from Google Drive or process single files')
    parser.add_argument('target_directory', help='Target directory for sync or single file output')
    parser.add_argument('--single-file', metavar='NOTE_FILE',
                       help='Process a single .note file instead of syncing from Google Drive')
    parser.add_argument('--format', choices=['svg', 'png'], default='svg',
                       help='Image format for extraction (default: svg)')
    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_arguments()

    if args.single_file:
        # Single file processing mode
        return process_single_file(args.single_file, args.target_directory, args.format)
    else:
        # Google Drive sync mode
        sync_notes(args.target_directory)
        return 0


if __name__ == '__main__':
    exit(main())

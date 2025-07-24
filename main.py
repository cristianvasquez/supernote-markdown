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


def download_file(file_id, file_size, file_path, service):
    """Download a file from Google Drive with progress bar"""
    request = service.files().get_media(fileId=file_id)
    downloaded_file = io.BytesIO()
    downloader = MediaIoBaseDownload(downloaded_file, request)
    
    with tqdm(total=file_size, unit='B', unit_scale=True, unit_divisor=1024) as progress_bar:
        done = False
        while not done:
            status, done = downloader.next_chunk()
            progress_bar.update(status.total_size)

    downloaded_file.seek(0)
    with open(file_path, 'wb') as f:
        f.write(downloaded_file.read())


def extract_images(note_file_path, images_output_dir, file_id=None, format='svg'):
    """Extract images from a note file to SVG or PNG files"""
    notebook = sn.load_notebook(note_file_path, policy=POLICY)
    total_pages = notebook.get_total_pages()
    max_digits = len(str(total_pages))
    
    if format.lower() == 'png':
        converter = sn.converter.ImageConverter(notebook)
        extension = 'png'
    else:
        palette = None
        converter = sn.converter.SvgConverter(notebook, palette=palette)
        extension = 'svg'

    for i in tqdm(range(total_pages), desc=f"Extracting images from {os.path.basename(note_file_path)}"):
        if file_id:
            # For Google Drive sync - use file_id prefix
            numbered_filename = f"{file_id}_{str(i).zfill(max_digits)}.{extension}"
        else:
            # For single file processing - use page numbers
            numbered_filename = f"page_{str(i+1).zfill(max_digits)}.{extension}"
        
        numbered_filename_path = os.path.join(images_output_dir, numbered_filename)
        img = converter.convert(i)

        if extension == 'svg':
            with open(numbered_filename_path, 'w') as f:
                f.write(img)
        else:
            img.save(numbered_filename_path)


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


def cleanup_deleted_files(sync_state, current_files, target_directory, extract_images_flag):
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
        
        # Move associated images to .deleted directory if image extraction was enabled
        if extract_images_flag:
            images_dir = os.path.join(target_directory, 'images')
            folder_path = deleted_file_info.get('folder_path', '')
            
            if folder_path:
                image_folder = os.path.join(images_dir, folder_path)
            else:
                image_folder = images_dir
            
            if os.path.exists(image_folder):
                # Look for image files that start with the file_id
                for root, dirs, files in os.walk(image_folder):
                    for image_file in files:
                        if image_file.startswith(deleted_file_id + '_'):
                            image_path = os.path.join(root, image_file)
                            move_to_deleted(image_path, target_directory)
        
        # Remove from sync state
        del sync_state[deleted_file_id]
    
    return len(deleted_files)


def setup_directories(target_directory, extract_images_flag):
    """Create necessary directories"""
    notes_output_dir = os.path.join(target_directory, 'notes')
    os.makedirs(notes_output_dir, exist_ok=True)
    
    images_output_dir = None
    if extract_images_flag:
        images_output_dir = os.path.join(target_directory, 'images')
        os.makedirs(images_output_dir, exist_ok=True)
    
    return notes_output_dir, images_output_dir


def process_note_file(file, sync_state, current_files, temp_dir, notes_output_dir, images_output_dir, service, extract_images_flag, folder_cache):
    """Process a single note file from Google Drive"""
    file_id = file["id"]
    file_size = int(file["size"])
    modified_time = file["modifiedTime"]
    note_file_name = file["name"]
    file_parents = file.get("parents", [])
    
    # Generate file hash for change detection
    file_hash = get_file_hash(file_id, modified_time, file_size)
    current_files.add(file_id)
    
    # Get folder path
    folder_path = get_folder_path(file_parents, service, folder_cache)
    relative_path = os.path.join(folder_path, note_file_name) if folder_path else note_file_name
    
    # Check if file has changed since last sync
    if file_id in sync_state and sync_state[file_id].get('hash') == file_hash:
        print(f"Skipping unchanged file: {relative_path}")
        return False
    
    print(f"Processing {'new' if file_id not in sync_state else 'updated'} file: {relative_path}")
    
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
    
    # Extract images if requested (organize by folder structure too)
    if extract_images_flag and images_output_dir:
        if folder_path:
            image_folder = os.path.join(images_output_dir, folder_path)
            os.makedirs(image_folder, exist_ok=True)
        else:
            image_folder = images_output_dir
        extract_images(note_temp_path, image_folder, file_id, 'svg')
    
    # Update sync state
    sync_state[file_id] = {
        'hash': file_hash,
        'name': note_file_name,
        'size': file_size,
        'modified_time': modified_time,
        'folder_path': folder_path,
        'relative_path': relative_path,
        'last_synced': datetime.now().isoformat()
    }
    
    return True


def sync_notes(target_directory, extract_images_flag=False):
    """Main synchronization function"""
    service = get_google_drive_service()
    query = "mimeType != 'application/vnd.google-apps.folder' and name contains '.note' and trashed = false"
    
    # Load previous sync state
    sync_state = load_sync_state(target_directory)
    current_files = set()
    folder_cache = {}  # Cache for folder path resolution
    
    # Setup directories
    notes_output_dir, images_output_dir = setup_directories(target_directory, extract_images_flag)
    
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
                        notes_output_dir, images_output_dir, service, extract_images_flag, folder_cache
                    )
                    
                    if processed:
                        files_processed += 1
                    else:
                        files_skipped += 1
            
            page_token = response.get('nextPageToken', None)
            if not page_token:
                break
        
        # Handle deleted files
        deleted_count = cleanup_deleted_files(sync_state, current_files, target_directory, extract_images_flag)
        
        # Save updated sync state
        save_sync_state(target_directory, sync_state)
        
        # Print summary
        print(f"\nSync completed:")
        print(f"  Files processed: {files_processed}")
        print(f"  Files skipped (unchanged): {files_skipped}")
        print(f"  Files deleted: {deleted_count}")
        if extract_images_flag:
            print(f"  Images extracted: Yes")
        else:
            print(f"  Images extracted: No (use --extract-images to enable)")


def process_single_file(note_file_path, output_dir, format='svg'):
    """Process a single .note file and extract images"""
    if not os.path.exists(note_file_path):
        print(f"Error: Note file not found: {note_file_path}")
        return 1
    
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Processing: {note_file_path}")
    print(f"Output directory: {output_dir}")
    print(f"Format: {format.upper()}")
    
    extract_images(note_file_path, output_dir, None, format)
    
    print(f"\nExtraction completed! Images saved to: {output_dir}")
    return 0


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Sync Supernote files from Google Drive or process single files')
    parser.add_argument('target_directory', help='Target directory for sync or single file output')
    parser.add_argument('--extract-images', action='store_true', 
                       help='Extract images from note files to SVG format (sync mode)')
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
        sync_notes(args.target_directory, args.extract_images)
        return 0


if __name__ == '__main__':
    exit(main())
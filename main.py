from __future__ import print_function

import io
import os
import os.path
import os.path
import tempfile
import shutil

import supernotelib as sn
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from tqdm import tqdm
import argparse

POLICY = 'strict'


def get_size_format(b, factor=1024, suffix="B"):
    """
    Scale bytes to its proper byte format
    e.g:
        1253656 => '1.20MB'
        1253656678 => '1.17GB'
    """
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if b < factor:
            return f"{b:.2f}{unit}{suffix}"
        b /= factor
    return f"{b:.2f}Y{suffix}"


SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


def get_google_drive_service():
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.realpath(__file__))

    # Construct the paths relative to the script directory
    token_path = os.path.join(script_dir, 'token.json')
    credentials_path = os.path.join(script_dir, 'credentials.json')

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        # Set up OAuth 2.0 credentials
        flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    # Create a Drive service
    return build('drive', 'v3', credentials=creds)


def produce_numbered_images(note_filename, images_output_dir, file_id):
    notebook = sn.load_notebook(note_filename, policy=POLICY)
    total_pages = notebook.get_total_pages()
    palette = None
    converter = sn.converter.SvgConverter(notebook, palette=palette)

    max_digits = len(str(total_pages))

    file_names = []

    for i in tqdm(range(total_pages), desc="Converting {}".format(note_filename)):
        numbered_filename = file_id + '_' + str(i).zfill(max_digits) + '.svg'
        numbered_filename_path = os.path.join(images_output_dir, numbered_filename)
        img = converter.convert(i)

        with open(numbered_filename_path, 'w') as f:
            f.write(img)

        file_names.append(numbered_filename)

    return file_names


def produce_markdown(file_name, images, modified, size, note_title):
    with open(file_name, 'w') as markdown_file:
        # Write YAML metadata
        metadata = f"---\nalias: {note_title}\nfile_size: {size}\nlast_modified: {modified}\n---\n\n"
        markdown_file.write(metadata)

        markdown_file.write(f"# {note_title}\n\n")

        # Write image section for each file in file_names
        for i, image_file in enumerate(images, start=1):
            markdown_file.write(f"![[{image_file}|{note_title} page-{i}]] ")


def download_file(file_id, file_size, file_path, service):
    # Download the file with tqdm progress bar
    request = service.files().get_media(fileId=file_id)
    downloaded_file = io.BytesIO()
    downloader = MediaIoBaseDownload(downloaded_file, request)
    with tqdm(total=file_size, unit='B', unit_scale=True, unit_divisor=1024) as progress_bar:
        done = False
        while not done:
            status, done = downloader.next_chunk()
            progress_bar.update(status.total_size)

    # Save the downloaded content to a file
    downloaded_file.seek(0)
    with open(file_path, 'wb') as f:
        f.write(downloaded_file.read())


def generate_index(index_file_name, notes):
    with open(index_file_name, 'w') as index_file:
        index_file.write("# Notes Index\n\n")
        for note in notes:
            index_file.write(f"## [[{note['markdown_file']}|{note['title']}]]\n\n")


def main(target_directory):
    service = get_google_drive_service()

    query = "mimeType != 'application/vnd.google-apps.folder' and name contains '.note' and trashed = false"
    note_details = []

    with tempfile.TemporaryDirectory() as temp_dir:

        images_output_dir = os.path.join(target_directory, 'images')

        # Delete the 'images' directory if it exists
        if os.path.exists(images_output_dir):
            shutil.rmtree(images_output_dir)

        # Create the 'images' directory again
        os.makedirs(images_output_dir)

        notes_output_dir = os.path.join(target_directory, 'notes')

        # Delete the 'notes' directory if it exists
        if os.path.exists(notes_output_dir):
            shutil.rmtree(notes_output_dir)

        # Create the 'notes' directory again
        os.makedirs(notes_output_dir)

        # get the GDrive ID of the file
        page_token = None

        while True:
            response = service.files().list(q=query,
                                            spaces="drive",
                                            fields="nextPageToken, files(id, name, mimeType, size, parents, modifiedTime)",
                                            pageToken=page_token).execute()

            for file in response.get("files", []):
                note_file_name = file["name"]

                if "size" in file and note_file_name.endswith(".note"):
                    file_id = file["id"]
                    file_size = int(file["size"])

                    markdown_file_name = '{} {}.md'.format(note_file_name, file_id)

                    note_details.append({
                        "title": note_file_name,
                        "markdown_file": markdown_file_name
                    })

                    # Download and produce the images
                    note_path = os.path.join(temp_dir, file_id)
                    download_file(file_id, file_size, note_path, service)
                    images = produce_numbered_images(note_path, images_output_dir, file_id)

                    # Produce the markdown
                    markdown_file_name = os.path.join(notes_output_dir, markdown_file_name)
                    produce_markdown(markdown_file_name, images, file["modifiedTime"], get_size_format(file_size),
                                     note_file_name)

            page_token = response.get('nextPageToken', None)
            if not page_token:
                # no more files
                break
    index_file_name = os.path.join(target_directory, 'index.md')
    generate_index(index_file_name, note_details)

def parse_arguments():
    parser = argparse.ArgumentParser(description='Process Google Drive notes and produce numbered images.')
    parser.add_argument('target_directory', help='Target directory for download')
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_arguments()
    print('ARGS',args)
    main(args.target_directory)
    main()

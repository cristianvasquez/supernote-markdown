#!/usr/bin/env python3

import argparse
import os
import sys
from tqdm import tqdm
import supernotelib as sn

def extract_images(note_file_path, output_dir, format='svg'):
    """Extract images from a note file to SVG or PNG files"""
    if not os.path.exists(note_file_path):
        print(f"Error: Note file not found: {note_file_path}", file=sys.stderr)
        return False
    
    try:
        notebook = sn.load_notebook(note_file_path, policy='strict')
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
            # Use page numbers for filename
            numbered_filename = f"page_{str(i+1).zfill(max_digits)}.{extension}"
            numbered_filename_path = os.path.join(output_dir, numbered_filename)
            img = converter.convert(i)

            if extension == 'svg':
                with open(numbered_filename_path, 'w') as f:
                    f.write(img)
            else:
                img.save(numbered_filename_path)
        
        return True
    except Exception as e:
        print(f"Error processing {note_file_path}: {e}", file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(
        prog='extract_images',
        description='Extracts all pages from a Supernote *.note file and saves them as individual SVG or PNG images.'
    )
    parser.add_argument('input', type=str, help='Input *.note file.')
    parser.add_argument('output_dir', type=str, help='Directory to save the output image files.')
    parser.add_argument(
        '--format',
        choices=['svg', 'png'],
        default='svg',
        help='Output format for images (default: svg).'
    )
    parser.add_argument(
        '--policy',
        choices=['strict', 'loose'],
        default='strict',
        help='Select parser policy for loading the note.'
    )

    args = parser.parse_args()

    # Argument validation and setup
    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.output_dir):
        print(f"Output directory not found. Creating directory: {args.output_dir}")
        os.makedirs(args.output_dir)

    print(f"Processing: {args.input}")
    print(f"Output directory: {args.output_dir}")
    print(f"Format: {args.format.upper()}")
    
    success = extract_images(args.input, args.output_dir, args.format)
    
    if success:
        print(f"\nExtraction completed! Images saved to: {args.output_dir}")
        sys.exit(0)
    else:
        print("Extraction failed.", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
#!/usr/bin/env python3

# Copyright (c) 2024 Gemini
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import os
import sys
import json
import traceback
from PIL import Image, ImageOps
import supernotelib as sn
from supernotelib.decoder import RattaRleDecoder, RattaRleX2Decoder
from supernotelib import exceptions

def main():
    parser = argparse.ArgumentParser(
        prog='extract_titles',
        description='Extracts all titles (anchors) from a Supernote *.note file and saves them as individual PNG images.'
    )
    parser.add_argument('input', type=str, help='Input *.note file.')
    parser.add_argument('output_dir', type=str, help='Directory to save the output PNG files.')
    parser.add_argument(
        '--policy',
        choices=['strict', 'loose'],
        default='strict',
        help='Select parser policy for loading the note.'
    )
    parser.add_argument(
        '--invert',
        action='store_true',
        help='Invert image colors (e.g., to get black text on a white background).'
    )


    args = parser.parse_args()

    # --- Argument Validation and Setup ---
    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.output_dir):
        print(f"Output directory not found. Creating directory: {args.output_dir}")
        os.makedirs(args.output_dir)

    try:
        print(f"Loading notebook: {args.input}...")
        notebook = sn.load_notebook(args.input, policy=args.policy)
        titles = notebook.get_titles()

        if not titles:
            print("No titles found in this note.")
            sys.exit(0)

        print(f"Found {len(titles)} titles. Extracting to {args.output_dir}...")

        for i, title in enumerate(titles):
            metadata = title.metadata
            content_1bit = title.get_content()

            if not content_1bit:
                print(f"Skipping title {i+1} on page {title.get_page_number() + 1} (no content).")
                continue

            # The rectangle of the title is stored in its metadata
            try:
                # TITLERECTORI contains the original rectangle
                rect = list(map(int, metadata['TITLERECTORI'].split(',')))
                width, height = rect[2], rect[3]
            except (KeyError, ValueError) as e:
                print(f"Warning: Could not determine dimensions for title {i+1}. Skipping. Error: {e}", file=sys.stderr)
                continue

            if width == 0 or height == 0:
                print(f"Warning: Skipping title {i+1} on page {title.get_page_number() + 1} due to zero dimensions (width={width}, height={height}).", file=sys.stderr)
                continue

            # Determine which RLE decoder to use based on the note's signature
            signature = notebook.get_metadata().signature
            if signature.startswith('SN_FILE_VER_2023') or signature.startswith('SN_FILE_VER_2022'): # Assuming X2-series signatures
                decoder = RattaRleX2Decoder()
            else:
                decoder = RattaRleDecoder()
            try:
                bitmap, (decoded_width, decoded_height), bpp = decoder.decode(content_1bit, width, height)
            except exceptions.DecoderException as e:
                print(f"Warning: Skipping title {i+1} on page {title.get_page_number() + 1} due to decoding error: {e}", file=sys.stderr)
                continue
            except Exception as e:
                print(f"Warning: Skipping title {i+1} on page {title.get_page_number() + 1} due to unexpected error during decoding: {e}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr) # Print full traceback
                continue

            # Explicitly check decoded data before creating image
            if not isinstance(bitmap, bytes) or not isinstance(decoded_width, int) or not isinstance(decoded_height, int):
                print(f"Warning: Skipping title {i+1} on page {title.get_page_number() + 1} due to invalid decoded data type. Bitmap type: {type(bitmap)}, Width type: {type(decoded_width)}, Height type: {type(decoded_height)}.", file=sys.stderr)
                continue
            if decoded_width <= 0 or decoded_height <= 0:
                print(f"Warning: Skipping title {i+1} on page {title.get_page_number() + 1} due to invalid decoded dimensions ({decoded_width}, {decoded_height}).", file=sys.stderr)
                continue
            if decoded_width != width or decoded_height != height:
                print(f"Warning: Skipping title {i+1} on page {title.get_page_number() + 1} due to dimension mismatch after decoding. Expected ({width}, {height}), got ({decoded_width}, {decoded_height}).", file=sys.stderr)
                continue

            img = Image.frombytes('L', (width, height), bitmap)

            if args.invert:
                # Invert colors to make it more readable (e.g., black text on white background)
                img = ImageOps.invert(img)

            page_num = title.get_page_number()
            # Use a clear and sortable filename
            filename = f"page_{page_num + 1:04d}_title_{i + 1:02d}.png"
            filepath = os.path.join(args.output_dir, filename)

            img.save(filepath, 'PNG')
            print(f"Saved: {filepath}")

        print("\nExtraction complete.")

    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()

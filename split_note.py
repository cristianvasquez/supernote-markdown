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
import copy

import supernotelib as sn
from supernotelib.fileformat import Page, Keyword, Title, Link, Cover

class SubsetNotebook:
    """
    A wrapper class that presents a subset of a Notebook's pages and metadata,
    making it compatible with the reconstruct function.
    """
    def __init__(self, original_notebook, start_page, end_page):
        if not (0 <= start_page <= end_page <= original_notebook.get_total_pages()):
            raise ValueError("Invalid page range")

        self._notebook = original_notebook
        self._start_page = start_page
        self._end_page = end_page
        self._total_pages = end_page - start_page
        self._metadata = self._notebook.get_metadata()

    def get_metadata(self):
        return self._metadata

    def get_total_pages(self):
        return self._total_pages

    def get_page(self, page_num):
        if not (0 <= page_num < self._total_pages):
            raise IndexError("Page number out of range for subset")
        return self._notebook.get_page(page_num + self._start_page)

    def get_cover(self):
        # Both split notes will share the same cover
        return self._notebook.get_cover()

    def _filter_and_remap(self, items, item_class):
        """Filters items based on page range and remaps their page numbers."""
        new_items = []
        for item in items:
            original_page_num = item.get_page_number()
            if self._start_page <= original_page_num < self._end_page:
                new_item = copy.deepcopy(item)
                new_item.set_page_number(original_page_num - self._start_page)
                new_items.append(new_item)
        return new_items

    def get_keywords(self):
        return self._filter_and_remap(self._notebook.get_keywords(), Keyword)

    def get_titles(self):
        return self._filter_and_remap(self._notebook.get_titles(), Title)

    def get_links(self):
        """
        Filters links and remaps both source and destination page numbers.
        Links pointing outside the subset are excluded.
        """
        new_links = []
        for link in self._notebook.get_links():
            original_page_num = link.get_page_number()
            original_link_to = link.get_link_to_page_number()

            if self._start_page <= original_page_num < self._end_page and \
               self._start_page <= original_link_to < self._end_page:
                new_link = copy.deepcopy(link)
                new_link.set_page_number(original_page_num - self._start_page)
                new_link.set_link_to_page_number(original_link_to - self._start_page)
                new_links.append(new_link)
        return new_links


def split_notebook(notebook, split_page_index):
    """
    Splits a notebook into two SubsetNotebook objects at a given page index.
    """
    total_pages = notebook.get_total_pages()
    if not (0 < split_page_index < total_pages):
        raise ValueError(f"Split page must be between 1 and {total_pages - 1}")

    part1 = SubsetNotebook(notebook, 0, split_page_index)
    part2 = SubsetNotebook(notebook, split_page_index, total_pages)
    return part1, part2

def main():
    parser = argparse.ArgumentParser(
        prog='split_note',
        description='Splits a Supernote *.note file into two separate files.'
    )
    parser.add_argument('input', type=str, help='Input *.note file to split.')
    parser.add_argument(
        'split_page',
        type=int,
        help='The page number to split AT. This page will become the first page of the second file. (1-based)'
    )
    parser.add_argument(
        'output1',
        type=str,
        help='Output file name for the first part of the note.'
    )
    parser.add_argument(
        'output2',
        type=str,
        help='Output file name for the second part of the note.'
    )
    parser.add_argument(
        '--policy',
        choices=['strict', 'loose'],
        default='strict',
        help='Select parser policy for loading the note.'
    )

    args = parser.parse_args()

    # --- Argument Validation ---
    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    if not args.output1.endswith('.note') or not args.output2.endswith('.note'):
        print("Warning: Output files should typically have a '.note' extension.", file=sys.stderr)

    try:
        print(f"Loading notebook: {args.input}...")
        notebook = sn.load_notebook(args.input, policy=args.policy)
        total_pages = notebook.get_total_pages()
        
        # Convert 1-based page number from user to 0-based index for logic
        split_index = args.split_page - 1

        if not (0 < args.split_page <= total_pages):
            print(f"Error: split_page must be between 1 and {total_pages}.", file=sys.stderr)
            sys.exit(1)
        
        if args.split_page == total_pages:
             print(f"Warning: Splitting at the last page will result in an empty second note.", file=sys.stderr)


        print(f"Splitting note at page {args.split_page}...")
        note_part1, note_part2 = split_notebook(notebook, split_index)

        # --- Reconstruct and Write Part 1 ---
        print(f"Reconstructing first part ({note_part1.get_total_pages()} pages)...")
        binary1 = sn.reconstruct(note_part1)
        with open(args.output1, 'wb') as f:
            f.write(binary1)
        print(f"Successfully saved first part to: {args.output1}")

        # --- Reconstruct and Write Part 2 ---
        print(f"Reconstructing second part ({note_part2.get_total_pages()} pages)...")
        binary2 = sn.reconstruct(note_part2)
        with open(args.output2, 'wb') as f:
            f.write(binary2)
        print(f"Successfully saved second part to: {args.output2}")

    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()

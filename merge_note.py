#!/usr/bin/env python3

import argparse
import os
import sys
import copy

import supernotelib as sn
from supernotelib.fileformat import Page, Keyword, Title, Link, Cover

class MergedNotebook:
    """
    A wrapper class that presents two notebooks as a single merged notebook,
    making it compatible with the reconstruct function.
    """
    def __init__(self, notebook1, notebook2):
        self._notebook1 = notebook1
        self._notebook2 = notebook2
        self._offset = notebook1.get_total_pages()
        self._total_pages = notebook1.get_total_pages() + notebook2.get_total_pages()
        self._metadata = notebook1.get_metadata()

    def get_metadata(self):
        return self._metadata

    def get_total_pages(self):
        return self._total_pages

    def get_page(self, page_num):
        if not (0 <= page_num < self._total_pages):
            raise IndexError("Page number out of range for merged notebook")
        
        if page_num < self._offset:
            return self._notebook1.get_page(page_num)
        else:
            return self._notebook2.get_page(page_num - self._offset)

    def get_cover(self):
        # Use the first notebook's cover
        return self._notebook1.get_cover()

    def get_keywords(self):
        """Merge keywords from both notebooks, remapping page numbers for second notebook."""
        merged_keywords = []
        
        # Add keywords from first notebook (no remapping needed)
        for keyword in self._notebook1.get_keywords():
            merged_keywords.append(copy.deepcopy(keyword))
        
        # Add keywords from second notebook (remap page numbers)
        for keyword in self._notebook2.get_keywords():
            new_keyword = copy.deepcopy(keyword)
            new_keyword.set_page_number(keyword.get_page_number() + self._offset)
            merged_keywords.append(new_keyword)
        
        return merged_keywords

    def get_titles(self):
        """Merge titles from both notebooks, remapping page numbers for second notebook."""
        merged_titles = []
        
        # Add titles from first notebook (no remapping needed)
        for title in self._notebook1.get_titles():
            merged_titles.append(copy.deepcopy(title))
        
        # Add titles from second notebook (remap page numbers)
        for title in self._notebook2.get_titles():
            new_title = copy.deepcopy(title)
            new_title.set_page_number(title.get_page_number() + self._offset)
            merged_titles.append(new_title)
        
        return merged_titles

    def get_links(self):
        """
        Skip links entirely to avoid complexity.
        Cross-notebook links would be broken anyway, and internal link remapping is complex.
        """
        return []


def merge_notebooks(notebook1, notebook2):
    """
    Merges two notebooks into a single MergedNotebook object.
    """
    return MergedNotebook(notebook1, notebook2)


def main():
    parser = argparse.ArgumentParser(
        prog='merge_note',
        description='Merges two Supernote *.note files into a single file.'
    )
    parser.add_argument('input1', type=str, help='First *.note file to merge.')
    parser.add_argument('input2', type=str, help='Second *.note file to merge.')
    parser.add_argument('output', type=str, help='Output file name for the merged note.')
    parser.add_argument(
        '--policy',
        choices=['strict', 'loose'],
        default='strict',
        help='Select parser policy for loading the notes.'
    )

    args = parser.parse_args()

    # --- Argument Validation ---
    if not os.path.exists(args.input1):
        print(f"Error: Input file not found: {args.input1}", file=sys.stderr)
        sys.exit(1)
    
    if not os.path.exists(args.input2):
        print(f"Error: Input file not found: {args.input2}", file=sys.stderr)
        sys.exit(1)

    if not args.output.endswith('.note'):
        print("Warning: Output file should typically have a '.note' extension.", file=sys.stderr)

    try:
        print(f"Loading first notebook: {args.input1}...")
        notebook1 = sn.load_notebook(args.input1, policy=args.policy)
        
        print(f"Loading second notebook: {args.input2}...")
        notebook2 = sn.load_notebook(args.input2, policy=args.policy)
        
        print(f"Merging notebooks ({notebook1.get_total_pages()} + {notebook2.get_total_pages()} pages)...")
        merged_notebook = merge_notebooks(notebook1, notebook2)

        # --- Reconstruct and Write Merged Notebook ---
        print(f"Reconstructing merged notebook ({merged_notebook.get_total_pages()} pages)...")
        binary_data = sn.reconstruct(merged_notebook)
        
        with open(args.output, 'wb') as f:
            f.write(binary_data)
        
        print(f"Successfully saved merged notebook to: {args.output}")

    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
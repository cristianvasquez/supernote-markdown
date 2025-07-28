#!/usr/bin/env python3
"""
Analyze an entire collection of Supernote files and generate a comprehensive markdown summary.
"""

import os
import sys
import argparse
from pathlib import Path
import json
from datetime import datetime
import base64
import re

import supernotelib as sn

def decode_base64_path(encoded_path):
    """Decode base64 encoded file paths"""
    try:
        decoded = base64.b64decode(encoded_path).decode('utf-8')
        # Extract just the filename from the path
        return os.path.basename(decoded)
    except:
        return encoded_path

def extract_file_structure(note_file_path):
    """Extract key structural information from a note file"""
    try:
        notebook = sn.load_notebook(note_file_path, policy='strict')
    except Exception as e:
        return {
            'error': str(e),
            'file_path': note_file_path,
            'file_name': os.path.basename(note_file_path)
        }
    
    structure = {
        'file_path': note_file_path,
        'file_name': os.path.basename(note_file_path),
        'file_size_mb': round(os.path.getsize(note_file_path) / (1024*1024), 1),
        'total_pages': notebook.get_total_pages(),
        'titles_count': 0,
        'links_count': 0,
        'keywords_count': 0,
        'titles': [],
        'links': [],
        'web_links': [],
        'file_links': [],
        'layer_info': {}
    }
    
    # Extract titles
    try:
        titles = notebook.get_titles()
        structure['titles_count'] = len(titles)
        
        for title in titles:
            title_info = {
                'page': title.get_page_number() if hasattr(title, 'get_page_number') else None,
                'position': title.get_position() if hasattr(title, 'get_position') else None,
                'content_size': len(title.get_content()) if hasattr(title, 'get_content') and title.get_content() else 0
            }
            
            # Try to get title metadata
            if hasattr(title, 'metadata') and title.metadata:
                title_info['level'] = title.metadata.get('TITLELEVEL', '1')
                title_info['rect'] = title.metadata.get('TITLERECT', '')
            
            structure['titles'].append(title_info)
    except Exception as e:
        structure['titles_error'] = str(e)
    
    # Extract links
    try:
        links = notebook.get_links()
        structure['links_count'] = len(links)
        
        for link in links:
            link_info = {
                'page': link.get_page_number() if hasattr(link, 'get_page_number') else None,
                'direction': link.get_inout() if hasattr(link, 'get_inout') else None
            }
            
            # Get target information
            if hasattr(link, 'get_filepath'):
                filepath = link.get_filepath()
                if filepath:
                    decoded_path = decode_base64_path(filepath)
                    link_info['target'] = decoded_path
                    
                    # Categorize link type
                    if decoded_path.startswith('http'):
                        structure['web_links'].append({
                            'page': link_info['page'],
                            'url': decoded_path
                        })
                    elif decoded_path.endswith('.note'):
                        structure['file_links'].append({
                            'page': link_info['page'],
                            'target_file': decoded_path
                        })
            
            structure['links'].append(link_info)
    except Exception as e:
        structure['links_error'] = str(e)
    
    # Extract keywords
    try:
        keywords = notebook.get_keywords()
        structure['keywords_count'] = len(keywords)
    except:
        pass
    
    # Analyze layer information
    try:
        total_main_content = 0
        total_bg_content = 0
        
        for page_num in range(structure['total_pages']):
            page = notebook.get_page(page_num)
            if hasattr(page, 'get_layers'):
                layers = page.get_layers()
                for layer in layers:
                    if hasattr(layer, 'get_name') and hasattr(layer, 'get_content'):
                        name = layer.get_name()
                        content = layer.get_content()
                        if content:
                            if name == 'MAINLAYER':
                                total_main_content += len(content)
                            elif name == 'BGLAYER':
                                total_bg_content += len(content)
        
        structure['layer_info'] = {
            'total_main_content_kb': round(total_main_content / 1024, 1),
            'total_bg_content_kb': round(total_bg_content / 1024, 1),
            'avg_content_per_page_kb': round(total_main_content / (1024 * structure['total_pages']), 1) if structure['total_pages'] > 0 else 0
        }
    except Exception as e:
        structure['layer_info'] = {'error': str(e)}
    
    return structure

def analyze_directory(directory_path):
    """Analyze all .note files in a directory recursively"""
    note_files = []
    
    # Find all .note files
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            if file.endswith('.note'):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, directory_path)
                note_files.append({
                    'full_path': full_path,
                    'relative_path': rel_path,
                    'folder': os.path.dirname(rel_path) if os.path.dirname(rel_path) else 'Root'
                })
    
    print(f"Found {len(note_files)} .note files")
    
    # Analyze each file
    results = []
    for i, note_file in enumerate(note_files, 1):
        print(f"Analyzing {i}/{len(note_files)}: {note_file['relative_path']}")
        structure = extract_file_structure(note_file['full_path'])
        structure['relative_path'] = note_file['relative_path']
        structure['folder'] = note_file['folder']
        results.append(structure)
    
    return results

def generate_markdown_summary(analysis_results, output_file):
    """Generate a comprehensive markdown summary"""
    
    # Sort by folder, then by filename
    analysis_results.sort(key=lambda x: (x.get('folder', ''), x.get('file_name', '')))
    
    # Calculate totals
    total_files = len(analysis_results)
    total_pages = sum(r.get('total_pages', 0) for r in analysis_results)
    total_size_mb = sum(r.get('file_size_mb', 0) for r in analysis_results)
    total_titles = sum(r.get('titles_count', 0) for r in analysis_results)
    total_links = sum(r.get('links_count', 0) for r in analysis_results)
    avg_pages = total_pages / total_files if total_files > 0 else 0
    
    # Group by folder
    folders = {}
    for result in analysis_results:
        folder = result.get('folder', 'Root')
        if folder not in folders:
            folders[folder] = []
        folders[folder].append(result)
    
    # Generate markdown
    md_content = f"""# Supernote Collection Analysis

**Analysis Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📊 Collection Overview

| Metric | Value |
|--------|-------|
| **Total Files** | {total_files} |
| **Total Pages** | {total_pages} |
| **Total Size** | {total_size_mb:.1f} MB |
| **Total Titles/Headers** | {total_titles} |
| **Total Links** | {total_links} |
| **Average Pages per File** | {avg_pages:.1f} |

## 📁 Folder Structure

"""
    
    # Add folder overview
    for folder, files in folders.items():
        folder_pages = sum(f.get('total_pages', 0) for f in files)
        folder_size = sum(f.get('file_size_mb', 0) for f in files)
        folder_titles = sum(f.get('titles_count', 0) for f in files)
        folder_links = sum(f.get('links_count', 0) for f in files)
        
        md_content += f"""### {folder}

| Files | Pages | Size (MB) | Titles | Links |
|-------|-------|-----------|--------|-------|
| {len(files)} | {folder_pages} | {folder_size:.1f} | {folder_titles} | {folder_links} |

"""

    # Add detailed file analysis
    md_content += """## 📄 Detailed File Analysis

"""
    
    for folder, files in folders.items():
        md_content += f"""### 📁 {folder}

"""
        
        # Create table for files in this folder
        md_content += """| File | Pages | Size (MB) | Titles | Links | Web Links | File Links | Avg Content/Page |
|------|-------|-----------|--------|-------|-----------|------------|------------------|
"""
        
        for file_data in files:
            file_name = file_data.get('file_name', 'Unknown')
            pages = file_data.get('total_pages', 0)
            size_mb = file_data.get('file_size_mb', 0)
            titles = file_data.get('titles_count', 0)
            links = file_data.get('links_count', 0)
            web_links = len(file_data.get('web_links', []))
            file_links = len(file_data.get('file_links', []))
            avg_content = file_data.get('layer_info', {}).get('avg_content_per_page_kb', 0)
            
            md_content += f"""| **{file_name}** | {pages} | {size_mb} | {titles} | {links} | {web_links} | {file_links} | {avg_content} KB |
"""
        
        md_content += "\n"
        
        # Add detailed breakdown for files with interesting structure
        for file_data in files:
            if file_data.get('titles_count', 0) > 0 or file_data.get('links_count', 0) > 3:
                file_name = file_data.get('file_name', 'Unknown')
                md_content += f"""#### 📝 {file_name}

"""
                
                if 'error' in file_data:
                    md_content += f"❌ **Error**: {file_data['error']}\n\n"
                    continue
                
                # Basic info
                md_content += f"""**Basic Info**: {file_data.get('total_pages', 0)} pages, {file_data.get('file_size_mb', 0)} MB

"""
                
                # Title structure
                if file_data.get('titles_count', 0) > 0:
                    md_content += f"""**Title Structure** ({file_data.get('titles_count', 0)} titles):

| Page | Position | Content Size | Level |
|------|----------|--------------|-------|
"""
                    for title in file_data.get('titles', []):
                        page = title.get('page', '?')
                        pos = title.get('position', '?')
                        size = f"{title.get('content_size', 0)} bytes"
                        level = title.get('level', '1')
                        md_content += f"| {page} | {pos} | {size} | {level} |\n"
                    
                    md_content += "\n"
                
                # Web links
                if file_data.get('web_links'):
                    md_content += f"""**Web Links** ({len(file_data.get('web_links', []))} found):

"""
                    for web_link in file_data.get('web_links', []):
                        page = web_link.get('page', '?')
                        url = web_link.get('url', 'Unknown')
                        md_content += f"- Page {page}: [{url}]({url})\n"
                    
                    md_content += "\n"
                
                # File links (internal references)
                if file_data.get('file_links'):
                    md_content += f"""**Internal File Links** ({len(file_data.get('file_links', []))} found):

"""
                    for file_link in file_data.get('file_links', []):
                        page = file_link.get('page', '?')
                        target = file_link.get('target_file', 'Unknown')
                        md_content += f"- Page {page}: `{target}`\n"
                    
                    md_content += "\n"
                
                md_content += "---\n\n"
    
    # Add cross-reference analysis
    md_content += """## 🔗 Cross-Reference Analysis

### Most Connected Files

"""
    
    # Sort by total connectivity (titles + links)
    connected_files = [(f.get('file_name', 'Unknown'), 
                       f.get('titles_count', 0) + f.get('links_count', 0),
                       f.get('titles_count', 0),
                       f.get('links_count', 0),
                       f.get('folder', 'Root')) 
                      for f in analysis_results]
    connected_files.sort(key=lambda x: x[1], reverse=True)
    
    md_content += """| File | Total Connections | Titles | Links | Folder |
|------|-------------------|--------|-------|--------|
"""
    
    for file_name, total_conn, titles, links, folder in connected_files[:10]:
        md_content += f"| **{file_name}** | {total_conn} | {titles} | {links} | {folder} |\n"
    
    # Add file network analysis
    md_content += """

### File Network Map

Files that reference other files in the collection:

"""
    
    file_references = {}
    for file_data in analysis_results:
        file_name = file_data.get('file_name', 'Unknown')
        file_links = file_data.get('file_links', [])
        
        if file_links:
            file_references[file_name] = [fl.get('target_file', 'Unknown') for fl in file_links]
    
    for source_file, targets in file_references.items():
        if targets:
            md_content += f"- **{source_file}** → {', '.join(f'`{t}`' for t in targets[:5])}"
            if len(targets) > 5:
                md_content += f" (and {len(targets) - 5} more)"
            md_content += "\n"
    
    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    return md_content

def main():
    parser = argparse.ArgumentParser(description='Analyze collection of Supernote files')
    parser.add_argument('directory', help='Directory containing .note files')
    parser.add_argument('--output', '-o', default='supernote_collection_summary.md', 
                       help='Output markdown file (default: supernote_collection_summary.md)')
    args = parser.parse_args()
    
    if not os.path.exists(args.directory):
        print(f"Error: Directory not found: {args.directory}")
        return 1
    
    print(f"Analyzing Supernote collection in: {args.directory}")
    
    # Analyze all files
    results = analyze_directory(args.directory)
    
    # Generate markdown summary
    print(f"Generating markdown summary...")
    generate_markdown_summary(results, args.output)
    
    print(f"Summary generated: {args.output}")
    
    return 0

if __name__ == '__main__':
    exit(main())
#!/usr/bin/env python3
"""
Extract D2 diagrams from ARCHITECTURE.md and render them to images.
Requires: d2 CLI installed (brew install d2 or https://d2lang.com/install)
"""

import re
import subprocess
import os
from pathlib import Path

def extract_d2_diagrams(markdown_file):
    """Extract all D2 code blocks from markdown file."""
    with open(markdown_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match D2 code blocks
    pattern = r'```d2\n(.*?)```'
    matches = re.findall(pattern, content, re.DOTALL)
    
    diagrams = []
    for i, diagram_code in enumerate(matches):
        # Extract title if present
        title_match = re.search(r'title:\s*(.+)', diagram_code)
        if title_match:
            title = title_match.group(1).strip()
        else:
            # Try to find a heading before the code block
            title = f"Diagram {i+1}"
        
        # Clean title for filename
        filename = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '-').lower()
        filename = re.sub(r'-+', '-', filename)  # Replace multiple dashes with single
        
        diagrams.append({
            'title': title,
            'filename': filename,
            'code': diagram_code.strip()
        })
    
    return diagrams

def check_d2_installed():
    """Check if D2 CLI is installed."""
    try:
        result = subprocess.run(['d2', '--version'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

def render_diagrams(diagrams, output_dir='diagrams', formats=['svg', 'png']):
    """Render D2 diagrams to image files."""
    Path(output_dir).mkdir(exist_ok=True)
    
    success_count = 0
    failed = []
    
    for diagram in diagrams:
        d2_file = Path(output_dir) / f"{diagram['filename']}.d2"
        
        # Write D2 file
        with open(d2_file, 'w', encoding='utf-8') as f:
            f.write(diagram['code'])
        
        # Render to each format
        for fmt in formats:
            output_file = Path(output_dir) / f"{diagram['filename']}.{fmt}"
            
            try:
                result = subprocess.run(
                    ['d2', str(d2_file), str(output_file)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    print(f"✓ Rendered: {diagram['title']} -> {output_file}")
                    if fmt == formats[0]:  # Count success only once per diagram
                        success_count += 1
                else:
                    error_msg = result.stderr.strip() or result.stdout.strip()
                    print(f"✗ Error rendering {diagram['title']} ({fmt}): {error_msg}")
                    if diagram['title'] not in failed:
                        failed.append(diagram['title'])
                        
            except subprocess.TimeoutExpired:
                print(f"✗ Timeout rendering {diagram['title']} ({fmt})")
                if diagram['title'] not in failed:
                    failed.append(diagram['title'])
            except Exception as e:
                print(f"✗ Exception rendering {diagram['title']} ({fmt}): {e}")
                if diagram['title'] not in failed:
                    failed.append(diagram['title'])
    
    return success_count, failed

def generate_markdown_references(diagrams, output_dir='diagrams', format='svg'):
    """Generate markdown with image references instead of D2 code blocks."""
    references = []
    references.append("## Rendered Diagrams\n\n")
    references.append("The following diagrams have been rendered from D2 source:\n\n")
    
    for diagram in diagrams:
        image_path = f"{output_dir}/{diagram['filename']}.{format}"
        references.append(f"### {diagram['title']}\n\n")
        references.append(f"![{diagram['title']}]({image_path})\n\n")
    
    return ''.join(references)

if __name__ == '__main__':
    markdown_file = 'ARCHITECTURE.md'
    
    if not Path(markdown_file).exists():
        print(f"Error: {markdown_file} not found")
        print("Please run this script from the project root directory")
        exit(1)
    
    # Check if D2 is installed
    print("Checking for D2 CLI...")
    if not check_d2_installed():
        print("✗ Error: D2 CLI not found.")
        print("\nPlease install D2 first:")
        print("  macOS:   brew install d2")
        print("  Linux:   curl -fsSL https://d2lang.com/install.sh | sh -s -- --prefix ~/.local")
        print("  Windows: https://d2lang.com/install")
        exit(1)
    
    print("✓ D2 CLI found\n")
    
    print("Extracting D2 diagrams from ARCHITECTURE.md...")
    diagrams = extract_d2_diagrams(markdown_file)
    print(f"Found {len(diagrams)} diagrams\n")
    
    if len(diagrams) == 0:
        print("No D2 diagrams found in ARCHITECTURE.md")
        exit(0)
    
    # List found diagrams
    print("Diagrams found:")
    for i, diagram in enumerate(diagrams, 1):
        print(f"  {i}. {diagram['title']} -> {diagram['filename']}.d2")
    print()
    
    # Render diagrams
    print("Rendering diagrams...")
    print("-" * 50)
    success_count, failed = render_diagrams(diagrams, formats=['svg', 'png'])
    print("-" * 50)
    
    if success_count > 0:
        print(f"\n✓ Successfully rendered {success_count}/{len(diagrams)} diagrams")
        print(f"  Output directory: diagrams/")
        print(f"  Formats: SVG and PNG")
        
        if failed:
            print(f"\n⚠ Failed to render {len(failed)} diagram(s):")
            for title in failed:
                print(f"  - {title}")
        
        # Generate reference markdown
        ref_md = generate_markdown_references(diagrams)
        with open('diagrams/README.md', 'w', encoding='utf-8') as f:
            f.write(ref_md)
        print("\n✓ Generated diagrams/README.md with image references")
        
        print("\nTo embed in ARCHITECTURE.md, replace D2 code blocks with:")
        print("  ![Diagram Title](diagrams/diagram-filename.svg)")
    else:
        print("\n✗ No diagrams were successfully rendered")
        if failed:
            print("\nCommon issues:")
            print("  - Check D2 syntax in the code blocks")
            print("  - Verify D2 installation: d2 --version")
            print("  - Try rendering manually: d2 diagram.d2 diagram.svg")


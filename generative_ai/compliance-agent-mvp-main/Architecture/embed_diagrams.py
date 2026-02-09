#!/usr/bin/env python3
"""
Embed rendered D2 diagrams into ARCHITECTURE.md by replacing D2 code blocks with image references.
This script assumes diagrams have already been rendered using render_d2_diagrams.py
"""

import re
from pathlib import Path

def extract_d2_blocks(markdown_file):
    """Extract all D2 code blocks and their positions."""
    with open(markdown_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match D2 code blocks
    pattern = r'(```d2\n.*?```)'
    matches = list(re.finditer(pattern, content, re.DOTALL))
    
    blocks = []
    for match in matches:
        block_content = match.group(1)
        # Extract title if present
        title_match = re.search(r'title:\s*(.+)', block_content)
        title = title_match.group(1).strip() if title_match else "Diagram"
        
        # Clean title for filename
        filename = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '-').lower()
        filename = re.sub(r'-+', '-', filename)
        
        blocks.append({
            'start': match.start(),
            'end': match.end(),
            'title': title,
            'filename': filename,
            'content': block_content
        })
    
    return blocks, content

def embed_diagrams(markdown_file, diagrams_dir='diagrams', format='svg', backup=True):
    """Replace D2 code blocks with image references."""
    blocks, content = extract_d2_blocks(markdown_file)
    
    if not blocks:
        print("No D2 code blocks found in ARCHITECTURE.md")
        return False
    
    # Create backup if requested
    if backup:
        backup_file = f"{markdown_file}.backup"
        Path(markdown_file).copy(backup_file)
        print(f"Created backup: {backup_file}")
    
    # Replace blocks in reverse order to maintain positions
    new_content = content
    for block in reversed(blocks):
        image_path = f"{diagrams_dir}/{block['filename']}.{format}"
        
        # Check if image exists
        if not Path(image_path).exists():
            print(f"⚠ Warning: Image not found: {image_path}")
            print(f"  Skipping replacement for: {block['title']}")
            continue
        
        # Create image markdown
        image_markdown = f'![{block["title"]}]({image_path})\n\n'
        
        # Replace the code block
        new_content = (
            new_content[:block['start']] + 
            image_markdown + 
            new_content[block['end']:]
        )
        
        print(f"✓ Embedded: {block['title']} -> {image_path}")
    
    # Write updated content
    with open(markdown_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    return True

def restore_d2_blocks(markdown_file, backup_file=None):
    """Restore D2 code blocks from backup."""
    if backup_file is None:
        backup_file = f"{markdown_file}.backup"
    
    if not Path(backup_file).exists():
        print(f"Error: Backup file not found: {backup_file}")
        return False
    
    Path(backup_file).copy(markdown_file)
    print(f"✓ Restored D2 code blocks from: {backup_file}")
    return True

if __name__ == '__main__':
    import sys
    
    markdown_file = 'ARCHITECTURE.md'
    
    if not Path(markdown_file).exists():
        print(f"Error: {markdown_file} not found")
        exit(1)
    
    if len(sys.argv) > 1 and sys.argv[1] == '--restore':
        restore_d2_blocks(markdown_file)
        exit(0)
    
    print("Embedding rendered diagrams into ARCHITECTURE.md...")
    print("-" * 50)
    
    if embed_diagrams(markdown_file, format='svg'):
        print("-" * 50)
        print("\n✓ Successfully embedded all diagrams")
        print(f"  Diagrams are now referenced as images in {markdown_file}")
        print("\nTo restore D2 code blocks, run:")
        print("  python3 embed_diagrams.py --restore")
    else:
        print("\n✗ Failed to embed diagrams")


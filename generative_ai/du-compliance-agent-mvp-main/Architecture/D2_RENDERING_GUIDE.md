# D2 Diagram Rendering Guide

This guide explains how to render the D2 diagrams included in `ARCHITECTURE.md`.

## Option 1: D2 CLI (Recommended for Production)

### Installation

**macOS:**
```bash
brew install d2
```

**Linux:**
```bash
curl -fsSL https://d2lang.com/install.sh | sh -s -- --prefix ~/.local
```

**Windows:**
Download from [https://d2lang.com/install](https://d2lang.com/install)

### Usage

#### Method A: Extract and Render Individual Diagrams

1. Extract a D2 diagram block from the markdown file
2. Save it to a `.d2` file
3. Render to image:

```bash
# Render to PNG
d2 diagram.d2 diagram.png

# Render to SVG (better for documentation)
d2 diagram.d2 diagram.svg

# Render to PDF
d2 diagram.d2 diagram.pdf
```

#### Method B: Batch Render All Diagrams

Create a script to extract and render all diagrams:

```bash
#!/bin/bash
# render_diagrams.sh

# Create output directory
mkdir -p diagrams

# Extract and render each D2 diagram
# You'll need to manually extract each ```d2 block or use a script
```

#### Method C: Embed Rendered Images in Markdown

After rendering, replace the D2 code blocks with image references:

```markdown
<!-- Before -->
```d2
title: System Architecture
...
```

<!-- After -->
![System Architecture](diagrams/system-architecture.png)
```

## Option 2: VS Code Extension

### Installation

1. Install the **D2** extension by Terrastruct in VS Code
2. Open a `.d2` file or a markdown file with D2 code blocks
3. The extension will render diagrams inline

**Extension**: Search for "D2" in VS Code Extensions marketplace

## Option 3: Online D2 Playground

1. Go to [https://play.d2lang.com/](https://play.d2lang.com/)
2. Copy a D2 diagram code block from the markdown
3. Paste into the playground
4. Export as PNG/SVG/PDF

## Option 4: Automated Script to Extract and Render

Here's a Python script to extract all D2 diagrams and render them:

```python
#!/usr/bin/env python3
"""
Extract D2 diagrams from ARCHITECTURE.md and render them to images.
Requires: d2 CLI installed
"""

import re
import subprocess
import os
from pathlib import Path

def extract_d2_diagrams(markdown_file):
    """Extract all D2 code blocks from markdown file."""
    with open(markdown_file, 'r') as f:
        content = f.read()
    
    # Pattern to match D2 code blocks
    pattern = r'```d2\n(.*?)```'
    matches = re.findall(pattern, content, re.DOTALL)
    
    diagrams = []
    for i, diagram_code in enumerate(matches):
        # Extract title if present
        title_match = re.search(r'title:\s*(.+)', diagram_code)
        title = title_match.group(1).strip() if title_match else f"diagram_{i+1}"
        
        # Clean title for filename
        filename = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '-').lower()
        
        diagrams.append({
            'title': title,
            'filename': filename,
            'code': diagram_code
        })
    
    return diagrams

def render_diagrams(diagrams, output_dir='diagrams'):
    """Render D2 diagrams to SVG files."""
    Path(output_dir).mkdir(exist_ok=True)
    
    for diagram in diagrams:
        d2_file = Path(output_dir) / f"{diagram['filename']}.d2"
        svg_file = Path(output_dir) / f"{diagram['filename']}.svg"
        png_file = Path(output_dir) / f"{diagram['filename']}.png"
        
        # Write D2 file
        with open(d2_file, 'w') as f:
            f.write(diagram['code'])
        
        # Render to SVG
        try:
            subprocess.run(['d2', str(d2_file), str(svg_file)], check=True)
            print(f"✓ Rendered: {diagram['title']} -> {svg_file}")
        except subprocess.CalledProcessError as e:
            print(f"✗ Error rendering {diagram['title']}: {e}")
        except FileNotFoundError:
            print("✗ Error: d2 CLI not found. Please install it first.")
            return False
        
        # Also render to PNG
        try:
            subprocess.run(['d2', str(d2_file), str(png_file)], check=True)
        except:
            pass  # PNG rendering is optional
    
    return True

if __name__ == '__main__':
    markdown_file = 'ARCHITECTURE.md'
    
    if not Path(markdown_file).exists():
        print(f"Error: {markdown_file} not found")
        exit(1)
    
    print("Extracting D2 diagrams...")
    diagrams = extract_d2_diagrams(markdown_file)
    print(f"Found {len(diagrams)} diagrams")
    
    print("\nRendering diagrams...")
    if render_diagrams(diagrams):
        print(f"\n✓ All diagrams rendered to 'diagrams/' directory")
        print("\nTo embed in markdown, replace D2 code blocks with:")
        print("  ![Diagram Title](diagrams/diagram-filename.svg)")
    else:
        print("\n✗ Rendering failed. Please install D2 CLI first.")
```

**Usage:**
```bash
python3 render_diagrams.py
```

## Option 5: GitHub/GitLab Integration

GitHub and GitLab don't natively support D2, but you can:

1. **Render diagrams to images** and commit them to the repo
2. **Use a GitHub Action** to auto-render diagrams on commit
3. **Link to D2 Playground** with pre-filled code

### GitHub Action Example

Create `.github/workflows/render-d2.yml`:

```yaml
name: Render D2 Diagrams

on:
  push:
    paths:
      - 'ARCHITECTURE.md'
      - '.github/workflows/render-d2.yml'

jobs:
  render:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install D2
        run: |
          curl -fsSL https://d2lang.com/install.sh | sh -s -- --prefix ~/.local
          echo "$HOME/.local/bin" >> $GITHUB_PATH
      
      - name: Render Diagrams
        run: |
          mkdir -p diagrams
          # Add your rendering script here
          python3 render_diagrams.py
      
      - name: Commit rendered diagrams
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add diagrams/
          git commit -m "Auto-render D2 diagrams" || exit 0
          git push
```

## Option 6: Documentation Tools

### MkDocs with D2 Plugin

If using MkDocs for documentation:

1. Install plugin: `pip install mkdocs-d2-plugin`
2. Configure in `mkdocs.yml`:
```yaml
plugins:
  - d2
```

### Docusaurus

Use the `docusaurus-plugin-d2` package.

## What Happens to Generated Diagrams?

When you run `render_d2_diagrams.py`, the diagrams are:

1. **Extracted** from ARCHITECTURE.md (D2 code blocks)
2. **Rendered** to SVG and PNG files
3. **Saved** in the `diagrams/` folder
4. **NOT automatically embedded** in ARCHITECTURE.md

The diagrams stay in the `diagrams/` folder as separate image files. The ARCHITECTURE.md file still contains the D2 source code blocks.

### Option A: Keep D2 Source Code (Recommended for Development)

- Keep the D2 code blocks in ARCHITECTURE.md
- View rendered diagrams separately in the `diagrams/` folder
- Easy to update diagrams by editing D2 code
- Works well with version control

### Option B: Embed Rendered Images

To replace D2 code blocks with image references:

```bash
# First render the diagrams
python3 render_d2_diagrams.py

# Then embed them in the markdown
python3 embed_diagrams.py
```

This will:
- Replace all D2 code blocks with `![Diagram Title](diagrams/filename.svg)` references
- Create a backup of the original file (`ARCHITECTURE.md.backup`)
- Allow you to restore D2 blocks later with `python3 embed_diagrams.py --restore`

**Note**: Once embedded, you'll need to manually edit images or restore D2 blocks to make changes.

## Quick Start (Recommended)

For immediate viewing:

1. **Install D2 CLI:**
   ```bash
   brew install d2  # macOS
   # or visit https://d2lang.com/install
   ```

2. **Render all diagrams:**
   ```bash
   python3 render_d2_diagrams.py
   ```

3. **View diagrams** in the `diagrams/` folder

4. **Optional: Embed in markdown:**
   ```bash
   python3 embed_diagrams.py
   ```

## Tips

- **SVG format** is best for documentation (scalable, small file size)
- **PNG format** is good for presentations (better compatibility)
- **PDF format** is ideal for printing
- Keep D2 source files in version control for easy updates
- Use descriptive filenames based on diagram titles

## Troubleshooting

**D2 not found:**
- Ensure D2 is in your PATH
- Try: `which d2` to verify installation

**Rendering errors:**
- Check D2 syntax in the code block
- Validate with: `d2 --check diagram.d2`

**Large diagrams:**
- Use `d2 --layout=elk` for better layout of complex diagrams
- Adjust with layout options: `d2 --layout=tala` or `d2 --layout=dagre`


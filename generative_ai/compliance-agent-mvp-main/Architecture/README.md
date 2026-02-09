# Architecture Documentation

This folder contains comprehensive solution architecture documentation for the DU Compliance Agent MVP, including detailed diagrams, business value analysis, and technical specifications.

## Contents

### Main Documentation

- **`ARCHITECTURE.md`** - Complete solution architecture documentation with D2 diagrams
  - Executive Summary
  - Business Value & ROI
  - Use Cases & Scenarios
  - System Architecture
  - User Journey
  - File Processing Flow
  - Component Interaction
  - Data Flow
  - API Endpoints
  - Technology Stack
  - Component Details
  - Deployment Architecture
  - Security & Compliance
  - Integration Points
  - Environment Configuration
  - Error Handling & Edge Cases

- **`ARCHITECTURE.pdf`** - PDF version of the architecture documentation

- **`ARCHITECTURE.md.backup`** - Backup of ARCHITECTURE.md (created when embedding diagrams)

### Diagram Files

- **`diagrams/`** - Folder containing all rendered D2 diagrams
  - Source D2 files (`.d2`)
  - Rendered SVG files (`.svg`) - Best for documentation
  - Rendered PNG files (`.png`) - Best for presentations
  - `README.md` - Reference guide for all diagrams

### Supporting Files

- **`architecture.mmd`** - Original Mermaid diagram source (legacy)
- **`D2_RENDERING_GUIDE.md`** - Comprehensive guide for rendering D2 diagrams
- **`DIAGRAMS_SUMMARY.md`** - Quick reference for diagram workflows

### Scripts

- **`render_d2_diagrams.py`** - Extracts and renders all D2 diagrams from ARCHITECTURE.md
- **`embed_diagrams.py`** - Embeds rendered diagrams into ARCHITECTURE.md (replaces D2 code blocks)

## Prerequisites

Before using the diagram rendering scripts, you need to install the D2 CLI:

### macOS
```bash
brew install d2
```

### Linux
```bash
curl -fsSL https://d2lang.com/install.sh | sh -s -- --prefix ~/.local
```

### Windows
Download from [https://d2lang.com/install](https://d2lang.com/install)

### Verify Installation
```bash
d2 --version
```

## Commands

### Render Diagrams

Extract all D2 diagrams from `ARCHITECTURE.md` and render them to SVG and PNG files:

```bash
cd Architecture
python3 render_d2_diagrams.py
```

**What it does:**
- Extracts all D2 code blocks from `ARCHITECTURE.md`
- Renders each diagram to both SVG and PNG formats
- Saves rendered files to `diagrams/` folder
- Generates `diagrams/README.md` with image references

**Output:**
- `diagrams/*.d2` - Source D2 files
- `diagrams/*.svg` - SVG images (for documentation)
- `diagrams/*.png` - PNG images (for presentations)

**Note:** This does NOT modify `ARCHITECTURE.md`. The D2 source code blocks remain in the file.

### Embed Diagrams

Replace D2 code blocks in `ARCHITECTURE.md` with image references:

```bash
cd Architecture
python3 embed_diagrams.py
```

**What it does:**
- Replaces all D2 code blocks with `![Diagram Title](diagrams/filename.svg)` references
- Creates a backup file: `ARCHITECTURE.md.backup`
- Preserves the original D2 source code in the backup

**When to use:**
- For final documentation
- For presentations where images are preferred
- For GitHub/GitLab viewing (if D2 isn't supported)

**Note:** After embedding, you'll need to restore D2 blocks to edit diagrams.

### Restore D2 Code Blocks

Restore the original D2 code blocks from backup:

```bash
cd Architecture
python3 embed_diagrams.py --restore
```

**What it does:**
- Restores `ARCHITECTURE.md` from `ARCHITECTURE.md.backup`
- Brings back all D2 source code blocks
- Allows you to edit diagrams again

**When to use:**
- When you need to edit diagram source code
- When switching back to D2-based workflow

## Workflow Options

### Option A: Keep D2 Source Code (Recommended for Development)

**Workflow:**
1. Edit D2 code blocks directly in `ARCHITECTURE.md`
2. Run `python3 render_d2_diagrams.py` to generate images
3. View rendered diagrams in `diagrams/` folder
4. Keep both source and rendered versions

**Benefits:**
- Easy to edit and update diagrams
- Version control friendly (text-based)
- Source code always available

### Option B: Embed Rendered Images (Recommended for Final Documentation)

**Workflow:**
1. Edit D2 code blocks in `ARCHITECTURE.md`
2. Run `python3 render_d2_diagrams.py` to generate images
3. Run `python3 embed_diagrams.py` to replace code blocks with images
4. Use embedded version for presentations/documentation
5. Run `python3 embed_diagrams.py --restore` when you need to edit

**Benefits:**
- Better for presentations
- Works everywhere (no D2 viewer needed)
- Cleaner markdown file

## Diagram List

The architecture documentation includes 10 D2 diagrams:

1. **DU Compliance Agent - System Architecture** - High-level system architecture
2. **User Journey - Complete Flow** - Complete user interaction flow
3. **User Journey Sequence Diagram** - Sequence diagram of user journey
4. **File Processing Flow - Complete Lifecycle** - Detailed file processing pipeline
5. **Frontend Component Interaction** - Frontend component relationships
6. **Backend Component Interaction** - Backend component relationships
7. **Request/Response Data Flow** - Request/response flow diagram
8. **Streaming Data Flow** - Streaming architecture flow
9. **API Endpoint Architecture** - API endpoint structure
10. **API Request/Response Flow** - API request/response sequence

## Quick Reference

```bash
# Navigate to Architecture folder
cd Architecture

# Render all diagrams
python3 render_d2_diagrams.py

# Embed diagrams in markdown (creates backup)
python3 embed_diagrams.py

# Restore D2 code blocks
python3 embed_diagrams.py --restore

# Render a single diagram manually
d2 diagrams/diagram-name.d2 diagrams/diagram-name.svg
```

## Troubleshooting

### D2 CLI Not Found
```bash
# Verify installation
which d2
d2 --version

# If not found, install D2 (see Prerequisites above)
```

### Diagram Rendering Errors
- Check D2 syntax in code blocks
- Validate with: `d2 --check diagrams/diagram-name.d2`
- Review error messages for syntax issues

### Backup File Missing
- If `ARCHITECTURE.md.backup` is missing, you cannot restore
- Always keep backups when embedding diagrams
- Consider using version control (Git) for additional safety

## File Structure

```
Architecture/
├── README.md                    # This file
├── ARCHITECTURE.md              # Main documentation (with D2 code blocks)
├── ARCHITECTURE.md.backup       # Backup (created when embedding)
├── ARCHITECTURE.pdf             # PDF version
├── architecture.mmd             # Legacy Mermaid source
├── D2_RENDERING_GUIDE.md        # Detailed rendering guide
├── DIAGRAMS_SUMMARY.md          # Quick reference summary
├── render_d2_diagrams.py        # Render script
├── embed_diagrams.py            # Embed script
└── diagrams/                    # Rendered diagrams
    ├── README.md
    ├── *.d2                     # D2 source files
    ├── *.svg                    # SVG images
    └── *.png                    # PNG images
```

## Additional Resources

- **D2 Documentation**: [https://d2lang.com/](https://d2lang.com/)
- **D2 Playground**: [https://play.d2lang.com/](https://play.d2lang.com/)
- **D2 Installation**: [https://d2lang.com/install](https://d2lang.com/install)

## Notes

- All diagrams are rendered in both SVG (scalable, small) and PNG (compatible) formats
- SVG files are recommended for documentation
- PNG files are recommended for presentations
- D2 source files are kept in `diagrams/` for easy editing
- Always commit both source and rendered files to version control


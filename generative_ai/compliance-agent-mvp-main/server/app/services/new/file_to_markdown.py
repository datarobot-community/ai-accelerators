"""
Unified function to convert files (PDF, DOCX, TXT) to Markdown format.
If the input is already a Markdown (.md) file, it is passed through as-is.
"""

import re
from pathlib import Path
from typing import Optional

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

try:
    import mammoth
except Exception:
    mammoth = None

try:
    from markdownify import markdownify as html_to_md
except Exception:
    html_to_md = None


def sanitize_stem(name: str) -> str:
    """Sanitize a filename stem for safe file system usage."""
    sanitized = re.sub(r"\s+", " ", name).strip()
    sanitized = sanitized.replace("/", "-")
    return sanitized


def convert_pdf_to_markdown(pdf_path: Path) -> str:
    """Convert a PDF file to Markdown format."""
    if PdfReader is None:
        raise RuntimeError(
            "pypdf is required. Please install dependencies from requirements.txt"
        )

    reader = PdfReader(str(pdf_path))
    page_texts = []
    for page in reader.pages:
        # pypdf returns None when a page has no extractable text
        content = page.extract_text() or ""
        page_texts.append(content)
    text = "\n\n".join(page_texts)

    # Normalize line endings and whitespace
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Basic paragraph reconstruction: collapse multiple spaces, keep blank lines
    lines = [ln.rstrip() for ln in text.split("\n")]

    # Merge hyphenated line breaks (e.g., "compli-\nance" -> "compliance")
    merged_lines = []
    for i, ln in enumerate(lines):
        if ln.endswith("-") and i + 1 < len(lines):
            next_ln = lines[i + 1].lstrip()
            merged_lines.append(ln[:-1] + next_ln)
            lines[i + 1] = ""
        else:
            merged_lines.append(ln)

    # Collapse multiple blank lines to at most one
    paragraphs = []
    blank = False
    for ln in merged_lines:
        if ln.strip() == "":
            if not blank:
                paragraphs.append("")
            blank = True
        else:
            paragraphs.append(ln)
            blank = False

    body = "\n".join(paragraphs).strip()

    # Build markdown with a top-level title
    title = sanitize_stem(pdf_path.stem)
    md = f"# {title}\n\n" + body + "\n"
    return md


def convert_docx_to_markdown(input_path: Path) -> str:
    """Convert a DOCX file to Markdown format."""
    if mammoth is None:
        raise RuntimeError("mammoth is required. Please install dependencies from requirements.txt")
    if html_to_md is None:
        raise RuntimeError("markdownify is required. Please install dependencies from requirements.txt")

    with input_path.open("rb") as f:
        result = mammoth.convert_to_html(f)
    html = result.value or ""

    # Convert HTML to Markdown
    markdown = html_to_md(html, heading_style="ATX")
    if not markdown.endswith("\n"):
        markdown += "\n"
    return markdown


def convert_txt_to_markdown(input_path: Path) -> str:
    """Convert a text file to Markdown format."""
    content = input_path.read_text(encoding="utf-8", errors="ignore")
    
    # Build markdown with a top-level title
    title = sanitize_stem(input_path.stem)
    md = f"# {title}\n\n{content}\n"
    return md


def file_to_markdown(file_path: str | Path, output_path: Optional[str | Path] = None) -> str:
    """
    Convert a file (PDF, DOCX, or TXT) to Markdown format.
    If the input is already Markdown (.md), pass it through unchanged.
    
    Args:
        file_path: Path to the input file (PDF, DOCX, TXT, or MD)
        output_path: Optional path for the output markdown file.
                    If not provided, the markdown file will be saved
                    next to the input file with a .md extension.
    
    Returns:
        Path to the generated markdown file as a string.
    
    Raises:
        FileNotFoundError: If the input file does not exist.
        ValueError: If the file type is not supported.
        RuntimeError: If required dependencies are missing.
    """
    input_path = Path(file_path).resolve()
    
    if not input_path.exists():
        raise FileNotFoundError(f"File not found: {input_path}")
    
    if not input_path.is_file():
        raise ValueError(f"Path is not a file: {input_path}")
    
    # Determine file type from extension
    suffix_lower = input_path.suffix.lower()
    
    # Handle markdown passthrough early
    if suffix_lower == ".md":
        # If no output_path is given, just return the original path
        if output_path is None:
            return str(input_path)
        # If an output_path is provided, copy content as-is
        output = Path(output_path).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        content = input_path.read_text(encoding="utf-8")
        output.write_text(content, encoding="utf-8")
        return str(output)

    # Convert based on file type
    if suffix_lower == ".pdf":
        md_content = convert_pdf_to_markdown(input_path)
    elif suffix_lower in [".docx", ".doc"]:
        md_content = convert_docx_to_markdown(input_path)
    elif suffix_lower == ".txt":
        md_content = convert_txt_to_markdown(input_path)
    else:
        raise ValueError(
            f"Unsupported file type: {suffix_lower}. "
            f"Supported types: .pdf, .docx, .doc, .txt, .md"
        )

    # Determine output path
    if output_path is not None:
        output = Path(output_path).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
    else:
        # Save next to the input file with .md extension
        output = input_path.with_suffix(".md")

    # Write the markdown file
    output.write_text(md_content, encoding="utf-8")

    return str(output)


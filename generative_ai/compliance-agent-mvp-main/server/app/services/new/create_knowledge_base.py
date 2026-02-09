import argparse
import re
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF  # type: ignore
except Exception:  # pragma: no cover
    fitz = None

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover
    PdfReader = None


def sanitize_stem(name: str) -> str:
    sanitized = re.sub(r"\s+", " ", name).strip()
    sanitized = sanitized.replace("/", "-")
    return sanitized


def guess_workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


def convert_pdf_to_markdown(pdf_path: Path) -> str:
    text = ""

    # Prefer PyMuPDF if available; it's faster and preserves layout better
    pymupdf_error: Exception | None = None
    if fitz is not None:
        try:
            with fitz.open(str(pdf_path)) as doc:
                page_texts = []
                for page in doc:
                    # "text" preserves a reasonable flow; "blocks" could be used for more structure
                    content = page.get_text("text") or ""
                    page_texts.append(content)
                text = "\n\n".join(page_texts)
        except Exception as e:  # pragma: no cover
            pymupdf_error = e

    # Fallback to pypdf if PyMuPDF is unavailable or failed
    if not text:
        if PdfReader is None:
            # If PyMuPDF failed and pypdf isn't available, raise the original error if present
            if pymupdf_error is not None:
                raise RuntimeError(
                    f"Failed to extract with PyMuPDF and pypdf not installed: {pymupdf_error}"
                )
            raise RuntimeError(
                "pypdf is required as a fallback. Please install dependencies from requirements.txt"
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


def convert_folder(input_dir: Path, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = [p for p in sorted(input_dir.glob("*.pdf")) if p.is_file()]
    if not pdf_files:
        print(f"No PDF files found in: {input_dir}")
        return 0

    successes = 0
    for pdf_path in pdf_files:
        try:
            md_content = convert_pdf_to_markdown(pdf_path)
            out_name = sanitize_stem(pdf_path.stem) + ".md"
            out_path = output_dir / out_name
            out_path.write_text(md_content, encoding="utf-8")
            print(f"Converted: {pdf_path.name} -> {out_path.relative_to(output_dir.parent)}")
            successes += 1
        except Exception as e:
            print(f"Failed to convert {pdf_path.name}: {e}", file=sys.stderr)

    return successes


def parse_args() -> argparse.Namespace:
    workspace = guess_workspace_root()
    default_input = workspace / "regulations_pdf"
    default_output = workspace / "knowledge-base"

    parser = argparse.ArgumentParser(
        description="Convert all PDFs in a folder to Markdown files."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=default_input,
        help=f"Input folder containing PDFs (default: {default_input})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output,
        help=f"Output folder for Markdown files (default: {default_output})",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    input_dir = args.input.resolve()
    output_dir = args.output.resolve()

    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Input directory does not exist or is not a directory: {input_dir}", file=sys.stderr)
        sys.exit(1)

    num = convert_folder(input_dir, output_dir)
    print(f"Done. Converted {num} file(s). Output: {output_dir}")


if __name__ == "__main__":
    main()



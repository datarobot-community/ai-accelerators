import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from server.services.new.json_schema import get_json_schema

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None  # type: ignore

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

try:
    import datarobot as dr
except Exception:  # pragma: no cover
    dr = None  # type: ignore

try:
    # For converting non-Markdown inputs to Markdown
    from server.services.new.file_to_markdown import file_to_markdown
except Exception:  # pragma: no cover
    file_to_markdown = None  # type: ignore


def read_markdown_files(directory: Path) -> List[Tuple[str, str]]:
    files = []
    for p in sorted(directory.glob("*.md")):
        if p.is_file():
            try:
                files.append((p.name, p.read_text(encoding="utf-8")))
            except Exception:
                continue
    return files


def truncate_corpus(pairs: List[Tuple[str, str]], max_chars: int) -> List[Tuple[str, str]]:
    total = 0
    kept: List[Tuple[str, str]] = []
    for name, content in pairs:
        if total >= max_chars:
            break
        budget = max_chars - total
        snippet = content[:budget]
        kept.append((name, snippet))
        total += len(snippet)
    return kept


 


def _extract_json_from_text(text: str) -> Optional[object]:
    """Try to extract a JSON object or array from arbitrary text.

    Looks for the first plausible JSON block (object or array) and attempts to parse it.
    Returns the parsed JSON (dict or list) or None if not found/parsable.
    """
    text_stripped = text.strip()
    # Fast paths: starts with fenced code
    if text_stripped.startswith("```json"):
        candidate = text_stripped[7:]
        if candidate.endswith("````"):
            candidate = candidate[:-4]
        if candidate.endswith("```"):
            candidate = candidate[:-3]
        try:
            return json.loads(candidate.strip())
        except Exception:
            pass
    elif text_stripped.startswith("```"):
        candidate = text_stripped[3:]
        if candidate.endswith("````"):
            candidate = candidate[:-4]
        if candidate.endswith("```"):
            candidate = candidate[:-3]
        try:
            return json.loads(candidate.strip())
        except Exception:
            pass

    # General search: find the first '{' or '[' and parse until matching end
    # We do a simple bracket counter to find a balanced JSON candidate
    for opener, closer in [("{", "}"), ("[", "]")]:
        start = text.find(opener)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            ch = text[i]
            if ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    candidate = text[start : i + 1]
                    try:
                        return json.loads(candidate)
                    except Exception:
                        break
    return None


def build_prompt(database_docs: List[Tuple[str, str]], input_sample: str) -> List[dict]:
    system_msg = (
        "You are a meticulous compliance analyst. Given telecom/domain policy markdown regulations "
        "and a product compliance input sample, identify non-compliant, missing, or misaligned "
        "claims. Output a JSON object with a 'compliance_report' array containing objects with the following keys: "
        "claim, regulation, clause_section, requirement, compliance_status, non_compliance_description, recommendation. "
        "CRITICAL: The 'requirement' field must contain the EXACT wording of the specific clause or section from the regulation, "
        "copied verbatim without any interpretation, rewording, or paraphrasing. Do NOT summarize or interpret the requirement. "
        "The compliance_status field should be set to 'Non-Compliant' for all non-compliant claims. "
        "Keep entries concise and only include actual non-compliance issues."
    )

    regs_blocks = []
    for name, content in database_docs:
        regs_blocks.append(f"### Regulation: {name}\n\n{content}\n")
    regs_str = "\n\n---\n\n".join(regs_blocks)

    user_msg = (
        "Evaluate the input against the regulations. Return a JSON object with a single key 'compliance_report', "
        "whose value is an array of non-compliance issues only. Do not include any other keys or text.\n\n"
        "Regulations (markdown corpus):\n\n"
        f"{regs_str}\n\n"
        "Input sample (markdown):\n\n"
        f"{input_sample}\n\n"
    )

    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]


def generate_compliance_report(
    input_markdown_path: Path,
    database_dir: Path,
    model: Optional[str] = None,
    max_corpus_chars: int = 300_000,
) -> List[dict]:
    """
    Generate a compliance report by evaluating a given input Markdown file against a directory of regulation Markdown documents.

    Args:
        input_markdown_path (Path): Path to the input markdown file (product compliance sample).
        database_dir (Path): Path to the directory containing regulation markdown files.
        model (Optional[str], optional): The LLM model name to use for evaluation. Priority: argument > .env CHAT_COMPLETIONS_MODEL > default ("gpt-4o-mini").
        max_corpus_chars (int, optional): Maximum number of characters from the regulation corpus to include in the prompt (default: 300,000).

    Returns:
        List[dict]: A list of compliance issues (in JSON serializable dicts), where each dict contains:
            - claim: The non-compliant or questionable claim from the input sample.
            - regulation: The name/title of the regulation document.
            - clause_section: The section or clause containing the requirement.
            - requirement: The EXACT wording of the relevant regulation requirement.
            - compliance_status: Will be "Non-Compliant" for each entry.
            - non_compliance_description: Explanation of why the claim is non-compliant.
            - recommendation: Recommendation(s) to remediate the issue.

    Raises:
        FileNotFoundError: If input_markdown_path or drconfig.yaml does not exist.
        NotADirectoryError: If database_dir is missing or not a directory.
        RuntimeError: If dependencies (openai, datarobot, or markdown regulation files) are missing.

    Description:
        This function loads a sample product compliance markdown file, collects all markdown regulation documents
        from the supplied database directory (truncating as needed), constructs an LLM prompt, and uses a DataRobot
        LLM Gateway-connected OpenAI-compatible API to generate a compliance report. The report only lists actual
        non-compliance issues according to the specified schema.
    """

    if OpenAI is None:
        raise RuntimeError("openai package is required. Please install dependencies from requirements.txt")
    if dr is None:
        raise RuntimeError("datarobot package is required. Please install dependencies from requirements.txt")

    # Load .env for optional CHAT_COMPLETIONS_MODEL override
    if load_dotenv is not None:
        repo_root = Path(__file__).resolve().parents[1]
        env_path = repo_root / ".env"
        if env_path.exists():
            load_dotenv(env_path)

    if not input_markdown_path.exists():
        raise FileNotFoundError(f"Input markdown not found: {input_markdown_path}")

    if not database_dir.exists() or not database_dir.is_dir():
        raise NotADirectoryError(f"Database directory not found: {database_dir}")

    # Normalize/convert input file to Markdown if needed
    source_path = input_markdown_path
    suffix_lower = source_path.suffix.lower()
    if suffix_lower != ".md":
        if file_to_markdown is None:
            raise RuntimeError("file_to_markdown dependency is required for non-Markdown inputs. Please install dependencies from requirements.txt")
        # Convert supported formats; let file_to_markdown raise with its own error message for unsupported types
        converted_path_str = file_to_markdown(source_path)
        input_markdown_path = Path(converted_path_str)

    input_md = input_markdown_path.read_text(encoding="utf-8")
    regs = read_markdown_files(database_dir)
    if not regs:
        raise RuntimeError(f"No markdown files found in database directory: {database_dir}")

    regs_trunc = truncate_corpus(regs, max_corpus_chars)
    messages = build_prompt(regs_trunc, input_md)
    json_schema = get_json_schema()

    # Initialize DataRobot client via drconfig.yaml at repo root
    repo_root = Path(__file__).resolve().parents[1]
    drconfig_path = repo_root / "drconfig.yaml"
    if not drconfig_path.exists():
        raise FileNotFoundError(f"drconfig.yaml not found at {drconfig_path}")

    dr_client = dr.Client(config_path=str(drconfig_path))
    dr_api_token = dr_client.token
    llm_gateway_base_url = f"{dr_client.endpoint}/genai/llmgw"

    # Resolve model: CLI arg > CHAT_COMPLETIONS_MODEL from .env > default
    if model is None:
        model = os.environ.get("CHAT_COMPLETIONS_MODEL", "gpt-4o-mini")

    # Use OpenAI-compatible client pointed at DR LLM Gateway
    client = OpenAI(base_url=llm_gateway_base_url, api_key=dr_api_token)
    print(f"Using model: {model}")
    
    # Try structured output with JSON schema - handle different API formats
    response = None
    format_attempts = [
        {"type": "json_object", "json_schema": json_schema},   # Meta Llama format
        {"type": "json_object", "schema": json_schema},        # Alternative format
        {"type": "json_object"},                               # Basic JSON mode
    ]
    
    for attempt, format_param in enumerate(format_attempts):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.1,
                response_format=format_param
            )
            if attempt > 0:
                print(f"Info: Using response_format attempt {attempt + 1}", file=sys.stderr)
            break
        except Exception as e:
            if attempt < len(format_attempts) - 1:
                continue  # Try next format
            else:
                raise RuntimeError(f"Failed to create chat completion with all response_format attempts. Last error: {e}")
    
    if response is None:
        raise RuntimeError("Failed to get response from API")

    # Parse the JSON response
    content = response.choices[0].message.content if response.choices else ""

    def _normalize_and_extract(content_text: str) -> List[dict]:
        if not content_text:
            return []
        try:
            content_clean = content_text.strip()
            if content_clean.startswith("```json"):
                content_clean = content_clean[7:]
            elif content_clean.startswith("```"):
                content_clean = content_clean[3:]
            if content_clean.endswith("```"):
                content_clean = content_clean[:-3]
            content_clean = content_clean.strip()

            # Try direct parse first
            try:
                parsed_local = json.loads(content_clean)
            except json.JSONDecodeError:
                # Try extracting JSON anywhere in the text
                extracted = _extract_json_from_text(content_text)
                if extracted is None:
                    return []
                parsed_local = extracted

            if isinstance(parsed_local, list):
                return parsed_local
            if isinstance(parsed_local, dict):
                if "compliance_report" in parsed_local and isinstance(parsed_local["compliance_report"], list):
                    return parsed_local["compliance_report"]
                for value in parsed_local.values():
                    if isinstance(value, list):
                        return value
            return []
        except Exception:
            return []

    report_items = _normalize_and_extract(content)

    # Fallback: if we got nothing, retry without response_format (some models ignore or blank content)
    if not report_items:
        try:
            fallback_response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.0,
            )
            fallback_content = fallback_response.choices[0].message.content if fallback_response.choices else ""
            report_items = _normalize_and_extract(fallback_content)
        except Exception as e:
            print(f"Fallback request failed: {e}", file=sys.stderr)

    return report_items


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    default_db = repo_root / "knowledge-base"
    default_input = repo_root / "product complience agent - input sample .md"

    parser = argparse.ArgumentParser(
        description="Evaluate product compliance against a Markdown regulations database using an LLM."
    )
    parser.add_argument("--database", type=Path, default=default_db, help=f"Path to knowledge base directory (default: {default_db})")
    parser.add_argument("--input", type=Path, default=default_input, help=f"Path to input Markdown sample (default: {default_input})")
    parser.add_argument("--model", type=str, default=None, help="Model to use (default: from CHAT_COMPLETIONS_MODEL in .env, or gpt-4o-mini)")
    parser.add_argument("--output", type=Path, default=None, help="Optional path to write the compliance report as JSON")
    parser.add_argument("--max-corpus-chars", type=int, default=300_000, help="Max total characters from regulations corpus")

    args = parser.parse_args()

    try:
        report_data = generate_compliance_report(
            input_markdown_path=args.input.resolve(),
            database_dir=args.database.resolve(),
            model=args.model,
            max_corpus_chars=args.max_corpus_chars,
        )
    except Exception as e:
        print(f"Compliance evaluation failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Format as JSON string with proper indentation
    json_output = json.dumps(report_data, indent=2, ensure_ascii=False)

    if args.output:
        out_path = args.output.resolve()
        out_path.write_text(json_output, encoding="utf-8")
        print(f"Compliance report written to: {out_path}")
    else:
        print(json_output)


if __name__ == "__main__":
    main()



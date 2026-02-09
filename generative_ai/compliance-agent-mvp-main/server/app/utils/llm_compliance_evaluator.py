"""
Utility for evaluating compliance using LLM.
Based on server/services/new/evaluate_compliance.py
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Optional, Dict

from app.utils.json_schema import sanitize_column_name, get_default_columns


def _get_reasoning_effort() -> Optional[str]:
    """
    Get reasoning effort setting from environment.
    Only applies when MODE=direct-llm.
    
    Returns:
        Reasoning effort value ('low', 'medium', 'high') or None if not applicable.
    """
    mode = os.environ.get("MODE", "dr-gateway").lower()
    
    # Only apply reasoning_effort for direct-llm mode
    # LLM gateways typically don't support this parameter
    if mode != "direct-llm":
        return None
    
    reasoning_effort = os.environ.get("REASONING_EFFORT", "").lower()
    
    # Validate the value
    valid_values = {"low", "medium", "high"}
    if reasoning_effort in valid_values:
        return reasoning_effort
    
    return None


def read_markdown_files(directory: Path) -> List[Tuple[str, str]]:
    """
    Read all markdown files from a directory.
    
    Args:
        directory: Path to directory containing markdown files
    
    Returns:
        List of tuples (filename, content)
    """
    files = []
    for p in sorted(directory.glob("*.md")):
        if p.is_file():
            try:
                files.append((p.name, p.read_text(encoding="utf-8")))
            except Exception:
                continue
    return files


def _build_column_keys_description(columns: List[Dict]) -> str:
    """
    Build a string listing column keys for the prompt.
    
    Args:
        columns: List of column dicts with 'name' and 'description'
        
    Returns:
        Comma-separated list of sanitized column names
    """
    sanitized_names = [sanitize_column_name(col.get("name", "")) for col in columns]
    return ", ".join(sanitized_names)


def _build_column_descriptions(columns: List[Dict]) -> str:
    """
    Build detailed column descriptions for the prompt.
    
    Args:
        columns: List of column dicts with 'name' and 'description'
        
    Returns:
        Formatted string with column descriptions
    """
    lines = []
    for col in columns:
        name = sanitize_column_name(col.get("name", ""))
        desc = col.get("description", "")
        if name and desc:
            lines.append(f"- '{name}': {desc}")
    return "\n".join(lines)


# Fixed system prompt prefix that cannot be modified by users
FIXED_SYSTEM_PREFIX = "You are a meticulous compliance analyst working at du (ETIC)."

# Default system prompt - comprehensive and self-contained
DEFAULT_SYSTEM_PROMPT = """Given a telecom/domain policy regulation and a product compliance input sample, conduct a thorough compliance analysis.

NORMATIVE LANGUAGE INTERPRETATION:
- Treat MUST / SHALL / REQUIRED / MUST NOT / SHALL NOT as mandatory requirements.
- Treat SHOULD / RECOMMENDED / MAY as non-mandatory unless the regulation explicitly states otherwise.
- Do NOT create findings solely from non-mandatory language.

ANALYSIS METHODOLOGY:
1. Carefully read and understand all mandatory requirements, prohibitions, and conditions in the regulation. Focus on clauses using mandatory language (must, shall, required).
2. Systematically examine the input sample to identify all claims, statements, and documented practices.
3. Map each regulation requirement to corresponding evidence (or lack thereof) in the input.
4. APPLICABILITY CHECK: Before flagging any issue, verify the regulation clause is applicable to the product/service type described in the input. If the input clearly describes a specific product type (e.g., 'Fixed Line', 'Consumer CVP') and the regulation clause is specific to another type (e.g., 'Mobile Pre-paid', 'Domain Registrar'), do NOT flag it as an issue.
5. Identify three types of compliance issues:
   - NON-COMPLIANCE: Input explicitly contradicts or violates a mandatory regulation requirement.
   - MISSING REQUIREMENTS: Regulation mandates something (using must/shall/required) that is not addressed in the input.
   - MISALIGNMENT: Input partially addresses a requirement but falls short of full compliance.
6. Only flag issues where there is clear evidence of a gap between the regulation and the input.
7. Avoid false positives - do not infer requirements that are not explicitly stated in the regulation.
8. For each issue, provide specific evidence quotes from both the regulation and the input.

HANDLING PARTIAL COMPLIANCE (MISALIGNMENT):
- When a document addresses a requirement incompletely or inadequately, clearly state:
  (1) What IS present in the input
  (2) What is MISSING or INADEQUATE
  (3) What needs to be ADDED or CHANGED
- For partially met requirements, quote the existing content, then explain the specific gaps.

HANDLING IMPLEMENTATION-DEPENDENT REQUIREMENTS:
- If the regulation requires a practice/process and the input describes a process that COULD satisfy it if implemented correctly, note this as 'Requires verification' and set criticality to Medium.
- Flag the need for validation/evidence of actual implementation beyond documentation.
- If the input is silent or vague on a mandatory requirement, flag as MISSING REQUIREMENT.

OUTPUT FORMAT:
Return a JSON object with a single key 'compliance_report', whose value is an array of non-compliance issues only.

QUALITY STANDARDS:
- Keep entries concise but complete - include all necessary information for understanding and addressing the issue.
- Only include actual non-compliance issues with clear evidence - avoid speculative or ambiguous findings.
- Ensure each entry is specific and actionable - vague or generic issues are not helpful.
- Provide precise section/clause references (e.g., 'Section 3.2.1', 'Clause 5(a)', 'Article 7.3').
- Cross-reference related clauses when an issue involves multiple regulation sections.
- Prioritize issues by severity - list Critical issues first, then Medium, then Low.
- If the input fully complies with a requirement, do not include it in the report.

DO NOT FLAG THE FOLLOWING:
- Requirements using 'may' or 'should' (only flag 'must', 'shall', 'required') unless explicitly stated as mandatory.
- Requirements that only apply to specific entity/product types not matching the input (e.g., domain registrars when evaluating a consumer CVP, mobile pre-paid when evaluating fixed line).
- General best practices not explicitly mandated in this specific regulation.
- Requirements already adequately addressed in the input, even if using different terminology.
- Procedural details that are internal to the regulator, not obligations on the licensee.
- Internal operational processes that wouldn't appear in customer-facing documents.
- Requirements from different regulations not provided in the context.

FALSE POSITIVE EXAMPLES TO AVOID:
- Flagging a consumer document for not mentioning internal operational processes.
- Citing requirements from regulations not provided in the evaluation context.
- Claiming 'missing' when the input addresses the requirement in a different section or with different wording.
- Flagging advisory ('should') language as if it were mandatory ('must').
- Flagging requirements specific to one product/service type when evaluating a different type."""

# Default user prompt - simple and minimal
DEFAULT_USER_PROMPT = "Conduct a comprehensive compliance evaluation based on the provided regulation and input sample."


def build_compliance_prompt(
    regulation_name: str, 
    regulation_content: str, 
    input_sample: str,
    custom_columns: Optional[List[Dict]] = None,
    custom_system_prompt: Optional[str] = None,
    custom_user_prompt: Optional[str] = None
) -> List[dict]:
    """
    Build the prompt messages for LLM compliance evaluation.
    
    Args:
        regulation_name: Name of the regulation file
        regulation_content: Content of the regulation
        input_sample: Input markdown content to evaluate
        custom_columns: Optional list of custom column definitions. If None, uses defaults.
        custom_system_prompt: Optional custom system prompt (editable portion only).
                              Will be prefixed with FIXED_SYSTEM_PREFIX.
        custom_user_prompt: Optional custom user prompt. Will be appended with
                            regulation name, content, and input sample.
    
    Returns:
        List of message dicts for LLM API
    """
    # Use custom columns if provided, otherwise use defaults from JSON schema
    columns = custom_columns if custom_columns else get_default_columns()
    
    # Build column keys list and descriptions
    column_keys = _build_column_keys_description(columns)
    column_descriptions = _build_column_descriptions(columns)
    
    # Format column definitions section
    column_definitions_section = (
        f"Each object in the array must have the following keys: {column_keys}.\n\n"
        f"Column definitions:\n{column_descriptions}"
    )
    
    # Use custom system prompt if provided, otherwise use default
    editable_system_prompt = custom_system_prompt if custom_system_prompt else DEFAULT_SYSTEM_PROMPT
    
    # Build complete system message: Fixed prefix + system prompt + column definitions (auto-appended)
    system_msg = f"{FIXED_SYSTEM_PREFIX} {editable_system_prompt}\n\n{column_definitions_section}"

    # Use custom user prompt if provided, otherwise use default
    editable_user_prompt = custom_user_prompt if custom_user_prompt else DEFAULT_USER_PROMPT
    
    # Build complete user message: editable portion + regulation and input content
    user_msg = (
        f"{editable_user_prompt}\n\n"
        f"Regulation: {regulation_name}\n\n"
        f"{regulation_content}\n\n"
        "---\n\n"
        "Input sample (markdown):\n\n"
        f"{input_sample}\n\n"
    )

    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]


def evaluate_compliance(client, model: str, messages: List[dict], json_schema: dict) -> List[dict]:
    """
    Evaluate compliance using LLM with structured output.
    
    Args:
        client: OpenAI-compatible client
        model: Model name to use
        messages: List of message dicts for the LLM
        json_schema: JSON schema for structured output
    
    Returns:
        List of compliance issue dicts
    """
    # Try structured output with JSON schema - handle different API formats
    response = None
    format_attempts = [
        {"type": "json_object", "schema": json_schema},             # Alternative format
        {"type": "json_schema", "json_schema": {"name": "compliance_report", "schema": json_schema}},
        {"type": "json_schema", "json_schema": {"schema": json_schema}},    # OpenAI-style JSON Schema format (strict)
        {"type": "json_object", "json_schema": json_schema},        # Meta Llama format
        {"type": "json_object"},                                    # Basic JSON mode
    ]
    
    # Get reasoning effort from environment (only applies in direct-llm mode)
    reasoning_effort = _get_reasoning_effort()
    
    for attempt, format_param in enumerate(format_attempts):
        try:
            # Build kwargs for the API call
            create_kwargs = {
                "model": model,
                "messages": messages,
                "temperature": 0.1,
                "response_format": format_param,
            }
            
            # Add reasoning_effort if configured (direct-llm mode only)
            if reasoning_effort:
                create_kwargs["reasoning_effort"] = reasoning_effort
            
            response = client.chat.completions.create(**create_kwargs)
            if attempt > 0:
                print(f"Info: Compliance Evaluator - Using response_format attempt {attempt + 1}", file=sys.stderr)
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
        """Normalize content and extract compliance report from JSON."""
        if not content_text or not content_text.strip():
            return []
        
        try:
            # Remove markdown code blocks using regex (handles BOM, whitespace, case variations)
            # Matches patterns like: \ufeff```json, ```json, ```JSON, ```, with optional whitespace/newlines
            # The pattern handles:
            # - UTF-8 BOM (\ufeff) at the start (optional)
            # - Optional leading whitespace/newlines
            # - Code block markers (```json or ```) with case-insensitive matching
            # - Optional trailing whitespace/newlines
            # - Closing ``` markers
            # Include BOM character directly in the pattern (it's not a regex metacharacter)
            bom_char = '\ufeff'
            content_clean = re.sub(
                rf'^\s*{bom_char}?\s*```\s*(?:json\s*)?',
                '',
                content_text,
                flags=re.IGNORECASE | re.DOTALL
            )
            content_clean = re.sub(
                r'```\s*$',
                '',
                content_clean,
                flags=re.DOTALL
            )
            content_clean = content_clean.strip()
            
            if not content_clean:
                return []
            
            # Try to parse JSON
            parsed = json.loads(content_clean)
            
            # Extract compliance_report array
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict):
                if "compliance_report" in parsed and isinstance(parsed["compliance_report"], list):
                    return parsed["compliance_report"]
                # Try to find any list value
                for value in parsed.values():
                    if isinstance(value, list):
                        return value
            return []
        except json.JSONDecodeError:
            return []
        except Exception:
            return []
    
    # Try to parse the initial response
    report_items = _normalize_and_extract(content)
    
    # Fallback: retry without response_format if initial parse failed or returned empty
    if not report_items:
        try:
            fallback_kwargs = {
                "model": model,
                "messages": messages,
                "temperature": 0.1,
            }
            
            # Add reasoning_effort if configured (direct-llm mode only)
            if reasoning_effort:
                fallback_kwargs["reasoning_effort"] = reasoning_effort
            
            fallback_response = client.chat.completions.create(**fallback_kwargs)
            fallback_content = fallback_response.choices[0].message.content if fallback_response.choices else ""
            report_items = _normalize_and_extract(fallback_content)
        except Exception as e:
            print(f"Fallback request failed: {e}", file=sys.stderr)
            return []
    
    return report_items

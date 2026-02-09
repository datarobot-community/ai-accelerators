"""JSON schema for compliance report matching frontend expectations."""
import json
import re
import html
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# Load default schema from JSON file
_DEFAULT_SCHEMA_PATH = Path(__file__).parent / "default_compliance_report.json"


def _load_default_schema() -> Dict:
    """Load the default JSON schema from file."""
    with open(_DEFAULT_SCHEMA_PATH, 'r') as f:
        return json.load(f)


def sanitize_column_name(name: str) -> str:
    """
    Sanitize a column name for use in JSON schema.
    
    Rules:
    - Trim whitespace
    - Replace spaces with underscores
    - Remove special characters (keep alphanumeric, underscores, hyphens)
    - Convert to lowercase
    - Must start with letter or underscore
    
    Args:
        name: Raw column name from user input
        
    Returns:
        Sanitized column name safe for JSON schema
    """
    if not name:
        return ""
    
    # Trim whitespace
    sanitized = name.strip()
    
    # Replace spaces with underscores
    sanitized = sanitized.replace(" ", "_")
    
    # Remove special characters (keep alphanumeric, underscores, hyphens)
    sanitized = re.sub(r'[^a-zA-Z0-9_\-]', '', sanitized)
    
    # Convert to lowercase
    sanitized = sanitized.lower()
    
    # Ensure it starts with letter or underscore
    if sanitized and not re.match(r'^[a-zA-Z_]', sanitized):
        sanitized = '_' + sanitized
    
    return sanitized


def sanitize_description(description: str) -> str:
    """
    Sanitize a column description.
    
    Rules:
    - Trim whitespace
    - Escape HTML entities
    - Remove control characters
    - Limit length to 1000 chars
    
    Args:
        description: Raw description from user input
        
    Returns:
        Sanitized description
    """
    if not description:
        return ""
    
    # Trim whitespace
    sanitized = description.strip()
    
    # Escape HTML entities to prevent injection
    sanitized = html.escape(sanitized)
    
    # Remove control characters (keep printable chars and newlines)
    sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', sanitized)
    
    # Limit length
    if len(sanitized) > 1000:
        sanitized = sanitized[:1000]
    
    return sanitized


def validate_column_name(name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a column name before sanitization.
    
    Validation rules (moderate):
    - Allow letters, numbers, spaces, hyphens, and underscores
    - Length: 1-100 chars
    
    Args:
        name: Raw column name from user input
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name or not name.strip():
        return False, "Column name cannot be empty"
    
    trimmed = name.strip()
    
    if len(trimmed) < 1:
        return False, "Column name must be at least 1 character"
    
    if len(trimmed) > 100:
        return False, "Column name must be at most 100 characters"
    
    # Allow letters, numbers, spaces, hyphens, and underscores
    if not re.match(r'^[a-zA-Z0-9\s\-_]+$', trimmed):
        return False, "Column name can only contain letters, numbers, spaces, hyphens, and underscores"
    
    return True, None


def validate_description(description: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a column description.
    
    Validation rules:
    - Length: 1-500 chars
    
    Args:
        description: Raw description from user input
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not description or not description.strip():
        return False, "Description cannot be empty"
    
    trimmed = description.strip()
    
    if len(trimmed) < 1:
        return False, "Description must be at least 1 character"
    
    if len(trimmed) > 1000:
        return False, "Description must be at most 1000 characters"
    
    return True, None


def get_default_columns() -> List[Dict]:
    """
    Get the list of default columns from the schema.
    
    Returns:
        List of column dicts with 'name', 'description', 'isDefault', 'type', and optionally 'enum' keys
    """
    schema = _load_default_schema()
    properties = schema.get("properties", {}).get("compliance_report", {}).get("items", {}).get("properties", {})
    
    columns = []
    for name, prop in properties.items():
        column = {
            "name": name,
            "description": prop.get("description", ""),
            "isDefault": True,
            "type": prop.get("type", "string")
        }
        # Include enum if present (e.g., for recommended_criticality)
        if "enum" in prop:
            column["enum"] = prop["enum"]
        columns.append(column)
    
    return columns


def build_dynamic_schema(user_columns: Optional[List[Dict]] = None) -> Dict:
    """
    Build a dynamic JSON schema based on user-defined columns.
    
    User columns can override, remove, or add to default columns.
    
    Args:
        user_columns: List of column dicts with 'name' and 'description' keys.
                     If None, returns the default schema.
                     
    Returns:
        Complete JSON schema for LLM structured output
        
    Raises:
        ValueError: If validation fails or duplicate column names detected
    """
    if not user_columns:
        return _load_default_schema()
    
    # Track sanitized names to detect duplicates
    seen_names = set()
    validated_columns = []
    
    for col in user_columns:
        raw_name = col.get("name", "")
        raw_description = col.get("description", "")
        
        # Validate name
        is_valid, error = validate_column_name(raw_name)
        if not is_valid:
            raise ValueError(f"Invalid column name '{raw_name}': {error}")
        
        # Validate description
        is_valid, error = validate_description(raw_description)
        if not is_valid:
            raise ValueError(f"Invalid description for column '{raw_name}': {error}")
        
        # Sanitize
        sanitized_name = sanitize_column_name(raw_name)
        sanitized_description = sanitize_description(raw_description)
        
        # Check for duplicates after sanitization
        if sanitized_name in seen_names:
            raise ValueError(f"Duplicate column name after sanitization: '{raw_name}' -> '{sanitized_name}'")
        
        seen_names.add(sanitized_name)
        validated_columns.append({
            "name": sanitized_name,
            "description": sanitized_description,
            "type": col.get("type", "string"),
            "enum": col.get("enum")  # For fields like recommended_criticality
        })
    
    # Build schema properties
    properties = {}
    required = []
    
    for col in validated_columns:
        prop = {
            "type": col["type"],
            "description": col["description"]
        }
        if col.get("enum"):
            prop["enum"] = col["enum"]
        
        properties[col["name"]] = prop
        required.append(col["name"])
    
    # Construct final schema
    return {
        "type": "object",
        "properties": {
            "compliance_report": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                    "additionalProperties": False
                }
            }
        },
        "required": ["compliance_report"],
        "additionalProperties": False
    }


def get_compliance_json_schema(custom_columns: Optional[List[Dict]] = None) -> Dict:
    """
    Define JSON schema for compliance report output that matches frontend expectations.
    
    Args:
        custom_columns: Optional list of custom column definitions.
                       Each dict should have 'name' and 'description' keys.
                       If provided, these will be used instead of defaults.
    
    Returns:
        Dict: JSON schema for LLM structured output
    """
    if custom_columns is not None:
        return build_dynamic_schema(custom_columns)
    
    return _load_default_schema()

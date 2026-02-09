from typing import Dict, Any, Optional


class ComplianceIssue:
    """
    Represents a compliance issue found during verification.
    
    Supports both default fields and custom fields for dynamic column support.
    The class stores all fields as a dictionary to preserve custom columns
    from LLM responses.
    """
    
    # Default field names for backward compatibility
    DEFAULT_FIELDS = {
        'regulation_file_name',
        'regulation_file_url', 
        'regulation_clause_section',
        'regulation_clause_text',
        'cvp_evidence',
        'recommended_criticality',
        'explanation',
        'recommendation'
    }
    
    def __init__(self, **kwargs):
        """
        Initialize a ComplianceIssue with arbitrary fields.
        
        Args:
            **kwargs: All fields to store. Can include default fields
                     and any custom fields defined by the user.
        """
        self._data: Dict[str, Any] = kwargs
    
    def __getattr__(self, name: str) -> Any:
        """Allow attribute-style access to fields."""
        if name.startswith('_'):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        return self._data.get(name)
    
    def __setattr__(self, name: str, value: Any) -> None:
        """Allow attribute-style setting of fields."""
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            self._data[name] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a field value with optional default."""
        return self._data.get(key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary, preserving all fields including custom ones.
        
        Returns:
            Dict containing all fields (default and custom)
        """
        return dict(self._data)
    
    def __repr__(self) -> str:
        fields = ", ".join(f"{k}={v!r}" for k, v in self._data.items())
        return f"ComplianceIssue({fields})"

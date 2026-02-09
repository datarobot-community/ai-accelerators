from typing import Dict


def get_json_schema() -> Dict:
    """Define JSON schema for compliance report output."""
    return {
        "type": "object",
        "properties": {
            "compliance_report": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "claim": {
                            "type": "string",
                            "description": "The claim or statement from the input that needs compliance verification"
                        },
                        "regulation": {
                            "type": "string",
                            "description": "The relevant regulation document name"
                        },
                        "clause_section": {
                            "type": "string",
                            "description": "The specific clause or section number/name from the regulation"
                        },
                        "requirement": {
                            "type": "string",
                            "description": "The exact wording of the specific clause or section from the regulation, copied verbatim without interpretation or rewording"
                        },
                        "compliance_status": {
                            "type": "string",
                            "description": "The compliance status of the claim, should be 'Non-Compliant' for non-compliant claims"
                        },
                        "non_compliance_description": {
                            "type": "string",
                            "description": "Description of the non-compliance, missing, or misaligned aspects"
                        },
                        "recommendation": {
                            "type": "string",
                            "description": "Recommendations to address the non-compliance"
                        }
                    },
                    "required": [
                        "claim",
                        "regulation",
                        "clause_section",
                        "requirement",
                        "compliance_status",
                        "non_compliance_description",
                        "recommendation",
                    ],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["compliance_report"],
        "additionalProperties": False,
    }



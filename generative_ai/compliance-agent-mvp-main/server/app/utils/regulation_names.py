"""Mapping of regulation filenames to human-readable names."""

REGULATION_NAMES = {
    "AEDAPOL001v11CommonDefinitions.md": "Common Definitions Policy v1.1",
    "AEDAPOL009v10DomainNamePasswordPolicy.md": "Domain Name Password Policy v1.0",
    "AEDAPOL013v11ComplaintsHandlingPolicy.md": "Complaints Handling Policy v1.1",
    "AEDAPOL014av11UAEDomainNameDisputeResolutionPolicy.md": "UAE Domain Name Dispute Resolution Policy v1.1",
    "AEDAPOL015v11CodeofPractice.md": "Code of Practice v1.1",
    "CONSUMER PROTECTION REGULATIONS VERSION 20 ISSUED 2572023.md": "Consumer Protection Regulations v2.0",
    "Domain Name Eligibility Policy pdf.md": "Domain Name Eligibility Policy v1.0",
    "International Telecommunications Cable Regulations Annex B V10.md": "International Telecommunications Cable Regulations Annex B v1.0",
    "International Telecommunications Cable Regulations V10.md": "International Telecommunications Cable Regulations v1.0",
    "People of determination accessibility to telecommunication.md": "People of Determination Accessibility to Telecommunication v1.0",
    "Resolution No 11 of 2022 on International Telecom Cables Ar.md": "Resolution No 11 of 2022 on International Telecom Cables v1.0",
    "V06 The International Cable Regulations Annex A.md": "International Cable Regulations Annex A v1.0",
}


def get_regulation_display_name(filename: str) -> str:
    """
    Get the human-readable display name for a regulation file.
    
    Args:
        filename: The regulation filename (e.g., "AEDAPOL001v11CommonDefinitions.md")
    
    Returns:
        Human-readable name if mapping exists, otherwise returns the filename
    """
    return REGULATION_NAMES.get(filename, filename)

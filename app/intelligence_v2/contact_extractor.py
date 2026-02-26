
import re
from typing import Dict, Optional

# Kenyan specific phone patterns
PHONE_REGEX = r"(\+254|0)[7-9][0-9]{8}"
EMAIL_REGEX = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"

def extract_contact_info(text: str) -> Dict[str, Optional[str]]:
    """
    DUMB SCRAPER fallback: The intelligence layer extracts contact info
    from raw signal text.
    """
    contacts = {
        "phone": None,
        "whatsapp": None,
        "email": None
    }
    
    if not text:
        return contacts
        
    # 1. Phone Extraction
    phone_match = re.search(PHONE_REGEX, text)
    if phone_match:
        phone = phone_match.group(0)
        contacts["phone"] = phone
        # In Kenya, most mobile numbers are WhatsApp active
        contacts["whatsapp"] = phone 
        
    # 2. Email Extraction
    email_match = re.search(EMAIL_REGEX, text)
    if email_match:
        contacts["email"] = email_match.group(0)
        
    return contacts

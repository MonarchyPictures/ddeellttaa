
import logging

logger = logging.getLogger(__name__)

def enrich_lead_data(lead_data: dict) -> dict:
    """
    Enrich the lead object with additional metadata or calculated fields.
    This is a lightweight enricher that doesn't make external calls by default
    to avoid latency, but ensures all required fields are present.
    """
    # Ensure badge is present
    intent = lead_data.get("intent_score", 0)
    urgency = lead_data.get("urgency_score", 0)
    
    if intent > 0.8 and urgency > 0.7:
        lead_data["badge"] = "HOT"
    elif intent > 0.6:
        lead_data["badge"] = "WARM"
    else:
        lead_data["badge"] = "COLD"
        
    # Ensure contact extraction completeness
    if "phone" not in lead_data:
        lead_data["phone"] = ""
    if "email" not in lead_data:
        lead_data["email"] = ""
        
    logger.debug(f"Enriched lead: {lead_data.get('title')}")
    return lead_data

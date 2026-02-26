
import logging
from typing import List, Dict, Any
from app.intelligence_v2.geo_score import calculate_geo_score

logger = logging.getLogger("GeoBias")

def apply_geo_bias(leads: List[Dict[str, Any]], boost_amount: float = 0.05) -> List[Dict[str, Any]]:
    """
    Enhanced Geo Intelligence (v2 Wrapper):
    - Calculates granular geo_score (0.0 -> 1.0)
    - Maps to geo_region (Nairobi, Mombasa, etc.)
    - Assigns geo_strength (high, medium, low)
    - Boosts intent_score and affects ranking
    """
    if not leads:
        return []

    boosted_count = 0
    for lead in leads:
        # Use the new intelligence_v2 module
        lead = calculate_geo_score(lead)
        
        # Apply Boost to Intent Score (Affects Strict Filtering)
        if lead.get("geo_score", 0) > 0:
            old_score = lead.get("intent_score", 0)
            # Geo score contributes up to 0.30 boost to intent
            boost = lead["geo_score"] * 0.30
            new_score = round(min(1.0, old_score + boost), 3)
            lead["intent_score"] = new_score
            lead["intent_strength"] = new_score
            lead["geo_boosted"] = True
            lead["property_country"] = "Kenya"
            boosted_count += 1

    if boosted_count > 0:
        logger.info(f"GEO-INTELLIGENCE V2: Mapped {boosted_count} leads to Kenyan regions.")
        
    return leads

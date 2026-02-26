
from sqlalchemy.orm import Session
from ..db import models
from .outreach import generate_message
import logging

logger = logging.getLogger(__name__)

def buyer_match_score(lead, buyer): 
    """
    Calculates the match score between a lead and a buyer profile.
    
    Args:
        lead: An object or dict with .type (or ['product_category']), .price, .location, .urgency_score, .final_score
        buyer: An object or dict with .interest_type, .budget_min, .budget_max, .location, .urgency
    """
    score = 0.0 

    # Helper to get values from either object or dict
    def get_val(obj, key, default=None):
        if hasattr(obj, key):
            return getattr(obj, key)
        if isinstance(obj, dict):
            # Map common keys if they differ
            mapping = {
                'type': 'product_category',
                'price': 'price',
                'location': 'location_raw', # Fixed to use location_raw from lead data
                'urgency_score': 'intent_strength', # Mapping from lead data
                'final_score': 'intent_strength'    # Using intent_strength as final_score fallback
            }
            actual_key = mapping.get(key, key)
            return obj.get(actual_key, default)
        return default

    v_type = get_val(lead, 'type')
    b_type = get_val(buyer, 'interest_type') or get_val(buyer, 'vehicle_type') # Support legacy field
    if b_type and v_type and b_type.lower() in v_type.lower(): 
        score += 0.40 

    v_price = get_val(lead, 'price')
    b_min = get_val(buyer, 'budget_min')
    b_max = get_val(buyer, 'budget_max')
    if b_min and b_max and v_price: 
        if b_min <= v_price <= b_max: 
            score += 0.40 

    v_loc = get_val(lead, 'location')
    b_loc = get_val(buyer, 'location')
    if b_loc and v_loc and b_loc.lower() == v_loc.lower(): 
        score += 0.20 

    return round(min(score, 1.0), 2)

class MarketBrain:
    """
    Core Intelligence: Seller -> Buyer Matching Loop.
    Matches incoming seller leads with active buyer intents.
    """
    def __init__(self, db: Session):
        self.db = db

    def find_matches_for_lead(self, lead: models.Lead):
        """Find all active buyers who might be interested in this new lead."""
        active_intents = self.db.query(models.BuyerIntent).filter(
            models.BuyerIntent.is_active == 1
        ).all()
        
        matches = []
        for intent in active_intents:
            score = buyer_match_score(lead, intent)
            if score >= 0.4: # Lowered threshold for 'Immediate Match' promise
                matches.append({
                    "intent": intent,
                    "score": score
                })
        
        # Sort by best match
        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches

    def process_new_lead(self, lead: models.Lead):
        """
        Matching Loop:
        1. Find matching buyers
        2. Log the match
        3. (Optional) Trigger notifications
        """
        matches = self.find_matches_for_lead(lead)
        if matches:
            logger.info(f"MATCH FOUND: Lead {lead.id} ({lead.product_category}) matched with {len(matches)} buyers.")
            for m in matches:
                intent = m["intent"]
                score = m["score"]
                # In a real scenario, we might create a 'Match' record in the DB
                # or send a push notification/whatsapp to the user associated with the intent.
                logger.info(f"  - Match with Intent {intent.id} (User: {intent.user_id}) - Score: {score}")
        
        return matches

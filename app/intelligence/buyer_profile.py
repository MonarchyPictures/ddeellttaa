from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

from .matcher import buyer_match_score

@dataclass
class BuyerProfile:
    interest_type: Optional[str] = None
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    location: Optional[str] = None
    urgency: float = 0.5  # 0–1

    def calculate_match_score(self, lead: dict) -> float:
        """Helper to calculate match score for a lead."""
        return buyer_match_score(lead, self)

def _safe_int(val):
    try:
        return int(val) if val else None
    except (ValueError, TypeError):
        return None

def _recent_activity_score(request):
    """
    Calculates a quick urgency score based on session activity or headers.
    Implicit intent detection.
    """
    # Quick check for high-velocity headers if frontend provides them
    if request.headers.get("x-high-urgency") == "true":
        return 0.9
    
    # Fallback to a default or session-based logic (could be expanded)
    return 0.5

def infer_buyer_profile(request): 
    """
    Infer buyer profile automatically (no forms).
    Buyer intent is implicit, not annoying.
    """
    return BuyerProfile( 
        interest_type=request.headers.get("x-interest-type"), 
        budget_min=_safe_int(request.headers.get("x-budget-min")), 
        budget_max=_safe_int(request.headers.get("x-budget-max")), 
        location=request.headers.get("x-location"), 
        urgency=_recent_activity_score(request) 
    ) 

class BuyerBehaviorEngine:
    """Infers BuyerProfile from user activity logs."""
    
    @staticmethod
    def infer_profile(activity_logs: List[Any]) -> BuyerProfile:
        profile = BuyerProfile()
        
        if not activity_logs:
            return profile
            
        interest_counts = {}
        locations = {}
        total_urgency = 0
        urgency_count = 0
        budgets = []

        # Weights for events
        EVENT_WEIGHTS = {
            "WHATSAPP_TAP": 1.0,
            "SEARCH_PERFORMED": 0.3,
            "LEAD_VIEWED": 0.1 # Future use
        }

        # Time decay factor (events from the last hour have weight 1.0, older ones decay)
        now = datetime.now(timezone.utc)
        
        for log in activity_logs:
            meta = log.extra_metadata or {}
            
            # Calculate time weight (simple linear decay over 24h)
            log_time = log.timestamp
            if log_time.tzinfo is None:
                log_time = log_time.replace(tzinfo=timezone.utc)
            
            hours_ago = (now - log_time).total_seconds() / 3600
            time_weight = max(0.1, 1.0 - (hours_ago / 24.0))
            
            event_base_weight = EVENT_WEIGHTS.get(log.event_type, 0.1)
            effective_weight = event_base_weight * time_weight
            
            # 1. Infer interest type from searches and taps
            product = meta.get("product") or meta.get("query")
            if product:
                product_key = product.lower()
                interest_counts[product_key] = interest_counts.get(product_key, 0) + effective_weight
            
            # 2. Infer location
            loc = meta.get("location")
            if loc:
                loc_key = loc.lower()
                locations[loc_key] = locations.get(loc_key, 0) + effective_weight
            
            # 3. Infer urgency from event types
            total_urgency += effective_weight * (0.9 if log.event_type == "WHATSAPP_TAP" else 0.4)
            urgency_count += effective_weight
            
            # 4. Infer budget (if available in metadata)
            price = meta.get("price")
            if price:
                budgets.append((price, effective_weight))

        # Finalize profile attributes
        if interest_counts:
            profile.interest_type = max(interest_counts, key=interest_counts.get)
            
        if locations:
            profile.location = max(locations, key=locations.get)
            
        if urgency_count > 0:
            profile.urgency = min(1.0, total_urgency / urgency_count)
            
        if budgets:
            # Weighted average for budget if multiple entries
            weighted_sum = sum(p * w for p, w in budgets)
            total_w = sum(w for p, w in budgets)
            avg_budget = weighted_sum / total_w
            profile.budget_min = int(avg_budget * 0.8)
            profile.budget_max = int(avg_budget * 1.2)
            
        return profile

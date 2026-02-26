
from datetime import datetime, timezone, timedelta
from typing import Optional
from app.intelligence_v2.source_weights import get_source_weight
from app.intelligence_v2.thresholds import FLOOR, HIGH_INTENT, STRICT_PUBLIC
from app.intelligence_v2.industry_aware import get_industrial_threshold_adjustment
from app.intelligence_v2.language_signals import SWAHILI_PATTERNS, SHENG_PATTERNS
from app.intelligence_v2.geo_score import compute_geo_score

def calculate_language_boost(text: str) -> float:
    """
    Returns a boost score (0.0 to 1.0) based on Swahili/Sheng buyer patterns.
    High boost for local market signals.
    """
    if not text:
        return 0.0
    
    text = text.lower()
    local_patterns = SWAHILI_PATTERNS + SHENG_PATTERNS
    
    matches = [p for p in local_patterns if p in text]
    if not matches:
        return 0.0
        
    # Boost scales with number of local signals, capped at 1.0
    boost = 0.5 + (len(matches) * 0.1)
    return min(1.0, boost)

def calculate_final_intelligence_score(
    raw_intent_score: float,
    semantic_score: float,
    text: str,
    source_name: str,
    lead_data: Optional[dict] = None
) -> float:
    """
    NON-NEGOTIABLE SCORING FORMULA:
    final_score = (
        (raw_intent_score * 0.35) + 
        (semantic_score * 0.35) + 
        (language_boost * 0.1) + 
        (geo_score * 0.2)
    ) * source_weight
    """
    # 1. Calculate Language Boost (Swahili/Sheng)
    language_boost = calculate_language_boost(text)
    
    # 2. Get Geo Score (Modular Integration)
    geo_score = 0.0
    if lead_data:
        # Use existing geo_score if already computed, or compute it
        if "geo_score" in lead_data:
            geo_score = lead_data["geo_score"]
        else:
            # Use the new compute_geo_score function with query context if available
            query = lead_data.get("product_category") or lead_data.get("query")
            location = lead_data.get("location_raw") or lead_data.get("location")
            geo_data = compute_geo_score(text, query=query, location=location)
            geo_score = geo_data.get("geo_score", 0.0)
    
    # 3. Get Source Trust Weight
    source_weight = get_source_weight(source_name)
    
    # 4. Apply the Core Weighted Formula (Kenya First Strategy)
    base_score = (
        (raw_intent_score * 0.35) + 
        (semantic_score * 0.35) + 
        (language_boost * 0.1) + 
        (geo_score * 0.2)
    )
    
    # 5. Apply Source Trust Multiplier
    final_score = base_score * source_weight
    
    return round(final_score, 2)

def classify_lead_priority(score: float, query: str = None) -> str:
    """Classifies lead based on strictly enforced thresholds."""
    adj = get_industrial_threshold_adjustment(query) if query else 0.0
    
    if score >= (STRICT_PUBLIC + adj):
        return "STRICT_PUBLIC"
    if score >= (HIGH_INTENT + adj):
        return "HIGH_INTENT"
    if score >= (FLOOR + adj):
        return "QUALIFIED"
    return "BOOTSTRAP"

def calculate_freshness_score(timestamp: Optional[datetime]) -> float:
    """
    Freshness weighting: 1.0 at 0h, 0.0 at 72h.
    """
    if not timestamp:
        return 0.5
        
    now = datetime.now(timezone.utc)
    if not timestamp.tzinfo:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
        
    diff = now - timestamp
    hours_since = diff.total_seconds() / 3600
    
    freshness = max(0.0, 1.0 - (hours_since / 72.0))
    return round(freshness, 2)

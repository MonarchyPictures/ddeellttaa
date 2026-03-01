# app/services/kenya_intent_engine.py
"""
KENYA INTENT SCORING ENGINE — Production-Grade v3 (Streamlined)

What This Engine Does Better Than Generic NLP:
✅ Rewards WhatsApp phone drops
✅ Understands Swahili buying verbs
✅ Scores Kenyan city-level specificity
✅ Prioritizes Facebook marketplace culture
✅ Detects budget-driven buyers
✅ Penalizes stale posts
✅ Allows fast-mode vs deep-mode threshold
"""

import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Tuple, Dict, List, Optional

logger = logging.getLogger(__name__)

# =============================
# CONFIGURATION WEIGHTS
# =============================

# Import thresholds from single source of truth
from app.services.search_config import (
    SEARCH_CONFIG,
    get_intent_threshold,
    get_adaptive_thresholds
)

WEIGHTS = {
    "intent": 0.35,
    "urgency": 0.20,
    "budget": 0.15,
    "location": 0.10,
    "platform": 0.10,
    "contact": 0.05,
    "freshness": 0.05,
}

# Legacy aliases - delegates to search_config.py
INTENT_THRESHOLD_FAST = SEARCH_CONFIG.FAST_INTENT_THRESHOLD
INTENT_THRESHOLD_DEEP = SEARCH_CONFIG.DEEP_INTENT_THRESHOLD
INTENT_THRESHOLD_MINIMUM = SEARCH_CONFIG.FAST_INTENT_THRESHOLD_LOW  # 0.10


# =============================
# SIGNAL PATTERNS
# =============================

BUYER_PATTERNS = [
    r"\blooking for\b",
    r"\bneed\b",
    r"\bwant to buy\b",
    r"\bwtb\b",
    r"\bnatafuta\b",
    r"\bnahitaji\b",
    r"\bnataka kununua\b",
    r"\bbuying\b",
    r"\blf\b",
    r"\bin need of\b",
    r"\bsearching for\b",
]

URGENCY_PATTERNS = [
    r"\burgent\b",
    r"\basap\b",
    r"\btoday\b",
    r"\bimmediately\b",
    r"\bharaka\b",
    r"\bleo\b",
    r"\bhapo sasa\b",
    r"\bkesho\b",
    r"\bnow\b",
]

BUDGET_PATTERNS = [
    r"\b\d{2,6}\s?(k|K)\b",        # 45k
    r"\bksh\s?\d+",                # ksh 45000
    r"\bkes\s?\d+",                # kes 45000
    r"\bbudget\b",
    r"\bwithin\b.*\d+",
    r"\baround\b.*\d+",
    r"\b\d+\s*/=",                 # 10000/=
]

PHONE_PATTERN = r"(07\d{8}|\+254\d{9})"

LOCATION_KEYWORDS = [
    "nairobi", "mombasa", "kisumu", "nakuru", "eldoret",
    "kiambu", "thika", "kitui", "machakos", "kajiado",
    "westlands", "kileleshwa", "ruaka", "kilimani", "karen",
    "langata", "eastleigh", "cbd", "ngong", "jogoo",
]

# Negative patterns (seller signals)
SELLER_PATTERNS = [
    r"\bselling\b",
    r"\bfor sale\b",
    r"\bwholesale\b",
    r"\bretail\b",
    r"\bstock available\b",
]


# =============================
# SCORING FUNCTIONS
# =============================

def score_intent(text: str) -> float:
    """Score buyer intent signals (0-1)."""
    matches = sum(bool(re.search(p, text, re.IGNORECASE)) for p in BUYER_PATTERNS)
    return min(matches / 2, 1.0)


def score_urgency(text: str) -> float:
    """Score urgency signals (0-1)."""
    matches = sum(bool(re.search(p, text, re.IGNORECASE)) for p in URGENCY_PATTERNS)
    return min(matches / 2, 1.0)


def score_budget(text: str) -> float:
    """Score budget mentions (0-1)."""
    matches = sum(bool(re.search(p, text, re.IGNORECASE)) for p in BUDGET_PATTERNS)
    return min(matches / 2, 1.0)


def score_contact(text: str) -> float:
    """Score contact intent (WhatsApp/phone drops)."""
    has_phone = bool(re.search(PHONE_PATTERN, text))
    has_whatsapp = "whatsapp" in text.lower()
    has_inbox = "inbox" in text.lower() or "dm" in text.lower()
    
    score = 0.0
    if has_phone:
        score += 0.6
    if has_whatsapp:
        score += 0.3
    if has_inbox:
        score += 0.2
    
    return min(score, 1.0)


def score_location(text: str) -> float:
    """Score Kenyan location specificity (0-1)."""
    text_lower = text.lower()
    matches = sum(loc in text_lower for loc in LOCATION_KEYWORDS)
    return min(matches / 2, 1.0)


def score_platform(source: str) -> float:
    """Score platform context (0-1)."""
    source = source.lower()
    if "facebook_group" in source or "facebook group" in source:
        return 1.0
    if "facebook" in source:
        return 0.9
    if "telegram" in source:
        return 0.9
    if "jiji" in source:
        return 0.8
    if "pigiame" in source:
        return 0.8
    if "twitter" in source:
        return 0.6
    if "duckduckgo" in source:
        return 0.6
    return 0.5


def score_freshness(hours_old: float = 0, published_at: datetime = None) -> float:
    """Score freshness/recency (0-1)."""
    if published_at:
        delta = datetime.now(timezone.utc) - published_at
        hours_old = delta.total_seconds() / 3600
    
    if hours_old <= 1:
        return 1.0
    elif hours_old <= 6:
        return 0.9
    elif hours_old <= 24:
        return 0.8
    elif hours_old <= 72:
        return 0.6
    elif hours_old <= 168:  # 7 days
        return 0.4
    else:
        return 0.2


def detect_seller_signals(text: str) -> float:
    """Detect seller signals that reduce buyer intent. Returns penalty (0 to -0.3)."""
    text_lower = text.lower()
    penalty = 0.0
    
    for pattern in SELLER_PATTERNS:
        if re.search(pattern, text_lower):
            penalty -= 0.15
    
    return max(penalty, -0.3)


# =============================
# MASTER SCORING FUNCTION
# =============================

def calculate_kenyan_buyer_score(
    text: str,
    source: str = "",
    hours_old: float = 0,
    published_at: datetime = None
) -> Tuple[float, Dict]:
    """
    Calculate comprehensive Kenyan buyer intent score.
    
    Args:
        text: The post/text to analyze
        source: Platform source (e.g., "facebook_group", "jiji")
        hours_old: Age of post in hours (alternative to published_at)
        published_at: Datetime of publication
    
    Returns:
        Tuple of (final_score, breakdown_dict)
    """
    if not text or len(text.strip()) < 5:
        return 0.0, {k: 0.0 for k in WEIGHTS.keys()}
    
    text_lower = text.lower()
    
    # Calculate individual scores
    scores = {
        "intent": score_intent(text_lower),
        "urgency": score_urgency(text_lower),
        "budget": score_budget(text_lower),
        "location": score_location(text_lower),
        "contact": score_contact(text_lower),
        "platform": score_platform(source),
        "freshness": score_freshness(hours_old, published_at),
    }
    
    # Calculate weighted final score
    final_score = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS.keys())
    
    # Apply seller penalty
    penalty = detect_seller_signals(text_lower)
    final_score = max(0.0, min(1.0, final_score + penalty))
    
    return round(final_score, 4), scores


# =============================
# BATCH PROCESSING & UTILITIES
# =============================

def get_intent_badge(score: float) -> str:
    """Get badge classification for score."""
    if score >= 0.60:
        return "hot_lead"
    elif score >= 0.45:
        return "warm_lead"
    elif score >= 0.30:
        return "maybe_buyer"
    elif score >= INTENT_THRESHOLD_MINIMUM:
        return "low_intent"
    else:
        return "none"


def get_threshold_for_mode(mode: str) -> float:
    """Get intent threshold for search mode."""
    if mode == "fast":
        return INTENT_THRESHOLD_FAST
    elif mode == "deep":
        return INTENT_THRESHOLD_DEEP
    return INTENT_THRESHOLD_MINIMUM


def batch_score_leads(leads: List[Dict], location: str = "Kenya") -> List[Dict]:
    """
    Score multiple leads and return sorted by intent score.
    
    Args:
        leads: List of lead dicts with 'text', 'source', 'hours_old'
        location: Location context (unused but kept for API compatibility)
    
    Returns:
        List of leads with added 'intent_score', 'intent_badge', 'score_breakdown'
    """
    scored_leads = []
    
    for lead in leads:
        text = lead.get("text", lead.get("snippet", lead.get("content", "")))
        source = lead.get("source", lead.get("platform", "unknown"))
        hours_old = lead.get("hours_old", lead.get("age_hours", 0))
        
        score, breakdown = calculate_kenyan_buyer_score(text, source, hours_old)
        
        lead["intent_score"] = score
        lead["intent_badge"] = get_intent_badge(score)
        lead["score_breakdown"] = breakdown
        lead["threshold_passed"] = score >= INTENT_THRESHOLD_MINIMUM
        
        scored_leads.append(lead)
    
    # Sort by intent score descending
    scored_leads.sort(key=lambda x: x.get("intent_score", 0), reverse=True)
    
    return scored_leads


def filter_by_threshold(leads: List[Dict], threshold: float) -> List[Dict]:
    """Filter leads by intent threshold."""
    return [lead for lead in leads if lead.get("intent_score", 0) >= threshold]


def get_lead_quality_stats(leads: List[Dict]) -> Dict:
    """Get statistics about lead quality distribution."""
    if not leads:
        return {"total": 0, "hot": 0, "warm": 0, "maybe": 0, "low": 0}
    
    stats = {"total": len(leads), "hot": 0, "warm": 0, "maybe": 0, "low": 0}
    
    for lead in leads:
        badge = lead.get("intent_badge", "none")
        if badge == "hot_lead":
            stats["hot"] += 1
        elif badge == "warm_lead":
            stats["warm"] += 1
        elif badge == "maybe_buyer":
            stats["maybe"] += 1
        else:
            stats["low"] += 1
    
    return stats


# =============================
# BACKWARD COMPATIBILITY
# =============================

def calculate_intent_score(
    text: str,
    source: str = "",
    hours_old: float = 0,
    location: str = "Kenya"
) -> Dict:
    """
    Backward-compatible wrapper that returns full dict (like v2).
    Used by existing code expecting detailed response.
    """
    score, breakdown = calculate_kenyan_buyer_score(text, source, hours_old)
    
    return {
        "total_score": score,
        "threshold_passed": score >= INTENT_THRESHOLD_MINIMUM,
        "badge": get_intent_badge(score),
        "breakdown": breakdown,
        "weights": WEIGHTS,
        "thresholds": {
            "fast": INTENT_THRESHOLD_FAST,
            "deep": INTENT_THRESHOLD_DEEP,
            "minimum": INTENT_THRESHOLD_MINIMUM
        }
    }


# =============================
# BACKWARD COMPATIBILITY ALIASES
# =============================

# For legacy code that imports calculate_kenyan_intent_score
calculate_kenyan_intent_score = calculate_kenyan_buyer_score

# For legacy code that imports from kenya_high_recall_pipeline
process_high_recall_results = batch_score_leads


def generate_high_recall_queries(product: str, location: str = "Kenya") -> List[str]:
    """
    Generate high-recall queries for agent/celery use.
    Combines fast and deep query strategies.
    """
    queries = [
        # Core buyer intent queries
        f'"{product}" "{location}" (natafuta OR nahitaji OR "looking for" OR need OR wtb)',
        f'"{product}" "{location}" budget',
        # Platform-specific
        f'site:facebook.com "{product}" "{location}" (natafuta OR "looking for")',
        f'site:t.me "{product}" "{location}"',
        f'site:jiji.co.ke "{product}" "{location}"',
        # Urgency-based
        f'"{product}" "{location}" urgently',
        f'"{product}" "{location}" asap',
    ]
    return queries



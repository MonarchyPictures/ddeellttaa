
import re
from typing import List
from app.intelligence_v2.language_signals import ALL_BUYER_PATTERNS, URGENCY_KEYWORDS

def is_buyer_intent(text: str) -> bool:
    """
    CORE LOGIC: Returns True if text exhibits clear buyer intent.
    Scrapers emit signals; this engine validates them.
    """
    if not text:
        return False
    text = text.lower()
    return any(p in text for p in ALL_BUYER_PATTERNS)

def calculate_intent_score(text: str) -> float:
    """
    Calculates a buyer intent score from 0.0 to 1.0.
    Heuristic: pattern matching + urgency + specificity.
    """
    if not text:
        return 0.0
        
    text = text.lower()
    score = 0.0

    # 1. Base intent from patterns
    matched_patterns = [p for p in ALL_BUYER_PATTERNS if p in text]
    if matched_patterns:
        score += 0.4
        score += min(len(matched_patterns) * 0.1, 0.3) # Bonus for multiple signals

    # 2. Urgency signals
    if any(u in text for u in URGENCY_KEYWORDS):
        score += 0.2

    # 3. Specificity signals (quantities, models, currencies)
    # Pattern for quantities (l, kg, tons) or years (202x) or money (ksh, sh)
    if re.search(r'(\d+)\s*(l|kg|units|pcs|ton|20\d{2}|ksh|sh|k\b|m|cm|mm|ft|inches)', text):
        score += 0.1
        
    # Bonus for direct questions/contact requests
    if "?" in text or "price" in text or "cost" in text:
        score += 0.1

    return min(score, 1.0)

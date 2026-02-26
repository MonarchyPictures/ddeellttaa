import logging
import re
from typing import Dict, Any, Tuple

from app.services.market_classifier import classify_market_side
from .intent import BUYER_PATTERNS, is_buyer_intent, buyer_intent_score

logger = logging.getLogger(__name__)

# Legacy support
BUYER_KEYWORDS = BUYER_PATTERNS
STRICT_BUYER_KEYWORDS = BUYER_PATTERNS
HIGH_INTENT = BUYER_PATTERNS # Simplified for now
MEDIUM_INTENT = BUYER_PATTERNS
LOW_INTENT = BUYER_PATTERNS
FINANCIAL_KEYWORDS = BUYER_PATTERNS
URGENCY_KEYWORDS = BUYER_PATTERNS
LOCAL_CONTEXT = BUYER_PATTERNS

# ⚠️ SELLER KEYWORDS (Flagging Only - Do Not Drop)
# Generalized to remove vehicle-specific "full duty paid", "accepting trade-ins" etc.
SELLER_KEYWORDS = [
    "for sale", "selling", "units available", "brand new", "dealers", "showroom", 
    "just arrived", "bank finance", "in stock", "we sell", "shop", "promo",
    "wholesale", "retail", "special offer", "discount", "order now"
]

# ⚠️ NEGATIVE / NON-BUYER INTENT (Flagging Only)
NEGATIVE_INTENT = [
    "free", "not buying", "just looking", "too expensive", "no money", "fake", "scam", "not interested",
    "ya bure", "sitanunua", "naangalia tu", "ni ghali", "sina pesa", "ni feki", "si serious", "siko interested",
    "tuangalie tu", "ni bei mingi", "pesa zimeisha", "mchezo", "si mimi"
]

# Legacy support for existing logic
SELLER_PATTERNS = SELLER_KEYWORDS

# 🎯 STRICT BUYER GATEKEEPERS (Legacy support - now using BUYER_KEYWORDS)
STRICT_BUYER_KEYWORDS = BUYER_PATTERNS

def classify_post(text: str) -> str:
    """
    Classifies a post as 'buyer' or 'seller' based on intent rules.
    Used for intent tagging (Soft Flagging).
    NOW USES SSoT from app.services.market_classifier
    """
    if not text:
        return "unclear"
    
    # Use the robust market classifier
    market_side = classify_market_side(text)
    
    # Map 'demand' -> 'buyer', 'supply' -> 'seller'
    if market_side == "demand":
        return "buyer"
    elif market_side == "supply":
        return "seller" # Return 'seller' instead of 'potential_seller' for strictness
    
    return "potential_seller"

def get_intent_score(text: str) -> float:
    """
    Calculates an intent score from 0.0 to 1.0 based on intensity of phrases.
    Uses the new generic Buyer Intent Engine.
    """
    return buyer_intent_score(text)

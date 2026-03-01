# app/services/scoring/intent_model.py
"""
Intent Signal Score (Weight: 40%)

Strongest signal in Kenya.
"""
import re

# Strong Buyer Signals (+1.0 raw)
STRONG_SIGNALS = [
    "natafuta",      # I'm looking for (Swahili)
    "nahitaji",      # I need (Swahili)
    "looking for",   # Direct English
    "want to buy",   # Direct English
    "wtb",           # Want to buy
    "need urgently", # Urgent need
    "cash ready",    # Ready to buy
]

# Medium Signals (+0.7 raw)
MEDIUM_SIGNALS = [
    "any leads",     # Looking for recommendations
    "who knows",     # Seeking info
    "inbox me",      # Kenyan style
    "dm me",         # Want details
    "recommend",     # Seeking suggestions
]

# Weak Signals (+0.4 raw)
WEAK_SIGNALS = [
    "price",         # Asking about price
    "available",     # Checking availability
    "how much",      # Budget inquiry
]

# Seller signals (hard reject)
SELLER_SIGNALS = [
    "for sale", "we sell", "i sell", "in stock",
    "shop now", "buy now", "order now",
    "contact us", "call us", "visit our",
    "dealer", "distributor", "retail", "wholesale",
    "supplier", "vendor", "price drop", "clearance"
]


def score_intent_signal(text: str) -> float:
    """
    Score buyer intent signals (0.0 to 1.0).
    
    Kenya-specific tiers:
    - STRONG (+1.0 raw): natafuta, nahitaji, looking for, wtb, cash ready, need urgently
    - MEDIUM (+0.7 raw): any leads, who knows, inbox me, dm me, recommend
    - WEAK (+0.4 raw): price, available, how much
    
    Hard reject sellers: "for sale", "selling", "we sell", etc.
    """
    if not text:
        return 0.0
        
    text_lower = text.lower()
    
    # HARD REJECT: Seller signals (check first)
    for signal in SELLER_SIGNALS:
        if signal in text_lower:
            return 0.0
    
    # Check for "selling" as a word boundary
    if re.search(r'\bselling\b', text_lower):
        return 0.0
    
    # STRONG signals (+1.0 raw)
    for signal in STRONG_SIGNALS:
        if signal in text_lower:
            return 1.0
    
    # MEDIUM signals (+0.7 raw)
    for signal in MEDIUM_SIGNALS:
        if signal in text_lower:
            return 0.7
    
    # WEAK signals (+0.4 raw)
    for signal in WEAK_SIGNALS:
        if signal in text_lower:
            return 0.4
    
    return 0.0

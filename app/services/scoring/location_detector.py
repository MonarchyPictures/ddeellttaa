# app/services/scoring/location_detector.py
"""
Location Score (Weight: 10%)

Kenyan buyers often mention specific estates/counties.
"""

# Kenya locations
KENYA_LOCATIONS = [
    "nairobi", "kileleshwa", "rongai", "ruaka",
    "syokimau", "westlands", "mombasa",
    "kisumu", "nakuru"
]


def score_location(text: str, target_location: str = "Kenya") -> float:
    """
    Score location specificity (0.0 to 1.0).
    
    If specific estate/county mentioned: boost to 1.0
    """
    if not text:
        return 0.0
        
    text_lower = text.lower()
    
    for loc in KENYA_LOCATIONS:
        if loc in text_lower:
            return 1.0
    
    return 0.0

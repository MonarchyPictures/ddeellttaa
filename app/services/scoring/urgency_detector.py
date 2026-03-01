# app/services/scoring/urgency_detector.py
"""
Urgency Score (Weight: 20%)

Kenyan buyers often express urgency.
"""

# Urgent terms
URGENT_TERMS = [
    "urgent", "urgently", "asap",
    "today", "immediately", "haraka"
]


def score_urgency(text: str) -> float:
    """
    Score urgency (0.0 to 1.0).
    
    Kenyan urgency terms:
    - "urgently", "asap", "today", "immediately", "haraka"
    """
    if not text:
        return 0.0
        
    text_lower = text.lower()
    
    for term in URGENT_TERMS:
        if term in text_lower:
            return 1.0
    
    return 0.0

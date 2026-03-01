# app/services/scoring/budget_detector.py
"""
Budget Score (Weight: 20%)

Kenyan buyers frequently mention money.
"""
import re


def score_budget(text: str) -> float:
    """
    Score budget clarity (0.0 to 1.0).
    
    Detects:
    - ksh
    - kes
    - "budget"
    - number + k
    - number + m
    
    Budget mention = serious buyer.
    """
    if not text:
        return 0.0
        
    text_lower = text.lower()
    
    # EXPLICIT budget mention = serious buyer
    if "budget" in text_lower:
        return 1.0
    
    # Currency mention (KSH/KES)
    if re.search(r"\b(ksh|kes)\b", text_lower):
        return 1.0
    
    # Price shorthand (50k, 100k, 1m, 1.5m)
    if re.search(r"\b\d+\s?k\b", text_lower):
        return 0.8
    
    if re.search(r"\b\d+\s?m\b", text_lower):
        return 0.8
    
    return 0.0

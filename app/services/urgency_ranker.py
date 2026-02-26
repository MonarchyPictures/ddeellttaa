
import re

def calculate_urgency_score(text: str) -> float:
    """
    Calculate urgency score based on keywords in the text.
    Returns a float between 0.0 and 1.0.
    """
    if not text:
        return 0.1
        
    text_lower = text.lower()
    
    critical_keywords = ["urgent", "emergency", "asap", "immediately", "deadline"]
    high_keywords = ["looking for", "need", "want to buy", "wtb", "ready to buy"]
    medium_keywords = ["interested", "planning", "price for"]
    
    score = 0.2
    
    for kw in critical_keywords:
        if kw in text_lower:
            score += 0.4
            
    for kw in high_keywords:
        if kw in text_lower:
            score += 0.2
            
    for kw in medium_keywords:
        if kw in text_lower:
            score += 0.1
            
    return min(score, 0.99)

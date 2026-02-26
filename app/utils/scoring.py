import re
from datetime import datetime

def calculate_scores(text: str, query: str, location: str, post_date: datetime = None) -> dict:
    """
    Calculates intent, geo, and freshness scores, and the final ranked score.
    Returns a dict with all scores.
    """
    text = (text or "").lower()
    query = (query or "").lower()
    location = (location or "").lower()
    
    # 1. Intent Score (0.0 - 1.0)
    # Base score
    intent_score = 0.3 
    
    high_intent_keywords = ["urgent", "looking for", "wtb", "buying", "need", "budget", "price", "cash ready"]
    medium_intent_keywords = ["interested", "details", "info", "how much", "available?"]
    
    # Check keywords
    found_high = False
    for word in high_intent_keywords:
        if word in text:
            intent_score += 0.15
            found_high = True
            
    for word in medium_intent_keywords:
        if word in text:
            intent_score += 0.05
    
    # Boost if multiple high intent keywords
    if found_high and any(word in text for word in high_intent_keywords if word not in text):
         intent_score += 0.1
            
    # Query match
    if query and query in text:
        intent_score += 0.2
        
    intent_score = min(max(intent_score, 0.0), 1.0)
    
    # 2. Geo Score (0.0 - 1.0)
    geo_score = 0.2 # Base
    if location:
        if location in text:
            geo_score = 1.0
        elif any(part in text for part in location.split() if len(part) > 3):
            # Partial match (e.g. "Nairobi" in "Nairobi, Kenya")
            geo_score = 0.6
    else:
        geo_score = 0.5 # Neutral if no location specified
        
    # 3. Freshness Score (0.0 - 1.0)
    freshness_score = 0.5 # Default
    
    if post_date:
        age_hours = (datetime.utcnow() - post_date).total_seconds() / 3600
        if age_hours < 24:
            freshness_score = 1.0
        elif age_hours < 48:
            freshness_score = 0.8
        elif age_hours < 168: # 1 week
            freshness_score = 0.5
        else:
            freshness_score = 0.2
    else:
        # Regex for time patterns in text
        if re.search(r'\b(just now|mins? ago|hours? ago|\d+h ago)\b', text):
            freshness_score = 1.0
        elif re.search(r'\b(yesterday|1 day ago|\d+d ago)\b', text):
            freshness_score = 0.8
        elif re.search(r'\b(\d+ days? ago)\b', text):
            freshness_score = 0.6
        elif re.search(r'\b(weeks? ago|months? ago)\b', text):
            freshness_score = 0.2
            
    # Final Ranked Score
    # Formula: (intent_score * 0.5) + (geo_score * 0.3) + (freshness_score * 0.2)
    ranked_score = (intent_score * 0.5) + (geo_score * 0.3) + (freshness_score * 0.2)
    
    return {
        "intent_score": round(intent_score, 2),
        "geo_score": round(geo_score, 2),
        "freshness_score": round(freshness_score, 2),
        "ranked_score": round(ranked_score, 2)
    }

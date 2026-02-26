import logging

logger = logging.getLogger(__name__)

from .buyer_classifier import get_intent_score

from datetime import datetime, timedelta, timezone

def calculate_buyer_score(lead: dict, target_location: str = "Nairobi") -> float:
    """
    📌 BUYER SCORING ENGINE (Money Maker Logic)
    Rules:
    - Budget mentioned? +20
    - Urgency? +25
    - Location match? +20
    - Recent post (<48h)? +25
    - Contact available? +10
    """
    score = 0
    intent_text = (lead.get("intent") or lead.get("buyer_intent_quote") or lead.get("buyer_request_snippet") or "").lower()
    
    # 💰 Budget mentioned? +20
    if lead.get("budget") or any(x in intent_text for x in ["budget", "kes", "sh", "price", "800k", "1.1m", "2.5m"]):
        score += 20
        
    # 🚀 Urgency? +25
    urgency_words = ["urgent", "asap", "immediately", "today", "now", "haraka", "sasa", "leo"]
    if any(word in intent_text for word in urgency_words) or lead.get("urgency_level") == "high":
        score += 25
        
    # 📍 Location match? +20
    lead_location = (lead.get("location") or lead.get("location_raw") or "").lower()
    if target_location.lower() in lead_location or any(loc in intent_text for loc in ["nairobi", "mombasa", "kisumu", "eldoret"]):
        score += 20
        
    # ⏱️ Recent post (<48h)? +25
    posted_at = lead.get("posted_at")
    if isinstance(posted_at, str):
        try:
            posted_at = datetime.strptime(posted_at, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except:
            posted_at = datetime.now(timezone.utc)
    
    if not posted_at:
        posted_at = datetime.now(timezone.utc)
        
    # Ensure posted_at is timezone-aware if naive
    if posted_at.tzinfo is None:
        posted_at = posted_at.replace(tzinfo=timezone.utc)
        
    if datetime.now(timezone.utc) - posted_at <= timedelta(hours=48):
        score += 25
        
    # 📱 Contact available? +10
    if lead.get("contact") or lead.get("contact_phone") or lead.get("whatsapp_link"):
        score += 10
        
    # Normalize to 0.0 - 1.0 for the internal engine
    return min(score / 100.0, 1.0)

def base_confidence(lead: dict) -> float:
    """
    📌 Legacy wrapper for internal engine compatibility.
    """
    return calculate_buyer_score(lead)

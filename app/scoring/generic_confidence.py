from datetime import datetime, timedelta

def active_seller_score(signal: dict) -> float:
    """
    Detects active sellers vs 'dead' posts.
    - Many comments: +0.3
    - Recent 'available' keyword in comments: +0.4
    - Updated within 24h: +0.3
    """
    score = 0.0
    
    # 💬 Comments count signal
    comments_count = signal.get("comments_count", 0)
    if comments_count > 3:
        score += 0.3
        
    # 🔄 Recency / Available signal in comments
    recent_comments = signal.get("recent_comments", "")
    if isinstance(recent_comments, list):
        recent_comments = " ".join(recent_comments)
    
    if "available" in str(recent_comments).lower():
        score += 0.4
        
    # ⏱️ Update window signal
    updated_at = signal.get("updated_at")
    if updated_at:
        if isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            except:
                updated_at = None
        
        if updated_at and (datetime.utcnow() - updated_at.replace(tzinfo=None)) < timedelta(hours=24):
            score += 0.3
    elif signal.get("is_recent") or signal.get("timestamp_recent"):
        # Fallback for scrapers that only provide a 'recent' flag
        score += 0.3

    return round(score, 2)

def calculate_freshness_score(signal: dict) -> float:
    """
    Freshness weighting: freshness_score = max(0, 1 - (hours_since_post / 72))
    Nothing older than 3 days (72 hours) survives.
    """
    created_at = signal.get("created_at") or signal.get("timestamp")
    
    if not created_at:
        # If no timestamp, check if it's explicitly marked as recent
        if signal.get("is_recent") or signal.get("timestamp_recent"):
            return 1.0 # Assume fresh if marked recent but no timestamp
        return 0.5 # Default middle ground for unknown age
        
    if isinstance(created_at, str):
        try:
            # Handle common ISO formats
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        except:
            return 0.5

    # Ensure naive vs aware comparison safety
    now = datetime.utcnow()
    if created_at.tzinfo:
        from datetime import timezone
        now = datetime.now(timezone.utc)
    
    diff = now - created_at
    hours_since_post = diff.total_seconds() / 3600
    
    freshness = max(0.0, 1.0 - (hours_since_post / 72.0))
    return round(freshness, 2)

def score_signal(signal: dict) -> float:
    """
    Calculates a confidence score for ANY market signal.
    Score components:
    - Price availability: +0.25
    - Location availability: +0.20
    - Contact info availability: +0.25
    - High-trust sources (FB/Classifieds): +0.20
    - Recency signal: +0.10
    """
    score = 0.0

    # 💰 Price availability
    if signal.get("price") or signal.get("buyer_budget"):
        score += 0.25
    
    # 📍 Location availability
    if signal.get("location") or signal.get("location_raw"):
        score += 0.20
    
    # 📞 Contact info (phone, whatsapp, etc)
    if signal.get("contact") or signal.get("buyer_contact") or signal.get("whatsapp_link"):
        score += 0.25
    
    # 🏛️ Trusted Sources
    source = str(signal.get("source", "")).lower()
    scraper_name = str(signal.get("_scraper_name", "")).lower()
    
    # Boost known good sources
    if any(x in source or x in scraper_name for x in ["jiji", "pigiame", "facebook", "maps"]):
        score += 0.20
        
    # ⏱️ Recency
    if signal.get("is_recent") or calculate_freshness_score(signal) > 0.8:
        score += 0.10

    return round(min(score, 1.0), 2)

def is_hot_lead(lead_data: dict) -> bool:
    """
    Monetization Logic: Determines if a lead qualifies as a "Hot Lead" (Pay-Per-Lead).
    Criteria:
    - Buyer match score >= 0.7 (High market relevance)
    - Freshness < 48h (Highly active)
    - Active seller score >= 0.5 (Proven responsiveness)
    """
    # 1. Match Score Check (Rank Score)
    match_score = lead_data.get("buyer_match_score", 0.0) or lead_data.get("rank_score", 0.0)
    
    # 2. Freshness Check
    created_at = lead_data.get("created_at") or lead_data.get("timestamp")
    freshness_hours = 999 # Default to stale
    if created_at:
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except: pass
        
        if isinstance(created_at, datetime):
            now = datetime.utcnow()
            if created_at.tzinfo:
                from datetime import timezone
                now = datetime.now(timezone.utc)
            diff = now - created_at
            freshness_hours = diff.total_seconds() / 3600

    # 3. Active Seller Score
    # We pass the lead_data directly to the scorer
    seller_score = active_seller_score(lead_data)

    return (
        match_score >= 0.7 and
        freshness_hours <= 48 and
        seller_score >= 0.5
    )

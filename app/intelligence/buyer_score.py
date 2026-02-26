def buyer_score(lead):
    """
    Lock Buyer Scoring (Simple, brutal, effective)
    Add a single final score that decides priority.
    """
    score = 0.0

    # Intent language
    # Assuming lead is a dict or has attributes
    intent_score = lead.get('intent_score') if isinstance(lead, dict) else getattr(lead, 'intent_score', 0)
    if intent_score is not None and intent_score >= 0.8:
        score += 0.4

    # Freshness
    hours_since_post = lead.get('hours_since_post') if isinstance(lead, dict) else getattr(lead, 'hours_since_post', 99)
    if hours_since_post <= 6:
        score += 0.3
    elif hours_since_post <= 24:
        score += 0.2

    # Contact availability
    phone = lead.get('phone') or lead.get('contact_phone') if isinstance(lead, dict) else (getattr(lead, 'phone', None) or getattr(lead, 'contact_phone', None))
    if phone:
        score += 0.2

    # Urgency keywords
    urgency = lead.get('urgency') or lead.get('urgency_level') if isinstance(lead, dict) else (getattr(lead, 'urgency', None) or getattr(lead, 'urgency_level', None))
    if urgency == "high":
        score += 0.1

    return round(min(score, 1.0), 2)

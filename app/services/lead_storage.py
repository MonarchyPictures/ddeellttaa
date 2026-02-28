# app/services/lead_storage.py
# ============================================================
# LEAD STORAGE — Clean Simple Implementation
# ============================================================

from app.models.lead import Lead


def save_leads_to_db(leads, db):
    """
    Save leads to database.
    
    Args:
        leads: List of lead dictionaries
        db: SQLAlchemy session
    """
    for l in leads:
        lead = Lead(
            title=l.get("title"),
            url=l.get("url"),
            snippet=l.get("snippet"),
            score=l.get("score", 0),
            source=l.get("source"),
            intent_score=l.get("intent_score", 0),
            badge=l.get("badge", "COLD")
        )
        db.add(lead)

    db.commit()

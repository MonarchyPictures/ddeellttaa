# app/services/lead_storage.py
# ============================================================
# LEAD STORAGE — Production-Grade Implementation
# ============================================================

import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone

from app.db.database import SessionLocal
from app.models.lead import Lead

logger = logging.getLogger(__name__)


def save_leads_to_db(leads: List[Dict], query_context: str = "") -> int:
    """
    Save leads to database.
    
    Args:
        leads: List of lead dictionaries
        query_context: Optional query/context for logging
        
    Returns:
        Number of leads saved
    """
    if not leads:
        return 0
    
    db = SessionLocal()
    saved_count = 0
    
    try:
        for lead_data in leads:
            # Skip if missing critical fields
            if not lead_data.get("url") and not lead_data.get("title"):
                continue
                
            # Create Lead model instance
            lead = Lead(
                title=lead_data.get("title", "Untitled Lead"),
                url=lead_data.get("url", ""),
                snippet=lead_data.get("snippet") or lead_data.get("buyer_request_snippet", ""),
                source=lead_data.get("source", "unknown"),
                source_url=lead_data.get("source_url") or lead_data.get("url", ""),
                location=lead_data.get("location", "Kenya"),
                contact_phone=lead_data.get("contact_phone") or lead_data.get("phone"),
                contact_email=lead_data.get("contact_email") or lead_data.get("email"),
                buyer_name=lead_data.get("buyer_name"),
                price=lead_data.get("price"),
                intent_score=lead_data.get("intent_score", 0),
                intent_badge=lead_data.get("intent_badge") or lead_data.get("badge", "COLD"),
                confidence=lead_data.get("confidence", lead_data.get("intent_score", 0) * 100),
                market_side="demand",
                status="NEW",
                whatsapp_url=lead_data.get("whatsapp_url"),
                telegram_username=lead_data.get("telegram_username"),
                telegram_link=lead_data.get("telegram_link"),
                telegram_group=lead_data.get("telegram_group"),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(lead)
            saved_count += 1
        
        db.commit()
        logger.info(f"💾 Saved {saved_count}/{len(leads)} leads to DB (context: {query_context or 'search'})")
        return saved_count
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save leads: {e}")
        return 0
    finally:
        db.close()


async def save_leads_to_db_async(leads: List[Dict], query_context: str = "") -> int:
    """Async wrapper for save_leads_to_db."""
    return save_leads_to_db(leads, query_context)

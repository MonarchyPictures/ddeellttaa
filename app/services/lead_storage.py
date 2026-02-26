import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.lead import Lead, CRMStatus

logger = logging.getLogger(__name__)

def save_leads_to_db(leads: List[Dict[str, Any]], query_text: str):
    """
    Saves a batch of leads to the database.
    Designed to be run as a background task.
    """
    if not leads:
        return

    db = SessionLocal()
    try:
        saved_count = 0
        for lead_data in leads:
            try:
                # 0. Validate URL
                url = lead_data.get("url")
                if not url:
                    continue

                # 1. Check for duplicates by URL
                existing = db.query(Lead).filter(Lead.url == url).first()
                if existing:
                    # Update existing? For now, skip to avoid overwriting with potentially less data
                    # Or maybe update timestamp?
                    continue

                # 2. Normalize confidence from either numeric score or label.
                confidence_map = {"high": 0.9, "medium": 0.6, "low": 0.3}
                confidence_raw = lead_data.get("confidence_score", lead_data.get("confidence", 0.3))
                if isinstance(confidence_raw, str):
                    confidence_val = confidence_map.get(confidence_raw.lower(), 0.3)
                else:
                    try:
                        confidence_val = float(confidence_raw)
                    except Exception:
                        confidence_val = 0.3
                confidence_val = max(0.0, min(1.0, confidence_val))
                
                # 3. Extract Entities
                extracted = lead_data.get("extracted", {}) or {}
                phone = extracted.get("phone") or lead_data.get("contact_phone") or lead_data.get("phone")
                email = extracted.get("email") or lead_data.get("contact_email") or lead_data.get("email")
                whatsapp_link = (
                    extracted.get("whatsapp_link")
                    or lead_data.get("whatsapp_link")
                    or lead_data.get("whatsapp_url")
                )
                buyer_name = lead_data.get("buyer_name") or lead_data.get("author") or "Market Signal"
                snippet = lead_data.get("snippet") or lead_data.get("buyer_request_snippet") or lead_data.get("text")
                intent_type = lead_data.get("intent_type")
                if not intent_type:
                    intent_type = "BUYER" if lead_data.get("is_buyer", True) else "SELLER"
                
                # 4. Create Lead Object
                new_lead = Lead(
                    title=lead_data.get("title") or "Untitled Lead",
                    buyer_name=buyer_name,
                    url=lead_data.get("url"),
                    source=lead_data.get("source"),
                    description=snippet,
                    buyer_request_snippet=snippet,
                    
                    # Intent & Scoring
                    intent_score=lead_data.get("intent_score", 0.0),
                    confidence_score=confidence_val,
                    intent_type=intent_type,
                    
                    # Entities
                    price=extracted.get("budget"), # Map budget to price/budget field
                    budget=extracted.get("budget"),
                    location=extracted.get("location") or lead_data.get("location"), # Fallback
                    location_raw=extracted.get("location") or lead_data.get("location"),
                    contact_phone=phone,
                    contact_email=email,
                    whatsapp_link=whatsapp_link,
                    
                    # Context
                    query=query_text,
                    status=CRMStatus.NEW,
                    
                    # Default Flags
                    is_verified_signal=1,
                    verification_flag="verified"
                )
                
                db.add(new_lead)
                saved_count += 1
            
            except Exception as e:
                logger.error(f"Failed to save individual lead: {e}")
                continue

        db.commit()
        logger.info(f"Saved {saved_count} new leads to DB (Background Task)")

    except Exception as e:
        logger.error(f"Database error in save_leads_to_db: {e}")
        db.rollback()
    finally:
        db.close()

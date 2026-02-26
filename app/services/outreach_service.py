from sqlalchemy.orm import Session
from app.db import models
from app.intelligence.outreach import generate_message
from app.utils.outreach import whatsapp_link
from app.intelligence.buyer_score import buyer_score
from datetime import datetime, timezone

def get_whatsapp_link_data(lead_id: str, db: Session):
    """Generates a WhatsApp link for a lead with a prefilled message."""
    try:
        lead_id_int = int(lead_id)
        lead = db.query(models.Lead).filter(models.Lead.id == lead_id_int).first()
    except ValueError:
        lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    
    if not lead:
        return {"url": None, "error": "Lead not found", "detail": f"No lead with ID {lead_id}"}
    
    # Generate the personalized message
    message = generate_message(lead)
    
    # Normalize phone number from lead data
    phone = lead.phone or lead.contact or getattr(lead, 'buyer_contact', None) or lead.contact_phone
    
    if not phone:
        # Fallback: check if the link itself is a whatsapp link
        if lead.url and "wa.me" in lead.url:
            return {"url": lead.url}
        if lead.whatsapp_link:
             return {"url": lead.whatsapp_link}

        return {
            "url": None, 
            "error": "No phone number available", 
            "detail": "Lead has no contact phone number"
        }
        
    return {
        "url": whatsapp_link(phone, message)
    }

def generate_outreach_message(lead_id: str, db: Session):
    """
    Calculates outreach scores and generates the best message.
    """
    # Try to find lead by ID
    try:
        lead_id_int = int(lead_id)
        lead = db.query(models.Lead).filter(models.Lead.id == lead_id_int).first()
    except ValueError:
        lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    
    if not lead:
        return {"error": "Lead not found", "lead_id": lead_id}
    
    # 📝 INJECT CALCULATED SCORES FOR MESSAGE LOGIC
    now = datetime.now(timezone.utc)
    lead_time = lead.created_at
    if lead_time.tzinfo is None:
        lead_time = lead_time.replace(tzinfo=timezone.utc)
    hours_old = (now - lead_time).total_seconds() / 3600
    
    # Temporarily add these to the lead object for the engine
    lead.hours_since_post = hours_old
    lead.buyer_match_score = buyer_score(lead)
    
    message = generate_message(lead)
    
    return {
        "lead_id": lead_id,
        "message": message,
        "buyer_match_score": lead.buyer_match_score
    }

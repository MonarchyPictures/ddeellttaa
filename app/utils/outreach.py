from app.db import models
from sqlalchemy.orm import Session
from sqlalchemy import or_
import json
from datetime import datetime, timezone
import urllib.parse

def whatsapp_link(phone: str, message: str):
    """Generates a prefilled WhatsApp link with zero friction."""
    if not phone:
        return ""
    clean = phone.replace("+", "").replace(" ", "").replace("-", "")
    encoded = urllib.parse.quote(message)
    return f"https://wa.me/{clean}?text={encoded}"

class OutreachEngine:
    def __init__(self):
        self.templates = {
            "distress": "I saw you’re selling urgently. I have a ready buyer in Nairobi — can we talk now?",
            "casual": "Your {product} fits a buyer request I’m handling. Is the price flexible?",
            "urgent_buyer": "Hi {name}, I saw you're looking for {product} urgently. I might be able to help you out right away. Are you still searching?",
            "general_buyer": "Hello {name}, regarding your post about needing {product} - I have some options that might fit what you're looking for. Let me know if you're interested!"
        }

    def generate_message(self, lead_data):
        """Generate a personalized message based on lead attributes."""
        name = lead_data.get("buyer_name", "there")
        product = lead_data.get("product_category") or lead_data.get("product") or "the item"
        intent_score = lead_data.get("intent_score") or lead_data.get("intent_strength", 0)
        
        # Determine if it's a seller or buyer (in this system, we focus on buyer intent, 
        # but the prompt specifically asked for seller templates too)
        is_distress = "urgent" in lead_data.get("buyer_request_snippet", "").lower() or \
                      "haraka" in lead_data.get("buyer_request_snippet", "").lower() or \
                      lead_data.get("urgency_level") == "high"

        # If we detect it's a seller post (though the engine is buyer-focused, 
        # we'll add logic to handle the user's specific seller template request)
        if "sell" in lead_data.get("buyer_request_snippet", "").lower() or \
           "sale" in lead_data.get("buyer_request_snippet", "").lower():
            if is_distress:
                return self.templates["distress"]
            else:
                return self.templates["casual"].format(product=product)

        # Standard Buyer Templates
        if intent_score > 0.8:
            return self.templates["urgent_buyer"].format(name=name, product=product)
        else:
            return self.templates["general_buyer"].format(name=name, product=product)

    def select_leads_for_outreach(self, db: Session, min_intent=0.7):
        """Select top-tier leads that haven't been contacted yet."""
        return db.query(models.Lead).filter(
            models.Lead.status == models.CRMStatus.NEW,
            models.Lead.intent_score >= min_intent
        ).order_by(models.Lead.intent_score.desc()).all()

    def mark_contacted(self, db: Session, lead_id: str):
        """Mark a lead as contacted and update timestamp."""
        try:
            lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
            if lead:
                lead.status = models.CRMStatus.CONTACTED
                lead.last_contact_attempt = datetime.now(timezone.utc)
                db.commit()
                return True
            return False
        except Exception as e:
            db.rollback()
            print(f"Error marking lead as contacted: {e}")
            return False

    def track_response(self, db: Session, lead_id: str, response_text: str):
        """Track and analyze response from a buyer with detailed metrics."""
        try:
            lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
            if lead:
                now = datetime.now(timezone.utc)
                
                # Update response metrics
                lead.response_count += 1
                
                if lead.last_contact_attempt:
                    # Calculate response time in minutes
                    diff = now - lead.last_contact_attempt
                    resp_time = diff.total_seconds() / 60
                    
                    if lead.average_response_time_mins:
                        # Rolling average
                        lead.average_response_time_mins = (lead.average_response_time_mins + resp_time) / 2
                    else:
                        lead.average_response_time_mins = resp_time
                
                lead.last_response_received = now
                
                # Improved conversion detection: Positive intent check
                # Check for positive signals while excluding negative context
                positive_words = ["interested", "price", "buy", "send", "yes", "deal", "whatsapp", "call"]
                negative_context = ["not interested", "too expensive", "no thanks", "stop", "wrong number"]
                
                text_lower = response_text.lower()
                is_positive = any(word in text_lower for word in positive_words)
                is_negative = any(context in text_lower for context in negative_context)
                
                if is_positive and not is_negative:
                    lead.status = models.CRMStatus.CONVERTED
                    # Real-world conversion signal: positive response received
                    lead.conversion_rate = 100.0 
                else:
                    lead.status = models.CRMStatus.CONTACTED
                    
                lead.notes = f"Response: {response_text}"
                db.commit()
                return lead.status
            return None
        except Exception as e:
            db.rollback()
            print(f"Error tracking response: {e}")
            return None

    def check_non_response_history(self, db: Session, phone: str = None, email: str = None):
        """Check if this contact has a history of not responding to outreach."""
        if not phone and not email:
            return False
            
        query = db.query(models.Lead)
        filters = []
        if phone:
            filters.append(models.Lead.contact_phone == phone)
        if email:
            filters.append(models.Lead.contact_email == email)
            
        # Look for leads that were contacted but have 0 responses
        history = query.filter(
            or_(*filters),
            models.Lead.status == models.CRMStatus.CONTACTED,
            models.Lead.response_count == 0
        ).all()
        
        return len(history) >= 2 # Flag if they've ignored us twice before

    def get_conversion_analytics(self, db: Session):
        """Get analytics for conversion rates across platforms."""
        stats = {}
        platforms = db.query(models.Lead.source_platform).distinct().all()
        for (platform,) in platforms:
            total = db.query(models.Lead).filter(models.Lead.source_platform == platform).count()
            contacted = db.query(models.Lead).filter(
                models.Lead.source_platform == platform,
                models.Lead.status != models.CRMStatus.NEW
            ).count()
            converted = db.query(models.Lead).filter(
                models.Lead.source_platform == platform,
                models.Lead.status == models.CRMStatus.CONVERTED
            ).count()
            
            stats[platform] = {
                "total_leads": total,
                "outreach_sent": contacted,
                "conversions": converted,
                "conversion_rate": (converted / contacted * 100) if contacted > 0 else 0
            }
        return stats


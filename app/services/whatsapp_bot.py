# app/services/whatsapp_bot.py
# ============================================================
# WHATSAPP AUTO-INTRODUCTION BOT — Enterprise Feature
# ============================================================
# Automatically sends WhatsApp messages to hot leads.
# 
# Requires: WhatsApp Business API (Twilio or Meta)
# ============================================================

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class WhatsAppTemplate:
    """WhatsApp message template (must be pre-approved by Meta)."""
    name: str
    template_id: str
    language: str = "en"
    
    def to_api_format(self, variables: Dict[str, str]) -> Dict[str, Any]:
        """Convert to WhatsApp API format."""
        return {
            "name": self.template_id,
            "language": {"code": self.language},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": variables.get("name", "")},
                        {"type": "text", "text": variables.get("product", "")},
                        {"type": "text", "text": variables.get("location", "")},
                    ]
                }
            ]
        }


# Pre-approved templates (must be approved by Meta)
WHATSAPP_TEMPLATES = {
    "intro": WhatsAppTemplate(
        name="intro",
        template_id="lead_intro_v1",
        language="en"
    ),
    "follow_up": WhatsAppTemplate(
        name="follow_up", 
        template_id="lead_followup_v1",
        language="en"
    ),
}


class WhatsAppBot:
    """
    WhatsApp auto-introduction bot.
    
    Enterprise feature - requires WhatsApp Business API.
    """
    
    def __init__(self, 
                 account_sid: str = None,
                 auth_token: str = None,
                 from_number: str = None):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.templates = WHATSAPP_TEMPLATES
        self.sent_messages: list[Dict] = []
    
    def is_configured(self) -> bool:
        """Check if bot is properly configured."""
        return all([self.account_sid, self.auth_token, self.from_number])
    
    def normalize_phone(self, phone: str) -> str:
        """Normalize phone number to WhatsApp format."""
        # Remove spaces, dashes
        phone = phone.replace(" ", "").replace("-", "")
        
        # Ensure starts with country code
        if phone.startswith("0"):
            phone = "254" + phone[1:]  # Kenya
        elif phone.startswith("+"):
            phone = phone[1:]
        
        return phone
    
    async def send_message(self, 
                          to_number: str, 
                          template: WhatsAppTemplate,
                          variables: Dict[str, str]) -> Dict[str, Any]:
        """
        Send WhatsApp message using template.
        
        Uses Twilio or Meta WhatsApp API.
        """
        if not self.is_configured():
            return {
                "status": "error",
                "error": "WhatsApp bot not configured. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, WHATSAPP_FROM_NUMBER"
            }
        
        # Normalize number
        to_number = self.normalize_phone(to_number)
        
        # Mock sending (replace with actual Twilio/Meta API call)
        # from twilio.rest import Client
        # client = Client(self.account_sid, self.auth_token)
        # message = client.messages.create(
        #     from_=f"whatsapp:{self.from_number}",
        #     to=f"whatsapp:{to_number}",
        #     content_sid=template.template_id
        # )
        
        message_id = f"wa_{datetime.now().timestamp()}"
        
        # Track
        record = {
            "message_id": message_id,
            "to": to_number,
            "template": template.name,
            "variables": variables,
            "sent_at": datetime.now().isoformat(),
            "status": "sent"
        }
        self.sent_messages.append(record)
        
        logger.info(f"Sent WhatsApp to {to_number}")
        
        return {
            "status": "success",
            "message_id": message_id,
            "recipient": to_number
        }
    
    async def send_intro(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """Send introduction message to lead."""
        phone = lead.get("contact_phone") or lead.get("phone")
        if not phone:
            return {
                "status": "error",
                "error": "No phone number for this lead"
            }
        
        template = self.templates["intro"]
        variables = {
            "name": lead.get("buyer_name", "there"),
            "product": lead.get("title", "this product"),
            "location": lead.get("location", "your area")
        }
        
        return await self.send_message(phone, template, variables)
    
    async def process_hot_leads(self, leads: List[Dict]) -> Dict[str, Any]:
        """Process all hot leads and send WhatsApp messages."""
        results = {
            "total_hot": 0,
            "sent": 0,
            "failed": 0,
            "errors": []
        }
        
        for lead in leads:
            if lead.get("badge") != "HOT":
                continue
            
            results["total_hot"] += 1
            
            # Skip if already contacted
            lead_id = lead.get("id")
            if any(m.get("lead_id") == lead_id for m in self.sent_messages):
                continue
            
            result = await self.send_intro(lead)
            
            if result["status"] == "success":
                results["sent"] += 1
                # Track lead_id in record
                self.sent_messages[-1]["lead_id"] = lead_id
            else:
                results["failed"] += 1
                results["errors"].append({
                    "lead_id": lead_id,
                    "error": result.get("error")
                })
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get bot statistics."""
        return {
            "total_sent": len(self.sent_messages),
            "last_7_days": len([m for m in self.sent_messages 
                               if (datetime.now() - datetime.fromisoformat(m["sent_at"])).days < 7]),
            "templates": list(self.templates.keys())
        }


# Global bot instance
whatsapp_bot = WhatsAppBot(
    account_sid=None,  # Load from env: TWILIO_ACCOUNT_SID
    auth_token=None,   # Load from env: TWILIO_AUTH_TOKEN  
    from_number=None   # Load from env: WHATSAPP_FROM_NUMBER
)


async def auto_whatsapp_hot_leads(leads: List[Dict]) -> Dict[str, Any]:
    """Convenience function to WhatsApp all hot leads."""
    return await whatsapp_bot.process_hot_leads(leads)

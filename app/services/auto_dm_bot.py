# app/services/auto_dm_bot.py
# ============================================================
# TELEGRAM AUTO-DM BOT — Enterprise Feature
# ============================================================
# Automatically sends introductory DMs to hot leads on Telegram.
# 
# Workflow:
# 1. Hot lead detected with Telegram handle
# 2. Bot sends personalized intro message
# 3. Tracks response rates
# ============================================================

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class DMTemplate:
    """DM message template."""
    name: str
    subject: str
    body: str
    
    def format(self, **kwargs) -> str:
        """Format template with variables."""
        return self.body.format(**kwargs)


# Default DM templates
DEFAULT_TEMPLATES = {
    "intro": DMTemplate(
        name="intro",
        subject="Introduction",
        body="""Hi {name},

I noticed you're looking for {product} in {location}. 

I can help you find quality {product} at competitive prices. Would you like to see our catalog?

Best regards,
{sender_name}"""
    ),
    "follow_up": DMTemplate(
        name="follow_up",
        subject="Following Up",
        body="""Hi {name},

Just following up on your interest in {product}. 

I have some great options that match your budget. Can we schedule a quick call?

Thanks,
{sender_name}"""
    ),
    "urgent": DMTemplate(
        name="urgent",
        subject="Urgent Response",
        body="""Hi {name},

I see you need {product} urgently. 

I can arrange fast delivery to {location}. Reply now for priority service!

{sender_name}"""
    ),
}


class TelegramDMBot:
    """
    Auto-DM bot for Telegram leads.
    
    Enterprise feature - requires Telegram API credentials.
    """
    
    def __init__(self, api_id: str = None, api_hash: str = None, bot_token: str = None):
        self.api_id = api_id
        self.api_hash = api_hash
        self.bot_token = bot_token
        self.templates = DEFAULT_TEMPLATES
        self.sent_messages: list[Dict] = []
    
    def is_configured(self) -> bool:
        """Check if bot is properly configured."""
        return all([self.api_id, self.api_hash, self.bot_token])
    
    def select_template(self, lead: Dict[str, Any]) -> DMTemplate:
        """Select appropriate template based on lead context."""
        urgency_score = lead.get("urgency_score", 0)
        
        if urgency_score > 0.7:
            return self.templates["urgent"]
        elif lead.get("contacted_before"):
            return self.templates["follow_up"]
        else:
            return self.templates["intro"]
    
    def format_message(self, lead: Dict[str, Any], template: DMTemplate) -> str:
        """Format message with lead data."""
        return template.format(
            name=lead.get("buyer_name", "there"),
            product=lead.get("product", "this item"),
            location=lead.get("location", "your area"),
            sender_name="Your Sales Team",
            price_estimate=lead.get("price_hint", "")
        )
    
    async def send_dm(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send DM to lead.
        
        Returns status and message ID.
        """
        if not self.is_configured():
            return {
                "status": "error",
                "error": "Bot not configured. Set TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_BOT_TOKEN"
            }
        
        # Get Telegram handle/phone
        telegram_handle = lead.get("telegram_handle") or lead.get("contact_phone")
        if not telegram_handle:
            return {
                "status": "error",
                "error": "No Telegram contact available for this lead"
            }
        
        # Select and format template
        template = self.select_template(lead)
        message = self.format_message(lead, template)
        
        # Mock sending (replace with actual Telegram API call)
        # from telethon import TelegramClient
        # async with TelegramClient('bot', self.api_id, self.api_hash) as client:
        #     await client.send_message(telegram_handle, message)
        
        message_id = f"msg_{datetime.now().timestamp()}"
        
        # Track sent message
        record = {
            "message_id": message_id,
            "lead_id": lead.get("id"),
            "telegram_handle": telegram_handle,
            "template": template.name,
            "message": message,
            "sent_at": datetime.now().isoformat(),
            "status": "sent"
        }
        self.sent_messages.append(record)
        
        logger.info(f"Sent DM to {telegram_handle} for lead {lead.get('id')}")
        
        return {
            "status": "success",
            "message_id": message_id,
            "template_used": template.name,
            "recipient": telegram_handle
        }
    
    async def process_hot_leads(self, leads: list[Dict]) -> Dict[str, Any]:
        """
        Process all hot leads and send DMs.
        
        Returns batch results.
        """
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
            
            # Check if already contacted
            if any(m["lead_id"] == lead.get("id") for m in self.sent_messages):
                continue
            
            result = await self.send_dm(lead)
            
            if result["status"] == "success":
                results["sent"] += 1
            else:
                results["failed"] += 1
                results["errors"].append({
                    "lead_id": lead.get("id"),
                    "error": result.get("error")
                })
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get bot statistics."""
        total_sent = len(self.sent_messages)
        recent = [m for m in self.sent_messages if 
                  (datetime.now() - datetime.fromisoformat(m["sent_at"])).days < 7]
        
        return {
            "total_sent": total_sent,
            "last_7_days": len(recent),
            "response_rate": None,  # Would track actual responses
            "templates_available": list(self.templates.keys())
        }


# Global bot instance
telegram_bot = TelegramDMBot(
    api_id=None,  # Load from env: TELEGRAM_API_ID
    api_hash=None,  # Load from env: TELEGRAM_API_HASH
    bot_token=None  # Load from env: TELEGRAM_BOT_TOKEN
)


async def auto_dm_hot_leads(leads: list[Dict]) -> Dict[str, Any]:
    """
    Convenience function to DM all hot leads.
    
    Usage:
        results = await auto_dm_hot_leads(leads)
        print(f"Sent {results['sent']} DMs")
    """
    return await telegram_bot.process_hot_leads(leads)

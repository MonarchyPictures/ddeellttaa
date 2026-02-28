
import logging
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from app.services.cache_service import cache
from app.services.lead_storage import save_leads_to_db
from app.services.kenya_high_recall_pipeline import calculate_kenyan_intent_score
from .notifier import BuyerNotifier

logger = logging.getLogger("telegram.processor")


class MessageProcessor:
    """
    Processes Telegram messages through the buyer classification pipeline.
    Uses new high-recall intent scoring (old engine removed).
    """

    def __init__(self):
        self.notifier = BuyerNotifier()
        self.processed_count = 0
        self.buyer_count = 0
        self.notification_handlers: List = []

        # Deduplication cache (in-memory + Redis)
        self._seen_hashes = set()

    def on_buyer_found(self, handler):
        """Register a callback for when a buyer is found."""
        self.notification_handlers.append(handler)
        return handler

    async def process_message(self, msg_data: Dict[str, Any]) -> Optional[Dict]:
        """
        Process a single Telegram message.
        
        Returns:
            Lead dict if buyer detected, None otherwise.
        """
        text = msg_data.get("text", "")
        if not text or len(text.strip()) < 15:
            return None

        # ── Deduplication ──────────────────────────────────
        text_hash = hashlib.md5(text.lower().strip()[:200].encode()).hexdigest()
        
        # Check memory cache
        if text_hash in self._seen_hashes:
            return None
        
        # Check Redis cache
        cache_key = f"tg_msg:{text_hash}"
        if cache.get(cache_key):
            return None

        self._seen_hashes.add(text_hash)
        cache.set(cache_key, "1", ttl_seconds=86400)  # 24 hour dedup window

        # ── Classify ───────────────────────────────────────
        # Use new high-recall intent scoring
        intent_score = calculate_kenyan_intent_score(text)
        
        self.processed_count += 1

        # Threshold check (0.25 = low threshold for high recall)
        if intent_score < 0.25:
            logger.debug(f"Not a buyer (score {intent_score:.2f}): {text[:50]}...")
            return None

        # Determine badge based on score
        if intent_score >= 0.7:
            badge = "HOT"
        elif intent_score >= 0.5:
            badge = "WARM"
        else:
            badge = "COLD"

        # ── Enhance with Telegram-specific data ────────────
        # Extract phone if present in text
        import re
        phone_match = re.search(r'(\+?254\d{9}|0\d{9}|\+?256\d{9})', text)
        phone = phone_match.group(0) if phone_match else None
        
        # Telegram gives us the sender's phone number directly!
        telegram_phone = msg_data.get("sender_phone", "")
        if telegram_phone and not phone:
            # Format phone number
            if not telegram_phone.startswith("+"):
                telegram_phone = f"+{telegram_phone}"
            phone = telegram_phone

        # Use sender name
        sender_name = msg_data.get("sender_name", "")
        buyer_name = sender_name if sender_name else "Anonymous"

        # ── Build Lead ─────────────────────────────────────
        lead = self._build_telegram_lead(msg_data, text, intent_score, badge, phone, buyer_name)

        self.buyer_count += 1
        logger.info(
            f"🎯 BUYER FOUND in @{msg_data.get('group_username', '?')}: "
            f"'{text[:60]}...' "
            f"Score={intent_score:.2f} Badge={badge} "
            f"Phone={phone or 'N/A'}"
        )

        try:
            # 5. Save to DB
            # We wrap in list because save_leads_to_db expects a batch
            save_leads_to_db([lead], query_text="telegram_monitor")

            # 6. Notify
            priority = "hot" if intent_score > 0.8 else "normal"
            await self.notifier.notify(lead, priority=priority)

        except Exception as e:
            logger.error(f"Error saving/notifying lead: {e}")

        # ── Notify handlers ────────────────────────────────
        for handler in self.notification_handlers:
            try:
                import asyncio
                if asyncio.iscoroutinefunction(handler):
                    await handler(lead)
                else:
                    handler(lead)
            except Exception as e:
                logger.error(f"Notification handler error: {e}")

        return lead

    async def process_batch(self, messages: List[Dict]) -> List[Dict]:
        """Process a batch of messages. Returns list of buyer leads."""
        leads = []
        for msg in messages:
            lead = await self.process_message(msg)
            if lead:
                leads.append(lead)
        
        logger.info(
            f"Batch processed: {len(messages)} messages → "
            f"{len(leads)} buyers found"
        )
        return leads

    def _build_telegram_lead(self, msg_data: Dict, text: str, intent_score: float, badge: str, phone: str, buyer_name: str) -> Dict:
        """Build a lead dict from Telegram message data (new version without old engine)."""
        
        url = msg_data.get("url", "")
        group_name = msg_data.get("group_name", "Telegram Group")
        group_username = msg_data.get("group_username", "")
        sender_username = msg_data.get("sender_username", "")

        # Build contact link
        contact_link = ""
        if sender_username:
            contact_link = f"https://t.me/{sender_username}"
        elif phone:
            clean = phone.replace("+", "").replace(" ", "")
            contact_link = f"https://wa.me/{clean}"

        # WhatsApp message template
        whatsapp_url = ""
        if phone:
            clean = phone.replace("+", "").replace(" ", "")
            if clean.startswith("0"):
                clean = "254" + clean[1:]
            elif not clean.startswith("254"):
                clean = "254" + clean
            whatsapp_url = f"https://wa.me/{clean}"

        # Unique ID
        lead_id = hashlib.md5(f"{url}:{text[:100]}".encode()).hexdigest()[:16]

        # Simple ranked score calculation
        ranked_score = round(intent_score * 0.7 + (0.3 if phone else 0), 2)

        return {
            # Core fields
            "id": lead_id,
            "buyer_name": buyer_name,
            "title": text[:200],
            "price": "Contact for Price",
            "location": "Kenya",
            "phone": phone,
            "contact_phone": phone,
            "email": None,
            "contact_email": None,
            "source": f"Telegram: {group_name}",
            "url": url,
            "source_url": url,

            # Telegram-specific
            "telegram_username": sender_username,
            "telegram_link": contact_link,
            "telegram_group": group_username,
            "telegram_group_name": group_name,
            "telegram_message_id": msg_data.get("message_id"),
            "has_media": msg_data.get("has_media", False),

            # Scores
            "intent_score": intent_score,
            "intent_strength": intent_score,
            "buyer_match_score": intent_score,
            "confidence": round(intent_score * 100, 2),
            "confidence_score": intent_score,
            "urgency_score": 0.5,
            "ranked_score": ranked_score,
            "rank_score": ranked_score,

            # Display
            "buyer_request_snippet": text[:500],
            "buyer_intent_quote": text[:300],
            "snippet": text[:300],

            # Metadata
            "market_side": "demand",
            "badge": badge,
            "verification_flag": "verified" if phone else "telegram_unverified",
            "intent_type": "BUYER",
            "persona": "price_conscious",
            "timeline": "flexible",
            "status": "NEW",
            "is_hot_lead": badge == "HOT",

            # WhatsApp
            "whatsapp_url": whatsapp_url,
            "whatsapp_link": whatsapp_url,

            # Timestamps
            "created_at": msg_data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "posted_at": msg_data.get("timestamp"),

            # Score details
            "score_details": {"method": "high_recall_pipeline_v2"},
            "ui_filter_status": "shown",
            "tap_count": 0
        }

    def get_stats(self) -> Dict:
        """Return processing statistics."""
        return {
            "processed": self.processed_count,
            "buyers_found": self.buyer_count,
            "conversion_rate": (
                round(self.buyer_count / self.processed_count * 100, 1)
                if self.processed_count > 0 else 0
            )
        }

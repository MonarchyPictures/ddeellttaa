# app/telegram/message_processor.py
# ============================================================
# MESSAGE PROCESSOR
# ============================================================
# Takes raw Telegram messages and:
# 1. Classifies as buyer/seller
# 2. Extracts contact info
# 3. Saves to database
# 4. Sends notifications for hot leads
# ============================================================

import logging
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from app.engine.buyer_classifier import BUYER_CLASSIFIER, BuyerSignal
from app.services.cache_service import cache
from app.services.lead_storage import save_leads_to_db
from .notifier import BuyerNotifier

logger = logging.getLogger("telegram.processor")


class MessageProcessor:
    """
    Processes Telegram messages through the buyer classification pipeline.
    """

    def __init__(self):
        self.classifier = BUYER_CLASSIFIER
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
        signal = self.classifier.classify(
            text=text,
            url=msg_data.get("url", ""),
            source="telegram"
        )

        self.processed_count += 1

        if not signal.is_buyer:
            logger.debug(f"Not a buyer: {text[:50]}...")
            return None

        # ── Enhance with Telegram-specific data ────────────
        # Telegram gives us the sender's phone number directly!
        telegram_phone = msg_data.get("sender_phone", "")
        if telegram_phone and not signal.phone:
            # Format phone number
            if not telegram_phone.startswith("+"):
                telegram_phone = f"+{telegram_phone}"
            signal.phone = telegram_phone

            # Generate WhatsApp link
            clean = telegram_phone.replace("+", "").replace(" ", "")
            signal.whatsapp = f"https://wa.me/{clean}"

        # Use sender name
        sender_name = msg_data.get("sender_name", "")
        if sender_name and signal.buyer_name == "Unknown":
            signal.buyer_name = sender_name

        # ── Build Lead ─────────────────────────────────────
        lead = self._build_telegram_lead(msg_data, signal)

        self.buyer_count += 1
        logger.info(
            f"🎯 BUYER FOUND in @{msg_data.get('group_username', '?')}: "
            f"'{text[:60]}...' "
            f"Score={signal.intent_score} Badge={signal.badge} "
            f"Phone={signal.phone or 'N/A'}"
        )

        try:
            # 5. Save to DB
            # We wrap in list because save_leads_to_db expects a batch
            save_leads_to_db([lead], query_text="telegram_monitor")

            # 6. Notify
            priority = "hot" if signal.intent_score > 0.8 else "normal"
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

    def _build_telegram_lead(self, msg_data: Dict, signal) -> Dict:
        """Build a lead dict from Telegram message data."""
        
        url = msg_data.get("url", "")
        text = msg_data.get("text", "")
        group_name = msg_data.get("group_name", "Telegram Group")
        group_username = msg_data.get("group_username", "")
        sender_username = msg_data.get("sender_username", "")

        # Build contact link
        contact_link = ""
        if sender_username:
            contact_link = f"https://t.me/{sender_username}"
        elif signal.phone:
            clean = signal.phone.replace("+", "").replace(" ", "")
            contact_link = f"https://wa.me/{clean}"

        # WhatsApp message template
        whatsapp_url = ""
        if signal.phone:
            clean = signal.phone.replace("+", "").replace(" ", "")
            if clean.startswith("0"):
                clean = "254" + clean[1:]
            elif not clean.startswith("254"):
                clean = "254" + clean
            whatsapp_url = f"https://wa.me/{clean}"

        # Unique ID
        lead_id = hashlib.md5(f"{url}:{text[:100]}".encode()).hexdigest()[:16]

        ranked_score = round(
            signal.intent_score * 0.4 +
            signal.urgency_score * 0.3 +
            signal.confidence * 0.3,
            2
        )

        return {
            # Core fields
            "id": lead_id,
            "buyer_name": signal.buyer_name,
            "title": text[:200],
            "price": signal.budget or "Contact for Price",
            "location": signal.location or "Kenya",
            "phone": signal.phone,
            "contact_phone": signal.phone,
            "email": signal.email,
            "contact_email": signal.email,
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
            "intent_score": signal.intent_score,
            "intent_strength": signal.intent_score,
            "buyer_match_score": signal.intent_score,
            "confidence": signal.confidence,
            "confidence_score": signal.confidence,
            "urgency_score": signal.urgency_score,
            "ranked_score": ranked_score,
            "rank_score": ranked_score,

            # Display
            "buyer_request_snippet": signal.specific_need[:500],
            "buyer_intent_quote": signal.specific_need[:300],
            "snippet": signal.specific_need[:300],

            # Metadata
            "market_side": "demand",
            "badge": signal.badge,
            "verification_flag": "verified" if signal.phone else "telegram_unverified",
            "intent_type": "BUYER",
            "persona": signal.persona,
            "timeline": signal.timeline,
            "status": "NEW",
            "is_hot_lead": signal.badge == "HOT",

            # WhatsApp
            "whatsapp_url": whatsapp_url,
            "whatsapp_link": whatsapp_url,

            # Timestamps
            "created_at": msg_data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "posted_at": msg_data.get("timestamp"),

            # Score details
            "score_details": signal.score_details,
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
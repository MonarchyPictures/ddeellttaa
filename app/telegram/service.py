# app/telegram/service.py
# ============================================================
# TELEGRAM SERVICE — Main orchestrator
# ============================================================
# Ties everything together:
# Monitor + Processor + GroupManager + Notifier
# Provides simple API for the rest of the app.
# ============================================================

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from .client import TelegramMonitor
from .message_processor import MessageProcessor
from .group_manager import GroupManager
from .notifier import BuyerNotifier, BUYER_NOTIFIER
from .config import TELEGRAM_ENABLED

logger = logging.getLogger(__name__)


class TelegramService:
    """
    High-level Telegram service for the app.
    
    Usage:
        service = TelegramService()
        await service.initialize()
        
        # Search for buyers
        leads = await service.search_buyers("2br kileleshwa", "real_estate")
        
        # Start real-time monitoring
        await service.start_monitoring("2br kileleshwa", "real_estate")
    """

    def __init__(self):
        self.monitor = TelegramMonitor()
        self.processor = MessageProcessor()
        self.group_manager = GroupManager(self.monitor)
        self.notifier = BUYER_NOTIFIER
        self._initialized = False
        self._monitoring = False

        # Register the processor as a message handler
        # When monitor receives a message, processor classifies it
        self.monitor.on_message(self._handle_message)

        # Register notifier with processor
        # When processor finds a buyer, notifier sends alert
        self.processor.on_buyer_found(self._handle_buyer_found)

    @property
    def is_available(self) -> bool:
        return TELEGRAM_ENABLED

    async def initialize(self) -> bool:
        """
        Initialize the Telegram service.
        Must be called before any other operation.
        """
        if not self.is_available:
            logger.warning(
                "Telegram not configured. Add to .env:\n"
                "  TELEGRAM_API_ID=your_id\n"
                "  TELEGRAM_API_HASH=your_hash\n"
                "  TELEGRAM_PHONE=+254712345678"
            )
            return False

        success = await self.monitor.connect()
        if success:
            self._initialized = True
            logger.info("✅ Telegram Service initialized")
        return success

    async def search_buyers(
        self,
        query: str,
        category: str = None,
        hours_back: int = 24,
        max_groups: int = 15
    ) -> List[Dict]:
        """
        Search Telegram groups for buyers.
        This polls recent messages (not real-time).
        
        Args:
            query: What you're selling
            category: Product category (auto-detected if None)
            hours_back: How far back to search
            max_groups: Maximum groups to search
            
        Returns:
            List of buyer lead dicts
        """
        if not self._initialized:
            success = await self.initialize()
            if not success:
                return []

        logger.info(f"🔍 Telegram Search: '{query}' (last {hours_back}h)")

        # 1. Setup relevant groups
        setup_result = await self.group_manager.setup_groups(
            query=query,
            category=category,
            max_groups=max_groups,
            auto_join=True
        )

        logger.info(
            f"Groups: {setup_result['added']} active, "
            f"{setup_result['failed']} failed"
        )

        if setup_result['added'] == 0:
            logger.warning("No groups available for monitoring")
            return []

        # 2. Poll recent messages
        messages = await self.monitor.poll_recent_messages(
            hours_back=hours_back,
            query_filter=query
        )

        logger.info(f"Polled {len(messages)} messages")

        if not messages:
            return []

        # 3. Process through buyer classifier
        leads = await self.processor.process_batch(messages)

        # 4. Sort by score
        leads.sort(
            key=lambda x: x.get("ranked_score", 0),
            reverse=True
        )

        logger.info(
            f"🎯 Found {len(leads)} buyers in Telegram "
            f"(from {len(messages)} messages)"
        )

        return leads

    async def start_monitoring(
        self,
        query: str = None,
        category: str = None,
        max_groups: int = 20
    ):
        """
        Start real-time monitoring of Telegram groups.
        This runs indefinitely until stopped.
        
        Messages are processed in real-time and buyers
        trigger instant notifications.
        """
        if not self._initialized:
            success = await self.initialize()
            if not success:
                return

        # Setup groups
        if query:
            await self.group_manager.setup_groups(
                query=query,
                category=category,
                max_groups=max_groups,
                auto_join=True
            )
        else:
            # Monitor all known groups
            from .config import KENYAN_GROUPS
            for cat, groups in KENYAN_GROUPS.items():
                for group in groups:
                    await self.monitor.add_group(
                        username=group["username"],
                        category=cat,
                        name=group.get("name")
                    )

        self._monitoring = True
        logger.info("🔴 Starting real-time Telegram monitoring...")

        # This blocks until stopped
        await self.monitor.start_realtime_monitor()

    async def stop_monitoring(self):
        """Stop real-time monitoring."""
        self._monitoring = False
        await self.monitor.disconnect()
        logger.info("Telegram monitoring stopped")

    async def _handle_message(self, msg_data: Dict):
        """Called when monitor receives a new message."""
        lead = await self.processor.process_message(msg_data)
        # Lead handling is done via the buyer_found callback

    async def _handle_buyer_found(self, lead: Dict):
        """Called when processor finds a buyer."""
        # Send notification
        await self.notifier.notify(lead, priority="hot" if lead.get("badge") == "HOT" else "normal")

        # Save to database (background)
        try:
            await self._save_lead_to_db(lead)
        except Exception as e:
            logger.error(f"Error saving Telegram lead to DB: {e}")

    async def _save_lead_to_db(self, lead: Dict):
        """Save a Telegram lead to the database."""
        try:
            from app.db.database import SessionLocal
            from app.db import models
            import uuid

            db = SessionLocal()
            try:
                # Check for duplicate
                existing = db.query(models.Lead).filter(
                    models.Lead.url == lead.get("url", "")
                ).first()

                if existing:
                    # Update if better score
                    if lead.get("intent_score", 0) > (existing.intent_score or 0):
                        existing.intent_score = lead["intent_score"]
                        existing.ranked_score = lead.get("ranked_score", 0)
                        db.commit()
                    return

                # Create new lead
                db_lead = models.Lead(
                    id=uuid.uuid4(),
                    buyer_name=lead.get("buyer_name", "Telegram User"),
                    title=lead.get("title", "")[:200],
                    price=lead.get("price"),
                    location=lead.get("location", "Kenya"),
                    source="telegram",
                    url=lead.get("url", ""),
                    intent_score=lead.get("intent_score", 0.5),
                    contact_phone=lead.get("phone"),
                    contact_email=lead.get("email"),
                    buyer_request_snippet=lead.get("buyer_request_snippet", "")[:500],
                    urgency_level=lead.get("badge", "WARM"),
                    confidence_score=lead.get("confidence", 0.5),
                    is_hot_lead=1 if lead.get("badge") == "HOT" else 0,
                    ranked_score=lead.get("ranked_score", 0),
                    intent_type="BUYER",
                    whatsapp_link=lead.get("whatsapp_url"),
                    notes=f"From Telegram: {lead.get('telegram_group_name', '')}"
                )

                db.add(db_lead)
                db.commit()
                logger.info(f"💾 Saved Telegram lead to DB: {lead.get('buyer_name')}")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"DB save error: {e}")

    def get_stats(self) -> Dict:
        """Get combined statistics."""
        return {
            "monitor": self.monitor.get_stats(),
            "processor": self.processor.get_stats(),
            "groups": self.group_manager.get_stats(),
            "notifications_sent": self.notifier.notifications_sent,
            "is_monitoring": self._monitoring
        }


# Singleton
TELEGRAM_SERVICE = TelegramService()
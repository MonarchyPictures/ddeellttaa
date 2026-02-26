# app/telegram/notifier.py
# ============================================================
# NOTIFICATION SERVICE
# ============================================================
# Sends instant alerts when hot buyers are found.
# Supports: Telegram Bot, WebSocket, Database.
# ============================================================

import logging
import os
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Telegram Bot API
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from .config import TELEGRAM_BOT_TOKEN, TELEGRAM_NOTIFY_CHAT_ID, SEND_NOTIFICATIONS


class BuyerNotifier:
    """
    Sends notifications when high-value buyers are found.
    
    Channels:
    1. Telegram Bot message (instant)
    2. WebSocket push to frontend (real-time)
    3. Database notification record (persistent)
    """

    def __init__(self):
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.notify_chat_id = TELEGRAM_NOTIFY_CHAT_ID
        self.websocket_connections = []  # List of active WebSocket connections
        self.notifications_sent = 0

    async def notify(self, lead: Dict[str, Any], priority: str = "normal"):
        """
        Send notification for a buyer lead.
        
        Args:
            lead: The lead dict from MessageProcessor
            priority: "hot", "normal", or "low"
        """
        # Only notify for HOT and WARM leads
        badge = lead.get("badge", "COLD")
        if badge == "COLD" and priority != "hot":
            return

        # ── 1. Telegram Bot Notification ───────────────────
        if SEND_NOTIFICATIONS and HTTPX_AVAILABLE:
            await self._send_telegram_notification(lead)

        # ── 2. WebSocket Push ──────────────────────────────
        await self._push_to_websockets(lead)

        # ── 3. Database Record ─────────────────────────────
        await self._save_notification(lead)

        self.notifications_sent += 1

    async def _send_telegram_notification(self, lead: Dict):
        """Send a formatted notification via Telegram Bot."""
        if not self.bot_token or not self.notify_chat_id:
            return

        badge = lead.get("badge", "COLD")
        badge_emoji = {"HOT": "🔥🔥🔥", "WARM": "🟡", "COLD": "🔵"}.get(badge, "⚪")

        buyer_name = lead.get("buyer_name", "Unknown")
        text = lead.get("buyer_request_snippet", "")[:300]
        phone = lead.get("phone", "")
        location = lead.get("location", "Kenya")
        source = lead.get("source", "Telegram")
        score = lead.get("intent_score", 0)
        budget = lead.get("price", "N/A")
        url = lead.get("url", "")
        whatsapp = lead.get("whatsapp_url", "")
        telegram_user = lead.get("telegram_username", "")
        timeline = lead.get("timeline", "")

        # Build message
        message = (
            f"{badge_emoji} **NEW BUYER ALERT** {badge_emoji}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 **{buyer_name}**\n"
            f"📝 _{text}_\n\n"
            f"💰 Budget: **{budget}**\n"
            f"📍 Location: **{location}**\n"
            f"⏰ Timeline: **{timeline}**\n"
            f"📊 Intent Score: **{score:.0%}**\n"
            f"🏷️ Badge: **{badge}**\n\n"
        )

        # Contact options
        if phone:
            message += f"📞 Phone: `{phone}`\n"
        if whatsapp:
            message += f"💬 [WhatsApp]({whatsapp})\n"
        if telegram_user:
            message += f"✈️ [Telegram](https://t.me/{telegram_user})\n"
        if url:
            message += f"🔗 [Source]({url})\n"

        message += (
            f"\n━━━━━━━━━━━━━━━━━━━━━\n"
            f"📡 Source: {source}\n"
            f"🕐 {datetime.now(timezone.utc).strftime('%H:%M UTC')}"
        )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                    json={
                        "chat_id": self.notify_chat_id,
                        "text": message,
                        "parse_mode": "Markdown",
                        "disable_web_page_preview": True
                    },
                    timeout=10
                )

                if response.status_code == 200:
                    logger.info(f"📨 Telegram notification sent for {buyer_name}")
                else:
                    logger.error(f"Telegram notification failed: {response.text}")

        except Exception as e:
            logger.error(f"Telegram notification error: {e}")

    async def _push_to_websockets(self, lead: Dict):
        """Push lead to all connected WebSocket clients."""
        if not self.websocket_connections:
            return

        message = {
            "type": "new_buyer",
            "data": lead
        }

        disconnected = []
        for ws in self.websocket_connections:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)

        # Clean up disconnected
        for ws in disconnected:
            self.websocket_connections.remove(ws)

    async def _save_notification(self, lead: Dict):
        """Save notification to database."""
        try:
            from app.db.database import SessionLocal
            from app.db import models

            db = SessionLocal()
            try:
                notification = models.Notification(
                    lead_id=None,  # Will link after lead is saved to DB
                    message=(
                        f"New {lead.get('badge', '')} buyer: "
                        f"{lead.get('buyer_name', 'Unknown')} - "
                        f"{lead.get('buyer_request_snippet', '')[:100]}"
                    )
                )
                db.add(notification)
                db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.debug(f"Could not save notification to DB: {e}")

    def register_websocket(self, ws):
        """Register a WebSocket connection for push notifications."""
        self.websocket_connections.append(ws)

    def unregister_websocket(self, ws):
        """Unregister a WebSocket connection."""
        if ws in self.websocket_connections:
            self.websocket_connections.remove(ws)


# Singleton
BUYER_NOTIFIER = BuyerNotifier()
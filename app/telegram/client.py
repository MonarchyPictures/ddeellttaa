# app/telegram/client.py
# ============================================================
# TELEGRAM CLIENT & REAL-TIME MONITOR
# ============================================================
# Core client that connects to Telegram, monitors groups,
# and streams buyer messages in real-time.
# ============================================================

import os
import logging
import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)

# Conditional import
try:
    from telethon import TelegramClient, events
    from telethon.tl.types import (
        Channel, Chat, User,
        MessageMediaPhoto, MessageMediaDocument
    )
    from telethon.tl.functions.channels import JoinChannelRequest
    from telethon.tl.functions.messages import ImportChatInviteRequest
    from telethon.errors import (
        FloodWaitError, ChannelPrivateError,
        ChatAdminRequiredError, UserAlreadyParticipantError,
        InviteHashExpiredError, InviteHashInvalidError
    )
    TELETHON_AVAILABLE = True
except ImportError:
    TELETHON_AVAILABLE = False
    logger.warning("telethon not installed. Run: pip install telethon")

from .config import (
    TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE,
    SESSION_NAME, SESSION_DIR, TELEGRAM_ENABLED,
    MONITOR_INTERVAL_SECONDS, MAX_MESSAGES_PER_CHECK,
    MESSAGE_AGE_LIMIT_HOURS, MIN_DELAY_BETWEEN_GROUPS,
    MAX_GROUPS_PER_CYCLE
)


class TelegramMonitor:
    """
    Real-time Telegram group monitor.
    
    Features:
    - Connects to your Telegram account
    - Monitors multiple groups simultaneously
    - Streams new messages in real-time via event handlers
    - Supports polling mode for historical messages
    - Rate-limit aware (handles FloodWaitError)
    - Fault-tolerant (reconnects automatically)
    """

    def __init__(self):
        self.client: Optional[TelegramClient] = None
        self.connected = False
        self.monitored_groups: Dict[str, Dict] = {}  # username -> group info
        self.message_handlers: List[Callable] = []
        self._running = False

        # Stats
        self.stats = {
            "messages_received": 0,
            "messages_processed": 0,
            "buyers_found": 0,
            "errors": 0,
            "last_message_at": None,
            "started_at": None,
            "groups_monitored": 0
        }

        # Ensure session directory exists
        os.makedirs(SESSION_DIR, exist_ok=True)

    @property
    def is_available(self) -> bool:
        return TELETHON_AVAILABLE and TELEGRAM_ENABLED

    def on_message(self, handler: Callable):
        """Register a callback for new messages."""
        self.message_handlers.append(handler)
        return handler

    async def connect(self) -> bool:
        """Connect to Telegram."""
        if not self.is_available:
            logger.error(
                "Telegram not configured. Set TELEGRAM_API_ID, "
                "TELEGRAM_API_HASH, TELEGRAM_PHONE in .env"
            )
            return False

        try:
            session_path = os.path.join(SESSION_DIR, SESSION_NAME)

            self.client = TelegramClient(
                session_path,
                TELEGRAM_API_ID,
                TELEGRAM_API_HASH,
                # Connection settings for reliability
                connection_retries=5,
                retry_delay=5,
                auto_reconnect=True,
                request_retries=3
            )

            await self.client.start(phone=TELEGRAM_PHONE)

            # Verify connection
            me = await self.client.get_me()
            self.connected = True
            self.stats["started_at"] = datetime.now(timezone.utc).isoformat()

            logger.info(
                f"✅ Telegram connected as: {me.first_name} "
                f"({me.phone})"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Telegram connection failed: {e}")
            self.connected = False
            return False

    async def disconnect(self):
        """Disconnect from Telegram."""
        self._running = False
        if self.client:
            await self.client.disconnect()
            self.connected = False
            logger.info("Telegram disconnected")

    async def join_group(self, username_or_link: str) -> bool:
        """
        Join a Telegram group/channel.
        Supports:
        - @username
        - https://t.me/username
        - https://t.me/+invite_hash (private groups)
        """
        if not self.client or not self.connected:
            return False

        try:
            # Handle invite links
            if "/+" in username_or_link or "joinchat" in username_or_link:
                # Extract invite hash
                if "/+" in username_or_link:
                    invite_hash = username_or_link.split("/+")[-1].strip()
                else:
                    invite_hash = username_or_link.split("/")[-1].strip()

                try:
                    await self.client(ImportChatInviteRequest(invite_hash))
                    logger.info(f"✅ Joined group via invite: {username_or_link}")
                    return True
                except UserAlreadyParticipantError:
                    logger.info(f"Already in group: {username_or_link}")
                    return True
                except (InviteHashExpiredError, InviteHashInvalidError):
                    logger.warning(f"Invalid/expired invite: {username_or_link}")
                    return False

            else:
                # Handle username
                username = username_or_link.replace("https://t.me/", "").replace("@", "").strip()

                try:
                    entity = await self.client.get_entity(username)
                    await self.client(JoinChannelRequest(entity))
                    logger.info(f"✅ Joined group: @{username}")
                    return True
                except UserAlreadyParticipantError:
                    logger.info(f"Already in group: @{username}")
                    return True

        except FloodWaitError as e:
            logger.warning(f"⚠️ Flood wait: {e.seconds}s. Telegram rate limit.")
            await asyncio.sleep(e.seconds)
            return False

        except ChannelPrivateError:
            logger.warning(f"🔒 Group is private: {username_or_link}")
            return False

        except Exception as e:
            logger.error(f"Error joining {username_or_link}: {e}")
            return False

    async def add_group(self, username: str, category: str = "general", name: str = None):
        """Add a group to the monitoring list."""
        self.monitored_groups[username] = {
            "username": username,
            "name": name or username,
            "category": category,
            "added_at": datetime.now(timezone.utc).isoformat(),
            "messages_received": 0,
            "buyers_found": 0,
            "last_message_at": None,
            "entity": None  # Will be resolved on first use
        }
        self.stats["groups_monitored"] = len(self.monitored_groups)

    async def add_groups_by_category(self, category: str):
        """Add all known groups for a category."""
        from .config import KENYAN_GROUPS

        groups = KENYAN_GROUPS.get(category, [])
        if not groups:
            # Fall back to general groups
            groups = KENYAN_GROUPS.get("general", [])

        for group in groups:
            await self.add_group(
                username=group["username"],
                category=category,
                name=group.get("name", group["username"])
            )

        logger.info(f"Added {len(groups)} groups for category '{category}'")

    async def resolve_group_entity(self, username: str):
        """Resolve a group username to a Telegram entity."""
        if not self.client:
            return None

        group_info = self.monitored_groups.get(username, {})

        if group_info.get("entity"):
            return group_info["entity"]

        try:
            entity = await self.client.get_entity(username)
            if username in self.monitored_groups:
                self.monitored_groups[username]["entity"] = entity
            return entity
        except Exception as e:
            logger.error(f"Could not resolve group @{username}: {e}")
            return None

    async def start_realtime_monitor(self):
        """
        Start real-time monitoring using Telegram event handlers.
        This listens for NEW messages as they arrive.
        """
        if not self.client or not self.connected:
            logger.error("Not connected. Call connect() first.")
            return

        # Resolve all group entities
        entities = []
        for username in list(self.monitored_groups.keys()):
            entity = await self.resolve_group_entity(username)
            if entity:
                entities.append(entity)
            else:
                logger.warning(f"Skipping unresolvable group: @{username}")

        if not entities:
            logger.error("No valid groups to monitor!")
            return

        logger.info(f"🔴 LIVE MONITORING {len(entities)} groups...")

        # Register event handler for new messages
        @self.client.on(events.NewMessage(chats=entities))
        async def handler(event):
            try:
                await self._process_event(event)
            except Exception as e:
                logger.error(f"Error processing message event: {e}")
                self.stats["errors"] += 1

        self._running = True
        self.stats["started_at"] = datetime.now(timezone.utc).isoformat()

        logger.info("✅ Real-time monitor started. Listening for buyer messages...")

        # Keep running
        try:
            while self._running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Monitor stopped by user")

    async def poll_recent_messages(
        self,
        hours_back: int = None,
        query_filter: str = None
    ) -> List[Dict]:
        """
        Poll recent messages from all monitored groups.
        Use this for initial data load or catch-up after downtime.
        
        Args:
            hours_back: How many hours back to look (default from config)
            query_filter: Optional keyword to filter messages
            
        Returns:
            List of raw message dicts
        """
        if not self.client or not self.connected:
            logger.error("Not connected")
            return []

        hours = hours_back or MESSAGE_AGE_LIMIT_HOURS
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        all_messages = []

        for username, group_info in list(self.monitored_groups.items()):
            try:
                entity = await self.resolve_group_entity(username)
                if not entity:
                    continue

                logger.info(f"📨 Polling @{username} (last {hours}h)...")

                count = 0
                async for message in self.client.iter_messages(
                    entity,
                    limit=MAX_MESSAGES_PER_CHECK,
                    offset_date=None,  # Start from newest
                    search=query_filter  # Optional keyword filter
                ):
                    # Check age
                    if message.date and message.date.replace(tzinfo=timezone.utc) < cutoff:
                        break

                    if not message.text:
                        continue

                    # Optional query filter (additional check since Telegram search is fuzzy)
                    if query_filter and query_filter.lower() not in message.text.lower():
                        continue

                    msg_data = await self._extract_message_data(message, username, group_info)
                    if msg_data:
                        all_messages.append(msg_data)
                        count += 1

                logger.info(f"  @{username}: {count} messages")

                # Rate limit between groups
                await asyncio.sleep(MIN_DELAY_BETWEEN_GROUPS)

            except FloodWaitError as e:
                logger.warning(f"⚠️ Flood wait: {e.seconds}s")
                await asyncio.sleep(min(e.seconds, 60))

            except ChannelPrivateError:
                logger.warning(f"🔒 Lost access to @{username}")

            except Exception as e:
                logger.error(f"Error polling @{username}: {e}")
                self.stats["errors"] += 1

        logger.info(f"📊 Total polled: {len(all_messages)} messages from {len(self.monitored_groups)} groups")
        return all_messages

    async def _process_event(self, event):
        """Process a real-time message event."""
        message = event.message

        if not message or not message.text:
            return

        self.stats["messages_received"] += 1

        # Determine which group this came from
        chat = await event.get_chat()
        group_username = getattr(chat, 'username', None) or str(chat.id)
        group_name = getattr(chat, 'title', group_username)

        # Build group info
        group_info = self.monitored_groups.get(group_username, {
            "username": group_username,
            "name": group_name,
            "category": "general"
        })

        # Extract message data
        msg_data = await self._extract_message_data(message, group_username, group_info)

        if msg_data:
            self.stats["messages_processed"] += 1
            self.stats["last_message_at"] = datetime.now(timezone.utc).isoformat()

            # Update group stats
            if group_username in self.monitored_groups:
                self.monitored_groups[group_username]["messages_received"] = \
                    self.monitored_groups[group_username].get("messages_received", 0) + 1
                self.monitored_groups[group_username]["last_message_at"] = \
                    datetime.now(timezone.utc).isoformat()

            # Call all registered handlers
            for handler in self.message_handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(msg_data)
                    else:
                        handler(msg_data)
                except Exception as e:
                    logger.error(f"Handler error: {e}")

    async def _extract_message_data(
        self, message, group_username: str, group_info: Dict
    ) -> Optional[Dict]:
        """Extract structured data from a Telegram message."""
        try:
            text = message.text
            if not text or len(text.strip()) < 10:
                return None

            # Get sender information
            sender = await message.get_sender()

            sender_name = ""
            sender_phone = ""
            sender_username = ""

            if sender:
                if isinstance(sender, User):
                    sender_name = f"{sender.first_name or ''} {sender.last_name or ''}".strip()
                    sender_phone = sender.phone or ""
                    sender_username = sender.username or ""
                elif hasattr(sender, 'title'):
                    sender_name = sender.title

            # Build message URL
            msg_url = f"https://t.me/{group_username}/{message.id}"

            # Check for media
            has_media = bool(message.media)
            media_type = None
            if isinstance(message.media, MessageMediaPhoto):
                media_type = "photo"
            elif isinstance(message.media, MessageMediaDocument):
                media_type = "document"

            return {
                # Core fields
                "text": text,
                "source": "telegram",
                "url": msg_url,
                "timestamp": message.date.isoformat() if message.date else datetime.now(timezone.utc).isoformat(),

                # Sender info
                "sender_name": sender_name,
                "sender_phone": sender_phone,
                "sender_username": sender_username,
                "sender_id": sender.id if sender else None,

                # Group info
                "group_username": group_username,
                "group_name": group_info.get("name", group_username),
                "group_category": group_info.get("category", "general"),

                # Message metadata
                "message_id": message.id,
                "has_media": has_media,
                "media_type": media_type,
                "reply_to": message.reply_to_msg_id if message.reply_to else None,
                "views": getattr(message, 'views', None),
                "forwards": getattr(message, 'forwards', None)
            }

        except Exception as e:
            logger.error(f"Error extracting message data: {e}")
            return None

    def get_stats(self) -> Dict:
        """Return monitoring statistics."""
        return {
            **self.stats,
            "groups": {
                username: {
                    "name": info.get("name"),
                    "category": info.get("category"),
                    "messages": info.get("messages_received", 0),
                    "buyers": info.get("buyers_found", 0),
                    "last_message": info.get("last_message_at")
                }
                for username, info in self.monitored_groups.items()
            }
        }
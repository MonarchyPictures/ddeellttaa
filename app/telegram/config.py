# app/telegram/config.py
# ============================================================
# TELEGRAM CONFIGURATION
# ============================================================
# 
# HOW TO GET CREDENTIALS:
# 1. Go to https://my.telegram.org/apps
# 2. Log in with your phone number
# 3. Create a new application
# 4. Copy api_id and api_hash
# 5. Add to your .env file
#
# HOW TO GET BOT TOKEN (Optional, for notifications):
# 1. Message @BotFather on Telegram
# 2. Send /newbot
# 3. Follow instructions
# 4. Copy the token
# ============================================================

import os
import logging

logger = logging.getLogger(__name__)

# Core credentials
try:
    TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
except ValueError:
    TELEGRAM_API_ID = 0
    logger.warning("TELEGRAM_API_ID in .env is not a valid integer. Defaulting to 0.")

TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE", "")  # Your phone number with country code

# Bot token (for sending notifications)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_NOTIFY_CHAT_ID = os.getenv("TELEGRAM_NOTIFY_CHAT_ID", "")  # Your personal chat ID

# Session file location
SESSION_NAME = os.getenv("TELEGRAM_SESSION_NAME", "delta9_telegram")
SESSION_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "sessions")

# Monitoring settings
MONITOR_INTERVAL_SECONDS = int(os.getenv("TELEGRAM_MONITOR_INTERVAL", "30"))
MAX_MESSAGES_PER_CHECK = int(os.getenv("TELEGRAM_MAX_MESSAGES", "100"))
MESSAGE_AGE_LIMIT_HOURS = int(os.getenv("TELEGRAM_MESSAGE_AGE_HOURS", "24"))

# Rate limiting
MIN_DELAY_BETWEEN_GROUPS = 1.0  # seconds
MAX_GROUPS_PER_CYCLE = 50

# Feature flags
TELEGRAM_ENABLED = bool(TELEGRAM_API_ID and TELEGRAM_API_HASH and TELEGRAM_PHONE)
AUTO_JOIN_GROUPS = os.getenv("TELEGRAM_AUTO_JOIN", "false").lower() == "true"
SEND_NOTIFICATIONS = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_NOTIFY_CHAT_ID)

if TELEGRAM_ENABLED:
    logger.info("âœ… Telegram Monitor: ENABLED")
else:
    logger.warning(
        "âš ï¸ Telegram Monitor: DISABLED. "
        "Set TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE in .env"
    )


def get_telegram_config_report() -> dict:
    """
    Safe runtime validation report (no secrets exposed).
    """
    missing = []
    if not TELEGRAM_API_ID:
        missing.append("TELEGRAM_API_ID")
    if not TELEGRAM_API_HASH:
        missing.append("TELEGRAM_API_HASH")
    if not TELEGRAM_PHONE:
        missing.append("TELEGRAM_PHONE")

    bot_missing = []
    if not TELEGRAM_BOT_TOKEN:
        bot_missing.append("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_NOTIFY_CHAT_ID:
        bot_missing.append("TELEGRAM_NOTIFY_CHAT_ID")

    return {
        "enabled": TELEGRAM_ENABLED,
        "core_credentials_present": len(missing) == 0,
        "missing_core": missing,
        "bot_notifications_ready": len(bot_missing) == 0,
        "missing_bot": bot_missing,
        "session_name": SESSION_NAME,
        "monitor_interval_seconds": MONITOR_INTERVAL_SECONDS
    }


# â”€â”€ KNOWN KENYAN GROUPS DATABASE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# These are real, active groups where Kenyans post buyer requests.
# Categories help match groups to user queries.
# 
# To find more groups:
# 1. Search Telegram for "Kenya" + your category
# 2. Use https://t.me/s/ search
# 3. Ask in existing groups for recommendations

KENYAN_GROUPS = {
    # Keep a minimal known seed set; runtime discovery adds fresh valid groups per query.
    "real_estate": [
        {"username": "KenyaMarket", "name": "Kenya Market", "members": "seed"}
    ],
    "vehicles": [],
    "electronics": [],
    "general": [
        {"username": "KenyaMarket", "name": "Kenya Market", "members": "seed"}
    ],
    "services": [],
    "agriculture": [],
    "fashion": [],
    "construction": []
}
# Flatten all groups into a single list for discovery
ALL_GROUPS = []
for category, groups in KENYAN_GROUPS.items():
    for group in groups:
        group["category"] = category
        ALL_GROUPS.append(group)


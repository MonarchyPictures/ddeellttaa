# app/config/runtime.py
# ============================================================
# DELTA-9 RUNTIME CONFIGURATION — SINGLE SOURCE OF TRUTH
# ============================================================

import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# --- MODE ---
HIGH_RECALL_MODE = True
PROD_STRICT = False

# --- THRESHOLDS (RELAXED FOR MORE LEADS) ---
INTENT_THRESHOLD = 0.05          # Very low to catch everything
MIN_INTENT_SCORE = INTENT_THRESHOLD
INTENT_POINTS_FLOOR = 5          # Was 10, now 5 (0-100 scale)
CONFIDENCE_FLOOR = 0.04          # Dropped to show more leads
REQUIRE_FIRST_PERSON = False     # Don't require "I" or "my"
REQUIRE_BUYER_KEYWORD = False    # Don't require "looking for"
REQUIRE_VERIFICATION = False

# --- SCRAPER PRIORITY LIST ---
# Higher number = runs first, gets more trust
# This is the MASTER priority list for the entire app
SCRAPER_PRIORITIES = {
    # TIER 1: Premium APIs (Highest priority, most reliable)
    "serpapi":          1000,
    "serpapi_google":   1000,
    "google_cse":       950,

    # TIER 2: Telegram (Real-time, highest quality buyers)
    "telegram":         900,
    "telegram_groups":  900,

    # TIER 3: Direct Platform Scrapers (Good quality)
    "facebook_groups":  800,
    "facebook":         750,
    "kenyan_forums":    700,
    "twitter_buyers":   650,
    "twitter":          650,

    # TIER 4: Marketplace Scrapers (Mixed buyer/seller)
    "jiji":             500,
    "pigiame":          500,

    # TIER 5: Maps & WhatsApp (Business/group discovery)
    "google_maps":      400,
    "whatsapp_groups":  350,
    "whatsapp":         350,

    # TIER 6: General Search (Lowest priority, fallback)
    "duckduckgo":       100,
}

# Source reliability scores (used in confidence calculation)
# Higher = more trusted source
SOURCE_RELIABILITY = {
    "serpapi_google":   0.95,
    "google_cse":       0.90,
    "telegram":         0.95,
    "telegram_groups":  0.95,
    "facebook_groups":  0.80,
    "facebook":         0.75,
    "KenyaTalk":        0.85,
    "Wazua":            0.85,
    "kenyan_forums":    0.80,
    "twitter":          0.70,
    "jiji.co.ke":       0.70,
    "jiji":             0.70,
    "pigiame":          0.70,
    "google_maps":      0.65,
    "whatsapp":         0.60,
    "duckduckgo":       0.50,
}

# Scraper timeout by tier (premium APIs get more time)
SCRAPER_TIMEOUTS = {
    "serpapi":          30,
    "serpapi_google":   30,
    "google_cse":       20,
    "telegram":         25,
    "telegram_groups":  25,
    "facebook_groups":  10,
    "facebook":         10,
    "kenyan_forums":    10,
    "twitter_buyers":   10,
    "twitter":          10,
    "jiji":             15,
    "pigiame":          15,
    "google_maps":      15,
    "whatsapp_groups":  10,
    "whatsapp":         10,
    "duckduckgo":       10,
}

# Max results per scraper (premium gets more)
SCRAPER_MAX_RESULTS = {
    "serpapi":          50,
    "serpapi_google":   50,
    "google_cse":       30,
    "telegram":         100,
    "telegram_groups":  100,
    "facebook_groups":  40,
    "facebook":         30,
    "kenyan_forums":    30,
    "twitter_buyers":   25,
    "twitter":          25,
    "jiji":             20,
    "pigiame":          20,
    "google_maps":      15,
    "whatsapp_groups":  15,
    "whatsapp":         15,
    "duckduckgo":       20,
}

# --- KENYA LOCKING ---
KENYA_ONLY = True
DEFAULT_LOCATION = "Kenya"
ALLOWED_LOCATIONS = [
    "kenya", "nairobi", "mombasa", "kisumu", "nakuru", "eldoret",
    "thika", "kitengela", "ruiru", "karen", "kilimani", "westlands",
    "kiambu", "machakos", "kajiado", "rongai", "juja", "ruaka",
    "syokimau", "langata", "south b", "south c", "cbd"
]

# --- API KEYS ---
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
SERPAPI_ENGINE = os.getenv("SERPAPI_ENGINE", "google")
SERPAPI_REGION = os.getenv("SERPAPI_REGION", "ke")
SERPAPI_LANGUAGE = os.getenv("SERPAPI_LANGUAGE", "en")
GOOGLE_CSE_API_KEY = os.getenv("GOOGLE_CSE_API_KEY", "")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID", "")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./intent_radar_v3.db")
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")

# --- FEATURE FLAGS ---
ENABLE_CELERY = False            # Direct processing, no queue blocking
ENABLE_TELEGRAM = True
ENABLE_SPECIAL_OPS = False
ENABLE_AI_EXTRACTION = True
ENABLE_SMART_MATCHING = True
SCRAPER_TIMEOUT = 15
MAX_RESULTS_PER_SCRAPER = 25
ENABLE_PLAYWRIGHT = True

# ============================================================
# INTERNAL ENGINE WEIGHTS (Preserved for compatibility)
# ============================================================

# --- CONFIDENCE WEIGHTS ---
CONFIDENCE_WEIGHT_INTENT = 0.5
CONFIDENCE_WEIGHT_URGENCY = 0.3
CONFIDENCE_WEIGHT_SOURCE = 0.2

# --- INTENT SCORING ---
INTENT_BASE_SCORE = 0.3
INTENT_WEIGHT_HIGH = 0.12
INTENT_WEIGHT_MEDIUM = 0.06
INTENT_WEIGHT_NEGATIVE = 0.15
INTENT_WEIGHT_PHONE = 0.1
INTENT_WEIGHT_BUDGET = 0.1
INTENT_WEIGHT_QUESTION = 0.05

# --- ALIASES ---
SOURCE_WEIGHTS = SOURCE_RELIABILITY
SOURCE_RELIABILITY_DEFAULT = 0.7

from app.config.runtime import INTENT_THRESHOLD, PROD_STRICT

# 🚦 Intelligence Thresholds
# Global floors for production stability.

# Non-negotiable thresholds
STRICT_PUBLIC = 0.4  # Lowered to 0.4 for broader lead inclusion
HIGH_INTENT   = 0.6
BOOTSTRAP     = 0.3
FLOOR         = 0.35  # Relaxed floor to match default intent threshold

# Operational windows
FRESHNESS_WINDOW_HOURS = 72
URGENT_FRESHNESS_HOURS = 24

# Legacy aliases (for backward compatibility)
MATCH_SCORE_THRESHOLD = STRICT_PUBLIC
HOT_LEAD_THRESHOLD = HIGH_INTENT

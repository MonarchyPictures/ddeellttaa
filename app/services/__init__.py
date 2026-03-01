# app/services/__init__.py
"""
Services module for Delta9 lead generation platform.
"""

# Kenya-optimized scoring (new structure)
from .scoring import (
    calculate_final_score,
    score_lead_kenya,
    MIN_ACCEPTABLE_SCORE,
    KENYA_INTENT_THRESHOLD,
)

__all__ = [
    "calculate_final_score",
    "score_lead_kenya",
    "MIN_ACCEPTABLE_SCORE",
    "KENYA_INTENT_THRESHOLD",
]

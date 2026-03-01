# app/services/scoring/__init__.py
"""
Kenya-optimized lead scoring module.

Usage:
    from app.services.scoring import calculate_final_score, MIN_ACCEPTABLE_SCORE
    
    score = calculate_final_score(
        text="Natafuta pipes budget 50k",
        platform="telegram",
        age_hours=12
    )
    
    if score >= MIN_ACCEPTABLE_SCORE:
        print(f"Lead qualified with score: {score}")
"""

from .intent_model import score_intent_signal, STRONG_SIGNALS, MEDIUM_SIGNALS, WEAK_SIGNALS
from .budget_detector import score_budget
from .urgency_detector import score_urgency
from .location_detector import score_location, KENYA_LOCATIONS
from .platform_detector import score_platform_reliability
from .recency_detector import score_recency
from .lead_scorer import (
    KenyaLeadScorer,
    calculate_final_score,
    score_lead_kenya,
    MIN_ACCEPTABLE_SCORE,
    KENYA_INTENT_THRESHOLD
)

__all__ = [
    # Component scorers
    "score_intent_signal",
    "score_budget",
    "score_urgency",
    "score_location",
    "score_platform_reliability",
    "score_recency",
    # Constants
    "STRONG_SIGNALS",
    "MEDIUM_SIGNALS",
    "WEAK_SIGNALS",
    "KENYA_LOCATIONS",
    "MIN_ACCEPTABLE_SCORE",
    "KENYA_INTENT_THRESHOLD",
    # Main functions
    "calculate_final_score",
    "score_lead_kenya",
    "KenyaLeadScorer",
]

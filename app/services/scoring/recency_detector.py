# app/services/scoring/recency_detector.py
"""
Recency Score (Weight: 5%)

Fresher leads are better.
"""


def score_recency(hours_old: int = 0) -> float:
    """
    Score recency (0.0 to 1.0).
    
    Recency scoring:
    - Within 24 hours: 1.0
    - Within 7 days: 0.7
    - Older: 0.3
    """
    if hours_old < 24:
        return 1.0
    if hours_old < 168:  # 7 days
        return 0.7
    return 0.3

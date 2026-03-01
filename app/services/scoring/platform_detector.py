# app/services/scoring/platform_detector.py
"""
Platform Reliability Score (Weight: 5%)

Higher trust platforms get higher scores.
"""


def score_platform_reliability(source: str) -> float:
    """
    Score platform reliability (0.0 to 1.0).
    
    Platform reliability:
    - facebook group: 1.0
    - telegram group: 0.9
    - jiji: 0.8
    - pigiame: 0.8
    - twitter: 0.6
    - unknown: 0.4
    """
    source_lower = (source or "").lower()
    
    if "facebook" in source_lower:
        return 1.0
    if "telegram" in source_lower:
        return 0.9
    if "jiji" in source_lower:
        return 0.8
    if "pigiame" in source_lower:
        return 0.8
    if "twitter" in source_lower:
        return 0.6
    
    return 0.4

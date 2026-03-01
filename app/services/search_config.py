# app/services/search_config.py
"""
Search configuration with different thresholds for Fast vs Deep mode.

Fast Mode: Adaptive - tries 0.35, then 0.25, then 0.10
Deep Mode: Discover hidden buyers (0.22)
"""

from dataclasses import dataclass
from typing import List


@dataclass
class SearchConfig:
    """Configuration for search modes."""
    
    # Intent thresholds - SINGLE SOURCE OF TRUTH
    # Adaptive thresholds for fast mode (high → medium → low)
    FAST_INTENT_THRESHOLD_HIGH: float = 0.15   # First attempt: high quality
    FAST_INTENT_THRESHOLD_MED: float = 0.25    # Second attempt: medium quality
    FAST_INTENT_THRESHOLD_LOW: float = 0.10    # Final attempt: relaxed quality
    
    # Legacy alias for backward compatibility
    FAST_INTENT_THRESHOLD: float = 0.15
    DEEP_INTENT_THRESHOLD: float = 0.22
    
    # Minimum safety: must have at least one buyer intent signal
    MIN_INTENT_SIGNAL_REQUIRED: bool = True
    
    # Timeouts
    FAST_TIMEOUT_SECONDS: int = 8
    DEEP_TIMEOUT_SECONDS: int = 300  # 5 minutes for deep search
    
    # Query limits
    FAST_MAX_QUERIES: int = 2
    DEEP_MAX_QUERIES: int = 6
    
    # Scraper limits
    FAST_MAX_SCRAPERS: int = 4
    DEEP_MAX_SCRAPERS: int = 7
    
    # Early stopping
    FAST_EARLY_STOP_LEADS: int = 20
    DEEP_TARGET_LEADS: int = 50
    
    # Concurrency
    MAX_CONCURRENCY: int = 4
    
    # Cache
    FAST_CACHE_TTL: int = 300  # 5 minutes


# Global config instance
SEARCH_CONFIG = SearchConfig()


def get_intent_threshold(mode: str) -> float:
    """Get intent threshold based on search mode."""
    if mode == "fast":
        return SEARCH_CONFIG.FAST_INTENT_THRESHOLD
    elif mode == "deep":
        return SEARCH_CONFIG.DEEP_INTENT_THRESHOLD
    return SEARCH_CONFIG.FAST_INTENT_THRESHOLD


def get_adaptive_thresholds() -> List[float]:
    """
    Get adaptive thresholds for progressive fallback.
    
    Returns thresholds from strict to relaxed:
    [0.35, 0.25, 0.10]
    
    This ensures:
    1. High-quality results first (0.35)
    2. Only relax if empty (0.25, then 0.10)
    3. No permanent low-quality flood
    """
    return [
        SEARCH_CONFIG.FAST_INTENT_THRESHOLD_HIGH,   # 0.35 - premium
        SEARCH_CONFIG.FAST_INTENT_THRESHOLD_MED,    # 0.25 - standard
        SEARCH_CONFIG.FAST_INTENT_THRESHOLD_LOW,    # 0.10 - relaxed
    ]


def should_accept_lead(intent_score: float, has_intent_signals: bool, threshold: float) -> bool:
    """
    Safety check for lead acceptance.
    
    Protects against garbage flood by requiring:
    1. Score meets threshold: intent_score >= threshold
    2. Has actual intent signals: has_intent_signals == True
    
    Args:
        intent_score: Calculated intent score (0.0-1.0)
        has_intent_signals: Whether any buyer keywords were detected
        threshold: Minimum score threshold
    
    Returns:
        True if lead should be accepted
    """
    if not has_intent_signals:
        return False
    return intent_score >= threshold

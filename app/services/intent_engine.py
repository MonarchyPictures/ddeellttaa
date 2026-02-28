# app/services/intent_engine.py
# ============================================================
# INTENT ENGINE — Enhanced with more signals
# ============================================================

from app.config.runtime import (
    INTENT_BASE_SCORE, INTENT_WEIGHT_HIGH, INTENT_WEIGHT_MEDIUM,
    INTENT_WEIGHT_NEGATIVE, INTENT_WEIGHT_PHONE, INTENT_WEIGHT_BUDGET,
    INTENT_WEIGHT_QUESTION
)

HIGH_INTENT_TERMS = [
    "urgent", "asap", "today", "immediately", "ready to buy", "cash buyer",
    "need now", "looking for", "want to buy", "natafuta", "nahitaji",
    "anyone selling", "who sells", "where can i buy", "wtb",
    "serious buyer", "cash ready", "budget", "buying"
]

MEDIUM_INTENT_TERMS = [
    "interested", "planning", "considering", "thinking about",
    "price", "cost", "how much", "recommendations", "suggest",
    "options", "alternatives", "compare"
]

NEGATIVE_TERMS = [
    "selling", "for sale", "we offer", "our store", "buy from us",
    "official dealer", "visit our"
]


def calculate_intent_score(text: str) -> float:
    """
    Calculate intent score (0.0 - 1.0) based on text signals.
    Enhanced with more terms and negative filtering.
    """
    if not text:
        return INTENT_BASE_SCORE  # Base score for any content

    text_lower = text.lower()
    score = INTENT_BASE_SCORE  # Base score

    # Negative signals (reduce score)
    for term in NEGATIVE_TERMS:
        if term in text_lower:
            score -= INTENT_WEIGHT_NEGATIVE

    # High intent signals
    high_hits = []
    for term in HIGH_INTENT_TERMS:
        if term in text_lower:
            score += INTENT_WEIGHT_HIGH
            high_hits.append(term)

    # Medium intent signals
    for term in MEDIUM_INTENT_TERMS:
        if term in text_lower:
            score += INTENT_WEIGHT_MEDIUM

    # Question marks suggest inquiry (buyer behavior)
    if "?" in text:
        score += INTENT_WEIGHT_QUESTION

    # Phone number present = high engagement
    import re
    if re.search(r'(\+254|07)\d{8}', text):
        score += INTENT_WEIGHT_PHONE

    # Budget/price mention
    if re.search(r'\b\d+\s*(k|m|ksh|kes)\b', text_lower):
        score += INTENT_WEIGHT_BUDGET

    final_score = max(0.0, min(score, 1.0))
    print(f"[INTENT_ENGINE] Text: '{text[:50]}...' | Score: {final_score:.2f} | High hits: {high_hits}", flush=True)
    return final_score
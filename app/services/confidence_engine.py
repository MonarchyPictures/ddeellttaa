# app/services/confidence_engine.py
# ============================================================
# CONFIDENCE ENGINE — Lowered floor to show more leads
# ============================================================

from app.config.runtime import SOURCE_RELIABILITY, CONFIDENCE_FLOOR


def calculate_confidence(
    intent_score_or_text=0.5,
    urgency_score_or_source=0.3,
    source_reliability: float = None
) -> float:
    """
    Calculate confidence score (0.0 - 1.0).
    
    Supports two calling conventions:
    1. calculate_confidence(0.8, 0.7, 0.9)  — numeric
    2. calculate_confidence("text here", "source_name")  — legacy string
    
    FLOOR: Returns at least CONFIDENCE_FLOOR (0.04) for any non-empty input.
    """
    # Handle legacy string arguments
    if isinstance(intent_score_or_text, str):
        from app.services.intent_engine import calculate_intent_score
        from app.services.urgency_ranker import calculate_urgency_score

        text = intent_score_or_text
        source_name = str(urgency_score_or_source).lower()

        intent_score = calculate_intent_score(text)
        urgency_score = calculate_urgency_score(text)
        source_rel = SOURCE_RELIABILITY.get(source_name, 0.5)
    else:
        intent_score = float(intent_score_or_text)
        urgency_score = float(urgency_score_or_source)
        source_rel = source_reliability if source_reliability is not None else 0.5

    # Weighted formula
    # Intent: 50%, Urgency: 30%, Source: 20%
    score = (intent_score * 0.5) + (urgency_score * 0.3) + (source_rel * 0.2)

    # Apply floor — never return below CONFIDENCE_FLOOR for any content
    score = max(score, CONFIDENCE_FLOOR)
    
    final_score = min(score, 0.99)
    print(f"[CONFIDENCE_ENGINE] Intent: {intent_score:.2f} | Urgency: {urgency_score:.2f} | Source: {source_rel:.2f} | Final: {final_score:.2f}")
    
    return final_score
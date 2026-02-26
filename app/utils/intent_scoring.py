import re
import logging
from typing import Tuple, List, Dict, Any
from app.config.runtime import INTENT_THRESHOLD

# Use the robust NLP service (Singleton pattern via module variable)
from ..nlp.intent_service import BuyingIntentNLP

logger = logging.getLogger(__name__)

# Global singleton to avoid reloading spaCy model on every request
_nlp_engine = None

def get_nlp_engine():
    global _nlp_engine
    if _nlp_engine is None:
        _nlp_engine = BuyingIntentNLP()
    return _nlp_engine

class IntentScorer:
    def __init__(self):
        self.engine = get_nlp_engine()
        
    def calculate_intent_score(self, text: str) -> float:
        """Calculate intent score from 0.0 to 1.0 using the NLP Engine."""
        if not text:
            return 0.0
        return self.engine.calculate_intent_score(text)

    def analyze_readiness(self, text: str) -> Tuple[str, float]:
        """
        Classify Buyer Readiness using NLP Engine.
        Returns: (readiness_level, score_out_of_10)
        """
        if not text:
            return "RESEARCHING", 0.0
        return self.engine.analyze_readiness(text)

    def validate_lead(self, text: str) -> bool:
        """
        Strict validation of whether the text represents a buyer.
        Delegates to NLP Engine's classification.
        """
        if not text:
            return False
            
        classification = self.engine.classify_intent(text)
        
        if classification == "BUYER":
            return True
            
        if classification == "SELLER":
            logger.info(f"validate_lead: Soft Flagged as SELLER (will be ingested with low confidence): {text[:50]}...")
            return True  # Soft flagging: allow ingestion but it will be scored low/flagged elsewhere
            
        # If UNCLEAR, we accept it (soft flagging handles quality downstream)
        # We rely on confidence_score and intent_type fields on the Lead model
        return True

    def validate_lead_debug(self, text: str) -> Dict[str, Any]:
        """Debug version of validate_lead that returns reasons."""
        if not text:
            return {"valid": False, "reasons": ["Empty text"], "score": 0.0}
            
        classification = self.engine.classify_intent(text)
        score = self.calculate_intent_score(text)
        
        reasons = []
        if classification != "BUYER":
            reasons.append(f"Classified as {classification}")
            
        if classification == "UNCLEAR" and score < INTENT_THRESHOLD:
            reasons.append(f"Score {score} below rescue threshold {INTENT_THRESHOLD}")
            
        if classification == "SELLER":
            reasons.append("Soft Flagged for SELLER intent (Low Confidence)")
            
        return {
            "valid": True, # Always valid for ingestion (soft flagging)
            "score": score,
            "reasons": reasons,
            "classification": classification
        }

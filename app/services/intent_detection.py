"""
Intent Detection & Scoring Service
Analyzes content to detect buying intent
"""
import re
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class IntentResult:
    """Result of intent analysis"""
    intent_score: float  # 0-1
    intent_category: str  # buying, researching, complaining, etc.
    buying_urgency: str  # immediate, soon, future
    keywords_matched: List[str]
    confidence: float  # 0-1


class IntentDetectionService:
    """
    Detects buying intent in text content.
    Uses keyword matching and scoring algorithms.
    """
    
    # High-intent keywords (strong buying signals)
    HIGH_INTENT_KEYWORDS = [
        "buy", "purchase", "order", "get", "need", "want",
        "looking for", "searching for", "recommend", "suggest",
        "quote", "pricing", "cost", "budget", "affordable",
        "hire", "pay", "spend", "invest", "purchase",
        "asap", "urgent", "immediately", "today", "now",
        "contact", "reach out", "dm", "message", "call",
    ]
    
    # Medium-intent keywords (researching)
    MEDIUM_INTENT_KEYWORDS = [
        "compare", "vs", "versus", "alternatives", "options",
        "review", "reviews", "rating", "rated", "best",
        "good", "quality", "reliable", "trustworthy",
        "considering", "thinking about", "interested in",
        "learn more", "information", "details",
    ]
    
    # Low-intent keywords (general discussion)
    LOW_INTENT_KEYWORDS = [
        "what is", "how does", "why", "opinion", "thoughts",
        "experience", "using", "used", "have", "had",
    ]
    
    # Urgency indicators
    URGENCY_PATTERNS = {
        "immediate": ["asap", "urgent", "immediately", "today", "now", "emergency", "rush"],
        "soon": ["this week", "soon", "quickly", "fast", "shortly", "couple days"],
        "future": ["next month", "later", "eventually", "someday", "considering"],
    }
    
    # Negative patterns (false positives)
    NEGATIVE_PATTERNS = [
        r"i (am|was) a \w+",  # "I am a plumber" (not looking for one)
        r"i work as",
        r"my company",
        r"we offer",
        r"we provide",
        r"for sale",
        r"selling",
        r"vendor",  # Often vendors posing as buyers
    ]
    
    # Contact info patterns (high value signal)
    CONTACT_PATTERNS = {
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "phone": r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        "dm_request": r'(dm me|message me|send me a dm|inbox|private message)',
    }
    
    def __init__(self):
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for efficiency"""
        self.negative_regex = [re.compile(p, re.IGNORECASE) for p in self.NEGATIVE_PATTERNS]
        self.contact_regex = {k: re.compile(v, re.IGNORECASE) for k, v in self.CONTACT_PATTERNS.items()}
    
    def analyze(self, text: str, query: str = "") -> IntentResult:
        """
        Analyze text for buying intent.
        
        Args:
            text: The content to analyze
            query: The search query that matched (for context)
            
        Returns:
            IntentResult with scores and classification
        """
        text_lower = text.lower()
        words = set(text_lower.split())
        
        # Check for negative patterns first (vendor/false positive detection)
        if self._is_likely_vendor(text):
            return IntentResult(
                intent_score=0.0,
                intent_category="vendor",
                buying_urgency="none",
                keywords_matched=[],
                confidence=0.9
            )
        
        # Count keyword matches
        high_matches = [kw for kw in self.HIGH_INTENT_KEYWORDS if kw in text_lower]
        medium_matches = [kw for kw in self.MEDIUM_INTENT_KEYWORDS if kw in text_lower]
        low_matches = [kw for kw in self.LOW_INTENT_KEYWORDS if kw in text_lower]
        
        # Calculate base intent score
        score = (
            len(high_matches) * 0.25 +
            len(medium_matches) * 0.10 +
            len(low_matches) * 0.02
        )
        
        # Boost score for contact info
        contact_info = self._extract_contact_signals(text)
        if contact_info:
            score += 0.15 * len(contact_info)
        
        # Boost for question marks (asking for help/recommendations)
        if "?" in text:
            score += 0.1
        
        # Boost for first-person pronouns (personal need)
        first_person = ["i ", "my ", "me ", "we ", "our "]
        if any(fp in text_lower for fp in first_person):
            score += 0.1
        
        # Determine urgency
        urgency = self._detect_urgency(text_lower)
        if urgency == "immediate":
            score += 0.2
        elif urgency == "soon":
            score += 0.1
        
        # Cap score at 1.0
        score = min(score, 1.0)
        
        # Determine category
        category = self._classify_intent(score, high_matches, medium_matches)
        
        # Calculate confidence based on text length and matches
        confidence = min((len(high_matches) + len(medium_matches)) / 3, 1.0)
        if len(text) < 20:  # Very short text
            confidence *= 0.5
        
        return IntentResult(
            intent_score=round(score, 3),
            intent_category=category,
            buying_urgency=urgency,
            keywords_matched=high_matches + medium_matches,
            confidence=round(confidence, 3)
        )
    
    def _is_likely_vendor(self, text: str) -> bool:
        """Check if text is likely from a vendor/seller"""
        return any(pattern.search(text) for pattern in self.negative_regex)
    
    def _detect_urgency(self, text: str) -> str:
        """Detect urgency level from text"""
        for level, keywords in self.URGENCY_PATTERNS.items():
            if any(kw in text for kw in keywords):
                return level
        return "unknown"
    
    def _extract_contact_signals(self, text: str) -> List[str]:
        """Extract contact information signals"""
        signals = []
        for name, pattern in self.contact_regex.items():
            if pattern.search(text):
                signals.append(name)
        return signals
    
    def _classify_intent(self, score: float, high: List, medium: List) -> str:
        """Classify the type of intent"""
        if score >= 0.6:
            return "buying"
        elif score >= 0.4:
            return "strong_interest"
        elif score >= 0.2:
            return "researching"
        elif high or medium:
            return "mild_interest"
        else:
            return "discussion"
    
    def is_high_intent(self, text: str, threshold: float = 0.5) -> bool:
        """Quick check if text has high buying intent"""
        result = self.analyze(text)
        return result.intent_score >= threshold and result.confidence >= 0.5


# Singleton
_intent_service = None


def get_intent_service() -> IntentDetectionService:
    """Get or create the intent detection service"""
    global _intent_service
    if _intent_service is None:
        _intent_service = IntentDetectionService()
    return _intent_service

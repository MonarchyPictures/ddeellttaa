"""
Intent Detection AI
Filters for true buyer intent with 0-1 probability scoring
"""
import re
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class IntentResult:
    """Result of intent analysis"""
    intent_score: float  # 0-1 buyer probability
    intent_category: str  # buying, researching, vendor, discussion
    buying_urgency: str  # immediate, soon, future, none
    keywords_matched: List[str]
    confidence: float  # 0-1 confidence in the score
    is_buyer: bool  # True if intent_score >= 0.5


class IntentDetectionService:
    """
    AI-powered Intent Detection
    
    Scores text for buyer intent (0-1 probability)
    Filters out vendors, spammers, and irrelevant content
    """
    
    # HIGH INTENT - Strong buying signals (weight: 0.25 each)
    HIGH_INTENT_KEYWORDS = [
        # Direct need
        "need", "i need", "we need",
        "looking for", "searching for", "trying to find",
        "want", "i want", "we want",
        
        # Urgency
        "asap", "urgently", "urgent", "immediately",
        "today", "this week", "right now",
        
        # Hiring/Purchasing
        "hire", "looking to hire", "want to hire",
        "buy", "looking to buy", "want to buy",
        "purchase", "order", "get",
        
        # Recommendations
        "recommend", "recommendation", "suggest",
        "any good", "best", "top rated",
        "who is the best", "who's the best",
        
        # Quotes/Pricing
        "quote", "pricing", "how much",
        "cost", "price", "budget",
        "affordable", "cheap", "reasonable price",
        
        # Contact intent
        "dm me", "message me", "contact me",
        "reach out", "call me", "email me",
    ]
    
    # MEDIUM INTENT - Researching (weight: 0.10 each)
    MEDIUM_INTENT_KEYWORDS = [
        # Research
        "compare", "vs", "versus", "alternatives",
        "review", "reviews", "rating", "rated",
        "experience with", "used", "using",
        
        # Interest
        "interested in", "considering", "thinking about",
        "learn more", "information about",
        "help with", "advice on",
        
        # Questions
        "where can i get", "where to find",
        "who provides", "who offers",
        "how do i", "what's the best",
    ]
    
    # LOW INTENT - General discussion (weight: 0.02 each)
    LOW_INTENT_KEYWORDS = [
        "what is", "how does", "why",
        "opinion", "thoughts on", "feedback",
    ]
    
    # NEGATIVE - Vendor/Seller indicators (penalty: -0.3)
    VENDOR_KEYWORDS = [
        # Self-promotion
        "i am a", "i'm a", "i am an", "i'm an",
        "we are a", "we're a",
        "i work as", "i work for",
        "my company", "our company",
        "i run", "we run",
        "my business", "our business",
        
        # Selling
        "for sale", "selling", "we sell",
        "i sell", "offering", "we offer",
        "services provided", "we provide",
        "contact us", "hire us", "choose us",
        "get in touch", "reach us",
        
        # Marketing speak
        "best prices", "guaranteed", "discount",
        "special offer", "limited time",
        "contact today", "call now",
    ]
    
    # NEGATIVE - Spam/low quality (penalty: -0.2)
    SPAM_INDICATORS = [
        "click here", "click link", "check my bio",
        "follow me", "subscribe", "share this",
        "upvote", "like this",
    ]
    
    # URGENCY PATTERNS
    URGENCY_PATTERNS = {
        "immediate": ["asap", "urgent", "immediately", "today", "now", "emergency", "right now"],
        "soon": ["this week", "soon", "quickly", "fast", "in a few days", "shortly"],
        "future": ["next month", "later", "eventually", "someday", "considering", "thinking"],
    }
    
    # CONTEXT BOOSTERS - Add context to scoring
    CONTEXT_PATTERNS = {
        "first_person": ["i ", "my ", "me ", "we ", "our "],  # +0.1
        "question": ["?"],  # +0.05
        "location": ["in nairobi", "in kenya", "near me", "local"],  # +0.05
    }
    
    def __init__(self):
        # Compile regex patterns for efficiency
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile regex patterns"""
        self.vendor_pattern = re.compile(
            r'\b(' + '|'.join(map(re.escape, self.VENDOR_KEYWORDS)) + r')\b',
            re.IGNORECASE
        )
        self.spam_pattern = re.compile(
            r'\b(' + '|'.join(map(re.escape, self.SPAM_INDICATORS)) + r')\b',
            re.IGNORECASE
        )
    
    def analyze(self, text: str, query: str = "") -> IntentResult:
        """
        Analyze text for buyer intent
        
        Returns IntentResult with:
        - intent_score: 0-1 probability of being a buyer
        - intent_category: buying, researching, vendor, or discussion
        - buying_urgency: immediate, soon, future, or none
        - keywords_matched: Which keywords were found
        - confidence: 0-1 confidence level
        - is_buyer: True if score >= 0.5
        """
        if not text:
            return IntentResult(
                intent_score=0.0,
                intent_category="unknown",
                buying_urgency="none",
                keywords_matched=[],
                confidence=0.0,
                is_buyer=False
            )
        
        text_lower = text.lower()
        score = 0.0
        keywords_matched = []
        
        # 1. Check for VENDOR indicators (immediate disqualifier)
        vendor_matches = self.vendor_pattern.findall(text_lower)
        if vendor_matches:
            score -= 0.4
            keywords_matched.extend([f"[VENDOR: {m}]" for m in vendor_matches[:3]])
        
        # 2. Check for SPAM indicators
        spam_matches = self.spam_pattern.findall(text_lower)
        if spam_matches:
            score -= 0.2
            keywords_matched.extend([f"[SPAM: {m}]" for m in spam_matches[:2]])
        
        # 3. Score HIGH INTENT keywords (strong buyer signals)
        for keyword in self.HIGH_INTENT_KEYWORDS:
            if keyword in text_lower:
                score += 0.25
                keywords_matched.append(keyword)
        
        # 4. Score MEDIUM INTENT keywords
        for keyword in self.MEDIUM_INTENT_KEYWORDS:
            if keyword in text_lower:
                score += 0.10
                if keyword not in keywords_matched:  # Avoid duplicates
                    keywords_matched.append(keyword)
        
        # 5. Score LOW INTENT keywords
        for keyword in self.LOW_INTENT_KEYWORDS:
            if keyword in text_lower:
                score += 0.02
                if keyword not in keywords_matched:
                    keywords_matched.append(keyword)
        
        # 6. Context boosters
        # First person pronouns (personal need vs general discussion)
        if any(p in text_lower for p in self.CONTEXT_PATTERNS["first_person"]):
            score += 0.10
        
        # Question marks (asking for help/recommendations)
        if "?" in text:
            score += 0.05
        
        # Location mentions (local intent)
        if any(loc in text_lower for loc in self.CONTEXT_PATTERNS["location"]):
            score += 0.05
        
        # 7. Determine urgency
        urgency = self._detect_urgency(text_lower)
        if urgency == "immediate":
            score += 0.15
        elif urgency == "soon":
            score += 0.05
        
        # 8. Cap score between 0 and 1
        score = max(0.0, min(1.0, score))
        
        # 9. Determine category
        category = self._classify_category(score, vendor_matches, keywords_matched)
        
        # 10. Calculate confidence
        confidence = self._calculate_confidence(text, keywords_matched)
        
        # 11. Determine if buyer
        is_buyer = score >= 0.5 and not vendor_matches
        
        return IntentResult(
            intent_score=round(score, 3),
            intent_category=category,
            buying_urgency=urgency,
            keywords_matched=keywords_matched[:10],  # Top 10
            confidence=round(confidence, 3),
            is_buyer=is_buyer
        )
    
    def _detect_urgency(self, text: str) -> str:
        """Detect urgency level from text"""
        text_lower = text.lower()
        
        for level, keywords in self.URGENCY_PATTERNS.items():
            if any(kw in text_lower for kw in keywords):
                return level
        
        return "none"
    
    def _classify_category(self, score: float, vendor_matches: List, keywords: List) -> str:
        """Classify the intent category"""
        if vendor_matches:
            return "vendor"
        
        if score >= 0.7:
            return "buying"
        elif score >= 0.5:
            return "strong_interest"
        elif score >= 0.3:
            return "researching"
        elif any(k in keywords for k in self.LOW_INTENT_KEYWORDS):
            return "discussion"
        else:
            return "low_intent"
    
    def _calculate_confidence(self, text: str, keywords_matched: List) -> float:
        """Calculate confidence in the intent score"""
        # More keywords = higher confidence
        keyword_confidence = min(len(keywords_matched) / 3, 1.0)
        
        # Longer text = more context = higher confidence (up to a point)
        text_length = len(text.split())
        length_confidence = min(text_length / 20, 1.0)
        
        # Very short text = low confidence
        if text_length < 5:
            length_confidence = 0.3
        
        return (keyword_confidence * 0.6) + (length_confidence * 0.4)
    
    def is_buyer(self, text: str, threshold: float = 0.5) -> bool:
        """
        Quick check if text indicates a buyer
        
        Args:
            text: The text to analyze
            threshold: Minimum score to be considered a buyer (default 0.5)
            
        Returns:
            bool: True if buyer intent detected
        """
        result = self.analyze(text)
        return result.intent_score >= threshold and result.is_buyer
    
    def score_batch(self, texts: List[str], query: str = "") -> List[IntentResult]:
        """Analyze multiple texts at once"""
        return [self.analyze(text, query) for text in texts]


# Example usage and testing
if __name__ == "__main__":
    service = IntentDetectionService()
    
    test_cases = [
        # High intent - should be buyers
        "I need a plumber ASAP! Please contact me.",
        "Looking for a good CRM software. Any recommendations?",
        "Where can I buy affordable web design services in Nairobi?",
        "Urgent: Looking to hire a developer this week.",
        
        # Medium intent - researching
        "What are the best options for accounting software?",
        "Has anyone used XYZ Company before?",
        
        # Low intent - discussion
        "What is CRM software?",
        
        # Vendors - should be filtered out
        "I am a plumber offering services in Nairobi. Contact us!",
        "We sell the best CRM software. Check our website.",
        "For sale: Web design services. Best prices guaranteed!",
    ]
    
    print("=" * 80)
    print("Intent Detection AI - Test Results")
    print("=" * 80)
    
    for text in test_cases:
        result = service.analyze(text)
        print(f"\nText: {text[:60]}...")
        print(f"  Score: {result.intent_score} | Category: {result.intent_category}")
        print(f"  Urgency: {result.buying_urgency} | Is Buyer: {result.is_buyer}")
        print(f"  Keywords: {', '.join(result.keywords_matched[:5])}")


# Singleton instance
_intent_service = None


def get_intent_service() -> IntentDetectionService:
    """Get or create the intent detection service singleton"""
    global _intent_service
    if _intent_service is None:
        _intent_service = IntentDetectionService()
    return _intent_service

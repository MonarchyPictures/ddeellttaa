import re
import logging
import json
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class AIExtractionService:
    """
    Service for extracting structured data from unstructured text using AI/NLP techniques.
    Supports local BERT model for NER if available, falls back to advanced regex heuristics.
    """
    
    # Pre-compiled regex patterns for performance
    PRICE_PATTERN = re.compile(r"(?:ksh|sh|kes|price|cost)[:\s]*([\d,]+(?:\.\d{2})?)", re.IGNORECASE)
    PHONE_PATTERN = re.compile(r"(?:\+?254|0)?(7\d{8}|1\d{8})")
    EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    
    # Enhanced location list (could be loaded from a file/db)
    LOCATION_KEYWORDS = {
        "nairobi", "mombasa", "kisumu", "nakuru", "eldoret", "thika", "kitengela", 
        "ruiru", "karen", "kilimani", "westlands", "ngong", "ongata rongai", "kiambu",
        "machakos", "naivasha", "malindi", "diani", "nyali", "kileleshwa", "lavington",
        "syokimau", "juja", "roysambu", "kasarani", "langata", "south b", "south c"
    }

    def __init__(self):
        self.nlp_pipeline = None
        self._load_model()

    def _load_model(self):
        """Attempts to load a local NLP model for Named Entity Recognition."""
        try:
            from transformers import pipeline
            # Load a small, fast model for NER (e.g., dslim/bert-base-NER or similar)
            # We use a try-catch to avoid crashing if model is not downloaded
            logger.info("🤖 AI: Loading NLP model for extraction...")
            self.nlp_pipeline = pipeline("ner", model="dslim/bert-base-NER", aggregation_strategy="simple")
            logger.info("✅ AI: NLP model loaded successfully.")
        except ImportError:
            logger.warning("⚠️ AI: 'transformers' library not found. Using regex fallback.")
        except Exception as e:
            logger.warning(f"⚠️ AI: Failed to load NLP model: {e}. Using regex fallback.")

    def extract(self, text: str, source_url: str = "") -> Dict[str, Any]:
        """
        Extracts structured data from text using the best available method.
        """
        if not text:
            return {}

        # 1. Try AI Extraction
        if self.nlp_pipeline:
            try:
                return self._extract_with_model(text)
            except Exception as e:
                logger.error(f"AI Extraction failed: {e}. Falling back to regex.")

        # 2. Fallback to Regex/Heuristics
        return self._extract_with_fallback(text)

    def _extract_with_model(self, text: str) -> Dict[str, Any]:
        """Uses BERT NER to extract entities."""
        entities = self.nlp_pipeline(text)
        
        result = {
            "price": None,
            "location": None,
            "item": None,
            "contact": None,
            "confidence": 0.85 # Higher confidence with AI
        }
        
        # Map NER tags to our fields
        # LOC -> Location
        # ORG/PER -> Item/Seller (imperfect, but better than nothing)
        # MISC -> Item?
        
        locations = []
        items = []
        
        for entity in entities:
            group = entity['entity_group']
            word = entity['word']
            
            if group == 'LOC':
                locations.append(word)
            elif group in ['ORG', 'MISC']:
                items.append(word)
                
        if locations:
            result["location"] = locations[0] # Take first location
            
        if items:
            # Simple heuristic: assume the first MISC/ORG is the item if valid
            result["item"] = items[0]

        # NLP models often miss specific formatting for price/phone, 
        # so we still run regex for those high-precision fields
        result["price"] = self._extract_price(text)
        result["contact"] = self._extract_contact(text)
        
        return result

    def _extract_with_fallback(self, text: str) -> Dict[str, Any]:
        """Robust regex and keyword matching."""
        result = {
            "price": self._extract_price(text),
            "location": self._extract_location(text),
            "item": self._extract_item(text), 
            "contact": self._extract_contact(text),
            "confidence": 0.5 # Baseline
        }
        
        # Adjust confidence
        if result["price"]: result["confidence"] += 0.2
        if result["contact"]: result["confidence"] += 0.2
        if result["location"]: result["confidence"] += 0.1
        
        return result

    def _extract_price(self, text: str) -> Optional[float]:
        match = self.PRICE_PATTERN.search(text)
        if match:
            try:
                # Remove commas and convert
                price_str = match.group(1).replace(",", "")
                return float(price_str)
            except:
                pass
        return None

    def _extract_location(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        # Check against known locations
        for loc in self.LOCATION_KEYWORDS:
            # Check for word boundary to avoid partial matches (e.g., "thika" in "thikar")
            if re.search(r'\b' + re.escape(loc) + r'\b', text_lower):
                return loc.title()
        return None

    def _extract_contact(self, text: str) -> Optional[str]:
        match = self.PHONE_PATTERN.search(text)
        if match:
            return match.group(0)
        return None

    def _extract_item(self, text: str) -> Optional[str]:
        # Heuristic: First 3-5 words often contain the item name in titles/posts
        words = text.split()
        if not words:
            return None
        return " ".join(words[:5])

AI_EXTRACTOR = AIExtractionService()

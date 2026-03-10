"""
Query Expansion AI Service
Expands user queries into buyer-intent phrases
"""
from typing import List, Dict
import re


class QueryExpansionService:
    """
    Expands simple queries into multiple buyer-intent search phrases.
    
    Example:
        Input: "plumber"
        Output: ["need plumber", "looking for plumber", "recommend plumber", ...]
    """
    
    # Intent patterns for different query types
    BUYER_INTENT_TEMPLATES = [
        # Direct need
        "need {query}",
        "i need {query}",
        "looking for {query}",
        "want {query}",
        
        # Recommendations
        "recommend {query}",
        "any good {query}",
        "best {query}",
        "top rated {query}",
        "who is the best {query}",
        
        # Questions
        "where to find {query}",
        "where can i get {query}",
        "who sells {query}",
        "who provides {query}",
        
        # Urgency
        "urgent {query}",
        "emergency {query}",
        "asap {query}",
        
        # Comparison/Research
        "{query} vs",
        "{query} reviews",
        "{query} near me",
        "{query} in my area",
        
        # Problem-based
        "help with {query}",
        "fix {query}",
        "solve {query} problem",
        "{query} not working",
        
        # Hiring/Service
        "hire {query}",
        "looking to hire {query}",
        "want to hire {query}",
        "{query} for hire",
        
        # Buying
        "buy {query}",
        "purchase {query}",
        "get {query}",
        "order {query}",
        
        # Quotes/Pricing
        "{query} quote",
        "{query} price",
        "how much does {query} cost",
        "{query} affordable",
        "cheap {query}",
    ]
    
    # Industry-specific expansions
    INDUSTRY_EXPANSIONS = {
        "software": [
            "saas {query}",
            "{query} software solution",
            "{query} platform",
            "{query} tool",
            "{query} app",
        ],
        "service": [
            "{query} service",
            "{query} professional",
            "{query} company",
            "{query} agency",
        ],
        "product": [
            "{query} supplier",
            "{query} vendor",
            "{query} manufacturer",
            "{query} distributor",
            "wholesale {query}",
        ],
    }
    
    # Location modifiers (auto-applied)
    LOCATION_MODIFIERS = [
        "{phrase} in kenya",
        "{phrase} nairobi",
        "{phrase} near me",
        "local {phrase}",
    ]
    
    def __init__(self):
        self.pattern_cache = {}
    
    def expand(self, query: str, category: str = "general", include_locations: bool = True) -> List[str]:
        """
        Expand a query into multiple buyer-intent phrases.
        
        Args:
            query: Original search term (e.g., "plumber", "crm software")
            category: Industry category (software, service, product)
            include_locations: Whether to add location modifiers
            
        Returns:
            List of expanded search phrases
        """
        query = query.lower().strip()
        phrases = []
        
        # 1. Apply buyer intent templates
        for template in self.BUYER_INTENT_TEMPLATES:
            phrase = template.format(query=query)
            phrases.append(phrase)
        
        # 2. Add category-specific expansions
        if category in self.INDUSTRY_EXPANSIONS:
            for template in self.INDUSTRY_EXPANSIONS[category]:
                phrase = template.format(query=query)
                phrases.append(phrase)
        
        # 3. Add variations with synonyms
        phrases.extend(self._add_synonym_variations(query))
        
        # 4. Add location modifiers if enabled
        if include_locations:
            base_phrases = phrases[:10]  # Top 10 phrases
            for phrase in base_phrases:
                for modifier in self.LOCATION_MODIFIERS:
                    location_phrase = modifier.format(phrase=phrase)
                    phrases.append(location_phrase)
        
        # 5. Clean and deduplicate
        phrases = self._clean_phrases(phrases)
        
        return phrases
    
    def expand_batch(self, queries: List[str], category: str = "general") -> Dict[str, List[str]]:
        """Expand multiple queries at once"""
        return {query: self.expand(query, category) for query in queries}
    
    def _add_synonym_variations(self, query: str) -> List[str]:
        """Add common synonym variations"""
        variations = []
        
        # Common business synonyms
        synonyms = {
            "software": ["app", "platform", "system", "tool"],
            "service": ["services", "solution", "solutions"],
            "company": ["business", "firm", "agency"],
            "buy": ["purchase", "get", "acquire"],
            "need": ["want", "require", "looking for"],
        }
        
        for word, alts in synonyms.items():
            if word in query:
                for alt in alts:
                    variations.append(query.replace(word, alt))
        
        return variations
    
    def _clean_phrases(self, phrases: List[str]) -> List[str]:
        """Remove duplicates and normalize phrases"""
        seen = set()
        cleaned = []
        
        for phrase in phrases:
            # Normalize
            phrase = phrase.lower().strip()
            phrase = re.sub(r'\s+', ' ', phrase)  # Multiple spaces to single
            
            if phrase and phrase not in seen:
                seen.add(phrase)
                cleaned.append(phrase)
        
        return cleaned
    
    def score_relevance(self, phrase: str, original_query: str) -> float:
        """
        Score how relevant an expanded phrase is to the original query.
        Returns 0-1 score.
        """
        phrase_words = set(phrase.lower().split())
        query_words = set(original_query.lower().split())
        
        # Calculate word overlap
        if not phrase_words:
            return 0.0
        
        overlap = len(phrase_words & query_words)
        return overlap / len(query_words) if query_words else 0.0


# Singleton instance
_expansion_service = None


def get_expansion_service() -> QueryExpansionService:
    """Get or create the query expansion service singleton"""
    global _expansion_service
    if _expansion_service is None:
        _expansion_service = QueryExpansionService()
    return _expansion_service

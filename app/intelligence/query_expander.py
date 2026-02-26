
import logging
import itertools
from typing import List, Optional

logger = logging.getLogger("QueryExpander")

# --- EXPANSION CONSTANTS (User Defined) ---

# 1. INTENT VARIATIONS
INTENT_PATTERNS = [
    "want to buy", "ready to buy", "need a", "need", "searching for", 
    "looking for", "planning to buy", "budget for", "serious buyer", 
    "cash buyer", "mortgage approved", "moving to", "relocating to", 
    "wanted", "in need of", "buying"
]

# 2. LOCATION VARIATIONS (Nairobi & Surroundings)
LOCATIONS_NAIROBI = [
    "kilimani", "kileleshwa", "westlands", "lavington", "ngong road", 
    "hurlingham", "south b", "south c", "ruaka", "runda", "karen", 
    "parklands", "syokimau", "kiambu", "machakos", "kajiado", "nairobi",
    "thika road", "kasarani", "roysambu", "kitengela", "rongai"
]

# 3. PROPERTY TYPE VARIATIONS
PROPERTY_TYPES = [
    "house", "apartment", "maisonette", "townhouse", "bungalow", 
    "duplex", "studio apartment", "1 bedroom", "2 bedroom", "3 bedroom", 
    "bedsitter", "off-plan", "gated community", "plot", "land"
]

# 4. BUDGET VARIATIONS (High Intent)
BUDGETS = [
    "budget", "under 5m", "under 10m", "under 15m", "under 20m", 
    "5 million", "10 million", "15 million", "20 million", 
    "affordable", "cheap"
]

# 5. URGENCY TRIGGERS
URGENCY_TRIGGERS = [
    "urgently", "urgent", "asap", "immediate", "ready cash", 
    "serious buyer only", "moving next month", "viewing this week"
]

# 6. SOCIAL / NATURAL LANGUAGE PATTERNS
SOCIAL_PATTERNS = [
    "anyone selling {property} in {location}",
    "who has {property} for sale {location}",
    "looking for {property} in {location}",
    "any leads for {property} in {location}",
    "recommendations for {property} in {location}",
    "budget for {property} {location}",
    "help me find {property} {location}"
]

class SmartQueryExpander:
    """
    Advanced Query Expansion Engine.
    Implements 'Query Multiplication Logic': Intent × Location × Property × Budget
    """
    
    @staticmethod
    def generate_combinations(seed_query: str, location_context: str = "Kenya") -> List[str]:
        """
        Generates a massive list of targeted queries based on a seed.
        
        Strategy:
        1. If seed contains specific keywords (e.g. 'house', 'apartment'), 
           we pivot around that property type.
        2. We cross-reference with Locations and Intents.
        3. We apply Social Patterns.
        """
        seed = seed_query.lower().strip()
        expanded_queries: List[str] = []
        seen = set()

        def add_query(q: str):
            q = (q or "").strip()
            if not q or q in seen:
                return
            seen.add(q)
            expanded_queries.append(q)

        add_query(seed)
        
        # Detect Property Type from Seed
        detected_properties = [p for p in PROPERTY_TYPES if p in seed]
        if not detected_properties:
            # Default to generic if no property specified, but don't go too wild
            # unless the seed is very generic like "real estate"
            if "buy" in seed or "invest" in seed:
                detected_properties = ["house", "apartment", "land"]
            else:
                detected_properties = []

        # Detect Location from Seed
        detected_locations = [l for l in LOCATIONS_NAIROBI if l in seed]
        if not detected_locations:
             # If no location in seed, try to infer from context
             loc_ctx = location_context.lower() if location_context else ""
             
             if "nairobi" in loc_ctx or "kenya" in loc_ctx:
                 # Inject top hotspots if context is Nairobi/Kenya
                 detected_locations = ["kilimani", "westlands", "kileleshwa", "nairobi"]
             elif "nairobi" in seed or "kenya" in seed:
                 detected_locations = ["kilimani", "westlands", "kileleshwa", "nairobi"]
             else:
                 # Don't inject locations if none provided/implied
                 detected_locations = []
        
        # --- GENERATION STRATEGY ---
        
        # 1. Intent × Property × Location (The Core Matrix)
        if detected_properties and detected_locations:
            for prop in detected_properties:
                for loc in detected_locations:
                    for intent in INTENT_PATTERNS:
                        # "want to buy apartment kilimani"
                        add_query(f"{intent} {prop} {loc}")
                        
                    for urgency in URGENCY_TRIGGERS:
                        # "urgent apartment kilimani"
                        add_query(f"{urgency} {prop} {loc}")
                        
                    for budget in BUDGETS:
                        # "apartment kilimani under 10m"
                        add_query(f"{prop} {loc} {budget}")

        # 2. Social / Natural Language Injection
        if detected_properties and detected_locations:
            for prop in detected_properties:
                for loc in detected_locations:
                    for pattern in SOCIAL_PATTERNS:
                        try:
                            q = pattern.format(property=prop, location=loc)
                            add_query(q)
                        except KeyError:
                            pass

        # 3. Fallback / Simple Expansion (if no matrix generated)
        if len(expanded_queries) == 1: # Only seed
            # Try simple variations
            if "buy" in seed:
                add_query(seed.replace("buy", "looking for"))
                add_query(seed.replace("buy", "want"))
            if "house" in seed:
                 add_query(seed.replace("house", "home"))
            
        # 4. Limit results to avoid API overload
        # We prioritize: Urgency > Budget > General Intent
        # Preserve deterministic generation order. Max limit 50 to prevent overload.
        return expanded_queries[:50]

def get_expanded_queries(query: str, location: str = "Kenya") -> List[str]:
    """
    Main entry point.
    Splits comma-separated seeds and expands each.
    """
    if not query:
        return []
        
    # Handle multiple seeds: "buy house, rent apartment"
    seeds = [s.strip() for s in query.split(',')]
    all_queries: List[str] = []
    seen = set()
    
    for seed in seeds:
        expanded = SmartQueryExpander.generate_combinations(seed, location)
        for q in expanded:
            if q not in seen:
                seen.add(q)
                all_queries.append(q)
        
    logger.info(f"Expanded '{query}' into {len(all_queries)} variations.")
    return all_queries

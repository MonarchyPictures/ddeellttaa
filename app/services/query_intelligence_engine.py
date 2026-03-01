# app/services/query_intelligence_engine.py
# ============================================================
# QUERY INTELLIGENCE ENGINE — SaaS-Grade Lead Engine
# ============================================================
# Transforms simple user queries into comprehensive search strategies
# through query expansion, synonym mapping, and multi-language support.
# ============================================================

import re
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass


@dataclass
class QueryExpansionResult:
    """Result of query expansion."""
    original: str
    expanded_queries: List[str]
    detected_language: str
    detected_vertical: str
    location_context: str


# ============================================================
# PRODUCT SYNONYM DATABASE
# ============================================================
# Maps common Kenyan product terms to their synonyms

PRODUCT_SYNONYMS = {
    # Construction / Plumbing
    "pipes": [
        "pvc pipes", "plumbing pipes", "water pipes", "drainage pipes",
        "mabomba", "mabomba ya maji", "plastic pipes", "hdpe pipes",
        "pipe fittings", "pipe connectors", "conduit pipes"
    ],
    "tiles": [
        "floor tiles", "wall tiles", "ceramic tiles", "porcelain tiles",
        "matiles", "tile adhesive", "grout", "tile cutter"
    ],
    "cement": [
        "bamburi cement", "mombasa cement", "simba cement", "rhino cement",
        "mchanga", "cement bags", "ordinary portland cement"
    ],
    
    # Real Estate
    "house": [
        "nyumba", "residential house", "home", "dwelling", "bungalow",
        "maisonette", "townhouse", "villa"
    ],
    "apartment": [
        "flat", "condo", "condominium", "rental unit", "ghetto",
        "bedsitter", "studio apartment"
    ],
    
    # Vehicles
    "car": [
        "gari", "vehicle", "automobile", "motor vehicle", "auto",
        "sedan", "hatchback", "suv", "truck"
    ],
    "toyota": [
        "toyota corolla", "toyota hiace", "toyota fielder", "toyota axio",
        "toyota prado", "toyota harrier", "toyota rav4"
    ],
    
    # Electronics
    "phone": [
        "simu", "mobile phone", "cell phone", "smartphone", "handset",
        "iphone", "samsung", "tecno", "infinix"
    ],
    "laptop": [
        "computer", "notebook", "portable computer", "pc", "macbook",
        "hp laptop", "dell laptop", "lenovo"
    ],
    
    # FMCG
    "diapers": [
        "baby diapers", "nappies", "pampers", "huggies", "diaper pants",
        "baby wipes", "changing mats"
    ],
    "rice": [
        "mchele", "basmati rice", "pishori rice", "brown rice",
        "white rice", "long grain rice"
    ],
    
    # Services
    "plumber": [
        "fundi wa bomba", "plumbing services", "water technician",
        "pipe fitter", "drainage expert"
    ],
    "electrician": [
        "fundi wa stima", "electrical technician", "wireman",
        "power technician", "solar technician"
    ],
}

# ============================================================
# LOCATION EXPANSION
# ============================================================

NAIROBI_AREAS = {
    "nairobi": ["cbd", "westlands", "kilimani", "kileleshwa", "karen", "rongai", 
                "syokimau", "ruaka", "kasarani", "parklands", "ngong road"],
    "westlands": ["westlands proper", "spring valley", "rhapta road", "riverside"],
    "kilimani": ["kilimani proper", "argwings kodhek", " Dennis pritt", "jabavu"],
    "karen": ["karen proper", "langata", "bomas", "ngong"],
    "rongai": ["rongai", "ngong", "kiserian", "ongata rongai"],
    "mombasa": ["nyali", "bamburi", "likoni", "kisauni", "changamwe"],
}

KENYA_TOWNS = [
    "nairobi", "mombasa", "kisumu", "nakuru", "eldoret", "thika",
    "kitengela", "machakos", "nyeri", "nanyuki", "meru", "embu"
]


class QueryIntelligenceEngine:
    """
    SaaS-grade query expansion engine.
    
    Transforms simple queries like "pipes" into comprehensive
    search strategies across languages and synonyms.
    """
    
    def __init__(self):
        self.synonyms = PRODUCT_SYNONYMS
        self.locations = NAIROBI_AREAS
        self.towns = KENYA_TOWNS
    
    def detect_language(self, query: str) -> str:
        """
        Detect primary language of query.
        
        Returns: 'swahili', 'english', or 'mixed'
        """
        query_lower = query.lower()
        
        # Swahili keywords
        swahili_words = [
            "natafuta", "nahitaji", "nataka", "naomba", "mabomba",
            "nyumba", "gari", "simu", "mchele", "bei", "wapi",
            "fundi", "tafuta", "hitaji", "pata"
        ]
        
        swahili_count = sum(1 for word in swahili_words if word in query_lower)
        
        if swahili_count >= 2:
            return "swahili"
        elif swahili_count == 1:
            return "mixed"
        else:
            return "english"
    
    def detect_vertical(self, query: str) -> str:
        """Detect business vertical from query."""
        query_lower = query.lower()
        
        vertical_keywords = {
            "real_estate": ["house", "apartment", "rent", "bedroom", "nyumba", "plot", "land"],
            "vehicles": ["car", "gari", "toyota", "honda", "nissan", "mazda", "truck"],
            "electronics": ["phone", "simu", "laptop", "computer", "tv", "iphone"],
            "construction": ["pipes", "mabomba", "tiles", "cement", "fundi", "plumber"],
            "fmcg": ["diapers", "rice", "mchele", "wholesale", "bulk", "supplier"],
            "services": ["cleaner", "accountant", "lawyer", "driver", "nanny"]
        }
        
        scores = {}
        for vertical, keywords in vertical_keywords.items():
            scores[vertical] = sum(1 for kw in keywords if kw in query_lower)
        
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        return "general"
    
    def expand_synonyms(self, query: str) -> List[str]:
        """
        Expand query with product synonyms.
        
        Example: "pipes" -> ["pipes", "pvc pipes", "mabomba", ...]
        """
        query_lower = query.lower().strip()
        expansions = [query]  # Always include original
        
        # Find matching synonym groups
        for key, synonyms in self.synonyms.items():
            if key in query_lower or any(syn in query_lower for syn in synonyms):
                # Add all synonyms for this product
                for syn in synonyms:
                    if syn not in expansions:
                        expansions.append(syn)
        
        return expansions
    
    def expand_location(self, location: str) -> List[str]:
        """
        Expand location with related areas.
        
        Example: "nairobi" -> ["nairobi", "cbd", "westlands", ...]
        """
        location_lower = location.lower().strip()
        expansions = [location]
        
        # Check if location has sub-areas
        if location_lower in self.locations:
            expansions.extend(self.locations[location_lower])
        
        # Check if query contains any area names
        for main_area, sub_areas in self.locations.items():
            if location_lower in sub_areas or location_lower == main_area:
                expansions.extend([main_area] + sub_areas)
        
        return list(set(expansions))
    
    def generate_search_variants(self, query: str, location: str = "Kenya") -> List[str]:
        """
        Generate all search query variants.
        
        Combines: original + synonyms + locations + buyer signals
        """
        # Expand query and location
        query_expansions = self.expand_synonyms(query)
        location_expansions = self.expand_location(location)
        
        # Buyer signals (English + Swahili)
        buyer_signals = [
            "looking for", "need", "want", "buying",
            "natafuta", "nahitaji", "nataka",
            "budget", "bei", "price",
            "urgent", "haraka", "asap"
        ]
        
        variants = []
        
        # Generate combinations
        for q_exp in query_expansions[:5]:  # Limit to top 5 synonyms
            for loc_exp in location_expansions[:3]:  # Limit to top 3 locations
                # Base query
                variants.append(f'"{q_exp}" "{loc_exp}"')
                
                # With buyer signals
                for signal in buyer_signals[:4]:  # Top 4 signals
                    variants.append(f'"{q_exp}" "{loc_exp}" "{signal}"')
        
        return list(set(variants))
    
    def process_query(self, query: str, location: str = "Kenya") -> QueryExpansionResult:
        """
        Main entry point: Process user query into expanded search strategy.
        """
        return QueryExpansionResult(
            original=query,
            expanded_queries=self.generate_search_variants(query, location),
            detected_language=self.detect_language(query),
            detected_vertical=self.detect_vertical(query),
            location_context=location
        )


# Global engine instance
query_engine = QueryIntelligenceEngine()


def expand_query_intelligently(query: str, location: str = "Kenya") -> QueryExpansionResult:
    """
    Expand user query using SaaS-grade intelligence.
    
    Usage:
        result = expand_query_intelligently("pipes", "Nairobi")
        print(result.expanded_queries)  # 20+ variants
    """
    return query_engine.process_query(query, location)

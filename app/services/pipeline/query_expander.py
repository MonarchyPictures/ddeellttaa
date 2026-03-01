# app/services/pipeline/query_expander.py
"""
Query expansion for Kenya-optimized lead discovery.

Expands user queries into high-recall search patterns.
"""
from typing import List, Dict, Callable


# Kenya locations
KENYA_LOCATIONS = [
    "nairobi", "kileleshwa", "rongai", "ruaka",
    "syokimau", "westlands", "mombasa",
    "kisumu", "nakuru", "eldoret", "thika"
]

# Vertical detection keywords
VERTICAL_KEYWORDS = {
    "real_estate": ["bedroom", "house", "apartment", "rent", "bedsitter", "sq"],
    "vehicle": ["toyota", "car", "gari", "honda", "nissan", "mazda", "bmw"],
    "electronics": ["iphone", "samsung", "laptop", "phone", "computer"],
    "construction": ["tiles", "gypsum", "plumber", "fundi", "cement"],
    "fmcg": ["bulk", "wholesale", "supplier", "stockist", "distributor"],
    "services": ["plumber", "electrician", "accountant", "lawyer", "fundi"],
}


def detect_vertical(product: str) -> str:
    """Detect product vertical from keywords."""
    p = product.lower()
    for vertical, keywords in VERTICAL_KEYWORDS.items():
        if any(k in p for k in keywords):
            return vertical
    return "general"


def generate_real_estate_queries(product: str, location: str) -> List[str]:
    """Generate real estate queries for Kenya."""
    queries = []
    top_areas = ["Nairobi", "Kileleshwa", "Westlands", "Kilimani", "Rongai", "Syokimau"]
    signals = ["looking for", "natafuta", "for rent", "budget", "cash buyer", "urgent"]
    
    for area in top_areas:
        for signal in signals:
            queries.append(f'"{product}" "{area}" "{signal}"')
    
    # Platform-specific
    for platform in ["site:facebook.com", "site:t.me"]:
        queries.append(f'{platform} "{product}" "{location}" "natafuta"')
    
    return list(set(queries))


def generate_vehicle_queries(product: str, location: str) -> List[str]:
    """Generate vehicle queries for Kenya."""
    queries = []
    signals = ["natafuta", "looking for", "cash ready", "budget", "owner selling", "clean unit"]
    
    for signal in signals:
        queries.append(f'"{product}" "{location}" "{signal}"')
    
    # Platform-specific
    for platform in ["site:facebook.com", "site:t.me", "site:jiji.co.ke"]:
        queries.extend([
            f'{platform} "{product}" "{location}" "natafuta"',
            f'{platform} "{product}" "{location}" "looking for"',
        ])
    
    return list(set(queries))


def generate_general_queries(product: str, location: str) -> List[str]:
    """Generate general queries for any product."""
    queries = []
    
    # Swahili buyer verbs
    swahili = ["natafuta", "nahitaji", "nataka", "naomba"]
    for verb in swahili:
        queries.append(f'"{verb} {product}" "{location}"')
    
    # English buyer verbs
    english = ["looking for", "need", "want to buy", "who has", "anyone selling"]
    for verb in english:
        queries.append(f'"{verb} {product}" "{location}"')
    
    # Budget-conscious
    queries.extend([
        f'"{product}" "budget" "{location}"',
        f'"{product}" "ksh" "{location}"',
    ])
    
    return list(set(queries))


# Vertical generators registry
VERTICAL_GENERATORS: Dict[str, Callable[[str, str], List[str]]] = {
    "real_estate": generate_real_estate_queries,
    "vehicle": generate_vehicle_queries,
    "electronics": generate_general_queries,
    "construction": generate_general_queries,
    "fmcg": generate_general_queries,
    "services": generate_general_queries,
    "general": generate_general_queries,
}


def expand_queries(product: str, location: str = "Kenya", vertical: str = None) -> List[str]:
    """
    Expand product query into high-recall search queries.
    
    Args:
        product: Product name/category
        location: Location (default: Kenya)
        vertical: Optional vertical override
        
    Returns:
        List of search queries
    """
    if vertical is None:
        vertical = detect_vertical(product)
    
    generator = VERTICAL_GENERATORS.get(vertical, generate_general_queries)
    return generator(product, location)


def generate_high_recall_queries(product: str, location: str = "Kenya") -> List[str]:
    """
    Generate high-recall queries for Kenya market.
    
    Delegates to vertical-specific generators.
    
    Args:
        product: Product to search for
        location: Location (default: Kenya)
        
    Returns:
        List of search queries
    """
    return expand_queries(product, location)

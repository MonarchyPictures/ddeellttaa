def build_generic_query(raw_query: str, location: str = "Kenya") -> str:
    """
    Normalizes raw user queries into high-intent search strings.
    Delta9 is now category-agnostic.
    """
    base = raw_query.strip()
    
    # Generic intent keywords
    intent_keywords = ["buy", "looking for", "price", "sale"]
    
    # Construct a broad but focused search string
    # We don't lock into specific categories anymore.
    intent_str = " OR ".join(intent_keywords)
    
    normalized = f"{base} ({intent_str}) {location}"
    
    return " ".join(normalized.split()).strip()

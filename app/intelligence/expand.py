def expand_query(q: str) -> list[str]:
    """
    Expands a search query into related terms to hit multiple markets.
    Refactored to be FULLY GENERIC. Special casing removed.
    
    STEP 3: Generic Expansion Logic.
    Adds plural versions and common intent variations.
    """
    if not q:
        return []

    q = q.lower().strip()
    expansions = [q]
    
    # Simple pluralization (generic)
    if not q.endswith('s'):
        expansions.append(f"{q}s")
    elif q.endswith('s') and len(q) > 3:
        expansions.append(q[:-1])

    # Intent-based expansions are handled by discovery_passes in ingestion.py,
    # so we keep this focused on the product itself.
    
    return list(set(expansions))

import random

BUYER_PATTERNS = [
    "looking for {q} in {loc}",
    "need {q} in {loc}",
    "want to buy {q} in {loc}",
    "WTB {q} {loc}",
    "anyone selling {q} in {loc}",
    "where can I buy {q} in {loc}",
    "{q} needed urgently in {loc}"
]

def build_buyer_query(query: str, location: str = "Kenya"):
    if not location:
        location = "Kenya"
        
    pattern = random.choice(BUYER_PATTERNS)
    return pattern.format(q=query, loc=location)

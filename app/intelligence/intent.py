"""
Universal Buyer Intent Engine
Generalizes intent detection across all categories (water pipes, cement, phones, cars, etc.)
Focuses exclusively on BUYERS, not sellers or ads.
"""

BUYER_PATTERNS = [
    # English
    "looking for",
    "need",
    "want to buy",
    "where can i buy",
    "anyone selling",
    "need supplier",
    "need vendor",
    "urgent need",
    "searching for",
    "interested in buying",
    "i want to purchase",
    "how much is",
    "price for",
    "get me",
    "find me",
    "can i get",
    "i need a",
    "i need an",
    "looking to acquire",
    "in the market for",
    "seeking",
    "where to find",
    "who sells",
    "any leads on",
    "supplier of",
    "any supplier",

    # Service / Job Buyer Signals (New Upgrade)
    "hiring",
    "vacancy",
    "job opening",
    "remote job",
    "looking for staff",
    "looking for employee",
    "looking for worker",
    "help wanted",
    "work available",
    "job opportunity",
    "recruiting",
    "seeking to hire",

    # B2B / Industrial signals (New Upgrade)
    "rfq",
    "quotation",
    "quotations",
    "supplier needed",
    "suppliers needed",
    "bulk order",
    "price per meter",
    "price per foot",
    "price per unit",
    "contractor looking",
    "tender",
    "procurement",
    "wholesale price",
    "delivery schedule",
    "business looking for",

    # Sheng (Kenyan slang/creole)
    "nataka",
    "nipe",
    "naeza pata",
    "ko wapi nipate",
    "una sell",
    "una kuuza",
    "ko bidii",
    "ko kitu",
    "naikua",
    "niskie",
    "ko na",
    "meko na",
    "niambie",
    "tupeane",
    "ko fresh",
    "niko na budget",
    "ko supply",
    "una supply",
    "nipe price",
    "ko bei",
    "nataka ku-buy",
    "ko link",
    "nao pia",
    "ko hio",
    "meko na hio",
    "nipatie",
    "ko pesa",
    "tunatafuta",
    "wanatafuta",

    # Swahili
    "ninataka",
    "ninaomba",
    "natafuta",
    "nahitaji",
    "wapi naweza kupata",
    "nani anauza",
    "tafuta muuzaji",
    "kuna mtu anayeuza",
    "kwa ajili ya ununuzi",
    "inapatikana kununua",
    "bei gani",
    "bei ya",
    "gharama ya",
    "nafuu zaidi",
    "bei nafuu ya",
    "nataka kununua", 
    "naangalia kununua", 
    "ninanunua", 
    "ninahitaji kununua", 
    "napa wapi kununua", 
    "anauza nani", 
    "naanga",

    # Sheng Extended (New Upgrade)
    "nataka kubuy", 
    "nimekua nikiangalia kubuy", 
    "ko mtu anauza", 
    "naomba kuniuzia", 
    "ko kitu hiki", 
    "nipe hio", 
    "ko nayo", 
    "bei ni ngapi", 
    "ko bei poa", 
    "niskie price", 
    "nipe muuzaji", 
    "ko supplier",

    # E-commerce & Product Search
    "add to cart", 
    "shopping for", 
    "product review", 
    "best deal on", 
    "compare prices", 
    "online shopping", 
    "store near me", 
    "in stock near me", 
    "order now", 
    "on sale", 
    "discount code for", 
    "promo for", 
    "ninatafuta bidhaa", 
    "ukaguzi wa bidhaa", 
    "ofa nzuri ya", 
    "linganisha bei", 
    "ununuzi mtandaoni", 
    "duka karibu nami", 
    "ipo stock karibu", 
    "agiza sasa", 
    "inauzwa", 
    "punguzo la", 
    "promo ya",
    
    # Direct Purchase & Inquiry Intent (Extended)
    "i want to buy", 
    "looking to buy", 
    "need to buy", 
    "where can i buy", 
    "find a seller", 
    "searching for", 
    "i am looking for", 
    "anyone selling", 
    "for purchase", 
    "available for purchase", 
    "how much is", 
    "price of", 
    "cost of", 
    "cheapest", 
    "best price for",
    "ninahitaji",
    "napenda kununua",
    "ninaweza kupata wapi",
    "anayeiuza",
    "muuzaji",
    "duka",
    "bei ya",
    "nipe",
    "tafadhali nisaidie",
    "ninatafuta",
    "mahali pa kununua",
    "ninachotafuta",
    "ninahitaji muuzaji",
    "kuna mtu anayeuza",
    "ninaweza kupata",
    "nipatie",
    "ninaweza kununua",
    "nina shida ya",
    "ko na",
    "naweza kuona",
    "natumai kupata",
    "ninatafuta muuzaji wa",
    "ninahitaji kununua",
]

def is_buyer_intent(text: str) -> bool:
    """
    CORE LOGIC: Returns True if text exhibits clear buyer intent.
    Works for any category (water pipes, cement, phones, cars, etc.)
    """
    if not text:
        return False
    text = text.lower()
    return any(p in text for p in BUYER_PATTERNS)

def buyer_intent_score(text: str, query: str = None) -> float:
    """
    Calculates a buyer intent score from 0.0 to 1.0.
    Heuristic: presence of buyer patterns + urgency + specs.
    """
    if not text:
        return 0.0
        
    text = text.lower()
    score = 0.0

    # 🏭 Industry Awareness
    from app.intelligence_v2.industry_aware import is_industrial_query
    is_industrial = is_industrial_query(query) if query else False

    # Base intent from patterns
    matched_patterns = [p for p in BUYER_PATTERNS if p in text]
    if matched_patterns:
        score += 0.4
        # Deduplicate overlapping patterns (e.g., "looking for" and "looking")
        # Sort by length descending and only count non-overlapping
        unique_matches = []
        sorted_patterns = sorted(matched_patterns, key=len, reverse=True)
        temp_text = text
        for p in sorted_patterns:
            if p in temp_text:
                unique_matches.append(p)
                temp_text = temp_text.replace(p, "###")
        
        score += min(len(unique_matches) * 0.1, 0.3) # Bonus for multiple signals

    # Urgency signals
    urgency_keywords = ["asap", "urgent", "immediately", "now", "today", "fast", "needed by", "quick"]
    if any(f" {u} " in f" {text} " for u in urgency_keywords):
        score += 0.2

    # Specificity signals (numbers, units, quantities)
    import re
    # Base pattern for quantities - match numbers followed by units
    # We require a unit to avoid matching random numbers like "iPhone 15"
    # UPDATED: Handles commas in numbers (e.g., 15,000) and currency prefixes (KSh 15000)
    qty_pattern = r'((?:ksh|tsh|sh|usd|\$)\s*[\d,]+|[\d,]+\s+(?:l|kg|units|pcs|ton|20\d{2}|ksh|sh|k\b|m|cm|mm|ft|inches|meters|metres|bags|bundles|rolls|drums))'
    if re.search(qty_pattern, text, re.IGNORECASE):
        # Check if it matched a year-like number (e.g., 2024)
        match = re.search(qty_pattern, text, re.IGNORECASE)
        matched_text = match.group(0).lower()
        # If it's just a number like "15" without a unit, don't count it as a quantity unless it's a specific B2B unit
        score += 0.1
        # 🏭 Industry Boost: Extra points for quantity in B2B
        if is_industrial:
            score += 0.1

    # 🏭 RFQ/Quotation Boost for Industrial
    if is_industrial:
        rfq_patterns = ["rfq", "quotation", "quote", "supplier", "bulk", "wholesale"]
        if any(rp in text for rp in rfq_patterns):
            score += 0.1

    # High Recall Mode: Allow lower confidence signals but mark them
    from app.config.runtime import INTENT_THRESHOLD, HIGH_RECALL_MODE
    if score < INTENT_THRESHOLD:
        if HIGH_RECALL_MODE:
             # Downgrade score but allow it to pass filter
             return score * 0.5
        return 0.0

    return min(score, 1.0)

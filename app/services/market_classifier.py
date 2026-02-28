# app/services/market_classifier.py
# ============================================================
# MARKET CLASSIFIER — Relaxed to show more leads
# ============================================================

import re
import logging
from app.config.runtime import (
    HIGH_RECALL_MODE,
    REQUIRE_FIRST_PERSON,
    REQUIRE_BUYER_KEYWORD,
    INTENT_POINTS_FLOOR,
    CONFIDENCE_FLOOR
)

logger = logging.getLogger(__name__)

# --- BUYER INTENT KEYWORDS ---
BUYER_INTENT_ALL = [
    # English formal
    "looking for", "looking to buy", "searching for", "want to buy",
    "planning to buy", "ready to buy", "serious buyer", "cash buyer",
    "ready with cash", "budget is", "my budget is", "urgently need",
    "in need of", "interested in buying", "anyone selling", "who is selling",
    "where can i find", "recommendations for", "need asap", "wtb",
    "mortgage", "loan approved", "finance approved",
    # English casual
    "any leads", "who has", "anyone with", "im after", "i need",
    "help me find", "looking around", "budget around", "need",
    "buying", "where can i get", "recommend", "suggestion",
    "how much", "price", "cost", "affordable",
    # Swahili
    "natafuta", "nahitaji", "nataka kununua", "niko tayari",
    "niko na pesa", "niko na budget", "nani anauza",
    "kuna mtu anauza", "ninatafuta", "naomba",
    # Sheng
    "niko na doh", "niko ready manze", "nataka deal safi",
    "nani ako na", "kuna deal", "budget iko"
]

# Soft reject - deduct points
SELLER_INDICATORS = [
    "free delivery", "best price", "in stock", "available stock",
    "call to order", "visit us", "shop now", "buy now", "order now",
    "we sell", "we supply", "distributor", "wholesaler", "manufacturer",
    "brand new", "warranty", "lowest price", "huge sale", "discount",
    "limited offer", "get yours", "grab yours", "delivery countrywide",
    "for sale", "call now", "dealer", "official store", "we ship",
    "delivery available", "stock available", "website link", "buy online",
    "price negotiable", "visit our shop", "latest collection",
    "visit our yard", "inventory", "financing arranged"
]

# Only HARD reject these — obvious automated seller content
SELLER_HARD_REJECT = [
    "add to cart", "checkout", "buy from us",
    "official distributor", "we sell", "we offer",
    "visit our store", "call to order",
    "payment on delivery", "lipa mdogo mdogo",
    "official dealer", "we are located", "wholesale prices",
    "ltd", "limited", "company", "enterprises",
    "dm for price", "price is", "listed by agent", "contact broker", "broker",
    "for sale", "visit our shop", "call our agent"
]

BUYER_STRONG_CUES = [
    "looking for", "looking to buy", "want to buy", "need to buy",
    "where can i buy", "anyone selling", "who is selling",
    "wtb", "wanted", "ready to buy", "cash buyer",
    "my budget is", "budget is",
    "natafuta", "nahitaji", "nataka kununua", "ninatafuta",
]

URGENCY_KEYWORDS = [
    "asap", "urgent", "haraka", "now", "today",
    "immediate", "sasa hivi", "this week", "deadline"
]

FIRST_PERSON_PRONOUNS = [
    "i", "im", "my", "me", "we", "our",
    "natafuta", "nahitaji", "nataka", "niko", "naomba", "ninatafuta"
]


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = text.replace("\u2019", "").replace("'", "")
    text = re.sub(r'[^\w\s?!.,@+\-/]', ' ', text)
    text = re.sub(r'(.)\1{2,}', r'\1', text)
    return text.strip()


def is_valid_buyer(text: str, url: str = None) -> bool:
    """
    Buyer-focused validation gate.
    Rejects seller/listing noise and requires at least minimal buyer evidence.
    """
    if not text or len(text.strip()) < 5:
        return False

    normalized = normalize_text(text)
    
    # HIGH RECALL MODE: Only reject obvious sellers, accept everything else
    if HIGH_RECALL_MODE:
        # Check for obvious seller signals
        has_seller_signal = any(word in normalized for word in SELLER_HARD_REJECT)
        if has_seller_signal:
            print(f"HIGH_RECALL_REJECT: Obvious seller signal in: {text[:60]}...")
            return False
        # Accept everything else in high recall mode
        print(f"HIGH_RECALL_ACCEPT: {text[:60]}...")
        return True

    # Only hard-reject obvious automated seller content
    for word in SELLER_HARD_REJECT:
        if word in normalized:
            print(f"CLASSIFIER_REJECT: Hard seller keyword '{word}' in: {text[:80]}...")
            logger.debug(f"REJECTED (Hard Seller): '{word}'")
            return False

    # URL check — only block obvious e-commerce/shop pages
    if url:
        url_lower = url.lower()
        BLOCKED_DOMAINS = ["jumia", "amazon", "aliexpress", "ebay", "kilimall", "jiji.co.ke/shop"]
        BLOCKED_PATHS = ["/product", "/shop", "/cart", "/checkout", "/item"]

        if any(d in url_lower for d in BLOCKED_DOMAINS):
            logger.debug(f"REJECTED (Blocked Domain): '{url}'")
            return False

        if any(p in url_lower for p in BLOCKED_PATHS):
            logger.debug(f"REJECTED (Blocked Path): '{url}'")
            return False
        # Marketplace domains are mostly seller listings unless explicitly "wanted".
        if any(d in url_lower for d in ["jiji.co.ke", "pigiame.co.ke", "facebook.com/marketplace"]):
            if "wanted" not in url_lower and "looking-for" not in url_lower:
                logger.debug(f"REJECTED (Marketplace listing URL): '{url}'")
                return False

    seller_soft_hits = sum(1 for phrase in SELLER_INDICATORS if phrase in normalized)
    has_buyer_phrase = any(phrase in normalized for phrase in BUYER_STRONG_CUES)
    if "are you looking for" in normalized or "looking for information" in normalized:
        has_buyer_phrase = False
    has_first_person = any(
        re.search(r'\b' + re.escape(word) + r'\b', normalized) for word in FIRST_PERSON_PRONOUNS
    )
    has_request_verb = bool(
        re.search(
            r"\b((i|we)\s+(need|want|am looking for|are looking for|looking for)|"
            r"where can i buy|anyone selling|wtb|wanted|"
            r"natafuta|nahitaji|nataka kununua|ninatafuta)\b",
            normalized,
        )
    )
    has_budget = bool(re.search(r'\b\d+\s*(k|m|million|thousand|sh|ksh|kes)\b', normalized))
    has_urgency = any(u in normalized for u in URGENCY_KEYWORDS)
    has_question = "?" in text
    is_editorial_or_directory = any(
        phrase in normalized for phrase in [
            "comprehensive list", "buy and sell", "our platform",
            "price guide", "facts lifehacks", "directory", "top 10",
            "best suppliers", "water tank prices in kenya",
        ]
    )
    if is_editorial_or_directory and not has_first_person:
        return False

    buyer_evidence = sum([
        1 if has_buyer_phrase else 0,
        1 if has_request_verb else 0,
        1 if has_first_person else 0,
        1 if has_budget else 0,
        1 if has_urgency else 0,
        1 if has_question else 0,
    ])

    # Seller-heavy text with no explicit buyer signal is not a buyer lead.
    # SCORING-BASED CLASSIFICATION for HIGH_RECALL_MODE
    if HIGH_RECALL_MODE:
        # Calculate buyer intent score (0.0 to 1.0)
        intent_score = 0.0
        
        # Product match (base score)
        intent_score += 0.3
        
        # Budget/price mention (+0.3)
        if has_budget:
            intent_score += 0.3
            
        # Buyer verb (+0.3)
        if has_buyer_phrase or has_request_verb:
            intent_score += 0.3
            
        # Question mark (+0.2)
        if has_question:
            intent_score += 0.2
            
        # Urgency (+0.2)
        if has_urgency:
            intent_score += 0.2
            
        # First person pronoun (+0.1)
        if has_first_person:
            intent_score += 0.1
        
        # Swahili buyer terms (+0.2)
        if any(term in normalized for term in ["natafuta", "nahitaji", "nataka", "iko"]):
            intent_score += 0.2
        
        # Currency mention (+0.2)
        if re.search(r'\d+\s*(k|m|ksh|kes)', normalized):
            intent_score += 0.2
        
        # Cap at 1.0
        intent_score = min(intent_score, 1.0)
        
        # Seller penalty
        if seller_soft_hits >= 2:
            intent_score -= 0.3
        if seller_soft_hits >= 4:
            intent_score -= 0.5
            
        # Hard reject only obvious sellers
        has_hard_seller = any(word in normalized for word in SELLER_HARD_REJECT)
        if has_hard_seller:
            print(f"SCORING_REJECT: Hard seller signal in: {text[:60]}...")
            return False
        
        # Accept if score >= 0.25 (very low threshold for high recall)
        print(f"SCORING: intent={intent_score:.2f} seller_hits={seller_soft_hits} text={text[:60]}...")
        return intent_score >= 0.25
    
    # Standard mode: stricter filtering
    if seller_soft_hits >= 1 and not has_buyer_phrase and not has_first_person:
        logger.debug("REJECTED (Seller-heavy text)")
        return False

    score, _ = calculate_kenyan_intent_score(text)
    min_score = max(INTENT_POINTS_FLOOR, 30)

    if score < min_score:
        return False

    result = has_buyer_phrase or has_request_verb or buyer_evidence >= 3
    return result


def calculate_kenyan_intent_score(text: str, query_context: str = None):
    """
    Calculates intent score 0-100.
    RELAXED: Gives base points to everything, bonus for buyer signals.
    """
    normalized_text = normalize_text(text)
    score = 0
    details = []

    if not normalized_text:
        return 0, ["Empty text"]

    # 1. Hard seller → instant reject
    for word in SELLER_HARD_REJECT:
        if word in normalized_text:
            return -100, [f"Hard Seller: {word}"]

    # 2. BASE SCORE for any content (ensures leads show up)
    score = 5
    details.append("Base score (+5)")

    # 3. Seller Indicators -> -50 each
    for phrase in SELLER_INDICATORS:
        if phrase in normalized_text:
            score -= 50
            details.append(f"Seller Indicator: '{phrase}' (-50)")

    # 4. Buyer phrases → +35 each (max 2)
    buyer_count = 0
    for phrase in BUYER_INTENT_ALL:
        if phrase in normalized_text:
            if buyer_count < 2:
                score += 35
                details.append(f"Buyer: '{phrase}' (+35)")
            buyer_count += 1

    # 5. First person → +10
    for word in FIRST_PERSON_PRONOUNS:
        if re.search(r'\b' + re.escape(word) + r'\b', normalized_text):
            score += 10
            details.append(f"First Person: '{word}' (+10)")
            break

    # 6. Budget pattern → +25
    if re.search(r'\b\d+\s*(k|m|million|thousand|sh|ksh|kes)\b', normalized_text):
        score += 25
        details.append("Budget Pattern (+25)")

    # 7. Cash/payment → +20
    if any(w in normalized_text for w in ["cash", "pesa", "doh", "mpesa", "m-pesa", "payment"]):
        score += 20
        details.append("Cash/Payment (+20)")

    # 8. Urgency → +20
    if any(u in normalized_text for u in URGENCY_KEYWORDS):
        score += 20
        details.append("Urgency (+20)")

    # 9. Location → +10
    locations = [
        "nairobi", "mombasa", "kisumu", "nakuru", "eldoret", "thika",
        "kiambu", "westlands", "kilimani", "kileleshwa", "lavington",
        "karen", "ruaka", "syokimau", "kitengela", "juja", "rongai",
        "south b", "south c", "langata", "cbd", "kenya"
    ]
    if any(loc in normalized_text for loc in locations):
        score += 10
        details.append("Location (+10)")

    # 10. Phone number present → +15
    if re.search(r'(\+254|07|01)\d{8}', normalized_text):
        score += 15
        details.append("Phone Found (+15)")

    # 11. Question mark → +5 (inquiry behavior)
    if "?" in text:
        score += 5
        details.append("Question (+5)")

    # 12. Query context bonuses
    if query_context:
        q_norm = normalize_text(query_context)
        if any(w in q_norm for w in ["urgent", "asap"]):
            score += 20
            details.append("Query: Urgent (+20)")
        if "cash" in q_norm:
            score += 30
            details.append("Query: Cash (+30)")
        if "budget" in q_norm:
            score += 15
            details.append("Query: Budget (+15)")

    # 13. Ensure minimum floor
    if score < INTENT_POINTS_FLOOR:
        score = INTENT_POINTS_FLOOR
        details.append(f"Floor applied ({INTENT_POINTS_FLOOR})")

    return score, details


def classify_market_side(text: str):
    """Returns 'demand' or 'supply'."""
    return "demand" if is_valid_buyer(text) else "supply"

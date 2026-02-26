
# 🌍 Language Signals (English + Swahili + Sheng)
# Focused on Kenyan market intent detection.

ENGLISH_PATTERNS = [
    "looking for", "need", "want to buy", "where can i buy", "anyone selling",
    "need supplier", "need vendor", "urgent need", "searching for",
    "interested in buying", "i want to purchase", "how much is", "price for",
    "get me", "find me", "can i get", "i need a", "i need an",
    "looking to acquire", "in the market for", "seeking", "where to find",
    "who sells", "any leads on"
]

SWAHILI_PATTERNS = [
    "ninataka", "ninaomba", "ninahitaji", "napenda kununua",
    "ninaweza kupata wapi", "anayeiuza", "muuzaji", "duka",
    "bei ya", "nipe", "tafadhali nisaidie", "ninatafuta",
    "mahali pa kununua", "ninachotafuta", "ninahitaji muuzaji",
    "kuna mtu anayeuza", "ninaweza kupata", "nipatie",
    "ninaweza kununua", "nina shida ya", "natumai kupata",
    "ninatafuta muuzaji wa", "ninahitaji kununua", "natafuta", "nahitaji"
]

SHENG_PATTERNS = [
    "nataka", "nipe", "naeza pata", "ko wapi nipate", "una sell",
    "una kuuza", "ko bidii", "ko kitu", "naikua", "niskie",
    "ko na", "meko na", "niambie", "tupeane", "ko fresh",
    "niko na budget", "ko supply", "una supply", "nipe price",
    "ko bei", "nataka ku-buy", "ko link", "nao pia", "ko hio",
    "meko na hio", "nipatie", "ko pesa", "tunatafuta", "wanatafuta"
]

ALL_BUYER_PATTERNS = ENGLISH_PATTERNS + SWAHILI_PATTERNS + SHENG_PATTERNS

URGENCY_KEYWORDS = [
    "asap", "urgent", "immediately", "now", "today", "fast", 
    "needed by", "quick", "haraka", "sasa hivi"
]

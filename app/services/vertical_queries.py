# app/services/vertical_queries.py
# ============================================================
# KENYA VERTICAL-SPECIFIC BUYER TEMPLATES
# ============================================================
# Generic queries are weak. Kenyan buying behavior changes per industry.
# We optimize per vertical for maximum buyer recall.
# ============================================================

from typing import List, Dict, Callable
import re

# ============================================================
# REAL ESTATE (Highest Buyer Volume in Kenya)
# ============================================================
# How Kenyans search for property:
# - "Looking for 2br in Kileleshwa budget 45k"
# - "Natafuta bedsitter Rongai"
# - "3 bedroom for rent Syokimau"
# - "Need shop space CBD urgently"
# - "Within 30k", "Budget 5m", "Cash buyer", "Owner direct"
# ============================================================

REAL_ESTATE_SIGNALS = [
    # English signals
    "looking for",
    "for rent",
    "for sale",
    "budget",
    "cash buyer",
    "owner direct",
    "urgent",
    "need",
    "wanted",
    "available",
    "within",
    "price",
    # Swahili signals
    "natafuta",
    "nahitaji",
    "iko",
    "bei",
    # Short forms common in Kenya
    "2br", "3br", "4br",  # Bedroom shorthand
    "bedsitter",
    "sq",  # Servant quarters
]

# Popular Nairobi areas + other major Kenyan towns
REAL_ESTATE_AREAS = [
    # Nairobi neighborhoods (high volume)
    "Nairobi",
    "Kileleshha",
    "Rongai",
    "Syokimau",
    "Westlands",
    "CBD",
    "Kasarani",
    "Ruaka",
    "Kilimani",
    "Lavington",
    "Karen",
    "Muthaiga",
    "Parklands",
    "Ngong Road",
    "Thika Road",
    "Mombasa Road",
    "Waiyaki Way",
    "Jogoo Road",
    # Other major towns
    "Mombasa",
    "Kisumu",
    "Nakuru",
    "Eldoret",
    "Thika",
    "Kitengela",
    "Machakos",
]

REAL_ESTATE_PROPERTY_TYPES = [
    "apartment",
    "house",
    "bedsitter",
    "bedroom",
    "shop",
    "office",
    "warehouse",
    "land",
    "plot",
    "studio",
]


def generate_real_estate_queries(product: str, location: str = "Kenya") -> List[str]:
    """
    Generate real estate-specific queries for Kenya.
    
    Examples:
    - "2 bedroom" "Kileleshwa" "looking for"
    - "bedsitter" "Rongai" "natafuta"
    - "shop" "CBD" "for rent"
    """
    queries = []
    
    # Focus on top Nairobi areas (most buyer volume)
    top_areas = [
        "Nairobi", "Kileleshwa", "Westlands", "Kilimani", "Karen",
        "Rongai", "Syokimau", "Ruaka", "Kasarani", "CBD"
    ]
    
    # Key buyer signals for real estate
    key_signals = [
        "looking for", "natafuta", "for rent", "for sale",
        "budget", "cash buyer", "owner direct", "urgent"
    ]
    
    # Core combinations: product + area + signal (limited to keep query count reasonable)
    for signal in key_signals:
        for area in top_areas:
            queries.append(f'"{product}" "{area}" "{signal}"')
    
    # Platform-specific with site filters (top platforms only)
    platforms = ["site:facebook.com", "site:t.me", "site:jiji.co.ke"]
    for platform in platforms:
        for signal in ["looking for", "natafuta", "for rent"]:
            for area in top_areas[:5]:  # Top 5 areas only
                queries.append(f'{platform} "{product}" "{area}" "{signal}"')
    
    # Budget-specific queries (high intent)
    budget_phrases = ["budget", "cash buyer", "owner direct"]
    for phrase in budget_phrases:
        queries.append(f'"{product}" "{location}" "{phrase}"')
    
    # Urgency queries
    queries.append(f'"{product}" "{location}" urgent')
    queries.append(f'"{product}" "Nairobi" needed asap')
    
    return list(set(queries))


# ============================================================
# VEHICLE / CAR TEMPLATES
# ============================================================
# How Kenyans ACTUALLY search for cars:
# - "Natafuta Prado 2014"
# - "Looking for Axio 2018"
# - "Budget 1.2m"
# - "Clean unit"
# - "Owner selling?"
# - "Cash ready"
# - "Import or local?"
# ============================================================

# Kenya car buyer signals (authentic language)
VEHICLE_SIGNALS = [
    # Swahili (high intent)
    "natafuta",
    "nahitaji",
    "nataka",
    "gari",  # car
    # English buyer phrases
    "looking for",
    "wanted",
    "budget",
    "cash ready",
    "cash buyer",
    # Condition/quality signals
    "clean unit",
    "clean",
    "mint condition",
    "well maintained",
    "original paint",
    "low mileage",
    # Transaction type
    "owner selling",
    "owner",
    "direct owner",
    "buyer",
    # Origin
    "import",
    "local",
    "imported",
    "new shape",
    "old shape",
    # Urgency
    "urgent",
    "asap",
    # Transmission
    "automatic",
    "manual",
    "auto",
]

# Budget terms Kenyans actually use
VEHICLE_BUDGET_TERMS = [
    "300k", "400k", "500k", "600k", "700k", "800k", "900k",
    "1m", "1.2m", "1.5m", "1.8m", "2m", "2.5m", "3m", "4m", "5m",
    "1 m", "1.2 m", "1.5 m", "2 m",
    "1000000", "1200000", "1500000", "2000000",
]

# Common car models in Kenya (for query expansion)
POPULAR_CAR_MODELS = {
    "toyota": ["axio", "fielder", "hiace", "harrier", "prado", "rav4", "vitz", "passo"],
    "honda": ["fit", "civic", "crv", "accord"],
    "nissan": ["note", "xtrail", "tiida", "sylphy", "serena"],
    "mazda": ["demio", "axela", "cx5"],
    "subaru": ["impreza", "forester", "legacy", "outback"],
    "mercedes": ["c200", "e200", "c180", "e250"],
    "bmw": ["x5", "x3", "320i", "520i"],
}


def generate_vehicle_queries(product: str, location: str = "Kenya") -> List[str]:
    """
    Generate vehicle/car-specific queries for Kenya.
    Uses authentic Kenyan car buyer language.
    """
    queries = []
    
    # Core buyer signals (authentic Kenyan)
    signals = [
        "natafuta",
        "looking for",
        "cash ready",
        "budget",
        "owner selling",
        "clean unit",
        "urgent",
    ]
    
    for signal in signals:
        queries.append(f'"{product}" "{location}" "{signal}"')
    
    # Platform-specific
    platforms = ["site:facebook.com", "site:t.me", "site:jiji.co.ke"]
    for platform in platforms:
        queries.append(f'{platform} "{product}" "{location}" "natafuta"')
        queries.append(f'{platform} "{product}" "{location}" "looking for"')
    
    return list(set(queries))


# ============================================================
# FMCG / RETAIL / ELECTRONICS (B2B/Bulk Buyers)
# ============================================================
# How Kenyan retailers/businesses search:
# - "Bulk buyer of diapers"
# - "Wholesale price for rice"
# - "Need supplier for cosmetics"
# - "Stockist of soft drinks?"
# - "Where can I buy in bulk"
# - "Quantity 100 cartons"
# ============================================================

# FMCG/Retail related keywords for detection
FMCG_KEYWORDS = [
    "bulk", "wholesale", "supplier", "stockist", "distributor", "reseller",
    "cartons", "boxes", "quantity", "moq", "minimum order",
    "retail shop", "retail store", "business", "trade",
    "diapers", "cosmetics", "soap", "detergent", "rice", "sugar", "oil",
    "soft drinks", "beverages", "juice",
]


def generate_fmcg_queries(product: str, location: str = "Kenya") -> List[str]:
    """
    Generate FMCG/Retail/B2B bulk buyer queries for Kenya.
    Targets retailers, shop owners, and resellers.
    """
    queries = []
    
    # B2B buyer signals (wholesale/bulk focus)
    signals = [
        "bulk buyer",
        "wholesale price",
        "need supplier",
        "stockist",
        "where can i buy",
        "buying in bulk",
        "wholesale",
        "supplier needed",
        "distributor",
        "reseller",
        "retail price",
        "bulk order",
        "quantity",
    ]
    
    for signal in signals:
        queries.append(f'"{product}" "{location}" "{signal}"')
        queries.append(f'"{signal}" "{product}" "{location}"')
    
    # Business-focused queries
    queries.append(f'"{product}" "{location}" "for resale"')
    queries.append(f'"{product}" "{location}" "for my shop"')
    queries.append(f'"{product}" "{location}" "business"')
    queries.append(f'"{product}" "{location}" "retail"')
    
    # Quantity-specific (high intent)
    quantities = ["10", "20", "50", "100", "cartons", "boxes", "dozens"]
    for qty in quantities:
        queries.append(f'"{product}" "{location}" "{qty}"')
        queries.append(f'"{product}" "{qty}" "{location}" "buying"')
    
    # Platform-specific B2B
    platforms = ["site:facebook.com", "site:t.me"]
    for platform in platforms:
        queries.append(f'{platform} "{product}" "{location}" "wholesale"')
        queries.append(f'{platform} "{product}" "{location}" "supplier"')
        queries.append(f'{platform} "{product}" "{location}" "bulk"')
    
    return list(set(queries))


# ============================================================
# ELECTRONICS / PHONES / LAPTOPS (Consumer)
# ============================================================
# How Kenyans search for electronics:
# - "iPhone 13 pro max 85k"
# - "Natafuta laptop ya 30k"
# - "Samsung A54 budget 25k"
# - "HP laptop i5 urgently"
# ============================================================

ELECTRONICS_SIGNALS = [
    "looking for",
    "wanted",
    "budget",
    "natafuta",
    "nahitaji",
    "used",
    "refurbished",
    "new",
    "box",  # "with box"
    "warranty",
    "urgent",
    "cash",
]


def generate_electronics_queries(product: str, location: str = "Kenya") -> List[str]:
    """Generate electronics/phones/laptops-specific queries for Kenya."""
    queries = []
    
    # Standard electronics signals
    for signal in ELECTRONICS_SIGNALS:
        queries.append(f'"{product}" "{location}" "{signal}"')
    
    # Common budget ranges for electronics
    budget_ranges = ["5k", "10k", "15k", "20k", "25k", "30k", "40k", "50k", "60k", "80k", "100k"]
    for budget in budget_ranges:
        queries.append(f'"{product}" "{location}" "{budget}"')
    
    # Condition-specific
    queries.append(f'"{product}" "{location}" "slightly used"')
    queries.append(f'"{product}" "{location}" "mint condition"')
    
    # Platform-specific
    platforms = ["site:facebook.com", "site:t.me", "site:jiji.co.ke"]
    for platform in platforms:
        queries.append(f'{platform} "{product}" "{location}" "looking for"')
        queries.append(f'{platform} "{product}" "{location}" "budget"')
    
    return list(set(queries))


# ============================================================
# CONSTRUCTION / FUNDIS (Huge Kenyan Market)
# ============================================================
# How Kenyans ACTUALLY search for construction workers:
# - "Looking for fundi wa tiles"
# - "Need plumber Ruaka"
# - "Natafuta gypsum fundi"
# - "Any electrician around Kasarani?"
# - "Who knows a good carpenter?"
# ============================================================

# Construction/fundi related keywords for detection
CONSTRUCTION_KEYWORDS = [
    "fundi", "plumber", "electrician", "carpenter", "mason", "painter",
    "tiler", "tiles", "gypsum", "cabro", "welder", "roofing",
    "aluminium", "glass", "waterproofing", "renovation", "repair",
    " Pop ", "pop ceiling", "biodigester", "septic", "excavation",
    "construction", "building", "contractor", "site"
]

# Construction worker types
CONSTRUCTION_TRADES = [
    "plumber", "electrician", "carpenter", "mason", "painter",
    "tiler", "welder", "roofer", "glazier", "bricklayer"
]


def generate_construction_queries(service: str, location: str = "Kenya") -> List[str]:
    """
    Generate construction/fundi-specific queries for Kenya.
    Huge market - Kenyans constantly need skilled workers.
    """
    queries = []
    
    # Core buyer signals (authentic Kenyan construction search)
    signals = [
        "looking for",
        "natafuta",
        "any fundi",
        "who knows",
        "need urgently",
        "recommend",
        "need",
        "nahitaji",
        "around",
    ]
    
    for signal in signals:
        queries.append(f'"{service}" "{location}" "{signal}"')
    
    # Fundi-specific patterns (very common in Kenya)
    # "fundi wa [service]" = "expert for [service]"
    queries.append(f'"fundi wa {service}" "{location}"')
    queries.append(f'"fundi wa {service}" "Nairobi"')
    
    # Alternative: "[service] fundi"
    queries.append(f'"{service} fundi" "{location}"')
    
    # Recommendation patterns
    queries.append(f'"who knows {service}" "{location}"')
    queries.append(f'"any good {service}" "{location}"')
    queries.append(f'"recommend {service}" "{location}"')
    
    # Urgency patterns (very common)
    queries.append(f'"{service}" "{location}" "urgently"')
    queries.append(f'"{service}" "{location}" "needed today"')
    queries.append(f'"{service}" "{location}" "asap"')
    queries.append(f'"{service}" "{location}" "haraka"')
    
    # Platform-specific (where Kenyans find fundis)
    platforms = ["site:facebook.com", "site:t.me"]
    for platform in platforms:
        queries.append(f'{platform} "fundi wa {service}" "{location}"')
        queries.append(f'{platform} "{service}" "{location}" "looking for"')
        queries.append(f'{platform} "{service}" "{location}" "natafuta"')
    
    # Area-specific (common Kenyan pattern: "service around area")
    queries.append(f'"{service}" around "{location}"')
    queries.append(f'"{service}" near "{location}"')
    
    return list(set(queries))


# ============================================================
# SERVICES (Fundi, Repairs, Professional Services)
# ============================================================
# How Kenyans search for services:
# - "Fundi wa tiles Karen"
# - "Need plumber urgently Lavington"
# - "Electrician available today"
# - "Natafuta mwanasheria"
# ============================================================

SERVICES_SIGNALS = [
    "fundi wa",  # Expert for/repairer of
    "need",
    "looking for",
    "natafuta",
    "nahitaji",
    "urgently",
    "available",
    "today",
    "haraka",
    "professional",
    "expert",
    "recommended",
]


def generate_services_queries(product: str, location: str = "Kenya") -> List[str]:
    """Generate services/fundi-specific queries for Kenya."""
    queries = []
    
    # Standard service signals
    for signal in SERVICES_SIGNALS:
        queries.append(f'"{product}" "{location}" "{signal}"')
    
    # Fundi-specific (very common Kenyan pattern)
    queries.append(f'"fundi wa {product}" "{location}"')
    queries.append(f'"fundi wa {product}" "Nairobi"')
    
    # Urgency-based
    queries.append(f'"{product}" "{location}" "urgently"')
    queries.append(f'"{product}" "{location}" "needed today"')
    
    # Recommendation-based
    queries.append(f'"{product}" "{location}" "who knows"')
    queries.append(f'"{product}" "{location}" "any recommendations"')
    
    return list(set(queries))


# ============================================================
# VERTICAL DETECTION & ROUTING
# ============================================================

def detect_vertical(product: str) -> str:
    """
    Detect which vertical a product belongs to.
    Returns: 'real_estate', 'vehicle', 'electronics', 'fmcg', 'construction', 'services', or 'general'
    """
    product_lower = product.lower()
    
    # FMCG keywords (check first for B2B signals)
    for keyword in FMCG_KEYWORDS:
        if keyword in product_lower:
            return 'fmcg'
    
    # Construction keywords (check early - high priority)
    for keyword in CONSTRUCTION_KEYWORDS:
        if keyword in product_lower:
            return 'construction'
    
    # Real estate keywords
    real_estate_keywords = [
        'house', 'apartment', 'rent', 'bedroom', 'bedsitter', 'sq', 'shop', 
        'office', 'warehouse', 'land', 'plot', 'studio', 'flat', 'to let',
        '2br', '3br', '4br', '1br', '2 bedroom', '3 bedroom', '4 bedroom',
        'kileleshwa', 'rongai', 'syokimau', 'westlands', 'kilimani', 'karen',
    ]
    
    # Vehicle keywords
    vehicle_keywords = [
        'car', 'toyota', 'honda', 'nissan', 'mazda', 'subaru', 'bmw', 'mercedes',
        'vw', 'volkswagen', 'suzuki', 'mitsubishi', 'gari', 'vehicle', 'truck',
        'van', 'matatu', 'motorcycle', 'bike', 'boda', 'pickup', 'prado', 'harrier',
    ]
    
    # Electronics keywords
    electronics_keywords = [
        'phone', 'iphone', 'samsung', 'xiaomi', 'oppo', 'tecno', 'infinix',
        'laptop', 'hp', 'dell', 'lenovo', 'macbook', 'computer', 'desktop',
        'tv', 'television', 'samsung', 'sony', 'lg', 'speaker', 'camera',
        'tablet', 'ipad', 'charger', 'earphones', 'headphones',
    ]
    
    # Services keywords (non-construction)
    services_keywords = [
        'accountant', 'lawyer', 'advocate', 'cleaner', 'nanny', 'househelp',
        'driver', 'security', 'guard', 'tailor', 'hairdresser', 'barber', 'caterer',
    ]
    
    # Check each vertical
    for keyword in real_estate_keywords:
        if keyword in product_lower:
            return 'real_estate'
    
    for keyword in vehicle_keywords:
        if keyword in product_lower:
            return 'vehicle'
    
    for keyword in electronics_keywords:
        if keyword in product_lower:
            return 'electronics'
    
    for keyword in services_keywords:
        if keyword in product_lower:
            return 'services'
    
    return 'general'


# Registry of vertical generators
VERTICAL_GENERATORS: Dict[str, Callable[[str, str], List[str]]] = {
    'real_estate': generate_real_estate_queries,
    'vehicle': generate_vehicle_queries,
    'electronics': generate_electronics_queries,
    'fmcg': generate_fmcg_queries,
    'construction': generate_construction_queries,
    'services': generate_services_queries,
}


def generate_vertical_queries(product: str, location: str = "Kenya") -> List[str]:
    """
    Generate vertical-specific queries for Kenya.
    
    Automatically detects the vertical and uses appropriate templates.
    Falls back to general buyer queries if no vertical detected.
    
    Args:
        product: Product or service being searched for
        location: Location (default: Kenya)
    
    Returns:
        List of optimized search queries
    """
    vertical = detect_vertical(product)
    
    if vertical in VERTICAL_GENERATORS:
        return VERTICAL_GENERATORS[vertical](product, location)
    
    # Generic fallback for non-vertical products
    return _generate_generic_queries(product, location)


def _generate_generic_queries(product: str, location: str = "Kenya") -> List[str]:
    """Generic fallback query generator for non-vertical products."""
    product = product.strip()
    location = location.strip()

    # Core buyer intent signals
    buyer_signals = [
        "looking for", "need urgently", "want to buy", "wtb",
        "natafuta", "nahitaji", "who has", "any leads", "budget", "within",
    ]

    # Kenya-specific platforms
    site_filters = [
        "site:facebook.com", "site:t.me", "site:jiji.co.ke", "site:pigiame.co.ke"
    ]

    queries = []

    # Generate systematic combinations
    for signal in buyer_signals:
        for site in site_filters:
            queries.append(f'{site} "{product}" "{location}" "{signal}"')

    # General high recall (non-site-specific)
    queries.append(f'"{product}" "{location}" looking for')
    queries.append(f'"{product}" "{location}" natafuta')

    return list(set(queries))

import re 
from typing import Dict, Optional 
 
KENYA_PHONE_REGEX = re.compile(r'(\+254\d{9}|0[71]\d{8})') 
 
KENYA_CITIES = [ 
    "nairobi", 
    "mombasa", 
    "kisumu", 
    "nakuru", 
    "eldoret", 
    "thika", 
    "kiambu", 
    "machakos", 
    "meru", 
    "nyeri" 
] 
 
SWAHILI_BUYER_SIGNALS = [ 
    "natafuta", 
    "nahitaji", 
    "bei gani", 
    "nani anauza", 
    "nataka", 
    "tafuta" 
] 
 
 
def compute_geo_score( 
    text: str, 
    query: Optional[str] = None, 
    location: Optional[str] = None 
) -> Dict: 
    """ 
    Dynamic Kenya geo scoring. 
    Works for ANY search query. 
    """ 
 
    if not text: 
        return { 
            "geo_score": 0.0, 
            "geo_strength": "low", 
            "geo_region": None 
        } 
 
    text_lower = text.lower() 
    phone_score = 0.0 
    city_score = 0.0 
    language_score = 0.0 
    query_match_score = 0.0 
    detected_region = None 
 
    # 1️⃣ Phone Detection 
    if KENYA_PHONE_REGEX.search(text): 
        phone_score = 0.4 
 
    # 2️⃣ City Detection 
    for city in KENYA_CITIES: 
        if city in text_lower: 
            city_score = 0.3 
            detected_region = city.title() 
            break 
 
    # 3️⃣ Swahili Intent Signals 
    for phrase in SWAHILI_BUYER_SIGNALS: 
        if phrase in text_lower: 
            language_score = 0.2 
            break 
 
    # 4️⃣ Query Match Boost (NEW) 
    if query and query.lower() in text_lower: 
        query_match_score = 0.1 
 
    # 5️⃣ Location Boost (if user specified) 
    if location and location.lower() in text_lower: 
        city_score = max(city_score, 0.4) 
        detected_region = location.title() 
 
    geo_score = min( 
        phone_score + city_score + language_score + query_match_score, 
        1.0 
    ) 
 
    if geo_score >= 0.7: 
        strength = "high" 
    elif geo_score >= 0.4: 
        strength = "medium" 
    else: 
        strength = "low" 
 
    return { 
        "geo_score": round(geo_score, 3), 
        "geo_strength": strength, 
        "geo_region": detected_region 
    }

def calculate_geo_score(lead: Dict) -> Dict:
    """
    🎯 The Intelligence Wrapper:
    Calculates geo score for a lead dictionary and updates it.
    Used by the legacy geo_bias utility.
    """
    text = lead.get("buyer_request_snippet") or lead.get("text") or ""
    query = lead.get("product_category") or lead.get("query")
    location = lead.get("location_raw") or lead.get("location")
    
    geo_data = compute_geo_score(text, query=query, location=location)
    lead.update(geo_data)
    return lead

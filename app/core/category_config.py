from typing import List, Dict, Any

class CategoryConfig:
    """Central configuration for market categories to enable rapid pipeline cloning."""
    
    CATEGORIES = {
        "vehicles": {
            "name": "Vehicles",
            "keywords": [
                "car", "vehicle", "toyota", "nissan", "subaru", "isuzu", "mazda", "honda", "mitsubishi",
                "prado", "vitz", "land cruiser", "hilux", "demio", "note", "forester", "truck", "pickup",
                "van", "bus", "spare parts", "engine", "gearbox", "tyre", "rim", "brakes"
            ],
            "search_terms": ["vehicles", "cars", "toyota", "nissan", "subaru", "isuzu"],
            "locations": ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret"],
            "price_bands": {
                "budget": [0, 500000],
                "mid": [500000, 1500000],
                "premium": [1500000, 5000000],
                "luxury": [5000000, 100000000]
            },
            "language_templates": {
                "buy": ["looking for", "where can i buy", "anyone selling", "natafuta", "nahitaji"],
                "sell": ["selling", "available", "on sale", "for sale"]
            },
            "is_active": True
        },
        "general": {
            "name": "General / Catch-All",
            "keywords": [
                "phone", "laptop", "job", "house", "car", "land", "plot", "furniture", 
                "clothes", "shoes", "tv", "fridge", "sofa", "bed", "book", "service", 
                "repair", "training", "course", "event", "ticket", "deal", "offer", 
                "nairobi", "kenya", "mombasa", "kisumu", "toy", "spoon", "kitchen",
                "household", "baby", "beauty", "fashion", "garden", "tools", "pet"
            ],
            "search_terms": [
                "for sale", "on sale", "kwa mnada", "inauzwa", "available", "ipo", 
                "looking for", "need", "natafuta", "nahitaji", "hiring", "kazi", 
                "to let", "kupanga", "rent", "service", "offer", "deal", "promo",
                "buy", "sell", "price", "cost", "wanted"
            ],
            "locations": ["Kenya", "Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret", "Kiambu", "Machakos", "Kajiado", "Thika"],
            "price_bands": {},
            "language_templates": {
                "buy": ["looking for", "want to buy", "need", "natafuta", "nahitaji", "anyone selling"],
                "sell": ["selling", "for sale", "inauzwa", "available", "ipo", "kwa mnada"]
            },
            "is_active": True
        },
        "real_estate": {
            "name": "Real Estate",
            "keywords": ["apartment", "house", "land", "plot", "rental", "bedsitter", "office space", "commercial"],
            "search_terms": ["apartment for rent", "house for sale", "land in kenya"],
            "locations": ["Nairobi", "Kiambu", "Machakos", "Kajiado"],
            "price_bands": {
                "rental_budget": [0, 20000],
                "rental_mid": [20000, 60000],
                "sale_mid": [1000000, 10000000]
            },
            "language_templates": {
                "buy": ["looking for house", "apartment needed", "natafuta shamba"],
                "sell": ["to let", "vacant", "for sale"]
            },
            "is_active": True
        },
        "electronics": {
            "name": "Electronics",
            "keywords": ["iphone", "samsung", "laptop", "macbook", "ps5", "tv", "camera", "fridge"],
            "search_terms": ["iphone", "macbook", "samsung", "laptop"],
            "locations": ["Nairobi", "Mombasa"],
            "price_bands": {},
            "language_templates": {
                "buy": ["looking for phone", "where can i buy iphone"],
                "sell": ["available", "brand new", "refurbished"]
            },
            "is_active": True
        }
    }

    @classmethod
    def get_config(cls, category_name: str) -> Dict[str, Any]:
        return cls.CATEGORIES.get(category_name)

    @classmethod
    def get_active_categories(cls) -> List[str]:
        return [k for k, v in cls.CATEGORIES.items() if v["is_active"]]

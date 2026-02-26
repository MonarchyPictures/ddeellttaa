import logging
import re
from datetime import datetime, timedelta, timezone

from ..intelligence.intent import BUYER_PATTERNS

logger = logging.getLogger(__name__)

class BuyingIntentNLP:
    def __init__(self):
        try:
            import spacy
            # Attempt to load spaCy model safely
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("✅ spaCy model loaded successfully.")
        except Exception as e:
            logger.warning(f"⚠️ spaCy model failed to load (Pydantic V1/V2 conflict likely): {e}. Using Regex Fallback.")
            self.nlp = None
        
        self.intent_patterns = BUYER_PATTERNS

    def extract_entities(self, text, category_config=None):
        """Extract products, locations, names, and prices."""
        entities = {"products": [], "locations": [], "names": [], "price": None}
        
        # Price extraction (KES/K/M formats)
        price_match = re.search(r'\b(kes|ksh|sh|shillings)?\s*(\d{1,3}(?:,\d{3})*|\d+)\s*(k|m|million|milio)?\b', text, re.IGNORECASE)
        if price_match:
            try:
                val = float(price_match.group(2).replace(',', ''))
                multiplier = price_match.group(3).lower() if price_match.group(3) else ''
                if multiplier in ['k']: val *= 1000
                elif multiplier in ['m', 'million', 'milio']: val *= 1000000
                entities["price"] = val
            except: pass

        if self.nlp:
            try:
                doc = self.nlp(text)
                entities["locations"] = [ent.text for ent in doc.ents if ent.label_ in ["GPE", "LOC"]]
                entities["names"] = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
                
                # Simple product extraction logic (Noun Phrases)
                for chunk in doc.noun_chunks:
                    if not any(word in chunk.text.lower() for word in self.intent_patterns):
                        entities["products"].append(chunk.text)
                return entities
            except Exception:
                pass # Fallback to regex if spacy fails at runtime

        # REGEX FALLBACK
        # Basic Kenya location detection
        kenya_cities = ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret", "Kenya", "Thika", "Naivasha", "Malindi"]
        for city in kenya_cities:
            if re.search(rf"\b{city}\b", text, re.IGNORECASE):
                entities["locations"].append(city)
        
        # Product Specificity Algorithm
        # Extract specs like size (50,000l, 10kg), model (2005, v8), price (50k)
        specs = {}
        # Improved regex for numbers with commas and units
        size_match = re.search(r'(\d{1,3}(?:,\d{3})*|\d+)\s*(l|liters|kg|units|pcs|pieces|ton|tons|ft|inches)\b', text, re.IGNORECASE)
        if size_match:
            specs["size"] = f"{size_match.group(1)} {size_match.group(2)}"
            
        model_match = re.search(r'\b(20\d{2}|19\d{2})\b', text)
        if model_match:
            specs["model_year"] = model_match.group(1)

        entities["specs"] = specs
        
        # Basic name detection (Capitalized words that aren't start of sentence)
        
        # Basic product detection (words after intent patterns)
        # Improved product extraction: look for nouns after intent keywords
        noise_words = [
            'clean', 'new', 'used', 'cheap', 'good', 'searching', 'looking', 
            'it', 'this', 'that', 'something', 'someone', 'delivered', 
            'to', 'for', 'a', 'an', 'the', 'in', 'at', 'by', 'with', 'asap',
            'delivery', 'urgent', 'urgently', 'me', 'us', 'i', 'my'
        ]
        
        for pattern in self.intent_patterns:
            # Match until a known delimiter or end of sentence, but be greedy enough to capture the product
            # Use non-greedy match to stop at first delimiter
            match = re.search(rf"{pattern}\s+(?:a|an|the)?\s*([\w\s,]+?)(?:\s+in\b|\s+at\b|\s+by\b|\s+with\b|\s+for\b|\s+asap\b|\s+delivered\b|\.|$)", text, re.IGNORECASE)
            if match:
                product_raw = match.group(1).strip()
                # Split by common conjunctions and take the first part if it's too long
                product_parts = re.split(r'\b(and|or|with|to)\b', product_raw, flags=re.IGNORECASE)
                product = product_parts[0].strip()
                
                # Clean up product string (remove common noise)
                words = product.split()
                cleaned_words = [w for w in words if w.lower() not in noise_words]
                product = " ".join(cleaned_words).strip()
                
                # Further filter: if it contains a city/neighborhood, it's likely noise or location
                is_location = any(loc.lower() in product.lower() for loc in entities["locations"])
                if not is_location and product and len(product) > 3: 
                    if product.lower() not in [p.lower() for p in entities["products"]]:
                        entities["products"].append(product)
        
        return entities

    def calculate_confidence(self, text, has_phone=False, extracted_price=None, price_bands=None):
        """Calculate a confidence score (0.0 - 1.0) for a lead signal."""
        score = 0.5
        text_lower = text.lower()
        
        # 1. Phone presence is the strongest signal (+0.3)
        if has_phone:
            score += 0.3
            
        # 2. Price alignment with category bands (+0.1 or -0.2)
        if extracted_price and price_bands:
            # Check if price falls into any of the bands
            in_band = False
            for band_name, (min_p, max_p) in price_bands.items():
                if min_p <= extracted_price <= max_p:
                    in_band = True
                    break
            if in_band: score += 0.1
            else: score -= 0.2 # Out of band price is suspicious for this category
            
        # 2. High-intent keywords (+0.1 each, max 0.2)
        intent_matches = 0
        for pattern in self.intent_patterns:
            if pattern in text_lower:
                intent_matches += 1
                score += 0.1
                if intent_matches >= 2:
                    break
                    
        # 3. Vehicle-specific high-confidence brands (+0.1)
        vehicle_brands = ["toyota", "nissan", "subaru", "isuzu", "mazda", "honda", "mitsubishi", "prado", "vitz", "v8", "hilux"]
        if any(brand in text_lower for brand in vehicle_brands):
            score += 0.1
            
        # 4. Urgency signals (+0.1)
        urgency_keywords = ["urgent", "urgently", "asap", "haraka", "now", "today"]
        if any(u in text_lower for u in urgency_keywords):
            score += 0.1
            
        return min(1.0, score)
                
        return entities

    def analyze_readiness(self, text):
        """
        Classify Buyer Readiness:
        - HOT: Immediate purchase intent + specs + urgency
        - WARM: Interest + products
        - RESEARCHING: General mentions
        """
        text_lower = text.lower()
        score = self.calculate_intent_score(text)
        
        # Urgency Indicators
        urgency_keywords = ["asap", "urgent", "immediately", "now", "today", "fast", "needed by", "quick"]
        has_urgency = any(u in text_lower for u in urgency_keywords)
        
        # Spec Indicators (Size, Model, Price)
        has_specs = bool(re.search(r'(\d+)\s*(l|kg|units|pcs|ton|20\d{2}|ksh|sh|k\b)', text_lower))
        
        # Classification
        if score > 0.7 and (has_urgency or has_specs):
            return "HOT", min(score * 10, 10.0)
        elif score > 0.4:
            return "WARM", min(score * 8, 10.0)
        else:
            return "RESEARCHING", min(score * 5, 10.0)

    def extract_budget(self, text):
        """Extract price mentions or budget ranges."""
        # Kenyan budget formats: Ksh 50k, 50,000/-, 50k, 50000 sh
        budget_pattern = r'(ksh|sh|shilling|shillings)?\s*(\d{1,3}(?:,\d{3})*|\d+)\s*(k|m)?\s*(/-|sh|ksh)?'
        match = re.search(budget_pattern, text, re.IGNORECASE)
        if match:
            val = match.group(2).replace(',', '')
            suffix = match.group(3).lower() if match.group(3) else ''
            if suffix == 'k': val = f"{int(val) * 1000}"
            elif suffix == 'm': val = f"{int(val) * 1000000}"
            return f"Ksh {int(val):,}"
        return "Negotiable"

    def classify_intent(self, text):
        """
        Final AI Intent Classifier (The Lock 🔒)
        Classify this post strictly as one of the following:
        BUYER, SELLER, or UNCLEAR.
        
        ENFORCEMENT RULES (MANDATORY):
        1. IF text contains selling language AND does NOT contain buyer language -> SELLER -> EXCLUDE.
        2. IF buyer language is missing -> intent = UNKNOWN/UNCLEAR -> EXCLUDE.
        3. NO IMPLICIT ASSUMPTIONS (Product mention != Buyer intent).
        """
        text_lower = text.lower()
        
        # 1. HARD SELLER BLOCK LIST (ABSOLUTE)
        seller_blacklist = [
            "for sale", "selling", "available", "price", "discount", "offer", 
            "promo", "delivery", "in stock", "we sell", "shop", "dealer", 
            "supplier", "warehouse", "order now", "dm for price", 
            "call / whatsapp", "our store", "brand new", "limited stock",
            "flash sale", "retail price", "wholesale", "best price",
            "check out", "visit us", "located at", "we deliver", "buy from us",
            "contact for price", "special offer", "new arrival", "stockist",
            "dm to order", "shipping available", "price is", "kwa bei ya",
            "tunauza", "mzigo mpya", "punguzo", "call me for", "contact me for",
            "we are selling", "buy now", "click here", "follow us", "best deals",
            "order today", "price:", "contact:", "dm for", "sold by", "authorized dealer",
            "warranty included", "limited time offer", "check price", "get yours",
            "brand new", "imported", "affordable", "wholesale price", "retail",
            "visit our shop", "we are located", "delivery available", "countrywide",
            "pay on delivery", "lipa baada ya", "mzigo umefika", "bei nafuu",
            "tuko na", "pata yako", "agiza sasa", "welcome to", "call us", "contact us",
            "our shop", "our store", "check our", "see more", "click the link",
            "available in", "brand new", "we offer", "we provide", "expert in",
            "specializing in", "quality service", "best in kenya", "top rated",
            # User-Specific Aggressive Blocklist (Layer 1)
            "shop", "buy online", "for sale", "order now", "call now", 
            "dealer", "official store", "we ship", "delivery available", 
            "price negotiable", "stock available", "visit our store", 
            "add to cart", "checkout", "website link",

            # Previous Blocklist
            "shop and buy", "digital store", "we ship", "call to order", 
            "leading dealer", "products dealer", "negotiable", "ksh", "kes", "/="
        ]
        
        # 2. EXPLICIT BUYER SIGNALS (ONLY THESE COUNT)
        buyer_keywords = [
            "looking for", "need", "need urgently", "want to buy", 
            "where can i buy", "anyone selling", "recommend me", 
            "who sells", "where can i get", "seeking", "iso", "wtb",
            "can i get", "i need", "anyone with", "looking to buy",
            "recommendation for", "best place to buy", "recommend a supplier",
            "natafuta", "nahitaji", "nimehitaji", "nataka kununua", 
            "ni wapi naweza pata", "mnisaidie kupata", "iko wapi",
            "nitapata wapi", "nataka", "unauza wapi", "how much is",
            "price for", "get one", "find one", "looking at buying",
            "recommend", "anyone know where", "where to get",
            "naomba", "tafadhali", "nisaidie", "mwenye anajua",
            "help me find", "assist me", "where can i find",
            "who has", "anyone having", "where is", "buying at",
            "budget is", "searching for", "trying to find", "trying to get",
            "want to get", "looking to find", "in search of", "does anyone have",
            "where can one buy", "where can one find"
        ]
        
        # 3. RULE: "who sells?" = BUYER, "selling" = SELLER
        # Refining buyer questions: Must be specific buyer-type questions, not general marketing questions
        buyer_questions = [
            "who sells", "anyone selling", "who is selling", "who has", 
            "where can i find", "where can i get", "anyone with", 
            "anyone selling?", "does anyone have", "is anyone selling",
            "how much is", "price of", "where is", "ni wapi naweza pata",
            "iko wapi", "nitapata wapi"
        ]
        
        # Check if it's a buyer question - avoid marking marketing questions as buyer intent
        is_buyer_question = any(bq in text_lower for bq in buyer_questions)
        
        # If it ends with a question mark, check if it contains a product and a buyer signal
        if text_lower.endswith('?') and not is_buyer_question:
            # Marketing questions often start with "looking for..." or "need..." to attract attention
            # e.g., "Looking for tires? Welcome to X."
            # We only count it as a buyer question if it doesn't have seller language
            is_seller_marketing = any(s in text_lower for s in ["welcome to", "visit us", "call us", "contact us", "our shop", "we are located"])
            if not is_seller_marketing:
                is_buyer_question = True
        
        # 4. ENFORCEMENT LOGIC
        is_seller = any(s in text_lower for s in seller_blacklist)
        is_buyer = any(b in text_lower for b in buyer_keywords)
        
        # MANDATORY OVERRIDE: IF SELLING LANGUAGE IS PRESENT AND NOT A CLEAR BUYER QUESTION -> SELLER
        if is_seller:
            # Strong rejection for classic marketing language even if it contains "looking for"
            seller_only_phrases = [
                "dm to order", "we deliver", "shop located at", "our store", 
                "authorized dealer for", "warranty included", "pay on delivery",
                "welcome to", "visit us", "call us", "contact us", "our shop", 
                "we are located", "check our", "see more", "click the link",
                "brand new", "available in", "in stock", "our website", "follow us"
            ]
            if any(s in text_lower for s in seller_only_phrases):
                return "SELLER"

            # If it has seller language, it MUST have strong buyer language AND a personal signal
            has_strong_buyer = any(b in text_lower for b in ["looking for", "need", "natafuta", "nahitaji", "want to buy", "where can i get"])
            personal_intent_signals = [
                "i ", "me ", "we ", "my ", "natafuta", "nahitaji", "nataka", 
                "i'm", "im ", "i am", "help me", "looking for",
                "mnisaidie", "nimehitaji", "want to", "looking to", "can i get",
                "trying to", "seeking", "searching", "anyone", "who has", "where is"
            ]
            has_personal_signal = any(p in text_lower for p in personal_intent_signals)
            
            if not is_buyer_question and not (has_strong_buyer and has_personal_signal):
                return "SELLER"

        # RULE: MUST HAVE EXPLICIT BUYER SIGNAL
        if not is_buyer and not is_buyer_question:
            # Fallback for very clear questions even without keywords
            if "?" in text_lower and any(kw in text_lower for kw in ["get", "buy", "find", "pata", "iko"]):
                return "BUYER"
            
            logger.info(f"⚠️ Flagged: No explicit buyer signal in: {text_lower[:50]}...")
            return "UNCLEAR"
        
        # RULE: Personal Intent Verification (Must be first-person or question)
        personal_intent_signals = [
            "i ", "me ", "we ", "my ", "natafuta", "nahitaji", "nataka", 
            "i'm", "im ", "i am", "help me", "looking for",
            "mnisaidie", "nimehitaji", "want to", "looking to", "can i get",
            "trying to", "seeking", "searching"
        ]
        has_personal_signal = any(p in text_lower for p in personal_intent_signals)
        
        # Final Decision
        if has_personal_signal or is_buyer_question:
            # Additional check: length (too short posts are usually spam or unclear)
            if len(text_lower) < 10 and not is_buyer_question:
                logger.info(f"⚠️ Flagged: Too short: {text_lower[:50]}...")
                return "UNCLEAR"
            
            # Final check to avoid e-commerce noise: "price is", "buy now"
            if any(s in text_lower for s in ["price is", "buy now", "order today"]) and not "looking for" in text_lower:
                logger.info(f"⚠️ Flagged: E-commerce noise: {text_lower[:50]}...")
                return "SELLER"
            
            logger.info(f"✅ Accepted: BUYER intent found in: {text_lower[:50]}...")
            return "BUYER"
        
        logger.info(f"⚠️ Flagged: No personal intent signal in: {text_lower[:50]}...")
        return "UNCLEAR"

    def calculate_intent_score(self, text):
        """Calculate intent using linguistic features."""
        score = 0.0
        text_lower = text.lower()
        
        # 1. Keyword match (Strong intent signals)
        high_intent = [
            "looking for", "want to buy", "buying", "need to purchase", 
            "searching for", "where can i find", "anyone selling", 
            "recommend", "where can i buy", "need urgently", "dm me", 
            "inbox me", "wtb", "ready to buy", "trying to find", "trying to get",
            "want to get", "looking to find", "in search of", "natafuta", "nahitaji"
        ]
        # Add imported BUYER_PATTERNS to high_intent
        for p in self.intent_patterns:
            if p not in high_intent:
                high_intent.append(p)

        medium_intent = [
            "price for", "how much is", "cost of", "recommendations for", 
            "best place for", "who has", "where is", "anyone know where",
            "where to get", "any leads", "budget is", "can i get", "i need"
        ]
        
        # Social media specific intent signals + Emojis
        social_intent = ["pls assist", "help me find", "anyone know where", "kindly suggest", "where to get", "💰", "🏠", "🚗", "📦", "📱"]
        if any(si in text_lower for si in social_intent):
            score += 0.35

        # Kenya-Specific High Intent Keywords
        kenya_intent = ["nimehitaji", "natafuta", "nahitaji", "nimehitaji", "iko wapi", "bei gani", "nitapata wapi"]
        if any(ki in text_lower for ki in kenya_intent):
            score += 0.4

        for pattern in high_intent:
            if pattern in text_lower:
                score += 0.5 # Increased from 0.4
                break 
                
        for pattern in medium_intent:
            if pattern in text_lower:
                score += 0.3 # Increased from 0.2
                break
        
        # 2. Urgency check
        urgency_keywords = ["urgent", "asap", "immediately", "now", "today", "fast"]
        if any(u in text_lower for u in urgency_keywords):
            score += 0.3
            
        # 3. Contact info check (High intent signal)
        if re.search(r'(\+?254|0)(7|1)\d{8}', text) or re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text):
            score += 0.3
            
        # 4. Quantity/Budget signals
        if re.search(r'\b\d+\s*(kg|liters|l|units|pieces|pcs|ksh|sh)\b', text_lower):
            score += 0.2
            
        # 5. Length penalty/bonus
        if len(text_lower) < 30:
            if any(p in text_lower for p in high_intent):
                score -= 0.1
            else:
                score -= 0.3
        elif 50 < len(text_lower) < 300:
            score += 0.1

        final_score = max(0.0, min(score, 1.0))
        # print(f"📊 Intent Score: {final_score:.2f} for text: {text_lower[:50]}...")
        return final_score

    def analyze_intent_extensions(self, text):
        """Extract quantity, payment methods, etc."""
        text_lower = text.lower()
        
        # 1. Quantity Detection
        quantity = "Single Unit"
        qty_match = re.search(r'(\d{1,3}(?:,\d{3})*|\d+)\s*(units|pcs|pieces|kg|liters|l|ton|bags|boxes)', text_lower)
        if qty_match:
            quantity = f"{qty_match.group(1)} {qty_match.group(2)}"
        elif "bulk" in text_lower or "wholesale" in text_lower:
            quantity = "Bulk"
            
        # 2. Payment Method Detection
        payment = "Negotiable"
        payment_map = {
            "m-pesa": ["mpesa", "m-pesa", "lipa na mpesa", "send money"],
            "cash": ["cash", "on delivery", "cod"],
            "installments": ["installments", "pole pole", "monthly", "credit"],
            "bank": ["bank transfer", "eft", "rtgs"]
        }
        for method, keywords in payment_map.items():
            if any(kw in text_lower for kw in keywords):
                payment = method.capitalize()
                break
                
        return quantity, payment

    def analyze_local_advantage(self, text):
        """Extract neighborhood and local preferences."""
        text_lower = text.lower()
        
        # 1. Neighborhood Detection (Kenya Specific)
        neighborhoods = [
            "Westlands", "Kilimani", "Kileleshwa", "Karen", "Runda", "South B", "South C", "Langata", "Embassy",
            "Pangani", "Parklands", "Donholm", "Buruburu", "Syokimau", "Kitengela", "Ruiru", "Juja", "Kiambu",
            "Nyali", "Bamburi", "Mtwapa", "Milimani", "Kondele", "Tom Mboya"
        ]
        neighborhood = None
        for n in neighborhoods:
            if re.search(rf"\b{n}\b", text, re.IGNORECASE):
                neighborhood = n
                break
        
        # 2. Pickup Preference
        pickup = 0
        if any(kw in text_lower for kw in ["pickup", "pick up", "collection", "collect"]):
            pickup = 1
            
        # 3. Delivery Constraints
        constraints = None
        delivery_keywords = ["deliver before", "same day", "within", "must be delivered", "drop off at", "delivered to"]
        for kw in delivery_keywords:
            if kw in text_lower:
                match = re.search(rf"{kw}\s+([^,.]+)", text_lower)
                if match:
                    constraints = f"{kw} {match.group(1).strip()}"
                    break
                    
        return neighborhood, pickup, constraints

    def assess_deal_readiness(self, text):
        """Assess decision authority, research, and deadlines."""
        text_lower = text.lower()
        
        # 1. Decision Authority
        authority = 0
        if any(kw in text_lower for kw in ["i am buying", "my company", "i need", "i want", "direct buyer", "for my house", "for my car"]):
            authority = 1
        
        # 2. Budget Approval / Readiness
        budget_ready = 0
        if any(kw in text_lower for kw in ["budget is ready", "cash ready", "finance approved", "already have the money", "willing to pay"]):
            budget_ready = 1
            
        # 3. Prior Research
        research = 0
        if any(kw in text_lower for kw in ["compared", "best price", "reviewed", "checked", "specs say", "seen others"]):
            research = 1
            
        # 4. Comparison
        comparison = 0
        if any(kw in text_lower for kw in ["vs", "better than", "instead of", "alternative to", "compared with"]):
            comparison = 1
            
        # 5. Upcoming Deadline
        deadline = None
        # Handle "by Friday", "before end of month", "deadline 25th", etc.
        deadline_match = re.search(r'(by|before|deadline|due)\s+([A-Za-z]+\s+\d{1,2}|\d{1,2}/\d{1,2}|\d{1,2}\s+[A-Za-z]+|today|tomorrow|friday|monday|next week)', text_lower)
        if deadline_match:
            keyword = deadline_match.group(2).strip()
            if keyword == "today":
                deadline = datetime.now()
            elif keyword == "tomorrow":
                deadline = datetime.now() + timedelta(days=1)
            elif "week" in keyword:
                deadline = datetime.now() + timedelta(days=7)
            else:
                # Default to 3 days if specific date parsing is complex
                deadline = datetime.now() + timedelta(days=3)
            
        return authority, research, comparison, deadline, budget_ready

    def extract_conversion_signals(self, text):
        """Detect language indicating imminent purchase and specific buyer signals."""
        text_lower = text.lower()
        signals = []
        
        # Imminent Purchase Language
        imminent_keywords = ["buying today", "need now", "buying as soon as", "ready to pick up", "where are you located", "asap", "urgently"]
        if any(kw in text_lower for kw in imminent_keywords):
            signals.append("imminent_purchase")
            
        # Financing/Budget
        if any(kw in text_lower for kw in ["financing", "loan", "installment", "mpesa ready", "cash in hand", "budget is approved", "budget ready"]):
            signals.append("budget_approved")
            
        # Comparison Shopping
        if any(kw in text_lower for kw in ["vs", "other sellers", "best offer", "cheaper", "price match"]):
            signals.append("comparison_shopping")
            
        return signals

    def generate_talking_points(self, lead_data):
        """Generate specific talking points based on lead intent and seller match."""
        points = []
        product = lead_data.get("product_category", "item")
        
        # Base on urgency
        if lead_data.get("readiness_level") == "HOT":
            points.append(f"Mention immediate availability for the {product}.")
            
        # Base on location
        if lead_data.get("neighborhood"):
            points.append(f"Highlight same-day delivery to {lead_data['neighborhood']}.")
            
        # Base on budget
        if lead_data.get("budget_info") != "Negotiable":
            points.append(f"Acknowledge the {lead_data['budget_info']} budget and offer our competitive pricing.")
            
        # Base on specs
        if lead_data.get("product_specs"):
            specs_str = ", ".join([f"{k}: {v}" for k, v in lead_data['product_specs'].items()])
            points.append(f"Confirm we have the exact specs: {specs_str}.")
            
        if not points:
            points.append(f"Inquire about specific requirements for the {product}.")
            
        return points

    def extract_time(self, text):
        """Extract time relative to now."""
        now = datetime.now(timezone.utc)
        
        # Simple keywords
        if "yesterday" in text.lower():
            return now - timedelta(days=1)
        if "today" in text.lower():
            return now
        
        # Simple date regex
        match = re.search(r'\d{1,2}/\d{1,2}/\d{4}', text)
        if match:
            try:
                return datetime.strptime(match.group(), "%d/%m/%Y").replace(tzinfo=timezone.utc)
            except:
                pass
        
        return now

import logging
import re
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timezone, timedelta
import phonenumbers
from email_validator import validate_email as check_email, EmailNotValidError
from app.config.runtime import PROD_STRICT

logger = logging.getLogger(__name__)

class ValidationService:
    """
    Validation Layer:
    Ensures that requests to the Scraper Layer are valid, safe, and policy-compliant.
    """
    
    BANNED_KEYWORDS = [
        "porn", "xxx", "casino", "gambling", "drugs", "weed", 
        "escort", "bitcoin", "crypto", "forex", "loan", "hack"
    ]
    
    ALLOWED_LOCATIONS = [
        "kenya", "nairobi", "mombasa", "kisumu", "nakuru", "eldoret", 
        "thika", "kitengela", "ruiru", "karen", "kilimani", "westlands",
        "kiambu", "machakos", "kajiado"
    ]

    def validate_search_request(self, query: str, location: str) -> Tuple[bool, Optional[str]]:
        """
        Validates a search request before it hits the Scraper Layer.
        Returns: (is_valid, error_message)
        """
        if not query or len(query.strip()) < 2:
            return False, "Query too short"
            
        if len(query) > 100:
            return False, "Query too long"
            
        # Check banned keywords
        query_lower = query.lower()
        for banned in self.BANNED_KEYWORDS:
            if f" {banned} " in f" {query_lower} ": # simplistic whole word check
                return False, f"Query contains banned keyword: {banned}"
                
        # KENYA LOCKING: Force location to be Kenya-related
        # Even if user sends "London", we reject it.
        valid_locations = ["kenya", "nairobi", "mombasa", "kisumu", "nakuru", "eldoret", "thika", "kiambu", "machakos", "kajiado"]
        if not any(loc in location.lower() for loc in valid_locations):
             # Auto-correct to Kenya if vague? No, reject to be strict as requested.
             # "Kenya Locking (Proper Way)... Enforce at API query filter"
             return False, f"Location '{location}' not supported. Kenya only."

        return True, None

    def validate_lead_data(self, lead_data: dict) -> Tuple[bool, Optional[str]]:
        """
        Validates scraped lead data before ingestion.
        """
        if not lead_data.get("title") and not lead_data.get("text"):
             return False, "Missing content"
             
        if not lead_data.get("url"):
             return False, "Missing URL"

        # Check timestamp freshness
        # RELAXED: Allow up to 30 days for open search
        ts = lead_data.get("timestamp")
        if ts:
            try:
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                
                age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
                if age_hours > 24 * 30: # 30 days
                    return False, f"Old result ({age_hours:.1f}h > 30d)"
            except Exception:
                pass # Ignore parsing errors, assume fresh enough or missing
             
        # Check for foreign content
        text = lead_data.get("title", "") + " " + lead_data.get("text", "") + " " + lead_data.get("snippet", "")
        if self.is_foreign_content(text, lead_data.get("url", "")):
            return False, "Foreign content detected"

        return True, None

    def is_foreign_content(self, text: str, url: str) -> bool:
        """
        Detect if the content is explicitly foreign (US/UK/etc) to filter out ads/irrelevant results.
        Target: Kenya Only.
        """
        text_lower = text.lower()
        url_lower = url.lower()
        
        # 1. POSITIVE CONFIRMATION (Whitelist)
        # If it explicitly mentions Kenya, Nairobi, etc, it's safe (mostly).
        # We check this first to allow "Import from USA to Kenya" type queries.
        kenya_keywords = ["kenya", "nairobi", "mombasa", "kisumu", "nakuru", "eldoret", "thika", ".co.ke", "shilling", "ksh", "kes"]
        if any(k in text_lower for k in kenya_keywords) or any(k in url_lower for k in kenya_keywords):
            return False # Not foreign (i.e., it is Kenyan)
            
        # 2. NEGATIVE CONFIRMATION (Blacklist)
        # If it doesn't mention Kenya, does it mention other places?
        foreign_keywords = [
            "california", "united states", "usa", "new york", "texas", "london", "uk", 
            "canada", "australia", "dubai", "india", "nigeria", "south africa", "lagos", "johannesburg",
            "dollar", "usd", "eur", "gbp", "shipping from china"
        ]
        
        if any(k in text_lower for k in foreign_keywords):
            return True # Is foreign

        # 3. DOMAIN CHECK
        # If TLD is explicitly foreign (.za, .ng, .uk, .us)
        if re.search(r'\.(za|ng|uk|us|in|au|ca)(/|$)', url_lower):
            return True

        return False

    def enrich_lead_data(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enriches lead data with validation and normalization:
        - Format Phone Numbers (Kenya Only)
        - Validate Emails
        """
        # 1. Phone Enrichment
        phone = lead_data.get("phone")
        if phone:
            valid, formatted, carrier = self.validate_kenyan_phone(phone)
            if valid:
                lead_data["phone"] = formatted
                lead_data["contact_metadata"] = {"carrier": carrier, "valid": True}
            else:
                # Keep original but mark invalid? Or clear it?
                # User wants "lead enrichment (phone/email validation APIs)"
                # If invalid, maybe clear it to avoid spamming wrong numbers.
                # But sometimes regex is too strict. Let's keep it but flag it.
                lead_data["contact_metadata"] = {"valid": False, "error": "Invalid Format"}
        
        # 2. Email Enrichment
        email = lead_data.get("email") or lead_data.get("contact_email")
        if email:
            valid, normalized = self.validate_email_address(email)
            if valid:
                lead_data["contact_email"] = normalized
            else:
                lead_data["contact_email"] = None # Clear invalid emails

        return lead_data

    def validate_kenyan_phone(self, phone: str) -> Tuple[bool, Optional[str], Optional[str]]:
        try:
            # Default region Kenya (KE)
            parsed = phonenumbers.parse(phone, "KE")
            if not phonenumbers.is_valid_number(parsed):
                return False, None, None
            
            # Ensure it's Kenyan (+254)
            if parsed.country_code != 254:
                return False, None, "Foreign Number"
                
            formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            # Carrier lookup requires offline database or API. Phonenumbers has offline DB.
            from phonenumbers import carrier
            carrier_name = carrier.name_for_number(parsed, "en")
            
            return True, formatted, carrier_name
        except Exception:
            return False, None, None

    def validate_email_address(self, email: str) -> Tuple[bool, Optional[str]]:
        try:
            # Check deliverability=False to avoid DNS checks if slow, but user wants API-level validation.
            # Default checks DNS.
            v = check_email(email, check_deliverability=False) 
            return True, v.normalized
        except EmailNotValidError as e:
            return False, None

VALIDATION_SERVICE = ValidationService()

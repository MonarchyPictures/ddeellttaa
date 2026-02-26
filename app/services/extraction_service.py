
import re
import logging

logger = logging.getLogger(__name__)

class ExtractionService:
    """
    Extracts structured data (Phone, Budget, Location) from unstructured text.
    """

    @staticmethod
    def extract_phone(text: str) -> str:
        if not text:
            return ""
        
        # Kenyan Phone Patterns
        patterns = [
            r'(\+254[\s-]*\d{3}[\s-]*\d{3}[\s-]*\d{3})',  # +254 7XX XXX XXX (flexible separators)
            r'(254[\s-]*\d{9})',                          # 2547XXXXXXXX
            r'(07\d{2}[\s-]*\d{3}[\s-]*\d{3})',           # 07XX XXX XXX
            r'(01\d{2}[\s-]*\d{3}[\s-]*\d{3})',           # 01XX XXX XXX
            r'(\+254\d{9})'                               # +2547XXXXXXXX
        ]
        
        for p in patterns:
            match = re.search(p, text)
            if match:
                # Normalize
                phone = match.group(1).replace(" ", "").replace("-", "")
                if phone.startswith("0"):
                    phone = "254" + phone[1:]
                if phone.startswith("+"):
                    phone = phone[1:]
                return phone
        return ""

    @staticmethod
    def extract_budget(text: str) -> str:
        if not text:
            return ""
        
        text_lower = text.lower()
        
        # Budget patterns
        patterns = [
            # Range: 50k-60k, 50000-60000, 1.5m-2m
            r'((?:budget|price)?\s*[\d.,]+(?:k|m)?\s*-\s*[\d.,]+(?:k|m|ksh|kes|sh|shillings)?)',
            # Explicit budget mentions
            r'(budget\s*(?:is|:)?\s*[\d.,]+(?:k|m|ksh|kes|sh|shillings)?)',
            r'([\d.,]+\s*(?:k|m|ksh|kes|sh|shillings)\s*budget)',
            # Contextual
            r'(looking for\s*.*?\s*around\s*[\d.,]+(?:k|m)?)',
            r'(max\s*[\d.,]+(?:k|m|ksh|kes)?)',
            r'([\d.,]+(?:k|m)\s*cash)'
        ]
        
        for p in patterns:
            match = re.search(p, text_lower)
            if match:
                return match.group(1).strip()
        
        # Fallback: finding bare prices like "50k", "50,000"
        price_match = re.search(r'\b(ksh\.?|kes\.?|sh\.?)\s?([\d.,]+(?:k|m)?)\b', text_lower)
        if price_match:
            return f"{price_match.group(1)} {price_match.group(2)}"

        return ""

    @staticmethod
    def extract_location(text: str, default: str = "Kenya") -> str:
        if not text:
            return default
            
        # Common Kenyan Locations (expand as needed)
        locations = [
            "nairobi", "mombasa", "kisumu", "nakuru", "eldoret", "thika",
            "kitengela", "kiambu", "karen", "kilimani", "kileleshwa",
            "westlands", "cbd", "ruiru", "juja", "rongai", "syokimau",
            "machakos", "nyeri", "meru", "kisii", "kakamega", "malindi"
        ]
        
        text_lower = text.lower()
        for loc in locations:
            if loc in text_lower:
                return loc.title()
                
        return default

    @staticmethod
    def enrich_lead(lead: dict) -> dict:
        """Enrich a lead dictionary with extracted fields."""
        full_text = f"{lead.get('title', '')} {lead.get('snippet', '')} {lead.get('text', '')}"
        
        # Phone
        if not lead.get('phone'):
            lead['phone'] = ExtractionService.extract_phone(full_text)
            if lead['phone']:
                lead['contact_phone'] = lead['phone']
                lead['whatsapp_url'] = f"https://wa.me/{lead['phone']}"
        
        # Budget/Price
        if not lead.get('price') or lead.get('price') == "Contact for Price":
            extracted_budget = ExtractionService.extract_budget(full_text)
            if extracted_budget:
                lead['price'] = extracted_budget
                lead['budget'] = extracted_budget # Explicit budget field
                
        # Location
        if not lead.get('location') or lead.get('location') == "Kenya":
             lead['location'] = ExtractionService.extract_location(full_text, lead.get('location', 'Kenya'))
             
        return lead

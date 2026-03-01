# app/services/deduplication_engine.py
# ============================================================
# LEAD DEDUPLICATION ENGINE — Beyond URL Matching
# ============================================================
# Deduplicates leads using multiple signals:
# - URL match (exact)
# - Text similarity (fuzzy)
# - Phone number match
# - Product match
# ============================================================

import re
import hashlib
from typing import List, Dict, Any, Set, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass
class LeadSignature:
    """Unique signature for deduplication."""
    url_hash: str
    phone_hash: str
    text_hash: str
    product_hash: str
    combined_hash: str


class DeduplicationEngine:
    """
    Multi-signal lead deduplication engine.
    
    Goes beyond simple URL matching to catch:
    - Same lead, different URLs
    - Same buyer, reworded text
    - Same phone, different platforms
    """
    
    # Similarity thresholds
    TEXT_SIMILARITY_THRESHOLD = 0.75  # 75% text match
    
    def __init__(self):
        self.seen_signatures: Set[str] = set()
        self.phone_index: Dict[str, List[Dict]] = {}
        self.text_fingerprints: List[Tuple[str, Dict]] = []
    
    def extract_phone(self, text: str) -> str:
        """Extract normalized phone number."""
        # Kenyan phone patterns
        patterns = [
            r'(\+?254\d{9})',      # +254712345678
            r'(07\d{8})',           # 0712345678
            r'(01\d{8})',           # 0112345678
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                phone = match.group(1)
                # Normalize: remove +, ensure 12 digits
                phone = phone.replace('+', '')
                if phone.startswith('0'):
                    phone = '254' + phone[1:]
                return phone
        return ""
    
    def extract_product(self, text: str) -> str:
        """Extract product keywords."""
        # Common product keywords in Kenya
        products = [
            "pipes", "mabomba", "tiles", "cement", "house", "nyumba",
            "car", "gari", "phone", "simu", "laptop", "diapers",
            "rice", "mchele", "plumber", "fundi", "electrician"
        ]
        
        text_lower = text.lower()
        found_products = []
        
        for product in products:
            if product in text_lower:
                found_products.append(product)
        
        return "|".join(sorted(found_products))
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        # Lowercase
        text = text.lower()
        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text)
        # Remove punctuation
        text = re.sub(r'[^\w\s]', '', text)
        # Remove common filler words
        filler_words = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for']
        words = [w for w in text.split() if w not in filler_words]
        return ' '.join(words)
    
    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity (0.0 to 1.0)."""
        norm1 = self.normalize_text(text1)
        norm2 = self.normalize_text(text2)
        
        if not norm1 or not norm2:
            return 0.0
        
        # Use SequenceMatcher for fuzzy matching
        similarity = SequenceMatcher(None, norm1, norm2).ratio()
        return similarity
    
    def generate_signature(self, lead: Dict[str, Any]) -> LeadSignature:
        """Generate deduplication signature for lead."""
        # URL hash
        url = lead.get("url", "")
        url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
        
        # Phone hash
        text = f"{lead.get('title', '')} {lead.get('snippet', '')}"
        phone = self.extract_phone(text)
        phone_hash = hashlib.md5(phone.encode()).hexdigest()[:16] if phone else ""
        
        # Text hash (first 100 chars normalized)
        normalized = self.normalize_text(text)[:100]
        text_hash = hashlib.md5(normalized.encode()).hexdigest()[:16]
        
        # Product hash
        product = self.extract_product(text)
        product_hash = hashlib.md5(product.encode()).hexdigest()[:16]
        
        # Combined hash
        combined = f"{url_hash}:{phone_hash}:{product_hash}"
        combined_hash = hashlib.md5(combined.encode()).hexdigest()[:16]
        
        return LeadSignature(
            url_hash=url_hash,
            phone_hash=phone_hash,
            text_hash=text_hash,
            product_hash=product_hash,
            combined_hash=combined_hash
        )
    
    def is_duplicate(self, lead: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check if lead is duplicate.
        
        Returns: (is_duplicate, reason)
        """
        signature = self.generate_signature(lead)
        text = f"{lead.get('title', '')} {lead.get('snippet', '')}"
        
        # Check 1: Exact URL match
        if signature.url_hash in self.seen_signatures:
            return True, "exact_url_match"
        
        # Check 2: Phone number match (strong signal)
        if signature.phone_hash and signature.phone_hash in self.phone_index:
            # Verify it's really the same person
            existing = self.phone_index[signature.phone_hash][0]
            similarity = self.calculate_text_similarity(text, existing.get('text', ''))
            if similarity > 0.5:  # 50% text similarity confirms same buyer
                return True, f"phone_match (similarity: {similarity:.2f})"
        
        # Check 3: Text similarity (fuzzy match)
        for fingerprint_text, existing_lead in self.text_fingerprints:
            similarity = self.calculate_text_similarity(text, fingerprint_text)
            if similarity >= self.TEXT_SIMILARITY_THRESHOLD:
                return True, f"text_similarity ({similarity:.2f})"
        
        # Check 4: Combined signature
        if signature.combined_hash in self.seen_signatures:
            return True, "combined_signature_match"
        
        return False, ""
    
    def add_lead(self, lead: Dict[str, Any]) -> None:
        """Add lead to deduplication index."""
        signature = self.generate_signature(lead)
        text = f"{lead.get('title', '')} {lead.get('snippet', '')}"
        
        # Add to indexes
        self.seen_signatures.add(signature.url_hash)
        self.seen_signatures.add(signature.combined_hash)
        
        if signature.phone_hash:
            if signature.phone_hash not in self.phone_index:
                self.phone_index[signature.phone_hash] = []
            self.phone_index[signature.phone_hash].append({
                **lead,
                "text": text
            })
        
        self.text_fingerprints.append((text, lead))
    
    def deduplicate(self, leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Main deduplication method.
        
        Returns unique leads with deduplication metadata.
        """
        unique_leads = []
        
        for lead in leads:
            is_dup, reason = self.is_duplicate(lead)
            
            if is_dup:
                # Add metadata about duplication
                lead["deduplicated"] = True
                lead["duplicate_reason"] = reason
            else:
                lead["deduplicated"] = False
                lead["duplicate_reason"] = None
                unique_leads.append(lead)
                self.add_lead(lead)
        
        return unique_leads
    
    def get_stats(self) -> Dict[str, Any]:
        """Get deduplication statistics."""
        return {
            "unique_urls": len([s for s in self.seen_signatures if len(s) == 16]),
            "unique_phones": len(self.phone_index),
            "text_fingerprints": len(self.text_fingerprints),
        }


# Global engine instance
dedup_engine = DeduplicationEngine()


def deduplicate_leads(leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate leads using multi-signal matching.
    
    Usage:
        unique_leads = deduplicate_leads(raw_leads)
        print(f"Removed {len(raw_leads) - len(unique_leads)} duplicates")
    """
    return dedup_engine.deduplicate(leads)

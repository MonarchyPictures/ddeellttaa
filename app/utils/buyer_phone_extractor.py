"""
Buyer Phone Number Extractor

RULE: Only extract phone numbers from posts with verified buyer intent.

IF text contains buyer intent
AND phone number is inside same message
AND phone passes Kenya validation
THEN accept
ELSE reject

Buyer Intent Keywords (case insensitive):
- "looking for" / "lookingfor"
- "niko natafuta" (Swahili)
- "need" / "i need"
- "anyone selling"
- "where can i buy"
- "who has"

Reject/Seller Keywords:
- "selling"
- "available"
- "price"
- "call me"
- "DM for price"
- "for sale"

Phone Validation (Kenya):
- Must match: ^(\\+254|0)[17]\\d{8}$
- Valid: +254712345678, 0712345678, 0112345678
- Invalid: wrong length, wrong prefix, wrong country

Example:
    ✅ "Looking for Toyota Vitz 0723898087" → Extract 254723898087
    ✅ "Niko natafuta gari call 0723123456" → Extract 254723123456
    ❌ "Selling Toyota Vitz 0723898087" → Reject (seller)
    ❌ "0723898087 call me" → Reject (no buyer intent)
    ❌ "Looking for car 12345" → Reject (invalid phone)
"""
import re
from typing import Optional, Dict, Any, Tuple, List, Set

try:
    from .phone_verification import KenyaPhoneVerifier, PhoneStatus
except ImportError:
    from phone_verification import KenyaPhoneVerifier, PhoneStatus


class BuyerPhoneExtractor:
    """
    Extracts phone numbers ONLY from buyer posts with verified intent.
    """
    
    # Buyer intent keywords (case insensitive)
    BUYER_KEYWORDS = [
        r'looking\s*for',           # "looking for", "lookingfor"
        r'niko\s+natafuta',         # Swahili: "I am looking for"
        r'\bneed\b',                # "need", "i need"
        r'anyone\s+selling',        # "anyone selling"
        r'where\s+can\s+i\s+buy',   # "where can i buy"
        r'who\s+has',               # "who has"
        r'tafuta',                  # Swahili: "look for"
        r'natafuta',                # Swahili: "I am looking for"
        r'want\s+to\s+buy',         # "want to buy"
        r'in\s+need\s+of',          # "in need of"
        r'searching\s+for',         # "searching for"
        r'shopping\s+for',          # "shopping for"
        r'interested\s+in\s+buying', # "interested in buying"
    ]
    
    # Seller/reject keywords (case insensitive)
    SELLER_KEYWORDS = [
        r'\bselling\b',
        r'\bavailable\b',
        r'\bprice\b',
        r'call\s+me',
        r'DM\s+for\s+price',
        r'for\s+sale',
        r'\bsell\b',
        r'inbox\s+for\s+price',
        r'hmu',                     # "hit me up" (seller slang)
        r'@\w+.*price',             # Tag with price
        r'\d+k',                    # Price like "450k", "1.2m"
        r'negotiable',
        r'ono',                     # "or nearest offer" (seller)
    ]
    
    # Phone patterns for Kenya and international
    PHONE_PATTERNS = [
        # Kenya formats
        r'(?:\+?254|0)\s*[17]\s*\d{2}\s*\d{3}\s*\d{3,4}',  # +254 712 345 678 or 0712345678
        r'(?:\+?254|0)\s*[17]\s*\d{8}',                      # Compact format
        # Generic international
        r'\+\d{1,3}\s*\d{3}\s*\d{3}\s*\d{3,4}',
        r'\+\d{10,15}',
    ]
    
    @classmethod
    def has_buyer_intent(cls, text: str) -> bool:
        """
        Check if text contains buyer intent keywords.
        
        Args:
            text: Post/message text
            
        Returns:
            True if buyer intent detected
        """
        if not text:
            return False
        
        text_lower = text.lower()
        
        for pattern in cls.BUYER_KEYWORDS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        
        return False
    
    @classmethod
    def has_seller_intent(cls, text: str) -> bool:
        """
        Check if text contains seller/reject keywords.
        
        Args:
            text: Post/message text
            
        Returns:
            True if seller intent detected
        """
        if not text:
            return False
        
        text_lower = text.lower()
        
        for pattern in cls.SELLER_KEYWORDS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        
        return False
    
    @classmethod
    def extract_phone(cls, text: str) -> Optional[str]:
        """
        Extract and normalize phone number from text.
        
        Args:
            text: Post/message text
            
        Returns:
            Normalized phone number (254XXXXXXXXX) or None
        """
        raw = cls.extract_raw_phone(text)
        if raw:
            return KenyaPhoneVerifier.normalize(raw)
        return None
    
    @classmethod
    def extract_buyer_phone(cls, text: str, existing_phones: Optional[Set[str]] = None) -> Tuple[Optional[str], str]:
        """
        Extract phone number ONLY from buyer posts with validation.
        
        This is the main method that enforces the rule:
        IF buyer intent AND valid phone (Kenya format) → return phone
        ELSE → return None with reason
        
        Args:
            text: Post/message text
            existing_phones: Set of existing phones for duplicate check
            
        Returns:
            Tuple of (phone_number, reason)
            - phone_number: Extracted phone or None
            - reason: Explanation of result
        """
        if not text:
            return None, "Empty text"
        
        # PRIORITY: Check for buyer intent FIRST
        has_buyer = cls.has_buyer_intent(text)
        
        if not has_buyer:
            # No buyer intent - check if it's a seller post
            if cls.has_seller_intent(text):
                return None, "Rejected: Seller post detected"
            return None, "Rejected: No buyer intent keywords found"
        
        # We have buyer intent - now extract phone
        raw_phone = cls.extract_raw_phone(text)
        
        if not raw_phone:
            return None, "Rejected: No phone number found"
        
        # Validate phone number (Kenya format) - validate raw format first
        validation_result = KenyaPhoneVerifier.validate(raw_phone, existing_phones)
        
        if not validation_result.is_valid:
            return None, f"Rejected: Invalid phone - {validation_result.error_message}"
        
        # Return the normalized (international) format
        return validation_result.normalized, f"Accepted: Buyer + valid phone ({validation_result.format_display})"

    @classmethod
    def extract_raw_phone(cls, text: str) -> Optional[str]:
        """
        Extract raw phone number from text (before normalization).
        
        Args:
            text: Post/message text
            
        Returns:
            Raw phone number (with + or 0 prefix) or None
        """
        if not text:
            return None
        
        for pattern in cls.PHONE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                phone = match.group(0)
                # Just clean whitespace, keep + and 0 prefix
                phone = re.sub(r'[\s\-\(\)\.]', '', phone)
                return phone
        
        return None
    
    @classmethod
    def validate_and_extract(cls, text: str, source: str = "unknown", existing_phones: Optional[Set[str]] = None) -> Dict[str, Any]:
        """
        Full validation and extraction with metadata.
        
        Args:
            text: Post/message text
            source: Source platform
            existing_phones: Set of existing phones for duplicate check
            
        Returns:
            Dict with extraction result and metadata
        """
        result = {
            "text": text,
            "source": source,
            "phone": None,
            "phone_formatted": None,
            "has_buyer_intent": False,
            "has_seller_intent": False,
            "is_valid_buyer": False,
            "reason": "",
        }
        
        if not text:
            result["reason"] = "Empty text"
            return result
        
        # Check intents
        result["has_buyer_intent"] = cls.has_buyer_intent(text)
        result["has_seller_intent"] = cls.has_seller_intent(text)
        
        # Extract phone with validation
        phone, reason = cls.extract_buyer_phone(text, existing_phones)
        result["phone"] = phone
        result["reason"] = reason
        result["is_valid_buyer"] = phone is not None
        
        # Add formatted phone if valid
        if phone:
            result["phone_formatted"] = KenyaPhoneVerifier.format_display(phone)
        
        return result


# Convenience functions for quick use
def extract_buyer_phone(text: str) -> Optional[str]:
    """
    Quick extraction - returns phone only from buyer posts.
    
    Args:
        text: Post/message text
        
    Returns:
        Phone number or None
    """
    phone, _ = BuyerPhoneExtractor.extract_buyer_phone(text)
    return phone


def is_valid_buyer_post(text: str) -> bool:
    """
    Quick check if text is a valid buyer post with phone.
    
    Args:
        text: Post/message text
        
    Returns:
        True if buyer post with phone
    """
    phone, _ = BuyerPhoneExtractor.extract_buyer_phone(text)
    return phone is not None


def filter_buyer_posts(posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter a list of posts to only valid buyer posts with phones.
    
    Args:
        posts: List of post dicts with 'text' field
        
    Returns:
        List of valid buyer posts with extracted phone
    """
    valid_posts = []
    
    for post in posts:
        text = post.get('text', '')
        result = BuyerPhoneExtractor.validate_and_extract(text, post.get('source', 'unknown'))
        
        if result['is_valid_buyer']:
            post['phone'] = result['phone']
            post['_buyer_validation'] = result
            valid_posts.append(post)
    
    return valid_posts


# Example usage
if __name__ == "__main__":
    # Test cases
    test_cases = [
        # Valid buyer posts (phone normalized to international format)
        ("Looking for Toyota Vitz 0723898087", True, "254723898087"),
        ("Niko natafuta gari call 0723123456", True, "254723123456"),
        ("Need iPhone 14 pro +254712345678", True, "254712345678"),
        ("Anyone selling a house? 0712345678", True, "254712345678"),  # Buyer asking who is selling
        ("Where can I buy a laptop 0711987654", True, "254711987654"),
        
        # Invalid - seller posts
        ("Selling Toyota Vitz 0723898087", False, None),
        ("iPhone available call 0723123456", False, None),
        ("DM for price 0712345678", False, None),
        
        # Invalid - no buyer intent
        ("0723898087 call me", False, None),
        ("Price is 450k DM me", False, None),
        ("Contact me 0712345678", False, None),
        
        # Invalid - bad phone numbers
        ("Looking for car 07234567", False, None),        # Too short
        ("Looking for car 07234567890", False, None),     # Too long
        ("Looking for car 1234567890", False, None),      # Wrong prefix
        ("Looking for car +255712345678", False, None),   # Wrong country (Tanzania)
    ]
    
    print("Buyer Phone Extractor - Test Results")
    print("=" * 60)
    
    for text, expected_valid, expected_phone in test_cases:
        result = BuyerPhoneExtractor.validate_and_extract(text)
        is_valid = result['is_valid_buyer']
        phone = result['phone']
        
        status = "[PASS]" if (is_valid == expected_valid and phone == expected_phone) else "[FAIL]"
        
        print(f"\n{status}")
        print(f"Text: {text}")
        print(f"Expected: {'Valid' if expected_valid else 'Invalid'}, Phone: {expected_phone}")
        print(f"Got: {'Valid' if is_valid else 'Invalid'}, Phone: {phone}")
        print(f"Reason: {result['reason']}")

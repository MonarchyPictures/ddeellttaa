"""
Phone Number Verification for Kenya

Validates phone numbers before showing/storing them.

Kenya Phone Pattern:
    ^(\\+254|0)[17]\\d{8}$
    
Examples:
    ✅ +254712345678
    ✅ +254112345678  
    ✅ 0712345678
    ✅ 0112345678
    
    ❌ 254712345678     (missing +)
    ❌ 0723123456       (wrong digit count)
    ❌ +255712345678    (wrong country - Tanzania)
    ❌ 07123456789      (too many digits)

Checks:
1. Format validation (regex)
2. Length check (13 chars with +, 10 chars with 0)
3. Country prefix (+254 or 0)
4. Mobile prefix (7 or 1)
5. Duplicate detection
6. Normalization (convert to standard format)
"""
import re
from typing import Optional, Dict, Any, Tuple, List, Set
from dataclasses import dataclass
from enum import Enum


class PhoneStatus(str, Enum):
    """Phone validation status"""
    VALID = "valid"
    INVALID_FORMAT = "invalid_format"
    INVALID_LENGTH = "invalid_length"
    INVALID_PREFIX = "invalid_prefix"
    INVALID_COUNTRY = "invalid_country"
    DUPLICATE = "duplicate"
    EMPTY = "empty"


@dataclass
class PhoneValidationResult:
    """Result of phone number validation"""
    original: str
    normalized: Optional[str]
    is_valid: bool
    status: PhoneStatus
    error_message: str
    format_display: Optional[str]  # Human readable format


class KenyaPhoneVerifier:
    """
    Verifies Kenyan phone numbers.
    
    Valid formats:
    - +254XXXXXXXXX (13 chars, international)
    - 0XXXXXXXXX (10 chars, local)
    
    Valid prefixes:
    - +2547 or 07 (Safaricom, Airtel, Telkom)
    - +2541 or 01 (New generation numbers)
    """
    
    # Kenya phone regex patterns
    KENYA_PHONE_REGEX = re.compile(r'^(\+254|0)[17]\d{8}$')
    
    # International format: +254 followed by 9 digits
    INTERNATIONAL_REGEX = re.compile(r'^\+254[17]\d{8}$')
    
    # Local format: 0 followed by 9 digits
    LOCAL_REGEX = re.compile(r'^0[17]\d{8}$')
    
    # Valid mobile prefixes (first digit after country code)
    VALID_PREFIXES = {'7', '1'}
    
    # Country code
    COUNTRY_CODE = '254'
    
    @classmethod
    def normalize(cls, phone: str) -> Optional[str]:
        """
        Normalize phone number to international format.
        
        Args:
            phone: Raw phone number
            
        Returns:
            Normalized phone (+254XXXXXXXXX) or None
        """
        if not phone:
            return None
        
        # Remove all non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', phone.strip())
        
        # Remove leading + if present for processing
        has_plus = cleaned.startswith('+')
        digits_only = re.sub(r'\D', '', cleaned)
        
        # Check length
        if len(digits_only) == 9 and digits_only.startswith(('7', '1')):
            # Missing country code, add it
            return f"{cls.COUNTRY_CODE}{digits_only}"
        
        elif len(digits_only) == 10 and digits_only.startswith('0'):
            # Local format, convert to international
            return f"{cls.COUNTRY_CODE}{digits_only[1:]}"
        
        elif len(digits_only) == 12 and digits_only.startswith(cls.COUNTRY_CODE):
            # Already international but missing +
            return digits_only
        
        elif len(digits_only) == 13 and digits_only.startswith(f"{cls.COUNTRY_CODE}"):
            # With country code but we removed the +
            return digits_only
        
        return None
    
    @classmethod
    def format_display(cls, phone: str) -> str:
        """
        Format phone for display (+254 712 345 678).
        
        Args:
            phone: Phone number (any format)
            
        Returns:
            Formatted phone number
        """
        normalized = cls.normalize(phone)
        if not normalized:
            return phone
        
        # Format: +254 712 345 678
        return f"+{normalized[:3]} {normalized[3:6]} {normalized[6:9]} {normalized[9:]}"
    
    @classmethod
    def validate(cls, phone: str, existing_phones: Optional[Set[str]] = None) -> PhoneValidationResult:
        """
        Validate a Kenyan phone number.
        
        Args:
            phone: Phone number to validate
            existing_phones: Set of existing normalized phones for duplicate check
            
        Returns:
            PhoneValidationResult with validation details
        """
        # Check empty
        if not phone or not str(phone).strip():
            return PhoneValidationResult(
                original=phone or "",
                normalized=None,
                is_valid=False,
                status=PhoneStatus.EMPTY,
                error_message="Phone number is empty",
                format_display=None
            )
        
        phone_str = str(phone).strip()
        
        # Remove common separators for validation
        cleaned = re.sub(r'[\s\-\(\)\.]', '', phone_str)
        
        # Check basic format
        if not cls.KENYA_PHONE_REGEX.match(cleaned):
            # Determine specific error
            digits_only = re.sub(r'\D', '', cleaned)
            
            if len(digits_only) not in [9, 10, 12, 13]:
                return PhoneValidationResult(
                    original=phone_str,
                    normalized=None,
                    is_valid=False,
                    status=PhoneStatus.INVALID_LENGTH,
                    error_message=f"Invalid length: {len(digits_only)} digits (expected 10 or 12/13)",
                    format_display=None
                )
            
            # Check country code
            if not (cleaned.startswith('+254') or cleaned.startswith('0')):
                if digits_only.startswith('254'):
                    return PhoneValidationResult(
                        original=phone_str,
                        normalized=None,
                        is_valid=False,
                        status=PhoneStatus.INVALID_PREFIX,
                        error_message="Missing + before 254 (should be +254...)",
                        format_display=None
                    )
                else:
                    return PhoneValidationResult(
                        original=phone_str,
                        normalized=None,
                        is_valid=False,
                        status=PhoneStatus.INVALID_COUNTRY,
                        error_message="Invalid country code (Kenya uses +254 or 0)",
                        format_display=None
                    )
            
            # Check mobile prefix
            if cleaned.startswith('+254'):
                prefix = cleaned[4] if len(cleaned) > 4 else ''
            else:
                prefix = cleaned[1] if len(cleaned) > 1 else ''
            
            if prefix not in cls.VALID_PREFIXES:
                return PhoneValidationResult(
                    original=phone_str,
                    normalized=None,
                    is_valid=False,
                    status=PhoneStatus.INVALID_PREFIX,
                    error_message=f"Invalid prefix: must start with 7 or 1 (got {prefix})",
                    format_display=None
                )
            
            return PhoneValidationResult(
                original=phone_str,
                normalized=None,
                is_valid=False,
                status=PhoneStatus.INVALID_FORMAT,
                error_message="Invalid phone number format",
                format_display=None
            )
        
        # Normalize the phone
        normalized = cls.normalize(phone_str)
        
        if not normalized:
            return PhoneValidationResult(
                original=phone_str,
                normalized=None,
                is_valid=False,
                status=PhoneStatus.INVALID_FORMAT,
                error_message="Could not normalize phone number",
                format_display=None
            )
        
        # Check for duplicates
        if existing_phones and normalized in existing_phones:
            return PhoneValidationResult(
                original=phone_str,
                normalized=normalized,
                is_valid=False,
                status=PhoneStatus.DUPLICATE,
                error_message="Duplicate phone number",
                format_display=cls.format_display(normalized)
            )
        
        # All checks passed
        return PhoneValidationResult(
            original=phone_str,
            normalized=normalized,
            is_valid=True,
            status=PhoneStatus.VALID,
            error_message="Valid Kenyan phone number",
            format_display=cls.format_display(normalized)
        )
    
    @classmethod
    def is_valid(cls, phone: str) -> bool:
        """
        Quick check if phone is valid.
        
        Args:
            phone: Phone number
            
        Returns:
            True if valid
        """
        result = cls.validate(phone)
        return result.is_valid
    
    @classmethod
    def validate_or_none(cls, phone: str, existing_phones: Optional[Set[str]] = None) -> Optional[str]:
        """
        Validate and return normalized phone, or None if invalid.
        
        Args:
            phone: Phone number
            existing_phones: Set of existing phones for duplicate check
            
        Returns:
            Normalized phone or None
        """
        result = cls.validate(phone, existing_phones)
        return result.normalized if result.is_valid else None


# Convenience functions
def validate_kenyan_phone(phone: str, existing_phones: Optional[Set[str]] = None) -> PhoneValidationResult:
    """Full validation with detailed result"""
    return KenyaPhoneVerifier.validate(phone, existing_phones)


def is_valid_kenyan_phone(phone: str) -> bool:
    """Quick validation check"""
    return KenyaPhoneVerifier.is_valid(phone)


def normalize_kenyan_phone(phone: str) -> Optional[str]:
    """Normalize to international format"""
    return KenyaPhoneVerifier.normalize(phone)


def format_kenyan_phone(phone: str) -> str:
    """Format for display"""
    return KenyaPhoneVerifier.format_display(phone)


# Example usage
if __name__ == "__main__":
    test_cases = [
        # Valid phones
        ("+254712345678", True),
        ("+254112345678", True),
        ("0712345678", True),
        ("0112345678", True),
        ("254712345678", False),  # Missing +
        ("+254 712 345 678", True),  # With spaces
        
        # Invalid phones
        ("", False),  # Empty
        ("072345678", False),  # Too short
        ("07234567890", False),  # Too long
        ("+255712345678", False),  # Wrong country (Tanzania)
        ("+254512345678", False),  # Wrong prefix (5 instead of 7/1)
        ("1234567890", False),  # No country code
    ]
    
    print("Kenya Phone Verification - Test Results")
    print("=" * 60)
    
    for phone, expected_valid in test_cases:
        result = KenyaPhoneVerifier.validate(phone)
        status = "[PASS]" if result.is_valid == expected_valid else "[FAIL]"
        
        print(f"\n{status} Phone: {phone or '(empty)'}")
        print(f"  Expected: {'Valid' if expected_valid else 'Invalid'}")
        print(f"  Got: {'Valid' if result.is_valid else 'Invalid'}")
        print(f"  Normalized: {result.normalized}")
        print(f"  Display: {result.format_display}")
        if not result.is_valid:
            print(f"  Error: {result.error_message}")

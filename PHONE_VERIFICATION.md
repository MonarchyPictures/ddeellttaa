# Phone Number Verification - Kenya

## Overview

All phone numbers are validated before being shown or stored. This ensures data quality and prevents invalid contacts.

## Kenya Phone Pattern

```
^(\\+254|0)[17]\\d{8}$
```

### Valid Formats

| Format | Example | Status |
|--------|---------|--------|
| +254712345678 | +254 712 345 678 | ✅ Valid |
| +254112345678 | +254 112 345 678 | ✅ Valid |
| 0712345678 | +254 712 345 678 | ✅ Valid (converted) |
| 0112345678 | +254 112 345 678 | ✅ Valid (converted) |
| 254712345678 | - | ❌ Invalid (missing +) |
| 072345678 | - | ❌ Invalid (too short) |
| 07234567890 | - | ❌ Invalid (too long) |
| +255712345678 | - | ❌ Invalid (Tanzania) |
| 0123456789 | - | ❌ Invalid (wrong prefix) |

## Validation Checks

1. **Format Validation** - Must match Kenya phone regex
2. **Length Check** - 10 digits (local) or 12/13 digits (international)
3. **Country Prefix** - Must be +254 or 0
4. **Mobile Prefix** - Must start with 7 or 1
5. **Duplicate Check** - Optional duplicate detection
6. **Normalization** - Convert to standard format

## Implementation

### New File: `app/utils/phone_verification.py`

```python
class KenyaPhoneVerifier:
    @classmethod
    def validate(cls, phone: str) -> PhoneValidationResult:
        # Returns validation result with details
        
    @classmethod
    def normalize(cls, phone: str) -> str:
        # Converts to 254XXXXXXXXX format
        
    @classmethod
    def format_display(cls, phone: str) -> str:
        # Formats as +254 712 345 678
```

### Usage

```python
from app.utils.phone_verification import KenyaPhoneVerifier

# Validate a phone
result = KenyaPhoneVerifier.validate("0723898087")
print(result.is_valid)  # True
print(result.normalized)  # 254723898087
print(result.format_display)  # +254 723 898 087

# Quick check
if KenyaPhoneVerifier.is_valid("0723898087"):
    print("Valid phone!")

# Normalize
normalized = KenyaPhoneVerifier.normalize("0712345678")
print(normalized)  # 254712345678
```

## Integration with Buyer Extraction

Phone verification is integrated into buyer phone extraction:

```python
from app.utils.buyer_phone_extractor import BuyerPhoneExtractor

result = BuyerPhoneExtractor.validate_and_extract(
    "Looking for Toyota 0723898087"
)

print(result)
# {
#     "phone": "254723898087",
#     "phone_formatted": "+254 723 898 087",
#     "is_valid_buyer": True,
#     "reason": "Accepted: Buyer + valid phone (+254 723 898 087)"
# }
```

## Frontend Display

Phone numbers are formatted for display:

```javascript
// Raw: 254723898087
// Display: +254 723 898 087

const displayPhone = (phone) => {
  if (phone.startsWith('254') && phone.length === 12) {
    return `+${phone.slice(0, 3)} ${phone.slice(3, 6)} ${phone.slice(6, 9)} ${phone.slice(9)}`;
  }
  return phone;
};
```

## Rejection Reasons

| Reason | Example |
|--------|---------|
| Empty phone | `""` → "Phone number is empty" |
| Invalid length | `"07234567"` → "Invalid length: 8 digits" |
| Invalid country | `"+255712345678"` → "Invalid country code" |
| Invalid prefix | `"+254512345678"` → "Invalid prefix: must start with 7 or 1" |
| Missing + | `"254712345678"` → "Missing + before 254" |
| Duplicate | Existing phone → "Duplicate phone number" |

## Test Results

```
Kenya Phone Verification - Test Results
============================================================

[PASS] +254712345678 → Valid
[PASS] +254112345678 → Valid  
[PASS] 0712345678 → Valid
[PASS] 0112345678 → Valid
[PASS] 254712345678 → Invalid (missing +)
[PASS] (empty) → Invalid (empty)
[PASS] 072345678 → Invalid (too short)
[PASS] 07234567890 → Invalid (too long)
[PASS] +255712345678 → Invalid (wrong country)
[PASS] +254512345678 → Invalid (wrong prefix)

ALL TESTS PASSED!
```

## Summary

✅ **Valid**: +254712345678, +254112345678, 0712345678, 0112345678  
❌ **Invalid**: Wrong length, wrong country, wrong prefix, missing +  
📱 **Format**: Stored as 254XXXXXXXXX, displayed as +254 XXX XXX XXX

All phone numbers are validated before storage, ensuring only valid Kenyan mobile numbers enter the system.

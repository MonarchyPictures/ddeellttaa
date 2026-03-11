# Buyer Phone Number Extraction - Implementation Summary

## Rule

**ONLY extract phone numbers from buyer posts.**

```
IF text contains buyer intent
AND phone number is inside same message
THEN accept
ELSE reject
```

## Buyer Intent Keywords

The scraper looks for these buyer intent keywords (case insensitive):

- `looking for` / `lookingfor`
- `niko natafuta` (Swahili: "I am looking for")
- `need` / `i need`
- `anyone selling`
- `where can i buy`
- `who has`
- `tafuta` (Swahili)
- `natafuta` (Swahili)
- `want to buy`
- `in need of`
- `searching for`
- `shopping for`
- `interested in buying`

## Seller/Reject Keywords

Posts containing these keywords are rejected (unless buyer intent is also present):

- `selling`
- `available`
- `price`
- `call me`
- `DM for price`
- `for sale`
- `sell`
- `inbox for price`
- `hmu` (hit me up)
- `negotiable`
- `ono` (or nearest offer)

## Examples

### ✅ Accepted (Buyer Posts)

```
"Looking for Toyota Vitz 0723898087"
→ Extracts: 254723898087

"Niko natafuta gari call 0723123456"
→ Extracts: 254723123456

"Need iPhone 14 pro +254712345678"
→ Extracts: 254712345678

"Anyone selling a house? 0712345678"
→ Extracts: 254712345678 (buyer asking)
```

### ❌ Rejected (Seller Posts)

```
"Selling Toyota Vitz 0723898087"
→ Rejected: Seller post detected

"iPhone available call 0723123456"
→ Rejected: Seller post detected

"DM for price 0712345678"
→ Rejected: Seller post detected
```

### ❌ Rejected (No Buyer Intent)

```
"0723898087 call me"
→ Rejected: No buyer intent keywords found

"Price is 450k contact me"
→ Rejected: No buyer intent keywords found

"Contact me 0712345678"
→ Rejected: No buyer intent keywords found
```

## Implementation

### 1. New File: `app/utils/buyer_phone_extractor.py`

Core extraction logic with buyer validation.

```python
class BuyerPhoneExtractor:
    @classmethod
    def extract_buyer_phone(cls, text: str) -> Tuple[Optional[str], str]:
        # 1. Check for buyer intent
        # 2. Check for seller intent (if no buyer intent)
        # 3. Extract phone if valid buyer post
        # Returns: (phone_number, reason)
```

### 2. Updated: `app/scrapers/scraper_manager.py`

The `_process_signal()` method now uses buyer-only extraction:

```python
def _process_signal(self, result: ScrapeResult, query: str):
    # ... intent analysis ...
    
    # Extract phone ONLY from buyer posts
    extraction_result = BuyerPhoneExtractor.validate_and_extract(full_text)
    
    if not extraction_result['is_valid_buyer']:
        print(f"[ScraperManager] Rejected: {extraction_result['reason']}")
        return None  # Skip this signal
    
    phone = extraction_result['phone']
    # ... create signal with validated phone ...
```

### 3. Updated: `app/services/ingestion_service.py`

Double validation at ingestion:

```python
def ingest_signal(db, signal, product_query):
    # ... validation ...
    
    # Re-validate buyer phone at ingestion
    buyer_extraction = BuyerPhoneExtractor.validate_and_extract(raw_text, source)
    
    if not buyer_extraction['is_valid_buyer']:
        logger.warning(f"Not a valid buyer post: {buyer_extraction['reason']}")
        return None
    
    phone = buyer_extraction['phone']
    # ... save lead ...
```

## API Usage

### Quick Extraction

```python
from app.utils.buyer_phone_extractor import extract_buyer_phone

phone = extract_buyer_phone("Looking for car 0723123456")
# Returns: "254723123456" or None
```

### Full Validation

```python
from app.utils.buyer_phone_extractor import BuyerPhoneExtractor

result = BuyerPhoneExtractor.validate_and_extract(
    "Looking for Toyota 0723123456",
    source="Telegram"
)

print(result)
# {
#     "text": "Looking for Toyota 0723123456",
#     "phone": "254723123456",
#     "has_buyer_intent": True,
#     "has_seller_intent": False,
#     "is_valid_buyer": True,
#     "reason": "Accepted: Buyer intent + phone (254723123456)"
# }
```

### Filter List of Posts

```python
from app.utils.buyer_phone_extractor import filter_buyer_posts

posts = [
    {"text": "Looking for car 0723123456", "source": "Telegram"},
    {"text": "Selling car 0723987654", "source": "Telegram"},
]

valid_posts = filter_buyer_posts(posts)
# Returns only posts with buyer intent + phone
```

## Test Results

```
Buyer Phone Extractor - Test Results
============================================================

[PASS] Looking for Toyota Vitz 0723898087
[PASS] Niko natafuta gari call 0723123456
[PASS] Need iPhone 14 pro +254712345678
[PASS] Anyone selling a house? 0712345678
[PASS] Where can I buy a laptop 0711987654
[PASS] Selling Toyota Vitz 0723898087 (rejected)
[PASS] iPhone available call 0723123456 (rejected)
[PASS] DM for price 0712345678 (rejected)
[PASS] 0723898087 call me (rejected)
[PASS] Price is 450k DM me (rejected)
[PASS] Contact me 0712345678 (rejected)

ALL TESTS PASSED!
```

## Benefits

1. **Quality Control** - Only genuine buyer leads enter the system
2. **Reduced Noise** - Seller posts are filtered out at source
3. **Trust** - Users know every lead is from someone actively looking to buy
4. **Compliance** - Follows the business rule strictly

## Summary

✅ **Buyer posts with phones → Accepted**
❌ **Seller posts → Rejected**
❌ **Posts without buyer intent → Rejected**

This ensures Delta-9 only processes genuine buyer leads, significantly improving lead quality.

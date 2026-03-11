# Correct Lead Intelligence Architecture - Implementation Summary

## Overview
Implemented the Correct Lead Intelligence Architecture where every lead **MUST** have 5 mandatory fields:

1. **text** - The lead text/content
2. **phone** - Contact phone number
3. **source** - Source platform (e.g., Telegram, Reddit)
4. **url** - URL to the source post/message
5. **timestamp** - ISO format timestamp

**Rule:** If any of these are missing → **DISCARD LEAD**

## Lead Freshness Filter (NEW)

Leads are also filtered by freshness based on timestamp:

| Category | Age | Action |
|----------|-----|--------|
| **Fresh** | < 24 hours | Highest priority |
| **Warm** | < 3 days | Medium priority |
| **Cold** | < 7 days | Low priority |
| **Stale** | >= 7 days | **DISCARDED** |

**Backend Rule:**
```python
if lead.timestamp < now() - 7 days:
    discard lead
```

## Example Valid Lead

```json
{
  "text": "Looking for Toyota Vitz 2016",
  "phone": "0723898087",
  "source": "Telegram",
  "url": "https://t.me/kenya_cars/83922",
  "timestamp": "2026-03-08T10:33"
}
```

---

## Files Changed

### 1. `app/schemas/lead.py`
**Changes:**
- Added `LeadBase` schema with 5 mandatory fields
- Updated `LeadResponse` to include mandatory fields
- Added `LeadValidator` class for validation logic
- Added example lead structure

**Key Code:**
```python
class LeadBase(BaseModel):
    """Every lead MUST have these 5 mandatory fields"""
    text: str
    phone: str
    source: str
    url: str
    timestamp: str

class LeadValidator:
    MANDATORY_FIELDS = ['text', 'phone', 'source', 'url', 'timestamp']
    
    @classmethod
    def validate(cls, lead_data: dict) -> tuple[bool, Optional[str]]:
        for field in cls.MANDATORY_FIELDS:
            value = lead_data.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                return False, f"Missing mandatory field: {field}"
        return True, None
```

---

### 2. `app/models/lead.py`
**Changes:**
- Added 5 mandatory fields to `Lead` model:
  - `text` (Text, nullable=False)
  - `phone` (String(50), nullable=False)
  - `source` (String(100), nullable=False)
  - `url` (Text, nullable=False)
  - `timestamp` (DateTime, nullable=False)
- Added `has_mandatory_fields` property for runtime checking
- Fixed duplicate `default=False` in Signal model
- Renamed `metadata` to `extra_metadata` (SQLAlchemy reserved name fix)

**Key Code:**
```python
class Lead(Base):
    # 5 MANDATORY FIELDS
    text = Column(Text, nullable=False, index=True)
    phone = Column(String(50), nullable=False, index=True)
    source = Column(String(100), nullable=False, index=True)
    url = Column(Text, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    @property
    def has_mandatory_fields(self) -> bool:
        return all([
            self.text and str(self.text).strip(),
            self.phone and str(self.phone).strip(),
            self.source and str(self.source).strip(),
            self.url and str(self.url).strip(),
            self.timestamp is not None
        ])
```

---

### 3. `app/utils/lead_validation.py` (NEW FILE)
**Purpose:** Central validation utility for leads

**Key Functions:**
- `LeadValidator.validate()` - Check if lead has all 5 mandatory fields
- `LeadValidator.validate_or_discard()` - Returns lead if valid, None if invalid
- `LeadValidator.validate_list()` - Batch validation
- `LeadValidator.enforce_strict()` - Raises exception on invalid
- `validate_lead()` - Convenience function
- `filter_valid_leads()` - Filter list to valid leads only

---

### 4. `app/services/ingestion_service.py`
**Changes:**
- Added import for `LeadValidator`
- Added mandatory field validation at start of `ingest_signal()`
- Leads missing mandatory fields are immediately discarded with warning log
- Updated Lead creation to populate mandatory fields

**Key Code:**
```python
def ingest_signal(db: Session, signal: Dict[str, Any], product_query: str = "Unknown"):
    # MANDATORY FIELD VALIDATION
    is_valid, error = LeadValidator.validate(signal)
    if not is_valid:
        logger.warning(f"[INGESTION] Lead discarded - {error}")
        return None
    
    # Extract mandatory fields
    mandatory_text = signal.get("text", "").strip()
    mandatory_phone = signal.get("phone", "").strip()
    mandatory_source = signal.get("source", "").strip()
    mandatory_url = signal.get("url", "").strip()
    mandatory_timestamp = signal.get("timestamp", "").strip()
    
    # Create Lead with mandatory fields
    db_lead = models.Lead(
        text=mandatory_text,
        phone=mandatory_phone,
        source=mandatory_source,
        url=mandatory_url,
        timestamp=parsed_timestamp,
        # ... other fields
    )
```

---

### 5. `app/services/pipeline.py`
**Changes:**
- Added import for `LeadValidator`
- Added mandatory field validation in `process_raw_lead()`
- Leads missing mandatory fields are rejected before processing

**Key Code:**
```python
def process_raw_lead(self, raw_data: Dict[str, Any]) -> Optional[models.Lead]:
    # MANDATORY FIELD VALIDATION
    is_valid, error = LeadValidator.validate(raw_data)
    if not is_valid:
        return self._reject(raw_data, f"Mandatory field validation failed: {error}")
    
    # Extract mandatory fields
    mandatory_text = raw_data.get('text', '').strip()
    mandatory_phone = raw_data.get('phone', '').strip()
    mandatory_source = raw_data.get('source', '').strip()
    mandatory_url = raw_data.get('url', '').strip()
    mandatory_timestamp = raw_data.get('timestamp', '').strip()
    
    # Continue processing...
```

---

### 6. `app/scrapers/scraper_manager.py`
**Changes:**
- Updated `_process_signal()` to include 5 mandatory fields in signal output
- Added `_extract_phone()` helper method to extract phone numbers from text
- Ensures signals produced by scrapers include all mandatory fields

**Key Code:**
```python
def _process_signal(self, result: ScrapeResult, query: str) -> Optional[Dict]:
    # Extract phone from content
    phone = self._extract_phone(full_text)
    
    return {
        # 5 MANDATORY FIELDS
        "text": full_text.strip(),
        "phone": phone or "",
        "source": result.source,
        "url": result.url,
        "timestamp": posted_at,
        # ... other fields
    }
```

---

### 7. `app/main.py`
**Changes:**
- Fixed import error: `process_signal` now imported from `signal_pipeline`

---

## Validation Behavior

### When a lead is valid:
```
[INGESTION] ✅ Mandatory fields validated for source: Telegram
[LeadValidator] ✅ Lead passes validation
```

### When a lead is missing mandatory fields:
```
[INGESTION] ❌ Lead discarded - Missing mandatory field: phone: https://t.me/...
[LeadValidator] ❌ Lead discarded: Missing mandatory field: phone
```

---

## Testing

Run manual validation test:
```python
from app.utils.lead_validation import LeadValidator

# Valid lead
lead = {
    "text": "Looking for Toyota Vitz 2016",
    "phone": "0723898087",
    "source": "Telegram",
    "url": "https://t.me/kenya_cars/83922",
    "timestamp": "2026-03-08T10:33"
}
is_valid, error = LeadValidator.validate(lead)
# Returns: (True, None)

# Invalid lead (missing phone)
invalid_lead = {
    "text": "Looking for Toyota Vitz 2016",
    "source": "Telegram",
    "url": "https://t.me/kenya_cars/83922",
    "timestamp": "2026-03-08T10:33"
}
is_valid, error = LeadValidator.validate(invalid_lead)
# Returns: (False, "Missing mandatory field: phone")

# Validate or discard
result = LeadValidator.validate_or_discard(invalid_lead)
# Returns: None (lead is discarded)
```

---

## Impact

### Before this fix:
- Leads could be created with missing critical information
- Incomplete leads polluted the database
- No standardized required fields

### After this fix:
- **Strict enforcement** of 5 mandatory fields
- Incomplete leads are **immediately discarded** at ingestion
- Consistent lead structure throughout the system
- Clear logging for rejected leads

---

## Migration Notes

1. **Existing leads** in the database may not have the mandatory fields populated
2. **New leads** will be required to have all 5 fields
3. **Scrapers** must be updated to extract phone numbers from content
4. **Database migration** may be needed to add the mandatory columns if they don't exist

---

## Summary

The Correct Lead Intelligence Architecture is now implemented.

### Mandatory Fields (5 required):
- ✅ `text` - Lead content
- ✅ `phone` - Contact number
- ✅ `source` - Platform source
- ✅ `url` - Source URL
- ✅ `timestamp` - ISO timestamp

**If any are missing → lead is DISCARDED**

### Freshness Filter:
- ✅ **Fresh** (< 24h) - Highest priority
- ✅ **Warm** (< 3 days) - Medium priority
- ✅ **Cold** (< 7 days) - Low priority
- ❌ **Stale** (≥ 7 days) - **DISCARDED**

### Additional Documentation:
- See `LEAD_FRESHNESS_FILTER.md` for detailed freshness filter documentation

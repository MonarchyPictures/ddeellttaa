# Lead Freshness Filter - Implementation Summary

## Overview
Added Lead Freshness Filter to automatically categorize and filter leads based on age.

## Freshness Categories

| Category | Age | Action |
|----------|-----|--------|
| **Fresh** | < 24 hours | Highest priority |
| **Warm** | < 3 days | Medium priority |
| **Cold** | < 7 days | Low priority |
| **Stale** | >= 7 days | **DISCARDED** |

## Backend Rule

```python
if lead.timestamp < now() - 7 days:
    discard lead
```

## Implementation

### 1. `app/utils/lead_validation.py`

Added freshness checking classes:

```python
class LeadFreshness(str, Enum):
    FRESH = "fresh"      # < 24 hours
    WARM = "warm"        # < 3 days
    COLD = "cold"        # < 7 days
    STALE = "stale"      # >= 7 days (DISCARD)

class FreshnessChecker:
    """Checks lead freshness based on timestamp"""
    
    def check_freshness(self, timestamp) -> LeadFreshness:
        # Returns freshness category
        
    def is_fresh_enough(self, timestamp) -> bool:
        # Returns True if < 7 days old
        
    def get_freshness_with_metadata(self, timestamp) -> dict:
        # Returns full freshness info
```

### 2. Combined Validation

```python
class LeadQualificationValidator:
    """Combined validator: mandatory fields + freshness"""
    
    @classmethod
    def validate_or_discard(cls, lead_data):
        # 1. Check 5 mandatory fields
        # 2. Check freshness (< 7 days)
        # Returns lead with freshness metadata, or None if rejected
```

### 3. Database Schema Updates

**`app/models/lead.py`:**
```python
class Lead(Base):
    # 5 MANDATORY FIELDS
    text = Column(Text, nullable=False)
    phone = Column(String(50), nullable=False)
    source = Column(String(100), nullable=False)
    url = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    
    # LEAD FRESHNESS (NEW)
    freshness = Column(String(20), default="unknown")
    age_hours = Column(Float, default=0.0)
```

**`app/schemas/lead.py`:**
```python
class LeadResponse(BaseModel):
    # 5 MANDATORY FIELDS
    text: str
    phone: str
    source: str
    url: str
    timestamp: str
    
    # FRESHNESS FIELDS (NEW)
    freshness: Optional[str]  # fresh/warm/cold/stale
    age_hours: Optional[float]
```

### 4. Ingestion Service Integration

**`app/services/ingestion_service.py`:**

```python
def ingest_signal(db, signal, product_query):
    # STEP 0: Combined validation (mandatory fields + freshness)
    validated_lead = LeadQualificationValidator.validate_or_discard(signal)
    if not validated_lead:
        return None
    
    # Extract freshness metadata
    freshness_metadata = validated_lead.get('_freshness', {})
    freshness_label = freshness_metadata.get('freshness_label', 'unknown')
    age_hours = freshness_metadata.get('age_hours', 0)
    
    # Create lead with freshness info
    db_lead = models.Lead(
        # ... mandatory fields ...
        freshness=freshness_label,
        age_hours=age_hours,
        # ... other fields ...
    )
```

## Usage Examples

### Check Freshness

```python
from app.utils.lead_validation import FreshnessChecker, LeadFreshness

checker = FreshnessChecker()
freshness = checker.check_freshness("2026-03-10T10:00:00")

if freshness == LeadFreshness.FRESH:
    print("High priority lead!")
elif freshness == LeadFreshness.STALE:
    print("Discard - too old")
```

### Validate with Freshness

```python
from app.utils.lead_validation import LeadQualificationValidator

lead = {
    "text": "Looking for Toyota Vitz",
    "phone": "0723898087",
    "source": "Telegram",
    "url": "https://t.me/kenya_cars/123",
    "timestamp": "2026-03-01T10:00:00"  # Old lead!
}

result = LeadQualificationValidator.validate_or_discard(lead)
# Returns None (lead is stale)
```

### Convenience Function

```python
from app.utils.lead_validation import check_lead_freshness

freshness = check_lead_freshness("2026-03-10T12:00:00")
print(freshness.value)  # "fresh", "warm", "cold", or "stale"
```

## Log Output Examples

### Fresh Lead Accepted:
```
[LeadQualification] ✅ Lead qualified: freshness=fresh, age=6.0h
[INGESTION] ✅ Lead qualified: source=Telegram, freshness=fresh
SIGNAL ACCEPTED: HIGH lead saved from Telegram | Score: 0.850 | Freshness: FRESH (6.0h old)
```

### Stale Lead Discarded:
```
[FreshnessChecker] ❌ Lead discarded: Too old (10.0 days)
[LeadQualification] ❌ Lead discarded: Lead too old: 10.0 days (max 7 days)
```

## Test Results

```
============================================================
LEAD FRESHNESS FILTER TESTS
============================================================

Categories:
  - Fresh = < 24 hours
  - Warm = < 3 days
  - Cold = < 7 days
  - Stale (DISCARD) = >= 7 days

[PASS] 12 hours old = FRESH
[PASS] 2 days old = WARM
[PASS] 5 days old = COLD
[PASS] 8 days old = STALE (discard)
[PASS] Exactly 7 days = STALE (discard cutoff)
[PASS] Almost 7 days = COLD

[PASS] Fresh, Warm, Cold leads are 'fresh enough'
[PASS] Stale leads are NOT 'fresh enough'

[PASS] Fresh metadata: {...}

[PASS] ISO string timestamp works
[PASS] Old ISO string timestamp = STALE

[PASS] Fresh lead passes freshness check
[PASS] Stale lead is discarded

[PASS] Valid + fresh lead passes full qualification
[PASS] Valid but stale lead is rejected
[PASS] Invalid lead (missing phone) is rejected

[PASS] check_lead_freshness() works with datetime
[PASS] check_lead_freshness() works with ISO string

============================================================
ALL FRESHNESS TESTS PASSED!
============================================================
```

## Summary

✅ Leads < 24h old → **FRESH** (highest priority)
✅ Leads < 3 days old → **WARM** (medium priority)
✅ Leads < 7 days old → **COLD** (low priority)
❌ Leads >= 7 days old → **STALE** (DISCARDED)

The freshness filter is now integrated into the lead qualification pipeline and will automatically reject stale leads before they enter the database.

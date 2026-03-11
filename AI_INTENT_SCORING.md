# AI Intent Scoring System

## Overview

Replaces random scoring with AI-powered intent analysis that scores leads from 0-100 based on buying signals in the text.

## Score Categories

| Category | Score | Description | Example |
|----------|-------|-------------|---------|
| **HOT** | 75-100 | Urgent buyer, ready now | "I need Toyota Vitz urgently today" |
| **WARM** | 50-74 | Active buyer, researching | "Looking for Vitz 2016 model" |
| **COLD** | 25-49 | Passive interest | "Thinking of buying Vitz" |
| **REJECT** | <25 | Not a genuine buyer | "Just browsing cars for fun" |

## Scoring Factors

### 1. Urgency Indicators (+60 max)
- **High (+30)**: urgently, immediately, asap, today, now, yesterday
- **Medium (+20)**: this week, soon, quickly, fast
- **Low (+10)**: this month
- **Swahili**: hapo sasa (+30), sasa hivi (+30)

### 2. Product Specificity (+65 max)
- **Brand + Model (+25)**: "Toyota Vitz", "Honda Fit"
- **Year Mentioned (+20)**: "2016 model", "'16 edition"
- **Color Preference (+15)**: "white one", "black color"

### 3. Buying Intent (+35 max)
- **Strong (+20)**: need, want to buy, natafuta, nahitaji
- **Medium (+18)**: looking for, searching for
- **Weak (+8)**: considering, thinking about

### 4. Price/Budget (+30 max)
- Budget mention (+15)
- Specific amount (+15): "800k", "1.2m"
- Range (+15): "between 500k and 800k"

### 5. Contact Readiness (+10 max)
- Phone present (+10)
- "Call me", "text me", "whatsapp" (+10)

### 6. Negative Signals (-80 max)
- **Strong (-40)**: just browsing, for fun, window shopping
- **Medium (-30)**: maybe later, not sure
- **Weak (-20)**: thinking, considering, might buy

### 7. Quality Indicators (+10 max)
- Good condition (+5)
- Clean (+5)
- Original paint (+5)
- Full documents (+5)

## Implementation

### New File: `app/utils/intent_scorer.py`

```python
from app.utils.intent_scorer import IntentScorer

# Score a lead
result = IntentScorer.calculate_score("I need Toyota Vitz urgently today")
print(result.score)        # 100
print(result.temperature)  # LeadTemperature.HOT
print(result.reasoning)    # "High urgency detected; Specific product mentioned; Strong buying intent"

# Quick classification
temp, score, reasoning = IntentScorer.classify("Looking for Vitz 2016")
print(temp)    # "WARM"
print(score)   # 72
```

### Database Schema

Added to `Lead` model:
```python
ai_intent_score = Column(Integer, default=0)  # 0-100
ai_temperature = Column(String(20))           # HOT/WARM/COLD/REJECT
ai_score_reasoning = Column(Text)             # Explanation
ai_score_breakdown = Column(JSONB)            # Point breakdown
```

### Integration

In `ingestion_service.py`:
```python
# AI Intent Scoring
intent_score_result = IntentScorer.calculate_score(raw_text)
ai_intent_score = intent_score_result.score
ai_temperature = intent_score_result.temperature.value

# Blend with traditional scoring (70% AI, 30% traditional)
blended_intent = (ai_intent_score / 100 * 0.7) + (raw_intent * 0.3)

# Reject if AI score is too low
if intent_score_result.temperature == LeadTemperature.REJECT:
    return None
```

## Frontend Display

### LeadCard Badge
```jsx
{aiScore > 0 && (
  <span className="...">
    <Flame size={12} />
    {aiScore}/100
  </span>
)}
```

### Temperature Display
- 🔥 **HOT** (75-100): Red badge
- ☀️ **WARM** (50-74): Yellow badge
- ❄️ **COLD** (25-49): Blue badge
- ⚪ **REJECT** (<25): Gray badge

## Test Examples

| Text | Score | Temperature |
|------|-------|-------------|
| "I need Toyota Vitz urgently today" | 100 | HOT |
| "Looking for fielder 2016 budget 800k call 0723..." | 100 | HOT |
| "Nahitaji gari urgently hapo sasa" | 80 | HOT |
| "Looking for Vitz 2016" | 43 | COLD |
| "Want to buy Honda Fit this week" | 80 | HOT |
| "Searching for clean premio around 1m" | 60 | WARM |
| "Thinking of buying Vitz maybe" | 5 | REJECT |
| "Just browsing cars for fun" | 0 | REJECT |

## Benefits

1. **Accurate Classification** - Based on actual message content
2. **Explainable** - Shows why a lead is HOT/WARM/COLD
3. **Language Support** - Works with English and Swahili
4. **Rejects Noise** - Filters out casual browsers
5. **Prioritizes Urgency** - Real buyers with timelines score higher

## Summary

✅ **HOT (75-100)**: Urgent buyers with specific needs  
✅ **WARM (50-74)**: Active buyers researching  
⚠️ **COLD (25-49)**: Passive interest only  
❌ **REJECT (<25)**: Not genuine buyers

AI Intent Scoring ensures leads are scored based on actual buying signals, not random numbers.

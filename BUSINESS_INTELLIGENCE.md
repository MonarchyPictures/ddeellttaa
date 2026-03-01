# Business Intelligence Layer

Delta9 now provides actionable business intelligence, not just raw leads.

---

## 📊 Layer 4 — Lead Intelligence Dashboard

### Problem: Raw Leads Are Not Actionable

**Before:**
```
Delta9 returns:
- Lead 1: "Natafuta pipes"
- Lead 2: "Looking for tiles"
- Lead 3: "Need cement"

User thinks: "So what? Where are my buyers?"
```

**After:**
```
Delta9 Intelligence Dashboard:

📍 Buyer Heatmap
   Nairobi: 45 leads (60% hot)
   Mombasa: 23 leads (40% hot)
   Kisumu:  12 leads (30% hot)

💰 Budget Distribution
   50K-100K:   30% of buyers
   100K-500K:  45% of buyers
   500K-1M:    20% of buyers
   1M+:         5% of buyers

⏰ Urgency Trends
   Urgent leads: ↑ 25% this week
   Normal leads: ↓ 10% this week

📈 Top Product Demand
   1. Pipes (35 leads)
   2. Tiles (28 leads)
   3. Cement (22 leads)
```

---

## API Endpoints

### Full Intelligence Dashboard

```bash
GET /api/dashboard/intelligence
```

**Response:**
```json
{
  "status": "success",
  "period": "last_30_days",
  "dashboard": {
    "total_leads": 156,
    "heatmap": {
      "type": "geo_heatmap",
      "top_county": "nairobi",
      "data": [
        {"county": "nairobi", "total_leads": 67, "hot_leads": 40, "intensity": 1.0},
        {"county": "mombasa", "total_leads": 34, "hot_leads": 15, "intensity": 0.51},
        {"county": "kisumu", "total_leads": 23, "hot_leads": 8, "intensity": 0.34}
      ]
    },
    "budget_distribution": {
      "average": 245000,
      "data": [
        {"range": "50K-100K", "count": 45, "percentage": 30.0},
        {"range": "100K-500K", "count": 68, "percentage": 45.0},
        {"range": "500K-1M", "count": 30, "percentage": 20.0}
      ]
    },
    "urgency_trends": {
      "trend_direction": "increasing",
      "data": [
        {"date": "2024-01-01", "urgent": 5, "high": 10, "normal": 20},
        {"date": "2024-01-02", "urgent": 8, "high": 12, "normal": 18}
      ]
    },
    "product_demand": {
      "top_product": "pipes",
      "data": [
        {"product": "pipes", "total_leads": 35, "hot_leads": 20, "demand_score": 75},
        {"product": "tiles", "total_leads": 28, "hot_leads": 15, "demand_score": 58},
        {"product": "cement", "total_leads": 22, "hot_leads": 10, "demand_score": 42}
      ]
    }
  }
}
```

### Individual Endpoints

```bash
# Buyer heatmap by county
GET /api/dashboard/heatmap

# Budget distribution
GET /api/dashboard/budget-distribution

# Product demand ranking
GET /api/dashboard/product-demand
```

---

## Visualizations

### 1. Buyer Heatmap by County

**Use Case:** Where should I focus my sales efforts?

```python
from app.services.intelligence_dashboard import IntelligenceDashboard

dashboard = IntelligenceDashboard(leads)
heatmap = dashboard.generate_heatmap()

# Result: Choropleth map or bar chart
# Nairobi: ████████████████████ 67 leads
# Mombasa: ██████████ 34 leads
# Kisumu:  ███████ 23 leads
```

### 2. Budget Distribution Chart

**Use Case:** What price range should I stock?

```python
distribution = dashboard.generate_budget_distribution()

# Result: Histogram
# 0-50K:    ██ 15 buyers
# 50-100K:  ██████ 45 buyers
# 100-500K: █████████ 68 buyers
# 500K-1M:  ████ 30 buyers
# 1M+:      █ 8 buyers
```

### 3. Urgency Trend Graph

**Use Case:** Are buyers becoming more urgent?

```python
trends = dashboard.generate_urgency_trends()

# Result: Line chart
# Jan 1: ●────●────●
# Jan 2:    ●────●────●
# Jan 3:       ●────●────● (trending up)
```

### 4. Top Product Demand

**Use Case:** What products are in highest demand?

```python
demand = dashboard.generate_product_demand()

# Result: Ranked list
# 1. Pipes  ████████████████████ 35 leads
# 2. Tiles  ████████████████ 28 leads
# 3. Cement ████████████ 22 leads
```

---

## Business Value

| Insight | Action | Revenue Impact |
|---------|--------|----------------|
| "Nairobi has 60% hot leads" | Focus sales team on Nairobi | +30% conversion |
| "Most buyers have 100K-500K budget" | Stock mid-range products | +25% sales |
| "Urgency trending up" | Increase prices slightly | +15% margin |
| "Pipes #1 demand" | Increase pipe inventory | +20% turnover |

---

## Deduplication Layer

### Beyond URL Matching

**File:** `app/services/deduplication_engine.py`

**Problem:** Same buyer posts on multiple platforms

```
Post 1: "Natafuta pipes" on Facebook
  URL: facebook.com/groups/xyz/posts/123
  Phone: 0712345678

Post 2: "Looking for pvc pipes" on Telegram
  URL: t.me/channel/456
  Phone: 0712345678  ← SAME PERSON

Old dedup: Keeps both (different URLs)
New dedup: Removes duplicate (same phone)
```

### Multi-Signal Deduplication

| Signal | Method | Weight |
|--------|--------|--------|
| **URL** | Exact match | 100% duplicate |
| **Phone** | Normalized match + text similarity | 90% confidence |
| **Text** | 75% fuzzy similarity | 80% confidence |
| **Product** | Same product category | 50% confidence |

**Example:**
```python
from app.services.deduplication_engine import deduplicate_leads

raw_leads = [
    {"title": "Natafuta pipes", "url": "fb.com/1", "snippet": "Call 0712345678"},
    {"title": "Need pipes", "url": "tg.me/2", "snippet": "Contact 0712345678"},  # Dup!
    {"title": "Selling pipes", "url": "fb.com/3", "snippet": "We have pipes"},  # Different
]

unique_leads = deduplicate_leads(raw_leads)
# Result: 2 leads (removed phone match duplicate)
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    RAW LEADS                                │
│  (from 14 scrapers)                                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    DEDUPLICATION ENGINE                      │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  URL Match   │  │ Phone Match  │  │ Text Similar │      │
│  │  (exact)     │  │ (+50% text)  │  │  (75% fuzz)  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  Result: Unique leads only                                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    SCORING & PROCESSING                      │
│  (weighted intent model)                                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    INTELLIGENCE DASHBOARD                    │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Heatmap    │  │   Budget     │  │   Trends     │      │
│  │  By County   │  │ Distribution │  │   Graph      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  ┌──────────────┐                                           │
│  │ Product      │                                           │
│  │ Demand       │                                           │
│  └──────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    ACTIONABLE INSIGHTS                       │
│  "Focus on Nairobi, stock 100K-500K pipes, urgency rising"  │
└─────────────────────────────────────────────────────────────┘
```

---

## Migration Guide

### Enable New Features

```bash
# Enable advanced deduplication
USE_ADVANCED_DEDUP=true

# Enable intelligence dashboard
USE_INTELLIGENCE_DASHBOARD=true

# Deduplication thresholds
TEXT_SIMILARITY_THRESHOLD=0.75
PHONE_MATCH_CONFIDENCE=0.90
```

### API Changes

**Old:**
```python
# Simple URL dedup
seen_urls = set()
for lead in leads:
    if lead['url'] not in seen_urls:
        process(lead)
        seen_urls.add(lead['url'])
```

**New:**
```python
# Multi-signal dedup
from app.services.deduplication_engine import deduplicate_leads

unique_leads = deduplicate_leads(raw_leads)
# Handles URL + phone + text similarity
```

---

**Delta9 is now a business intelligence tool, not just a scraper.**

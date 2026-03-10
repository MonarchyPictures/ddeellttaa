# Delta-9 Lead Database

Structured PostgreSQL database for storing verified leads.

## Schema Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  search_queries │────▶│     signals     │────▶│      leads      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │ lead_activities │
                                               └─────────────────┘
```

## Tables

### 1. search_queries
Tracks what users are searching for.

```sql
id                  INTEGER PRIMARY KEY
original_query      VARCHAR(255)        -- User's search term
expanded_queries    JSON                -- AI-expanded phrases
category            VARCHAR(100)        -- Industry category
location            VARCHAR(100)        -- Geographic location
is_active           BOOLEAN             -- Still monitoring?
created_at          TIMESTAMP
last_searched       TIMESTAMP
total_signals       INTEGER
total_leads         INTEGER
```

### 2. signals
Raw signals from scrapers (Signal Stream persistent storage).

```sql
id                  INTEGER PRIMARY KEY
external_id         VARCHAR(255)        -- Reddit post ID, Tweet ID, etc.
source              VARCHAR(50)         -- reddit, twitter, forum
source_url          TEXT                -- Link to original post
title               TEXT
content             TEXT                -- Main signal text
raw_content         TEXT                -- Original unprocessed
author              VARCHAR(255)        -- Username
author_karma        INTEGER             -- Platform karma/score
account_created_at  TIMESTAMP           -- For age verification
query_matched       VARCHAR(255)        -- Which query found this
subreddit           VARCHAR(100)        -- For Reddit
forum_name          VARCHAR(100)        -- For forums

-- Intent Detection AI results
intent_score        FLOAT               -- 0-1 buyer probability
intent_category     VARCHAR(50)         -- buying, researching, vendor
buying_urgency      VARCHAR(20)         -- immediate, soon, future
keywords_matched    VARCHAR[]           -- PostgreSQL array

-- Lead Verification Layer results
verification_score  FLOAT               -- 0-1 quality score
verification_status VARCHAR(20)         -- verified, suspicious, rejected
rejection_reasons   VARCHAR[]           -- spam, bot, repost, too_old

-- Status
is_processed        BOOLEAN
is_lead             BOOLEAN
is_duplicate        BOOLEAN
posted_at           TIMESTAMP           -- When posted on source
discovered_at       TIMESTAMP           -- When we found it
processed_at        TIMESTAMP
metadata            JSONB               -- Platform-specific data
```

**Indexes:**
- `idx_signals_source_intent` (source, intent_score)
- `idx_signals_author_source` (author, source)
- `idx_signals_discovered_intent` (discovered_at, intent_score)
- `idx_signals_verification` (verification_status, is_lead)

### 3. leads
Verified leads with full contact data.

```sql
id                  INTEGER PRIMARY KEY
signal_ids          INTEGER[]           -- Source signal IDs
sources             VARCHAR[]           -- ["reddit", "twitter"]

-- Contact Info
name                VARCHAR(255)
username            VARCHAR(255)        -- Platform username
email               VARCHAR(255)        -- Extracted email
phone               VARCHAR(50)         -- Extracted phone
company             VARCHAR(255)
job_title           VARCHAR(255)

-- Location
location            VARCHAR(255)
country             VARCHAR(100)        -- Default: Kenya

-- Intent Data
intent_signals      TEXT[]              -- What they said
intent_category     VARCHAR(50)         -- buying, researching
intent_score        FLOAT               -- 0-1
buying_urgency      VARCHAR(20)         -- immediate, soon, future
budget_hint         VARCHAR(100)        -- Extracted budget mentions

-- Verification
verification_score  FLOAT               -- 0-1
verification_status VARCHAR(20)

-- Engagement
profile_urls        JSONB               -- {"reddit": "...", "twitter": "..."}

-- CRM
status              VARCHAR(20)         -- new, qualified, contacted, converted
priority            VARCHAR(20)         -- low, medium, high, urgent
priority_score      FLOAT               -- Combined score for sorting
assigned_to         VARCHAR(255)        -- Sales rep
tags                VARCHAR[]
notes               TEXT

-- Communication Tracking
contacted_at        TIMESTAMP
contacted_via       VARCHAR(50)         -- email, phone, dm
response_at         TIMESTAMP
converted_at        TIMESTAMP

-- Timestamps
first_seen          TIMESTAMP
last_active         TIMESTAMP
updated_at          TIMESTAMP

-- Extensibility
custom_fields       JSONB
```

**Indexes:**
- `idx_leads_status_priority` (status, priority_score)
- `idx_leads_intent_verification` (intent_score, verification_score)
- `idx_leads_country_status` (country, status)

### 4. lead_activities
CRM-style activity log for each lead.

```sql
id              INTEGER PRIMARY KEY
lead_id         INTEGER FOREIGN KEY
activity_type   VARCHAR(50)     -- email_sent, call_made, note_added
description     TEXT
performed_by    VARCHAR(255)    -- User who did this
created_at      TIMESTAMP
metadata        JSONB
```

### 5. lead_analytics
Daily metrics for analytics (consider ClickHouse for scale).

```sql
id                  INTEGER PRIMARY KEY
date                TIMESTAMP
new_leads           INTEGER
qualified_leads     INTEGER
contacted_leads     INTEGER
converted_leads     INTEGER
source_breakdown    JSONB           -- {"reddit": 10, "twitter": 5}
intent_breakdown    JSONB           -- {"buying": 8, "researching": 7}
avg_intent_score    FLOAT
avg_verification    FLOAT
conversion_rate     FLOAT
```

## Usage

### Initialize Database

```bash
# Create all tables
python manage_db.py init

# Run migrations (Alembic)
python manage_db.py migrate

# Seed with sample data
python manage_db.py seed

# Verify connection
python manage_db.py verify
```

### Quick Stats

```bash
python manage_db.py stats
```

### Using in Code

```python
from app.models.lead import get_db, Lead, Signal
from sqlalchemy.orm import Session

# FastAPI dependency
def get_leads(db: Session = Depends(get_db)):
    return db.query(Lead).filter(Lead.status == "new").all()

# Direct usage
db = SessionLocal()
try:
    # Query leads
    high_priority = db.query(Lead).filter(
        Lead.intent_score >= 0.7,
        Lead.verification_score >= 0.8
    ).order_by(Lead.priority_score.desc()).all()
    
    # Create lead
    lead = Lead(
        username="john_buyer",
        email="john@example.com",
        intent_score=0.85,
        sources=["reddit"],
    )
    db.add(lead)
    db.commit()
finally:
    db.close()
```

### Query Examples

```sql
-- High-quality leads (intent + verified)
SELECT * FROM leads 
WHERE intent_score >= 0.7 
  AND verification_score >= 0.8
  AND status = 'new'
ORDER BY priority_score DESC
LIMIT 50;

-- Recent signals by source
SELECT source, COUNT(*) 
FROM signals 
WHERE discovered_at > NOW() - INTERVAL '24 hours'
GROUP BY source;

-- Lead conversion funnel
SELECT 
    status,
    COUNT(*),
    AVG(intent_score) as avg_intent
FROM leads 
GROUP BY status;

-- Search query performance
SELECT 
    original_query,
    total_leads,
    (total_leads::float / NULLIF(total_signals, 0)) as conversion_rate
FROM search_queries
WHERE is_active = true;
```

## PostgreSQL vs SQLite

### Development (SQLite)
```bash
DATABASE_URL="sqlite:///./delta9.db"
```

### Production (PostgreSQL)
```bash
DATABASE_URL="postgresql://user:pass@localhost:5432/delta9"
```

Benefits of PostgreSQL:
- ✅ Concurrent connections (pooling)
- ✅ Full-text search
- ✅ JSONB for metadata
- ✅ Array columns
- ✅ Better performance at scale
- ✅ Advanced indexing (GIN, etc.)

## High Scale: ClickHouse

For analytics at scale (>10M signals/day), use ClickHouse:

```python
# Store transactional data in PostgreSQL
# Store analytics data in ClickHouse

# Example: Bulk insert to ClickHouse
from clickhouse_driver import Client

client = Client('localhost')
client.execute('''
    INSERT INTO signals (id, source, intent_score, discovered_at)
    VALUES
''', signals_batch)
```

## Connection Pooling

Production PostgreSQL configuration:

```python
engine = create_engine(
    DATABASE_URL,
    pool_size=10,              # Keep 10 connections ready
    max_overflow=20,           # Allow 20 extra under load
    pool_pre_ping=True,        # Verify before using
    pool_recycle=3600,         # Recycle after 1 hour
)
```

## Backup & Restore

### PostgreSQL
```bash
# Backup
pg_dump $DATABASE_URL > backup.sql

# Restore
psql $DATABASE_URL < backup.sql
```

### SQLite
```bash
# Backup
python manage_db.py backup

# Or manually
cp delta9.db delta9_backup.db
```

## Schema Migrations

Using Alembic:

```bash
# Create migration
alembic revision --autogenerate -m "add new field"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

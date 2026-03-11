# Source Panel - Filter Component

## Overview

The Source Panel provides an intuitive filtering interface for leads by source platform and freshness. This allows users to quickly narrow down leads based on where they came from and how recent they are.

---

## Features

### Source Filters

| Source | Icon | Color | Description |
|--------|------|-------|-------------|
| Telegram | MessageCircle | Blue | Telegram channels and groups |
| Facebook | Globe | Blue | Facebook posts and marketplace |
| Jiji | ShoppingBag | Orange | Jiji.co.ke listings |
| Reddit | Globe | Orange | Reddit posts and comments |
| Google | Search | Green | Google search results |

### Freshness Filters

| Filter | Label | Description |
|--------|-------|-------------|
| 24h | Last 24h | Fresh leads - highest priority |
| 3d | Last 3 days | Warm leads - medium priority |
| 7d | Last 7 days | Cold leads - still relevant |

---

## UI Components

### SourceFilterPanel

```jsx
<SourceFilterPanel 
  onFilterChange={handleFilterChange}
  initialFilters={{
    sources: ['telegram', 'facebook', 'jiji', 'reddit', 'google'],
    freshness: ['24h', '3d', '7d']
  }}
/>
```

**Props:**
- `onFilterChange` (function) - Called when filters change
- `initialFilters` (object) - Initial filter state

### Visual Design

```
┌─────────────────────────────────────────────────────────┐
│ [⚙️] Source Panel                      [2 of 8]    [▼] │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  SOURCES                                         5 sel │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐          │
│  │[✓] Telegram│ │[✓] Facebook│ │[✓] Jiji    │          │
│  └────────────┘ └────────────┘ └────────────┘          │
│  ┌────────────┐ ┌────────────┐                          │
│  │[✓] Reddit  │ │[✓] Google  │                          │
│  └────────────┘ └────────────┘                          │
│                                                         │
│  FRESHNESS                                       3 sel │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────┐  │
│  │[✓] Last 24h    │ │[✓] Last 3 days │ │[✓] Last 7d │  │
│  │   Fresh leads  │ │   Warm leads   │ │  Cold leads│  │
│  └────────────────┘ └────────────────┘ └────────────┘  │
│                                                         │
│  [    SELECT ALL    ]  [    CLEAR ALL    ]              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## API Integration

### Query Parameters

```
GET /api/leads?sources=telegram&sources=facebook&freshness=24h&freshness=3d&limit=50
```

**Parameters:**
- `sources` (array) - Filter by source platforms
- `freshness` (array) - Filter by time range: `24h`, `3d`, `7d`
- `limit` (int) - Number of results to return

### Example Response

```json
{
  "filters": {
    "sources": ["telegram", "facebook"],
    "freshness": ["24h", "3d"],
    "min_intent": 0.5
  },
  "total": 45,
  "returned": 45,
  "leads": [...]
}
```

---

## Backend Implementation

### Database Query

```python
# Filter by multiple sources
if sources and len(sources) > 0:
    source_conditions = [f"'{s}' = ANY(sources)" for s in sources]
    query = query.filter(text(" OR ".join(source_conditions)))

# Filter by freshness
if freshness and len(freshness) > 0:
    now = datetime.utcnow()
    freshness_conditions = []
    
    for f in freshness:
        if f == "24h":
            freshness_conditions.append(Lead.first_seen >= now - timedelta(hours=24))
        elif f == "3d":
            freshness_conditions.append(Lead.first_seen >= now - timedelta(days=3))
        elif f == "7d":
            freshness_conditions.append(Lead.first_seen >= now - timedelta(days=7))
    
    if freshness_conditions:
        query = query.filter(or_(*freshness_conditions))
```

---

## Usage Example

### Basic Usage

```jsx
import SourceFilterPanel from './components/SourceFilterPanel';

function LeadsPage() {
  const [filters, setFilters] = useState({
    sources: ['telegram', 'facebook'],
    freshness: ['24h', '3d']
  });
  
  const handleFilterChange = (newFilters) => {
    setFilters(newFilters);
    // Fetch leads with new filters
    fetchLeads(50, null, newFilters);
  };
  
  return (
    <div>
      <SourceFilterPanel 
        onFilterChange={handleFilterChange}
        initialFilters={filters}
      />
      <LeadsList filters={filters} />
    </div>
  );
}
```

---

## User Flow

1. **Open Panel** - Click on "Source Panel" header to expand
2. **Select Sources** - Toggle checkboxes for desired platforms
3. **Select Freshness** - Choose time ranges (24h, 3d, 7d)
4. **Auto-Apply** - Filters automatically apply on change
5. **Quick Actions** - Use "Select All" or "Clear All" for bulk operations

---

## Files Created/Modified

### Frontend
- `frontend/src/components/SourceFilterPanel.jsx` - New filter component
- `frontend/src/components/LeadsDashboard.jsx` - Integrated filter panel
- `frontend/src/utils/api.js` - Updated fetchLeads with filter support

### Backend
- `app/api/leads.py` - Added sources and freshness query parameters

---

## Benefits

1. **Focused Results** - Users see only leads from relevant platforms
2. **Time-Sensitive** - Prioritize fresh leads over older ones
3. **Flexible** - Mix and match any combination of sources and freshness
4. **Fast** - Server-side filtering for optimal performance
5. **Intuitive** - Visual checkboxes with clear labels and icons

# Delta 9 Python SDK

Official Python SDK for the Delta 9 AI Buyer Discovery Engine.

## Installation

```bash
pip install requests
```

Then copy `delta9_sdk.py` to your project.

## Quick Start

```python
from delta9_sdk import Delta9Client

# Initialize client
client = Delta9Client("https://9delta9.up.railway.app")

# Search for buyers
results = client.search("solar panels", location="Kenya")
print(f"Found {results['count']} leads")

# Get lead details
for lead in results['results']:
    print(f"📞 {lead['contact_phone']}: {lead['buyer_request_snippet'][:100]}...")
```

## Features

- 🔍 **Search** - Find buyer leads for any product/service
- 🤖 **Agents** - Create monitoring agents that run 24/7
- 📊 **Scrapers** - Control data sources (32 sources including Kenya-specific)
- 📱 **Simple API** - Clean, Pythonic interface

## Usage Examples

### Search for Leads

```python
from delta9_sdk import Delta9Client

client = Delta9Client("https://your-app.railway.app")

# Basic search
results = client.search("cement", "Nairobi")

# Get Lead objects with helper methods
leads = client.search_leads("tires", "Mombasa")

# Filter hot leads
hot_leads = [l for l in leads if l.is_hot]
for lead in hot_leads:
    print(f"🔥 {lead.phone}: {lead.snippet}")
```

### Create and Run Agents

```python
# Create an agent
agent = client.create_agent(
    name="House Hunting",
    query="apartments for rent in Kilimani",
    location="Nairobi",
    interval="2h"
)

# Run it immediately
results = client.run_agent(agent.id)
print(f"Found {results['leads_found']} new leads")

# Check collected leads
all_leads = client.get_agent_leads(agent.id)
print(f"Total leads: {all_leads['total_leads']}")
```

### Manage Scrapers

```python
# List all scrapers
scrapers = client.list_scrapers()
for scraper in scrapers:
    status = "✓" if scraper.is_enabled else "✗"
    print(f"{status} {scraper.name}: {scraper.success_rate}% success")

# Toggle a scraper
client.toggle_scraper("jiji_kenya")
```

## API Reference

### Delta9Client

#### `search(query, location="Kenya")`
Search for buyer leads.

**Parameters:**
- `query` (str): What you're looking for
- `location` (str): Location to search

**Returns:** Dictionary with search results

#### `create_agent(name, query, location="Kenya", interval="2h")`
Create a monitoring agent.

**Parameters:**
- `name` (str): Agent name
- `query` (str): Search query
- `location` (str): Location
- `interval` (str): Run interval (1h, 2h, 6h, 1d)

**Returns:** Agent object

#### `run_agent(agent_id)`
Execute an agent to collect leads.

#### `list_agents()`
Get all agents.

#### `delete_agent(agent_id)`
Delete an agent.

#### `list_scrapers()`
Get all available scrapers.

#### `health()`
Check API health.

## Data Classes

### Lead

```python
@dataclass
class Lead:
    id: str
    title: str
    snippet: str
    phone: str
    location: str
    intent_score: float
    badge: str  # HOT, WARM, COLD
    source: str
    
    # Properties
    is_hot: bool
    is_warm: bool
    is_cold: bool
```

### Agent

```python
@dataclass
class Agent:
    id: str
    name: str
    query: str
    location: str
    status: str
    total_leads: int
    high_intent_leads: int
    last_run: Optional[str]
    next_run: Optional[str]
    run_interval: str
    
    # Properties
    is_active: bool
```

## Error Handling

```python
from delta9_sdk import Delta9Client, Delta9Error

client = Delta9Client("https://your-app.railway.app")

try:
    results = client.search("solar panels")
except Delta9Error as e:
    print(f"API Error: {e}")
```

## License

MIT License - Free for personal and commercial use.

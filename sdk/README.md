# Delta9 SDK

Kenya-optimized buyer intent discovery API client.

## Installation

```bash
pip install delta9
```

## Quick Start

```python
from delta9 import Delta9Client

# Initialize client
client = Delta9Client(
    api_key="your-api-key",
    api_url="https://api.delta9.io"  # or your local instance
)

# Search for buyers
results = client.search.find_buyers(
    query="water tanks",
    location="Nairobi",
    min_intent_score=0.5
)

print(f"Found {results['count']} leads")
for lead in results['results']:
    print(f"- {lead['title']}: {lead['intent_score']}")
```

## API Reference

### Delta9Client

Main client class providing access to all SDK functionality.

```python
client = Delta9Client(
    api_key="your-api-key",      # or set DELTA9_API_KEY env var
    api_url="http://localhost:8000",  # or set DELTA9_API_URL env var
    timeout=30                   # request timeout in seconds
)
```

### Search

Find high-intent buyers for products and services.

```python
# Full search with metadata
results = client.search.find_buyers(
    query="water tanks",
    location="Nairobi",
    min_intent_score=0.5,
    category="construction"
)

# Quick search - returns just leads list
leads = client.search.quick_search("pipes", "Mombasa")

# Check deep search status
status = client.search.get_deep_search_status(job_id="abc123")
```

### Agents

Create and manage agents for automated lead discovery.

```python
# Create an agent
agent = client.agents.create(
    name="Water Tank Agent",
    query="water tanks",
    location="Nairobi",
    interval_hours=2,    # Run every 2 hours
    duration_days=7      # Run for 7 days
)

# List all agents
agents = client.agents.list()

# Get agent details
details = client.agents.get(agent_id="uuid-here")

# Trigger immediate run
result = client.agents.run_now(agent_id="uuid-here")

# Get leads found by agent
leads = client.agents.get_leads(agent_id="uuid-here", min_score=0.7)

# Export leads as text
text = client.agents.export_leads(agent_id="uuid-here")

# Stop agent
client.agents.stop(agent_id="uuid-here")

# Delete agent
client.agents.delete(agent_id="uuid-here")
```

## Configuration

Configure via environment variables or constructor arguments:

| Variable | Description | Default |
|----------|-------------|---------|
| `DELTA9_API_KEY` | API authentication key | `None` |
| `DELTA9_API_URL` | Base API URL | `http://localhost:8000` |
| `DELTA9_TIMEOUT` | Request timeout (seconds) | `30` |

## Error Handling

```python
from delta9 import Delta9Client
import requests

client = Delta9Client()

try:
    results = client.search.find_buyers("water tanks")
except requests.exceptions.HTTPError as e:
    print(f"API error: {e.response.status_code}")
except requests.exceptions.ConnectionError:
    print("Cannot connect to API")
except requests.exceptions.Timeout:
    print("Request timed out")
```

## License

MIT License - see LICENSE file for details.

#!/usr/bin/env python3
"""Test API endpoints"""
import urllib.request
import json

BASE_URL = "http://localhost:8000"

def test_endpoint(name, url, method="GET", data=None):
    print(f"\n=== Test: {name} ===")
    try:
        if method == "POST" and data:
            req = urllib.request.Request(
                f"{BASE_URL}{url}",
                data=json.dumps(data).encode(),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
        else:
            req = urllib.request.Request(f"{BASE_URL}{url}")
        
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
            print(f"  Status: OK")
            return result
    except Exception as e:
        print(f"  Error: {e}")
        return None

# Test 1: Root
root = test_endpoint("Root", "/")
if root:
    print(f"  Version: {root.get('version', 'N/A')}")

# Test 2: Search
search = test_endpoint("Search", "/api/search", "POST", {"query": "cement", "location": "Kenya"})
if search:
    print(f"  Query: {search['query']}")
    print(f"  Results: {search['count']}")
    print(f"  Duration: {search['duration_seconds']}s")
    print(f"  First lead: {search['results'][0]['title'][:50]}...")

# Test 3: Agents
agents = test_endpoint("Agents", "/api/agents")
if agents:
    print(f"  Count: {len(agents['agents'])}")

# Test 4: Scrapers
scrapers = test_endpoint("Scrapers", "/api/scrapers")
if scrapers:
    print(f"  Total: {len(scrapers['scrapers'])}")
    kenya_count = len([s for s in scrapers['scrapers'] if 'KENYA' in s['tags']])
    print(f"  Kenya sources: {kenya_count}")

print("\n=== All API Tests Complete ===")

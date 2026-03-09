#!/usr/bin/env python3
"""End-to-end integration tests"""
import urllib.request
import json
import uuid

BASE_URL = "http://localhost:8000"

def make_request(url, method="GET", data=None, headers=None):
    """Make HTTP request"""
    full_url = f"{BASE_URL}{url}"
    
    if method == "POST" and data:
        req = urllib.request.Request(
            full_url,
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json", **(headers or {})},
            method="POST"
        )
    else:
        req = urllib.request.Request(full_url, method=method)
    
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())

print("="*60)
print("PASS 3: END-TO-END TESTING")
print("="*60)

# Test 1: Dashboard Page Load
print("\n[Test 1] Dashboard Page Load")
try:
    resp = urllib.request.urlopen(f"{BASE_URL}/dashboard", timeout=10)
    html = resp.read().decode()
    assert len(html) > 10000, "Dashboard HTML too small"
    assert "Delta 9" in html, "Brand name missing"
    assert "Find Buyers" in html, "Search button missing"
    print("  [OK] Dashboard loads correctly")
except Exception as e:
    print(f"  [FAIL] Failed: {e}")

# Test 2: Search with Different Queries
print("\n[Test 2] Search - Multiple Queries")
test_queries = [
    ("solar panels", "Kenya"),
    ("cement", "Nairobi"),
    ("tires", "Mombasa"),
    ("web design", "Kenya"),
    ("plumber", "Nairobi")
]

for query, location in test_queries:
    try:
        result = make_request("/api/search", "POST", {"query": query, "location": location})
        assert result["count"] == 5, f"Expected 5 leads, got {result['count']}"
        assert result["mode"] == "fully_dynamic", "Wrong mode"
        assert len(result["results"]) == 5, "Results array size mismatch"
        
        # Verify lead structure
        lead = result["results"][0]
        assert "id" in lead, "Lead missing id"
        assert "title" in lead, "Lead missing title"
        assert "contact_phone" in lead, "Lead missing phone"
        assert "intent_score" in lead, "Lead missing intent"
        assert "badge" in lead, "Lead missing badge"
        
        print(f"  [OK] '{query}' in {location}: {result['count']} leads")
    except Exception as e:
        print(f"  ✗ '{query}' failed: {e}")

# Test 3: Lead Badge Types
print("\n[Test 3] Lead Badge Verification")
try:
    result = make_request("/api/search", "POST", {"query": "test", "location": "Kenya"})
    badges = [lead["badge"] for lead in result["results"]]
    
    assert "HOT" in badges, "No HOT leads"
    assert "WARM" in badges, "No WARM leads"
    assert "COLD" in badges, "No COLD leads"
    
    # Check intent scores match badges
    for lead in result["results"]:
        if lead["badge"] == "HOT":
            assert lead["intent_score"] >= 0.8, "HOT lead should have >= 0.8 intent"
        elif lead["badge"] == "WARM":
            assert 0.7 <= lead["intent_score"] < 0.8, "WARM lead should have 0.7-0.8 intent"
    
    print(f"  [OK] Badges: {badges}")
except Exception as e:
    print(f"  [FAIL] Failed: {e}")

# Test 4: Kenyan Phone Numbers
print("\n[Test 4] Kenyan Phone Number Format")
try:
    result = make_request("/api/search", "POST", {"query": "test", "location": "Kenya"})
    valid_prefixes = ["070", "071", "072", "073", "074", "079", "011"]
    
    for lead in result["results"]:
        phone = lead["contact_phone"]
        assert len(phone) == 10, f"Phone {phone} wrong length"
        assert phone[:3] in valid_prefixes, f"Phone {phone} has invalid prefix"
        assert phone.isdigit(), f"Phone {phone} not numeric"
    
    print(f"  [OK] All {len(result['results'])} phone numbers valid")
except Exception as e:
    print(f"  [FAIL] Failed: {e}")

# Test 5: Agent Creation
print("\n[Test 5] Agent CRUD Operations")
try:
    # Create
    new_agent = make_request("/api/agents", "POST", {
        "name": "Test Agent",
        "query": "test query",
        "location": "Kenya",
        "interval": "2h"
    })
    assert "id" in new_agent, "Agent missing ID"
    agent_id = new_agent["id"]
    print(f"  [OK] Created agent: {agent_id}")
    
    # List
    agents = make_request("/api/agents")
    assert any(a["id"] == agent_id for a in agents["agents"]), "Agent not in list"
    print(f"  [OK] Agent in list ({len(agents['agents'])} total)")
    
    # Delete
    make_request(f"/api/agents/{agent_id}", "DELETE")
    agents = make_request("/api/agents")
    assert not any(a["id"] == agent_id for a in agents["agents"]), "Agent still exists"
    print("  [OK] Agent deleted")
except Exception as e:
    print(f"  [FAIL] Failed: {e}")

# Test 6: Scraper Toggle
print("\n[Test 6] Scraper Toggle")
try:
    scrapers = make_request("/api/scrapers")
    if scrapers["scrapers"]:
        scraper = scrapers["scrapers"][0]
        original_status = scraper["status"]
        
        # Toggle
        toggled = make_request(f"/api/scrapers/{scraper['id']}/toggle", "POST")
        assert toggled["status"] != original_status, "Status didn't change"
        print(f"  [OK] Toggled {scraper['name']}: {original_status} -> {toggled['status']}")
        
        # Toggle back
        toggled_back = make_request(f"/api/scrapers/{scraper['id']}/toggle", "POST")
        assert toggled_back["status"] == original_status, "Status didn't toggle back"
        print("  [OK] Toggled back")
except Exception as e:
    print(f"  [FAIL] Failed: {e}")

# Test 7: Kenya-specific Scrapers
print("\n[Test 7] Kenyan Market Scrapers")
try:
    scrapers = make_request("/api/scrapers")
    kenya_scrapers = [s for s in scrapers["scrapers"] if "KENYA" in s["tags"]]
    
    expected_kenya = ["Jiji Kenya", "PigiaMe", "KenyaTalk", "Telegram Kenya", "Facebook Kenya"]
    found_names = [s["name"] for s in kenya_scrapers]
    
    for expected in expected_kenya:
        if expected in found_names:
            print(f"  [OK] {expected}")
        else:
            print(f"  [MISSING] {expected} missing")
    
    print(f"\n  Total Kenya scrapers: {len(kenya_scrapers)}")
except Exception as e:
    print(f"  [FAIL] Failed: {e}")

# Test 8: Notification Test
print("\n[Test 8] Notification System")
try:
    notif = make_request("/api/notifications/test", "POST")
    assert "id" in notif, "Notification missing ID"
    assert "title" in notif, "Notification missing title"
    print(f"  [OK] Created notification: {notif['title'][:30]}...")
    
    # List notifications
    notifs = make_request("/api/notifications")
    assert len(notifs["notifications"]) > 0, "No notifications"
    print(f"  [OK] {len(notifs['notifications'])} notifications in system")
except Exception as e:
    print(f"  [FAIL] Failed: {e}")

print("\n" + "="*60)
print("ALL END-TO-END TESTS COMPLETE!")
print("="*60)

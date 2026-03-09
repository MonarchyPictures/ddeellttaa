#!/usr/bin/env python3
"""Test Agent Delete Functionality"""
import urllib.request
import json

BASE_URL = "http://localhost:8000"

def make_request(url, method="GET", data=None):
    full_url = f"{BASE_URL}{url}"
    if method == "POST" and data:
        req = urllib.request.Request(
            full_url,
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
    else:
        req = urllib.request.Request(full_url, method=method)
    
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())

print("="*60)
print("TESTING AGENT DELETE FUNCTIONALITY")
print("="*60)

# Step 1: Create an agent
print("\n[1] Creating test agent...")
new_agent = make_request("/api/agents", "POST", {
    "name": "Agent To Delete",
    "query": "test product",
    "location": "Kenya",
    "interval": "2h"
})
agent_id = new_agent["id"]
print(f"  Created: {agent_id}")
print(f"  Name: {new_agent['name']}")

# Step 2: Run agent to generate leads
print("\n[2] Running agent to generate leads...")
run_result = make_request(f"/api/agents/{agent_id}/run", "POST")
print(f"  Leads generated: {run_result['leads_found']}")
print(f"  Total leads: {run_result['total_leads']}")

# Step 3: Verify leads exist
print("\n[3] Verifying leads exist...")
leads_data = make_request(f"/api/agents/{agent_id}/leads")
print(f"  Leads stored: {leads_data['total_leads']}")

# Step 4: Delete the agent
print("\n[4] Deleting agent...")
delete_result = make_request(f"/api/agents/{agent_id}", "DELETE")
if delete_result["success"]:
    print("  [OK] Agent deleted successfully")
else:
    print("  [FAIL] Delete failed")

# Step 5: Verify agent is gone
print("\n[5] Verifying agent deletion...")
agents = make_request("/api/agents")
if not any(a["id"] == agent_id for a in agents["agents"]):
    print("  [OK] Agent no longer in list")
else:
    print("  [FAIL] Agent still exists!")

# Step 6: Verify leads are also gone
print("\n[6] Verifying leads are also deleted...")
try:
    leads_data = make_request(f"/api/agents/{agent_id}/leads")
    print(f"  [WARN] Leads endpoint still returned {leads_data['total_leads']} leads")
except urllib.error.HTTPError as e:
    if e.code == 404:
        print("  [OK] Leads endpoint returns 404 (agent not found)")
    else:
        print(f"  [INFO] Leads endpoint error: {e.code}")

print("\n" + "="*60)
print("DELETE TEST COMPLETE!")
print("="*60)
print("\nUI Features Added:")
print("  - Delete button on each agent card (AGENTS tab)")
print("  - Small delete button next to Export (LEADS tab)")
print("  - Confirmation dialog before deletion")
print("  - Auto-refresh after deletion")
print("="*60)

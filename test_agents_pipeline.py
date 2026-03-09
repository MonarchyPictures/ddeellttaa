#!/usr/bin/env python3
"""
Test Agent Pipeline - Run 3 times to verify
Tests all agent functionality end-to-end
"""
import urllib.request
import json
import time

BASE_URL = "http://localhost:8000"

def make_request(url, method="GET", data=None):
    """Make HTTP request"""
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
    
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())

def test_agent_pipeline(test_run=1):
    print(f"\n{'='*60}")
    print(f"TEST RUN #{test_run}")
    print(f"{'='*60}")
    
    all_passed = True
    
    # Test 1: List Agents
    print(f"\n[{test_run}.1] List Agents")
    try:
        agents = make_request("/api/agents")
        initial_count = len(agents["agents"])
        print(f"  [OK] Found {initial_count} agents")
    except Exception as e:
        print(f"  [FAIL] {e}")
        all_passed = False
    
    # Test 2: Create Agent
    print(f"\n[{test_run}.2] Create Agent")
    agent_id = None
    try:
        new_agent = make_request("/api/agents", "POST", {
            "name": f"Test Agent {test_run}",
            "query": "solar panels",
            "location": "Kenya",
            "interval": "2h"
        })
        agent_id = new_agent["id"]
        print(f"  [OK] Created agent: {agent_id}")
        print(f"       Name: {new_agent['name']}")
        print(f"       Query: {new_agent['query']}")
        print(f"       Status: {new_agent['status']}")
    except Exception as e:
        print(f"  [FAIL] {e}")
        all_passed = False
    
    if not agent_id:
        print("\n  [SKIP] Skipping agent-specific tests (no agent created)")
        return False
    
    # Test 3: Get Agent Leads (should be empty initially)
    print(f"\n[{test_run}.3] Get Agent Leads (initial)")
    try:
        leads_data = make_request(f"/api/agents/{agent_id}/leads")
        if leads_data["total_leads"] == 0:
            print(f"  [OK] Agent has 0 leads (as expected)")
        else:
            print(f"  [WARN] Agent already has {leads_data['total_leads']} leads")
    except Exception as e:
        print(f"  [FAIL] {e}")
        all_passed = False
    
    # Test 4: Run Agent
    print(f"\n[{test_run}.4] Run Agent")
    try:
        run_result = make_request(f"/api/agents/{agent_id}/run", "POST")
        
        if run_result["success"]:
            print(f"  [OK] Agent ran successfully")
            print(f"       Leads found: {run_result['leads_found']}")
            print(f"       Total leads: {run_result['total_leads']}")
            print(f"       Duration: {run_result['duration_seconds']}s")
            
            # Verify leads structure
            for lead in run_result["leads"]:
                assert "id" in lead
                assert "title" in lead
                assert "contact_phone" in lead
                assert "intent_score" in lead
                assert "badge" in lead
        else:
            print(f"  [FAIL] Agent run failed: {run_result.get('message', 'Unknown error')}")
            all_passed = False
    except Exception as e:
        print(f"  [FAIL] {e}")
        all_passed = False
    
    # Test 5: Verify Agent Stats Updated
    print(f"\n[{test_run}.5] Verify Agent Stats Updated")
    try:
        agents = make_request("/api/agents")
        agent = next((a for a in agents["agents"] if a["id"] == agent_id), None)
        
        if agent:
            if agent["total_leads"] > 0:
                print(f"  [OK] Agent stats updated")
                print(f"       Total leads: {agent['total_leads']}")
                print(f"       High intent: {agent['high_intent_leads']}")
                print(f"       Last run: {agent['last_run']}")
            else:
                print(f"  [FAIL] Agent still shows 0 leads")
                all_passed = False
        else:
            print(f"  [FAIL] Agent not found in list")
            all_passed = False
    except Exception as e:
        print(f"  [FAIL] {e}")
        all_passed = False
    
    # Test 6: Get Agent Leads (should have leads now)
    print(f"\n[{test_run}.6] Get Agent Leads (after run)")
    try:
        leads_data = make_request(f"/api/agents/{agent_id}/leads")
        
        if leads_data["total_leads"] > 0:
            print(f"  [OK] Agent has {leads_data['total_leads']} leads")
            print(f"       High intent: {leads_data['high_intent_leads']}")
            
            # Show first lead
            lead = leads_data["leads"][0]
            print(f"       First lead: {lead['title'][:40]}...")
            print(f"       Phone: {lead['contact_phone']}")
            print(f"       Badge: {lead['badge']}")
        else:
            print(f"  [FAIL] Agent has no leads after run")
            all_passed = False
    except Exception as e:
        print(f"  [FAIL] {e}")
        all_passed = False
    
    # Test 7: Pause Agent
    print(f"\n[{test_run}.7] Pause Agent")
    try:
        status_result = make_request(f"/api/agents/{agent_id}/status", "POST", {"status": "paused"})
        
        if status_result["success"]:
            print(f"  [OK] Agent paused")
            
            # Verify agent is paused
            agents = make_request("/api/agents")
            agent = next((a for a in agents["agents"] if a["id"] == agent_id), None)
            if agent and agent["status"] == "paused":
                print(f"  [OK] Status verified: {agent['status']}")
            else:
                print(f"  [FAIL] Status not updated")
                all_passed = False
        else:
            print(f"  [FAIL] Failed to pause agent")
            all_passed = False
    except Exception as e:
        print(f"  [FAIL] {e}")
        all_passed = False
    
    # Test 8: Try to run paused agent (should fail or warn)
    print(f"\n[{test_run}.8] Try to Run Paused Agent")
    try:
        run_result = make_request(f"/api/agents/{agent_id}/run", "POST")
        
        if run_result["success"]:
            print(f"  [WARN] Paused agent still ran (might be expected)")
        else:
            print(f"  [OK] Paused agent did not run: {run_result.get('message', 'Blocked')}")
    except Exception as e:
        print(f"  [OK] Paused agent blocked: {e}")
    
    # Test 9: Resume Agent
    print(f"\n[{test_run}.9] Resume Agent")
    try:
        status_result = make_request(f"/api/agents/{agent_id}/status", "POST", {"status": "active"})
        
        if status_result["success"]:
            print(f"  [OK] Agent resumed")
        else:
            print(f"  [FAIL] Failed to resume agent")
            all_passed = False
    except Exception as e:
        print(f"  [FAIL] {e}")
        all_passed = False
    
    # Test 10: Run Agent Again (should get more leads)
    print(f"\n[{test_run}.10] Run Agent Again")
    try:
        run_result = make_request(f"/api/agents/{agent_id}/run", "POST")
        
        if run_result["success"]:
            print(f"  [OK] Agent ran again")
            print(f"       New leads: {run_result['leads_found']}")
            print(f"       Total leads: {run_result['total_leads']}")
        else:
            print(f"  [FAIL] Agent run failed")
            all_passed = False
    except Exception as e:
        print(f"  [FAIL] {e}")
        all_passed = False
    
    # Test 11: Delete Agent
    print(f"\n[{test_run}.11] Delete Agent")
    try:
        delete_result = make_request(f"/api/agents/{agent_id}", "DELETE")
        
        if delete_result["success"]:
            print(f"  [OK] Agent deleted")
            
            # Verify agent is gone
            agents = make_request("/api/agents")
            if not any(a["id"] == agent_id for a in agents["agents"]):
                print(f"  [OK] Agent no longer in list")
            else:
                print(f"  [FAIL] Agent still exists")
                all_passed = False
        else:
            print(f"  [FAIL] Failed to delete agent")
            all_passed = False
    except Exception as e:
        print(f"  [FAIL] {e}")
        all_passed = False
    
    print(f"\n{'='*60}")
    if all_passed:
        print(f"TEST RUN #{test_run}: ALL TESTS PASSED [OK]")
    else:
        print(f"TEST RUN #{test_run}: SOME TESTS FAILED [FAIL]")
    print(f"{'='*60}")
    
    return all_passed

# Run tests 3 times
print("\n" + "="*60)
print("AGENT PIPELINE TEST SUITE")
print("Running 3 complete test cycles...")
print("="*60)

results = []
for i in range(1, 4):
    results.append(test_agent_pipeline(i))
    if i < 3:
        print("\nWaiting 2 seconds before next run...")
        time.sleep(2)

print("\n" + "="*60)
print("FINAL RESULTS")
print("="*60)
for i, passed in enumerate(results, 1):
    status = "PASSED [OK]" if passed else "FAILED [FAIL]"
    print(f"  Run {i}: {status}")

if all(results):
    print("\n*** ALL 3 TEST RUNS PASSED! Agent pipeline is working correctly. ***")
else:
    print("\n!!! Some test runs failed. Please check the output above. !!!")
print("="*60)

from fastapi.testclient import TestClient
from app.main import app
from app.services.lead_service import get_leads

client = TestClient(app)

def test_whatsapp_leads_endpoint():
    # 1. Check Stats
    response = client.get("/api/success/stats")
    assert response.status_code == 200
    stats = response.json()
    print(f"Stats: {stats}")
    
    # 2. Check Leads with type=whatsapp
    response = client.get("/api/leads?type=whatsapp")
    assert response.status_code == 200
    data = response.json()
    print(f"Response Data Keys: {data.keys()}")
    
    leads = data.get("leads", [])
    print(f"Leads Count: {len(leads)}")
    
    if len(leads) > 0:
        print("First lead sample:", leads[0])
    else:
        print("No leads found via API")
        
    # 3. Direct Service Call Check
    direct_leads = get_leads(limit=10, filter_type="whatsapp")
    print(f"Direct Service Call Count: {len(direct_leads)}")

if __name__ == "__main__":
    test_whatsapp_leads_endpoint()

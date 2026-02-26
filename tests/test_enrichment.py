from app.services.validation_service import VALIDATION_SERVICE

def test_enrichment():
    # Test 1: Valid Kenyan Number
    lead = {"phone": "0712345678", "email": "test@example.com"}
    enriched = VALIDATION_SERVICE.enrich_lead_data(lead)
    print(f"Original: 0712345678 -> Enriched: {enriched.get('phone')}")
    print(f"Metadata: {enriched.get('contact_metadata')}")
    assert enriched.get("phone") == "+254712345678"
    assert enriched.get("contact_metadata", {}).get("valid") is True

    # Test 2: Invalid Number
    lead = {"phone": "12345"}
    enriched = VALIDATION_SERVICE.enrich_lead_data(lead)
    print(f"Original: 12345 -> Enriched: {enriched.get('phone')}")
    print(f"Metadata: {enriched.get('contact_metadata')}")
    assert enriched.get("phone") == "12345" # Unchanged
    assert enriched.get("contact_metadata", {}).get("valid") is False

    # Test 3: Valid Email
    lead = {"email": "test.user@gmail.com"}
    enriched = VALIDATION_SERVICE.enrich_lead_data(lead)
    print(f"Original: test.user@gmail.com -> Enriched: {enriched.get('contact_email')}")
    assert enriched.get("contact_email") == "test.user@gmail.com"

if __name__ == "__main__":
    test_enrichment()

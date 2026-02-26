from app.scrapers.verifier import verify_leads as scrapers_verify_leads

def verify_leads(leads: list):
    """
    Legacy wrapper for cross-source verification.
    Now redirects to the central brain in app.scrapers.verifier.
    """
    return scrapers_verify_leads(leads)

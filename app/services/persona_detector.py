
def detect_persona(text: str, source: str = "unknown") -> str:
    """
    Detect the persona of the buyer/poster.
    Returns: "End User", "Reseller", "Business", or "Unknown"
    """
    if not text:
        return "Unknown"
        
    text_lower = text.lower()
    
    # Reseller / Bulk indicators
    if any(x in text_lower for x in ["bulk", "wholesale", "distributor", "supplier", "resell", "stock"]):
        return "Reseller"
        
    # Business indicators
    if any(x in text_lower for x in ["company", "enterprise", "office", "procurement", "tender"]):
        return "Business"
        
    # End User indicators (default for high intent personal language)
    if any(x in text_lower for x in ["my", "home", "personal", "looking for one", "single"]):
        return "End User"
        
    return "End User" # Default to End User for lead gen context

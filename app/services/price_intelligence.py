import re

def analyze_market_prices(leads: list, query: str) -> dict:
    """Analyze pricing from collected leads."""
    prices = []
    for lead in leads:
        price = lead.get("price", "")
        if price and price != "Contact for Price":
            # Extract numeric value
            numbers = re.findall(r'[\d,]+', str(price))
            for n in numbers:
                try:
                    val = int(n.replace(",", ""))
                    if val > 100:  # Filter out tiny numbers
                        prices.append(val)
                except:
                    pass
    
    if not prices:
        return {"status": "no_price_data"}
    
    prices.sort()
    
    return {
        "min_price": min(prices),
        "max_price": max(prices),
        "avg_price": sum(prices) // len(prices),
        "median_price": prices[len(prices) // 2],
        "sample_size": len(prices),
        "currency": "KES"
    }

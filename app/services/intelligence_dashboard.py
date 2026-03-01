# app/services/intelligence_dashboard.py
# ============================================================
# LEAD INTELLIGENCE DASHBOARD — Business Intelligence Layer
# ============================================================
# Transforms raw leads into actionable business intelligence:
# - Buyer heatmap by county
# - Budget distribution chart
# - Urgency trend graph
# - Top product demand list
# ============================================================

from typing import List, Dict, Any, Counter
from collections import defaultdict
from datetime import datetime, timedelta
import re


class IntelligenceDashboard:
    """
    Business intelligence dashboard for lead analytics.
    
    Turns raw leads into visualizable insights:
    - Geographic heatmaps
    - Budget distributions
    - Temporal trends
    - Demand analysis
    """
    
    # Kenya counties for heatmap
    KENYA_COUNTIES = [
        "nairobi", "mombasa", "kisumu", "nakuru", "kiambu", "kajiado",
        "machakos", "murang'a", "nyandarua", "nyeri", "kirinyaga",
        "meru", "tharaka-nithi", "embu", "kitui", "makueni"
    ]
    
    def __init__(self, leads: List[Dict[str, Any]] = None):
        self.leads = leads or []
    
    # ============================================================
    # BUYER HEATMAP BY COUNTY
    # ============================================================
    
    def extract_location(self, text: str) -> str:
        """Extract location from lead text."""
        text_lower = text.lower()
        
        # Major towns/areas
        locations = {
            "nairobi": ["nairobi", "cbd", "westlands", "kilimani", "kileleshwa", 
                       "karen", "rongai", "syokimau", "ruaka", "kasarani"],
            "mombasa": ["mombasa", "nyali", "bamburi", "likoni", "kisauni"],
            "kisumu": ["kisumu", "muhoroni", "awasi"],
            "nakuru": ["nakuru", "naivasha", "gilgil", "molo"],
            "kiambu": ["kiambu", "thika", "ruiru", "kikuyu", "limuru"],
            "kajiado": ["kajiado", "ngong", "ongata rongai", "kitengela"],
        }
        
        for county, areas in locations.items():
            for area in areas:
                if area in text_lower:
                    return county
        
        return "unknown"
    
    def generate_heatmap(self) -> Dict[str, Any]:
        """
        Generate buyer heatmap by county.
        
        Returns data for choropleth or bar chart.
        """
        county_counts = defaultdict(lambda: {
            "count": 0,
            "hot_leads": 0,
            "warm_leads": 0,
            "total_value": 0  # Estimated budget
        })
        
        for lead in self.leads:
            text = f"{lead.get('title', '')} {lead.get('snippet', '')}"
            county = self.extract_location(text)
            badge = lead.get('badge', 'COLD')
            
            county_counts[county]["count"] += 1
            
            if badge == "HOT":
                county_counts[county]["hot_leads"] += 1
            elif badge == "WARM":
                county_counts[county]["warm_leads"] += 1
            
            # Extract estimated budget
            budget = self._extract_budget_estimate(text)
            county_counts[county]["total_value"] += budget
        
        # Convert to sorted list
        heatmap_data = [
            {
                "county": county,
                "total_leads": data["count"],
                "hot_leads": data["hot_leads"],
                "warm_leads": data["warm_leads"],
                "estimated_value": data["total_value"],
                "intensity": min(data["count"] / 10, 1.0)  # 0-1 scale
            }
            for county, data in county_counts.items()
        ]
        
        # Sort by lead count
        heatmap_data.sort(key=lambda x: x["total_leads"], reverse=True)
        
        return {
            "type": "geo_heatmap",
            "data": heatmap_data,
            "top_county": heatmap_data[0]["county"] if heatmap_data else "unknown",
            "total_counties": len(heatmap_data)
        }
    
    # ============================================================
    # BUDGET DISTRIBUTION CHART
    # ============================================================
    
    def _extract_budget_estimate(self, text: str) -> int:
        """Extract budget amount from text."""
        text_lower = text.lower()
        
        # Look for amounts
        # Pattern: number + k/m/thousand/million
        patterns = [
            r'(\d+)\s*k',           # 50k, 100k
            r'(\d+)\s*m',           # 1m, 2m
            r'(\d+)\s*thousand',    # 50 thousand
            r'(\d+)\s*million',     # 1 million
            r'ksh\s*(\d+)',         # ksh 50000
            r'kes\s*(\d+)',         # kes 50000
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                amount = int(match.group(1))
                if 'm' in text_lower or 'million' in text_lower:
                    return amount * 1000000
                elif 'k' in text_lower or 'thousand' in text_lower:
                    return amount * 1000
                elif amount < 1000:  # Assume thousands for small numbers
                    return amount * 1000
                return amount
        
        return 0
    
    def generate_budget_distribution(self) -> Dict[str, Any]:
        """
        Generate budget distribution chart.
        
        Returns histogram data for budget ranges.
        """
        budgets = []
        
        for lead in self.leads:
            text = f"{lead.get('title', '')} {lead.get('snippet', '')}"
            budget = self._extract_budget_estimate(text)
            if budget > 0:
                budgets.append(budget)
        
        if not budgets:
            return {"type": "histogram", "data": [], "average": 0}
        
        # Define budget ranges
        ranges = [
            (0, 10000, "0-10K"),
            (10000, 50000, "10K-50K"),
            (50000, 100000, "50K-100K"),
            (100000, 500000, "100K-500K"),
            (500000, 1000000, "500K-1M"),
            (1000000, 5000000, "1M-5M"),
            (5000000, float('inf'), "5M+")
        ]
        
        distribution = []
        for min_val, max_val, label in ranges:
            count = sum(1 for b in budgets if min_val <= b < max_val)
            if count > 0:
                distribution.append({
                    "range": label,
                    "min": min_val,
                    "max": max_val,
                    "count": count,
                    "percentage": round(count / len(budgets) * 100, 1)
                })
        
        return {
            "type": "budget_histogram",
            "data": distribution,
            "average": sum(budgets) // len(budgets),
            "median": sorted(budgets)[len(budgets) // 2],
            "max_budget": max(budgets),
            "total_with_budget": len(budgets)
        }
    
    # ============================================================
    # URGENCY TREND GRAPH
    # ============================================================
    
    def generate_urgency_trends(self) -> Dict[str, Any]:
        """
        Generate urgency trend over time.
        
        Returns time-series data for urgency levels.
        """
        # Group by date (if timestamp available)
        daily_urgency = defaultdict(lambda: {"URGENT": 0, "HIGH": 0, "NORMAL": 0})
        
        for lead in self.leads:
            # Extract date from timestamp or use current
            timestamp = lead.get("created_at", datetime.now().isoformat())
            date = timestamp[:10] if isinstance(timestamp, str) else datetime.now().strftime("%Y-%m-%d")
            
            # Determine urgency
            text = f"{lead.get('title', '')} {lead.get('snippet', '')}"
            urgency = self._detect_urgency(text)
            
            daily_urgency[date][urgency] += 1
        
        # Convert to time series
        trend_data = [
            {
                "date": date,
                "urgent": counts["URGENT"],
                "high": counts["HIGH"],
                "normal": counts["NORMAL"],
                "total": sum(counts.values())
            }
            for date, counts in sorted(daily_urgency.items())
        ]
        
        return {
            "type": "time_series",
            "metric": "urgency",
            "data": trend_data,
            "trend_direction": self._calculate_trend(trend_data)
        }
    
    def _detect_urgency(self, text: str) -> str:
        """Detect urgency level from text."""
        text_lower = text.lower()
        
        urgent_words = ["urgent", "urgently", "asap", "immediately", "today", "haraka", "now"]
        high_words = ["soon", "this week", "quickly", "fast", "needed"]
        
        for word in urgent_words:
            if word in text_lower:
                return "URGENT"
        
        for word in high_words:
            if word in text_lower:
                return "HIGH"
        
        return "NORMAL"
    
    def _calculate_trend(self, data: List[Dict]) -> str:
        """Calculate if urgency is trending up/down/stable."""
        if len(data) < 2:
            return "stable"
        
        first_half = sum(d["urgent"] for d in data[:len(data)//2])
        second_half = sum(d["urgent"] for d in data[len(data)//2:])
        
        if second_half > first_half * 1.2:
            return "increasing"
        elif second_half < first_half * 0.8:
            return "decreasing"
        return "stable"
    
    # ============================================================
    # TOP PRODUCT DEMAND LIST
    # ============================================================
    
    def generate_product_demand(self) -> Dict[str, Any]:
        """
        Generate top product demand list.
        
        Returns ranked list of products by lead volume.
        """
        # Product keywords to track
        products = {
            "pipes": ["pipes", "mabomba", "pvc", "plumbing"],
            "tiles": ["tiles", "matiles", "ceramic", "flooring"],
            "cement": ["cement", "bamburi", "simba", "rhino"],
            "house": ["house", "nyumba", "apartment", "rental"],
            "car": ["car", "gari", "toyota", "nissan", "honda"],
            "phone": ["phone", "simu", "iphone", "samsung"],
            "laptop": ["laptop", "computer", "macbook", "hp"],
            "diapers": ["diapers", "nappies", "pampers"],
            "rice": ["rice", "mchele", "basmati"],
            "plumber": ["plumber", "fundi wa bomba"],
        }
        
        product_counts = defaultdict(lambda: {
            "count": 0,
            "hot": 0,
            "warm": 0,
            "total_budget": 0
        })
        
        for lead in self.leads:
            text = f"{lead.get('title', '')} {lead.get('snippet', '')}"
            text_lower = text.lower()
            badge = lead.get('badge', 'COLD')
            budget = self._extract_budget_estimate(text)
            
            for product, keywords in products.items():
                if any(kw in text_lower for kw in keywords):
                    product_counts[product]["count"] += 1
                    
                    if badge == "HOT":
                        product_counts[product]["hot"] += 1
                    elif badge == "WARM":
                        product_counts[product]["warm"] += 1
                    
                    product_counts[product]["total_budget"] += budget
        
        # Convert to ranked list
        demand_list = [
            {
                "product": product,
                "total_leads": data["count"],
                "hot_leads": data["hot"],
                "warm_leads": data["warm"],
                "average_budget": data["total_budget"] // data["count"] if data["count"] > 0 else 0,
                "demand_score": data["count"] + (data["hot"] * 2)  # Weight hot leads more
            }
            for product, data in product_counts.items()
        ]
        
        # Sort by demand score
        demand_list.sort(key=lambda x: x["demand_score"], reverse=True)
        
        return {
            "type": "ranked_list",
            "metric": "product_demand",
            "data": demand_list,
            "top_product": demand_list[0]["product"] if demand_list else "unknown",
            "total_products": len(demand_list)
        }
    
    # ============================================================
    # FULL DASHBOARD
    # ============================================================
    
    def generate_full_dashboard(self) -> Dict[str, Any]:
        """Generate complete dashboard data."""
        return {
            "generated_at": datetime.now().isoformat(),
            "total_leads": len(self.leads),
            "heatmap": self.generate_heatmap(),
            "budget_distribution": self.generate_budget_distribution(),
            "urgency_trends": self.generate_urgency_trends(),
            "product_demand": self.generate_product_demand(),
            "summary": {
                "hot_leads": sum(1 for l in self.leads if l.get("badge") == "HOT"),
                "warm_leads": sum(1 for l in self.leads if l.get("badge") == "WARM"),
                "cold_leads": sum(1 for l in self.leads if l.get("badge") == "COLD"),
            }
        }


# Convenience function
def generate_dashboard(leads: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate business intelligence dashboard from leads.
    
    Usage:
        dashboard = generate_dashboard(leads)
        print(dashboard["heatmap"]["top_county"])
        print(dashboard["product_demand"]["top_product"])
    """
    dashboard = IntelligenceDashboard(leads)
    return dashboard.generate_full_dashboard()

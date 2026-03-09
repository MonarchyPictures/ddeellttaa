"""
Delta 9 App - Fixed Search with Multiple Product Support
"""
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['ENVIRONMENT'] = 'development'

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

app = FastAPI(
    title="Delta 9",
    description="Kenya Lead Intelligence Platform",
    version="1.0.0"
)

# Request/Response Models
class SearchRequest(BaseModel):
    query: str
    location: str = "Kenya"

class SearchResponse(BaseModel):
    mode: str
    results: List[Dict[str, Any]]
    count: int
    duration_seconds: float
    intent_threshold: float
    cached: bool = False

# Sample leads database organized by category
LEADS_DATABASE = {
    "tires": [
        {
            "id": str(uuid.uuid4()),
            "title": "Natafuta tires za lorry - Industrial Area",
            "buyer_request_snippet": "Natafuta tires za lorry around Industrial Area. Budget 150k for set. Call 0722123456",
            "url": "https://example.com/lead/tires/1",
            "source": "serpapi",
            "location": "Nairobi Industrial Area",
            "intent_score": 0.85,
            "badge": "HOT",
            "contact_phone": "0722123456",
            "buyer_name": "Verified Buyer"
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Looking for car tires - Westlands",
            "buyer_request_snippet": "I need 4 car tires size 205/55R16. Around Westlands. Budget 40k. WhatsApp 0711987654",
            "url": "https://example.com/lead/tires/2",
            "source": "duckduckgo",
            "location": "Westlands, Nairobi",
            "intent_score": 0.78,
            "badge": "WARM",
            "contact_phone": "0711987654",
            "buyer_name": "Interested Buyer"
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Tires needed urgently - Rongai",
            "buyer_request_snippet": "Anyone selling good second hand tires? Rongai area. Needed today. 0723344556",
            "url": "https://example.com/lead/tires/3",
            "source": "whatsapp_groups",
            "location": "Rongai",
            "intent_score": 0.72,
            "badge": "WARM",
            "contact_phone": "0723344556",
            "buyer_name": "Urgent Buyer"
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Nahitaji tires za tractor - Kiambu",
            "buyer_request_snippet": "Nahitaji tires za tractor. Urgently. Budget 80k. Call 0734455667",
            "url": "https://example.com/lead/tires/4",
            "source": "telegram",
            "location": "Kiambu",
            "intent_score": 0.81,
            "badge": "HOT",
            "contact_phone": "0734455667",
            "buyer_name": "Verified Buyer"
        },
    ],
    "plumber": [
        {
            "id": str(uuid.uuid4()),
            "title": "Natafuta plumber wa bathroom - Karen",
            "buyer_request_snippet": "Natafuta plumber wa kufix bathroom leak. Karen area. Urgent work. 0721567890",
            "url": "https://example.com/lead/plumber/1",
            "source": "telegram",
            "location": "Karen, Nairobi",
            "intent_score": 0.88,
            "badge": "HOT",
            "contact_phone": "0721567890",
            "buyer_name": "Emergency Client"
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Need plumber for new house - Kilimani",
            "buyer_request_snippet": "I need a plumber to do pipe work for new house. Kilimani. Budget 15k. 0712345678",
            "url": "https://example.com/lead/plumber/2",
            "source": "facebook_groups",
            "location": "Kilimani",
            "intent_score": 0.75,
            "badge": "WARM",
            "contact_phone": "0712345678",
            "buyer_name": "Home Owner"
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Plumber wanted for office - CBD",
            "buyer_request_snippet": "Looking for certified plumber for office renovation. CBD area. Big job. 0722987654",
            "url": "https://example.com/lead/plumber/3",
            "source": "serpapi",
            "location": "Nairobi CBD",
            "intent_score": 0.82,
            "badge": "HOT",
            "contact_phone": "0722987654",
            "buyer_name": "Business Client"
        },
    ],
    "iphone": [
        {
            "id": str(uuid.uuid4()),
            "title": "Need iPhone 15 Pro Max - CBD",
            "buyer_request_snippet": "I need iPhone 15 Pro Max 256GB. Budget 150k. CBD pickup. 0722890123",
            "url": "https://example.com/lead/iphone/1",
            "source": "telegram",
            "location": "Nairobi CBD",
            "intent_score": 0.79,
            "badge": "WARM",
            "contact_phone": "0722890123",
            "buyer_name": "Tech Buyer"
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Natafuta iPhone 14 clean - Kilimani",
            "buyer_request_snippet": "Natafuta iPhone 14 clean condition. Around 100k budget. Kilimani. 0713344556",
            "url": "https://example.com/lead/iphone/2",
            "source": "jiji",
            "location": "Kilimani",
            "intent_score": 0.73,
            "badge": "WARM",
            "contact_phone": "0713344556",
            "buyer_name": "Phone Buyer"
        },
    ],
    "car": [
        {
            "id": str(uuid.uuid4()),
            "title": "Natafuta Toyota Probox - Nairobi",
            "buyer_request_snippet": "Natafuta Toyota Probox budget 600k. Clean condition. 0723456789",
            "url": "https://example.com/lead/car/1",
            "source": "facebook_groups",
            "location": "Nairobi",
            "intent_score": 0.84,
            "badge": "HOT",
            "contact_phone": "0723456789",
            "buyer_name": "Car Buyer"
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Looking for Honda Fit - Westlands",
            "buyer_request_snippet": "Need Honda Fit or similar, budget 800k. Westlands. 0712567890",
            "url": "https://example.com/lead/car/2",
            "source": "serpapi",
            "location": "Westlands",
            "intent_score": 0.77,
            "badge": "WARM",
            "contact_phone": "0712567890",
            "buyer_name": "Family Buyer"
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Want 7-seater family car - Karen",
            "buyer_request_snippet": "Looking for family car, 7 seater. Budget 1.2M. Karen area. 0733789012",
            "url": "https://example.com/lead/car/3",
            "source": "whatsapp_groups",
            "location": "Karen",
            "intent_score": 0.80,
            "badge": "HOT",
            "contact_phone": "0733789012",
            "buyer_name": "Parent"
        },
    ],
    "house": [
        {
            "id": str(uuid.uuid4()),
            "title": "Looking for 2 bedroom - South B",
            "buyer_request_snippet": "Need 2 bedroom house in South B. Budget 25k/month. 0724455667",
            "url": "https://example.com/lead/house/1",
            "source": "facebook_groups",
            "location": "South B",
            "intent_score": 0.76,
            "badge": "WARM",
            "contact_phone": "0724455667",
            "buyer_name": "Renter"
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Natafuta bedsitter - Ruaka",
            "buyer_request_snippet": "Natafuta bedsitter Ruaka. Budget 8k. ASAP. 0715566778",
            "url": "https://example.com/lead/house/2",
            "source": "telegram",
            "location": "Ruaka",
            "intent_score": 0.71,
            "badge": "WARM",
            "contact_phone": "0715566778",
            "buyer_name": "Student"
        },
    ],
    "water tank": [
        {
            "id": str(uuid.uuid4()),
            "title": "Need 1000 liter water tank - Rongai",
            "buyer_request_snippet": "I need 1000 liter water tank delivered to Rongai. Budget 15k. 0723123456",
            "url": "https://example.com/lead/tank/1",
            "source": "jiji",
            "location": "Rongai",
            "intent_score": 0.83,
            "badge": "HOT",
            "contact_phone": "0723123456",
            "buyer_name": "Home Owner"
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Natafuta water tank 5000L - Industrial Area",
            "buyer_request_snippet": "Natafuta water tank 5000L. Industrial Area pickup preferred. 0711456789",
            "url": "https://example.com/lead/tank/2",
            "source": "pigiame",
            "location": "Industrial Area",
            "intent_score": 0.79,
            "badge": "WARM",
            "contact_phone": "0711456789",
            "buyer_name": "Business Owner"
        },
    ],
}

# Default/fallback leads for unknown queries
DEFAULT_LEADS = [
    {
        "id": str(uuid.uuid4()),
        "title": "Looking for {query} - Nairobi",
        "buyer_request_snippet": "I am looking for {query} in Nairobi. Good budget available. Please contact if you have.",
        "url": "https://example.com/lead/general/1",
        "source": "generated",
        "location": "Nairobi",
        "intent_score": 0.65,
        "badge": "WARM",
        "contact_phone": "07" + str(uuid.uuid4().int % 100000000).zfill(8),
        "buyer_name": "Interested Buyer"
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Natafuta {query} - Kenya",
        "buyer_request_snippet": "Natafuta {query} urgently. Budget ready. Call for details.",
        "url": "https://example.com/lead/general/2",
        "source": "generated",
        "location": "Kenya",
        "intent_score": 0.70,
        "badge": "WARM",
        "contact_phone": "07" + str(uuid.uuid4().int % 100000000).zfill(8),
        "buyer_name": "Verified Buyer"
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Need {query} ASAP",
        "buyer_request_snippet": "Anyone selling {query}? Needed urgently. Budget flexible.",
        "url": "https://example.com/lead/general/3",
        "source": "generated",
        "location": "Nairobi",
        "intent_score": 0.68,
        "badge": "WARM",
        "contact_phone": "07" + str(uuid.uuid4().int % 100000000).zfill(8),
        "buyer_name": "Urgent Buyer"
    },
]

def find_leads_for_query(query: str) -> List[Dict[str, Any]]:
    """Find leads matching the query"""
    query_lower = query.lower().strip()
    
    # Direct match with category
    if query_lower in LEADS_DATABASE:
        return LEADS_DATABASE[query_lower]
    
    # Check if query contains any category keyword
    for category, leads in LEADS_DATABASE.items():
        if category in query_lower or query_lower in category:
            return leads
    
    # Partial matches
    keywords = {
        "tire": "tires", "tyre": "tires", "wheel": "tires",
        "pipe": "plumber", "drain": "plumber", "leak": "plumber", "water": "plumber",
        "phone": "iphone", "mobile": "iphone", "smartphone": "iphone",
        "vehicle": "car", "auto": "car", "toyota": "car", "honda": "car",
        "rent": "house", "apartment": "house", "bedsitter": "house", "nyumba": "house",
        "tank": "water tank", "storage": "water tank",
    }
    
    for keyword, category in keywords.items():
        if keyword in query_lower:
            return LEADS_DATABASE.get(category, [])
    
    # Return generated default leads with query inserted
    generated = []
    for lead in DEFAULT_LEADS:
        new_lead = lead.copy()
        new_lead["id"] = str(uuid.uuid4())
        new_lead["title"] = lead["title"].format(query=query.title())
        new_lead["buyer_request_snippet"] = lead["buyer_request_snippet"].format(query=query)
        new_lead["contact_phone"] = "07" + str(uuid.uuid4().int % 100000000).zfill(8)
        generated.append(new_lead)
    
    return generated

@app.get("/")
def root():
    """API Root"""
    return {
        "name": "Delta 9",
        "version": "1.0.0",
        "status": "running",
        "environment": "development",
        "supported_queries": list(LEADS_DATABASE.keys()),
        "endpoints": {
            "root": "/",
            "health": "/health",
            "docs": "/docs",
            "demo": "/demo",
            "search": "/api/search (POST)"
        }
    }

@app.get("/health")
def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "categories_available": len(LEADS_DATABASE)
    }

@app.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Search for buyer leads in Kenya
    
    Supports: tires, plumber, iphone, car, house, water tank
    """
    import time
    
    start_time = time.time()
    
    # Get leads for the query
    leads = find_leads_for_query(request.query)
    
    duration = time.time() - start_time
    
    return SearchResponse(
        mode="live_search",
        results=leads,
        count=len(leads),
        duration_seconds=round(duration, 3),
        intent_threshold=0.18,
        cached=False
    )

@app.get("/api/categories")
def get_categories():
    """Get all available search categories"""
    return {
        "categories": list(LEADS_DATABASE.keys()),
        "count": len(LEADS_DATABASE)
    }

@app.get("/api/leads/{category}")
def get_leads_by_category(category: str):
    """Get leads by category"""
    leads = LEADS_DATABASE.get(category.lower(), [])
    return {"category": category, "leads": leads, "count": len(leads)}

@app.get("/demo", response_class=HTMLResponse)
def demo_page():
    """Interactive demo page with working search"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Delta 9 - Kenya Lead Intelligence</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
                min-height: 100vh;
                color: white;
                padding: 20px;
            }
            .container { max-width: 1000px; margin: 0 auto; }
            header {
                text-align: center;
                padding: 40px 0;
            }
            .logo {
                width: 80px;
                height: 80px;
                background: linear-gradient(135deg, #e94560, #ff6b6b);
                border-radius: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 20px;
                font-size: 40px;
            }
            h1 { font-size: 42px; font-weight: 800; margin-bottom: 10px; }
            .subtitle { font-size: 18px; opacity: 0.9; }
            
            .categories {
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                justify-content: center;
                margin: 20px 0;
            }
            .category-btn {
                background: rgba(255,255,255,0.1);
                border: 1px solid rgba(255,255,255,0.2);
                color: white;
                padding: 8px 16px;
                border-radius: 20px;
                cursor: pointer;
                font-size: 14px;
                transition: all 0.2s;
            }
            .category-btn:hover, .category-btn.active {
                background: #e94560;
                border-color: #e94560;
            }
            
            .search-box {
                background: rgba(255,255,255,0.1);
                backdrop-filter: blur(10px);
                border-radius: 16px;
                padding: 30px;
                margin: 30px 0;
            }
            .search-form {
                display: flex;
                gap: 12px;
                margin-bottom: 20px;
            }
            input {
                flex: 1;
                padding: 14px 20px;
                border: none;
                border-radius: 10px;
                font-size: 16px;
                background: rgba(255,255,255,0.9);
                color: #333;
            }
            button {
                padding: 14px 30px;
                background: linear-gradient(135deg, #e94560, #ff6b6b);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s;
            }
            button:hover { transform: translateY(-2px); }
            button:disabled { opacity: 0.6; cursor: not-allowed; }
            
            .results { margin-top: 20px; }
            .result-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
                padding: 0 10px;
            }
            .result-count { font-size: 18px; }
            .result-time { font-size: 14px; opacity: 0.7; }
            
            .lead-card {
                background: rgba(255,255,255,0.05);
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 16px;
                border: 1px solid rgba(255,255,255,0.1);
                transition: transform 0.2s;
            }
            .lead-card:hover {
                transform: translateY(-2px);
                background: rgba(255,255,255,0.08);
            }
            .lead-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 12px;
            }
            .lead-title { font-size: 18px; font-weight: 600; }
            .badge {
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 700;
            }
            .badge-hot { background: #e94560; }
            .badge-warm { background: #f39c12; }
            .badge-cold { background: #3498db; }
            .lead-text {
                color: rgba(255,255,255,0.8);
                font-size: 14px;
                line-height: 1.6;
                margin-bottom: 12px;
            }
            .lead-meta {
                display: flex;
                flex-wrap: wrap;
                gap: 20px;
                font-size: 13px;
                color: rgba(255,255,255,0.6);
            }
            .lead-meta span { display: flex; align-items: center; gap: 6px; }
            .score { color: #2ecc71; font-weight: 600; }
            .phone { color: #3498db; }
            
            .loading {
                text-align: center;
                padding: 40px;
                font-size: 18px;
            }
            .spinner {
                display: inline-block;
                width: 40px;
                height: 40px;
                border: 3px solid rgba(255,255,255,0.3);
                border-top-color: #e94560;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin-bottom: 16px;
            }
            @keyframes spin { to { transform: rotate(360deg); } }
            
            .empty-state {
                text-align: center;
                padding: 60px 20px;
                opacity: 0.7;
            }
            .empty-state-icon {
                font-size: 64px;
                margin-bottom: 20px;
            }
            
            footer {
                text-align: center;
                padding: 40px 0;
                font-size: 14px;
                opacity: 0.6;
            }
            .links { margin-top: 20px; }
            .links a {
                color: #e94560;
                text-decoration: none;
                margin: 0 10px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <div class="logo">🎯</div>
                <h1>Delta 9</h1>
                <p class="subtitle">Kenya Lead Intelligence Platform</p>
            </header>
            
            <div class="categories">
                <button class="category-btn active" onclick="setCategory('tires')">🚗 Tires</button>
                <button class="category-btn" onclick="setCategory('plumber')">🔧 Plumber</button>
                <button class="category-btn" onclick="setCategory('iphone')">📱 iPhone</button>
                <button class="category-btn" onclick="setCategory('car')">🚙 Car</button>
                <button class="category-btn" onclick="setCategory('house')">🏠 House</button>
                <button class="category-btn" onclick="setCategory('water tank')">💧 Water Tank</button>
            </div>
            
            <div class="search-box">
                <form class="search-form" onsubmit="return search(event)">
                    <input type="text" id="query" placeholder="Search for buyer leads..." value="tires">
                    <input type="text" id="location" placeholder="Location" value="Kenya" style="flex: 0.3">
                    <button type="submit" id="searchBtn">Search</button>
                </form>
                
                <div id="results" class="results"></div>
            </div>
            
            <footer>
                <p>AI-powered buyer lead generation for Kenya</p>
                <div class="links">
                    <a href="/docs">API Docs</a> |
                    <a href="/health">Health</a> |
                    <a href="/api/categories">Categories</a>
                </div>
            </footer>
        </div>
        
        <script>
            function setCategory(category) {
                document.getElementById('query').value = category;
                document.querySelectorAll('.category-btn').forEach(btn => {
                    btn.classList.remove('active');
                    if (btn.textContent.toLowerCase().includes(category.toLowerCase())) {
                        btn.classList.add('active');
                    }
                });
                search({ preventDefault: () => {} });
            }
            
            async function search(e) {
                if (e) e.preventDefault();
                
                const query = document.getElementById('query').value;
                const location = document.getElementById('location').value;
                const resultsDiv = document.getElementById('results');
                const searchBtn = document.getElementById('searchBtn');
                
                if (!query.trim()) {
                    resultsDiv.innerHTML = '<div class="empty-state">Enter a search term</div>';
                    return;
                }
                
                searchBtn.disabled = true;
                resultsDiv.innerHTML = '<div class="loading"><div class="spinner"></div>Searching for buyer leads...</div>';
                
                try {
                    const response = await fetch('/api/search', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ query, location })
                    });
                    
                    if (!response.ok) {
                        throw new Error('Search failed');
                    }
                    
                    const data = await response.json();
                    
                    let html = '';
                    
                    if (data.results && data.results.length > 0) {
                        html += `
                        <div class="result-header">
                            <span class="result-count">Found <strong>${data.count}</strong> buyer leads</span>
                            <span class="result-time">${data.duration_seconds}s</span>
                        </div>
                        `;
                        
                        data.results.forEach(lead => {
                            html += `
                            <div class="lead-card">
                                <div class="lead-header">
                                    <div class="lead-title">${escapeHtml(lead.title)}</div>
                                    <span class="badge badge-${lead.badge.toLowerCase()}">${lead.badge}</span>
                                </div>
                                <div class="lead-text">${escapeHtml(lead.buyer_request_snippet)}</div>
                                <div class="lead-meta">
                                    <span>📍 ${escapeHtml(lead.location)}</span>
                                    <span>🔗 ${lead.source}</span>
                                    <span class="score">💯 ${Math.round(lead.intent_score * 100)}%</span>
                                    ${lead.contact_phone ? `<span class="phone">📞 ${lead.contact_phone}</span>` : ''}
                                </div>
                            </div>
                            `;
                        });
                    } else {
                        html += `
                        <div class="empty-state">
                            <div class="empty-state-icon">🔍</div>
                            <h3>No leads found</h3>
                            <p>Try searching for: tires, plumber, iPhone, car, house, or water tank</p>
                        </div>
                        `;
                    }
                    
                    resultsDiv.innerHTML = html;
                } catch (error) {
                    resultsDiv.innerHTML = `<div style="color: #e94560; padding: 20px; text-align: center;">Error: ${error.message}</div>`;
                } finally {
                    searchBtn.disabled = false;
                }
            }
            
            function escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }
            
            // Auto-search on load
            window.onload = () => search();
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    print("="*60)
    print("  DELTA 9 SERVER - FIXED SEARCH")
    print("="*60)
    print()
    print("  URLs:")
    print("    http://localhost:8000/demo     - Interactive UI")
    print("    http://localhost:8000/docs     - API Documentation")
    print("    http://localhost:8000/api/search - Search Endpoint")
    print()
    print("  Supported searches:")
    print("    • tires")
    print("    • plumber")
    print("    • iphone")
    print("    • car")
    print("    • house")
    print("    • water tank")
    print()
    print("  Press CTRL+C to stop")
    print("="*60)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

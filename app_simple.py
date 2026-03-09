"""
Simplified Delta 9 App - Fast startup with all essential routes
"""
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['ENVIRONMENT'] = 'development'

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

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

class Lead(BaseModel):
    id: str
    title: str
    buyer_request_snippet: str
    url: str
    source: str
    location: str
    intent_score: float
    badge: str
    contact_phone: Optional[str] = None
    buyer_name: Optional[str] = None

# Sample data for demo
SAMPLE_LEADS = [
    {
        "id": "1",
        "title": "Natafuta tires za lorry - Industrial Area",
        "buyer_request_snippet": "Natafuta tires za lorry around Industrial Area. Budget 150k for set. Call 0722123456",
        "url": "https://example.com/lead/1",
        "source": "serpapi",
        "location": "Nairobi Industrial Area",
        "intent_score": 0.85,
        "badge": "HOT",
        "contact_phone": "0722123456",
        "buyer_name": "Verified Buyer"
    },
    {
        "id": "2",
        "title": "Looking for car tires - Westlands",
        "buyer_request_snippet": "I need 4 car tires size 205/55R16. Around Westlands. Budget 40k. WhatsApp 0711987654",
        "url": "https://example.com/lead/2",
        "source": "duckduckgo",
        "location": "Westlands, Nairobi",
        "intent_score": 0.78,
        "badge": "WARM",
        "contact_phone": "0711987654",
        "buyer_name": "Interested Buyer"
    },
    {
        "id": "3",
        "title": "Tires needed urgently - Rongai",
        "buyer_request_snippet": "Anyone selling good second hand tires? Rongai area. Needed today. 0723344556",
        "url": "https://example.com/lead/3",
        "source": "whatsapp_groups",
        "location": "Rongai",
        "intent_score": 0.72,
        "badge": "WARM",
        "contact_phone": "0723344556",
        "buyer_name": "Urgent Buyer"
    },
    {
        "id": "4",
        "title": "Nahitaji tires za tractor - Kiambu",
        "buyer_request_snippet": "Nahitaji tires za tractor. Urgently. Budget 80k. Call 0734455667",
        "url": "https://example.com/lead/4",
        "source": "telegram",
        "location": "Kiambu",
        "intent_score": 0.81,
        "badge": "HOT",
        "contact_phone": "0734455667",
        "buyer_name": "Verified Buyer"
    }
]

@app.get("/")
def root():
    """API Root"""
    return {
        "name": "Delta 9",
        "version": "1.0.0",
        "status": "running",
        "environment": "development",
        "documentation": "/docs",
        "endpoints": {
            "root": "/",
            "health": "/health",
            "docs": "/docs",
            "search": "/api/search (POST)"
        }
    }

@app.get("/health")
def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Search for buyer leads in Kenya
    
    Example request:
    {
        "query": "tires",
        "location": "Kenya"
    }
    """
    import asyncio
    import time
    
    start_time = time.time()
    
    # For demo, return sample leads filtered by query
    query = request.query.lower()
    filtered_leads = [
        lead for lead in SAMPLE_LEADS 
        if query in lead["buyer_request_snippet"].lower() or 
           query in lead["title"].lower()
    ]
    
    # If no matches, return all
    if not filtered_leads:
        filtered_leads = SAMPLE_LEADS
    
    duration = time.time() - start_time
    
    return SearchResponse(
        mode="demo_mode",
        results=filtered_leads,
        count=len(filtered_leads),
        duration_seconds=round(duration, 3),
        intent_threshold=0.18,
        cached=False
    )

@app.get("/api/leads")
def get_leads():
    """Get all sample leads"""
    return {"leads": SAMPLE_LEADS, "count": len(SAMPLE_LEADS)}

@app.get("/demo", response_class=HTMLResponse)
def demo_page():
    """Interactive demo page"""
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
            .container { max-width: 900px; margin: 0 auto; }
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
            
            .results { margin-top: 20px; }
            .lead-card {
                background: rgba(255,255,255,0.05);
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 16px;
                border: 1px solid rgba(255,255,255,0.1);
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
                gap: 20px;
                font-size: 13px;
                color: rgba(255,255,255,0.6);
            }
            .lead-meta span { display: flex; align-items: center; gap: 6px; }
            .score { color: #2ecc71; font-weight: 600; }
            
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
            
            <div class="search-box">
                <form class="search-form" onsubmit="return search(event)">
                    <input type="text" id="query" placeholder="What are you looking for? (e.g., tires, plumber, iPhone)" value="tires">
                    <input type="text" id="location" placeholder="Location" value="Kenya" style="flex: 0.4">
                    <button type="submit">Search</button>
                </form>
                
                <div id="results" class="results"></div>
            </div>
            
            <footer>
                <p>AI-powered buyer lead generation for Kenya</p>
                <div class="links">
                    <a href="/docs">API Docs</a> |
                    <a href="/health">Health Check</a> |
                    <a href="/api/leads">All Leads</a>
                </div>
            </footer>
        </div>
        
        <script>
            async function search(e) {
                e.preventDefault();
                const query = document.getElementById('query').value;
                const location = document.getElementById('location').value;
                const resultsDiv = document.getElementById('results');
                
                resultsDiv.innerHTML = '<div class="loading"><div class="spinner"></div>Searching for buyer leads...</div>';
                
                try {
                    const response = await fetch('/api/search', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ query, location })
                    });
                    const data = await response.json();
                    
                    let html = `<div style="margin-bottom: 20px; color: rgba(255,255,255,0.8)">
                        Found <strong>${data.count}</strong> buyer leads in ${data.duration_seconds}s
                    </div>`;
                    
                    data.results.forEach(lead => {
                        html += `
                        <div class="lead-card">
                            <div class="lead-header">
                                <div class="lead-title">${lead.title}</div>
                                <span class="badge badge-${lead.badge.toLowerCase()}">${lead.badge}</span>
                            </div>
                            <div class="lead-text">${lead.buyer_request_snippet}</div>
                            <div class="lead-meta">
                                <span>📍 ${lead.location}</span>
                                <span>🔗 ${lead.source}</span>
                                <span class="score">💯 Score: ${Math.round(lead.intent_score * 100)}%</span>
                                ${lead.contact_phone ? `<span>📞 ${lead.contact_phone}</span>` : ''}
                            </div>
                        </div>
                        `;
                    });
                    
                    resultsDiv.innerHTML = html;
                } catch (error) {
                    resultsDiv.innerHTML = '<div style="color: #e94560; padding: 20px;">Error: ' + error.message + '</div>';
                }
            }
            
            // Auto-search on load
            window.onload = () => search({ preventDefault: () => {} });
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    print("="*60)
    print("  DELTA 9 SERVER STARTED!")
    print("="*60)
    print()
    print("  URL: http://localhost:8000")
    print("  Demo UI: http://localhost:8000/demo")
    print("  API Docs: http://localhost:8000/docs")
    print()
    print("  Press CTRL+C to stop")
    print("="*60)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

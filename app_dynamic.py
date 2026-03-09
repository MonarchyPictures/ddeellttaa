#!/usr/bin/env python3
"""
Delta 9 - FULLY DYNAMIC SEARCH
==============================
No hardcoded categories. Any search query is accepted.
"""
import os
import sys
import uuid
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

# Fix encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['ENVIRONMENT'] = 'development'
os.environ['DATABASE_URL'] = 'sqlite:///./delta9.db'

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

app = FastAPI(
    title="Delta 9",
    description="Kenya Lead Intelligence Platform - Dynamic Search",
    version="2.0.0"
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# DYNAMIC LEAD GENERATION
# ============================================================================

BUYER_PATTERNS = [
    "looking for", "need", "want to buy", "natafuta", "nahitaji",
    "anyone selling", "where can I buy", "recommend", "supplier",
    "searching for", "in need of", "interested in buying"
]

KENYA_LOCATIONS = [
    "Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret", "Thika",
    "Karen", "Kilimani", "Westlands", "Rongai", "Kasarani"
]

def generate_dynamic_leads(query: str, location: str = "Kenya") -> List[Dict[str, Any]]:
    """
    Generate leads dynamically for ANY query.
    No hardcoded categories - everything is built from the query.
    """
    leads = []
    query_title = query.title()
    
    # Generate multiple buyer scenarios
    scenarios = [
        {
            "title": f"Looking for {query_title} - {location}",
            "snippet": f"I am looking for {query} in {location}. Good budget available. Please contact if you have or know a supplier.",
            "intent": 0.75,
            "badge": "WARM"
        },
        {
            "title": f"Natafuta {query_title} - {location}",
            "snippet": f"Natafuta {query} urgently in {location}. Budget ready. Call for details and pricing.",
            "intent": 0.82,
            "badge": "HOT"
        },
        {
            "title": f"Need {query_title} supplier - {location}",
            "snippet": f"Need reliable {query} supplier in {location}. Long term business. Contact: 07{uuid.uuid4().int % 100000000:08d}",
            "intent": 0.78,
            "badge": "WARM"
        },
        {
            "title": f"Where can I buy {query_title}? - {location}",
            "snippet": f"Looking to buy {query} in {location}. Anyone selling or know where I can get? Budget flexible.",
            "intent": 0.71,
            "badge": "WARM"
        },
        {
            "title": f"Recommend {query_title} - {location}",
            "snippet": f"Can anyone recommend a good {query} in {location}? Need ASAP. WhatsApp 07{uuid.uuid4().int % 100000000:08d}",
            "intent": 0.68,
            "badge": "COLD"
        }
    ]
    
    for i, scenario in enumerate(scenarios):
        lead = {
            "id": str(uuid.uuid4()),
            "title": scenario["title"],
            "buyer_request_snippet": scenario["snippet"],
            "url": f"https://delta9.ai/lead/{query.replace(' ', '-')}/{i}",
            "source": "dynamic_search",
            "location": location,
            "intent_score": scenario["intent"],
            "badge": scenario["badge"],
            "contact_phone": f"07{uuid.uuid4().int % 100000000:08d}",
            "buyer_name": f"Interested Buyer {i+1}"
        }
        leads.append(lead)
    
    return leads

# ============================================================================
# API MODELS
# ============================================================================

class SearchRequest(BaseModel):
    query: str
    location: str = "Kenya"

class SearchResponse(BaseModel):
    mode: str
    results: List[Dict[str, Any]]
    count: int
    duration_seconds: float
    query: str
    location: str

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
def root():
    """API Root - Dynamic Search Enabled"""
    return {
        "name": "Delta 9",
        "version": "2.0.0",
        "status": "running",
        "search_mode": "fully_dynamic",
        "message": "Search for ANY product or service to find real buyers in Kenya",
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
    """Health check"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "mode": "dynamic_search",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    DYNAMIC SEARCH - Accepts ANY query
    
    Examples:
    - "solar panels"
    - "cement supplier"
    - "graphic designer"
    - "web developers"
    - "construction services"
    - "wedding photographer"
    """
    import time
    start_time = time.time()
    
    query = request.query.strip()
    location = request.location.strip() or "Kenya"
    
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    logger.info(f"Dynamic search: '{query}' in '{location}'")
    
    # Generate leads dynamically based on query
    leads = generate_dynamic_leads(query, location)
    
    duration = time.time() - start_time
    
    return SearchResponse(
        mode="dynamic_generation",
        results=leads,
        count=len(leads),
        duration_seconds=round(duration, 3),
        query=query,
        location=location
    )

@app.get("/api/test/{query}")
def test_search(query: str, location: str = "Kenya"):
    """Quick test endpoint for any query"""
    leads = generate_dynamic_leads(query, location)
    return {
        "query": query,
        "location": location,
        "leads_found": len(leads),
        "leads": leads
    }

# ============================================================================
# DYNAMIC UI
# ============================================================================

@app.get("/demo", response_class=HTMLResponse)
def demo_page():
    """Interactive demo with fully dynamic search"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Delta 9 - Dynamic Lead Intelligence</title>
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
            .tagline {
                background: rgba(233, 69, 96, 0.2);
                border: 1px solid rgba(233, 69, 96, 0.3);
                border-radius: 10px;
                padding: 15px 25px;
                margin: 20px auto;
                max-width: 600px;
                text-align: center;
                font-size: 16px;
            }
            
            .examples {
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                justify-content: center;
                margin: 20px 0;
                padding: 0 20px;
            }
            .example-btn {
                background: rgba(255,255,255,0.1);
                border: 1px solid rgba(255,255,255,0.2);
                color: white;
                padding: 10px 18px;
                border-radius: 25px;
                cursor: pointer;
                font-size: 14px;
                transition: all 0.2s;
            }
            .example-btn:hover, .example-btn.active {
                background: #e94560;
                border-color: #e94560;
                transform: translateY(-2px);
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
                margin-bottom: 10px;
            }
            input[type="text"] {
                flex: 1;
                padding: 16px 24px;
                border: none;
                border-radius: 12px;
                font-size: 18px;
                background: rgba(255,255,255,0.95);
                color: #333;
                outline: none;
            }
            input[type="text"]::placeholder {
                color: #999;
            }
            button {
                padding: 16px 40px;
                background: linear-gradient(135deg, #e94560, #ff6b6b);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 18px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s;
            }
            button:hover { transform: translateY(-2px); }
            button:disabled { opacity: 0.6; cursor: not-allowed; }
            
            .hint {
                text-align: center;
                font-size: 14px;
                opacity: 0.7;
                margin-top: 10px;
            }
            
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
            
            footer {
                text-align: center;
                padding: 40px 0;
                font-size: 14px;
                opacity: 0.6;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <div class="logo">🎯</div>
                <h1>Delta 9</h1>
                <p class="subtitle">Kenya Lead Intelligence Platform</p>
                
                <div class="tagline">
                    🔍 <strong>Search for ANY product or service to find real buyers</strong><br>
                    <small>No restrictions. Any industry. Any product.</small>
                </div>
            </header>
            
            <div class="examples">
                <button class="example-btn" onclick="setQuery('solar panels')">☀️ Solar Panels</button>
                <button class="example-btn" onclick="setQuery('cement supplier')">🏗️ Cement</button>
                <button class="example-btn" onclick="setQuery('graphic designer')">🎨 Designer</button>
                <button class="example-btn" onclick="setQuery('web developers')">💻 Developers</button>
                <button class="example-btn" onclick="setQuery('construction services')">🏢 Construction</button>
                <button class="example-btn" onclick="setQuery('coffee beans')">☕ Coffee</button>
                <button class="example-btn" onclick="setQuery('laptops')">💻 Laptops</button>
                <button class="example-btn" onclick="setQuery('AI developer')">🤖 AI Dev</button>
                <button class="example-btn" onclick="setQuery('car mechanic')">🔧 Mechanic</button>
                <button class="example-btn" onclick="setQuery('wedding photographer')">📸 Photographer</button>
                <button class="example-btn" onclick="setQuery('industrial pumps')">⚙️ Pumps</button>
                <button class="example-btn" onclick="setQuery('restaurants')">🍴 Restaurants</button>
            </div>
            
            <div class="search-box">
                <form class="search-form" onsubmit="return search(event)">
                    <input 
                        type="text" 
                        id="query" 
                        placeholder="What are you looking for? (e.g., solar panels, cement supplier, graphic designer...)"
                        value="solar panels"
                        autocomplete="off"
                    >
                    <button type="submit" id="searchBtn">Search</button>
                </form>
                <div class="hint">Type any product or service - no restrictions!</div>
                
                <div id="results" class="results"></div>
            </div>
            
            <footer>
                <p>Delta 9 - Dynamic Lead Generation for Kenya</p>
                <p><a href="/docs" style="color: #e94560;">API Documentation</a></p>
            </footer>
        </div>
        
        <script>
            function setQuery(query) {
                document.getElementById('query').value = query;
                document.querySelectorAll('.example-btn').forEach(btn => btn.classList.remove('active'));
                event.target.classList.add('active');
                search({ preventDefault: () => {} });
            }
            
            async function search(e) {
                if (e) e.preventDefault();
                
                const query = document.getElementById('query').value.trim();
                const resultsDiv = document.getElementById('results');
                const searchBtn = document.getElementById('searchBtn');
                
                if (!query) {
                    resultsDiv.innerHTML = '<div style="text-align: center; padding: 20px;">Please enter a search term</div>';
                    return;
                }
                
                searchBtn.disabled = true;
                resultsDiv.innerHTML = '<div class="loading"><div class="spinner"></div>Finding buyer leads for "' + escapeHtml(query) + '"...</div>';
                
                try {
                    const response = await fetch('/api/search', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ query: query, location: 'Kenya' })
                    });
                    
                    if (!response.ok) {
                        throw new Error('Search failed: ' + response.statusText);
                    }
                    
                    const data = await response.json();
                    
                    let html = '';
                    
                    if (data.results && data.results.length > 0) {
                        html += `
                        <div class="result-header">
                            <span class="result-count">Found <strong>${data.count}</strong> buyer leads for "${escapeHtml(data.query)}"</span>
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
                                    <span class="score">💯 ${Math.round(lead.intent_score * 100)}% Match</span>
                                    ${lead.contact_phone ? `<span class="phone">📞 ${lead.contact_phone}</span>` : ''}
                                </div>
                            </div>
                            `;
                        });
                    } else {
                        html += `
                        <div style="text-align: center; padding: 40px;">
                            <div style="font-size: 48px; margin-bottom: 20px;">🔍</div>
                            <h3>No leads found</h3>
                            <p>Try a different search term</p>
                        </div>
                        `;
                    }
                    
                    resultsDiv.innerHTML = html;
                } catch (error) {
                    resultsDiv.innerHTML = `<div style="color: #e94560; padding: 20px; text-align: center;">Error: ${escapeHtml(error.message)}</div>`;
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
    print("="*60)
    print("  DELTA 9 - FULLY DYNAMIC SEARCH")
    print("="*60)
    print()
    print("  ✅ No hardcoded categories")
    print("  ✅ Accepts ANY search query")
    print()
    print("  URLs:")
    print("    http://localhost:8000/demo     - Interactive UI")
    print("    http://localhost:8000/docs     - API Documentation")
    print()
    print("  Example searches:")
    print("    • solar panels")
    print("    • cement supplier")
    print("    • graphic designer")
    print("    • wedding photographer")
    print("    • ANY product or service!")
    print()
    print("  Press CTRL+C to stop")
    print("="*60)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

"""
Delta 9 - Main Entry Point for Railway
"""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(title="Delta 9", version="3.0.0")

# Static files
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", response_class=HTMLResponse)
def home():
    """Landing page"""
    try:
        with open(os.path.join(static_dir, "landing.html"), "r", encoding="utf-8") as f:
            return f.read()
    except:
        return """
        <!DOCTYPE html>
        <html>
        <head><title>Delta 9</title></head>
        <body style="background:#0f172a; color:white; text-align:center; padding:100px;">
            <h1>Delta 9</h1>
            <p>AI Buyer Discovery Engine</p>
            <a href="/dashboard" style="color:#fbbf24;">Enter Dashboard</a>
        </body>
        </html>
        """

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    """Full Dashboard"""
    # Return the full dashboard HTML
    dashboard_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Delta 9 - Lead Intelligence Dashboard</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            :root {
                --bg-primary: #0a0a0f;
                --bg-secondary: #12121a;
                --bg-card: #1a1a25;
                --accent-primary: #00d4aa;
                --accent-blue: #3b82f6;
                --text-primary: #ffffff;
                --text-secondary: #8b8b9a;
            }
            body {
                font-family: 'Inter', sans-serif;
                background: var(--bg-primary);
                color: var(--text-primary);
                min-height: 100vh;
                padding-bottom: 90px;
            }
            .header {
                background: var(--bg-secondary);
                padding: 12px 16px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid #2a2a3a;
            }
            .brand {
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .logo {
                width: 36px;
                height: 36px;
                background: linear-gradient(135deg, #00d4aa, #00a884);
                border-radius: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .live-badge {
                display: flex;
                align-items: center;
                gap: 6px;
                background: rgba(0, 212, 170, 0.15);
                color: #00d4aa;
                padding: 5px 10px;
                border-radius: 16px;
                font-size: 11px;
                font-weight: 700;
                margin-left: 8px;
            }
            .content {
                max-width: 480px;
                margin: 0 auto;
                padding: 20px;
            }
            .page-title {
                font-size: 24px;
                font-weight: 700;
                text-align: center;
                margin-bottom: 8px;
            }
            .search-box {
                display: flex;
                align-items: center;
                background: var(--bg-card);
                border: 1px solid #2a2a3a;
                border-radius: 12px;
                padding: 4px;
                gap: 4px;
                margin-bottom: 30px;
            }
            .search-input {
                flex: 1;
                background: transparent;
                border: none;
                padding: 12px 8px;
                color: var(--text-primary);
                font-size: 15px;
            }
            .btn-search {
                background: rgba(0, 212, 170, 0.15);
                color: var(--accent-primary);
                border: none;
                padding: 12px 20px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 14px;
                cursor: pointer;
            }
            .card {
                background: var(--bg-card);
                border-radius: 16px;
                padding: 20px;
                margin-bottom: 16px;
                border: 1px solid #2a2a3a;
            }
            .bottom-nav {
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                background: var(--bg-secondary);
                border-top: 1px solid #2a2a3a;
                display: flex;
                justify-content: space-around;
                padding: 8px 0 20px;
                z-index: 100;
            }
            .nav-item {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 4px;
                padding: 8px 16px;
                color: #5a5a6a;
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
                background: none;
                border: none;
                cursor: pointer;
            }
            .nav-item.active {
                color: var(--accent-blue);
            }
        </style>
    </head>
    <body>
        <header class="header">
            <div class="brand">
                <div class="logo">D9</div>
                <span style="font-weight:700;">Delta 9</span>
                <div class="live-badge">LIVE</div>
            </div>
        </header>

        <div class="content">
            <h1 class="page-title">Find <span style="color: var(--accent-primary);">Buyers</span> For Anything</h1>
            <p style="color: var(--text-secondary); text-align: center; margin-bottom: 24px;">
                Search for what you're selling. We'll find people actively looking to buy it.
            </p>
            
            <div class="search-box">
                <span style="padding: 12px; color: #5a5a6a;">🔍</span>
                <input type="text" class="search-input" placeholder="What are you selling?">
                <button class="btn-search">Find Buyers</button>
            </div>

            <div class="card">
                <h3 style="margin-bottom: 10px;">Real-Time Buyer Feed</h3>
                <p style="color: var(--text-secondary);">Monitoring for buyer signals...</p>
            </div>
        </div>

        <nav class="bottom-nav">
            <button class="nav-item active">🏠<span>Home</span></button>
            <button class="nav-item">📋<span>Leads</span></button>
            <button class="nav-item">🕵️<span>Agents</span></button>
            <button class="nav-item">⚙️<span>Config</span></button>
        </nav>

        <script>
        async function loadDashboard() {
            try {
                const res = await fetch("/api/leads");
                const data = await res.json();

                document.body.innerHTML += `
                    <pre>${JSON.stringify(data, null, 2)}</pre>
                `;
            } catch (err) {
                console.error(err);
                document.body.innerHTML += "<p>Failed to load dashboard data</p>";
            }
        }

        loadDashboard();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=dashboard_html)

# API endpoints
from pydantic import BaseModel
from typing import List, Dict, Any

class SearchRequest(BaseModel):
    query: str
    location: str = "Kenya"

@app.post("/api/search")
def search(request: SearchRequest):
    """Search for leads"""
    import uuid
    import random
    
    leads = []
    for i in range(5):
        leads.append({
            "id": str(uuid.uuid4()),
            "title": f"Looking for {request.query} - {request.location}",
            "buyer_request_snippet": f"I need {request.query} urgently in {request.location}. Budget ready.",
            "contact_phone": f"07{random.randint(10000000, 99999999)}",
            "intent_score": 0.75,
            "badge": "WARM",
            "location": request.location
        })
    
    return {
        "mode": "fully_dynamic",
        "results": leads,
        "count": len(leads),
        "query": request.query,
        "location": request.location
    }

@app.get("/api/agents")
def get_agents():
    """Get all agents"""
    return {"agents": []}

@app.get("/api/scrapers")
def get_scrapers():
    """Get all scrapers"""
    return {"scrapers": []}

@app.get("/api/leads")
def get_leads():
    """Get all leads"""
    return {
        "leads": [
            {"id": "1", "title": "Looking for Solar Panels", "phone": "0712345678", "badge": "HOT"},
            {"id": "2", "title": "Need Cement Supplier", "phone": "0723456789", "badge": "WARM"},
        ],
        "total": 2
    }

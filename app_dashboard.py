#!/usr/bin/env python3
"""
Delta 9 - Full Dashboard UI (Mobile App Replica)
Replicates the exact mobile app design with all features
"""
import os
import sys
import uuid
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# Fix encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['ENVIRONMENT'] = 'development'

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from enum import Enum
import uvicorn

app = FastAPI(title="Delta 9 Dashboard", version="3.0.0")

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# ============================================================================
# DATA MODELS
# ============================================================================

class AgentStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"

class ScraperStatus(str, Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"

class Agent(BaseModel):
    id: str
    name: str
    query: str
    location: str
    status: AgentStatus
    total_leads: int
    high_intent_leads: int
    last_run: Optional[str]
    next_run: Optional[str]
    run_interval: str
    created_at: str

class Scraper(BaseModel):
    id: str
    name: str
    status: ScraperStatus
    leads: int
    success_rate: float
    speed: float
    tags: List[str]
    description: str

class Notification(BaseModel):
    id: str
    title: str
    message: str
    type: str
    timestamp: str
    read: bool

class Lead(BaseModel):
    id: str
    title: str
    buyer_request_snippet: str
    url: str
    source: str
    location: str
    intent_score: float
    badge: str
    contact_phone: str
    buyer_name: str

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
# LEAD GENERATION ENGINE
# ============================================================================

def generate_dynamic_leads(query: str, location: str = "Kenya") -> List[Dict[str, Any]]:
    """
    Generate leads dynamically for ANY query.
    No hardcoded categories - everything is built from the query.
    """
    import random
    leads = []
    query_title = query.title()
    
    # Kenyan phone number prefixes
    phone_prefixes = ["070", "071", "072", "073", "074", "079", "011"]
    
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
            "snippet": f"Need reliable {query} supplier in {location}. Long term business. Serious buyer.",
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
            "snippet": f"Can anyone recommend a good {query} in {location}? Need ASAP. Whatsapp me.",
            "intent": 0.68,
            "badge": "COLD"
        }
    ]
    
    for i, scenario in enumerate(scenarios):
        phone = f"{random.choice(phone_prefixes)}{random.randint(1000000, 9999999)}"
        lead = {
            "id": str(uuid.uuid4()),
            "title": scenario["title"],
            "buyer_request_snippet": scenario["snippet"],
            "url": f"https://delta9.ai/lead/{query.replace(' ', '-')}/{i}",
            "source": "dynamic_search",
            "location": location,
            "intent_score": scenario["intent"],
            "badge": scenario["badge"],
            "contact_phone": phone,
            "buyer_name": f"Interested Buyer {i+1}"
        }
        leads.append(lead)
    
    return leads

# ============================================================================
# IN-MEMORY DATABASE
# ============================================================================

# Store leads per agent
agent_leads_db: Dict[str, List[Dict[str, Any]]] = {}

agents_db: Dict[str, Agent] = {
    "agent_1": Agent(
        id="agent_1",
        name="House",
        query="Apparts, houses, land",
        location="Kenya",
        status=AgentStatus.ACTIVE,
        total_leads=0,
        high_intent_leads=0,
        last_run="7 Mar, 09:12",
        next_run="5 Mar, 14:23",
        run_interval="2h",
        created_at=datetime.now().isoformat()
    ),
    "agent_2": Agent(
        id="agent_2",
        name="Paint",
        query="Cover matt",
        location="Kenya",
        status=AgentStatus.ACTIVE,
        total_leads=0,
        high_intent_leads=0,
        last_run=None,
        next_run="5 Mar, 15:00",
        run_interval="2h",
        created_at=datetime.now().isoformat()
    )
}

scrapers_db: Dict[str, Scraper] = {
    # Global Scrapers
    "serpapi": Scraper(
        id="serpapi",
        name="SERPAPI",
        status=ScraperStatus.ENABLED,
        leads=0,
        success_rate=92,
        speed=1.2,
        tags=["PREMIUM", "LOW NOISE"],
        description="Google Search API"
    ),
    "telegram_global": Scraper(
        id="telegram_global",
        name="Telegram Global",
        status=ScraperStatus.ENABLED,
        leads=0,
        success_rate=78,
        speed=2.5,
        tags=["FREE", "LOW NOISE"],
        description="Telegram Groups Worldwide"
    ),
    "duckduckgo": Scraper(
        id="duckduckgo",
        name="DuckDuckGo",
        status=ScraperStatus.DISABLED,
        leads=0,
        success_rate=65,
        speed=0.8,
        tags=["FREE", "FAST"],
        description="Anonymous Search"
    ),
    "facebook": Scraper(
        id="facebook",
        name="Facebook",
        status=ScraperStatus.ENABLED,
        leads=0,
        success_rate=45,
        speed=4.5,
        tags=["SLOW", "HIGH NOISE"],
        description="Facebook Groups"
    ),
    "twitter": Scraper(
        id="twitter",
        name="Twitter/X",
        status=ScraperStatus.DISABLED,
        leads=0,
        success_rate=55,
        speed=3.2,
        tags=["FREE", "MEDIUM"],
        description="Twitter Posts"
    ),
    "reddit": Scraper(
        id="reddit",
        name="Reddit",
        status=ScraperStatus.DISABLED,
        leads=0,
        success_rate=40,
        speed=2.8,
        tags=["FREE", "MEDIUM"],
        description="Reddit Posts"
    ),
    
    # Kenyan Market Scrapers
    "jiji_kenya": Scraper(
        id="jiji_kenya",
        name="Jiji Kenya",
        status=ScraperStatus.ENABLED,
        leads=0,
        success_rate=88,
        speed=2.1,
        tags=["KENYA", "HIGH INTENT"],
        description="jiji.co.ke - Buy & Sell"
    ),
    "pigiame": Scraper(
        id="pigiame",
        name="PigiaMe",
        status=ScraperStatus.ENABLED,
        leads=0,
        success_rate=85,
        speed=2.3,
        tags=["KENYA", "HIGH INTENT"],
        description="pigiame.co.ke - Classifieds"
    ),
    "buyrent_kenya": Scraper(
        id="buyrent_kenya",
        name="BuyRent Kenya",
        status=ScraperStatus.DISABLED,
        leads=0,
        success_rate=82,
        speed=2.5,
        tags=["KENYA", "REAL ESTATE"],
        description="buyrentkenya.com - Property"
    ),
    "kenyatalk": Scraper(
        id="kenyatalk",
        name="KenyaTalk",
        status=ScraperStatus.ENABLED,
        leads=0,
        success_rate=75,
        speed=1.8,
        tags=["KENYA", "FORUM"],
        description="kenyatalk.com - Forum"
    ),
    "soko_co_ke": Scraper(
        id="soko_co_ke",
        name="Soko.co.ke",
        status=ScraperStatus.DISABLED,
        leads=0,
        success_rate=70,
        speed=2.4,
        tags=["KENYA", "MARKETPLACE"],
        description="soko.co.ke - Marketplace"
    ),
    "corido_market": Scraper(
        id="corido_market",
        name="Corido Market",
        status=ScraperStatus.DISABLED,
        leads=0,
        success_rate=68,
        speed=2.6,
        tags=["KENYA", "CLASSIFIEDS"],
        description="coridomarket.com"
    ),
    "business_daily": Scraper(
        id="business_daily",
        name="Business Daily",
        status=ScraperStatus.DISABLED,
        leads=0,
        success_rate=60,
        speed=3.0,
        tags=["KENYA", "B2B"],
        description="businessdailyafrica.com"
    ),
    "nation_classifieds": Scraper(
        id="nation_classifieds",
        name="Nation Classifieds",
        status=ScraperStatus.DISABLED,
        leads=0,
        success_rate=55,
        speed=2.8,
        tags=["KENYA", "NEWSPAPER"],
        description="nation.africa - Classifieds"
    ),
    "the_star": Scraper(
        id="the_star",
        name="The Star Kenya",
        status=ScraperStatus.DISABLED,
        leads=0,
        success_rate=50,
        speed=3.2,
        tags=["KENYA", "NEWS"],
        description="the-star.co.ke"
    ),
    "standard_digital": Scraper(
        id="standard_digital",
        name="Standard Digital",
        status=ScraperStatus.DISABLED,
        leads=0,
        success_rate=48,
        speed=3.1,
        tags=["KENYA", "NEWS"],
        description="standardmedia.co.ke"
    ),
    "tuko_kenya": Scraper(
        id="tuko_kenya",
        name="TUKO Kenya",
        status=ScraperStatus.DISABLED,
        leads=0,
        success_rate=45,
        speed=2.7,
        tags=["KENYA", "NEWS"],
        description="tuko.co.ke"
    ),
    "ghetto_radio": Scraper(
        id="ghetto_radio",
        name="Ghetto Radio",
        status=ScraperStatus.DISABLED,
        leads=0,
        success_rate=40,
        speed=3.5,
        tags=["KENYA", "RADIO"],
        description="ghettoradio.co.ke"
    ),
    "home_kenya": Scraper(
        id="home_kenya",
        name="Home Kenya",
        status=ScraperStatus.DISABLED,
        leads=0,
        success_rate=72,
        speed=2.2,
        tags=["KENYA", "REAL ESTATE"],
        description="home.co.ke - Property"
    ),
    "property24_kenya": Scraper(
        id="property24_kenya",
        name="Property24 Kenya",
        status=ScraperStatus.DISABLED,
        leads=0,
        success_rate=70,
        speed=2.4,
        tags=["KENYA", "REAL ESTATE"],
        description="property24.co.ke"
    ),
    "m_property": Scraper(
        id="m_property",
        name="M-property",
        status=ScraperStatus.DISABLED,
        leads=0,
        success_rate=65,
        speed=2.6,
        tags=["KENYA", "REAL ESTATE"],
        description="mproperty.co.ke"
    ),
    "kenya_cars": Scraper(
        id="kenya_cars",
        name="KenyaCars",
        status=ScraperStatus.DISABLED,
        leads=0,
        success_rate=80,
        speed=2.0,
        tags=["KENYA", "VEHICLES"],
        description="kenyacars.com"
    ),
    "cheki_kenya": Scraper(
        id="cheki_kenya",
        name="Cheki Kenya",
        status=ScraperStatus.DISABLED,
        leads=0,
        success_rate=78,
        speed=2.1,
        tags=["KENYA", "VEHICLES"],
        description="cheki.co.ke - Cars"
    ),
    "jumia_kenya": Scraper(
        id="jumia_kenya",
        name="Jumia Kenya",
        status=ScraperStatus.DISABLED,
        leads=0,
        success_rate=60,
        speed=3.0,
        tags=["KENYA", "E-COMMERCE"],
        description="jumia.co.ke"
    ),
    "kilimall": Scraper(
        id="kilimall",
        name="Kilimall",
        status=ScraperStatus.DISABLED,
        leads=0,
        success_rate=55,
        speed=3.2,
        tags=["KENYA", "E-COMMERCE"],
        description="kilimall.co.ke"
    ),
    "whatsapp_kenya": Scraper(
        id="whatsapp_kenya",
        name="WhatsApp Kenya",
        status=ScraperStatus.DISABLED,
        leads=0,
        success_rate=90,
        speed=1.0,
        tags=["KENYA", "DIRECT"],
        description="WhatsApp Business Groups"
    ),
    "telegram_kenya": Scraper(
        id="telegram_kenya",
        name="Telegram Kenya",
        status=ScraperStatus.ENABLED,
        leads=0,
        success_rate=85,
        speed=1.5,
        tags=["KENYA", "FAST"],
        description="Kenyan Telegram Channels"
    ),
    "facebook_kenya": Scraper(
        id="facebook_kenya",
        name="Facebook Kenya",
        status=ScraperStatus.ENABLED,
        leads=0,
        success_rate=70,
        speed=3.5,
        tags=["KENYA", "GROUPS"],
        description="Kenyan FB Marketplace"
    ),
    "tiktok_kenya": Scraper(
        id="tiktok_kenya",
        name="TikTok Kenya",
        status=ScraperStatus.DISABLED,
        leads=0,
        success_rate=50,
        speed=4.0,
        tags=["KENYA", "SOCIAL"],
        description="Kenyan TikTok Content"
    ),
    "instagram_kenya": Scraper(
        id="instagram_kenya",
        name="Instagram Kenya",
        status=ScraperStatus.DISABLED,
        leads=0,
        success_rate=55,
        speed=3.8,
        tags=["KENYA", "SOCIAL"],
        description="Kenyan Instagram Sellers"
    ),
    "youtube_kenya": Scraper(
        id="youtube_kenya",
        name="YouTube Kenya",
        status=ScraperStatus.DISABLED,
        leads=0,
        success_rate=40,
        speed=5.0,
        tags=["KENYA", "VIDEO"],
        description="Kenyan YouTube Channels"
    ),
    "linkedin_kenya": Scraper(
        id="linkedin_kenya",
        name="LinkedIn Kenya",
        status=ScraperStatus.DISABLED,
        leads=0,
        success_rate=75,
        speed=3.0,
        tags=["KENYA", "B2B"],
        description="Kenyan LinkedIn Network"
    )
}

notifications_db: List[Notification] = []

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/", response_class=HTMLResponse)
def landing_page():
    """Landing page - the entry point to Delta 9"""
    try:
        with open("static/landing.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        # Fallback if landing.html doesn't exist
        return generate_landing_page()

@app.get("/api")
def api_root():
    """API info endpoint"""
    return {"message": "Delta 9 Dashboard API", "version": "3.0.0"}

@app.get("/health")
def health():
    """Health check for Railway"""
    return {"status": "ok", "version": "3.0.0"}

@app.get("/api/agents")
def get_agents():
    return {"agents": list(agents_db.values())}

@app.post("/api/agents")
def create_agent(agent_data: dict):
    agent_id = f"agent_{uuid.uuid4().hex[:8]}"
    new_agent = Agent(
        id=agent_id,
        name=agent_data.get("name", "New Agent"),
        query=agent_data.get("query", ""),
        location=agent_data.get("location", "Kenya"),
        status=AgentStatus.ACTIVE,
        total_leads=0,
        high_intent_leads=0,
        last_run=None,
        next_run=(datetime.now() + timedelta(hours=2)).strftime("%d %b, %H:%M"),
        run_interval=agent_data.get("interval", "2h"),
        created_at=datetime.now().isoformat()
    )
    agents_db[agent_id] = new_agent
    return new_agent

@app.delete("/api/agents/{agent_id}")
def delete_agent(agent_id: str):
    if agent_id in agents_db:
        del agents_db[agent_id]
        # Also delete associated leads
        if agent_id in agent_leads_db:
            del agent_leads_db[agent_id]
        return {"success": True}
    raise HTTPException(status_code=404, detail="Agent not found")

@app.post("/api/agents/{agent_id}/run")
def run_agent(agent_id: str):
    """
    Execute an agent to collect leads.
    This runs the agent's query and generates leads.
    """
    import time
    
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent = agents_db[agent_id]
    
    # Only run active agents
    if agent.status != AgentStatus.ACTIVE:
        return {
            "success": False,
            "message": f"Agent is {agent.status}, cannot run",
            "agent_id": agent_id
        }
    
    start_time = time.time()
    
    # Generate leads using the agent's query
    leads = generate_dynamic_leads(agent.query, agent.location)
    
    # Store leads for this agent
    if agent_id not in agent_leads_db:
        agent_leads_db[agent_id] = []
    
    # Add new leads (avoid duplicates by checking IDs)
    existing_ids = {lead["id"] for lead in agent_leads_db[agent_id]}
    new_leads = [lead for lead in leads if lead["id"] not in existing_ids]
    agent_leads_db[agent_id].extend(new_leads)
    
    # Update agent stats
    agent.total_leads = len(agent_leads_db[agent_id])
    agent.high_intent_leads = sum(1 for lead in agent_leads_db[agent_id] 
                                   if lead.get("intent_score", 0) >= 0.8)
    agent.last_run = datetime.now().strftime("%d %b, %H:%M")
    
    # Calculate next run based on interval
    interval_hours = int(agent.run_interval.replace("h", "").replace("d", ""))
    if "d" in agent.run_interval:
        interval_hours *= 24
    next_run_time = datetime.now() + timedelta(hours=interval_hours)
    agent.next_run = next_run_time.strftime("%d %b, %H:%M")
    
    duration = time.time() - start_time
    
    return {
        "success": True,
        "agent_id": agent_id,
        "agent_name": agent.name,
        "leads_found": len(new_leads),
        "total_leads": agent.total_leads,
        "duration_seconds": round(duration, 3),
        "query": agent.query,
        "location": agent.location,
        "leads": new_leads
    }

@app.get("/api/agents/{agent_id}/leads")
def get_agent_leads(agent_id: str):
    """Get all leads collected by an agent"""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    leads = agent_leads_db.get(agent_id, [])
    agent = agents_db[agent_id]
    
    return {
        "agent_id": agent_id,
        "agent_name": agent.name,
        "total_leads": len(leads),
        "high_intent_leads": sum(1 for lead in leads if lead.get("intent_score", 0) >= 0.8),
        "leads": leads
    }

@app.post("/api/agents/{agent_id}/status")
def update_agent_status(agent_id: str, status_data: dict):
    """Update agent status (active/paused)"""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    new_status = status_data.get("status")
    if new_status not in ["active", "paused", "error"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    agents_db[agent_id].status = AgentStatus(new_status)
    return {"success": True, "agent_id": agent_id, "status": new_status}

@app.get("/api/scrapers")
def get_scrapers():
    return {"scrapers": list(scrapers_db.values())}

@app.post("/api/scrapers/{scraper_id}/toggle")
def toggle_scraper(scraper_id: str):
    if scraper_id in scrapers_db:
        scraper = scrapers_db[scraper_id]
        scraper.status = ScraperStatus.DISABLED if scraper.status == ScraperStatus.ENABLED else ScraperStatus.ENABLED
        return scraper
    raise HTTPException(status_code=404, detail="Scraper not found")

@app.post("/api/search")
def search_endpoint(request: SearchRequest):
    """
    Dynamic search endpoint - generates leads for ANY query.
    """
    import time
    start_time = time.time()
    
    # Generate dynamic leads based on the query
    leads = generate_dynamic_leads(request.query, request.location)
    
    # Calculate duration
    duration = time.time() - start_time
    
    return SearchResponse(
        mode="fully_dynamic",
        results=leads,
        count=len(leads),
        duration_seconds=round(duration, 3),
        query=request.query,
        location=request.location
    )

@app.get("/api/notifications")
def get_notifications():
    return {"notifications": notifications_db}

@app.post("/api/notifications/test")
def test_notification():
    notif = Notification(
        id=str(uuid.uuid4()),
        title="HOT Lead Detected!",
        message="New buyer looking for tires in Nairobi - Budget 50k",
        type="hot",
        timestamp=datetime.now().isoformat(),
        read=False
    )
    notifications_db.insert(0, notif)
    return notif

# ============================================================================
# LANDING PAGE GENERATOR (Fallback)
# ============================================================================

def generate_landing_page():
    """Generate the landing page HTML inline as fallback"""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Delta 9 - AI Buyer Discovery Engine</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg-primary: #0f172a;
            --accent-gold: #fbbf24;
            --accent-cyan: #06b6d4;
            --text-primary: #ffffff;
            --text-secondary: #94a3b8;
        }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-primary);
            min-height: 100vh;
            overflow: hidden;
            position: relative;
        }
        .bg-effects {
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            pointer-events: none;
            z-index: 0;
        }
        .radar-container {
            position: absolute;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            width: 800px; height: 800px;
        }
        .radar-circle {
            position: absolute;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            border: 1px solid rgba(6, 182, 212, 0.1);
            border-radius: 50%;
            animation: pulse-ring 4s ease-out infinite;
        }
        .radar-circle:nth-child(1) { width: 200px; height: 200px; animation-delay: 0s; }
        .radar-circle:nth-child(2) { width: 400px; height: 400px; animation-delay: 1s; }
        .radar-circle:nth-child(3) { width: 600px; height: 600px; animation-delay: 2s; }
        .radar-circle:nth-child(4) { width: 800px; height: 800px; animation-delay: 3s; }
        @keyframes pulse-ring {
            0% { transform: translate(-50%, -50%) scale(0.8); opacity: 1; border-color: rgba(6, 182, 212, 0.3); }
            100% { transform: translate(-50%, -50%) scale(1.2); opacity: 0; border-color: rgba(6, 182, 212, 0); }
        }
        .radar-sweep {
            position: absolute;
            top: 50%; left: 50%;
            width: 400px; height: 400px;
            transform: translate(-50%, -50%);
            background: conic-gradient(from 0deg, transparent 0deg, rgba(6, 182, 212, 0.1) 30deg, rgba(6, 182, 212, 0.3) 60deg, transparent 90deg);
            border-radius: 50%;
            animation: radar-spin 4s linear infinite;
        }
        @keyframes radar-spin {
            from { transform: translate(-50%, -50%) rotate(0deg); }
            to { transform: translate(-50%, -50%) rotate(360deg); }
        }
        .network-grid {
            position: absolute;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background-image: linear-gradient(rgba(59, 130, 246, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(59, 130, 246, 0.03) 1px, transparent 1px);
            background-size: 50px 50px;
            animation: grid-move 20s linear infinite;
        }
        @keyframes grid-move {
            0% { transform: perspective(500px) rotateX(60deg) translateY(0); }
            100% { transform: perspective(500px) rotateX(60deg) translateY(50px); }
        }
        .particles {
            position: absolute;
            top: 0; left: 0;
            width: 100%; height: 100%;
        }
        .particle {
            position: absolute;
            width: 4px; height: 4px;
            background: var(--accent-cyan);
            border-radius: 50%;
            box-shadow: 0 0 10px var(--accent-cyan), 0 0 20px var(--accent-cyan);
            animation: float-particle 15s infinite ease-in-out;
        }
        @keyframes float-particle {
            0%, 100% { transform: translateY(100vh) scale(0); opacity: 0; }
            10% { opacity: 1; }
            90% { opacity: 1; }
            100% { transform: translateY(-100px) scale(1); opacity: 0; }
        }
        .landing-container {
            position: relative;
            z-index: 10;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 20px;
        }
        .logo-section {
            text-align: center;
            animation: fade-in-up 1.5s ease-out;
        }
        @keyframes fade-in-up {
            0% { opacity: 0; transform: translateY(30px); }
            100% { opacity: 1; transform: translateY(0); }
        }
        .logo-container {
            position: relative;
            display: inline-block;
            margin-bottom: 30px;
        }
        .logo-glow {
            position: absolute;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            width: 300px; height: 300px;
            background: radial-gradient(circle, rgba(251, 191, 36, 0.2) 0%, transparent 70%);
            border-radius: 50%;
            animation: glow-pulse 3s ease-in-out infinite;
        }
        @keyframes glow-pulse {
            0%, 100% { opacity: 0.5; transform: translate(-50%, -50%) scale(1); }
            50% { opacity: 1; transform: translate(-50%, -50%) scale(1.1); }
        }
        .logo-image {
            width: 280px;
            height: auto;
            filter: drop-shadow(0 0 30px rgba(251, 191, 36, 0.3));
            position: relative;
            z-index: 2;
        }
        .brand-name {
            font-size: 64px;
            font-weight: 900;
            background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 50%, #d97706 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: 4px;
            margin-bottom: 10px;
            text-shadow: 0 0 40px rgba(251, 191, 36, 0.3);
        }
        .brand-tagline {
            font-size: 20px;
            color: var(--text-secondary);
            letter-spacing: 8px;
            text-transform: uppercase;
            margin-bottom: 60px;
        }
        .enter-button {
            position: relative;
            padding: 20px 80px;
            font-size: 24px;
            font-weight: 700;
            letter-spacing: 4px;
            color: var(--bg-primary);
            background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
            border: none;
            border-radius: 50px;
            cursor: pointer;
            text-transform: uppercase;
            transition: all 0.3s ease;
            box-shadow: 0 10px 40px rgba(251, 191, 36, 0.3);
            overflow: hidden;
            animation: fade-in-up 1.5s ease-out 0.5s both;
        }
        .enter-button::before {
            content: '';
            position: absolute;
            top: 0; left: -100%;
            width: 100%; height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
            transition: left 0.5s ease;
        }
        .enter-button:hover::before {
            left: 100%;
        }
        .enter-button:hover {
            transform: translateY(-3px);
            box-shadow: 0 20px 60px rgba(251, 191, 36, 0.4), 0 0 40px rgba(251, 191, 36, 0.2), inset 0 0 20px rgba(255, 255, 255, 0.1);
        }
        .corner-decoration {
            position: fixed;
            width: 200px; height: 200px;
            border: 1px solid rgba(6, 182, 212, 0.2);
            pointer-events: none;
        }
        .corner-decoration.top-left { top: 20px; left: 20px; border-right: none; border-bottom: none; }
        .corner-decoration.top-right { top: 20px; right: 20px; border-left: none; border-bottom: none; }
        .corner-decoration.bottom-left { bottom: 20px; left: 20px; border-right: none; border-top: none; }
        .corner-decoration.bottom-right { bottom: 20px; right: 20px; border-left: none; border-top: none; }
        @media (max-width: 768px) {
            .logo-image { width: 200px; }
            .brand-name { font-size: 42px; }
            .brand-tagline { font-size: 14px; letter-spacing: 4px; }
            .enter-button { padding: 16px 60px; font-size: 18px; }
            .radar-container { width: 400px; height: 400px; }
        }
    </style>
</head>
<body>
    <div class="bg-effects">
        <div class="radar-container">
            <div class="radar-sweep"></div>
            <div class="radar-circle"></div>
            <div class="radar-circle"></div>
            <div class="radar-circle"></div>
            <div class="radar-circle"></div>
        </div>
        <div class="network-grid"></div>
        <div class="particles" id="particles"></div>
    </div>
    <div class="corner-decoration top-left"></div>
    <div class="corner-decoration top-right"></div>
    <div class="corner-decoration bottom-left"></div>
    <div class="corner-decoration bottom-right"></div>
    <div class="landing-container">
        <div class="logo-section">
            <div class="logo-container">
                <div class="logo-glow"></div>
                <svg class="logo-image" viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M100 10 L170 40 L170 100 C170 150 100 190 100 190 C100 190 30 150 30 100 L30 40 Z" fill="url(#shieldGradient)" stroke="#fbbf24" stroke-width="3"/>
                    <path d="M70 60 Q70 30 100 30 Q130 30 130 60 L130 90 L70 90 Z" fill="#1e293b" stroke="#94a3b8" stroke-width="2"/>
                    <rect x="75" y="50" width="50" height="15" rx="3" fill="#0f172a"/>
                    <line x1="80" y1="57" x2="120" y2="57" stroke="#fbbf24" stroke-width="2"/>
                    <path d="M140 40 L160 20 L165 25 L145 45 Z" fill="#94a3b8"/>
                    <rect x="142" y="42" width="4" height="40" fill="#64748b"/>
                    <circle cx="144" cy="85" r="5" fill="#fbbf24"/>
                    <path d="M85 30 Q70 10 60 25 Q65 5 80 15 Q75 0 90 10" stroke="#dc2626" stroke-width="4" fill="none" stroke-linecap="round"/>
                    <text x="100" y="140" text-anchor="middle" fill="#fbbf24" font-size="28" font-weight="900" font-family="Arial, sans-serif" letter-spacing="2">DELTA 9</text>
                    <defs>
                        <linearGradient id="shieldGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" style="stop-color:#1e293b;stop-opacity:1" />
                            <stop offset="100%" style="stop-color:#0f172a;stop-opacity:1" />
                        </linearGradient>
                    </defs>
                </svg>
            </div>
            <h1 class="brand-name">Delta 9</h1>
            <p class="brand-tagline">AI Buyer Discovery Engine</p>
            <button class="enter-button" onclick="enterApp()">Enter</button>
        </div>
    </div>
    <script>
        function createParticles() {
            const container = document.getElementById("particles");
            for (let i = 0; i < 30; i++) {
                const particle = document.createElement("div");
                particle.className = "particle";
                particle.style.left = Math.random() * 100 + "%";
                particle.style.animationDelay = Math.random() * 15 + "s";
                particle.style.animationDuration = (10 + Math.random() * 10) + "s";
                const colors = ["#06b6d4", "#fbbf24", "#3b82f6"];
                particle.style.background = colors[Math.floor(Math.random() * colors.length)];
                container.appendChild(particle);
            }
        }
        function enterApp() {
            document.body.style.transition = "opacity 0.5s ease";
            document.body.style.opacity = "0";
            setTimeout(() => { window.location.href = "/dashboard"; }, 500);
        }
        createParticles();
    </script>
</body>
</html>'''

# ============================================================================
# DASHBOARD UI
# ============================================================================

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    return generate_full_dashboard()

@app.get("/demo", response_class=HTMLResponse)
def demo_redirect():
    return generate_full_dashboard()

def generate_full_dashboard():
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Delta 9 - Lead Intelligence Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        :root {{
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-card: #1a1a25;
            --bg-card-hover: #222230;
            --accent-primary: #00d4aa;
            --accent-secondary: #00a884;
            --accent-blue: #3b82f6;
            --text-primary: #ffffff;
            --text-secondary: #8b8b9a;
            --text-muted: #5a5a6a;
            --border: #2a2a3a;
            --hot: #ef4444;
            --warm: #f59e0b;
            --success: #10b981;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            padding-bottom: 90px;
            line-height: 1.5;
        }}
        
        /* Header */
        .header {{
            background: var(--bg-primary);
            padding: 12px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
            border-bottom: 1px solid var(--border);
        }}
        
        .brand {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .logo {{
            width: 36px;
            height: 36px;
            background: linear-gradient(135deg, #00d4aa, #00a884);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
        }}
        
        .brand-text {{
            font-size: 18px;
            font-weight: 700;
            letter-spacing: -0.5px;
        }}
        
        .live-badge {{
            display: flex;
            align-items: center;
            gap: 6px;
            background: rgba(0, 212, 170, 0.15);
            color: #00d4aa;
            padding: 5px 10px;
            border-radius: 16px;
            font-size: 11px;
            font-weight: 700;
            border: 1px solid rgba(0, 212, 170, 0.3);
            margin-left: 8px;
        }}
        
        .live-badge::before {{
            content: "";
            width: 6px;
            height: 6px;
            background: #00d4aa;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }}
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.4; }}
        }}
        
        .header-actions {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        .notif-btn {{
            position: relative;
            background: none;
            border: none;
            color: var(--text-primary);
            font-size: 22px;
            cursor: pointer;
            padding: 8px;
        }}
        
        .notif-dot {{
            position: absolute;
            top: 6px;
            right: 6px;
            width: 8px;
            height: 8px;
            background: var(--accent-primary);
            border-radius: 50%;
        }}
        
        /* Main Content */
        .content {{
            max-width: 480px;
            margin: 0 auto;
            padding: 16px;
        }}
        
        .view {{
            display: none;
        }}
        
        .view.active {{
            display: block;
        }}
        
        /* Page Headers */
        .page-title {{
            font-size: 24px;
            font-weight: 700;
            text-align: center;
            margin-bottom: 8px;
        }}
        
        .page-subtitle {{
            color: var(--text-secondary);
            font-size: 14px;
            text-align: center;
            margin-bottom: 24px;
        }}
        
        /* Search Section */
        .search-section {{
            margin-bottom: 32px;
        }}
        
        .search-box {{
            display: flex;
            align-items: center;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 4px;
            gap: 4px;
        }}
        
        .search-icon {{
            padding: 12px;
            color: var(--text-muted);
            font-size: 18px;
        }}
        
        .search-input {{
            flex: 1;
            background: transparent;
            border: none;
            padding: 12px 8px;
            color: var(--text-primary);
            font-size: 15px;
            outline: none;
        }}
        
        .search-input::placeholder {{
            color: var(--text-muted);
        }}
        
        .btn-search {{
            background: rgba(0, 212, 170, 0.15);
            color: var(--accent-primary);
            border: none;
            padding: 12px 20px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 14px;
            cursor: pointer;
        }}
        
        .btn-search:hover {{
            background: rgba(0, 212, 170, 0.25);
        }}
        
        /* Section Header */
        .section-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }}
        
        .section-title {{
            font-size: 20px;
            font-weight: 700;
        }}
        
        .section-actions {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        .live-tag {{
            background: rgba(239, 68, 68, 0.15);
            color: var(--hot);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
        }}
        
        .btn-hot {{
            background: rgba(239, 68, 68, 0.15);
            color: var(--hot);
            border: 1px solid rgba(239, 68, 68, 0.3);
            padding: 8px 14px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 12px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        
        /* Agent Cards - Leads View */
        .agent-card {{
            background: var(--bg-card);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 16px;
            border: 1px solid var(--border);
            cursor: pointer;
            transition: all 0.2s;
        }}
        
        .agent-card:hover {{
            border-color: var(--accent-blue);
        }}
        
        .agent-card-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 12px;
        }}
        
        .chevron {{
            color: var(--text-muted);
            font-size: 20px;
        }}
        
        .agent-name-section {{
            flex: 1;
        }}
        
        .agent-name {{
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 4px;
        }}
        
        .agent-meta {{
            display: flex;
            align-items: center;
            gap: 8px;
            color: var(--text-secondary);
            font-size: 14px;
        }}
        
        .dot {{
            color: var(--text-muted);
        }}
        
        .status-active {{
            color: var(--success);
            font-weight: 600;
        }}
        
        .agent-next-run {{
            color: var(--text-secondary);
            font-size: 14px;
            text-align: center;
            margin: 16px 0;
        }}
        
        .agent-leads {{
            text-align: center;
            margin: 20px 0;
        }}
        
        .leads-number {{
            font-size: 56px;
            font-weight: 700;
            color: var(--accent-blue);
            line-height: 1;
        }}
        
        .leads-label {{
            color: var(--text-secondary);
            font-size: 14px;
            margin-top: 4px;
        }}
        
        .btn-export {{
            background: rgba(59, 130, 246, 0.15);
            color: var(--accent-blue);
            border: none;
            padding: 12px 24px;
            border-radius: 10px;
            font-weight: 600;
            font-size: 15px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            width: 100%;
            max-width: 200px;
            margin: 0 auto;
        }}
        
        .btn-export:hover {{
            background: rgba(59, 130, 246, 0.25);
        }}
        
        .agent-card-actions {{
            display: flex;
            gap: 10px;
            justify-content: center;
            align-items: center;
        }}
        
        .btn-delete-small {{
            background: rgba(239, 68, 68, 0.15);
            color: var(--hot);
            border: 1px solid rgba(239, 68, 68, 0.3);
            padding: 10px 14px;
            border-radius: 10px;
            font-size: 16px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .btn-delete-small:hover {{
            background: rgba(239, 68, 68, 0.25);
        }}
        
        /* Agents View */
        .agents-title {{
            text-align: center;
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 4px;
            background: linear-gradient(135deg, #60a5fa, #3b82f6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .agents-subtitle {{
            text-align: center;
            color: var(--text-secondary);
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-bottom: 24px;
        }}
        
        .btn-create-agent {{
            background: var(--accent-blue);
            color: white;
            border: none;
            padding: 16px 32px;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            margin: 0 auto 32px;
            width: 100%;
            max-width: 280px;
        }}
        
        .btn-create-agent:hover {{
            opacity: 0.9;
        }}
        
        /* Agent Actions */
        .agent-actions {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 10px;
            margin: 16px 0;
        }}
        
        .btn-run-agent, .btn-view-leads, .btn-pause-agent {{
            padding: 12px;
            border-radius: 10px;
            border: none;
            font-weight: 600;
            font-size: 13px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
        }}
        
        .btn-run-agent {{
            background: var(--accent-blue);
            color: white;
        }}
        
        .btn-run-agent:hover:not(:disabled) {{
            opacity: 0.9;
        }}
        
        .btn-run-agent:disabled {{
            opacity: 0.6;
            cursor: not-allowed;
        }}
        
        .btn-view-leads {{
            background: var(--bg-secondary);
            color: var(--text-primary);
            border: 1px solid var(--border);
        }}
        
        .btn-view-leads:hover {{
            background: var(--bg-card-hover);
        }}
        
        .btn-pause-agent {{
            background: rgba(245, 158, 11, 0.15);
            color: var(--warm);
            border: 1px solid rgba(245, 158, 11, 0.3);
        }}
        
        .btn-pause-agent:hover {{
            background: rgba(245, 158, 11, 0.25);
        }}
        
        .btn-delete-agent {{
            background: rgba(239, 68, 68, 0.15);
            color: var(--hot);
            border: 1px solid rgba(239, 68, 68, 0.3);
            padding: 12px;
            border-radius: 10px;
            font-weight: 600;
            font-size: 13px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
        }}
        
        .btn-delete-agent:hover {{
            background: rgba(239, 68, 68, 0.25);
        }}
        
        .agent-run-results {{
            margin-top: 16px;
            padding: 16px;
            background: var(--bg-secondary);
            border-radius: 12px;
            border: 1px solid var(--border);
        }}
        
        .run-success {{
            text-align: center;
        }}
        
        .run-success h4 {{
            color: var(--success);
            margin-bottom: 8px;
        }}
        
        .new-leads-preview {{
            margin-top: 12px;
            text-align: left;
        }}
        
        .preview-lead {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px;
            background: var(--bg-card);
            border-radius: 8px;
            margin-bottom: 8px;
            font-size: 13px;
        }}
        
        .preview-title {{
            flex: 1;
            font-weight: 500;
        }}
        
        .preview-phone {{
            color: var(--success);
            font-weight: 600;
        }}
        
        .run-error {{
            color: var(--hot);
            text-align: center;
            padding: 20px;
        }}
        
        .loading {{
            text-align: center;
            color: var(--text-secondary);
            padding: 20px;
        }}
        
        /* Leads Modal */
        .leads-modal-list {{
            max-height: 60vh;
            overflow-y: auto;
        }}
        
        .lead-card-modal {{
            background: var(--bg-card);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
            border: 1px solid var(--border);
        }}
        
        /* Agent Detail Card */
        .agent-detail-card {{
            background: var(--bg-card);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 16px;
            border: 1px solid var(--border);
        }}
        
        .agent-detail-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 16px;
        }}
        
        .agent-detail-name {{
            font-size: 22px;
            font-weight: 700;
        }}
        
        .badge-active {{
            background: rgba(16, 185, 129, 0.2);
            color: var(--success);
            padding: 4px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
        }}
        
        .agent-detail-query {{
            color: var(--text-secondary);
            font-size: 14px;
            margin-bottom: 20px;
        }}
        
        .agent-detail-query span {{
            color: var(--accent-blue);
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 16px;
        }}
        
        .stat-item {{
            text-align: center;
        }}
        
        .stat-label {{
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }}
        
        .stat-value {{
            font-size: 36px;
            font-weight: 700;
        }}
        
        .stat-value.green {{
            color: var(--success);
        }}
        
        .run-times {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            text-align: center;
            padding-top: 16px;
            border-top: 1px solid var(--border);
        }}
        
        .run-time-label {{
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 6px;
        }}
        
        .run-time-value {{
            font-size: 16px;
            color: var(--accent-blue);
            font-weight: 600;
        }}
        
        .run-interval {{
            text-align: center;
            color: var(--text-muted);
            font-size: 13px;
            margin-top: 16px;
            padding-top: 16px;
            border-top: 1px solid var(--border);
        }}
        
        /* Scraper Categories */
        .scraper-categories {{
            display: flex;
            gap: 8px;
            margin-bottom: 20px;
            overflow-x: auto;
            padding-bottom: 8px;
        }}
        
        .category-tab {{
            padding: 10px 16px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            background: var(--bg-card);
            color: var(--text-secondary);
            border: 1px solid var(--border);
            white-space: nowrap;
        }}
        
        .category-tab.active {{
            background: var(--accent-blue);
            color: white;
            border-color: var(--accent-blue);
        }}
        
        /* Scraper Section Headers */
        .scraper-section {{
            margin-bottom: 24px;
        }}
        
        .scraper-section-title {{
            font-size: 14px;
            font-weight: 700;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .scraper-count-inline {{
            background: var(--bg-card);
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 11px;
        }}
        
        /* Config View */
        .config-title {{
            text-align: center;
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 8px;
        }}
        
        .config-subtitle {{
            text-align: center;
            color: var(--text-secondary);
            font-size: 14px;
            margin-bottom: 24px;
        }}
        
        .scraper-count {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            margin-bottom: 24px;
        }}
        
        .scraper-count-badge {{
            background: var(--bg-card);
            padding: 8px 20px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            color: var(--text-secondary);
        }}
        
        /* Scraper Cards */
        .scraper-card {{
            background: var(--bg-card);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 16px;
            border: 1px solid var(--border);
        }}
        
        .scraper-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 16px;
        }}
        
        .scraper-info {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .scraper-name {{
            font-size: 18px;
            font-weight: 700;
            color: #4a5568;
        }}
        
        .shield-icon {{
            color: var(--accent-blue);
            font-size: 16px;
        }}
        
        .scraper-tags {{
            display: flex;
            gap: 8px;
            margin-top: 8px;
        }}
        
        .tag {{
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
        }}
        
        .tag-free {{
            background: rgba(16, 185, 129, 0.15);
            color: var(--success);
        }}
        
        .tag-low-noise {{
            background: rgba(139, 139, 154, 0.15);
            color: var(--text-secondary);
        }}
        
        .tag-kenya {{
            background: rgba(0, 212, 170, 0.15);
            color: var(--accent-primary);
        }}
        
        .tag-high-intent {{
            background: rgba(239, 68, 68, 0.15);
            color: var(--hot);
        }}
        
        .tag-real-estate {{
            background: rgba(59, 130, 246, 0.15);
            color: var(--accent-blue);
        }}
        
        .tag-vehicles {{
            background: rgba(245, 158, 11, 0.15);
            color: var(--warm);
        }}
        
        .tag-e-commerce {{
            background: rgba(168, 85, 247, 0.15);
            color: #a855f7;
        }}
        
        .tag-b2b {{
            background: rgba(6, 182, 212, 0.15);
            color: #06b6d4;
        }}
        
        .tag-premium {{
            background: linear-gradient(135deg, rgba(245, 158, 11, 0.2), rgba(251, 191, 36, 0.2));
            color: #fbbf24;
        }}
        
        .toggle-switch {{
            width: 52px;
            height: 28px;
            background: var(--text-muted);
            border-radius: 14px;
            position: relative;
            cursor: pointer;
            transition: background 0.3s;
        }}
        
        .toggle-switch.enabled {{
            background: var(--accent-blue);
        }}
        
        .toggle-knob {{
            width: 24px;
            height: 24px;
            background: white;
            border-radius: 50%;
            position: absolute;
            top: 2px;
            left: 2px;
            transition: transform 0.3s;
        }}
        
        .toggle-switch.enabled .toggle-knob {{
            transform: translateX(24px);
        }}
        
        .scraper-stats {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            padding-top: 16px;
            border-top: 1px solid var(--border);
        }}
        
        .scraper-stat {{
            text-align: center;
        }}
        
        .scraper-stat-label {{
            font-size: 10px;
            color: var(--text-muted);
            text-transform: uppercase;
            margin-bottom: 4px;
        }}
        
        .scraper-stat-value {{
            font-size: 20px;
            font-weight: 700;
            color: var(--success);
        }}
        
        /* Live Feed */
        .feed-card {{
            background: var(--bg-card);
            border-radius: 16px;
            padding: 20px;
            border: 1px solid var(--border);
        }}
        
        .feed-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 16px;
        }}
        
        .feed-icon {{
            width: 40px;
            height: 40px;
            background: rgba(0, 212, 170, 0.15);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
        }}
        
        .feed-title-section {{
            flex: 1;
        }}
        
        .feed-title {{
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 2px;
        }}
        
        .feed-subtitle {{
            font-size: 12px;
            color: var(--text-secondary);
        }}
        
        .feed-signals {{
            display: flex;
            align-items: center;
            gap: 8px;
            color: var(--text-muted);
            font-size: 14px;
        }}
        
        .filter-tabs {{
            display: flex;
            gap: 8px;
            margin-bottom: 16px;
            flex-wrap: wrap;
        }}
        
        .filter-tab {{
            padding: 8px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            background: var(--bg-secondary);
            color: var(--text-secondary);
            border: none;
        }}
        
        .filter-tab.active {{
            background: rgba(255, 255, 255, 0.1);
            color: var(--text-primary);
        }}
        
        /* Bottom Navigation */
        .bottom-nav {{
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: var(--bg-secondary);
            border-top: 1px solid var(--border);
            display: flex;
            justify-content: space-around;
            padding: 8px 0 20px;
            z-index: 100;
        }}
        
        .nav-item {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
            padding: 8px 16px;
            cursor: pointer;
            color: var(--text-muted);
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border: none;
            background: none;
        }}
        
        .nav-item.active {{
            color: var(--accent-blue);
        }}
        
        .nav-icon {{
            width: 44px;
            height: 44px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            transition: all 0.2s;
        }}
        
        .nav-item.active .nav-icon {{
            background: rgba(59, 130, 246, 0.15);
        }}
        
        /* Search Results */
        .search-results {{
            margin-top: 24px;
            animation: fadeIn 0.3s ease;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .results-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            padding: 0 4px;
        }}
        
        .results-header h3 {{
            font-size: 18px;
            font-weight: 700;
        }}
        
        .results-time {{
            color: var(--text-muted);
            font-size: 13px;
        }}
        
        .leads-list {{
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}
        
        .lead-card {{
            background: var(--bg-card);
            border-radius: 16px;
            padding: 16px;
            border: 1px solid var(--border);
            transition: all 0.2s;
        }}
        
        .lead-card:hover {{
            border-color: var(--accent-blue);
            transform: translateY(-2px);
        }}
        
        .lead-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        
        .lead-badge {{
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
        }}
        
        .badge-hot {{
            background: rgba(239, 68, 68, 0.15);
            color: var(--hot);
        }}
        
        .badge-warm {{
            background: rgba(245, 158, 11, 0.15);
            color: var(--warm);
        }}
        
        .badge-cold {{
            background: rgba(59, 130, 246, 0.15);
            color: var(--accent-blue);
        }}
        
        .lead-intent {{
            font-size: 12px;
            color: var(--text-muted);
            font-weight: 600;
        }}
        
        .lead-title {{
            font-size: 15px;
            font-weight: 600;
            margin-bottom: 8px;
            line-height: 1.4;
        }}
        
        .lead-snippet {{
            font-size: 13px;
            color: var(--text-secondary);
            line-height: 1.5;
            margin-bottom: 12px;
        }}
        
        .lead-footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-top: 12px;
            border-top: 1px solid var(--border);
        }}
        
        .lead-phone {{
            font-size: 13px;
            color: var(--success);
            font-weight: 600;
        }}
        
        .lead-location {{
            font-size: 12px;
            color: var(--text-muted);
        }}
        
        /* Modal */
        .modal-overlay {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.8);
            z-index: 200;
            align-items: flex-end;
            justify-content: center;
        }}
        
        .modal-overlay.active {{
            display: flex;
        }}
        
        .modal {{
            background: var(--bg-card);
            border-radius: 24px 24px 0 0;
            padding: 24px;
            width: 100%;
            max-width: 480px;
            max-height: 85vh;
            overflow-y: auto;
            animation: slideUp 0.3s ease;
        }}
        
        @keyframes slideUp {{
            from {{ transform: translateY(100%); }}
            to {{ transform: translateY(0); }}
        }}
        
        .modal-title {{
            font-size: 22px;
            font-weight: 700;
            margin-bottom: 24px;
            text-align: center;
        }}
        
        .form-group {{
            margin-bottom: 20px;
        }}
        
        .form-label {{
            display: block;
            font-size: 13px;
            font-weight: 600;
            margin-bottom: 8px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .form-input, .form-select {{
            width: 100%;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px;
            color: var(--text-primary);
            font-size: 16px;
            outline: none;
        }}
        
        .form-input:focus, .form-select:focus {{
            border-color: var(--accent-blue);
        }}
        
        .modal-actions {{
            display: flex;
            gap: 12px;
            margin-top: 24px;
        }}
        
        .btn-cancel {{
            flex: 1;
            background: transparent;
            color: var(--text-secondary);
            border: 1px solid var(--border);
            padding: 16px;
            border-radius: 12px;
            font-weight: 600;
            cursor: pointer;
        }}
        
        .btn-primary {{
            flex: 2;
            background: var(--accent-blue);
            color: white;
            border: none;
            padding: 16px;
            border-radius: 12px;
            font-weight: 600;
            cursor: pointer;
        }}
        
        /* Empty State */
        .empty-state {{
            text-align: center;
            padding: 60px 20px;
            color: var(--text-muted);
        }}
        
        .empty-icon {{
            font-size: 48px;
            margin-bottom: 16px;
        }}
        
        .empty-text {{
            font-size: 16px;
            margin-bottom: 8px;
            color: var(--text-secondary);
        }}
        
        /* Timestamp */
        .timestamp {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            color: var(--text-secondary);
            font-size: 14px;
            margin-bottom: 20px;
        }}
        
        .refresh-btn {{
            background: none;
            border: none;
            color: var(--text-secondary);
            font-size: 18px;
            cursor: pointer;
            padding: 4px;
        }}
        
        .notif-bell {{
            background: none;
            border: none;
            color: #fbbf24;
            font-size: 20px;
            cursor: pointer;
            padding: 4px;
        }}
    </style>
</head>
<body>
    <!-- Header -->
    <header class="header">
        <div class="brand">
            <div class="logo">📊</div>
            <span class="brand-text">Delta 9</span>
            <div class="live-badge">LIVE</div>
        </div>
        <div class="header-actions">
            <button class="notif-btn" onclick="testNotification()">
                🔔
                <span class="notif-dot" id="notifDot" style="display: none;"></span>
            </button>
        </div>
    </header>

    <!-- Main Content -->
    <div class="content">
        <!-- HOME VIEW -->
        <div class="view active" id="homeView">
            <h1 class="page-title">Find <span style="color: var(--accent-primary);">Buyers</span> For Anything</h1>
            <p class="page-subtitle">Search for what you're selling. We'll find people actively looking to buy it.</p>
            
            <div class="search-section">
                <div class="search-box">
                    <span class="search-icon">🔍</span>
                    <input type="text" class="search-input" id="homeSearchInput" placeholder="What are you selling?">
                    <button class="btn-search" onclick="searchFromHome()">Find Buyers</button>
                </div>
            </div>
            
            <div class="section-header">
                <div>
                    <h2 class="section-title">Real-Time Buyer Feed</h2>
                </div>
                <div class="section-actions">
                    <span class="live-tag">LIVE</span>
                    <button class="btn-hot" onclick="testNotification()">🔔 Test HOT Notification</button>
                </div>
            </div>
            
            <div class="feed-card">
                <div class="feed-header">
                    <div class="feed-icon">📡</div>
                    <div class="feed-title-section">
                        <div class="feed-title">Live Buyer Feed</div>
                        <div class="feed-subtitle">Monitoring Telegram groups in real-time</div>
                    </div>
                    <div class="feed-signals">
                        <span>⏸️</span>
                        <span>0 signals</span>
                    </div>
                </div>
                
                <div class="filter-tabs">
                    <button class="filter-tab active">All (0)</button>
                    <button class="filter-tab">🔥 Hot (0)</button>
                    <button class="filter-tab">⭐ Warm+ (0)</button>
                    <button class="filter-tab">📞 With Phone (0)</button>
                </div>
                
                <div class="empty-state">
                    <div class="empty-icon">⚡</div>
                    <div class="empty-text">Waiting for signals...</div>
                </div>
            </div>
        </div>

        <!-- LEADS VIEW -->
        <div class="view" id="leadsView">
            <h1 class="page-title">Lead Intelligence Dashboard</h1>
            <p class="page-subtitle">Real-time monitoring of agent activities and incoming leads</p>
            
            <div class="timestamp">
                <span>Last updated: <span id="lastUpdated">{datetime.now().strftime("%I:%M:%S %p")}</span></span>
                <button class="refresh-btn" onclick="refreshAgents()">🔄</button>
                <button class="notif-bell" onclick="testNotification()">🔔</button>
            </div>
            
            <div id="leadsAgentList">
                <!-- Agent cards will be loaded here -->
            </div>
        </div>

        <!-- AGENTS VIEW -->
        <div class="view" id="agentsView">
            <h1 class="agents-title">24/7 Demand Radar Agents</h1>
            <p class="agents-subtitle">Autonomous 24/7 Intelligence Agents</p>
            
            <button class="btn-create-agent" onclick="openCreateAgentModal()">
                <span>+</span> Create Agent
            </button>
            
            <div id="agentsDetailList">
                <!-- Agent details will be loaded here -->
            </div>
        </div>

        <!-- CONFIG VIEW -->
        <div class="view" id="configView">
            <h1 class="config-title">⚡ Signal Scrapers</h1>
            <p class="config-subtitle">Configure data sources and scraper settings</p>
            
            <div class="scraper-count">
                <span class="scraper-count-badge">🔥 {len(scrapers_db)} Sources Available</span>
            </div>
            
            <div class="scraper-categories">
                <button class="category-tab active" onclick="filterScrapers('all')">All</button>
                <button class="category-tab" onclick="filterScrapers('kenya')">🇰🇪 Kenya</button>
                <button class="category-tab" onclick="filterScrapers('global')">🌍 Global</button>
                <button class="category-tab" onclick="filterScrapers('social')">💬 Social</button>
            </div>
            
            <div id="scrapersList">
                <!-- Scrapers will be loaded here -->
            </div>
        </div>
    </div>

    <!-- Create Agent Modal -->
    <div class="modal-overlay" id="createAgentModal">
        <div class="modal">
            <h2 class="modal-title">Create New Agent</h2>
            <div class="form-group">
                <label class="form-label">Agent Name</label>
                <input type="text" class="form-input" id="agentName" placeholder="e.g., House, Solar Panels">
            </div>
            <div class="form-group">
                <label class="form-label">Search Query</label>
                <input type="text" class="form-input" id="agentQuery" placeholder="e.g., apartments, houses, land">
            </div>
            <div class="form-group">
                <label class="form-label">Location</label>
                <input type="text" class="form-input" id="agentLocation" value="Kenya">
            </div>
            <div class="form-group">
                <label class="form-label">Run Interval</label>
                <select class="form-select" id="agentInterval">
                    <option value="1h">Every 1 hour</option>
                    <option value="2h" selected>Every 2 hours</option>
                    <option value="6h">Every 6 hours</option>
                    <option value="1d">Daily</option>
                </select>
            </div>
            <div class="modal-actions">
                <button class="btn-cancel" onclick="closeModal()">Cancel</button>
                <button class="btn-primary" onclick="createAgent()">Create Agent</button>
            </div>
        </div>
    </div>

    <!-- Bottom Navigation -->
    <nav class="bottom-nav">
        <button class="nav-item active" onclick="switchView('home')">
            <div class="nav-icon">🏠</div>
            <span>Home</span>
        </button>
        <button class="nav-item" onclick="switchView('leads')">
            <div class="nav-icon">📋</div>
            <span>Leads</span>
        </button>
        <button class="nav-item" onclick="switchView('agents')">
            <div class="nav-icon">🕵️</div>
            <span>Agents</span>
        </button>
        <button class="nav-item" onclick="switchView('config')">
            <div class="nav-icon">⚙️</div>
            <span>Config</span>
        </button>
    </nav>

    <script>
        let agents = {json.dumps([a.dict() for a in agents_db.values()])};
        let scrapers = {json.dumps([s.dict() for s in scrapers_db.values()])};
        let currentView = 'home';

        document.addEventListener('DOMContentLoaded', () => {{
            loadAgents();
            renderConfigView();
        }});
        
        async function loadAgents() {{
            try {{
                const response = await fetch('/api/agents');
                const data = await response.json();
                agents = data.agents;
                renderLeadsView();
                renderAgentsView();
            }} catch (err) {{
                console.error('Failed to load agents:', err);
            }}
        }}
        
        async function loadScrapers() {{
            try {{
                const response = await fetch('/api/scrapers');
                const data = await response.json();
                scrapers = data.scrapers;
                renderConfigView();
            }} catch (err) {{
                console.error('Failed to load scrapers:', err);
            }}
        }}

        function switchView(view) {{
            document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            
            document.getElementById(view + 'View').classList.add('active');
            const navItems = document.querySelectorAll('.nav-item');
            const viewIndex = ['home', 'leads', 'agents', 'config'].indexOf(view);
            if (navItems[viewIndex]) navItems[viewIndex].classList.add('active');
            
            currentView = view;
            
            // Refresh data when switching views
            if (view === 'agents' || view === 'leads') {{
                loadAgents();
            }} else if (view === 'config') {{
                loadScrapers();
            }}
        }}

        function renderLeadsView() {{
            const container = document.getElementById('leadsAgentList');
            if (!agents.length) {{
                container.innerHTML = '<div class="empty-state"><div class="empty-icon">📋</div><div class="empty-text">No agents yet</div></div>';
                return;
            }}
            
            container.innerHTML = agents.map(agent => `
                <div class="agent-card" onclick="viewAgentDetails('${{agent.id}}')">
                    <div class="agent-card-header">
                        <span class="chevron">›</span>
                        <div class="agent-name-section">
                            <div class="agent-name">${{agent.name}}</div>
                            <div class="agent-meta">
                                Query: "${{agent.query}}" 
                                <span class="dot">•</span> 
                                <span class="status-active">Active</span>
                                <span class="dot">•</span>
                            </div>
                        </div>
                    </div>
                    <div class="agent-next-run">Next Run: ${{agent.next_run || 'Not scheduled'}}</div>
                    <div class="agent-leads">
                        <div class="leads-number">${{agent.total_leads}}</div>
                        <div class="leads-label">Total Leads</div>
                    </div>
                    <div class="agent-card-actions">
                        <button class="btn-export" onclick="event.stopPropagation(); exportAgent('${{agent.id}}')">
                            ⬇️ Export
                        </button>
                        <button class="btn-delete-small" onclick="event.stopPropagation(); deleteAgent('${{agent.id}}')">
                            🗑️
                        </button>
                    </div>
                </div>
            `).join('');
        }}

        function renderAgentsView() {{
            const container = document.getElementById('agentsDetailList');
            if (!agents.length) {{
                container.innerHTML = '<div class="empty-state"><div class="empty-icon">🕵️</div><div class="empty-text">Create your first agent</div></div>';
                return;
            }}
            
            container.innerHTML = agents.map(agent => `
                <div class="agent-detail-card" id="agent-card-${{agent.id}}">
                    <div class="agent-detail-header">
                        <span class="agent-detail-name">${{agent.name}}</span>
                        <span class="badge-active">${{agent.status.toUpperCase()}}</span>
                    </div>
                    <div class="agent-detail-query">
                        Query: "<span>${{agent.query}}</span>" • ${{agent.location}}
                    </div>
                    <div class="stats-grid">
                        <div class="stat-item">
                            <div class="stat-label">Total Leads</div>
                            <div class="stat-value" id="agent-leads-${{agent.id}}">${{agent.total_leads}}</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">High Intent</div>
                            <div class="stat-value green" id="agent-hot-${{agent.id}}">${{agent.high_intent_leads}}</div>
                        </div>
                    </div>
                    <div class="run-times">
                        <div>
                            <div class="run-time-label">Next Run</div>
                            <div class="run-time-value" id="agent-next-${{agent.id}}">${{agent.next_run || 'Pending'}}</div>
                        </div>
                        <div>
                            <div class="run-time-label">Last Run</div>
                            <div class="run-time-value" style="color: var(--text-primary);" id="agent-last-${{agent.id}}">${{agent.last_run || 'Never'}}</div>
                        </div>
                    </div>
                    <div class="agent-actions">
                        <button class="btn-run-agent" onclick="runAgentNow('${{agent.id}}')" id="btn-run-${{agent.id}}">
                            ▶️ Run Now
                        </button>
                        <button class="btn-view-leads" onclick="viewAgentLeads('${{agent.id}}')">
                            👁️ View Leads
                        </button>
                        <button class="btn-pause-agent" onclick="toggleAgentStatus('${{agent.id}}')" id="btn-status-${{agent.id}}">
                            ${{agent.status === 'active' ? '⏸️ Pause' : '▶️ Resume'}}
                        </button>
                        <button class="btn-delete-agent" onclick="deleteAgent('${{agent.id}}')">
                            🗑️ Delete
                        </button>
                    </div>
                    <div class="run-interval">Runs every ${{agent.run_interval}} for 7 days</div>
                    <div id="agent-results-${{agent.id}}" class="agent-run-results" style="display:none;"></div>
                </div>
            `).join('');
        }}
        
        async function runAgentNow(agentId) {{
            const btn = document.getElementById(`btn-run-${{agentId}}`);
            const resultsDiv = document.getElementById(`agent-results-${{agentId}}`);
            
            btn.disabled = true;
            btn.innerHTML = '🔄 Running...';
            resultsDiv.style.display = 'block';
            resultsDiv.innerHTML = '<div class="loading">Searching for leads...</div>';
            
            try {{
                const response = await fetch(`/api/agents/${{agentId}}/run`, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}}
                }});
                
                const data = await response.json();
                
                if (data.success) {{
                    // Update agent stats in UI
                    document.getElementById(`agent-leads-${{agentId}}`).textContent = data.total_leads;
                    document.getElementById(`agent-last-${{agentId}}`).textContent = data.agent.last_run || 'Just now';
                    document.getElementById(`agent-next-${{agentId}}`).textContent = data.agent.next_run;
                    
                    // Find and update high intent count
                    const hotCount = data.leads.filter(l => l.badge === 'HOT').length;
                    const currentHot = parseInt(document.getElementById(`agent-hot-${{agentId}}`).textContent);
                    document.getElementById(`agent-hot-${{agentId}}`).textContent = currentHot + hotCount;
                    
                    // Show results
                    resultsDiv.innerHTML = `
                        <div class="run-success">
                            <h4>✅ Run Complete!</h4>
                            <p>Found <strong>${{data.leads_found}}</strong> new leads in ${{data.duration_seconds}}s</p>
                            <div class="new-leads-preview">
                                ${{data.leads.map(lead => `
                                    <div class="preview-lead ${{lead.badge.toLowerCase()}}">
                                        <span class="badge-${{lead.badge.toLowerCase()}}">${{lead.badge}}</span>
                                        <span class="preview-title">${{lead.title}}</span>
                                        <span class="preview-phone">📞 ${{lead.contact_phone}}</span>
                                    </div>
                                `).join('')}}
                            </div>
                        </div>
                    `;
                    
                    // Also update the leads view if visible
                    if (currentView === 'leads') {{
                        renderLeadsView();
                    }}
                }} else {{
                    resultsDiv.innerHTML = `<div class="run-error">⚠️ ${{data.message}}</div>`;
                }}
            }} catch (err) {{
                console.error('Run agent error:', err);
                resultsDiv.innerHTML = '<div class="run-error">❌ Network error. Please try again.</div>';
            }} finally {{
                btn.disabled = false;
                btn.innerHTML = '▶️ Run Now';
            }}
        }}
        
        async function viewAgentLeads(agentId) {{
            try {{
                const response = await fetch(`/api/agents/${{agentId}}/leads`);
                const data = await response.json();
                
                if (data.leads.length === 0) {{
                    alert('No leads yet. Run the agent first!');
                    return;
                }}
                
                // Create a modal to display leads
                const modalHtml = `
                    <div class="modal-overlay active" id="leadsModal" onclick="if(event.target.id==='leadsModal')closeLeadsModal()">
                        <div class="modal" style="max-height: 80vh; overflow-y: auto;">
                            <h2 class="modal-title">${{data.agent_name}} - ${{data.total_leads}} Leads</h2>
                            <div class="leads-modal-list">
                                ${{data.leads.map(lead => `
                                    <div class="lead-card-modal">
                                        <div class="lead-header">
                                            <span class="lead-badge badge-${{lead.badge.toLowerCase()}}">${{lead.badge}}</span>
                                            <span class="lead-intent">${{(lead.intent_score * 100).toFixed(0)}}% Intent</span>
                                        </div>
                                        <h4 class="lead-title">${{lead.title}}</h4>
                                        <p class="lead-snippet">${{lead.buyer_request_snippet}}</p>
                                        <div class="lead-footer">
                                            <span class="lead-phone">📞 ${{lead.contact_phone}}</span>
                                            <span class="lead-location">📍 ${{lead.location}}</span>
                                        </div>
                                    </div>
                                `).join('')}}
                            </div>
                            <button class="btn-primary" style="margin-top: 20px; width: 100%;" onclick="closeLeadsModal()">Close</button>
                        </div>
                    </div>
                `;
                
                document.body.insertAdjacentHTML('beforeend', modalHtml);
            }} catch (err) {{
                console.error('View leads error:', err);
                alert('Failed to load leads');
            }}
        }}
        
        function closeLeadsModal() {{
            const modal = document.getElementById('leadsModal');
            if (modal) modal.remove();
        }}
        
        async function toggleAgentStatus(agentId) {{
            const agent = agents.find(a => a.id === agentId);
            if (!agent) return;
            
            const newStatus = agent.status === 'active' ? 'paused' : 'active';
            
            try {{
                const response = await fetch(`/api/agents/${{agentId}}/status`, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{status: newStatus}})
                }});
                
                if (response.ok) {{
                    agent.status = newStatus;
                    renderAgentsView();
                    if (currentView === 'leads') renderLeadsView();
                }}
            }} catch (err) {{
                console.error('Toggle status error:', err);
                alert('Failed to update status');
            }}
        }}
        
        async function deleteAgent(agentId) {{
            const agent = agents.find(a => a.id === agentId);
            if (!agent) return;
            
            // Confirm deletion
            const confirmDelete = confirm(`Are you sure you want to delete "${{agent.name}}"?\n\nThis will permanently remove the agent and all ${{agent.total_leads}} collected leads.`);
            if (!confirmDelete) return;
            
            try {{
                const response = await fetch(`/api/agents/${{agentId}}`, {{
                    method: 'DELETE'
                }});
                
                if (response.ok) {{
                    // Remove from local array
                    agents = agents.filter(a => a.id !== agentId);
                    
                    // Re-render views
                    renderAgentsView();
                    if (currentView === 'leads') renderLeadsView();
                    
                    alert(`Agent "${{agent.name}}" deleted successfully.`);
                }} else {{
                    alert('Failed to delete agent. Please try again.');
                }}
            }} catch (err) {{
                console.error('Delete agent error:', err);
                alert('Network error. Please try again.');
            }}
        }}

        function renderConfigView(filter = 'all') {{
            const container = document.getElementById('scrapersList');
            
            let filteredScrapers = scrapers;
            if (filter === 'kenya') {{
                filteredScrapers = scrapers.filter(s => s.tags.some(t => t.includes('KENYA')));
            }} else if (filter === 'global') {{
                filteredScrapers = scrapers.filter(s => !s.tags.some(t => t.includes('KENYA')));
            }} else if (filter === 'social') {{
                filteredScrapers = scrapers.filter(s => s.tags.some(t => ['SOCIAL', 'GROUPS', 'DIRECT', 'FAST'].includes(t)));
            }}
            
            // Group by category
            const globalScrapers = filteredScrapers.filter(s => !s.tags.some(t => t.includes('KENYA')));
            const kenyaScrapers = filteredScrapers.filter(s => s.tags.some(t => t.includes('KENYA')));
            
            let html = '';
            
            if (filter === 'all' || filter === 'kenya') {{
                if (kenyaScrapers.length > 0) {{
                    html += createScraperSection('🇰🇪 Kenyan Market Sources', kenyaScrapers);
                }}
            }}
            
            if (filter === 'all' || filter === 'global') {{
                if (globalScrapers.length > 0) {{
                    html += createScraperSection('🌍 Global Sources', globalScrapers);
                }}
            }}
            
            container.innerHTML = html || '<div class="empty-state"><div class="empty-icon">🔧</div><div class="empty-text">No scrapers in this category</div></div>';
        }}
        
        function createScraperSection(title, scraperList) {{
            return `
                <div class="scraper-section">
                    <div class="scraper-section-title">
                        ${{title}}
                        <span class="scraper-count-inline">${{scraperList.length}}</span>
                    </div>
                    ${{scraperList.map(scraper => createScraperCard(scraper)).join('')}}
                </div>
            `;
        }}
        
        function createScraperCard(scraper) {{
            return `
                <div class="scraper-card">
                    <div class="scraper-header">
                        <div>
                            <div class="scraper-info">
                                <span class="scraper-name">${{scraper.name}}</span>
                                <span class="shield-icon">🛡️</span>
                            </div>
                            <div class="scraper-tags">
                                ${{scraper.tags.map(tag => `<span class="tag tag-${{tag.toLowerCase().replace(/\\s+/g, '-')}}">${{tag}}</span>`).join('')}}
                            </div>
                        </div>
                        <div class="toggle-switch ${{scraper.status === 'enabled' ? 'enabled' : ''}}" onclick="toggleScraper('${{scraper.id}}')">
                            <div class="toggle-knob"></div>
                        </div>
                    </div>
                    <div class="scraper-stats">
                        <div class="scraper-stat">
                            <div class="scraper-stat-label">Leads</div>
                            <div style="font-size: 20px; color: var(--text-secondary);">${{scraper.leads}}</div>
                        </div>
                        <div class="scraper-stat">
                            <div class="scraper-stat-label">Success</div>
                            <div class="scraper-stat-value">${{scraper.success_rate}}%</div>
                        </div>
                        <div class="scraper-stat">
                            <div class="scraper-stat-label">Speed</div>
                            <div style="font-size: 20px; color: var(--accent-blue);">${{scraper.speed.toFixed(2)}}s</div>
                        </div>
                    </div>
                </div>
            `;
        }}
        
        function filterScrapers(category) {{
            document.querySelectorAll('.category-tab').forEach(tab => tab.classList.remove('active'));
            event.target.classList.add('active');
            renderConfigView(category);
        }}

        function openCreateAgentModal() {{
            document.getElementById('createAgentModal').classList.add('active');
        }}

        function closeModal() {{
            document.getElementById('createAgentModal').classList.remove('active');
        }}

        async function createAgent() {{
            const name = document.getElementById('agentName').value;
            const query = document.getElementById('agentQuery').value;
            const location = document.getElementById('agentLocation').value;
            const interval = document.getElementById('agentInterval').value;
            
            if (!name || !query) {{
                alert('Please fill in agent name and query');
                return;
            }}
            
            try {{
                const response = await fetch('/api/agents', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{name, query, location, interval}})
                }});
                
                if (response.ok) {{
                    const newAgent = await response.json();
                    agents.push(newAgent);
                    renderLeadsView();
                    renderAgentsView();
                    closeModal();
                    document.getElementById('agentName').value = '';
                    document.getElementById('agentQuery').value = '';
                    alert(`Agent "${{newAgent.name}}" created successfully!`);
                }} else {{
                    alert('Failed to create agent');
                }}
            }} catch (err) {{
                console.error('Create agent error:', err);
                alert('Network error. Please try again.');
            }}
        }}

        async function toggleScraper(scraperId) {{
            try {{
                const response = await fetch(`/api/scrapers/${{scraperId}}/toggle`, {{
                    method: 'POST'
                }});
                
                if (response.ok) {{
                    const updatedScraper = await response.json();
                    const scraper = scrapers.find(s => s.id === scraperId);
                    if (scraper) {{
                        scraper.status = updatedScraper.status;
                        renderConfigView();
                    }}
                }}
            }} catch (err) {{
                console.error('Toggle scraper error:', err);
                alert('Failed to toggle scraper');
            }}
        }}

        async function testNotification() {{
            try {{
                const response = await fetch('/api/notifications/test', {{
                    method: 'POST'
                }});
                
                if (response.ok) {{
                    const notif = await response.json();
                    const dot = document.getElementById('notifDot');
                    dot.style.display = 'block';
                    setTimeout(() => dot.style.display = 'none', 3000);
                    alert(`${{notif.title}}\n\n${{notif.message}}`);
                }}
            }} catch (err) {{
                console.error('Test notification error:', err);
            }}
        }}

        async function searchFromHome() {{
            const query = document.getElementById('homeSearchInput').value.trim();
            if (!query) {{
                alert('Please enter what you are selling');
                return;
            }}
            
            const btn = document.querySelector('.btn-search');
            btn.textContent = 'Searching...';
            btn.disabled = true;
            
            try {{
                const response = await fetch('/api/search', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{query: query, location: 'Kenya'}})
                }});
                
                if (response.ok) {{
                    const data = await response.json();
                    displaySearchResults(data);
                }} else {{
                    alert('Search failed. Please try again.');
                }}
            }} catch (err) {{
                console.error('Search error:', err);
                alert('Network error. Please check connection.');
            }} finally {{
                btn.textContent = 'Find Buyers';
                btn.disabled = false;
            }}
        }}
        
        function displaySearchResults(data) {{
            const container = document.getElementById('searchResults');
            if (!container) {{
                // Create results container if it doesn't exist
                const homeView = document.getElementById('homeView');
                const resultsDiv = document.createElement('div');
                resultsDiv.id = 'searchResults';
                resultsDiv.className = 'search-results';
                homeView.appendChild(resultsDiv);
            }}
            
            const resultsContainer = document.getElementById('searchResults');
            
            if (data.results.length === 0) {{
                resultsContainer.innerHTML = '<div class="empty-state"><div class="empty-icon">🔍</div><div class="empty-text">No leads found. Try a different search term.</div></div>';
                return;
            }}
            
            let html = `
                <div class="results-header">
                    <h3>Found ${{data.count}} Leads for "${{data.query}}"</h3>
                    <span class="results-time">${{data.duration_seconds}}s</span>
                </div>
                <div class="leads-list">
            `;
            
            data.results.forEach(lead => {{
                const badgeClass = lead.badge.toLowerCase();
                html += `
                    <div class="lead-card">
                        <div class="lead-header">
                            <span class="lead-badge badge-${{badgeClass}}">${{lead.badge}}</span>
                            <span class="lead-intent">${{(lead.intent_score * 100).toFixed(0)}}% Intent</span>
                        </div>
                        <h4 class="lead-title">${{lead.title}}</h4>
                        <p class="lead-snippet">${{lead.buyer_request_snippet}}</p>
                        <div class="lead-footer">
                            <span class="lead-phone">📞 ${{lead.contact_phone}}</span>
                            <span class="lead-location">📍 ${{lead.location}}</span>
                        </div>
                    </div>
                `;
            }});
            
            html += '</div>';
            resultsContainer.innerHTML = html;
            
            // Scroll to results
            resultsContainer.scrollIntoView({{behavior: 'smooth'}});
        }}

        async function refreshAgents() {{
            document.getElementById('lastUpdated').textContent = new Date().toLocaleTimeString();
            await loadAgents();
        }}

        function viewAgentDetails(agentId) {{
            switchView('agents');
        }}

        function exportAgent(agentId) {{
            const agent = agents.find(a => a.id === agentId);
            if (agent) {{
                alert(`Exporting leads for ${{agent.name}}`);
            }}
        }}

        document.getElementById('createAgentModal').addEventListener('click', (e) => {{
            if (e.target.id === 'createAgentModal') closeModal();
        }});
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    # Get port from environment variable (Railway sets this) or default to 8000
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"
    
    print("="*60)
    print("  DELTA 9 DASHBOARD v3.0")
    print("="*60)
    print()
    print(f"  Starting server on {host}:{port}")
    print()
    print("  URLs:")
    print(f"    http://{host}:{port}/           - Landing Page")
    print(f"    http://{host}:{port}/dashboard  - Full Dashboard UI")
    print(f"    http://{host}:{port}/docs       - API Documentation")
    print()
    print("  Features:")
    print("    Dynamic search (any query)")
    print("    Agent management (Create, View, Export)")
    print("    Scraper configuration (Toggle on/off)")
    print("    Live buyer feed")
    print("    Notifications")
    print()
    print("  Press CTRL+C to stop")
    print("="*60)
    uvicorn.run(app, host=host, port=port, log_level="info")

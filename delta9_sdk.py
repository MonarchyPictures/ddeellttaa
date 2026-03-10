#!/usr/bin/env python3
"""
Delta 9 Python SDK
==================
Official Python SDK for interacting with the Delta 9 AI Buyer Discovery API.

Installation:
    pip install requests

Usage:
    from delta9_sdk import Delta9Client
    
    client = Delta9Client(base_url="https://your-app.railway.app")
    
    # Search for buyers
    results = client.search("solar panels", location="Kenya")
    
    # Create an agent
    agent = client.create_agent("House", "apartments, houses", "Nairobi")
    
    # Run the agent
    leads = client.run_agent(agent.id)

Author: Delta 9 Team
Version: 1.0.0
"""

import requests
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Lead:
    """Represents a buyer lead"""
    id: str
    title: str
    snippet: str
    phone: str
    location: str
    intent_score: float
    badge: str
    source: str
    
    @property
    def is_hot(self) -> bool:
        return self.badge == "HOT"
    
    @property
    def is_warm(self) -> bool:
        return self.badge == "WARM"
    
    @property
    def is_cold(self) -> bool:
        return self.badge == "COLD"


@dataclass
class Agent:
    """Represents a monitoring agent"""
    id: str
    name: str
    query: str
    location: str
    status: str
    total_leads: int
    high_intent_leads: int
    last_run: Optional[str]
    next_run: Optional[str]
    run_interval: str
    
    @property
    def is_active(self) -> bool:
        return self.status == "active"


@dataclass
class Scraper:
    """Represents a data source/scraper"""
    id: str
    name: str
    status: str
    leads: int
    success_rate: float
    speed: float
    tags: List[str]
    description: str
    
    @property
    def is_enabled(self) -> bool:
        return self.status == "enabled"


class Delta9Error(Exception):
    """Base exception for Delta 9 SDK"""
    pass


class Delta9Client:
    """
    Delta 9 API Client
    
    Main client for interacting with the Delta 9 Buyer Discovery API.
    
    Args:
        base_url: The base URL of your Delta 9 instance
                  (e.g., "https://9delta9.up.railway.app")
        timeout: Request timeout in seconds (default: 30)
    
    Example:
        >>> client = Delta9Client("https://9delta9.up.railway.app")
        >>> results = client.search("solar panels")
        >>> print(f"Found {results['count']} leads")
    """
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make HTTP request to API"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Delta9Error(f"API request failed: {e}")
    
    # ==================== SEARCH ====================
    
    def search(self, query: str, location: str = "Kenya") -> Dict[str, Any]:
        """
        Search for buyer leads.
        
        Args:
            query: What you're looking for (e.g., "solar panels", "cement")
            location: Location to search in (default: "Kenya")
        
        Returns:
            Dictionary with search results containing leads
        
        Example:
            >>> results = client.search("solar panels", "Nairobi")
            >>> for lead in results['results']:
            ...     print(f"{lead['contact_phone']}: {lead['buyer_request_snippet']}")
        """
        data = {"query": query, "location": location}
        return self._request("POST", "/api/search", json=data)
    
    def search_leads(self, query: str, location: str = "Kenya") -> List[Lead]:
        """
        Search and return Lead objects.
        
        Args:
            query: Search query
            location: Location
        
        Returns:
            List of Lead objects
        
        Example:
            >>> leads = client.search_leads("tires", "Mombasa")
            >>> hot_leads = [l for l in leads if l.is_hot]
        """
        results = self.search(query, location)
        return [
            Lead(
                id=r["id"],
                title=r["title"],
                snippet=r["buyer_request_snippet"],
                phone=r["contact_phone"],
                location=r["location"],
                intent_score=r["intent_score"],
                badge=r["badge"],
                source=r["source"]
            )
            for r in results.get("results", [])
        ]
    
    # ==================== AGENTS ====================
    
    def list_agents(self) -> List[Agent]:
        """Get all agents"""
        data = self._request("GET", "/api/agents")
        return [
            Agent(
                id=a["id"],
                name=a["name"],
                query=a["query"],
                location=a["location"],
                status=a["status"],
                total_leads=a["total_leads"],
                high_intent_leads=a["high_intent_leads"],
                last_run=a.get("last_run"),
                next_run=a.get("next_run"),
                run_interval=a["run_interval"]
            )
            for a in data.get("agents", [])
        ]
    
    def create_agent(
        self,
        name: str,
        query: str,
        location: str = "Kenya",
        interval: str = "2h"
    ) -> Agent:
        """
        Create a new monitoring agent.
        
        Args:
            name: Agent name (e.g., "House", "Solar Panels")
            query: Search query (e.g., "apartments for rent")
            location: Location to monitor
            interval: Run interval (1h, 2h, 6h, 1d)
        
        Returns:
            Created Agent object
        """
        data = {
            "name": name,
            "query": query,
            "location": location,
            "interval": interval
        }
        result = self._request("POST", "/api/agents", json=data)
        return Agent(
            id=result["id"],
            name=result["name"],
            query=result["query"],
            location=result["location"],
            status=result["status"],
            total_leads=result["total_leads"],
            high_intent_leads=result["high_intent_leads"],
            last_run=result.get("last_run"),
            next_run=result.get("next_run"),
            run_interval=result["run_interval"]
        )
    
    def run_agent(self, agent_id: str) -> Dict[str, Any]:
        """
        Run an agent to collect leads.
        
        Args:
            agent_id: The agent ID
        
        Returns:
            Run results including new leads found
        """
        return self._request("POST", f"/api/agents/{agent_id}/run")
    
    def get_agent_leads(self, agent_id: str) -> Dict[str, Any]:
        """Get all leads collected by an agent"""
        return self._request("GET", f"/api/agents/{agent_id}/leads")
    
    def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent"""
        result = self._request("DELETE", f"/api/agents/{agent_id}")
        return result.get("success", False)
    
    def pause_agent(self, agent_id: str) -> bool:
        """Pause an agent"""
        result = self._request("POST", f"/api/agents/{agent_id}/status", 
                              json={"status": "paused"})
        return result.get("success", False)
    
    def resume_agent(self, agent_id: str) -> bool:
        """Resume a paused agent"""
        result = self._request("POST", f"/api/agents/{agent_id}/status",
                              json={"status": "active"})
        return result.get("success", False)
    
    # ==================== SCRAPERS ====================
    
    def list_scrapers(self) -> List[Scraper]:
        """Get all available scrapers"""
        data = self._request("GET", "/api/scrapers")
        return [
            Scraper(
                id=s["id"],
                name=s["name"],
                status=s["status"],
                leads=s["leads"],
                success_rate=s["success_rate"],
                speed=s["speed"],
                tags=s["tags"],
                description=s["description"]
            )
            for s in data.get("scrapers", [])
        ]
    
    def toggle_scraper(self, scraper_id: str) -> Scraper:
        """Enable/disable a scraper"""
        result = self._request("POST", f"/api/scrapers/{scraper_id}/toggle")
        return Scraper(
            id=result["id"],
            name=result["name"],
            status=result["status"],
            leads=result["leads"],
            success_rate=result["success_rate"],
            speed=result["speed"],
            tags=result["tags"],
            description=result["description"]
        )
    
    # ==================== HEALTH ====================
    
    def health(self) -> Dict[str, Any]:
        """Check API health"""
        return self._request("GET", "/health")
    
    def is_healthy(self) -> bool:
        """Quick health check"""
        try:
            result = self.health()
            return result.get("status") == "ok"
        except:
            return False


# ==================== EXAMPLE USAGE ====================

if __name__ == "__main__":
    # Example usage
    print("Delta 9 SDK Example")
    print("===================\n")
    
    # Initialize client
    client = Delta9Client("http://localhost:8000")
    
    # Check health
    if client.is_healthy():
        print("✓ API is healthy\n")
    else:
        print("✗ API is not responding\n")
        exit(1)
    
    # Search for leads
    print("Searching for 'solar panels' in Kenya...")
    results = client.search("solar panels", "Kenya")
    print(f"Found {results['count']} leads in {results['duration_seconds']}s\n")
    
    # Display leads
    for lead in results['results'][:3]:
        print(f"  [{lead['badge']}] {lead['title']}")
        print(f"    Phone: {lead['contact_phone']}")
        print(f"    Intent: {lead['intent_score']:.0%}")
        print()
    
    # List agents
    print("\nActive Agents:")
    agents = client.list_agents()
    for agent in agents:
        status = "✓" if agent.is_active else "✗"
        print(f"  {status} {agent.name} ({agent.total_leads} leads)")

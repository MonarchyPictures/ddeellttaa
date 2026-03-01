"""Agents functionality for Delta9 SDK."""

from typing import List, Dict, Any, Optional
from uuid import UUID
import requests
from .config import Config


class AgentsClient:
    """Client for agent management operations.
    
    Agents automatically search for leads at scheduled intervals.
    
    Example:
        >>> from delta9 import Delta9Client
        >>> client = Delta9Client()
        >>> 
        >>> # Create an agent
        >>> agent = client.agents.create(
        ...     name="Water Tank Agent",
        ...     query="water tanks",
        ...     location="Nairobi",
        ...     interval_hours=2
        ... )
        >>> 
        >>> # List all agents
        >>> agents = client.agents.list()
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.base_url = f"{config.api_url}/api/agents"
    
    def create(
        self,
        name: str,
        query: str,
        location: Optional[str] = None,
        interval_hours: int = 2,
        duration_days: int = 7
    ) -> Dict[str, Any]:
        """Create a new agent.
        
        Args:
            name: Agent name for identification
            query: Search query (e.g., "water tanks")
            location: Geographic location (default: "Kenya")
            interval_hours: Hours between runs (default: 2)
            duration_days: Total agent lifetime in days (default: 7)
        
        Returns:
            dict with agent details including id
        """
        payload = {
            "name": name,
            "query": query,
            "location": location or "Kenya",
            "interval_hours": interval_hours,
            "duration_days": duration_days
        }
        
        response = requests.post(
            self.base_url,
            json=payload,
            headers=self.config.headers,
            timeout=self.config.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def list(self) -> List[Dict[str, Any]]:
        """List all agents.
        
        Returns:
            List of agent dictionaries
        """
        response = requests.get(
            self.base_url,
            headers=self.config.headers,
            timeout=self.config.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def get(self, agent_id: str) -> Dict[str, Any]:
        """Get agent details by ID.
        
        Args:
            agent_id: The agent UUID
        
        Returns:
            dict with agent details
        """
        response = requests.get(
            f"{self.base_url}/{agent_id}",
            headers=self.config.headers,
            timeout=self.config.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def run_now(self, agent_id: str) -> Dict[str, Any]:
        """Trigger an agent to run immediately.
        
        Args:
            agent_id: The agent UUID
        
        Returns:
            dict with execution status
        """
        response = requests.post(
            f"{self.base_url}/{agent_id}/run",
            headers=self.config.headers,
            timeout=self.config.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def stop(self, agent_id: str) -> Dict[str, Any]:
        """Stop/deactivate an agent.
        
        Args:
            agent_id: The agent UUID
        
        Returns:
            dict with status
        """
        response = requests.post(
            f"{self.base_url}/{agent_id}/stop",
            headers=self.config.headers,
            timeout=self.config.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def delete(self, agent_id: str) -> Dict[str, Any]:
        """Delete an agent.
        
        Args:
            agent_id: The agent UUID
        
        Returns:
            dict with status
        """
        response = requests.delete(
            f"{self.base_url}/{agent_id}",
            headers=self.config.headers,
            timeout=self.config.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def get_leads(
        self,
        agent_id: str,
        min_score: Optional[float] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get leads found by an agent.
        
        Args:
            agent_id: The agent UUID
            min_score: Minimum confidence score filter
            limit: Maximum number of leads to return
        
        Returns:
            List of lead dictionaries
        """
        params = {"limit": limit}
        if min_score is not None:
            params["min_score"] = min_score
        
        response = requests.get(
            f"{self.base_url}/{agent_id}/leads",
            params=params,
            headers=self.config.headers,
            timeout=self.config.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def export_leads(self, agent_id: str) -> str:
        """Export agent leads as text.
        
        Args:
            agent_id: The agent UUID
        
        Returns:
            Text content of leads export
        """
        response = requests.get(
            f"{self.base_url}/{agent_id}/export",
            headers=self.config.headers,
            timeout=self.config.timeout
        )
        response.raise_for_status()
        return response.text

"""Main Delta9 SDK client."""

from typing import Optional
from .config import Config
from .search import SearchClient
from .agents import AgentsClient


class Delta9Client:
    """Unified Delta9 API client.
    
    Provides access to search and agents functionality with Kenya-optimized
    buyer intent discovery.
    
    Args:
        api_key: API authentication key (or set DELTA9_API_KEY env var)
        api_url: Base API URL (default: http://localhost:8000)
        timeout: Request timeout in seconds (default: 30)
    
    Example:
        >>> from delta9 import Delta9Client
        >>> client = Delta9Client(api_key="your-key")
        >>> 
        >>> # Search for buyers
        >>> results = client.search.find_buyers("water tanks", location="Nairobi")
        >>>
        >>> # Manage agents
        >>> agent = client.agents.create(name="Tank Agent", query="water tanks Nairobi")
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: str = "http://localhost:8000",
        timeout: int = 30
    ):
        self.config = Config(api_key=api_key, api_url=api_url, timeout=timeout)
        self._search: Optional[SearchClient] = None
        self._agents: Optional[AgentsClient] = None
    
    @property
    def search(self) -> SearchClient:
        """Access search functionality."""
        if self._search is None:
            self._search = SearchClient(self.config)
        return self._search
    
    @property
    def agents(self) -> AgentsClient:
        """Access agents functionality."""
        if self._agents is None:
            self._agents = AgentsClient(self.config)
        return self._agents
    
    def health(self) -> dict:
        """Check API health status.
        
        Returns:
            dict with status information
        """
        import requests
        response = requests.get(
            f"{self.config.api_url}/health",
            timeout=self.config.timeout
        )
        response.raise_for_status()
        return response.json()

"""Search functionality for Delta9 SDK."""

from typing import List, Dict, Any, Optional
import requests
from .config import Config


class SearchClient:
    """Client for search operations.
    
    Example:
        >>> from delta9 import Delta9Client
        >>> client = Delta9Client()
        >>> results = client.search.find_buyers("water tanks", location="Nairobi")
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.base_url = f"{config.api_url}/api/search"
    
    def find_buyers(
        self,
        query: str,
        location: str = "Kenya",
        min_intent_score: Optional[float] = None,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """Search for high-intent buyers.
        
        Args:
            query: Product or service to search for (e.g., "water tanks")
            location: Geographic location (default: "Kenya")
            min_intent_score: Minimum intent score filter (0.0-1.0)
            category: Product category hint
        
        Returns:
            dict containing leads and metadata
        
        Example:
            >>> results = client.search.find_buyers(
            ...     "water tanks",
            ...     location="Nairobi",
            ...     min_intent_score=0.5
            ... )
            >>> print(f"Found {results['count']} leads")
        """
        payload = {
            "query": query,
            "location": location,
        }
        if category:
            payload["category"] = category
        
        response = requests.post(
            self.base_url,
            json=payload,
            headers=self.config.headers,
            timeout=self.config.timeout
        )
        response.raise_for_status()
        data = response.json()
        
        # Filter by min_intent_score if specified
        if min_intent_score is not None and "results" in data:
            data["results"] = [
                lead for lead in data["results"]
                if lead.get("intent_score", 0) >= min_intent_score
            ]
            data["count"] = len(data["results"])
        
        return data
    
    def quick_search(self, query: str, location: str = "Kenya") -> List[Dict[str, Any]]:
        """Quick search returning just the leads list.
        
        Args:
            query: Product or service to search for
            location: Geographic location
        
        Returns:
            List of lead dictionaries
        """
        results = self.find_buyers(query, location)
        return results.get("results", [])
    
    def get_deep_search_status(self, job_id: str) -> Dict[str, Any]:
        """Check status of a background deep search job.
        
        Args:
            job_id: The job ID from a previous search
        
        Returns:
            dict with job status and results if complete
        """
        response = requests.get(
            f"{self.base_url}/deep-status",
            params={"job_id": job_id},
            headers=self.config.headers,
            timeout=self.config.timeout
        )
        response.raise_for_status()
        return response.json()

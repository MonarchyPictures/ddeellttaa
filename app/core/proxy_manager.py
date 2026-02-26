import random
import logging
import os
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class ProxyManager:
    """
    Manages proxy rotation.
    In a real production environment, this would integrate with services like BrightData, Oxylabs, etc.
    """
    
    # Placeholder for free proxies or rotation service API
    # Format: http://user:pass@host:port
    _PROXIES = [
        # Add your proxies here or load from env
    ]

    def __init__(self):
        self.proxies = self._load_proxies()
        self.current_index = 0

    def _load_proxies(self):
        env_proxies = os.getenv("PROXY_LIST", "")
        if env_proxies:
            return env_proxies.split(",")
        return self._PROXIES

    def get_proxy(self) -> Optional[Dict[str, str]]:
        """Returns a proxy dictionary for requests/playwright."""
        if not self.proxies:
            return None
        
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        
        # Requests format
        return {
            "http": proxy,
            "https": proxy
        }

    def get_playwright_proxy(self) -> Optional[Dict[str, str]]:
        """Returns a proxy dictionary for Playwright."""
        if not self.proxies:
            return None
            
        proxy_url = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        
        # Parse basic auth if present
        # server: http://user:pass@host:port
        return {"server": proxy_url}

# Global instance
PROXY_MANAGER = ProxyManager()

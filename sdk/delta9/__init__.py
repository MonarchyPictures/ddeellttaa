"""
Delta9 SDK - Kenya-optimized buyer intent discovery API client.

Clean public interface for programmatic access to Delta9 lead generation.
"""

__version__ = "1.0.0"
__author__ = "Delta9 Team"

# Clean public exports - no internal scrapers exposed
from .client import Delta9Client
from .search import SearchClient
from .agents import AgentsClient
from .config import Config

__all__ = [
    "Delta9Client",
    "SearchClient", 
    "AgentsClient",
    "Config",
]

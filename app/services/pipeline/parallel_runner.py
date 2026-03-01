# app/services/pipeline/parallel_runner.py
"""
Parallel scraper runner with weight-based concurrency.

Separates light (API) vs heavy (Playwright) scrapers.
"""
import asyncio
import random
import os
from typing import List, Dict, Any, Callable
from functools import wraps


# Concurrency limits (Railway-safe)
MAX_LIGHT_CONCURRENCY = int(os.getenv("LIGHT_SCRAPER_CONCURRENCY", 4))
MAX_HEAVY_CONCURRENCY = int(os.getenv("HEAVY_SCRAPER_CONCURRENCY", 2))


class ParallelScraperRunner:
    """
    Runs scrapers in parallel with proper concurrency controls.
    
    Light scrapers (API-based): max 4 concurrent
    Heavy scrapers (Playwright): max 2 concurrent
    """
    
    LIGHT_SCRAPERS = {"serpapi", "duckduckgo", "google_cse", "yahoo", "yandex", "brave"}
    HEAVY_SCRAPERS = {"facebook", "twitter", "telegram", "jiji", "pigiame", "google_maps"}
    
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []
    
    def classify_scraper(self, name: str) -> str:
        """Classify scraper as light or heavy."""
        name_lower = name.lower()
        if any(s in name_lower for s in self.LIGHT_SCRAPERS):
            return "light"
        return "heavy"
    
    async def run_with_semaphore(
        self,
        scraper_func: Callable,
        semaphore: asyncio.Semaphore,
        *args,
        **kwargs
    ) -> Any:
        """Run scraper with semaphore-controlled concurrency."""
        async with semaphore:
            # Add jitter to prevent thundering herd
            await asyncio.sleep(random.uniform(0.5, 1.5))
            return await scraper_func(*args, **kwargs)
    
    async def run_scrapers(
        self,
        scraper_tasks: List[tuple],
        query: str
    ) -> List[Dict[str, Any]]:
        """
        Run scrapers in parallel with weight-based concurrency.
        
        Args:
            scraper_tasks: List of (name, scraper_func) tuples
            query: Search query
            
        Returns:
            Combined results from all scrapers
        """
        # Separate by weight
        light_tasks = []
        heavy_tasks = []
        
        for name, func in scraper_tasks:
            weight = self.classify_scraper(name)
            if weight == "light":
                light_tasks.append((name, func))
            else:
                heavy_tasks.append((name, func))
        
        # Create semaphores
        light_semaphore = asyncio.Semaphore(MAX_LIGHT_CONCURRENCY)
        heavy_semaphore = asyncio.Semaphore(MAX_HEAVY_CONCURRENCY)
        
        # Build async tasks
        async_tasks = []
        
        for name, func in light_tasks:
            task = self.run_with_semaphore(func, light_semaphore, query)
            async_tasks.append((name, task, "light"))
        
        for name, func in heavy_tasks:
            task = self.run_with_semaphore(func, heavy_semaphore, query)
            async_tasks.append((name, task, "heavy"))
        
        # Run all tasks
        results = []
        for name, coro, weight in async_tasks:
            try:
                result = await coro
                results.append({
                    "scraper": name,
                    "weight": weight,
                    "results": result,
                    "status": "success"
                })
            except Exception as e:
                self.errors.append({
                    "scraper": name,
                    "weight": weight,
                    "error": str(e)
                })
                results.append({
                    "scraper": name,
                    "weight": weight,
                    "results": [],
                    "status": "error"
                })
        
        return results


def retry_with_backoff(max_retries=3, base_delay=2.0):
    """Decorator for retry with exponential backoff."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt == max_retries - 1:
                        raise last_exception
                    delay = min(base_delay * (2 ** attempt), 60.0)
                    await asyncio.sleep(delay + random.uniform(0, delay * 0.5))
            return None
        return wrapper
    return decorator

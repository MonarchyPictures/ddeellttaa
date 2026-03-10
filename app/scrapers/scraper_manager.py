"""
Scraper Manager
Orchestrates all scrapers and aggregates results
"""
import asyncio
from typing import List, Dict, Optional
from datetime import datetime

from .reddit_scraper import RedditScraper
from .twitter_scraper import TwitterScraper
from .forum_scraper import ForumScraper
from .base import ScrapeResult
from ..services.query_expansion import get_expansion_service
from ..services.intent_detection import get_intent_service
from ..services.lead_verification import get_verification_service


class ScraperManager:
    """
    Manages all scrapers and coordinates:
    1. Query expansion
    2. Parallel scraping
    3. Intent detection
    4. Lead verification
    5. Database storage
    """
    
    def __init__(self):
        self.reddit = RedditScraper()
        self.twitter = TwitterScraper()
        self.forum = ForumScraper()
        
        self.expansion_service = get_expansion_service()
        self.intent_service = get_intent_service()
        self.verification_service = get_verification_service()
    
    async def search_all(
        self,
        query: str,
        expand: bool = True,
        max_results_per_source: int = 10
    ) -> Dict:
        """
        Search all sources with query expansion
        
        Args:
            query: Original search query
            expand: Whether to expand the query
            max_results_per_source: Max results per scraper
            
        Returns:
            Dictionary with signals, leads, and stats
        """
        all_signals = []
        
        # Expand query if enabled
        if expand:
            expanded_queries = self.expansion_service.expand(query, limit=5)
            print(f"Expanded '{query}' into {len(expanded_queries)} search phrases")
            # Use top 3 expanded queries
            search_queries = expanded_queries[:3]
        else:
            search_queries = [query]
        
        # Search all sources for each query
        for search_query in search_queries:
            print(f"Searching: '{search_query}'")
            
            # Run scrapers in parallel
            results = await asyncio.gather(
                self.reddit.search(search_query, max_results_per_source),
                self.twitter.search(search_query, max_results_per_source),
                self.forum.search(search_query, max_results_per_source),
                return_exceptions=True
            )
            
            # Process results
            for scraper_results in results:
                if isinstance(scraper_results, Exception):
                    print(f"Scraper error: {scraper_results}")
                    continue
                
                for result in scraper_results:
                    # Convert ScrapeResult to dict with intent analysis
                    signal = self._process_signal(result, search_query)
                    if signal:
                        all_signals.append(signal)
        
        # Deduplicate signals
        all_signals = self._deduplicate_signals(all_signals)
        
        # Filter high-intent signals
        high_intent_signals = [
            s for s in all_signals
            if s.get("intent_score", 0) >= 0.3
        ]
        
        # Group signals by author for lead creation
        leads = self._aggregate_leads(high_intent_signals)
        
        return {
            "query": query,
            "expanded_queries": search_queries if expand else [query],
            "total_signals": len(all_signals),
            "high_intent_signals": len(high_intent_signals),
            "leads_found": len(leads),
            "signals": all_signals[:50],  # Limit for response
            "leads": leads[:20],  # Top 20 leads
            "searched_at": datetime.utcnow().isoformat(),
        }
    
    def _process_signal(self, result: ScrapeResult, query: str) -> Optional[Dict]:
        """Process a scrape result into a signal with intent analysis"""
        # Analyze intent
        full_text = f"{result.title} {result.content}"
        intent = self.intent_service.analyze(full_text, query)
        
        # Skip low confidence signals
        if intent.confidence < 0.3:
            return None
        
        return {
            "external_id": result.external_id,
            "source": result.source,
            "title": result.title,
            "content": result.content[:500],  # Truncate
            "author": result.author,
            "source_url": result.url,
            "query_matched": query,
            "subreddit": result.subreddit,
            "posted_at": result.posted_at.isoformat() if result.posted_at else None,
            "intent_score": intent.intent_score,
            "intent_category": intent.intent_category,
            "buying_urgency": intent.buying_urgency,
            "keywords_matched": intent.keywords_matched,
            "confidence": intent.confidence,
            "discovered_at": datetime.utcnow().isoformat(),
            "metadata": result.metadata or {},
        }
    
    def _deduplicate_signals(self, signals: List[Dict]) -> List[Dict]:
        """Remove duplicate signals by external_id"""
        seen = set()
        unique = []
        
        for signal in signals:
            ext_id = signal.get("external_id")
            if ext_id and ext_id not in seen:
                seen.add(ext_id)
                unique.append(signal)
            elif not ext_id:
                unique.append(signal)
        
        return unique
    
    def _aggregate_leads(self, signals: List[Dict]) -> List[Dict]:
        """Group signals by author and create leads"""
        # Group by author
        by_author: Dict[str, List[Dict]] = {}
        for signal in signals:
            author = signal.get("author", "")
            if author and author != "[deleted]":
                if author not in by_author:
                    by_author[author] = []
                by_author[author].append(signal)
        
        # Create leads from grouped signals
        leads = []
        for author, author_signals in by_author.items():
            if len(author_signals) >= 1:  # At least 1 signal
                # Calculate aggregate scores
                avg_intent = sum(s.get("intent_score", 0) for s in author_signals) / len(author_signals)
                
                # Get sources
                sources = list(set(s.get("source") for s in author_signals))
                
                # Build profile URLs
                profile_urls = {}
                for s in author_signals:
                    source = s.get("source")
                    url = s.get("source_url", "")
                    if source and url:
                        profile_urls[source] = url
                
                lead = {
                    "username": author,
                    "sources": sources,
                    "profile_urls": profile_urls,
                    "intent_score": round(avg_intent, 3),
                    "intent_category": author_signals[0].get("intent_category"),
                    "buying_urgency": author_signals[0].get("buying_urgency"),
                    "signal_count": len(author_signals),
                    "intent_signals": [s.get("content", "")[:200] for s in author_signals[:3]],
                    "first_seen": author_signals[0].get("discovered_at"),
                    "last_active": author_signals[-1].get("discovered_at"),
                    "location": self._extract_location_from_signals(author_signals),
                    "status": "new",
                    "verification_score": min(len(author_signals) * 0.2 + 0.3, 1.0),
                    "priority_score": round(avg_intent * min(len(author_signals) / 3, 1.0), 3),
                }
                leads.append(lead)
        
        # Sort by priority score
        leads.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
        
        return leads
    
    def _extract_location_from_signals(self, signals: List[Dict]) -> Optional[str]:
        """Try to extract location from signal metadata"""
        for signal in signals:
            subreddit = signal.get("subreddit")
            if subreddit and subreddit.lower() in ["nairobi", "kenya", "mombasa"]:
                return subreddit
            
            metadata = signal.get("metadata", {})
            location = metadata.get("location")
            if location:
                return location
        
        return None
    
    async def close(self):
        """Close all scrapers"""
        await asyncio.gather(
            self.reddit.close(),
            self.twitter.close(),
            self.forum.close(),
            return_exceptions=True
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Singleton
_scraper_manager = None


def get_scraper_manager() -> ScraperManager:
    """Get or create the scraper manager"""
    global _scraper_manager
    if _scraper_manager is None:
        _scraper_manager = ScraperManager()
    return _scraper_manager

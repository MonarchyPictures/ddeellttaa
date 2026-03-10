"""
Celery Tasks for Scraper Workers - Signal Stream Version
Scrapers publish to Signal Stream, processors consume from stream
"""
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from celery import chain, group, chord

from app.core.celery_config import celery_app
from app.services.signal_stream import get_signal_producer, Signal
from app.services.query_expansion import get_expansion_service
from app.scrapers.reddit_scraper import RedditScraper
from app.scrapers.twitter_scraper import TwitterScraper
from app.scrapers.forum_scraper import ForumScraper


@celery_app.task(bind=True, max_retries=3)
def scrape_reddit(self, query: str, search_query_id: Optional[int] = None) -> Dict:
    """
    Scrape Reddit and publish signals to stream
    
    Args:
        query: Search query
        search_query_id: Optional database ID for tracking
        
    Returns:
        Dict with scraping results
    """
    print(f"[Worker] Scraping Reddit for: {query}")
    
    try:
        # Run async scraper
        scraper = RedditScraper()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            results = loop.run_until_complete(scraper.search(query, limit=25))
        finally:
            loop.run_until_complete(scraper.close())
            loop.close()
        
        # Publish signals to stream
        producer = get_signal_producer()
        signals_published = 0
        
        for result in results:
            # Skip deleted/invalid authors
            if not result.author or result.author == '[deleted]':
                continue
            
            text = f"{result.title} {result.content}".strip()
            
            # Create signal
            signal = Signal(
                id=result.external_id,
                text=text,
                platform='reddit',
                url=result.url,
                author=result.author,
                timestamp=result.posted_at.isoformat() if result.posted_at else datetime.utcnow().isoformat(),
                query=query,
                metadata={
                    'subreddit': result.subreddit,
                    'score': result.metadata.get('score', 0),
                    'num_comments': result.metadata.get('num_comments', 0),
                }
            )
            
            # Publish to stream
            success = producer.send_signal(
                text=text,
                platform='reddit',
                url=result.url,
                author=result.author,
                query=query,
                metadata={
                    'subreddit': result.subreddit,
                    'score': result.metadata.get('score', 0),
                },
                signal_id=result.external_id,
            )
            
            if success:
                signals_published += 1
        
        print(f"[Worker] Reddit: Published {signals_published} signals to stream")
        
        return {
            "task_id": self.request.id,
            "source": "reddit",
            "query": query,
            "scraped_count": len(results),
            "signals_published": signals_published,
            "status": "completed",
        }
        
    except Exception as exc:
        print(f"[Worker] Reddit scrape failed: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True, max_retries=3)
def scrape_twitter(self, query: str, search_query_id: Optional[int] = None) -> Dict:
    """Scrape Twitter and publish signals to stream"""
    print(f"[Worker] Scraping Twitter for: {query}")
    
    try:
        scraper = TwitterScraper()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            results = loop.run_until_complete(scraper.search(query, limit=20))
        finally:
            loop.run_until_complete(scraper.close())
            loop.close()
        
        producer = get_signal_producer()
        signals_published = 0
        
        for result in results:
            text = result.content
            
            success = producer.send_signal(
                text=text,
                platform='twitter',
                url=result.url,
                author=result.author,
                query=query,
                metadata={
                    'likes': result.metadata.get('likes', 0),
                    'retweets': result.metadata.get('retweets', 0),
                },
                signal_id=result.external_id,
            )
            
            if success:
                signals_published += 1
        
        print(f"[Worker] Twitter: Published {signals_published} signals to stream")
        
        return {
            "task_id": self.request.id,
            "source": "twitter",
            "query": query,
            "scraped_count": len(results),
            "signals_published": signals_published,
            "status": "completed",
        }
        
    except Exception as exc:
        print(f"[Worker] Twitter scrape failed: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True, max_retries=3)
def scrape_forum(self, query: str, search_query_id: Optional[int] = None) -> Dict:
    """Scrape Forums and publish signals to stream"""
    print(f"[Worker] Scraping Forums for: {query}")
    
    try:
        scraper = ForumScraper()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            results = loop.run_until_complete(scraper.search(query, limit=15))
        finally:
            loop.run_until_complete(scraper.close())
            loop.close()
        
        producer = get_signal_producer()
        signals_published = 0
        
        for result in results:
            text = f"{result.title} {result.content}".strip()
            
            success = producer.send_signal(
                text=text,
                platform='forum',
                url=result.url,
                author=result.author,
                query=query,
                metadata={
                    'forum_name': result.subreddit,  # Used as forum name
                    'views': result.metadata.get('views', 0),
                    'replies': result.metadata.get('replies', 0),
                },
                signal_id=result.external_id,
            )
            
            if success:
                signals_published += 1
        
        print(f"[Worker] Forum: Published {signals_published} signals to stream")
        
        return {
            "task_id": self.request.id,
            "source": "forum",
            "query": query,
            "scraped_count": len(results),
            "signals_published": signals_published,
            "status": "completed",
        }
        
    except Exception as exc:
        print(f"[Worker] Forum scrape failed: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task
def scrape_all_sources(query: str, expand: bool = True) -> Dict:
    """
    Launch parallel scrapers that all publish to the Signal Stream
    """
    print(f"[Worker] Launching parallel scrape for: {query}")
    
    # Expand query if enabled
    if expand:
        expansion_service = get_expansion_service()
        expanded = expansion_service.expand(query, limit=3)
        queries = expanded[:3]
    else:
        queries = [query]
    
    results = {
        "query": query,
        "expanded_queries": queries,
        "tasks": [],
    }
    
    # Create parallel task groups for each query
    for q in queries:
        job = group(
            scrape_reddit.s(q),
            scrape_twitter.s(q),
            scrape_forum.s(q),
        )
        
        result = job.apply_async()
        
        results["tasks"].append({
            "query": q,
            "group_id": result.id,
            "task_ids": [r.id for r in result.results],
        })
    
    return results


@celery_app.task
def search_and_process(query: str, expand: bool = True) -> Dict:
    """
    Complete search workflow with Signal Stream:
    1. Scrape all sources (publish to stream)
    2. Process signals from stream (intent detection)
    3. Create leads from high-intent signals
    
    The actual processing happens via signal_pipeline tasks
    that consume from the Redis stream.
    """
    print(f"[Worker] Full workflow for: {query}")
    
    # Step 1: Scrape all sources (they publish to stream)
    scrape_result = scrape_all_sources(query, expand)
    
    # Step 2: Start stream consumer to process signals
    from app.tasks.signal_pipeline import consume_signal_stream
    consumer_task = consume_signal_stream.delay(duration=300)  # 5 minutes
    
    return {
        "workflow": "search_and_process",
        "query": query,
        "scrape_tasks": scrape_result,
        "consumer_task_id": consumer_task.id,
        "status": "initiated",
        "message": "Scrapers publishing to stream. Consumer processing signals.",
    }

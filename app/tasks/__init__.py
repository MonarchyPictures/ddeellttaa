"""Celery Tasks for Delta-9"""

# Scraper Tasks (publish to Signal Stream)
from .scraper_tasks import (
    scrape_reddit,
    scrape_twitter,
    scrape_forum,
    scrape_all_sources,
    search_and_process,
)

# Signal Pipeline Tasks (process from stream)
from .signal_pipeline import (
    process_signal_stream,
    create_lead_from_signal,
    batch_process_signals,
    consume_signal_stream,
)

# Lead Tasks
from .lead_tasks import (
    create_lead_from_signals,
    verify_lead,
    enrich_lead_data,
    process_unprocessed_signals,
)

__all__ = [
    # Scrapers
    "scrape_reddit",
    "scrape_twitter",
    "scrape_forum",
    "scrape_all_sources",
    "search_and_process",
    
    # Signal Pipeline
    "process_signal_stream",
    "create_lead_from_signal",
    "batch_process_signals",
    "consume_signal_stream",
    
    # Leads
    "create_lead_from_signals",
    "verify_lead",
    "enrich_lead_data",
    "process_unprocessed_signals",
]

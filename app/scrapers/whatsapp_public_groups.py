# app/scrapers/whatsapp_public_groups.py
# FIXED: Line at the end returned 'result' instead of 'results'

import logging
import urllib.parse
from datetime import datetime, timezone
from .base_scraper import BaseScraper, ScraperSignal

logger = logging.getLogger(__name__)


class WhatsAppPublicGroupScraper(BaseScraper):
    source = "whatsapp"

    def scrape(self, query: str, time_window_hours: int):
        # USE DUCKDUCKGO TO FIND WHATSAPP GROUPS (Avoids Google Blocking)
        try:
            from ddgs import DDGS
        except ImportError:
            logger.error("DDGS package missing")
            return []

        search_terms = [
            f'site:chat.whatsapp.com Kenya {query}',
            f'whatsapp group {query} Kenya',
            f'chat.whatsapp.com {query}',
            f'whatsapp group link {query}',
            f'site:chat.whatsapp.com {query}',
            'site:chat.whatsapp.com Kenya group',
            'chat.whatsapp.com Kenya',
            f'{query} whatsapp group'
        ]
        logger.info(f"WHATSAPP: Searching via DDG: {search_terms[0]}")
        
        results = []
        for term in search_terms:
            try:
                results = list(DDGS().text(term, region='ke-en', max_results=10))
            except Exception as e:
                logger.error(f"WHATSAPP: DDG Search failed for '{term}': {e}")
                results = []
            if results:
                break
        
        if not results:
            for term in search_terms:
                try:
                    results = list(DDGS().text(term, region='wt-wt', max_results=10, backend='html'))
                except Exception:
                    results = []
                if results:
                    break
        
        if not results:
            fallback_terms = ['chat.whatsapp.com Kenya', 'whatsapp group Kenya']
            for term in fallback_terms:
                try:
                    results = list(DDGS().text(term, region='wt-wt', max_results=10, backend='html'))
                except Exception:
                    results = []
                if results:
                    break
            
        signals = []
        for r in results:
            title = r.get('title', 'WhatsApp Group')
            link = r.get('href', '')
            snippet = r.get('body', '')
            
            if "chat.whatsapp.com" not in link:
                continue
                
            signal = ScraperSignal(
                source=self.source,
                text=f"{title} - {snippet}",
                author="WhatsApp Group Invite",
                contact={"phone": None, "whatsapp": link, "email": None},
                location="Kenya",
                url=link,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            signals.append(signal.model_dump())
        
        if not signals and results:
            for r in results[:5]:
                title = r.get('title', 'WhatsApp Group')
                link = r.get('href', '')
                snippet = r.get('body', '')
                signal = ScraperSignal(
                    source=self.source,
                    text=f"{title} - {snippet}",
                    author="WhatsApp Group Invite",
                    contact={"phone": None, "whatsapp": link, "email": None},
                    location="Kenya",
                    url=link,
                    timestamp=datetime.now(timezone.utc).isoformat()
                )
                signals.append(signal.model_dump())
            
        logger.info(f"WHATSAPP: Found {len(signals)} groups")
        return signals

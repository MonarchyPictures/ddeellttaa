import json
import os
import requests
import time
import random  # Added missing import
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from urllib.parse import quote
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from ddgs import DDGS
from googlesearch import search as google_search

from app.utils.normalization import LeadValidator
from app.nlp.intent_service import BuyingIntentNLP
from app.core.compliance import ComplianceManager

class SpecialOpsAgent:
    """
    Autonomous web intelligence router for Delta 9.
    Follows strict decision logic for search, crawl, and extraction.
    """
    
    def __init__(self):
        self.ddgs = DDGS()
        self.compliance = ComplianceManager()
        self.intent_service = BuyingIntentNLP()
        self.validator = LeadValidator()
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        
        # Kenya Location Signals
        self.kenya_signals = {
            "cities": ["nairobi", "mombasa", "kisumu", "nakuru", "eldoret", "thika", "machakos", "kiambu"],
            "areas": ["westlands", "cbd", "eastlands", "kileleshwa", "karen", "rongai", "ruaka"],
            "phone_prefixes": ["+254", "07", "01"],
            "currency": ["kes", "ksh", "kshs", "/="],
            "slang": ["bei", "ni how much", "dm for price", "iko?", "niko", "ule"]
        }

    def execute_mission(self, query: str, location: str = "Kenya") -> List[Dict]:
        """
        Main entry point for the agent to find and extract leads.
        """
        print(f"🚀 SpecialOps Mission Started: {query} in {location}")
        
        # STEP 1: SEARCH (MANDATORY) - Use DuckDuckGo
        search_results = self._perform_search(query, location)
        if not search_results:
            print(f"⚠️ No search results for '{query}' in {location}. Mission aborted.")
            return []

        leads = []
        for result in search_results:
            url = result.get("href") or result.get("url")
            if not url:
                continue
                
            # STEP 2: CLASSIFICATION & STEP 3: CRAWLING
            page_type = self._classify_page(url)
            crawl_data = None
            
            if page_type == "DYNAMIC" or "facebook.com" in url or "reddit.com" in url:
                crawl_data = self._playwright_crawl(url)
            else:
                content = self._scrapy_crawl(url)
                if content:
                    crawl_data = {"content": content, "type": "general"}
            
            if not crawl_data:
                # Fallback: Use snippet from search result if crawling fails
                crawl_data = {
                    "content": result.get("body", "") or result.get("snippet", ""),
                    "type": "snippet",
                    "title": result.get("title", "")
                }

            # STEP 4: EXTRACTION & SCORING
            try:
                # Use the new classify_intent for the final lock
                # Use extracted body if available, otherwise use full text
                content_text = crawl_data.get("body", "") or crawl_data.get("title", "")
                if not content_text and crawl_data.get("content"):
                    content_text = crawl_data["content"][:2000]
                
                classification = self.intent_service.classify_intent(content_text)
                
                # ONLY ALLOW BUYER
                if classification != "BUYER":
                    print(f"⏩ Discarding non-buyer lead (Classification: {classification}): {url}")
                    print(f"   Content preview: {content_text[:150]}...")
                    continue

                extracted_data = self._extract_intelligence(crawl_data, url, query)
                final_lead = self._apply_kenya_scoring(extracted_data)
                
                # Boost confidence if explicitly classified as BUYER
                final_lead["confidence"] = min(99.0, final_lead["confidence"] + 15)
                # Ensure it's marked as hot lead if confidence is high
                final_lead["is_hot_lead"] = 1 if final_lead["confidence"] >= 85 else 0
            except Exception as e:
                print(f"⚠️ Intent analysis failed for {url}: {e}")
                continue
            
            # CONFIDENCE RULE (NO GUESSING)
            # Lowered threshold to 50 for live signals
            if final_lead.get("confidence", 0) >= 50: 
                leads.append(final_lead)
            else:
                print(f"📉 Low confidence ({final_lead.get('confidence')}) for {url}. Dropping.")

        return leads

    def _perform_search(self, query: str, location: str) -> List[Dict]:
        """
        Search using DuckDuckGo with Internal Query Rewriting and Kenyan intent patterns.
        """
        # INTERNAL QUERY REWRITE (NOT visible to user)
        # We rewrite the query to focus ONLY on buyer phrases
        buyer_phrases = [
            "want to buy", "looking for", "need", "seeking", 
            "anyone selling?", "where can I get", "who sells",
            "natafuta", "nahitaji", "nimehitaji"
        ]
        
        # Construct expanded queries using Kenyan language patterns
        # REWRITTEN: Stricter buyer-only intent queries with broader platform coverage
        # REDUCED count to avoid 429s and excessive resource usage
        expanded_queries = [
            f'"{query}" Kenya "looking for"',
            f'"{query}" Kenya "natafuta"',
            f'"{query}" Kenya "where to buy"',
            f'"{query}" Kenya "anyone selling"',
            f'"{query}" Kenya "need"'
        ]
        
        # Add social specific queries
        social_queries = [
            f'site:reddit.com "{query}" Kenya "looking for"',
            f'site:facebook.com "{query}" Kenya "looking for"',
            f'site:twitter.com "{query}" Kenya "looking for"'
        ]
        
        # ABSOLUTE SELLER BLOCKLIST (Internal) - Expanded
        seller_block_keywords = [
            "for sale", "selling", "available", "price", "discount", "offer", 
            "promo", "delivery", "in stock", "we sell", "shop", "dealer", 
            "supplier", "warehouse", "order now", "dm for price", 
            "call / whatsapp", "our store", "brand new", "limited stock",
            "flash sale", "retail price", "wholesale", "best price",
            "check out", "visit us", "located at", "we deliver", "buy from us",
            "contact for price", "special offer", "new arrival", "stockist",
            "dm to order", "shipping available", "price is", "kwa bei ya",
            "tunauza", "mzigo mpya", "punguzo", "call me for", "contact me for",
            "brand new", "imported", "affordable", "wholesale price", "retail",
            "visit our shop", "we are located", "delivery available", "countrywide",
            "pay on delivery", "lipa baada ya", "mzigo umefika", "bei nafuu",
            "tuko na", "pata yako", "agiza sasa"
        ]
        
        # Exclude common irrelevant domains
        excluded_sites = [
            "amazon.com", "alibaba.com", "ebay.com", "aliexpress.com", 
            "jumia.co.ke", "jiji.co.ke", "pigiame.co.ke", "kilimall.co.ke",
            "jumia.com", "jiji.com", "pigiame.com", "kilimall.com"
        ]
        site_filter = " " + " ".join([f"-site:{site}" for site in excluded_sites])
        
        print(f"🔍 Starting Kenyan Intent Search for: {query}")
        
        all_results = []
        
        # Combine and vary search patterns
        target_queries = expanded_queries + social_queries
        
        # Limit to 5 queries for better coverage
        for q in target_queries[:5]:
            try:
                # Determine source based on query
                source = "DuckDuckGo"
                if "site:facebook.com" in q: source = "Facebook"
                elif "site:reddit.com" in q: source = "Reddit"
                elif "site:twitter.com" in q: source = "Twitter"
                
                # Keep query short and sweet
                search_q = q
                
                print(f"🔎 Query: {search_q} (Source: {source})")
                
                # DuckDuckGo search using ddgs directly
                # Add retry logic and error handling
                scraper_results = []
                for attempt in range(2):
                    try:
                        results = self.ddgs.text(search_q, region='ke-ke', max_results=10)
                        scraper_results = [{"text": r.get("body", ""), "url": r.get("href", "")} for r in results]
                        if scraper_results: break
                        time.sleep(random.uniform(3, 6))
                    except Exception as e:
                        print(f"⚠️ Attempt {attempt+1} failed for {source}: {e}")
                        time.sleep(5)
                
                if scraper_results:
                    for r in scraper_results:
                        all_results.append({
                    "title": r.get("text", "")[:100],
                    "body": r.get("text", ""),
                    "url": r.get("url")
                })
                
                # SIGNIFICANT delay to avoid 429
                time.sleep(random.uniform(5, 12))
                
                if len(all_results) >= 40: # Increased to get more candidates
                    break
                            
            except Exception as e:
                print(f"⚠️ Search Error for query {q}: {e}")

        # RELEVANCE FILTERING (ENFORCEMENT)
        filtered = []
        seen_urls = set()
        for r in all_results:
            url = r.get("url")
            if not url or url in seen_urls:
                continue
                
            title = r.get("title", "").lower()
            snippet = r.get("body", "").lower()
            combined_text = f"{title} {snippet}"
            
            # Use the central classifier for consistency
            classification = self.intent_service.classify_intent(combined_text)
            
            # ABSOLUTE DISCARD: If intent is not clearly BUYER or UNCLEAR (with query match) -> DISCARD.
            if classification not in ["BUYER", "UNCLEAR"]:
                continue
            
            # Check if query keywords are in title or snippet
            query_keywords = query.lower().split()
            important_keywords = [kw for kw in query_keywords if len(kw) > 2]
            
            # BROADENED RELEVANCE: Check for ANY important keyword
            # We are now very lenient here - if it passed the search query, it's likely relevant
            has_query = any(kw in combined_text for kw in important_keywords)
            
            # If no keyword match, check if it's a social site (often minimal snippets)
            is_social_url = any(s in url.lower() for s in ["reddit.com", "facebook.com", "x.com", "twitter.com", "instagram.com"])
            
            if not has_query and not is_social_url:
                print(f"⏩ Skipping {url}: No query match in snippet")
                continue
            
            # Kenya signal check
            kenyan_cities = ["nairobi", "mombasa", "kisumu", "nakuru", "eldoret", "thika", "machakos", "kiambu", "kenya", "naivasha", "kitui", "embu", "meru"]
            has_kenya_signal = any(sig in combined_text or sig in url.lower() for sig in kenyan_cities + [".ke", "/ke/"])
            
            # If it's a social site or it's clearly a BUYER, we are more lenient with the geo signal
            if is_social_url or classification == "BUYER":
                has_kenya_signal = True 
            
            if has_kenya_signal:
                filtered.append(r)
                seen_urls.add(url)
            else:
               print(f"⏩ Skipping {url}: No Kenya signal")
        
        return filtered

    def _searxng_search(self, query: str, location: str) -> List[Dict]:
        """Deprecated: Use _perform_search instead"""
        return self._perform_search(query, location)

    def _classify_page(self, url: str) -> str:
        """
        Classify page as STATIC or DYNAMIC.
        """
        dynamic_indicators = ["facebook.com", "instagram.com", "twitter.com", "x.com", "reddit.com", "linkedin.com"]
        if any(ind in url for ind in dynamic_indicators):
            return "DYNAMIC"
        
        # Default to dynamic for most modern sites unless we have signals otherwise
        return "DYNAMIC" 

    def _playwright_crawl(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Crawl dynamic pages using Playwright.
        REDDIT EXTRACTION RULES: Extract Post title, body, subreddit, timestamp, etc.
        """
        print(f"🌐 Playwright Crawl: {url}")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(user_agent=random.choice(self.user_agents))
                page = context.new_page()
                
                # Facebook specific handling
                if "facebook.com" in url:
                    # Check compliance/rate limits
                    self.compliance.wait_for_rate_limit("facebook")
                    
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=30000)
                        
                        # Wait for potential content or "See More"
                        try:
                            page.wait_for_selector("text=See more", timeout=5000)
                            page.click("text=See more")
                        except: pass
                        
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                        time.sleep(2)
                    except Exception as e:
                        print(f"⚠️ Facebook goto/scroll failed: {e}")
                    
                    # Extract Facebook specific content if possible
                    # Try to find post text
                    body = ""
                    for selector in ["[data-ad-preview='message']", "[data-testid='post_message']", ".xdj266r", ".x11i5rnm", ".x1iorvi4", ".x78zum5"]:
                        try:
                            elements = page.query_selector_all(selector)
                            if elements:
                                body = " ".join([el.inner_text() for el in elements if len(el.inner_text()) > 10])
                                if body: break
                        except: continue
                        
                    content = page.content()
                    browser.close()
                    return {
                        "content": content, 
                        "type": "facebook",
                        "body": body or "Facebook Content",
                        "title": "Facebook Post"
                    }
                
                # Reddit specific handling (No Login)
                elif "reddit.com" in url:
                    # Check compliance/rate limits
                    self.compliance.wait_for_rate_limit("reddit")
                    
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=30000)
                        
                        # Wait for content to load
                        try:
                            page.wait_for_selector("h1, .post-title, [data-test-id='post-content']", timeout=15000)
                        except:
                            print(f"⚠️ Timeout waiting for Reddit selectors on {url}")
                    except Exception as e:
                        print(f"⚠️ Page.goto failed for Reddit {url}: {e}")
                        # Fallback to simple request if playwright fails
                        content = self._scrapy_crawl(url)
                        if content:
                            browser.close()
                            return {"content": content, "type": "reddit", "title": "Reddit Post (Fallback)", "body": ""}
                        browser.close()
                        return None
                    
                    # Extract Reddit specific fields with fallbacks
                    title = ""
                    for selector in ["h1", "shredded-post h1", "[data-test-id='post-content'] h1", "h1[slot='title']", ".post-title"]:
                        try:
                            el = page.query_selector(selector)
                            if el:
                                title = el.inner_text()
                                if title: break
                        except: continue

                    body = ""
                    # Reddit uses many different structures. Try several.
                    for selector in [
                        "[data-test-id='post-content']", 
                        ".post-content", 
                        "shredded-post p", 
                        ".RichTextJSON-root",
                        "div[slot='text-body']",
                        "#post-data",
                        ".usertext-body",
                        "p"
                    ]:
                        try:
                            elements = page.query_selector_all(selector)
                            if elements:
                                body = " ".join([el.inner_text() for el in elements if len(el.inner_text()) > 20])
                                if body: break
                        except: continue

                    # If body is still empty, get all text from the main post area
                    if not body:
                        try:
                            main = page.query_selector("main")
                            if main:
                                body = main.inner_text()
                        except: pass

                    data = {
                        "type": "reddit",
                        "title": title or "Reddit Post",
                        "body": body,
                        "subreddit": url.split("/r/")[1].split("/")[0] if "/r/" in url else "unknown",
                        "timestamp": str(datetime.now(timezone.utc)),
                        "comment_count": "0",
                        "author": "public",
                        "content": page.content()
                    }
                    browser.close()
                    return data
                
                else:
                    page.goto(url, wait_until="load", timeout=20000)
                    content = page.content()
                    browser.close()
                    return {"content": content, "type": "general"}
        except Exception as e:
            print(f"❌ Playwright Error for {url}: {e}")
            return None

    def _scrapy_crawl(self, url: str) -> Optional[str]:
        """
        Crawl static pages using simple HTTP fetch (Scrapy fallback).
        """
        print(f"📄 Static Crawl: {url}")
        try:
            headers = {"User-Agent": random.choice(self.user_agents)}
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                return response.text
            return None
        except Exception as e:
            print(f"❌ Static Crawl Error: {e}")
            return None

    def _extract_intelligence(self, crawl_data: Dict[str, Any], url: str, query: str) -> Dict:
        """
        Extract structured leads using semantic analysis.
        REDDIT INTENT SCORING: 95+ confidence if keywords + geo signal.
        """
        content = crawl_data.get("content", "")
        soup = BeautifulSoup(content, 'html.parser')
        soup_text = soup.get_text(separator=' ', strip=True)

        # PREFER pre-extracted body/title for dynamic sites (Reddit, Facebook, etc.)
        # If soup_text is garbage (login wall), use body.
        extracted_body = crawl_data.get("body", "").strip()
        extracted_title = crawl_data.get("title", "").strip()
        
        # Determine best text source
        text = soup_text
        if extracted_body and extracted_body != "Facebook Content":
             text = f"{extracted_title} {extracted_body}"
        elif len(soup_text) < 100 and extracted_body: # Soup failed
             text = f"{extracted_title} {extracted_body}"
             
        # Ensure text is not empty to avoid pipeline rejection
        if not text.strip():
            text = f"{extracted_title} {extracted_body}" or "No content extracted"
        
        # KENYA LOCATION SIGNALS CHECK
        geo_confidence = self._calculate_geo_confidence(text)
        
        # Intent Analysis
        # Use the robust text we just determined
        extraction_text = text

        intent_score_raw = self.intent_service.calculate_intent_score(extraction_text)
        readiness, readiness_score = self.intent_service.analyze_readiness(extraction_text)
        intent_score = intent_score_raw * 100
        
        # REDDIT SPECIFIC INTENT SCORING
        is_reddit = crawl_data.get("type") == "reddit"
        if is_reddit:
            reddit_intent_keywords = [
                "looking for", "need", "any recommendations", "where can i get", 
                "anyone selling", "where to buy", "natafuta", "nahitaji", "nimehitaji",
                "anyone with", "best place to", "how much is", "where is", "buy",
                "can someone point me", "looking to buy"
            ]
            has_reddit_intent = any(kw in extraction_text.lower() for kw in reddit_intent_keywords)
            if has_reddit_intent and geo_confidence > 30:
                intent_score = max(intent_score, 95)
            elif has_reddit_intent:
                intent_score = max(intent_score, 85)
        
        # Override with readiness if it's higher
        intent_score = max(intent_score, readiness_score * 10)

        # CONFIDENCE RULE (CORE RULES)
        confidence = 0
        has_phone = any(p in text for p in self.kenya_signals["phone_prefixes"])
        has_currency = any(c in text.lower() for c in self.kenya_signals["currency"])
        has_city = any(city in text.lower() for city in self.kenya_signals["cities"])
        
        # Add slang check for Kenya relevance
        has_slang = any(s in text.lower() for s in self.kenya_signals["slang"])
        
        # Intent Check: Does the text contain the user's query keywords?
        query_keywords = query.lower().split()
        important_keywords = [kw for kw in query_keywords if len(kw) > 2]
        has_query_keywords = any(kw in text.lower() for kw in important_keywords)
        
        if has_phone and intent_score > 60 and has_query_keywords:
            confidence = 98 
        elif (has_city or has_currency or has_slang) and intent_score > 50 and has_query_keywords:
            confidence = 96
        elif intent_score > 80 and geo_confidence > 30 and has_query_keywords:
            confidence = 95
        else:
            # More generous fallback
            confidence = (intent_score * 0.6) + (geo_confidence * 0.4)
            if (is_reddit or "facebook" in url) and has_query_keywords:
                confidence += 20 # Boost social results as they are often more "live"
            
            # If the query keywords are completely missing from the text, penalize heavily
            if not has_query_keywords:
                confidence -= 40
            
        confidence = min(max(confidence, 0.0), 99.0)

        # Lead Type
        lead_type = "GENERAL"
        if "buy" in text.lower() or "looking for" in text.lower() or "price" in text.lower():
            lead_type = "BUY_INTENT"
        elif "sell" in text.lower():
            lead_type = "SELL_INTENT"

        return {
            "source": crawl_data.get("type", "general"),
            "url": url,
            "confidence": round(confidence, 2),
            "text": text,
            "raw_data": {**crawl_data, "url": url, "source": crawl_data.get("type", "general")},
            "data": {
                "title": crawl_data.get("title") or (soup.title.string if soup.title else "Untitled Lead"),
                "summary": text[:200] + "...",
                "fields": {
                    "lead_type": lead_type,
                    "location_score": geo_confidence,
                    "intent_score": intent_score,
                    "is_kenya_relevant": geo_confidence > 40,
                    "phone": self._extract_phone_simple(text)
                },
                "raw_text": text[:2000]
            }
        }

    def _extract_phone_simple(self, text: str) -> Optional[str]:
        import re
        # Basic Kenya phone regex
        match = re.search(r'(\+254|0)(7|1)\d{8}', text)
        return match.group(0) if match else None

    def _apply_kenya_scoring(self, lead: Dict) -> Dict:
        """
        KENYA LEAD SCORING (FINAL STEP)
        Base score: 70
        +15 if phone/WhatsApp present
        +10 if Nairobi / major town
        +5 if price mentioned
        -10 if location unclear
        -20 if repost or spam
        IF score ≥85: → MARK AS HOT LEAD
        """
        score = 70
        text = lead.get("text", "").lower()
        
        # +15 if phone/WhatsApp present
        if lead.get("data", {}).get("fields", {}).get("phone"):
            score += 15
            
        # +10 if Nairobi / major town
        major_towns = ["nairobi", "mombasa", "kisumu", "nakuru", "eldoret", "thika"]
        if any(town in text for town in major_towns):
            score += 10
            
        # +5 if price mentioned
        if any(p in text for p in ["kes", "ksh", "price", "cost", "bei"]):
            score += 5
            
        # -10 if location unclear
        if not lead.get("data", {}).get("fields", {}).get("is_kenya_relevant"):
            score -= 10
            
        # -20 if repost or spam
        if any(s in text for s in ["spam", "repost", "fake"]):
            score -= 20
            
        lead["confidence"] = min(99.0, score)
        lead["is_hot_lead"] = 1 if score >= 85 else 0
        
        # FINAL OUTPUT (WhatsApp-Ready)
        lead["whatsapp_ready"] = {
            "platform": lead.get("source", "web"),
            "location": "Kenya",
            "intent": "BUY_INTENT" if "buy" in text or "looking for" in text else "GENERAL",
            "confidence": lead["confidence"],
            "contact": lead.get("data", {}).get("fields", {}).get("phone"),
            "message_hint": f"Hi, I saw your post regarding {lead.get('data', {}).get('title', 'this')} in Kenya..."
        }
        
        return lead

    def _calculate_geo_confidence(self, text: str) -> float:
        """
        Calculate confidence score (0-100) for Kenya relevance.
        """
        text_lower = text.lower()
        score = 0
        
        # Strong Signals (95-100)
        for city in self.kenya_signals["cities"]:
            if city in text_lower: score += 40
        for area in self.kenya_signals["areas"]:
            if area in text_lower: score += 30
        for prefix in self.kenya_signals["phone_prefixes"]:
            if prefix in text: score += 50 # Case sensitive check for phone numbers
            
        # Currency & Slang
        for curr in self.kenya_signals["currency"]:
            if curr in text_lower: score += 20
        for slang in self.kenya_signals["slang"]:
            if slang in text_lower: score += 15
            
        return min(100.0, float(score))

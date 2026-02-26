# app/telegram/group_manager.py
# ============================================================
# GROUP MANAGER
# ============================================================
# Manages Telegram group discovery, joining, and health.
# Auto-discovers new groups relevant to user queries.
# ============================================================

import logging
import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timezone

from .config import KENYAN_GROUPS, ALL_GROUPS, AUTO_JOIN_GROUPS

logger = logging.getLogger(__name__)


class GroupManager:
    """
    Manages Telegram groups for monitoring.
    
    Features:
    - Auto-select groups based on product category
    - Join new groups
    - Track group health (activity, member count)
    - Discover new groups via search
    """

    def __init__(self, monitor=None):
        self.monitor = monitor
        self.active_groups: Dict[str, Dict] = {}
        self.failed_groups: Dict[str, str] = {}  # username -> reason

    def get_groups_for_query(self, query: str, category: str = None) -> List[Dict]:
        """
        Get relevant Telegram groups for a search query.
        
        Args:
            query: What the user is selling
            category: Pre-detected category (optional)
            
        Returns:
            List of group dicts sorted by relevance
        """
        if not category:
            category = self._detect_category(query)

        # Get category-specific groups
        groups = list(KENYAN_GROUPS.get(category, []))

        # Always include general marketplace groups
        if category != "general":
            groups.extend(KENYAN_GROUPS.get("general", []))

        # Deduplicate
        seen = set()
        unique_groups = []
        for g in groups:
            if g["username"] not in seen:
                seen.add(g["username"])
                g["category"] = category
                unique_groups.append(g)

        logger.info(
            f"Found {len(unique_groups)} groups for "
            f"category '{category}' (query: '{query}')"
        )
        return unique_groups

    async def setup_groups(
        self, query: str, category: str = None,
        max_groups: int = 20, auto_join: bool = None
    ) -> Dict:
        """
        Set up monitoring groups for a search query.
        
        1. Gets relevant groups for the category
        2. Optionally joins groups not yet joined
        3. Adds groups to monitor
        
        Returns:
            {"added": N, "failed": N, "groups": [...]}
        """
        if not self.monitor:
            return {"error": "No monitor attached", "added": 0}

        if auto_join is None:
            auto_join = AUTO_JOIN_GROUPS

        groups = self.get_groups_for_query(query, category)[:max_groups]
        discovered_cache: List[Dict] = []

        added = 0
        failed = 0
        group_results = []

        for group in groups:
            username = group["username"]

            try:
                # Try to join if auto_join is enabled
                if auto_join and self.monitor.connected:
                    success = await self.monitor.join_group(username)
                    if not success:
                        self.failed_groups[username] = "join_failed"
                        failed += 1
                        group_results.append({
                            **group, "status": "join_failed"
                        })
                        continue

                # Add to monitor
                await self.monitor.add_group(
                    username=username,
                    category=group.get("category", "general"),
                    name=group.get("name", username)
                )

                self.active_groups[username] = {
                    **group,
                    "status": "active",
                    "added_at": datetime.now(timezone.utc).isoformat()
                }
                added += 1
                group_results.append({**group, "status": "active"})

                # Small delay between join attempts
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error setting up group @{username}: {e}")
                self.failed_groups[username] = str(e)
                failed += 1
                group_results.append({**group, "status": "error", "error": str(e)})

        # If static groups fail, discover and try fresh public groups from web search.
        if added == 0 and max_groups > 0:
            if not discovered_cache:
                discovered_cache = await self.discover_new_groups(query)
            if discovered_cache:
                logger.info(f"Retrying Telegram setup with {len(discovered_cache)} discovered groups")
            for group in discovered_cache[:max_groups]:
                username = group.get("username", "").strip()
                if not username:
                    continue
                if username in self.active_groups or username in self.failed_groups:
                    continue
                try:
                    if auto_join and self.monitor.connected:
                        success = await self.monitor.join_group(username)
                        if not success:
                            self.failed_groups[username] = "join_failed"
                            failed += 1
                            group_results.append({**group, "status": "join_failed"})
                            continue

                    await self.monitor.add_group(
                        username=username,
                        category=category or "general",
                        name=group.get("name", username)
                    )
                    self.active_groups[username] = {
                        **group,
                        "category": category or "general",
                        "status": "active",
                        "added_at": datetime.now(timezone.utc).isoformat()
                    }
                    added += 1
                    group_results.append({**group, "status": "active", "discovered": True})
                    await asyncio.sleep(1)
                except Exception as e:
                    self.failed_groups[username] = str(e)
                    failed += 1
                    group_results.append({**group, "status": "error", "error": str(e), "discovered": True})

        result = {
            "added": added,
            "failed": failed,
            "total_available": len(groups),
            "groups": group_results
        }

        logger.info(
            f"Group setup complete: {added} active, "
            f"{failed} failed, {len(groups)} total"
        )
        return result

    async def discover_new_groups(self, query: str) -> List[Dict]:
        """
        Discover new Telegram groups by searching.
        Uses DDG to find t.me links related to the query.
        """
        try:
            from ddgs import DDGS
        except ImportError:
            return []

        discovered = []

        search_queries = [
            f'site:t.me "{query}" Kenya',
            f'site:t.me Kenya "{query}" group',
            f'telegram group "{query}" Kenya join',
        ]

        try:
            with DDGS() as ddgs:
                for sq in search_queries:
                    results = list(ddgs.text(sq, max_results=10, region='ke-en'))

                    for r in results:
                        url = r.get('href', '')
                        if 't.me/' not in url:
                            continue

                        # Extract group username from URL
                        # Handles: t.me/username, t.me/+invite, t.me/s/username
                        parts = url.replace("https://t.me/", "").replace("http://t.me/", "")
                        parts = parts.split("/")[0].split("?")[0]

                        if parts.startswith("+"):
                            # Invite link
                            group_type = "invite"
                        elif parts.startswith("s/"):
                            parts = parts[2:]
                            group_type = "public"
                        else:
                            group_type = "public"

                        # Skip if already known
                        known_usernames = {g["username"] for g in ALL_GROUPS}
                        if parts in known_usernames:
                            continue

                        discovered.append({
                            "username": parts,
                            "name": r.get('title', parts),
                            "url": url,
                            "type": group_type,
                            "snippet": r.get('body', '')[:200]
                        })

        except Exception as e:
            logger.error(f"Group discovery error: {e}")

        # Deduplicate
        seen = set()
        unique = []
        for g in discovered:
            if g["username"] not in seen:
                seen.add(g["username"])
                unique.append(g)

        logger.info(f"Discovered {len(unique)} new groups for '{query}'")
        return unique

    def _detect_category(self, query: str) -> str:
        """Simple category detection from query."""
        query_lower = query.lower()

        for category, groups in KENYAN_GROUPS.items():
            # Check against keywords from the query intelligence engine
            from app.engine.query_intelligence import CATEGORY_PATTERNS
            config = CATEGORY_PATTERNS.get(category, {})
            if any(kw in query_lower for kw in config.get("keywords", [])):
                return category

        return "general"

    def get_stats(self) -> Dict:
        return {
            "active_groups": len(self.active_groups),
            "failed_groups": len(self.failed_groups),
            "groups": self.active_groups
        }

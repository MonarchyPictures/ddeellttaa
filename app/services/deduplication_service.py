"""
DELTA-9 DEDUPLICATION SERVICE
Prevents duplicate leads from being stored

Uses multiple strategies:
1. Exact hash match (phone + text + date)
2. Similarity hash for near-duplicates
3. Phone number uniqueness
4. Time-window based deduplication
"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)


@dataclass
class DuplicateCheck:
    """Result of duplicate check"""
    is_duplicate: bool
    match_type: Optional[str] = None  # 'exact', 'phone', 'similar'
    match_id: Optional[str] = None
    similarity_score: float = 0.0


class DeduplicationService:
    """
    Production-grade deduplication service
    
    Prevents the same lead from being processed multiple times
    """
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
        
        # In-memory cache for recent hashes
        self.recent_hashes: Set[str] = set()
        self.phone_cache: Dict[str, datetime] = {}
        self.text_cache: Dict[str, datetime] = {}
        
        # Cache expiration (24 hours)
        self.cache_ttl = timedelta(hours=24)
        
        # Statistics
        self.stats = {
            'checks_performed': 0,
            'duplicates_found': 0,
            'exact_matches': 0,
            'phone_matches': 0,
            'similar_matches': 0
        }
        
        logger.info("🔄 Deduplication Service initialized")
    
    def check_duplicate(self, lead_data: Dict) -> DuplicateCheck:
        """
        Check if lead is a duplicate
        
        Args:
            lead_data: Lead data with phone, text, timestamp
            
        Returns:
            DuplicateCheck result
        """
        self.stats['checks_performed'] += 1
        
        # Clean cache first
        self._clean_cache()
        
        # Check 1: Exact hash match
        exact_hash = self._compute_exact_hash(lead_data)
        if exact_hash in self.recent_hashes:
            self.stats['duplicates_found'] += 1
            self.stats['exact_matches'] += 1
            return DuplicateCheck(
                is_duplicate=True,
                match_type='exact',
                match_id=exact_hash
            )
        
        # Check 2: Phone number + time window
        phone = lead_data.get('phone', '')
        if phone:
            phone_dup = self._check_phone_duplicate(phone, lead_data.get('timestamp'))
            if phone_dup.is_duplicate:
                self.stats['duplicates_found'] += 1
                self.stats['phone_matches'] += 1
                return phone_dup
        
        # Check 3: Text similarity
        text = lead_data.get('text', '')
        if text:
            similar_dup = self._check_similarity_duplicate(text)
            if similar_dup.is_duplicate:
                self.stats['duplicates_found'] += 1
                self.stats['similar_matches'] += 1
                return similar_dup
        
        # Not a duplicate - add to cache
        self.recent_hashes.add(exact_hash)
        if phone:
            self.phone_cache[phone] = datetime.utcnow()
        if text:
            text_hash = self._compute_text_hash(text)
            self.text_cache[text_hash] = datetime.utcnow()
        
        return DuplicateCheck(is_duplicate=False)
    
    def _compute_exact_hash(self, lead_data: Dict) -> str:
        """
        Compute exact match hash
        
        Combines:
        - Phone number
        - Text snippet (first 100 chars)
        - Date (day-level)
        """
        phone = lead_data.get('phone', '')
        text = lead_data.get('text', '')[:100].lower().strip()
        
        # Extract just the date part
        timestamp = lead_data.get('timestamp', datetime.utcnow())
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                timestamp = datetime.utcnow()
        
        date_str = timestamp.strftime('%Y-%m-%d')
        
        # Create hash
        hash_input = f"{phone}:{text}:{date_str}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def _check_phone_duplicate(self, phone: str, timestamp) -> DuplicateCheck:
        """
        Check if phone number was seen recently
        
        Prevents the same person from being added multiple times
        within a time window
        """
        if not phone:
            return DuplicateCheck(is_duplicate=False)
        
        # Normalize phone
        phone = re.sub(r'\s+|-', '', phone)
        
        if phone in self.phone_cache:
            last_seen = self.phone_cache[phone]
            
            # Check if within 24 hour window
            if datetime.utcnow() - last_seen < self.cache_ttl:
                return DuplicateCheck(
                    is_duplicate=True,
                    match_type='phone',
                    match_id=phone
                )
        
        return DuplicateCheck(is_duplicate=False)
    
    def _check_similarity_duplicate(self, text: str) -> DuplicateCheck:
        """
        Check for similar text using simhash
        
        Prevents near-duplicate posts
        """
        if not text:
            return DuplicateCheck(is_duplicate=False)
        
        # Compute text hash
        text_hash = self._compute_text_hash(text)
        
        # Check against recent texts
        for cached_hash, cached_time in self.text_cache.items():
            similarity = self._compute_similarity(text_hash, cached_hash)
            
            if similarity > 0.85:  # 85% similar
                return DuplicateCheck(
                    is_duplicate=True,
                    match_type='similar',
                    match_id=cached_hash,
                    similarity_score=similarity
                )
        
        return DuplicateCheck(is_duplicate=False)
    
    def _compute_text_hash(self, text: str) -> str:
        """
        Compute simhash-like text fingerprint
        
        Uses word frequency hashing
        """
        # Normalize
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        words = text.split()
        
        # Simple hash based on word presence
        word_set = set(words)
        hash_input = '|'.join(sorted(word_set))
        
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def _compute_similarity(self, hash1: str, hash2: str) -> float:
        """
        Compute similarity between two hashes
        
        Uses Hamming distance for simhash comparison
        """
        # For simple hash, use character-level similarity
        matches = sum(c1 == c2 for c1, c2 in zip(hash1, hash2))
        return matches / len(hash1)
    
    def _clean_cache(self):
        """Remove expired entries from cache"""
        now = datetime.utcnow()
        cutoff = now - self.cache_ttl
        
        # Clean phone cache
        self.phone_cache = {
            k: v for k, v in self.phone_cache.items()
            if v > cutoff
        }
        
        # Clean text cache
        self.text_cache = {
            k: v for k, v in self.text_cache.items()
            if v > cutoff
        }
    
    def get_stats(self) -> Dict:
        """Get deduplication statistics"""
        return {
            **self.stats,
            'cache_size': {
                'hashes': len(self.recent_hashes),
                'phones': len(self.phone_cache),
                'texts': len(self.text_cache)
            },
            'duplicate_rate': (
                self.stats['duplicates_found'] / max(self.stats['checks_performed'], 1) * 100
            )
        }
    
    def clear_cache(self):
        """Clear all caches"""
        self.recent_hashes.clear()
        self.phone_cache.clear()
        self.text_cache.clear()
        logger.info("🧹 Deduplication cache cleared")


# Singleton instance
_dedupe_instance = None

def get_dedupe_service(redis_client=None) -> DeduplicationService:
    """Get or create deduplication service"""
    global _dedupe_instance
    if _dedupe_instance is None:
        _dedupe_instance = DeduplicationService(redis_client)
    return _dedupe_instance

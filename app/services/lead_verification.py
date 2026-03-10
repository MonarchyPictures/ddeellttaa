"""
Lead Verification Layer
The secret sauce that filters spam, bots, and low-quality leads

Verifies:
- Not spam (content analysis)
- Not bots (behavioral patterns)
- Not reposts (duplicate detection)
- Recent activity (post age < 48h)
- Account quality (account age > 30d)
- Engagement quality
"""
import re
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    PENDING = "pending"
    REJECTED = "rejected"
    SUSPICIOUS = "suspicious"


class RejectionReason(str, Enum):
    SPAM = "spam"
    BOT = "bot"
    REPOST = "repost"
    TOO_OLD = "too_old"
    LOW_QUALITY_ACCOUNT = "low_quality_account"
    VENDOR = "vendor"
    DUPLICATE = "duplicate"


@dataclass
class VerificationResult:
    """Result of lead verification"""
    is_verified: bool
    status: VerificationStatus
    verification_score: float  # 0-1
    rejection_reasons: List[RejectionReason] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    checks_passed: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class LeadVerificationService:
    """
    Comprehensive Lead Verification
    
    Filters out:
    - Spam posts
    - Bot accounts
    - Reposts/duplicates
    - Old posts (>48h)
    - New/suspicious accounts (<30d)
    - Low engagement quality
    """
    
    # SPAM PATTERNS
    SPAM_KEYWORDS = [
        "click here", "click link", "check my bio", "link in bio",
        "limited time", "act now", "don't miss out",
        "100% free", "guaranteed", "no risk",
        "make money", "earn $", "work from home",
        "crypto", "bitcoin", "investment opportunity",
        "weight loss", "diet pill", "miracle cure",
    ]
    
    SPAM_PATTERNS = [
        r'\b\d{3,}\s*\$+\b',  # Excessive $$$ signs
        r'[!]{3,}',  # Multiple exclamation marks
        r'[A-Z]{10,}',  # ALL CAPS words
        r'(.)\1{5,}',  # Repeated characters
    ]
    
    # BOT INDICATORS
    BOT_PATTERNS = [
        r'^\d+$',  # Username is only numbers
        r'^[a-z]+\d{4,}$',  # Username like john12345
        r'bot\d*',  # Username contains "bot"
        r'auto',  # Username contains "auto"
    ]
    
    # SUSPICIOUS POSTING BEHAVIOR
    SUSPICIOUS_PATTERNS = [
        r'\b(buy now|order now|click here)\b.*\b(buy now|order now|click here)\b',  # Repeated CTAs
    ]
    
    def __init__(self):
        self._seen_hashes: set = set()  # For duplicate detection (in-memory cache)
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns"""
        self.spam_regex = [re.compile(p, re.IGNORECASE) for p in self.SPAM_PATTERNS]
        self.bot_regex = [re.compile(p, re.IGNORECASE) for p in self.BOT_PATTERNS]
        self.suspicious_regex = [re.compile(p, re.IGNORECASE) for p in self.SUSPICIOUS_PATTERNS]
    
    def verify(self, signal_data: Dict) -> VerificationResult:
        """
        Comprehensive verification of a signal/lead
        
        Args:
            signal_data: Dict with signal information
                - text: Post content
                - author: Username
                - platform: Source platform
                - posted_at: Post timestamp (ISO format)
                - account_created_at: Account creation (ISO format, optional)
                - author_karma: Account karma/score (optional)
                - metadata: Additional platform data
        
        Returns:
            VerificationResult with detailed checks
        """
        checks_passed = []
        warnings = []
        rejection_reasons = []
        score = 1.0
        metadata = {}
        
        # Extract data
        text = signal_data.get('text', '')
        author = signal_data.get('author', '')
        platform = signal_data.get('platform', '')
        posted_at_str = signal_data.get('posted_at') or signal_data.get('timestamp')
        account_created_str = signal_data.get('account_created_at')
        author_karma = signal_data.get('author_karma', 0)
        
        # 1. Check for SPAM
        spam_score = self._check_spam(text)
        if spam_score > 0.5:
            rejection_reasons.append(RejectionReason.SPAM)
            score -= spam_score
            warnings.append(f"High spam indicators: {spam_score:.2f}")
        else:
            checks_passed.append("spam_check")
        
        # 2. Check for BOT accounts
        bot_score = self._check_bot(author, signal_data.get('metadata', {}))
        if bot_score > 0.5:
            rejection_reasons.append(RejectionReason.BOT)
            score -= bot_score
            warnings.append(f"Bot indicators detected: {bot_score:.2f}")
        else:
            checks_passed.append("bot_check")
        
        # 3. Check for REPOSTS/DUPLICATES
        is_duplicate = self._check_duplicate(text, author)
        if is_duplicate:
            rejection_reasons.append(RejectionReason.REPOST)
            score -= 0.4
            warnings.append("Duplicate/repost detected")
        else:
            checks_passed.append("duplicate_check")
        
        # 4. Check POST AGE (< 48 hours)
        post_age_hours = self._calculate_post_age(posted_at_str)
        metadata['post_age_hours'] = post_age_hours
        
        if post_age_hours is not None:
            if post_age_hours > 48:
                rejection_reasons.append(RejectionReason.TOO_OLD)
                score -= 0.3
                warnings.append(f"Post too old: {post_age_hours:.1f} hours")
            elif post_age_hours < 0.5:  # Less than 30 minutes (suspicious speed)
                warnings.append("Very recent post - possible automation")
                score -= 0.1
            else:
                checks_passed.append("recency_check")
        
        # 5. Check ACCOUNT AGE (> 30 days)
        account_age_days = self._calculate_account_age(account_created_str)
        metadata['account_age_days'] = account_age_days
        
        if account_age_days is not None:
            if account_age_days < 30:
                rejection_reasons.append(RejectionReason.LOW_QUALITY_ACCOUNT)
                score -= 0.3
                warnings.append(f"New account: {account_age_days} days old")
            elif account_age_days < 7:
                score -= 0.5  # Very new account
                warnings.append(f"Very new account: {account_age_days} days old")
            else:
                checks_passed.append("account_age_check")
        
        # 6. Check ACCOUNT QUALITY (karma/engagement)
        if author_karma is not None:
            metadata['author_karma'] = author_karma
            if author_karma < 10:
                warnings.append("Very low karma/account activity")
                score -= 0.2
            elif author_karma > 100:
                score += 0.1  # Boost for established accounts
                checks_passed.append("account_quality_check")
        
        # 7. Check for VENDOR (selling, not buying)
        vendor_score = self._check_vendor(text)
        if vendor_score > 0.5:
            rejection_reasons.append(RejectionReason.VENDOR)
            score -= vendor_score
            warnings.append("Vendor/seller detected")
        else:
            checks_passed.append("vendor_check")
        
        # Calculate final score
        verification_score = max(0.0, min(1.0, score))
        
        # Determine status
        if rejection_reasons and verification_score < 0.3:
            status = VerificationStatus.REJECTED
            is_verified = False
        elif rejection_reasons or warnings:
            status = VerificationStatus.SUSPICIOUS
            is_verified = verification_score >= 0.5
        else:
            status = VerificationStatus.VERIFIED
            is_verified = True
        
        return VerificationResult(
            is_verified=is_verified,
            status=status,
            verification_score=round(verification_score, 3),
            rejection_reasons=rejection_reasons,
            warnings=warnings,
            checks_passed=checks_passed,
            metadata=metadata
        )
    
    def _check_spam(self, text: str) -> float:
        """Check for spam indicators. Returns 0-1 score."""
        if not text:
            return 0.0
        
        text_lower = text.lower()
        score = 0.0
        
        # Check spam keywords
        for keyword in self.SPAM_KEYWORDS:
            if keyword in text_lower:
                score += 0.2
        
        # Check spam patterns
        for pattern in self.spam_regex:
            if pattern.search(text):
                score += 0.15
        
        # Check for excessive URLs
        url_count = len(re.findall(r'http[s]?://', text))
        if url_count > 2:
            score += 0.2 * url_count
        
        # Check for excessive hashtags
        hashtag_count = text.count('#')
        if hashtag_count > 5:
            score += 0.1 * (hashtag_count - 5)
        
        return min(score, 1.0)
    
    def _check_bot(self, username: str, metadata: Dict) -> float:
        """Check for bot account indicators. Returns 0-1 score."""
        if not username:
            return 0.5
        
        score = 0.0
        username_lower = username.lower()
        
        # Check username patterns
        for pattern in self.bot_regex:
            if pattern.match(username_lower):
                score += 0.4
        
        # Check posting frequency (if available)
        posts_per_hour = metadata.get('posts_per_hour', 0)
        if posts_per_hour > 10:
            score += 0.3
        if posts_per_hour > 50:
            score += 0.4
        
        # Check if profile is empty/minimal
        if metadata.get('is_empty_profile', False):
            score += 0.2
        
        # Check follower/following ratio
        followers = metadata.get('followers', 0)
        following = metadata.get('following', 0)
        if followers and following:
            ratio = followers / following if following > 0 else 0
            if ratio < 0.01:  # Following many, few followers
                score += 0.2
        
        return min(score, 1.0)
    
    def _check_duplicate(self, text: str, author: str) -> bool:
        """Check if this is a repost/duplicate."""
        # Create content hash (normalized)
        normalized = re.sub(r'\s+', ' ', text.lower().strip())
        normalized = re.sub(r'[^\w\s]', '', normalized)  # Remove punctuation
        content_hash = hashlib.md5(f"{author}:{normalized[:100]}".encode()).hexdigest()
        
        if content_hash in self._seen_hashes:
            return True
        
        # Add to seen (with size limit to prevent memory issues)
        if len(self._seen_hashes) > 10000:
            self._seen_hashes.clear()
        
        self._seen_hashes.add(content_hash)
        return False
    
    def _calculate_post_age(self, posted_at_str: Optional[str]) -> Optional[float]:
        """Calculate post age in hours."""
        if not posted_at_str:
            return None
        
        try:
            # Try ISO format
            posted_at = datetime.fromisoformat(posted_at_str.replace('Z', '+00:00'))
            age = datetime.utcnow() - posted_at.replace(tzinfo=None)
            return age.total_seconds() / 3600  # Convert to hours
        except:
            return None
    
    def _calculate_account_age(self, created_at_str: Optional[str]) -> Optional[int]:
        """Calculate account age in days."""
        if not created_at_str:
            return None
        
        try:
            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            age = datetime.utcnow() - created_at.replace(tzinfo=None)
            return age.days
        except:
            return None
    
    def _check_vendor(self, text: str) -> float:
        """Check if text indicates a vendor (seller, not buyer)."""
        text_lower = text.lower()
        score = 0.0
        
        vendor_phrases = [
            "i am a", "i'm a", "we are a", "we're a",
            "i provide", "we provide", "i offer", "we offer",
            "my services", "our services", "hire me", "hire us",
            "contact me", "contact us", "reach me", "reach us",
            "for sale", "selling", "we sell", "i sell",
        ]
        
        for phrase in vendor_phrases:
            if phrase in text_lower:
                score += 0.2
        
        return min(score, 1.0)
    
    def quick_verify(self, text: str, author: str, posted_at: str) -> bool:
        """Quick verification - returns True if passes basic checks."""
        result = self.verify({
            'text': text,
            'author': author,
            'posted_at': posted_at,
        })
        return result.is_verified


# Singleton
_verification_service = None


def get_verification_service() -> LeadVerificationService:
    """Get or create the verification service singleton"""
    global _verification_service
    if _verification_service is None:
        _verification_service = LeadVerificationService()
    return _verification_service


# Example usage
if __name__ == "__main__":
    service = LeadVerificationService()
    
    test_cases = [
        # Good lead
        {
            "text": "Looking for a plumber in Nairobi. Need urgent help with a leak!",
            "author": "homeowner_ke",
            "posted_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            "account_created_at": (datetime.utcnow() - timedelta(days=365)).isoformat(),
            "author_karma": 150,
        },
        # Spam
        {
            "text": "CLICK HERE!!! Best prices guaranteed!!! Buy now!!!",
            "author": "deals12345",
            "posted_at": (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
            "account_created_at": (datetime.utcnow() - timedelta(days=2)).isoformat(),
            "author_karma": 1,
        },
        # Old post
        {
            "text": "Looking for a web developer",
            "author": "startup_founder",
            "posted_at": (datetime.utcnow() - timedelta(days=5)).isoformat(),
            "account_created_at": (datetime.utcnow() - timedelta(days=500)).isoformat(),
        },
        # Vendor (not buyer)
        {
            "text": "I am a web developer offering services. Contact me for best rates!",
            "author": "dev_services",
            "posted_at": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
        },
    ]
    
    print("=" * 80)
    print("Lead Verification Layer - Test Results")
    print("=" * 80)
    
    for i, signal in enumerate(test_cases, 1):
        result = service.verify(signal)
        print(f"\nTest {i}:")
        print(f"  Text: {signal['text'][:50]}...")
        print(f"  Score: {result.verification_score} | Verified: {result.is_verified}")
        print(f"  Status: {result.status}")
        if result.rejection_reasons:
            print(f"  Rejected: {[r.value for r in result.rejection_reasons]}")
        if result.warnings:
            print(f"  Warnings: {result.warnings}")

"""
Security module tests.
"""

from datetime import timedelta

import pytest

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
    verify_token_type,
)


class TestPasswordHashing:
    """Test password hashing functionality."""
    
    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "testpass123"  # Under 72 bytes for bcrypt
        hashed = get_password_hash(password)
        
        # Hash should be different from plain password
        assert hashed != password
        
        # Verification should succeed
        assert verify_password(password, hashed) is True
        
        # Wrong password should fail
        assert verify_password("wrongpassword", hashed) is False
    
    def test_different_passwords_different_hashes(self):
        """Test that same password produces different hashes (due to salt)."""
        password = "testpass123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Hashes should be different due to salt
        assert hash1 != hash2
        
        # But both should verify
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTTokens:
    """Test JWT token functionality."""
    
    def test_create_access_token(self):
        """Test access token creation."""
        token = create_access_token(subject="user123")
        
        # Should be a string
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Should be decodable
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["type"] == "access"
    
    def test_create_refresh_token(self):
        """Test refresh token creation."""
        token = create_refresh_token(subject="user123")
        
        # Should be a string
        assert isinstance(token, str)
        
        # Should be decodable
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["type"] == "refresh"
    
    def test_token_with_custom_expiry(self):
        """Test token with custom expiration."""
        # Short expiration
        token = create_access_token(
            subject="user123",
            expires_delta=timedelta(minutes=5)
        )
        
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user123"
    
    def test_decode_invalid_token(self):
        """Test decoding an invalid token."""
        payload = decode_token("invalid.token.here")
        assert payload is None
    
    def test_decode_malformed_token(self):
        """Test decoding a malformed token."""
        payload = decode_token("not_a_valid_jwt")
        assert payload is None
    
    def test_verify_token_type_access(self):
        """Test verifying access token type."""
        token = create_access_token(subject="user123")
        payload = decode_token(token)
        
        assert verify_token_type(payload, "access") is True
        assert verify_token_type(payload, "refresh") is False
    
    def test_verify_token_type_refresh(self):
        """Test verifying refresh token type."""
        token = create_refresh_token(subject="user123")
        payload = decode_token(token)
        
        assert verify_token_type(payload, "refresh") is True
        assert verify_token_type(payload, "access") is False
    
    def test_token_with_additional_claims(self):
        """Test token with additional claims."""
        token = create_access_token(
            subject="user123",
            additional_claims={"role": "admin", "custom": "value"}
        )
        
        payload = decode_token(token)
        assert payload["sub"] == "user123"
        assert payload["role"] == "admin"
        assert payload["custom"] == "value"


class TestTokenSecurity:
    """Test token security features."""
    
    def test_tokens_are_unique(self):
        """Test that each token is unique (within same second may be identical)."""
        import time
        token1 = create_access_token(subject="user1")
        time.sleep(0.1)  # Small delay to ensure different timestamps
        token2 = create_access_token(subject="user1")
        
        # Same user, different tokens
        assert token1 != token2
    
    def test_different_subjects_different_tokens(self):
        """Test tokens for different subjects."""
        token1 = create_access_token(subject="user1")
        token2 = create_access_token(subject="user2")
        
        assert token1 != token2
        
        payload1 = decode_token(token1)
        payload2 = decode_token(token2)
        
        assert payload1["sub"] == "user1"
        assert payload2["sub"] == "user2"

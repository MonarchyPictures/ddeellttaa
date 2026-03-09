"""
Configuration module tests.
"""

import os

import pytest

from app.core.config import Settings, get_settings, parse_cors_origins


class TestParseCorsOrigins:
    """Test CORS origins parsing."""
    
    def test_parse_string(self):
        """Test parsing CORS origins from string."""
        origins = parse_cors_origins("http://localhost:3000, http://localhost:8000")
        assert origins == ["http://localhost:3000", "http://localhost:8000"]
    
    def test_parse_list(self):
        """Test parsing CORS origins from list."""
        input_list = ["http://localhost:3000", "http://localhost:8000"]
        origins = parse_cors_origins(input_list)
        assert origins == input_list
    
    def test_parse_empty_string(self):
        """Test parsing empty string."""
        origins = parse_cors_origins("")
        assert origins == []
    
    def test_parse_none(self):
        """Test parsing None."""
        origins = parse_cors_origins(None)
        assert origins == []


class TestSettings:
    """Test Settings class."""
    
    def test_default_values(self):
        """Test default configuration values."""
        settings = Settings(ENVIRONMENT="development")
        
        assert settings.APP_NAME == "Delta 9"
        assert settings.APP_VERSION == "1.0.0"
        assert settings.HOST == "0.0.0.0"
        assert settings.PORT == 8000
    
    def test_environment_detection_development(self):
        """Test development environment detection."""
        settings = Settings(ENVIRONMENT="development")
        assert settings.is_development is True
        assert settings.is_production is False
        assert settings.is_testing is False
    
    def test_environment_detection_production(self):
        """Test production environment detection."""
        settings = Settings(ENVIRONMENT="production")
        assert settings.is_development is False
        assert settings.is_production is True
        assert settings.is_testing is False
    
    def test_environment_detection_testing(self):
        """Test testing environment detection."""
        settings = Settings(ENVIRONMENT="testing")
        assert settings.is_development is False
        assert settings.is_production is False
        assert settings.is_testing is True
    
    def test_cors_origins_parsing(self):
        """Test CORS origins parsing in settings."""
        settings = Settings(CORS_ORIGINS="http://localhost:3000, http://localhost:8000")
        assert "http://localhost:3000" in settings.CORS_ORIGINS
        assert "http://localhost:8000" in settings.CORS_ORIGINS
    
    def test_database_url(self):
        """Test database URL setting."""
        settings = Settings(DATABASE_URL="postgresql://user:pass@localhost/db")
        assert settings.DATABASE_URL == "postgresql://user:pass@localhost/db"
    
    def test_secret_key(self):
        """Test secret key setting."""
        settings = Settings(SECRET_KEY="my-secret-key")
        assert settings.SECRET_KEY == "my-secret-key"
    
    def test_rate_limiting_settings(self):
        """Test rate limiting settings."""
        settings = Settings(
            RATE_LIMIT_ENABLED=True,
            RATE_LIMIT_REQUESTS=200,
            RATE_LIMIT_WINDOW=120
        )
        assert settings.RATE_LIMIT_ENABLED is True
        assert settings.RATE_LIMIT_REQUESTS == 200
        assert settings.RATE_LIMIT_WINDOW == 120


class TestGetSettings:
    """Test get_settings function."""
    
    def test_get_settings_returns_settings(self):
        """Test that get_settings returns a Settings instance."""
        settings = get_settings()
        assert isinstance(settings, Settings)
    
    def test_get_settings_cached(self):
        """Test that get_settings returns cached instance."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

"""
Pytest configuration and fixtures.

Provides test fixtures for database sessions, authenticated clients,
and other testing utilities.
"""

import os
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Set test environment variables BEFORE any imports
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["ENVIRONMENT"] = "testing"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["RATE_LIMIT_ENABLED"] = "false"

# Import after setting env vars
from app.core.config import settings
from app.db.base_class import Base
from app.db.database import get_db
from app.main import app

# Verify we're using test settings
assert settings.ENVIRONMENT == "testing", "Tests must run in testing environment"

# Create test engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=None,
)

# Create test session factory
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db() -> Generator[Session, None, None]:
    """Override get_db dependency for testing."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override the dependency
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create test database tables before running tests."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield
    # Drop tables after tests
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Create a fresh database session for each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client() -> Generator[TestClient, None, None]:
    """Create a test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
def authenticated_client(client: TestClient, db_session: Session) -> TestClient:
    """Create an authenticated test client with a user in DB."""
    from app.db.repositories.user import UserRepository
    
    # Create test user directly in database
    user_repo = UserRepository(db_session)
    user = user_repo.create(
        email="test@example.com",
        password="testpassword123",
        full_name="Test User"
    )
    
    # Login to get token
    login_response = client.post(
        "/api/auth/login",
        data={
            "username": "test@example.com",
            "password": "testpassword123",
        },
    )
    
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    token = login_response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    
    return client


@pytest.fixture
def sample_agent_data():
    """Return sample agent data for testing."""
    return {
        "name": "Test Agent",
        "query": "Toyota Land Cruiser",
        "location": "Nairobi",
        "interval_hours": 2,
        "duration_days": 7,
    }


@pytest.fixture
def sample_search_request():
    """Return sample search request data."""
    return {
        "query": "iPhone 15",
        "location": "Kenya",
        "filters": {
            "min_intent_score": 0.5,
        },
    }


@pytest.fixture
def sample_user_data():
    """Return sample user registration data."""
    return {
        "email": "newuser@example.com",
        "password": "securepassword123",
        "full_name": "New User",
    }

"""
Authentication endpoint tests.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.repositories.user import UserRepository


class TestAuthentication:
    """Test authentication endpoints."""
    
    def test_register_user(self, client: TestClient, db_session: Session):
        """Test user registration."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "securepassword123",
                "full_name": "New User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert "id" in data
        assert "is_active" in data
        assert "hashed_password" not in data
    
    def test_register_duplicate_email(self, client: TestClient, db_session: Session):
        """Test registering with duplicate email fails."""
        # Register first user
        user_repo = UserRepository(db_session)
        user_repo.create(
            email="duplicate@example.com",
            password="password123",
            full_name="First User"
        )
        
        # Try to register again with same email
        response = client.post(
            "/api/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "password456",
                "full_name": "Second User",
            },
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()
    
    def test_login_success(self, client: TestClient, db_session: Session):
        """Test successful login."""
        # Create user first
        user_repo = UserRepository(db_session)
        user_repo.create(
            email="login@example.com",
            password="testpass123",
            full_name="Login User"
        )
        
        # Login
        response = client.post(
            "/api/auth/login",
            data={
                "username": "login@example.com",
                "password": "testpass123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
    
    def test_login_invalid_credentials(self, client: TestClient):
        """Test login with invalid credentials fails."""
        response = client.post(
            "/api/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401
    
    def test_login_wrong_password(self, client: TestClient, db_session: Session):
        """Test login with wrong password fails."""
        # Create user
        user_repo = UserRepository(db_session)
        user_repo.create(
            email="wrongpass@example.com",
            password="correctpassword",
            full_name="Test User"
        )
        
        # Try login with wrong password
        response = client.post(
            "/api/auth/login",
            data={
                "username": "wrongpass@example.com",
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401
    
    def test_get_current_user(self, authenticated_client: TestClient):
        """Test getting current user info."""
        response = authenticated_client.get("/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert "full_name" in data
        assert data["email"] == "test@example.com"
    
    def test_get_current_user_unauthorized(self, client: TestClient):
        """Test getting current user without auth fails."""
        response = client.get("/api/auth/me")
        assert response.status_code == 401
    
    def test_logout(self, authenticated_client: TestClient):
        """Test logout endpoint."""
        response = authenticated_client.post("/api/auth/logout")
        assert response.status_code == 200
        assert "successfully logged out" in response.json()["message"].lower()
    
    def test_token_refresh(self, client: TestClient, db_session: Session):
        """Test token refresh."""
        # Create user
        user_repo = UserRepository(db_session)
        user_repo.create(
            email="refresh@example.com",
            password="testpass123",
            full_name="Refresh User"
        )
        
        # Login to get tokens
        login_response = client.post(
            "/api/auth/login",
            data={
                "username": "refresh@example.com",
                "password": "testpass123",
            },
        )
        assert login_response.status_code == 200
        refresh_token = login_response.json()["refresh_token"]
        
        # Refresh token
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
    
    def test_refresh_invalid_token(self, client: TestClient):
        """Test refresh with invalid token fails."""
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid-token"},
        )
        assert response.status_code == 401
    
    def test_password_hashing(self, db_session: Session):
        """Test that passwords are properly hashed."""
        from app.core.security import verify_password
        
        user_repo = UserRepository(db_session)
        user = user_repo.create(
            email="hash@test.com",
            password="mypassword",
            full_name="Hash Test"
        )
        
        # Password should be hashed
        assert user.hashed_password != "mypassword"
        assert len(user.hashed_password) > 50  # bcrypt hashes are long
        
        # Verification should work
        assert verify_password("mypassword", user.hashed_password) is True
        assert verify_password("wrongpassword", user.hashed_password) is False

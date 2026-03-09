"""
API dependencies for authentication, authorization, and common utilities.

Provides FastAPI dependencies that can be injected into route handlers.
"""

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.security import decode_token, verify_token_type
from app.db.database import get_db
from app.db.repositories.user import UserRepository

# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[str]:
    """
    Extract and validate the current user ID from JWT token.
    
    Args:
        credentials: The authorization credentials from the request
        
    Returns:
        The user ID if token is valid, None otherwise
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_token_type(payload, "access"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_id


def require_auth(
    user_id: Optional[str] = Depends(get_current_user_id),
) -> str:
    """
    Require authentication for a route.
    
    Args:
        user_id: The user ID from the token
        
    Returns:
        The validated user ID
        
    Raises:
        HTTPException: If user is not authenticated
    """
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


def get_current_user(
    user_id: str = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Get the current authenticated user from database.
    
    Args:
        user_id: The user ID from the token
        db: Database session
        
    Returns:
        The User model instance
        
    Raises:
        HTTPException: If user not found or inactive
    """
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(UUID(user_id))
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    
    return user


class RoleChecker:
    """
    Dependency for checking user roles.
    
    Example:
        require_admin = RoleChecker(["admin"])
        
        @app.get("/admin")
        def admin_endpoint(user: User = Depends(require_admin)):
            pass
    """
    
    def __init__(self, allowed_roles: list[str]):
        """
        Initialize with allowed roles.
        
        Args:
            allowed_roles: List of roles that are allowed access
        """
        self.allowed_roles = allowed_roles
    
    def __call__(self, user=Depends(get_current_user)):
        """
        Check if user has required role.
        
        Args:
            user: The authenticated user
            
        Returns:
            The user if authorized
            
        Raises:
            HTTPException: If user doesn't have required role
        """
        # Check superuser (superusers have all permissions)
        if user.is_superuser:
            return user
        
        # Check specific roles
        user_roles = ["user"]  # Default role for all authenticated users
        if user.is_superuser:
            user_roles.append("admin")
        
        has_permission = any(role in self.allowed_roles for role in user_roles)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        
        return user


# Pre-defined role checkers
require_admin = RoleChecker(["admin"])
require_user = RoleChecker(["user", "admin"])

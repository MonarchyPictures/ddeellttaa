"""
User repository for database operations.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.models.user import User


class UserRepository:
    """Repository for user database operations."""
    
    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db
    
    def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email).first()
    
    def create(self, email: str, password: str, full_name: str) -> User:
        """Create a new user."""
        hashed_password = get_password_hash(password)
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def authenticate(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user."""
        user = self.get_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        return user
    
    def update_last_login(self, user: User) -> None:
        """Update user's last login time."""
        from datetime import datetime
        user.last_login = datetime.utcnow()
        self.db.commit()
    
    def update_password(self, user: User, new_password: str) -> None:
        """Update user's password."""
        user.hashed_password = get_password_hash(new_password)
        self.db.commit()
    
    def deactivate(self, user: User) -> None:
        """Deactivate a user."""
        user.is_active = False
        self.db.commit()
    
    def activate(self, user: User) -> None:
        """Activate a user."""
        user.is_active = True
        self.db.commit()

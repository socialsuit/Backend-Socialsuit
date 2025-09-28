from fastapi import Request, HTTPException, status, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from core.dependencies import get_current_user
from sqlalchemy.orm import Session
from app.services.database.database import get_db
from typing import Optional
from app.services.models.user_model import User

# Enhanced security with auto error handling
security = HTTPBearer(
    auto_error=True,
    description="JWT token required in Authorization header with Bearer prefix"
)

def auth_required(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db)
) -> User:
    """Require a valid JWT token for access."""
    token = credentials.credentials
    return get_current_user(token=token, db=db)


def optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Optional authentication - doesn't require a token but uses it if provided."""
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        return get_current_user(token=token, db=db)
    except HTTPException:
        return None


def admin_required(
    user: User = Depends(auth_required)
) -> User:
    """Require an admin user for access."""
    # TODO: Add admin field to User model and check it here
    # For now, we'll just use the auth_required dependency
    return user

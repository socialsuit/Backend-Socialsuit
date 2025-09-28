from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from jose import JWTError, jwt, ExpiredSignatureError
from app.services.database.database import get_db
from core.config import settings
from typing import Optional, Dict, Any
from datetime import datetime

# Import User model at module level to avoid circular imports
from app.services.models.user_model import User

def get_current_user(db: Session = Depends(get_db), token: str = Depends(lambda: None)):
    """Validate JWT token and return the corresponding user."""
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    
    expired_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token has expired",
        headers={"WWW-Authenticate": "Bearer"}
    )
    
    try:
        # Decode the JWT token
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET, 
            algorithms=["HS256"]
        )
        
        # Extract token data
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        # Validate token data
        if user_id is None:
            raise credentials_exception
            
        # Ensure it's an access token, not a refresh token
        if token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"}
            )
            
    except ExpiredSignatureError:
        # Specific error for expired tokens
        raise expired_exception
    except JWTError:
        # General JWT validation error
        raise credentials_exception

    # Get the user from the database
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
        
    # Update last activity time (optional)
    # user.last_activity = datetime.utcnow()
    # db.commit()
    
    return user


def validate_refresh_token(token: str) -> Dict[str, Any]:
    """Validate a refresh token and return its payload."""
    invalid_token_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"}
    )
    
    expired_token_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token has expired",
        headers={"WWW-Authenticate": "Bearer"}
    )
    
    try:
        # Decode the JWT token
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET, 
            algorithms=["HS256"]
        )
        
        # Extract and validate token data
        user_id = payload.get("sub")
        token_type = payload.get("type")
        
        if not user_id or token_type != "refresh":
            raise invalid_token_exception
            
        return payload
        
    except ExpiredSignatureError:
        raise expired_token_exception
    except JWTError:
        raise invalid_token_exception

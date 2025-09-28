# services/auth/controller.py

import uuid
import secrets
from datetime import timedelta, datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.services.auth.email.auth_schema import (
    LoginRequest, RegisterRequest, AuthResponse, UserInDB,
    PasswordResetRequest, PasswordResetConfirmRequest, RefreshTokenRequest
)
from app.services.auth.jwt_handler import create_access_token, create_refresh_token, decode_token
from app.services.models.user_model import User
from passlib.context import CryptContext
from typing import Optional, Dict
from core.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In-memory store for password reset tokens (should use Redis in production)
PASSWORD_RESET_TOKENS: Dict[str, Dict] = {}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password for storing."""
    return pwd_context.hash(password)


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate a user by email and password."""
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


async def register_user(db: Session, request: RegisterRequest) -> AuthResponse:
    """Register a new user."""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(request.password)
    
    new_user = User(
        id=user_id,
        email=request.email,
        hashed_password=hashed_password,
        is_verified=False,  # Require email verification
        created_at=datetime.utcnow(),
        last_login=datetime.utcnow()
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Generate tokens
    access_token = create_access_token(user_id=user_id, email=request.email)
    refresh_token = create_refresh_token(user_id=user_id)
    
    # TODO: Send verification email
    
    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=3600
    )


async def login_user(db: Session, request: LoginRequest) -> AuthResponse:
    """Authenticate a user and return tokens."""
    user = authenticate_user(db, request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Update last login time
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Generate tokens
    access_token = create_access_token(user_id=str(user.id), email=user.email)
    refresh_token = create_refresh_token(user_id=str(user.id))
    
    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=3600
    )


async def request_password_reset(db: Session, request: PasswordResetRequest) -> dict:
    """Request a password reset token."""
    # Check if user exists
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        # Don't reveal that the email doesn't exist for security reasons
        return {"message": "If your email is registered, you will receive a password reset link"}
    
    # Generate a reset token
    reset_token = secrets.token_urlsafe(32)
    
    # Store the token with expiration time (24 hours)
    expiration = datetime.utcnow() + timedelta(hours=24)
    PASSWORD_RESET_TOKENS[reset_token] = {
        "user_id": str(user.id),
        "email": user.email,
        "expires": expiration
    }
    
    # TODO: Send password reset email with the token
    
    return {"message": "If your email is registered, you will receive a password reset link"}


async def confirm_password_reset(db: Session, request: PasswordResetConfirmRequest) -> dict:
    """Reset a user's password using a valid token."""
    # Check if token exists and is valid
    token_data = PASSWORD_RESET_TOKENS.get(request.token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token"
        )
    
    # Check if token is expired
    if datetime.utcnow() > token_data["expires"]:
        # Remove expired token
        PASSWORD_RESET_TOKENS.pop(request.token, None)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token has expired"
        )
    
    # Get user and update password
    user = db.query(User).filter(User.id == token_data["user_id"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update password
    user.hashed_password = get_password_hash(request.new_password)
    db.commit()
    
    # Remove used token
    PASSWORD_RESET_TOKENS.pop(request.token, None)
    
    return {"message": "Password has been reset successfully"}


async def refresh_access_token(request: RefreshTokenRequest) -> AuthResponse:
    """Generate a new access token using a valid refresh token."""
    try:
        # Decode and validate the refresh token
        payload = decode_token(request.refresh_token)
        
        # Check if it's a refresh token
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token type"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token"
            )
        
        # Generate a new access token
        access_token = create_access_token(user_id=user_id)
        
        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=3600
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

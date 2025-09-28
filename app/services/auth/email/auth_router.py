# services/endpoint/auth_router.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.services.auth.email.auth_schema import (
    LoginRequest, RegisterRequest, AuthResponse, 
    PasswordResetRequest, PasswordResetConfirmRequest, RefreshTokenRequest
)
from app.services.auth.email.auth_controller import (
    login_user, register_user, request_password_reset, 
    confirm_password_reset, refresh_access_token
)
from app.services.database.database import get_db

# Import response envelope components
from shared.utils.response_envelope import ResponseEnvelope
from shared.utils.response_wrapper import envelope_response, create_error_response

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=ResponseEnvelope[AuthResponse], status_code=status.HTTP_201_CREATED)
@envelope_response
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user account"""
    try:
        return await register_user(db, request)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/login", response_model=ResponseEnvelope[AuthResponse])
@envelope_response
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login with email and password"""
    try:
        return await login_user(db, request)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )

@router.post("/password-reset/request", response_model=ResponseEnvelope[Dict[str, str]])
@envelope_response
async def password_reset(request: PasswordResetRequest, db: Session = Depends(get_db)):
    """Request a password reset token"""
    try:
        return await request_password_reset(db, request)
    except Exception as e:
        # Always return the same response for security reasons
        return {"message": "If your email is registered, you will receive a password reset link"}

@router.post("/password-reset/confirm", response_model=ResponseEnvelope[Dict[str, str]])
@envelope_response
async def password_reset_confirm(request: PasswordResetConfirmRequest, db: Session = Depends(get_db)):
    """Reset password using a valid token"""
    try:
        return await confirm_password_reset(db, request)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password reset failed: {str(e)}"
        )

@router.post("/refresh", response_model=ResponseEnvelope[AuthResponse])
@envelope_response
async def refresh(request: RefreshTokenRequest):
    """Get a new access token using a refresh token"""
    try:
        return await refresh_access_token(request)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token refresh failed: {str(e)}"
        )

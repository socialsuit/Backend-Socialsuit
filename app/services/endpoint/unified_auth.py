"""Unified Authentication API endpoints."""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.services.database.database import get_db
from app.services.auth.unified_auth_service import auth_service
from app.services.models.user_model import User
from app.services.schemas.auth_schemas import (
    UserCreate, UserCreateWallet, UserLogin, UserLoginWallet,
    WalletChallenge, WalletChallengeResponse, LinkWallet, LinkEmail,
    TokenResponse, RefreshToken, UserProfile, AuthMethodsResponse,
    PasswordChange, ApiResponse
)

# Rate limiting setup
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()

# In-memory storage for wallet challenges (in production, use Redis)
wallet_challenges: Dict[str, Dict[str, Any]] = {}


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> User:
    """Get current authenticated user from JWT token."""
    token = credentials.credentials
    payload = auth_service.verify_token(token, "access")
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user


@router.post("/register/email", response_model=TokenResponse)
@limiter.limit("5/minute")
async def register_with_email(request: Request, user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user with email and password."""
    try:
        user = auth_service.register_user_email(db, user_data.email, user_data.password)
        tokens = auth_service.create_token_pair(user)
        return tokens
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/register/wallet", response_model=TokenResponse)
@limiter.limit("5/minute")
async def register_with_wallet(request: Request, user_data: UserCreateWallet, db: Session = Depends(get_db)):
    """Register a new user with wallet address."""
    try:
        # Verify the wallet signature
        if not auth_service.verify_wallet_signature(user_data.wallet_address, user_data.message, user_data.signature):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid wallet signature"
            )
        
        user = auth_service.register_user_wallet(db, user_data.wallet_address, user_data.network)
        tokens = auth_service.create_token_pair(user)
        return tokens
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login/email", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login_with_email(request: Request, login_data: UserLogin, db: Session = Depends(get_db)):
    """Login with email and password."""
    user = auth_service.authenticate_user_email(db, login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Update last login
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    
    tokens = auth_service.create_token_pair(user)
    return tokens


@router.post("/login/wallet", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login_with_wallet(request: Request, login_data: UserLoginWallet, db: Session = Depends(get_db)):
    """Login with wallet signature."""
    user = auth_service.authenticate_user_wallet(db, login_data.wallet_address, login_data.message, login_data.signature)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid wallet signature or wallet not registered"
        )
    
    # Update last login
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    
    tokens = auth_service.create_token_pair(user)
    return tokens


@router.post("/wallet/challenge", response_model=WalletChallengeResponse)
@limiter.limit("20/minute")
async def get_wallet_challenge(request: Request, challenge_data: WalletChallenge):
    """Get a challenge message for wallet authentication."""
    message = auth_service.generate_wallet_challenge(challenge_data.wallet_address)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    
    # Store challenge temporarily (in production, use Redis with TTL)
    wallet_challenges[challenge_data.wallet_address] = {
        "message": message,
        "expires_at": expires_at
    }
    
    return WalletChallengeResponse(message=message, expires_at=expires_at)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("20/minute")
async def refresh_token(request: Request, token_data: RefreshToken, db: Session = Depends(get_db)):
    """Refresh access token using refresh token."""
    try:
        tokens = auth_service.refresh_access_token(db, token_data.refresh_token)
        return tokens
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/link/wallet", response_model=ApiResponse)
@limiter.limit("5/minute")
async def link_wallet_to_account(request: Request, wallet_data: LinkWallet, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Link a wallet address to the current user account."""
    try:
        # Verify the wallet signature
        if not auth_service.verify_wallet_signature(wallet_data.wallet_address, wallet_data.message, wallet_data.signature):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid wallet signature"
            )
        
        user = auth_service.link_wallet_to_user(db, str(current_user.id), wallet_data.wallet_address, wallet_data.network)
        return ApiResponse(success=True, message="Wallet linked successfully", data={"auth_type": user.auth_type.value})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to link wallet"
        )


@router.post("/link/email", response_model=ApiResponse)
@limiter.limit("5/minute")
async def link_email_to_account(request: Request, email_data: LinkEmail, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Link email and password to the current wallet-only user account."""
    try:
        user = auth_service.link_email_to_user(db, str(current_user.id), email_data.email, email_data.password)
        return ApiResponse(success=True, message="Email linked successfully", data={"auth_type": user.auth_type.value})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to link email"
        )


@router.delete("/unlink/wallet", response_model=ApiResponse)
@limiter.limit("5/minute")
async def unlink_wallet_from_account(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Unlink wallet from the current user account."""
    try:
        user = auth_service.unlink_wallet_from_user(db, str(current_user.id))
        return ApiResponse(success=True, message="Wallet unlinked successfully", data={"auth_type": user.auth_type.value})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unlink wallet"
        )


@router.get("/profile", response_model=UserProfile)
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile with authentication methods."""
    return UserProfile(
        id=str(current_user.id),
        email=current_user.email,
        wallet_address=current_user.wallet_address,
        network=current_user.network,
        auth_type=current_user.auth_type.value if current_user.auth_type else "email",
        is_verified=current_user.is_verified,
        email_verified=current_user.email_verified,
        wallet_verified=current_user.wallet_verified,
        auth_methods=current_user.get_auth_methods(),
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )


@router.get("/methods", response_model=AuthMethodsResponse)
async def get_auth_methods(current_user: User = Depends(get_current_user)):
    """Get available authentication methods for the current user."""
    return AuthMethodsResponse(
        user_id=str(current_user.id),
        auth_methods=current_user.get_auth_methods(),
        has_email=current_user.has_email_auth(),
        has_wallet=current_user.has_wallet_auth(),
        auth_type=current_user.auth_type.value if current_user.auth_type else "email"
    )


@router.post("/change-password", response_model=ApiResponse)
@limiter.limit("3/minute")
async def change_password(request: Request, password_data: PasswordChange, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Change user password."""
    # Verify current password
    if not current_user.hashed_password or not auth_service.verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid current password"
        )
    
    # Update password
    current_user.hashed_password = auth_service.get_password_hash(password_data.new_password)
    db.commit()
    
    return ApiResponse(success=True, message="Password changed successfully")


@router.post("/logout", response_model=ApiResponse)
async def logout(current_user: User = Depends(get_current_user)):
    """Logout user (client should discard tokens)."""
    # In a production environment, you might want to blacklist the token
    # For now, we'll just return a success response
    return ApiResponse(success=True, message="Logged out successfully")


# Add rate limit exception handler
router.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
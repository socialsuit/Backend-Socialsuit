import jwt
from datetime import datetime, timedelta
from typing import Optional
from core.config import settings


def create_access_token(
    user_id: str,
    email: Optional[str] = None,
    wallet_address: Optional[str] = None,
    expires_delta: timedelta = timedelta(hours=1)
) -> str:
    """
    Generates a JWT access token.
    """
    payload = {
        "sub": str(user_id),
        "email": email,
        "wallet_address": wallet_address,
        "type": "access",
        "exp": datetime.utcnow() + expires_delta
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def create_refresh_token(
    user_id: str,
    expires_delta: timedelta = timedelta(days=7)
) -> str:
    """
    Generates a JWT refresh token.
    """
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": datetime.utcnow() + expires_delta
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict:
    """
    Decodes a JWT token.
    """
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")


def generate_token_pair(
    user_id: str,
    email: Optional[str] = None,
    wallet_address: Optional[str] = None
) -> dict:
    """
    Returns both access and refresh tokens in standard format.
    """
    access_token = create_access_token(user_id, email, wallet_address)
    refresh_token = create_refresh_token(user_id)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 3600
    }

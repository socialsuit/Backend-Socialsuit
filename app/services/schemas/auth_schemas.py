"""Pydantic schemas for unified authentication system."""

from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema."""
    email: Optional[EmailStr] = None
    wallet_address: Optional[str] = Field(None, min_length=42, max_length=42)
    network: Optional[str] = Field("ethereum", max_length=50)


class UserCreate(BaseModel):
    """Schema for creating a user with email/password."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserCreateWallet(BaseModel):
    """Schema for creating a user with wallet."""
    wallet_address: str = Field(..., min_length=42, max_length=42)
    network: str = Field("ethereum", max_length=50)
    message: str
    signature: str
    
    @validator('wallet_address')
    def validate_wallet_address(cls, v):
        if not v.startswith('0x'):
            raise ValueError('Wallet address must start with 0x')
        if len(v) != 42:
            raise ValueError('Wallet address must be 42 characters long')
        return v.lower()


class UserLogin(BaseModel):
    """Schema for user login with email/password."""
    email: EmailStr
    password: str


class UserLoginWallet(BaseModel):
    """Schema for user login with wallet."""
    wallet_address: str = Field(..., min_length=42, max_length=42)
    message: str
    signature: str
    
    @validator('wallet_address')
    def validate_wallet_address(cls, v):
        if not v.startswith('0x'):
            raise ValueError('Wallet address must start with 0x')
        if len(v) != 42:
            raise ValueError('Wallet address must be 42 characters long')
        return v.lower()


class WalletChallenge(BaseModel):
    """Schema for wallet authentication challenge."""
    wallet_address: str = Field(..., min_length=42, max_length=42)
    
    @validator('wallet_address')
    def validate_wallet_address(cls, v):
        if not v.startswith('0x'):
            raise ValueError('Wallet address must start with 0x')
        if len(v) != 42:
            raise ValueError('Wallet address must be 42 characters long')
        return v.lower()


class WalletChallengeResponse(BaseModel):
    """Schema for wallet challenge response."""
    message: str
    expires_at: datetime


class LinkWallet(BaseModel):
    """Schema for linking wallet to existing account."""
    wallet_address: str = Field(..., min_length=42, max_length=42)
    network: str = Field("ethereum", max_length=50)
    message: str
    signature: str
    
    @validator('wallet_address')
    def validate_wallet_address(cls, v):
        if not v.startswith('0x'):
            raise ValueError('Wallet address must start with 0x')
        if len(v) != 42:
            raise ValueError('Wallet address must be 42 characters long')
        return v.lower()


class LinkEmail(BaseModel):
    """Schema for linking email to existing wallet account."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class TokenResponse(BaseModel):
    """Schema for token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshToken(BaseModel):
    """Schema for refresh token request."""
    refresh_token: str


class UserProfile(BaseModel):
    """Schema for user profile response."""
    id: str
    email: Optional[str] = None
    wallet_address: Optional[str] = None
    network: Optional[str] = None
    auth_type: str
    is_verified: bool
    email_verified: bool
    wallet_verified: bool
    auth_methods: List[str]
    created_at: datetime
    last_login: datetime
    
    class Config:
        from_attributes = True


class AuthMethodsResponse(BaseModel):
    """Schema for authentication methods response."""
    user_id: str
    auth_methods: List[str]
    has_email: bool
    has_wallet: bool
    auth_type: str


class PasswordChange(BaseModel):
    """Schema for password change request."""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)
    
    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class EmailVerification(BaseModel):
    """Schema for email verification."""
    verification_token: str


class PasswordReset(BaseModel):
    """Schema for password reset request."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""
    reset_token: str
    new_password: str = Field(..., min_length=8, max_length=100)
    
    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class ApiResponse(BaseModel):
    """Generic API response schema."""
    success: bool
    message: str
    data: Optional[dict] = None
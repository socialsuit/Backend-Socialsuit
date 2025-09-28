# services/auth/auth_schema.py
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
import re

class LoginRequest(BaseModel):
    """Schema for user login request."""
    email: EmailStr = Field(..., example="user@example.com", description="Valid email address")
    password: str = Field(..., min_length=8, example="securepassword123", description="Password (min 8 chars)")

class RegisterRequest(BaseModel):
    """Schema for user registration request."""
    email: EmailStr = Field(..., example="user@example.com", description="Valid email address")
    password: str = Field(..., min_length=8, example="securepassword123", description="Password (min 8 chars)")
    confirm_password: str = Field(..., min_length=8, example="securepassword123", description="Confirm password")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('password')
    def password_strength(cls, v):
        # Check for at least one uppercase, one lowercase, one digit, and one special character
        if not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', v):
            raise ValueError('Password must contain at least one uppercase letter, one lowercase letter, one digit, and one special character')
        return v

class PasswordResetRequest(BaseModel):
    """Schema for password reset request."""
    email: EmailStr = Field(..., example="user@example.com", description="Email address for password reset")

class PasswordResetConfirmRequest(BaseModel):
    """Schema for password reset confirmation."""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, example="newSecurePassword123", description="New password (min 8 chars)")
    confirm_password: str = Field(..., min_length=8, example="newSecurePassword123", description="Confirm new password")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('new_password')
    def password_strength(cls, v):
        # Check for at least one uppercase, one lowercase, one digit, and one special character
        if not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', v):
            raise ValueError('Password must contain at least one uppercase letter, one lowercase letter, one digit, and one special character')
        return v

class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request."""
    refresh_token: str = Field(..., description="Refresh token to get a new access token")

class TokenData(BaseModel):
    """Schema for decoded JWT token data."""
    user_id: Optional[str] = None
    email: Optional[EmailStr] = None
    token_type: Optional[str] = None

class AuthResponse(BaseModel):
    """Schema for authentication response."""
    access_token: str = Field(..., example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
    token_type: str = Field(default="bearer", example="bearer")
    expires_in: Optional[int] = Field(default=3600, example=3600, description="Token expiry in seconds")
    refresh_token: Optional[str] = Field(None, example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")

class UserInDB(BaseModel):
    """Schema for user data in database."""
    id: str
    email: EmailStr
    hashed_password: str
    disabled: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


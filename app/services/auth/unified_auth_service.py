"""Unified Authentication Service for Social Suit and Suit Research."""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
from fastapi import HTTPException, status
from passlib.context import CryptContext
from jose import JWTError, jwt
from eth_account.messages import encode_defunct
from eth_account import Account
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.services.models.user_model import User, AuthType
from app.services.core.config import settings


class UnifiedAuthService:
    """Unified authentication service supporting email/password and wallet authentication."""
    
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 7
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against its hash."""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Generate password hash."""
        return self.pwd_context.hash(password)
    
    def create_access_token(self, data: Dict[str, Any]) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=self.algorithm)
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create JWT refresh token."""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)
        to_encode.update({"exp": expire, "type": "refresh"})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=self.algorithm)
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[self.algorithm])
            if payload.get("type") != token_type:
                return None
            return payload
        except JWTError:
            return None
    
    def verify_wallet_signature(self, wallet_address: str, message: str, signature: str) -> bool:
        """Verify wallet signature for authentication."""
        try:
            # Create the message that was signed
            message_hash = encode_defunct(text=message)
            
            # Recover the address from the signature
            recovered_address = Account.recover_message(message_hash, signature=signature)
            
            # Compare addresses (case-insensitive)
            return recovered_address.lower() == wallet_address.lower()
        except Exception:
            return False
    
    def generate_wallet_challenge(self, wallet_address: str) -> str:
        """Generate a challenge message for wallet authentication."""
        timestamp = int(datetime.now(timezone.utc).timestamp())
        nonce = secrets.token_hex(16)
        return f"Sign this message to authenticate with Social Suit:\nWallet: {wallet_address}\nTimestamp: {timestamp}\nNonce: {nonce}"
    
    def authenticate_user_email(self, db: Session, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password."""
        user = db.query(User).filter(User.email == email).first()
        if not user or not user.hashed_password:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user
    
    def authenticate_user_wallet(self, db: Session, wallet_address: str, message: str, signature: str) -> Optional[User]:
        """Authenticate user with wallet signature."""
        if not self.verify_wallet_signature(wallet_address, message, signature):
            return None
        
        user = db.query(User).filter(User.wallet_address == wallet_address.lower()).first()
        return user
    
    def register_user_email(self, db: Session, email: str, password: str) -> User:
        """Register a new user with email and password."""
        # Check if email already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user
        hashed_password = self.get_password_hash(password)
        user = User(
            email=email,
            hashed_password=hashed_password,
            auth_type=AuthType.EMAIL,
            email_verified=False
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    def register_user_wallet(self, db: Session, wallet_address: str, network: str = "ethereum") -> User:
        """Register a new user with wallet address."""
        # Check if wallet already exists
        existing_user = db.query(User).filter(User.wallet_address == wallet_address.lower()).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Wallet already registered"
            )
        
        # Create new user
        user = User(
            wallet_address=wallet_address.lower(),
            network=network,
            auth_type=AuthType.WALLET,
            wallet_verified=True  # Wallet is verified through signature
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    def link_wallet_to_user(self, db: Session, user_id: str, wallet_address: str, network: str = "ethereum") -> User:
        """Link a wallet address to an existing user account."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if wallet is already linked to another user
        existing_wallet_user = db.query(User).filter(
            User.wallet_address == wallet_address.lower(),
            User.id != user_id
        ).first()
        if existing_wallet_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Wallet already linked to another account"
            )
        
        # Link wallet to user
        user.wallet_address = wallet_address.lower()
        user.network = network
        user.wallet_verified = True
        user.update_auth_type()
        
        db.commit()
        db.refresh(user)
        return user
    
    def link_email_to_user(self, db: Session, user_id: str, email: str, password: str) -> User:
        """Link email and password to an existing wallet-only user account."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if email is already linked to another user
        existing_email_user = db.query(User).filter(
            User.email == email,
            User.id != user_id
        ).first()
        if existing_email_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already linked to another account"
            )
        
        # Link email to user
        user.email = email
        user.hashed_password = self.get_password_hash(password)
        user.email_verified = False
        user.update_auth_type()
        
        db.commit()
        db.refresh(user)
        return user
    
    def unlink_wallet_from_user(self, db: Session, user_id: str) -> User:
        """Unlink wallet from user account."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Ensure user has email auth before unlinking wallet
        if not user.has_email_auth():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot unlink wallet: user must have email authentication set up"
            )
        
        user.wallet_address = None
        user.network = None
        user.wallet_verified = False
        user.update_auth_type()
        
        db.commit()
        db.refresh(user)
        return user
    
    def create_token_pair(self, user: User) -> Dict[str, str]:
        """Create access and refresh token pair for user."""
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "wallet_address": user.wallet_address,
            "auth_type": user.auth_type.value if user.auth_type else "email"
        }
        
        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token({"sub": str(user.id)})
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    def refresh_access_token(self, db: Session, refresh_token: str) -> Dict[str, str]:
        """Refresh access token using refresh token."""
        payload = self.verify_token(refresh_token, "refresh")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return self.create_token_pair(user)


# Global instance
auth_service = UnifiedAuthService()
import uuid
from typing import List, Optional
from sqlalchemy import Column, String, Boolean, DateTime, Index, UniqueConstraint, Enum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship, Mapped
from datetime import datetime, timezone
from enum import Enum as PyEnum
from app.services.database.database import Base


class AuthType(PyEnum):
    EMAIL = "email"
    WALLET = "wallet"
    HYBRID = "hybrid"  # User has both email and wallet linked


class User(Base):
    __tablename__ = "users"   # Fixed: double underscore for tablename

    # ✅ Primary key: UUID, PostgreSQL-native
    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        index=True
    )

    # ✅ Email
    email = Column(
        String(255),
        unique=True,
        nullable=True,
        index=True
    )

    # ✅ Hashed Password — nullable=True for wallet-only logins
    hashed_password = Column(
        String(255),
        nullable=True
    )

    # ✅ Wallet Address — for Web3 users
    wallet_address = Column(
        String(42),  # 42 chars for Ethereum-style addresses
        unique=True,
        nullable=True,
        index=True
    )

    network = Column(
        String(50),
        nullable=True,
        default="ethereum"
    )

    # ✅ Authentication type tracking
    auth_type = Column(
        Enum(AuthType),
        nullable=False,
        default=AuthType.EMAIL
    )

    is_verified = Column(
        Boolean,
        default=False,
        nullable=False
    )

    # ✅ Email verification status
    email_verified = Column(
        Boolean,
        default=False,
        nullable=False
    )

    # ✅ Wallet verification status
    wallet_verified = Column(
        Boolean,
        default=False,
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    last_login = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    __table_args__ = (
        Index('idx_wallet_network', 'wallet_address', 'network'),
        Index('idx_auth_type', 'auth_type'),
        UniqueConstraint('email', name='uq_user_email'),
        UniqueConstraint('wallet_address', name='uq_user_wallet'),
        {'extend_existing': True}
    )
    
    def has_email_auth(self) -> bool:
        """Check if user has email authentication set up."""
        return self.email is not None and self.hashed_password is not None
    
    def has_wallet_auth(self) -> bool:
        """Check if user has wallet authentication set up."""
        return self.wallet_address is not None
    
    def get_auth_methods(self) -> List[str]:
        """Get list of available authentication methods for this user."""
        methods = []
        if self.has_email_auth():
            methods.append("email")
        if self.has_wallet_auth():
            methods.append("wallet")
        return methods
    
    def update_auth_type(self):
        """Update auth_type based on available authentication methods."""
        if self.has_email_auth() and self.has_wallet_auth():
            self.auth_type = AuthType.HYBRID
        elif self.has_wallet_auth():
            self.auth_type = AuthType.WALLET
        else:
            self.auth_type = AuthType.EMAIL
    
    # Relationships
    platform_tokens = relationship("PlatformToken", back_populates="user", cascade="all, delete-orphan")
    scheduled_posts = relationship("ScheduledPost", back_populates="user", cascade="all, delete-orphan")
    post_engagements = relationship("PostEngagement", back_populates="user", cascade="all, delete-orphan")
    user_metrics = relationship("UserMetrics", back_populates="user", cascade="all, delete-orphan")
    content_performance = relationship("ContentPerformance", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, wallet={self.wallet_address})>"
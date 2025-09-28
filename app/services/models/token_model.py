from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.services.database.database import Base

class PlatformToken(Base):
    __tablename__ = "platform_tokens"   # ✅ Correct magic attribute

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(String, index=True)  # e.g. facebook, instagram, twitter
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    channel_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship back to user
    user = relationship("User", back_populates="platform_tokens")
    
    __table_args__ = (
        Index('idx_platform_user', 'platform', 'user_id'),
        {'extend_existing': True}
    )
    
    def __repr__(self):   # Fixed: double underscore for repr
        return f"<PlatformToken(platform={self.platform}, user_id={self.user_id})>"
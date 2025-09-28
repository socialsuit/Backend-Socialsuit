from sqlalchemy import Column, Integer, String, DateTime, JSON, Enum, ForeignKey, Index, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY
from app.services.database.database import Base
import enum

class PostStatus(str, enum.Enum):
    PENDING = "pending"
    PUBLISHING = "publishing"
    PUBLISHED = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"

class ScheduledPost(Base):
    __tablename__= "scheduled_posts" 

    id = Column(Integer, primary_key=True, index=True)
    
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)  # link to user_model
    
    # Relationship back to user
    user = relationship("User", back_populates="scheduled_posts")
    platform = Column(String)  # e.g. facebook, instagram
    
    post_payload = Column(JSON)  # e.g. {"caption": "...", "image_url": "..."}
    
    scheduled_time = Column(DateTime)  # e.g. 2025-06-24T05:00:00Z
    
    status = Column(Enum(PostStatus), default=PostStatus.PENDING)
    retries = Column(Integer, default=0)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    __table_args__ = (
        Index('idx_scheduled_time', 'scheduled_time'),
        Index('idx_user_platform', 'user_id', 'platform'),
        Index('idx_status', 'status'),
        {'extend_existing': True, 'sqlite_autoincrement': True}
    )
    
    def __repr__(self):
        return f"<ScheduledPost(id={self.id}, user_id={self.user_id}, platform={self.platform}, status={self.status})"
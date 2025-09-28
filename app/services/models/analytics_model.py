from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, ForeignKey, Index, Enum, Table
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from app.services.database.database import Base
import enum
from datetime import datetime

class EngagementType(str, enum.Enum):
    like = "like"
    comment = "comment"
    share = "share"
    click = "click"
    view = "view"
    save = "save"
    impression = "impression"

class PostEngagement(Base):
    """Stores individual engagement events for posts"""
    __tablename__ = "post_engagements"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Link to user who owns the post
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Platform and post identifiers
    platform = Column(String, nullable=False, index=True)  # e.g., facebook, instagram, twitter
    platform_post_id = Column(String, nullable=False, index=True)  # ID of the post on the platform
    
    # Engagement details
    engagement_type = Column(Enum(EngagementType), nullable=False, index=True)
    engagement_count = Column(Integer, default=1, nullable=False)  # Number of this type of engagement
    
    # Metadata
    engagement_date = Column(DateTime, nullable=False, index=True)  # When the engagement occurred
    engagement_metadata = Column(JSON, nullable=True)  # Additional platform-specific data
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="post_engagements")
    
    __table_args__ = (
        Index('idx_post_platform_date', 'platform', 'platform_post_id', 'engagement_date'),
        Index('idx_user_platform', 'user_id', 'platform'),
        {'extend_existing': True}
    )
    
    def __repr__(self):
        return f"<PostEngagement(id={self.id}, platform={self.platform}, type={self.engagement_type})>"

class UserMetrics(Base):
    """Stores aggregated user metrics by day"""
    __tablename__ = "user_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Link to user
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Time period
    date = Column(DateTime, nullable=False, index=True)  # Date of these metrics
    platform = Column(String, nullable=False, index=True)  # e.g., facebook, instagram, twitter
    
    # Follower metrics
    followers_count = Column(Integer, nullable=True)  # Total followers
    followers_growth = Column(Integer, nullable=True)  # Change in followers
    
    # Engagement metrics
    engagement_rate = Column(Float, nullable=True)  # Average engagement rate for the day
    total_engagements = Column(Integer, nullable=True)  # Total engagements across all types
    
    # Post metrics
    posts_count = Column(Integer, nullable=True)  # Number of posts made
    
    # Detailed engagement breakdown
    engagement_breakdown = Column(JSON, nullable=True)  # e.g., {"likes": 120, "comments": 45}
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="user_metrics")
    
    __table_args__ = (
        Index('idx_user_date_platform', 'user_id', 'date', 'platform', unique=True),
        {'extend_existing': True}
    )
    
    def __repr__(self):
        return f"<UserMetrics(user_id={self.user_id}, date={self.date}, platform={self.platform})>"

class ContentPerformance(Base):
    """Stores performance metrics for individual content pieces"""
    __tablename__ = "content_performance"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Link to user who owns the content
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Content identifiers
    platform = Column(String, nullable=False, index=True)  # e.g., facebook, instagram, twitter
    platform_post_id = Column(String, nullable=False, index=True)  # ID of the post on the platform
    content_type = Column(String, nullable=False)  # e.g., post, video, story, reel
    
    # Performance metrics
    impressions = Column(Integer, nullable=True)
    reach = Column(Integer, nullable=True)
    engagement_count = Column(Integer, nullable=True)  # Total engagements
    engagement_rate = Column(Float, nullable=True)  # Engagement rate percentage
    
    # Detailed metrics
    likes = Column(Integer, nullable=True)
    comments = Column(Integer, nullable=True)
    shares = Column(Integer, nullable=True)
    saves = Column(Integer, nullable=True)
    clicks = Column(Integer, nullable=True)
    
    # Content metadata
    post_date = Column(DateTime, nullable=False, index=True)  # When the content was posted
    content_metadata = Column(JSON, nullable=True)  # Additional content data (hashtags, mentions, etc.)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="content_performance")
    
    __table_args__ = (
        Index('idx_platform_post', 'platform', 'platform_post_id', unique=True),
        Index('idx_user_platform_date', 'user_id', 'platform', 'post_date'),
        {'extend_existing': True}
    )
    
    def __repr__(self):
        return f"<ContentPerformance(platform={self.platform}, post_id={self.platform_post_id})>"
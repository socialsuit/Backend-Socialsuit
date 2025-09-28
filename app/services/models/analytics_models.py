from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Float, Integer, Text, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.services.database.database import Base

class PostEngagement(Base):
    """Model for tracking engagement metrics for individual posts"""
    __tablename__ = "post_engagements"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(String, nullable=False, index=True)  # e.g., "twitter", "facebook", "instagram"
    post_id = Column(String, nullable=False, index=True)   # Platform-specific post ID
    post_url = Column(String)                              # URL to the post
    post_content = Column(Text)                            # Content of the post
    post_type = Column(String)                             # e.g., "text", "image", "video", "link"
    post_date = Column(DateTime, nullable=False, index=True)
    
    # Engagement metrics
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    reach = Column(Integer, default=0)
    engagement_rate = Column(Float, default=0.0)
    
    # Additional platform-specific metrics stored as JSON
    platform_metrics = Column(JSON, default={})
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="post_engagements")
    
    __table_args__ = (
        Index('idx_post_engagement_user_platform', 'user_id', 'platform'),
        Index('idx_post_engagement_date', 'post_date'),
        {'extend_existing': True}
    )
    
    def __repr__(self):
        return f"<PostEngagement(id={self.id}, platform={self.platform}, post_id={self.post_id})>"

class UserMetrics(Base):
    """Model for tracking user-level metrics across platforms"""
    __tablename__ = "user_metrics"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(String, nullable=False, index=True)  # e.g., "twitter", "facebook", "instagram"
    date = Column(DateTime, nullable=False, index=True)    # Date of the metrics snapshot
    
    # Audience metrics
    followers = Column(Integer, default=0)
    following = Column(Integer, default=0)
    total_posts = Column(Integer, default=0)
    
    # Engagement metrics
    total_engagement = Column(Integer, default=0)
    engagement_rate = Column(Float, default=0.0)
    
    # Reach and impression metrics
    total_impressions = Column(Integer, default=0)
    total_reach = Column(Integer, default=0)
    
    # Growth metrics
    followers_change = Column(Integer, default=0)  # Change since last snapshot
    engagement_change = Column(Float, default=0.0)  # Change since last snapshot
    
    # Additional platform-specific metrics stored as JSON
    platform_metrics = Column(JSON, default={})
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="user_metrics")
    
    __table_args__ = (
        Index('idx_user_metrics_user_platform', 'user_id', 'platform'),
        Index('idx_user_metrics_date', 'date'),
        {'extend_existing': True}
    )
    
    def __repr__(self):
        return f"<UserMetrics(id={self.id}, user_id={self.user_id}, platform={self.platform}, date={self.date})>"

class ContentPerformance(Base):
    """Model for analyzing content performance patterns"""
    __tablename__ = "content_performance"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(String, nullable=False, index=True)  # e.g., "twitter", "facebook", "instagram"
    
    # Content categorization
    content_type = Column(String, index=True)  # e.g., "text", "image", "video", "link"
    content_category = Column(String, index=True)  # e.g., "product", "lifestyle", "educational"
    content_tags = Column(String, default="[]")  # Tags or topics in the content
    
    # Time-based analysis
    post_hour = Column(Integer, index=True)  # Hour of day (0-23)
    post_day = Column(Integer, index=True)   # Day of week (0-6, 0=Monday)
    post_date = Column(DateTime, index=True) # Full date of post
    
    # Performance metrics
    engagement_rate = Column(Float, default=0.0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    reach = Column(Integer, default=0)
    
    # Reference to original post
    post_id = Column(String, nullable=False)
    post_url = Column(String)
    
    # Additional analysis data
    performance_score = Column(Float, default=0.0)  # Composite score based on multiple metrics
    analysis_data = Column(JSON, default={})        # Additional analysis results
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="content_performance")
    
    __table_args__ = (
        Index('idx_content_performance_user_platform', 'user_id', 'platform'),
        Index('idx_content_performance_type', 'content_type'),
        Index('idx_content_performance_time', 'post_hour', 'post_day'),
        {'extend_existing': True}
    )
    
    def __repr__(self):
        return f"<ContentPerformance(id={self.id}, platform={self.platform}, post_id={self.post_id})>"
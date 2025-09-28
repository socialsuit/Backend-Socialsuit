"""
Comprehensive Pydantic Validation Models for API Security

This module provides secure, validated input models for all API endpoints
with proper sanitization, validation, and security checks.
"""

import re
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, validator, model_validator
from enum import Enum
import html

# Security constants
MAX_TEXT_LENGTH = 10000
MAX_SHORT_TEXT_LENGTH = 500
MAX_USERNAME_LENGTH = 50
MAX_EMAIL_LENGTH = 254
MAX_URL_LENGTH = 2048
MAX_PLATFORM_COUNT = 10
MAX_TAGS_COUNT = 20
MAX_TAG_LENGTH = 50

# Allowed platforms
class PlatformType(str, Enum):
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    TELEGRAM = "telegram"
    FARCASTER = "farcaster"

# Content types
class ContentType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    LINK = "link"
    POLL = "poll"

# Metrics for analytics
class MetricType(str, Enum):
    ENGAGEMENT_RATE = "engagement_rate"
    FOLLOWERS = "followers"
    IMPRESSIONS = "impressions"
    CLICKS = "clicks"
    SHARES = "shares"
    COMMENTS = "comments"
    LIKES = "likes"
    REACH = "reach"

# Chart types
class ChartType(str, Enum):
    TIME_SERIES = "time_series"
    PLATFORM_COMPARISON = "platform_comparison"
    ENGAGEMENT_BREAKDOWN = "engagement_breakdown"
    CONTENT_PERFORMANCE = "content_performance"

# Time grouping options
class TimeGrouping(str, Enum):
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"

class BaseValidationModel(BaseModel):
    """Base model with common validation methods."""
    
    @validator('*', pre=True)
    def sanitize_strings(cls, v):
        """Sanitize string inputs to prevent XSS."""
        if isinstance(v, str):
            # HTML escape
            v = html.escape(v)
            # Remove null bytes
            v = v.replace('\x00', '')
            # Normalize whitespace
            v = ' '.join(v.split())
        return v
    
    class Config:
        # Allow population by field name or alias
        populate_by_name = True

# User-related validation models
class UserIdValidation(BaseValidationModel):
    """Validation for user ID parameters."""
    user_id: str = Field(
        ..., 
        min_length=1, 
        max_length=100,
        pattern=r'^[a-zA-Z0-9_-]+$',
        description="User identifier (alphanumeric, underscore, hyphen only)"
    )

class EmailValidation(BaseValidationModel):
    """Email validation with security checks."""
    email: str = Field(
        ...,
        max_length=MAX_EMAIL_LENGTH,
        pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        description="Valid email address"
    )
    
    @validator('email')
    def validate_email_security(cls, v):
        """Additional email security validation."""
        # Convert to lowercase
        v = v.lower()
        # Check for suspicious patterns
        suspicious_patterns = [
            r'\.{2,}',  # Multiple consecutive dots
            r'^\.|\.$',  # Starting or ending with dot
            r'[<>"\']',  # HTML/script injection characters
        ]
        for pattern in suspicious_patterns:
            if re.search(pattern, v):
                raise ValueError("Invalid email format")
        return v

# Content validation models
class ContentValidation(BaseValidationModel):
    """Validation for content text."""
    content: str = Field(
        ...,
        min_length=1,
        max_length=MAX_TEXT_LENGTH,
        description="Content text"
    )
    
    @validator('content')
    def validate_content_security(cls, v):
        """Validate content for security issues."""
        # Check for script injection
        script_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'data:text/html',
        ]
        for pattern in script_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("Content contains potentially malicious code")
        
        # Check for excessive special characters (potential injection)
        special_char_ratio = len(re.findall(r'[<>"\'\(\)\{\}\[\]\\]', v)) / len(v)
        if special_char_ratio > 0.1:  # More than 10% special characters
            raise ValueError("Content contains too many special characters")
        
        return v

class UrlValidation(BaseValidationModel):
    """URL validation with security checks."""
    url: str = Field(
        ...,
        max_length=MAX_URL_LENGTH,
        pattern=r'^https?://[^\s/$.?#].[^\s]*$',
        description="Valid HTTP/HTTPS URL"
    )
    
    @validator('url')
    def validate_url_security(cls, v):
        """Validate URL for security issues."""
        # Convert to lowercase for checking
        v_lower = v.lower()
        
        # Block dangerous protocols
        dangerous_protocols = ['javascript:', 'data:', 'vbscript:', 'file:']
        for protocol in dangerous_protocols:
            if v_lower.startswith(protocol):
                raise ValueError("Dangerous URL protocol detected")
        
        # Block localhost and private IPs in production
        localhost_patterns = [
            r'://localhost[:/]',
            r'://127\.0\.0\.1[:/]',
            r'://192\.168\.',
            r'://10\.',
            r'://172\.(1[6-9]|2[0-9]|3[01])\.',
        ]
        for pattern in localhost_patterns:
            if re.search(pattern, v_lower):
                raise ValueError("Private/localhost URLs not allowed")
        
        return v

# Platform and scheduling validation
class PlatformValidation(BaseValidationModel):
    """Platform validation."""
    platform: PlatformType = Field(..., description="Social media platform")

class PlatformsValidation(BaseValidationModel):
    """Multiple platforms validation."""
    platforms: List[PlatformType] = Field(
        ...,
        min_items=1,
        max_items=MAX_PLATFORM_COUNT,
        description="List of social media platforms"
    )
    
    @validator('platforms')
    def validate_unique_platforms(cls, v):
        """Ensure platforms are unique."""
        if len(v) != len(set(v)):
            raise ValueError("Duplicate platforms not allowed")
        return v

class DateTimeValidation(BaseValidationModel):
    """DateTime validation with security checks."""
    scheduled_time: datetime = Field(..., description="Scheduled date and time")
    
    @validator('scheduled_time')
    def validate_future_time(cls, v):
        """Ensure scheduled time is in the future."""
        if v <= datetime.utcnow():
            raise ValueError("Scheduled time must be in the future")
        
        # Prevent scheduling too far in the future (1 year max)
        max_future = datetime.utcnow() + timedelta(days=365)
        if v > max_future:
            raise ValueError("Cannot schedule more than 1 year in advance")
        
        return v

# Analytics validation models
class AnalyticsTimeRangeValidation(BaseValidationModel):
    """Time range validation for analytics."""
    days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Number of days to analyze (1-365)"
    )

class AnalyticsQueryValidation(BaseValidationModel):
    """Analytics query validation."""
    user_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r'^[a-zA-Z0-9_-]+$'
    )
    days: int = Field(default=30, ge=1, le=365)
    platform: Optional[PlatformType] = None
    metric: Optional[MetricType] = None

class ChartDataValidation(BaseValidationModel):
    """Chart data request validation."""
    chart_type: ChartType = Field(..., description="Type of chart to generate")
    user_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r'^[a-zA-Z0-9_-]+$'
    )
    metric: MetricType = Field(..., description="Metric to chart")
    platform: Optional[PlatformType] = None
    days: int = Field(default=30, ge=1, le=365)
    group_by: TimeGrouping = Field(default=TimeGrouping.DAY, description="Time grouping")

# A/B Testing validation models
class ABTestContentValidation(BaseValidationModel):
    """A/B test content validation."""
    content_a: str = Field(
        ...,
        min_length=1,
        max_length=MAX_TEXT_LENGTH,
        description="First content variation"
    )
    content_b: str = Field(
        ...,
        min_length=1,
        max_length=MAX_TEXT_LENGTH,
        description="Second content variation"
    )
    
    @validator('content_a', 'content_b')
    def validate_content_differences(cls, v, values):
        """Ensure content variations are different."""
        if 'content_a' in values and v == values['content_a']:
            raise ValueError("Content variations must be different")
        return v
    
    @model_validator(mode='after')
    def validate_content_similarity(self):
        """Ensure content variations are sufficiently different."""
        content_a = getattr(self, 'content_a', '')
        content_b = getattr(self, 'content_b', '')
        
        if content_a and content_b:
            # Simple similarity check (can be enhanced with more sophisticated algorithms)
            similarity = len(set(content_a.lower().split()) & set(content_b.lower().split()))
            total_words = len(set(content_a.lower().split()) | set(content_b.lower().split()))
            
            if total_words > 0 and similarity / total_words > 0.8:
                raise ValueError("Content variations are too similar")
        
        return self

class ABTestConfigValidation(BaseValidationModel):
    """A/B test configuration validation."""
    test_name: Optional[str] = Field(
        None,
        max_length=MAX_SHORT_TEXT_LENGTH,
        description="Test name for tracking"
    )
    target_metric: MetricType = Field(
        default=MetricType.ENGAGEMENT_RATE,
        description="Metric to optimize"
    )
    audience_percentage: float = Field(
        default=0.5,
        ge=0.1,
        le=1.0,
        description="Percentage of audience to include (0.1-1.0)"
    )
    platforms: List[PlatformType] = Field(
        default=[PlatformType.TWITTER],
        min_items=1,
        max_items=MAX_PLATFORM_COUNT
    )

# Scheduled post validation models
class ScheduledPostValidation(BaseValidationModel):
    """Scheduled post validation."""
    content: str = Field(
        ...,
        min_length=1,
        max_length=MAX_TEXT_LENGTH
    )
    platform: PlatformType = Field(...)
    scheduled_time: datetime = Field(...)
    media_urls: Optional[List[str]] = Field(
        None,
        max_items=10,
        description="Media URLs (max 10)"
    )
    tags: Optional[List[str]] = Field(
        None,
        max_items=MAX_TAGS_COUNT,
        description="Content tags"
    )
    
    @validator('media_urls')
    def validate_media_urls(cls, v):
        """Validate media URLs."""
        if v:
            for url in v:
                # Basic URL validation
                if not re.match(r'^https?://[^\s/$.?#].[^\s]*$', url):
                    raise ValueError(f"Invalid media URL: {url}")
                # Check file extension for media files
                allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mov', '.avi']
                if not any(url.lower().endswith(ext) for ext in allowed_extensions):
                    raise ValueError(f"Unsupported media type: {url}")
        return v
    
    @validator('tags')
    def validate_tags(cls, v):
        """Validate content tags."""
        if v:
            for tag in v:
                if len(tag) > MAX_TAG_LENGTH:
                    raise ValueError(f"Tag too long: {tag}")
                if not re.match(r'^[a-zA-Z0-9_-]+$', tag):
                    raise ValueError(f"Invalid tag format: {tag}")
        return v
    
    @validator('scheduled_time')
    def validate_scheduled_time(cls, v):
        """Validate scheduled time."""
        if v <= datetime.utcnow():
            raise ValueError("Scheduled time must be in the future")
        
        max_future = datetime.utcnow() + timedelta(days=365)
        if v > max_future:
            raise ValueError("Cannot schedule more than 1 year in advance")
        
        return v

# Search and pagination validation
class SearchValidation(BaseValidationModel):
    """Search query validation."""
    query: str = Field(
        ...,
        min_length=1,
        max_length=MAX_SHORT_TEXT_LENGTH,
        description="Search query"
    )
    
    @validator('query')
    def validate_search_query(cls, v):
        """Validate search query for security."""
        # Remove potential injection patterns
        dangerous_patterns = [
            r'[<>"\']',  # HTML/script injection
            r'\\x[0-9a-fA-F]{2}',  # Hex encoding
            r'%[0-9a-fA-F]{2}',  # URL encoding of dangerous chars
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, v):
                raise ValueError("Search query contains invalid characters")
        
        return v.strip()

class PaginationValidation(BaseValidationModel):
    """Pagination parameters validation."""
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of items per page (1-100)"
    )
    offset: int = Field(
        default=0,
        ge=0,
        le=10000,
        description="Number of items to skip (0-10000)"
    )

# File upload validation
class FileUploadValidation(BaseValidationModel):
    """File upload validation."""
    filename: str = Field(
        ...,
        max_length=255,
        description="Original filename"
    )
    content_type: str = Field(
        ...,
        max_length=100,
        description="MIME content type"
    )
    
    @validator('filename')
    def validate_filename(cls, v):
        """Validate filename for security."""
        # Remove path traversal attempts
        v = v.replace('..', '').replace('/', '').replace('\\', '')
        
        # Check for dangerous extensions
        dangerous_extensions = [
            '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js',
            '.jar', '.php', '.asp', '.aspx', '.jsp', '.py', '.rb', '.pl'
        ]
        
        for ext in dangerous_extensions:
            if v.lower().endswith(ext):
                raise ValueError(f"File type not allowed: {ext}")
        
        # Ensure filename is not empty after sanitization
        if not v.strip():
            raise ValueError("Invalid filename")
        
        return v.strip()
    
    @validator('content_type')
    def validate_content_type(cls, v):
        """Validate MIME content type."""
        allowed_types = [
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'video/mp4', 'video/quicktime', 'video/x-msvideo',
            'text/plain', 'application/json'
        ]
        
        if v not in allowed_types:
            raise ValueError(f"Content type not allowed: {v}")
        
        return v

# Bulk operations validation
class BulkOperationValidation(BaseValidationModel):
    """Bulk operation validation."""
    ids: List[str] = Field(
        ...,
        min_items=1,
        max_items=100,
        description="List of IDs (max 100)"
    )
    
    @validator('ids')
    def validate_ids(cls, v):
        """Validate ID list."""
        # Check for duplicates
        if len(v) != len(set(v)):
            raise ValueError("Duplicate IDs not allowed")
        
        # Validate each ID format
        for id_val in v:
            if not re.match(r'^[a-zA-Z0-9_-]+$', id_val):
                raise ValueError(f"Invalid ID format: {id_val}")
        
        return v

# Combined validation models for specific endpoints
class CreateScheduledPostRequest(ScheduledPostValidation, UserIdValidation):
    """Complete validation for creating scheduled posts."""
    pass

class AnalyticsRequest(AnalyticsQueryValidation):
    """Complete validation for analytics requests."""
    pass

class ABTestRequest(ABTestContentValidation, ABTestConfigValidation, UserIdValidation):
    """Complete validation for A/B test creation."""
    pass

class SearchRequest(SearchValidation, PaginationValidation, UserIdValidation):
    """Complete validation for search requests."""
    pass

class BulkUpdateRequest(BulkOperationValidation, UserIdValidation):
    """Complete validation for bulk update requests."""
    status: str = Field(
        ...,
        pattern=r'^(draft|scheduled|published|failed|cancelled)$',
        description="New status for posts"
    )
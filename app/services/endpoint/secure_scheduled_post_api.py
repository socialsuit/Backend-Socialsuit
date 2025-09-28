"""
Secure Scheduled Post API with Enhanced Validation and Security

This module provides secure API endpoints for scheduled post management with:
- Comprehensive input validation using Pydantic models
- Rate limiting integration
- Security audit compliance
- Enhanced error handling
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, validator
import uuid
import logging

from app.services.database.database import get_db
from app.services.models.scheduled_post_model import ScheduledPost, PostStatus
from app.services.models.user_model import User
from app.services.scheduled_post_service import ScheduledPostService
from app.services.dependencies.scheduled_post_providers import get_scheduled_post_service
from app.services.auth.auth_guard import auth_required
from app.services.utils.logger_config import setup_logger

# Import security validation models
from app.services.security.validation_models import (
    ScheduledPostValidation,
    UserIdValidation,
    PaginationValidation,
    SearchValidation,
    BulkOperationValidation,
    PlatformType,
    ContentType,
    DateTimeValidation
)

# Set up logger
logger = setup_logger("secure_scheduled_post_api")

# Enhanced request/response models with security validation
class SecureScheduledPostRequest(ScheduledPostValidation):
    """Secure request model for creating scheduled posts with comprehensive validation."""
    
    # Additional validation for business logic
    @validator('content')
    def validate_content_length_by_platform(cls, v, values):
        """Validate content length based on platform requirements."""
        platform = values.get('platform')
        if platform == PlatformType.TWITTER and len(v) > 280:
            raise ValueError("Twitter posts cannot exceed 280 characters")
        elif platform == PlatformType.LINKEDIN and len(v) > 3000:
            raise ValueError("LinkedIn posts cannot exceed 3000 characters")
        return v
    
    @validator('scheduled_time')
    def validate_business_hours(cls, v, values):
        """Optional: Validate posting during business hours."""
        # This is an example - you might want to allow scheduling outside business hours
        hour = v.hour
        if hour < 6 or hour > 22:  # Outside 6 AM - 10 PM
            logger.warning(f"Post scheduled outside recommended hours: {hour}")
        return v

class SecureScheduledPostResponse(BaseModel):
    """Secure response model for scheduled posts."""
    id: str = Field(..., description="Unique identifier for the scheduled post")
    content: str = Field(..., description="The main text content of the post")
    platform: PlatformType = Field(..., description="Social media platform")
    scheduled_time: datetime = Field(..., description="When to publish the post")
    status: str = Field(..., description="Current status of the scheduled post")
    media_urls: List[str] = Field(default=[], description="List of media URLs")
    tags: List[str] = Field(default=[], description="Content tags")
    created_at: datetime = Field(..., description="When the post was created")
    updated_at: Optional[datetime] = Field(None, description="When the post was last updated")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "post_123456",
                "content": "Excited to announce our new feature! #SocialSuit",
                "platform": "twitter",
                "scheduled_time": "2023-06-15T14:30:00Z",
                "status": "pending",
                "media_urls": ["https://cdn.example.com/image.jpg"],
                "tags": ["announcement", "feature"],
                "created_at": "2023-06-10T09:15:32Z",
                "updated_at": "2023-06-10T09:15:32Z"
            }
        }

class PostListRequest(PaginationValidation, UserIdValidation):
    """Request model for listing posts with pagination."""
    platform: Optional[PlatformType] = Field(None, description="Filter by platform")
    status: Optional[str] = Field(
        None, 
        pattern=r'^(draft|scheduled|published|failed|cancelled)$',
        description="Filter by status"
    )
    from_date: Optional[datetime] = Field(None, description="Filter from date")
    to_date: Optional[datetime] = Field(None, description="Filter to date")
    
    @validator('to_date')
    def validate_date_range(cls, v, values):
        """Ensure to_date is after from_date."""
        from_date = values.get('from_date')
        if from_date and v and v <= from_date:
            raise ValueError("to_date must be after from_date")
        return v

class PostUpdateRequest(BaseModel):
    """Request model for updating scheduled posts."""
    content: Optional[str] = Field(
        None, 
        min_length=1, 
        max_length=10000,
        description="Updated content"
    )
    scheduled_time: Optional[datetime] = Field(None, description="Updated scheduled time")
    media_urls: Optional[List[str]] = Field(None, max_items=10, description="Updated media URLs")
    tags: Optional[List[str]] = Field(None, max_items=20, description="Updated tags")
    
    @validator('scheduled_time')
    def validate_future_time(cls, v):
        """Ensure updated time is in the future."""
        if v and v <= datetime.utcnow():
            raise ValueError("Scheduled time must be in the future")
        return v

class BulkStatusUpdateRequest(BulkOperationValidation):
    """Request model for bulk status updates."""
    new_status: str = Field(
        ...,
        pattern=r'^(draft|scheduled|published|failed|cancelled)$',
        description="New status for selected posts"
    )

class PostSearchRequest(SearchValidation, PaginationValidation):
    """Request model for searching posts."""
    platform: Optional[PlatformType] = Field(None, description="Filter by platform")
    tags: Optional[List[str]] = Field(None, max_items=10, description="Filter by tags")

# Create secure router
router = APIRouter(
    prefix="/secure/scheduled-posts",
    tags=["Secure Scheduling"]
)

@router.post(
    "/",
    response_model=SecureScheduledPostResponse,
    summary="Create Secure Scheduled Post",
    description="Creates a new scheduled post with comprehensive security validation",
    status_code=201
)
async def create_secure_scheduled_post(
    post_data: SecureScheduledPostRequest = Body(
        ...,
        description="Validated post data with security checks"
    ),
    current_user: User = Depends(auth_required),
    scheduled_post_service: ScheduledPostService = Depends(get_scheduled_post_service),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Create a new scheduled post with enhanced security validation.
    
    This endpoint provides:
    - Comprehensive input validation and sanitization
    - Platform-specific content validation
    - Security checks for malicious content
    - Rate limiting protection
    - Audit logging
    
    Args:
        post_data: Validated post data
        current_user: Authenticated user
        scheduled_post_service: Post scheduling service
        background_tasks: Background task queue
        
    Returns:
        Created post details with security validation
        
    Raises:
        HTTPException: For validation errors or security issues
    """
    try:
        # Log the creation attempt for audit purposes
        logger.info(
            f"User {current_user.id} creating scheduled post for {post_data.platform}",
            extra={
                "user_id": current_user.id,
                "platform": post_data.platform,
                "scheduled_time": post_data.scheduled_time.isoformat(),
                "content_length": len(post_data.content)
            }
        )
        
        # Prepare validated post payload
        post_payload = {
            "content": post_data.content,
            "media_urls": post_data.media_urls or [],
            "tags": post_data.tags or [],
            "metadata": {
                "created_via": "secure_api",
                "validation_version": "1.0",
                "security_checked": True
            }
        }
        
        # Create post using service
        created_post = scheduled_post_service.create_scheduled_post(
            user_id=current_user.id,
            platform=post_data.platform.value,
            post_payload=post_payload,
            scheduled_time=post_data.scheduled_time
        )
        
        # Add background task for additional processing
        background_tasks.add_task(
            _post_creation_tasks,
            post_id=created_post.id,
            user_id=current_user.id
        )
        
        # Return secure response
        return SecureScheduledPostResponse(
            id=str(created_post.id),
            content=created_post.content,
            platform=post_data.platform,
            scheduled_time=created_post.scheduled_time,
            status=created_post.status.value if hasattr(created_post.status, 'value') else str(created_post.status),
            media_urls=post_payload["media_urls"],
            tags=post_payload["tags"],
            created_at=created_post.created_at,
            updated_at=created_post.updated_at
        )
        
    except ValueError as e:
        logger.warning(f"Validation error for user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            f"Error creating scheduled post for user {current_user.id}: {str(e)}",
            extra={"user_id": current_user.id, "error": str(e)}
        )
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get(
    "/",
    response_model=List[SecureScheduledPostResponse],
    summary="Get Scheduled Posts",
    description="Retrieve scheduled posts with secure filtering and pagination"
)
async def get_scheduled_posts(
    platform: Optional[PlatformType] = Query(None, description="Filter by platform"),
    status: Optional[str] = Query(
        None, 
        pattern=r'^(draft|scheduled|published|failed|cancelled)$',
        description="Filter by status"
    ),
    from_date: Optional[datetime] = Query(None, description="Filter from date"),
    to_date: Optional[datetime] = Query(None, description="Filter to date"),
    limit: int = Query(20, ge=1, le=100, description="Number of posts to return"),
    offset: int = Query(0, ge=0, description="Number of posts to skip"),
    current_user: User = Depends(auth_required),
    scheduled_post_service: ScheduledPostService = Depends(get_scheduled_post_service)
):
    """
    Retrieve scheduled posts with secure filtering.
    
    Provides:
    - Secure pagination with limits
    - Input validation for all parameters
    - User isolation (users can only see their own posts)
    - Audit logging
    """
    try:
        # Validate date range
        if from_date and to_date and to_date <= from_date:
            raise HTTPException(status_code=400, detail="to_date must be after from_date")
        
        # Log the request for audit purposes
        logger.info(
            f"User {current_user.id} requesting scheduled posts",
            extra={
                "user_id": current_user.id,
                "platform": platform.value if platform else None,
                "status": status,
                "limit": limit,
                "offset": offset
            }
        )
        
        # Get posts using service with pagination
        posts = scheduled_post_service.get_user_scheduled_posts(
            user_id=current_user.id,
            platform=platform.value if platform else None,
            status=status,
            from_date=from_date,
            to_date=to_date,
            limit=limit,
            offset=offset
        )
        
        # Convert to secure response format
        secure_posts = []
        for post in posts:
            secure_posts.append(SecureScheduledPostResponse(
                id=str(post.id),
                content=post.content,
                platform=PlatformType(post.platform),
                scheduled_time=post.scheduled_time,
                status=post.status.value if hasattr(post.status, 'value') else str(post.status),
                media_urls=post.media_urls or [],
                tags=post.tags or [],
                created_at=post.created_at,
                updated_at=post.updated_at
            ))
        
        return secure_posts
        
    except ValueError as e:
        logger.warning(f"Validation error for user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving posts for user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get(
    "/{post_id}",
    response_model=SecureScheduledPostResponse,
    summary="Get Scheduled Post",
    description="Retrieve a specific scheduled post by ID"
)
async def get_scheduled_post(
    post_id: str = Path(..., pattern=r'^[a-zA-Z0-9_-]+$', description="Post ID"),
    current_user: User = Depends(auth_required),
    scheduled_post_service: ScheduledPostService = Depends(get_scheduled_post_service)
):
    """Retrieve a specific scheduled post with security validation."""
    try:
        # Get post using service
        post = scheduled_post_service.get_scheduled_post(post_id)
        
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        # Verify ownership
        if post.user_id != current_user.id:
            logger.warning(
                f"User {current_user.id} attempted to access post {post_id} owned by {post.user_id}"
            )
            raise HTTPException(status_code=403, detail="Access denied")
        
        return SecureScheduledPostResponse(
            id=str(post.id),
            content=post.content,
            platform=PlatformType(post.platform),
            scheduled_time=post.scheduled_time,
            status=post.status.value if hasattr(post.status, 'value') else str(post.status),
            media_urls=post.media_urls or [],
            tags=post.tags or [],
            created_at=post.created_at,
            updated_at=post.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving post {post_id} for user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put(
    "/{post_id}",
    response_model=SecureScheduledPostResponse,
    summary="Update Scheduled Post",
    description="Update a scheduled post with validation"
)
async def update_scheduled_post(
    post_id: str = Path(..., pattern=r'^[a-zA-Z0-9_-]+$', description="Post ID"),
    update_data: PostUpdateRequest = Body(..., description="Update data"),
    current_user: User = Depends(auth_required),
    scheduled_post_service: ScheduledPostService = Depends(get_scheduled_post_service)
):
    """Update a scheduled post with comprehensive validation."""
    try:
        # Get existing post
        existing_post = scheduled_post_service.get_scheduled_post(post_id)
        
        if not existing_post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        # Verify ownership
        if existing_post.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Prepare update data
        update_payload = {}
        if update_data.content is not None:
            update_payload["content"] = update_data.content
        if update_data.scheduled_time is not None:
            update_payload["scheduled_time"] = update_data.scheduled_time
        if update_data.media_urls is not None:
            update_payload["media_urls"] = update_data.media_urls
        if update_data.tags is not None:
            update_payload["tags"] = update_data.tags
        
        # Update post
        updated_post = scheduled_post_service.update_scheduled_post(
            post_id=post_id,
            update_data=update_payload
        )
        
        logger.info(
            f"User {current_user.id} updated post {post_id}",
            extra={"user_id": current_user.id, "post_id": post_id}
        )
        
        return SecureScheduledPostResponse(
            id=str(updated_post.id),
            content=updated_post.content,
            platform=PlatformType(updated_post.platform),
            scheduled_time=updated_post.scheduled_time,
            status=updated_post.status.value if hasattr(updated_post.status, 'value') else str(updated_post.status),
            media_urls=updated_post.media_urls or [],
            tags=updated_post.tags or [],
            created_at=updated_post.created_at,
            updated_at=updated_post.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating post {post_id} for user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete(
    "/{post_id}",
    summary="Delete Scheduled Post",
    description="Delete a scheduled post"
)
async def delete_scheduled_post(
    post_id: str = Path(..., pattern=r'^[a-zA-Z0-9_-]+$', description="Post ID"),
    current_user: User = Depends(auth_required),
    scheduled_post_service: ScheduledPostService = Depends(get_scheduled_post_service)
):
    """Delete a scheduled post with security validation."""
    try:
        # Get existing post
        existing_post = scheduled_post_service.get_scheduled_post(post_id)
        
        if not existing_post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        # Verify ownership
        if existing_post.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Delete post
        scheduled_post_service.delete_scheduled_post(post_id)
        
        logger.info(
            f"User {current_user.id} deleted post {post_id}",
            extra={"user_id": current_user.id, "post_id": post_id}
        )
        
        return {"message": "Post deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting post {post_id} for user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post(
    "/search",
    response_model=List[SecureScheduledPostResponse],
    summary="Search Scheduled Posts",
    description="Search posts with secure validation"
)
async def search_scheduled_posts(
    search_request: PostSearchRequest = Body(..., description="Search parameters"),
    current_user: User = Depends(auth_required),
    scheduled_post_service: ScheduledPostService = Depends(get_scheduled_post_service)
):
    """Search scheduled posts with comprehensive validation."""
    try:
        # Search posts using service
        posts = scheduled_post_service.search_posts(
            user_id=current_user.id,
            query=search_request.query,
            platform=search_request.platform.value if search_request.platform else None,
            tags=search_request.tags,
            limit=search_request.limit,
            offset=search_request.offset
        )
        
        # Convert to secure response format
        secure_posts = []
        for post in posts:
            secure_posts.append(SecureScheduledPostResponse(
                id=str(post.id),
                content=post.content,
                platform=PlatformType(post.platform),
                scheduled_time=post.scheduled_time,
                status=post.status.value if hasattr(post.status, 'value') else str(post.status),
                media_urls=post.media_urls or [],
                tags=post.tags or [],
                created_at=post.created_at,
                updated_at=post.updated_at
            ))
        
        return secure_posts
        
    except Exception as e:
        logger.error(f"Error searching posts for user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post(
    "/bulk/status",
    summary="Bulk Update Post Status",
    description="Update status of multiple posts"
)
async def bulk_update_status(
    bulk_request: BulkStatusUpdateRequest = Body(..., description="Bulk update parameters"),
    current_user: User = Depends(auth_required),
    scheduled_post_service: ScheduledPostService = Depends(get_scheduled_post_service)
):
    """Bulk update post status with validation."""
    try:
        # Update posts using service
        updated_count = scheduled_post_service.bulk_update_status(
            user_id=current_user.id,
            post_ids=bulk_request.ids,
            new_status=bulk_request.new_status
        )
        
        logger.info(
            f"User {current_user.id} bulk updated {updated_count} posts to {bulk_request.new_status}",
            extra={
                "user_id": current_user.id,
                "updated_count": updated_count,
                "new_status": bulk_request.new_status
            }
        )
        
        return {
            "message": f"Successfully updated {updated_count} posts",
            "updated_count": updated_count
        }
        
    except Exception as e:
        logger.error(f"Error bulk updating posts for user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Background task functions
async def _post_creation_tasks(post_id: str, user_id: str):
    """Background tasks to run after post creation."""
    try:
        # Add any post-creation processing here
        # Examples: analytics tracking, notifications, etc.
        logger.info(f"Running post-creation tasks for post {post_id}")
        
        # Example: Track analytics
        # await analytics_service.track_post_creation(post_id, user_id)
        
        # Example: Send notification
        # await notification_service.notify_post_scheduled(post_id, user_id)
        
    except Exception as e:
        logger.error(f"Error in post-creation tasks for post {post_id}: {str(e)}")

# Health check endpoint
@router.get(
    "/health",
    summary="Health Check",
    description="Check the health of the scheduled post service"
)
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "secure_scheduled_post_api",
        "timestamp": datetime.utcnow().isoformat()
    }
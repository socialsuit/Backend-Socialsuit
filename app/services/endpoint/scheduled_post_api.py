from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, AnyUrl
import uuid

from app.services.database.database import get_db
from app.services.models.scheduled_post_model import ScheduledPost, PostStatus
from app.services.models.user_model import User
from app.services.scheduled_post_service import ScheduledPostService
from app.services.dependencies.scheduled_post_providers import get_scheduled_post_service
from app.services.auth.auth_guard import auth_required
from app.services.utils.logger_config import setup_logger

# Set up logger
logger = setup_logger("scheduled_post_api")

# Pydantic models for request/response validation
class MediaUrl(BaseModel):
    """Model representing a media URL for a post."""
    url: str = Field(..., description="URL to the media file")
    type: str = Field("image", description="Media type (image, video, etc.)")

class PostMetadata(BaseModel):
    """Model representing additional metadata for a post."""
    hashtags: Optional[List[str]] = Field(None, description="List of hashtags to include")
    mentions: Optional[List[str]] = Field(None, description="List of accounts to mention")
    location: Optional[str] = Field(None, description="Location tag for the post")
    alt_text: Optional[str] = Field(None, description="Alt text for media accessibility")

class ScheduledPostRequest(BaseModel):
    """Request model for creating a scheduled post.
    
    Contains all necessary information to schedule a social media post.
    """
    content: str = Field(..., description="The main text content of the post")
    platform: str = Field(..., description="Social media platform for posting")
    scheduled_time: str = Field(..., description="ISO format datetime for when to publish")
    media_urls: Optional[List[str]] = Field([], description="List of media URLs to attach")
    metadata: Optional[Dict[str, Any]] = Field({}, description="Additional post metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "Excited to announce our new feature launch! #SocialSuit #SocialMedia",
                "platform": "twitter",
                "scheduled_time": "2023-06-15T14:30:00Z",
                "media_urls": ["https://example.com/images/feature-preview.jpg"],
                "metadata": {
                    "hashtags": ["SocialSuit", "SocialMedia"],
                    "mentions": ["@competitor"],
                    "alt_text": "Screenshot of the new feature dashboard"
                }
            }
        }

class ScheduledPostResponse(BaseModel):
    """Response model for a scheduled post.
    
    Contains details about the created or retrieved scheduled post.
    """
    id: int = Field(..., description="Unique identifier for the scheduled post")
    content: str = Field(..., description="The main text content of the post")
    platform: str = Field(..., description="Social media platform for posting")
    scheduled_time: str = Field(..., description="ISO format datetime for when to publish")
    status: str = Field(..., description="Current status of the scheduled post")
    media_urls: List[str] = Field([], description="List of media URLs attached to the post")
    metadata: Dict[str, Any] = Field({}, description="Additional post metadata")
    created_at: Optional[str] = Field(None, description="When the post was created")
    updated_at: Optional[str] = Field(None, description="When the post was last updated")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 123,
                "content": "Excited to announce our new feature launch! #SocialSuit #SocialMedia",
                "platform": "twitter",
                "scheduled_time": "2023-06-15T14:30:00Z",
                "status": "pending",
                "media_urls": ["https://example.com/images/feature-preview.jpg"],
                "metadata": {
                    "hashtags": ["SocialSuit", "SocialMedia"],
                    "mentions": ["@competitor"],
                    "alt_text": "Screenshot of the new feature dashboard"
                },
                "created_at": "2023-06-10T09:15:32Z",
                "updated_at": "2023-06-10T09:15:32Z"
            }
        }

class CreatePostResponse(BaseModel):
    """Response model for post creation confirmation."""
    message: str = Field(..., description="Success message")
    post_id: int = Field(..., description="ID of the created post")
    scheduled_time: str = Field(..., description="Confirmed scheduled time (ISO format)")

# Create router
router = APIRouter(
    prefix="/scheduled-posts", 
    tags=["Scheduling"]
)

@router.post(
    "/", 
    response_model=CreatePostResponse,
    summary="Create Scheduled Post",
    description="Creates a new scheduled post for publishing to a social media platform at the specified time",
    response_description="Returns confirmation with the post ID and scheduled time"
)
async def create_scheduled_post(
    post_data: ScheduledPostRequest = Body(
        ...,
        description="Post data including content, platform, and scheduled time"
    ),
    current_user: User = Depends(auth_required),
    scheduled_post_service: ScheduledPostService = Depends(get_scheduled_post_service)
):
    """Create a new scheduled social media post.
    
    This endpoint allows users to schedule posts for future publication on various
    social media platforms. The post can include text content, media attachments,
    and platform-specific metadata.
    
    Args:
        post_data: The post content and scheduling information
        current_user: The authenticated user (injected by dependency)
        scheduled_post_service: Service for post scheduling operations
        
    Returns:
        A JSON object with confirmation message, post ID, and scheduled time
        
    Raises:
        HTTPException: If post creation fails or validation errors occur
    """
    try:
        # Parse scheduled time
        try:
            scheduled_time = datetime.fromisoformat(post_data.scheduled_time.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid scheduled_time format. Use ISO format.")
        
        # Prepare post payload
        post_payload = {
            "content": post_data.content,
            "media_urls": post_data.media_urls,
            "metadata": post_data.metadata
        }
        
        # Create post using service
        created_post = scheduled_post_service.create_scheduled_post(
            user_id=current_user.id,
            platform=post_data.platform,
            post_payload=post_payload,
            scheduled_time=scheduled_time
        )
        
        return {
            "message": "Scheduled post created successfully",
            "post_id": created_post.id,
            "scheduled_time": created_post.scheduled_time.isoformat()
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error creating scheduled post: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating scheduled post: {str(e)}")

@router.get(
    "/", 
    response_model=List[ScheduledPostResponse],
    summary="Get Scheduled Posts",
    description="Retrieves all scheduled posts for the current user with optional filtering by platform, status, and date range",
    response_description="Returns a list of scheduled posts matching the filter criteria"
)
async def get_scheduled_posts(
    platform: Optional[str] = Query(
        None, 
        description="Filter by platform",
        example="twitter",
        enum=["twitter", "facebook", "instagram", "linkedin", "tiktok"]
    ),
    status: Optional[str] = Query(
        None, 
        description="Filter by post status",
        example="pending",
        enum=["pending", "publishing", "success", "failed", "cancelled", "retry"]
    ),
    from_date: Optional[str] = Query(
        None, 
        description="Filter from date (ISO format)",
        example="2023-06-01T00:00:00Z"
    ),
    to_date: Optional[str] = Query(
        None, 
        description="Filter to date (ISO format)",
        example="2023-06-30T23:59:59Z"
    ),
    current_user: User = Depends(auth_required),
    scheduled_post_service: ScheduledPostService = Depends(get_scheduled_post_service)
):
    """Get all scheduled posts for the current user with optional filters.
    
    This endpoint retrieves scheduled posts with flexible filtering options to help
    users manage their content calendar effectively.
    
    Args:
        platform: Optional filter for specific social media platform
        status: Optional filter for post status
        from_date: Optional start date for filtering (ISO format)
        to_date: Optional end date for filtering (ISO format)
        current_user: The authenticated user (injected by dependency)
        scheduled_post_service: Service for post scheduling operations
        
    Returns:
        A list of scheduled posts matching the filter criteria
        
    Raises:
        HTTPException: If retrieval fails or validation errors occur
    """
    try:
        # Parse date filters if provided
        start_date = None
        end_date = None
        
        if from_date:
            try:
                start_date = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid from_date format. Use ISO format.")
        
        if to_date:
            try:
                end_date = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid to_date format. Use ISO format.")
        
        # Get posts with filters using service
        posts = scheduled_post_service.get_user_scheduled_posts(
            user_id=current_user.id,
            platform=platform,
            status=status,
            start_date=start_date,
            end_date=end_date
        )
        
        # Convert to response format
        response_posts = []
        for post in posts:
            response_posts.append({
                "id": post.id,
                "content": post.post_payload.get("content", ""),
                "platform": post.platform,
                "scheduled_time": post.scheduled_time.isoformat(),
                "status": post.status,
                "media_urls": post.post_payload.get("media_urls", []),
                "metadata": post.post_payload.get("metadata", {}),
                "created_at": post.created_at.isoformat() if post.created_at else None,
                "updated_at": post.updated_at.isoformat() if post.updated_at else None
            })
        
        return response_posts
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error retrieving scheduled posts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving scheduled posts: {str(e)}")

@router.get(
    "/{post_id}", 
    response_model=ScheduledPostResponse,
    summary="Get Scheduled Post by ID",
    description="Retrieves a specific scheduled post by its unique identifier",
    response_description="Returns the detailed information for the requested scheduled post"
)
async def get_scheduled_post(
    post_id: int = Path(
        ..., 
        description="ID of the scheduled post to retrieve",
        example=123,
        gt=0
    ),
    current_user: User = Depends(auth_required),
    scheduled_post_service: ScheduledPostService = Depends(get_scheduled_post_service)
):
    """Get a specific scheduled post by ID.
    
    This endpoint retrieves detailed information about a single scheduled post,
    including its content, scheduling information, and current status.
    
    Args:
        post_id: The unique identifier of the scheduled post
        current_user: The authenticated user (injected by dependency)
        scheduled_post_service: Service for post scheduling operations
        
    Returns:
        A detailed representation of the scheduled post
        
    Raises:
        HTTPException: If post not found, user not authorized, or retrieval fails
    """
    try:
        post = scheduled_post_service.get_scheduled_post(post_id)
        
        if not post:
            raise HTTPException(status_code=404, detail="Scheduled post not found")
        
        # Verify ownership
        if post.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this post")
        
        return {
            "id": post.id,
            "content": post.post_payload.get("content", ""),
            "platform": post.platform,
            "scheduled_time": post.scheduled_time.isoformat(),
            "status": post.status,
            "media_urls": post.post_payload.get("media_urls", []),
            "metadata": post.post_payload.get("metadata", {}),
            "created_at": post.created_at.isoformat() if post.created_at else None,
            "updated_at": post.updated_at.isoformat() if post.updated_at else None
        }

class UpdatePostRequest(BaseModel):
    """Request model for updating a scheduled post.
    
    Contains fields that can be updated for an existing scheduled post.
    All fields are optional since this is used for partial updates.
    """
    content: Optional[str] = Field(None, description="The main text content of the post")
    platform: Optional[str] = Field(None, description="Social media platform for posting")
    scheduled_time: Optional[str] = Field(None, description="ISO format datetime for when to publish")
    media_urls: Optional[List[str]] = Field(None, description="List of media URLs to attach")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional post metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "Updated announcement for our feature launch! #SocialSuit",
                "scheduled_time": "2023-06-16T10:00:00Z",
                "media_urls": ["https://example.com/images/updated-preview.jpg"],
                "metadata": {
                    "hashtags": ["SocialSuit", "Update"],
                    "mentions": ["@partner"],
                    "alt_text": "Updated screenshot of the feature dashboard"
                }
            }
        }

class UpdatePostResponse(BaseModel):
    """Response model for post update confirmation."""
    message: str = Field(..., description="Success message")
    post_id: int = Field(..., description="ID of the updated post")
    scheduled_time: str = Field(..., description="Updated scheduled time (ISO format)")

@router.put(
    "/{post_id}",
    response_model=UpdatePostResponse,
    summary="Update Scheduled Post",
    description="Updates an existing scheduled post with new content or scheduling information",
    response_description="Returns confirmation with the post ID and updated scheduled time"
)
async def update_scheduled_post(
    post_id: int = Path(
        ..., 
        description="ID of the scheduled post to update",
        example=123,
        gt=0
    ),
    post_data: UpdatePostRequest = Body(
        ...,
        description="Updated post data including content, platform, and/or scheduled time"
    ),
    current_user: User = Depends(auth_required),
    scheduled_post_service: ScheduledPostService = Depends(get_scheduled_post_service)
):
    """Update an existing scheduled post.
    
    This endpoint allows users to modify the content or scheduling details of an
    existing post before it's published. All fields are optional, allowing for
    partial updates.
    
    Args:
        post_id: The unique identifier of the scheduled post to update
        post_data: The updated post content and scheduling information
        current_user: The authenticated user (injected by dependency)
        scheduled_post_service: Service for post scheduling operations
        
    Returns:
        A JSON object with confirmation message, post ID, and updated scheduled time
        
    Raises:
        HTTPException: If post not found, user not authorized, or update fails
    """
    try:
        # Get existing post
        post = scheduled_post_service.get_scheduled_post(post_id)
        
        if not post:
            raise HTTPException(status_code=404, detail="Scheduled post not found")
        
        # Verify ownership
        if post.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to update this post")
        
        # Prepare updated payload
        post_payload = dict(post.post_payload) if post.post_payload else {}
        scheduled_time = None
        
        if post_data.content is not None:
            post_payload["content"] = post_data.content
        
        if post_data.media_urls is not None:
            post_payload["media_urls"] = post_data.media_urls
        
        if post_data.metadata is not None:
            post_payload["metadata"] = post_data.metadata
        
        if post_data.scheduled_time is not None:
            try:
                scheduled_time = datetime.fromisoformat(post_data.scheduled_time.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid scheduled_time format. Use ISO format.")
        
        # Update post using service
        updated_post = scheduled_post_service.update_scheduled_post(
            post_id=post_id,
            post_payload=post_payload,
            scheduled_time=scheduled_time
        )
        
        return {
            "message": "Scheduled post updated successfully",
            "post_id": updated_post.id,
            "scheduled_time": updated_post.scheduled_time.isoformat()
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error updating scheduled post: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating scheduled post: {str(e)}")

class DeletePostResponse(BaseModel):
    """Response model for post deletion confirmation."""
    message: str = Field(..., description="Success message")

@router.delete(
    "/{post_id}",
    response_model=DeletePostResponse,
    summary="Delete Scheduled Post",
    description="Permanently removes a scheduled post from the system",
    response_description="Returns confirmation of successful deletion"
)
async def delete_scheduled_post(
    post_id: int = Path(
        ..., 
        description="ID of the scheduled post to delete",
        example=123,
        gt=0
    ),
    current_user: User = Depends(auth_required),
    scheduled_post_service: ScheduledPostService = Depends(get_scheduled_post_service)
):
    """Delete a scheduled post.
    
    This endpoint permanently removes a scheduled post from the system. Once deleted,
    the post cannot be recovered and will not be published.
    
    Args:
        post_id: The unique identifier of the scheduled post to delete
        current_user: The authenticated user (injected by dependency)
        scheduled_post_service: Service for post scheduling operations
        
    Returns:
        A JSON object with confirmation message
        
    Raises:
        HTTPException: If post not found, user not authorized, or deletion fails
    """
    try:
        # Get existing post
        post = scheduled_post_service.get_scheduled_post(post_id)
        
        if not post:
            raise HTTPException(status_code=404, detail="Scheduled post not found")
        
        # Verify ownership
        if post.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this post")
        
        # Delete using service
        scheduled_post_service.delete_scheduled_post(post_id)
        
        return {"message": "Scheduled post deleted successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error deleting scheduled post: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting scheduled post: {str(e)}")

class PublishResponse(BaseModel):
    """Response model for immediate post publishing confirmation."""
    message: str = Field(..., description="Success message")
    status: str = Field(..., description="Publishing status result")

@router.post(
    "/{post_id}/publish",
    response_model=PublishResponse,
    summary="Publish Post Immediately",
    description="Immediately publishes a scheduled post to the specified platform",
    response_description="Returns confirmation of publishing initiation or completion"
)
async def publish_post_now(
    post_id: int = Path(
        ..., 
        description="ID of the scheduled post to publish immediately",
        example=123,
        gt=0
    ),
    current_user: User = Depends(auth_required),
    background_tasks: BackgroundTasks = None,
    scheduled_post_service: ScheduledPostService = Depends(get_scheduled_post_service)
):
    """Publish a scheduled post immediately.
    
    This endpoint allows users to publish a scheduled post right away, regardless of
    its originally scheduled time. The post will be sent to the specified social media
    platform immediately.
    
    Args:
        post_id: The unique identifier of the scheduled post to publish
        current_user: The authenticated user (injected by dependency)
        background_tasks: FastAPI background tasks manager for async processing
        scheduled_post_service: Service for post scheduling operations
        
    Returns:
        A JSON object with confirmation message and status
        
    Raises:
        HTTPException: If post not found, already published, user not authorized, or publishing fails
    """
    try:
        # Get existing post
        post = scheduled_post_service.get_scheduled_post(post_id)
        
        if not post:
            raise HTTPException(status_code=404, detail="Scheduled post not found")
        
        # Verify ownership
        if post.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to publish this post")
        
        # Check if post is already published
        if post.status == PostStatus.PUBLISHED:
            raise HTTPException(status_code=400, detail="Post has already been published")
        
        # Publish post using service (in background if available)
        if background_tasks:
            background_tasks.add_task(scheduled_post_service.publish_post, post_id)
            return {"message": "Post publishing initiated", "status": "PUBLISHING"}
        else:
            success = scheduled_post_service.publish_post(post_id)
            if success:
                return {"message": "Post published successfully", "status": "PUBLISHED"}
            else:
                return {"message": "Failed to publish post", "status": "FAILED"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error publishing post: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error publishing post: {str(e)}")

class PendingPostsResponse(BaseModel):
    """Response model for pending posts processing."""
    message: str = Field(..., description="Processing result message")
    published_count: int = Field(..., description="Number of posts processed")

@router.get(
    "/pending/next",
    response_model=PendingPostsResponse,
    summary="Process Pending Posts",
    description="Administrative endpoint to process pending posts that are due for publishing",
    response_description="Returns count of processed posts",
    include_in_schema=False
)
async def get_next_pending_posts(
    limit: int = Query(10, ge=1, le=100, description="Maximum number of posts to process"),
    scheduled_post_service: ScheduledPostService = Depends(get_scheduled_post_service)
):
    """Get and process next pending posts that are due for publishing (admin/system endpoint).
    
    This endpoint is designed for administrative use and background processing.
    It retrieves and processes the next batch of posts that are scheduled to be published soon.
    
    Args:
        limit: Maximum number of pending posts to process
        scheduled_post_service: Service for post scheduling operations
        
    Returns:
        A JSON object with processing results and count
        
    Raises:
        HTTPException: If processing fails
    """
    try:
        # Process pending posts using service
        published_count = scheduled_post_service.process_pending_posts(limit=limit)
        
        return {
            "message": f"Processed {published_count} pending posts",
            "published_count": published_count
        }
    except Exception as e:
        logger.error(f"Error retrieving pending posts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving pending posts: {str(e)}")

@router.put("/{post_id}/status")
async def update_post_status(
    post_id: int,
    status_data: dict = Body(...),
    scheduled_post_service: ScheduledPostService = Depends(get_scheduled_post_service)
):
    """Update the status of a scheduled post (admin/system endpoint)"""
    try:
        # Validate status
        if "status" not in status_data:
            raise HTTPException(status_code=400, detail="Missing status field")
        
        new_status = status_data["status"]
        if new_status not in [status.value for status in PostStatus]:
            raise HTTPException(status_code=400, detail=f"Invalid status. Valid options are: {', '.join([s.value for s in PostStatus])}")
        
        # Update status using service
        success = scheduled_post_service.update_post_status(post_id, new_status)
        
        if not success:
            raise HTTPException(status_code=404, detail="Scheduled post not found or status update failed")
        
        return {"message": f"Post status updated to {new_status}", "post_id": post_id}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error updating post status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating post status: {str(e)}")
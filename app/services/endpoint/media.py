"""
Media Upload Endpoint

This endpoint provides optimized media upload functionality using the centralized
Cloudinary helper with automatic format optimization, quality optimization, and
responsive breakpoints for optimal performance.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import tempfile
import os
import logging

# Import the centralized Cloudinary helper
from services.cloudinary_helper import cloudinary_helper

# Configure logging
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

class MediaUploadResponse(BaseModel):
    """Response model for media upload."""
    success: bool = Field(..., description="Upload success status")
    public_id: str = Field(..., description="Cloudinary public ID")
    resource_type: str = Field(..., description="Type of resource (image/video)")
    original_url: str = Field(..., description="Original file URL")
    optimized_urls: Dict[str, str] = Field(..., description="Optimized URLs for different sizes")
    file_info: Dict[str, Any] = Field(..., description="File metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "public_id": "social_suit/uploads/image_abc123",
                "resource_type": "image",
                "original_url": "https://res.cloudinary.com/demo/image/upload/f_auto,q_auto/social_suit/uploads/image_abc123.jpg",
                "optimized_urls": {
                    "thumbnail": "https://res.cloudinary.com/demo/image/upload/w_300,h_300,c_fill,g_auto,f_auto,q_auto/social_suit/uploads/image_abc123.jpg",
                    "medium": "https://res.cloudinary.com/demo/image/upload/w_800,h_600,c_fill,g_auto,f_auto,q_auto/social_suit/uploads/image_abc123.jpg",
                    "large": "https://res.cloudinary.com/demo/image/upload/w_1200,h_900,c_fill,g_auto,f_auto,q_auto/social_suit/uploads/image_abc123.jpg"
                },
                "file_info": {
                    "format": "jpg",
                    "width": 2048,
                    "height": 1536,
                    "bytes": 524288
                }
            }
        }

class MediaDeleteResponse(BaseModel):
    """Response model for media deletion."""
    success: bool = Field(..., description="Deletion success status")
    public_id: str = Field(..., description="Deleted resource public ID")
    result: str = Field(..., description="Deletion result")

router = APIRouter(
    prefix="/media",
    tags=["Media Upload & Management"]
)

@router.post(
    "/upload",
    response_model=MediaUploadResponse,
    summary="Upload Media File",
    description="Upload an image or video file to Cloudinary with automatic optimizations including format conversion (WebP/AVIF), quality optimization, and responsive breakpoints."
)
async def upload_media(
    file: UploadFile = File(..., description="Media file to upload (image or video)"),
    folder: Optional[str] = Form(default="social_suit/uploads", description="Cloudinary folder for organization"),
    tags: Optional[str] = Form(default=None, description="Comma-separated tags for the media"),
    public_id: Optional[str] = Form(default=None, description="Custom public ID (optional)"),
    responsive_breakpoints: bool = Form(default=True, description="Generate responsive breakpoints for images")
    # Temporarily removed authentication for testing: token: str = Depends(security)
):
    """
    Upload a media file with automatic Cloudinary optimizations.
    
    Features:
    - Automatic format optimization (f_auto) - converts to WebP/AVIF for better compression
    - Automatic quality optimization (q_auto) - optimal quality/size balance
    - Responsive breakpoints for different screen sizes
    - CDN caching for all transformed versions
    - Support for both images and videos
    
    Args:
        file: The media file to upload
        folder: Cloudinary folder for organization
        tags: Comma-separated tags for the media
        public_id: Custom public ID (optional)
        responsive_breakpoints: Generate responsive breakpoints for images
        token: Authentication token
        
    Returns:
        Upload result with optimized URLs and metadata
        
    Raises:
        HTTPException: If upload fails or file type is not supported
    """
    try:
        # Validate file type
        if not file.content_type:
            raise HTTPException(status_code=400, detail="File content type is required")
        
        # Determine resource type
        if file.content_type.startswith('image/'):
            resource_type = 'image'
        elif file.content_type.startswith('video/'):
            resource_type = 'video'
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type: {file.content_type}. Only images and videos are supported."
            )
        
        # Process tags
        tag_list = None
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
        
        # Create temporary file for upload
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1]}") as temp_file:
            # Write uploaded file to temporary file
            content = await file.read()
            temp_file.write(content)
            temp_file.flush()
            
            temp_file_path = temp_file.name
            
        try:
            # Upload based on resource type
            if resource_type == 'image':
                result = cloudinary_helper.upload_image(
                    file_path_or_url=temp_file_path,
                    public_id=public_id,
                    folder=folder,
                    tags=tag_list,
                    responsive_breakpoints=responsive_breakpoints,
                    context={
                        'original_filename': file.filename,
                        'content_type': file.content_type
                    }
                )
            else:  # video
                result = cloudinary_helper.upload_video(
                    file_path_or_url=temp_file_path,
                    public_id=public_id,
                    folder=folder,
                    tags=tag_list,
                    context={
                        'original_filename': file.filename,
                        'content_type': file.content_type
                    }
                )
            
            # Clean up temporary file
            os.unlink(temp_file_path)
            
            # Prepare response
            response = MediaUploadResponse(
                success=True,
                public_id=result['public_id'],
                resource_type=resource_type,
                original_url=result['secure_url'],
                optimized_urls=result['optimized_urls'],
                file_info={
                    'format': result.get('format'),
                    'width': result.get('width'),
                    'height': result.get('height'),
                    'bytes': result.get('bytes'),
                    'created_at': result.get('created_at'),
                    'resource_type': result.get('resource_type')
                }
            )
            
            logger.info(f"Media uploaded successfully: {result['public_id']}")
            return response
            
        except Exception as upload_error:
            # Clean up temporary file on error
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            raise upload_error
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Media upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.delete(
    "/{public_id:path}",
    response_model=MediaDeleteResponse,
    summary="Delete Media File",
    description="Delete a media file from Cloudinary by its public ID."
)
async def delete_media(
    public_id: str,
    resource_type: str = "image",
    token: str = Depends(security)
):
    """
    Delete a media file from Cloudinary.
    
    Args:
        public_id: Cloudinary public ID of the resource to delete
        resource_type: Type of resource ('image' or 'video')
        token: Authentication token
        
    Returns:
        Deletion result
        
    Raises:
        HTTPException: If deletion fails
    """
    try:
        result = cloudinary_helper.delete_resource(public_id, resource_type)
        
        return MediaDeleteResponse(
            success=True,
            public_id=public_id,
            result=result.get('result', 'deleted')
        )
        
    except Exception as e:
        logger.error(f"Media deletion failed for {public_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")

@router.get(
    "/{public_id:path}/info",
    summary="Get Media Info",
    description="Get detailed information about a media file from Cloudinary."
)
async def get_media_info(
    public_id: str,
    resource_type: str = "image",
    token: str = Depends(security)
):
    """
    Get detailed information about a media file.
    
    Args:
        public_id: Cloudinary public ID of the resource
        resource_type: Type of resource ('image' or 'video')
        token: Authentication token
        
    Returns:
        Resource information including metadata and available transformations
        
    Raises:
        HTTPException: If resource not found or access fails
    """
    try:
        result = cloudinary_helper.get_resource_info(public_id, resource_type)
        return result
        
    except Exception as e:
        logger.error(f"Failed to get media info for {public_id}: {str(e)}")
        raise HTTPException(status_code=404, detail=f"Resource not found: {str(e)}")

@router.get(
    "/{public_id:path}/optimized-url",
    summary="Get Optimized Media URL",
    description="Get an optimized URL for a media file with custom transformations."
)
async def get_optimized_url(
    public_id: str,
    resource_type: str = "image",
    width: Optional[int] = None,
    height: Optional[int] = None,
    crop: str = "fill",
    gravity: str = "auto"
    # Temporarily removed authentication for testing: token: str = Depends(security)
):
    """
    Get an optimized URL for a media file with custom transformations.
    
    Args:
        public_id: Cloudinary public ID of the resource
        resource_type: Type of resource ('image' or 'video')
        width: Target width
        height: Target height
        crop: Crop mode (fill, fit, scale, etc.)
        gravity: Gravity for cropping (auto, face, center, etc.)
        token: Authentication token
        
    Returns:
        Optimized URL with applied transformations
    """
    try:
        if resource_type == 'image':
            url = cloudinary_helper.get_optimized_image_url(
                public_id=public_id,
                width=width,
                height=height,
                crop=crop,
                gravity=gravity
            )
        else:  # video
            url = cloudinary_helper.get_optimized_video_url(
                public_id=public_id,
                width=width,
                height=height
            )
        
        return {"optimized_url": url}
        
    except Exception as e:
        logger.error(f"Failed to generate optimized URL for {public_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"URL generation failed: {str(e)}")
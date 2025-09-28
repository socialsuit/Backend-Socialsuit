"""
Centralized Cloudinary Helper Utility

This module provides optimized Cloudinary integration with automatic transformations
for images and videos, including format optimization, quality optimization, and
responsive breakpoints for optimal performance and user experience.
"""

import os
import logging
from typing import Dict, List, Optional, Union, Any
from urllib.parse import urlparse
import cloudinary
import cloudinary.uploader
import cloudinary.utils
from cloudinary import CloudinaryImage, CloudinaryVideo

# Configure logging
logger = logging.getLogger(__name__)

class CloudinaryHelper:
    """
    Centralized Cloudinary helper with automatic optimizations.
    
    Features:
    - Automatic format optimization (f_auto)
    - Automatic quality optimization (q_auto) 
    - CDN caching for transformed versions
    - Responsive breakpoints for different screen sizes
    - Support for both images and videos
    - Environment-based configuration
    """
    
    def __init__(self):
        """Initialize Cloudinary configuration from environment variables."""
        self._configure_cloudinary()
        
        # Default transformation settings
        self.default_image_transformations = {
            'fetch_format': 'auto',  # f_auto - WebP/AVIF etc.
            'quality': 'auto',       # q_auto - optimal quality/size balance
            'flags': 'progressive'   # Progressive loading
        }
        
        self.default_video_transformations = {
            'fetch_format': 'auto',  # f_auto - optimal video format
            'quality': 'auto',       # q_auto - optimal quality
            'bit_rate': 'auto'       # br_auto - optimal bitrate
        }
        
        # Responsive breakpoints for different screen sizes
        self.responsive_breakpoints = [
            {'max_width': 480, 'max_images': 3},   # Mobile
            {'max_width': 768, 'max_images': 3},   # Tablet
            {'max_width': 1200, 'max_images': 3},  # Desktop
            {'max_width': 1920, 'max_images': 3}   # Large screens
        ]
    
    def _configure_cloudinary(self):
        """Configure Cloudinary using environment variables."""
        cloudinary_url = os.getenv('CLOUDINARY_URL')
        if not cloudinary_url or cloudinary_url == 'your_cloudinary_url_here':
            # Use fallback configuration for development
            logger.warning("CLOUDINARY_URL not configured, using development fallback")
            cloudinary.config(
                cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME', 'development'),
                api_key=os.getenv('CLOUDINARY_API_KEY', 'development'),
                api_secret=os.getenv('CLOUDINARY_API_SECRET', 'development'),
                secure=True
            )
            return
        
        # Parse the Cloudinary URL
        parsed = urlparse(cloudinary_url)
        if parsed.scheme != 'cloudinary':
            logger.warning("Invalid CLOUDINARY_URL format, using fallback configuration")
            cloudinary.config(
                cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME', 'development'),
                api_key=os.getenv('CLOUDINARY_API_KEY', 'development'),
                api_secret=os.getenv('CLOUDINARY_API_SECRET', 'development'),
                secure=True
            )
            return
        
        # Configure Cloudinary
        cloudinary.config(
            cloud_name=parsed.hostname,
            api_key=parsed.username,
            api_secret=parsed.password,
            secure=True
        )
        
        logger.info(f"Cloudinary configured for cloud: {parsed.hostname}")
    
    def upload_image(
        self,
        file_path_or_url: str,
        public_id: Optional[str] = None,
        folder: Optional[str] = None,
        tags: Optional[List[str]] = None,
        context: Optional[Dict[str, str]] = None,
        responsive_breakpoints: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Upload an image to Cloudinary with automatic optimizations.
        
        Args:
            file_path_or_url: Local file path or URL to upload
            public_id: Custom public ID for the image
            folder: Folder to organize the image
            tags: Tags for the image
            context: Additional metadata
            responsive_breakpoints: Generate responsive breakpoints
            **kwargs: Additional Cloudinary upload parameters
            
        Returns:
            Upload result with optimized URLs and metadata
        """
        try:
            upload_params = {
                'resource_type': 'image',
                'use_filename': True,
                'unique_filename': True if not public_id else False,
                'overwrite': False,
                **kwargs
            }
            
            if public_id:
                upload_params['public_id'] = public_id
            if folder:
                upload_params['folder'] = folder
            if tags:
                upload_params['tags'] = tags
            if context:
                upload_params['context'] = context
            
            # Add responsive breakpoints if requested
            if responsive_breakpoints:
                upload_params['responsive_breakpoints'] = self.responsive_breakpoints
            
            # Upload the image
            result = cloudinary.uploader.upload(file_path_or_url, **upload_params)
            
            # Generate optimized URLs
            optimized_urls = self._generate_optimized_image_urls(result['public_id'])
            result['optimized_urls'] = optimized_urls
            
            logger.info(f"Image uploaded successfully: {result['public_id']}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to upload image: {str(e)}")
            raise
    
    def upload_video(
        self,
        file_path_or_url: str,
        public_id: Optional[str] = None,
        folder: Optional[str] = None,
        tags: Optional[List[str]] = None,
        context: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Upload a video to Cloudinary with automatic optimizations.
        
        Args:
            file_path_or_url: Local file path or URL to upload
            public_id: Custom public ID for the video
            folder: Folder to organize the video
            tags: Tags for the video
            context: Additional metadata
            **kwargs: Additional Cloudinary upload parameters
            
        Returns:
            Upload result with optimized URLs and metadata
        """
        try:
            upload_params = {
                'resource_type': 'video',
                'use_filename': True,
                'unique_filename': True if not public_id else False,
                'overwrite': False,
                **kwargs
            }
            
            if public_id:
                upload_params['public_id'] = public_id
            if folder:
                upload_params['folder'] = folder
            if tags:
                upload_params['tags'] = tags
            if context:
                upload_params['context'] = context
            
            # Upload the video
            result = cloudinary.uploader.upload(file_path_or_url, **upload_params)
            
            # Generate optimized URLs
            optimized_urls = self._generate_optimized_video_urls(result['public_id'])
            result['optimized_urls'] = optimized_urls
            
            logger.info(f"Video uploaded successfully: {result['public_id']}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to upload video: {str(e)}")
            raise
    
    def get_optimized_image_url(
        self,
        public_id: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        crop: str = 'fill',
        gravity: str = 'auto',
        **transformations
    ) -> str:
        """
        Get an optimized image URL with automatic transformations.
        
        Args:
            public_id: Cloudinary public ID of the image
            width: Target width
            height: Target height
            crop: Crop mode (fill, fit, scale, etc.)
            gravity: Gravity for cropping (auto, face, center, etc.)
            **transformations: Additional transformations
            
        Returns:
            Optimized image URL
        """
        transform_params = {
            **self.default_image_transformations,
            **transformations
        }
        
        if width:
            transform_params['width'] = width
        if height:
            transform_params['height'] = height
        if width or height:
            transform_params['crop'] = crop
            transform_params['gravity'] = gravity
        
        return CloudinaryImage(public_id).build_url(**transform_params)
    
    def get_optimized_video_url(
        self,
        public_id: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        **transformations
    ) -> str:
        """
        Get an optimized video URL with automatic transformations.
        
        Args:
            public_id: Cloudinary public ID of the video
            width: Target width
            height: Target height
            **transformations: Additional transformations
            
        Returns:
            Optimized video URL
        """
        transform_params = {
            **self.default_video_transformations,
            **transformations
        }
        
        if width:
            transform_params['width'] = width
        if height:
            transform_params['height'] = height
        
        return CloudinaryVideo(public_id).build_url(**transform_params)
    
    def _generate_optimized_image_urls(self, public_id: str) -> Dict[str, str]:
        """Generate a set of optimized image URLs for different use cases."""
        return {
            'original': self.get_optimized_image_url(public_id),
            'thumbnail': self.get_optimized_image_url(public_id, width=300, height=300),
            'medium': self.get_optimized_image_url(public_id, width=800, height=600),
            'large': self.get_optimized_image_url(public_id, width=1200, height=900),
            'mobile': self.get_optimized_image_url(public_id, width=480, height=360),
            'tablet': self.get_optimized_image_url(public_id, width=768, height=576),
            'desktop': self.get_optimized_image_url(public_id, width=1200, height=900)
        }
    
    def _generate_optimized_video_urls(self, public_id: str) -> Dict[str, str]:
        """Generate a set of optimized video URLs for different use cases."""
        return {
            'original': self.get_optimized_video_url(public_id),
            'mobile': self.get_optimized_video_url(public_id, width=480),
            'tablet': self.get_optimized_video_url(public_id, width=768),
            'desktop': self.get_optimized_video_url(public_id, width=1200),
            'hd': self.get_optimized_video_url(public_id, width=1920)
        }
    
    def delete_resource(self, public_id: str, resource_type: str = 'image') -> Dict[str, Any]:
        """
        Delete a resource from Cloudinary.
        
        Args:
            public_id: Cloudinary public ID of the resource
            resource_type: Type of resource ('image' or 'video')
            
        Returns:
            Deletion result
        """
        try:
            result = cloudinary.uploader.destroy(public_id, resource_type=resource_type)
            logger.info(f"Resource deleted successfully: {public_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to delete resource {public_id}: {str(e)}")
            raise
    
    def get_resource_info(self, public_id: str, resource_type: str = 'image') -> Dict[str, Any]:
        """
        Get detailed information about a Cloudinary resource.
        
        Args:
            public_id: Cloudinary public ID of the resource
            resource_type: Type of resource ('image' or 'video')
            
        Returns:
            Resource information
        """
        try:
            result = cloudinary.api.resource(public_id, resource_type=resource_type)
            return result
        except Exception as e:
            logger.error(f"Failed to get resource info for {public_id}: {str(e)}")
            raise


# Global instance for easy import and use
cloudinary_helper = CloudinaryHelper()

# Convenience functions for direct use
def upload_image(*args, **kwargs):
    """Convenience function to upload an image."""
    return cloudinary_helper.upload_image(*args, **kwargs)

def upload_video(*args, **kwargs):
    """Convenience function to upload a video."""
    return cloudinary_helper.upload_video(*args, **kwargs)

def get_optimized_image_url(*args, **kwargs):
    """Convenience function to get an optimized image URL."""
    return cloudinary_helper.get_optimized_image_url(*args, **kwargs)

def get_optimized_video_url(*args, **kwargs):
    """Convenience function to get an optimized video URL."""
    return cloudinary_helper.get_optimized_video_url(*args, **kwargs)

def delete_resource(*args, **kwargs):
    """Convenience function to delete a resource."""
    return cloudinary_helper.delete_resource(*args, **kwargs)

def get_resource_info(*args, **kwargs):
    """Convenience function to get resource information."""
    return cloudinary_helper.get_resource_info(*args, **kwargs)
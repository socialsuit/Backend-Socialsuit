import cloudinary
import cloudinary.uploader
import os
from typing import Dict, Optional
from pathlib import Path
import logging
from fastapi import HTTPException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CloudinaryService:
    """
    Secure Cloudinary upload service with validation and error handling
    """
    
    # Allowed file types and max size (5MB)
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

    @classmethod
    def initialize(cls):
        """Initialize Cloudinary config with env vars"""
        try:
            # Try to use CLOUDINARY_URL first, then fall back to individual vars
            cloudinary_url = os.getenv("CLOUDINARY_URL")
            if cloudinary_url:
                cloudinary.config(cloudinary_url=cloudinary_url, secure=True)
            else:
                cloudinary.config(
                    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
                    api_key=os.getenv("CLOUDINARY_API_KEY"),
                    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
                    secure=True  # Always use HTTPS
                )
            logger.info("✅ Cloudinary configured")
        except Exception as e:
            logger.error(f"❌ Cloudinary config failed: {e}")
            raise

    @classmethod
    def validate_file(cls, file_path: str) -> bool:
        """
        Validate file before upload:
        - Check extension
        - Check size
        - Verify file exists
        """
        try:
            path = Path(file_path)
            
            # Check file exists
            if not path.exists():
                raise ValueError("File does not exist")
                
            # Check extension
            if path.suffix.lower()[1:] not in cls.ALLOWED_EXTENSIONS:
                raise ValueError(f"Only {cls.ALLOWED_EXTENSIONS} files allowed")
                
            # Check size
            if path.stat().st_size > cls.MAX_FILE_SIZE:
                raise ValueError(f"File exceeds {cls.MAX_FILE_SIZE/1024/1024}MB limit")
                
            return True
            
        except Exception as e:
            logger.error(f"🛑 File validation failed: {e}")
            raise

    @classmethod
    def upload_image(cls, file_path: str, folder: Optional[str] = None) -> Dict:
        """
        Upload image with:
        - Automatic folder organization
        - File validation
        - Error handling
        """
        try:
            # Validate first
            cls.validate_file(file_path)
            
            # Upload with additional options
            result = cloudinary.uploader.upload(
                file_path,
                folder=folder,  # e.g. "user_uploads"
                use_filename=True,  # Keep original filename
                unique_filename=False,  # Allow duplicates
                overwrite=True,
                resource_type="image",
                quality="auto:best"  # Auto-optimize
            )
            
            logger.info(f"📤 Uploaded {file_path} to {result.get('url')}")
            return {
                "public_id": result["public_id"],
                "url": result["secure_url"],
                "format": result["format"],
                "size": os.path.getsize(file_path)
            }
            
        except cloudinary.exceptions.Error as e:
            logger.error(f"☁️ Cloudinary error: {e}")
            raise HTTPException(500, "Image upload failed")
        except Exception as e:
            logger.error(f"⚠️ Upload failed: {e}")
            raise HTTPException(400, str(e))

# Initialize on app startup
CloudinaryService.initialize()
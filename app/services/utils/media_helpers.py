# services/utils/download_media_helper.py

import os
import requests
import tempfile
from app.services.utils.logger_config import logger

import cloudinary
import cloudinary.uploader

# 👉 Cloudinary config
# Initialize Cloudinary with unified URL or individual vars
cloudinary_url = os.getenv("CLOUDINARY_URL")
if cloudinary_url:
    cloudinary.config(cloudinary_url=cloudinary_url, secure=True)
else:
    cloudinary.config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        api_key=os.getenv("CLOUDINARY_API_KEY"),
        api_secret=os.getenv("CLOUDINARY_API_SECRET"),
        secure=True
    )

def download_media_from_cloudinary(media_url: str, suffix=".jpg") -> str:
    """
    Downloads a media file from Cloudinary (or any URL) to a local temp file.
    Returns the local file path.
    """
    try:
        response = requests.get(media_url, stream=True, timeout=30)
        response.raise_for_status()

        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                tmp_file.write(chunk)
        tmp_file.close()

        logger.info(f"[Download] Temp file created: {tmp_file.name}")
        return tmp_file.name

    except Exception as e:
        logger.error(f"[Download] Failed: {e}")
        raise RuntimeError(f"Failed to download media: {str(e)}")

def upload_temp_file_to_cdn(file_path: str, folder: str = "socialsuit_uploads") -> str:
    """
    Uploads a local temp file to Cloudinary CDN.
    Returns the secure CDN URL.
    """
    try:
        response = cloudinary.uploader.upload(
            file_path,
            folder=folder
        )
        url = response.get("secure_url")
        if not url:
            raise RuntimeError("No URL returned from Cloudinary upload.")
        
        logger.info(f"[Upload] File uploaded to CDN: {url}")
        return url

    except Exception as e:
        logger.error(f"[Upload] Failed to CDN: {e}")
        raise RuntimeError(f"Failed to upload to CDN: {str(e)}")

def cleanup_temp_file(file_path: str):
    """
    Deletes the local temp file after upload.
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"[Cleanup] Temp file deleted: {file_path}")
    except Exception as e:
        logger.warning(f"[Cleanup] Could not delete temp file: {e}")
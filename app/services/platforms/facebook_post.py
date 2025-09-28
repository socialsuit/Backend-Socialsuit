import os
import requests
from app.services.utils.media_helpers import (
    download_media_from_cloudinary,
    upload_temp_file_to_cdn,
    cleanup_temp_file
)
from app.services.utils.logger_config import logger

def call_facebook_post(user_token: dict, post_payload: dict):
    """
    Post text, image, or video to a Facebook Page using Graph API.
    If media URL is given, it will download → upload to CDN → post.
    """
    access_token = user_token["access_token"]
    page_id = user_token["page_id"]
    text = post_payload.get("text", "")
    media_url = post_payload.get("media_url")
    media_type = post_payload.get("media_type", "image")  # default to image

    final_media_url = media_url
    temp_file = None

    try:
        logger.info(f"[Facebook] Preparing post | Page ID: {page_id} | Type: {media_type}")

        # If media is provided
        if media_url:
            # Download from Cloudinary or any URL
            suffix = ".mp4" if media_type == "video" else ".jpg"
            temp_file = download_media_from_cloudinary(media_url, suffix=suffix)
            logger.info(f"[Facebook] Downloaded temp file: {temp_file}")

            # Upload to your own CDN (optional)
            final_media_url = upload_temp_file_to_cdn(
                temp_file,
                folder="socialsuit_facebook_posts"
            )
            logger.info(f"[Facebook] Uploaded to CDN: {final_media_url}")

            if media_type == "video":
                # Video post endpoint
                post_url = f"https://graph.facebook.com/{page_id}/videos"
                payload = {
                    "access_token": access_token,
                    "description": text,
                    "file_url": final_media_url
                }
            else:
                # Image post endpoint
                post_url = f"https://graph.facebook.com/{page_id}/photos"
                payload = {
                    "access_token": access_token,
                    "caption": text,
                    "url": final_media_url
                }

        else:
            # Text-only post → Feed endpoint
            post_url = f"https://graph.facebook.com/{page_id}/feed"
            payload = {
                "access_token": access_token,
                "message": text
            }

        response = requests.post(post_url, data=payload)
        logger.info(f"[Facebook] Post response: {response.status_code} | {response.text}")

        return response.json()

    except Exception as e:
        logger.exception(f"[Facebook] Post failed: {str(e)}")
        return {"error": str(e)}

    finally:
        if temp_file:
            cleanup_temp_file(temp_file)
            logger.info(f"[Facebook] Temp file cleaned up: {temp_file}")
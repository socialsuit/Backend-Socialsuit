import requests
import logging
import os
from app.services.utils.media_helpers import (
    download_media_from_cloudinary,
    cleanup_temp_file,
    upload_temp_file_to_cdn
)

logger = logging.getLogger("socialsuit")  # ✅ Use standard logger

def call_telegram_api(user_token: dict, post_payload: dict):
    """
    Publishes a post to Telegram channel using Bot API.
    Downloads Cloudinary URL → uploads as native file.
    Also uploads to CDN for tracking (optional).
    """
    bot_token = user_token["access_token"]
    channel_id = user_token["channel_id"]

    text = post_payload.get("text", "")
    media_url = post_payload.get("media_url")
    media_type = post_payload.get("media_type", "image")

    logger.info(f"[Telegram] Start | Media type: {media_type} | Channel: {channel_id}")

    temp_file = None
    response = None

    try:
        if not media_url:
            # ✅ Just text
            logger.info("[Telegram] Sending text message only.")
            api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": channel_id,
                "text": text
            }
            response = requests.post(api_url, data=payload)
            logger.info(f"[Telegram] Text sent | Status: {response.status_code}")
            return response.json()

        # ✅ Download media to temp
        suffix = ".mp4" if media_type == "video" else ".jpg"
        temp_file = download_media_from_cloudinary(media_url, suffix=suffix)
        logger.info(f"[Telegram] Downloaded temp file: {temp_file}")

        # ✅ Optional: Upload temp file to your CDN (for logs / reuse)
        cdn_url = upload_temp_file_to_cdn(temp_file)
        logger.info(f"[Telegram] Uploaded temp file to CDN: {cdn_url}")

        if media_type == "video":
            api_url = f"https://api.telegram.org/bot{bot_token}/sendVideo"
            files = {"video": open(temp_file, "rb")}
        else:
            api_url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
            files = {"photo": open(temp_file, "rb")}

        payload = {
            "chat_id": channel_id,
            "caption": text
        }

        response = requests.post(api_url, data=payload, files=files)
        logger.info(f"[Telegram] Media sent | Status: {response.status_code}")

        files[list(files.keys())[0]].close()

        return response.json()

    except Exception as e:
        logger.exception(f"[Telegram] Post failed: {e}")
        return {"error": str(e)}

    finally:
        if temp_file:
            cleanup_temp_file(temp_file)
            logger.info(f"[Telegram] Cleaned up temp file: {temp_file}")
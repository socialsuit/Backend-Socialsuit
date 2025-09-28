import requests
import logging
from app.services.utils.media_helpers import (
    download_media_from_cloudinary,
    cleanup_temp_file,
    upload_temp_file_to_cdn
)

logger = logging.getLogger("socialsuit")  # ✅ Standard logger

def call_tiktok_post(user_token: dict, post_payload: dict):
    """
    Publishes a video post to TikTok using TikTok Open API.
    Uses Cloudinary video URL → temp download → optional CDN upload → native upload.
    """
    access_token = user_token["access_token"]
    open_id = user_token["open_id"]

    video_url = post_payload.get("media_url")
    description = post_payload.get("text", "")

    logger.info(f"[TikTok] Start | OpenID: {open_id}")

    temp_file = None
    response = None

    try:
        # ✅ Download video to temp
        temp_file = download_media_from_cloudinary(video_url, suffix=".mp4")
        logger.info(f"[TikTok] Downloaded temp video: {temp_file}")

        # ✅ Upload temp video to CDN for audit (optional)
        cdn_url = upload_temp_file_to_cdn(temp_file)
        logger.info(f"[TikTok] Uploaded temp video to CDN: {cdn_url}")

        # ✅ Upload to TikTok (native binary)
        upload_url = f"https://open.tiktokapis.com/v2/post/publish/video/"
        headers = {"Authorization": f"Bearer {access_token}"}

        files = {
            "video": open(temp_file, "rb")
        }

        data = {
            "open_id": open_id,
            "text": description
        }

        response = requests.post(upload_url, data=data, files=files, headers=headers)
        logger.info(f"[TikTok] Uploaded video | Status: {response.status_code}")

        files["video"].close()

        return response.json()

    except Exception as e:
        logger.exception(f"[TikTok] Upload failed: {e}")
        return {"error": str(e)}

    finally:
        if temp_file:
            cleanup_temp_file(temp_file)
            logger.info(f"[TikTok] Cleaned up temp file: {temp_file}")
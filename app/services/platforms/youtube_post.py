from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
import requests
import logging
import os

from app.services.utils.media_helpers import download_media_from_cloudinary, cleanup_temp_file, upload_temp_file_to_cdn

logger = logging.getLogger("socialsuit")  # ✅ Proper logger name

def call_youtube_post(user_token: dict, post_payload: dict):
    """
    Upload a video to YouTube using Google API client.
    Resumable native upload with Cloudinary temp.
    """
    credentials = user_token["credentials"]  # Valid OAuth2 credentials

    title = post_payload.get("title", "Untitled Video")
    description = post_payload.get("text", "")
    media_url = post_payload.get("media_url")

    youtube = build("youtube", "v3", credentials=credentials)

    temp_file = None

    try:
        # ✅ Download video → temp file
        temp_file = download_media_from_cloudinary(media_url, suffix=".mp4")
        logger.info(f"[YouTube] Downloaded temp file: {temp_file}")

        # ✅ OPTIONAL: Upload to CDN (not needed for native YouTube upload)
        # final_media_url = upload_temp_file_to_cdn(temp_file)
        # logger.info(f"[YouTube] Uploaded to CDN: {final_media_url}")

        # ✅ Open file stream for resumable upload
        with open(temp_file, "rb") as f:
            media = MediaIoBaseUpload(
                f,
                mimetype="video/*",
                chunksize=8 * 1024 * 1024,  # 8 MB
                resumable=True
            )

            request = youtube.videos().insert(
                part="snippet,status",
                body={
                    "snippet": {
                        "title": title,
                        "description": description,
                        "tags": ["SocialSuit"],
                        "categoryId": "22"  # People & Blogs
                    },
                    "status": {"privacyStatus": "public"}
                },
                media_body=media
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logger.info(f"[YouTube] Upload progress: {int(status.progress() * 100)}%")

            logger.info(f"[YouTube] Upload complete | Video ID: {response.get('id')}")
            return response

    except Exception as e:
        logger.exception(f"[YouTube] Upload failed: {str(e)}")
        return {"error": str(e)}

    finally:
        if temp_file:
            try:
                cleanup_temp_file(temp_file)
                logger.info(f"[YouTube] Temp file cleaned up: {temp_file}")
            except Exception as ce:
                logger.warning(f"[YouTube] Cleanup failed: {str(ce)}")
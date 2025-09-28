import os
import requests
import logging

from app.services.utils.media_helpers import (
    download_media_from_cloudinary,
    cleanup_temp_file,
    upload_temp_file_to_cdn
)

logger = logging.getLogger("socialsuit")  # ✅ Standard named logger

def call_twitter_post(user_token: dict, post_payload: dict):
    """
    Twitter native upload: handles both image and chunked video.
    Includes proper error handling and retry logic for API rate limits.
    """
    # Validate required token fields
    if not user_token.get("access_token"):
        logger.error("[Twitter] Missing access_token in user_token")
        return {"error": "Missing access token", "retry": False}
    access_token = user_token["access_token"]
    media_url = post_payload.get("media_url")
    text = post_payload.get("text", "")
    media_type = post_payload.get("media_type", "image")

    headers = {"Authorization": f"Bearer {access_token}"}

    media_id = None
    temp_file = None

    try:
        if media_url:
            if media_type == "video":
                # ✅ Download video to temp
                temp_file = download_media_from_cloudinary(media_url, suffix=".mp4")
                total_bytes = os.path.getsize(temp_file)

                # ✅ Upload to CDN for audit
                cdn_url = upload_temp_file_to_cdn(temp_file)
                logger.info(f"[Twitter] Video uploaded to CDN: {cdn_url}")

                logger.info(f"[Twitter] Video size: {total_bytes} bytes")

                # ✅ INIT upload
                init_res = requests.post(
                    "https://upload.twitter.com/1.1/media/upload.json",
                    data={
                        "command": "INIT",
                        "media_type": "video/mp4",
                        "total_bytes": total_bytes,
                        "media_category": "tweet_video"
                    },
                    headers=headers
                )
                init_json = init_res.json()
                media_id = init_json.get("media_id_string")
                logger.info(f"[Twitter] INIT media_id: {media_id}")

                # ✅ APPEND chunks
                segment_id = 0
                with open(temp_file, "rb") as f:
                    while True:
                        chunk = f.read(4 * 1024 * 1024)  # 4 MB
                        if not chunk:
                            break

                        append_res = requests.post(
                            "https://upload.twitter.com/1.1/media/upload.json",
                            data={
                                "command": "APPEND",
                                "media_id": media_id,
                                "segment_index": segment_id
                            },
                            files={"media": chunk},
                            headers=headers
                        )
                        logger.info(f"[Twitter] APPEND segment {segment_id}: {append_res.status_code}")
                        segment_id += 1

                # ✅ FINALIZE
                finalize_res = requests.post(
                    "https://upload.twitter.com/1.1/media/upload.json",
                    data={
                        "command": "FINALIZE",
                        "media_id": media_id
                    },
                    headers=headers
                )
                logger.info(f"[Twitter] FINALIZE response: {finalize_res.json()}")

            else:
                # ✅ For image, download temp optional but good for audit
                temp_file = download_media_from_cloudinary(media_url, suffix=".jpg")

                # ✅ Upload image to CDN for audit
                cdn_url = upload_temp_file_to_cdn(temp_file)
                logger.info(f"[Twitter] Image uploaded to CDN: {cdn_url}")

                with open(temp_file, "rb") as f:
                    img_res = requests.post(
                        "https://upload.twitter.com/1.1/media/upload.json",
                        files={"media": f},
                        headers=headers
                    )
                img_json = img_res.json()
                media_id = img_json.get("media_id_string")
                logger.info(f"[Twitter] Uploaded image media_id: {media_id}")
                # ✅ Post Tweet
        payload = {"status": text}
        if media_id:
            payload["media_ids"] = media_id

        post_url = "https://api.twitter.com/1.1/statuses/update.json"
        res = requests.post(post_url, params=payload, headers=headers)
        logger.info(f"[Twitter] Tweet posted: {res.status_code}")

        return res.json()

    except requests.exceptions.HTTPError as http_err:
        status_code = getattr(http_err.response, 'status_code', 0)
        response_text = getattr(http_err.response, 'text', '')
        
        # Handle rate limiting (429) - should retry
        if status_code == 429:
            logger.warning(f"[Twitter] Rate limited: {response_text}")
            return {"error": "Rate limited by Twitter API", "retry": True}
        
        # Handle authentication errors (401) - should not retry
        elif status_code == 401:
            logger.error(f"[Twitter] Authentication failed: {response_text}")
            return {"error": "Authentication failed", "retry": False}
            
        # Handle other HTTP errors
        else:
            logger.error(f"[Twitter] HTTP error {status_code}: {response_text}")
            # Retry for server errors (5xx), don't retry for client errors (4xx)
            should_retry = status_code >= 500
            return {"error": f"HTTP error {status_code}: {str(http_err)}", "retry": should_retry}
    
    except requests.exceptions.ConnectionError as conn_err:
        logger.error(f"[Twitter] Connection error: {conn_err}")
        return {"error": f"Connection error: {str(conn_err)}", "retry": True}
        
    except requests.exceptions.Timeout as timeout_err:
        logger.error(f"[Twitter] Request timed out: {timeout_err}")
        return {"error": f"Request timed out: {str(timeout_err)}", "retry": True}
        
    except Exception as e:
        logger.exception(f"[Twitter] Unexpected error: {e}")
        return {"error": str(e), "retry": True}

    finally:
        if temp_file:
            cleanup_temp_file(temp_file)
            logger.info(f"[Twitter] Cleaned up temp file: {temp_file}")
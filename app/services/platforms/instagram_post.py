import requests
from app.services.utils.media_helpers import (
    download_media_from_cloudinary,
    cleanup_temp_file,
    upload_temp_file_to_cdn  # ✅ CDN uploader
)
from app.services.utils.logger_config import logger  # ✅ Logger

def call_instagram_post(user_token: dict, post_payload: dict):
    access_token = user_token["access_token"]
    ig_user_id = user_token["ig_user_id"]
    caption = post_payload.get("text", "")
    media_url = post_payload.get("media_url")
    media_type = post_payload.get("media_type", "image")

    final_media_url = media_url
    temp_file = None

    try:
        logger.info(f"[Instagram] Preparing post | IG User: {ig_user_id} | Type: {media_type}")

        # 👉 If a media_url exists & is already a URL, re-upload to your CDN for safety
        if media_url and media_url.startswith("https://"):
            suffix = ".mp4" if media_type == "video" else ".jpg"

            # 1️⃣ Download original file
            temp_file = download_media_from_cloudinary(media_url, suffix=suffix)
            logger.info(f"[Instagram] Downloaded temp file: {temp_file}")

            # 2️⃣ Upload to your Cloudinary folder for Instagram
            final_media_url = upload_temp_file_to_cdn(
                temp_file,
                folder="socialsuit_instagram_posts"  # ✅ Folder name for clarity
            )
            logger.info(f"[Instagram] Uploaded to CDN: {final_media_url}")

        # 3️⃣ Create IG container
        container_url = f"https://graph.facebook.com/v19.0/{ig_user_id}/media"

        payload = {
            "access_token": access_token,
            "caption": caption
        }

        if media_type == "video":
            payload["media_type"] = "VIDEO"
            payload["video_url"] = final_media_url
        else:
            payload["image_url"] = final_media_url

        logger.info(f"[Instagram] Creating media container...")

        res = requests.post(container_url, data=payload)
        container_id = res.json().get("id")

        if not container_id:
            logger.warning(f"[Instagram] Failed to create container: {res.json()}")
            return {"error": "Failed to create container", "details": res.json()}

        # 4️⃣ Publish post
        publish_url = f"https://graph.facebook.com/v19.0/{ig_user_id}/media_publish"
        logger.info(f"[Instagram] Publishing container ID: {container_id}")

        publish_res = requests.post(publish_url, data={
            "creation_id": container_id,
            "access_token": access_token
        })

        if publish_res.status_code != 200:
            logger.warning(f"[Instagram] Publish failed: {publish_res.text}")

        return publish_res.json()

    except Exception as e:
        logger.exception(f"[Instagram] Post failed: {str(e)}")
        return {"error": str(e)}

    finally:
        if temp_file:
            cleanup_temp_file(temp_file)
            logger.info(f"[Instagram] Cleaned up temp file: {temp_file}")
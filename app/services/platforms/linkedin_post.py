import requests
from app.services.utils.media_helpers import (
    download_media_from_cloudinary,
    upload_temp_file_to_cdn,
    cleanup_temp_file
)
from app.services.utils.logger_config import logger

def call_linkedin_post(user_token: dict, post_payload: dict):
    """
    Upload a post to LinkedIn.
    Supports text-only, image, or video.
    """
    access_token = user_token["access_token"]
    owner = user_token["linkedin_urn"]  # Example: "urn:li:person:XXXXX"
    text = post_payload.get("text", "")
    media_url = post_payload.get("media_url")
    media_type = post_payload.get("media_type", "image")  # image or video

    temp_file = None
    upload_url = None
    asset = None

    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0"
    }

    try:
        logger.info(f"[LinkedIn] Preparing post | Owner: {owner} | Type: {media_type}")

        if media_url and media_url.startswith("https://"):

            suffix = ".mp4" if media_type == "video" else ".jpg"
            temp_file = download_media_from_cloudinary(media_url, suffix=suffix)
            logger.info(f"[LinkedIn] Downloaded temp file: {temp_file}")

            # 1️⃣ Register upload (video or image asset)
            register_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
            register_body = {
                "registerUploadRequest": {
                    "recipes": [
                        "urn:li:digitalmediaRecipe:feedshare-video"
                    ] if media_type == "video" else [
                        "urn:li:digitalmediaRecipe:feedshare-image"
                    ],
                    "owner": owner,
                    "serviceRelationships": [
                        {
                            "relationshipType": "OWNER",
                            "identifier": "urn:li:userGeneratedContent"
                        }
                    ]
                }
            }

            register_res = requests.post(register_url, json=register_body, headers={**headers, "Content-Type": "application/json"})
            register_json = register_res.json()
            logger.info(f"[LinkedIn] Register Upload response: {register_json}")

            upload_url = register_json["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
            asset = register_json["value"]["asset"]

            # 2️⃣ Upload binary file
            with open(temp_file, "rb") as f:
                upload_res = requests.put(upload_url, data=f, headers={"Authorization": f"Bearer {access_token}"})
                logger.info(f"[LinkedIn] Upload binary response: {upload_res.status_code}")

        # 3️⃣ Create post (text + asset)
        api_url = "https://api.linkedin.com/v2/ugcPosts"

        share_media_category = "NONE"
        media = []

        if asset:
            share_media_category = "VIDEO" if media_type == "video" else "IMAGE"
            media = [{
                "status": "READY",
                "description": {"text": text},
                "media": asset,
                "title": {"text": "Social Suit Upload"}
            }]

        body = {
            "author": owner,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": share_media_category,
                    "media": media
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
        }

        res = requests.post(api_url, json=body, headers={**headers, "Content-Type": "application/json"})
        logger.info(f"[LinkedIn] Post published | Status: {res.status_code}")

        return res.json()

    except Exception as e:
        logger.exception(f"[LinkedIn] Post failed: {e}")
        return {"error": str(e)}
    finally:
        if temp_file:
            cleanup_temp_file(temp_file)
            logger.info(f"[LinkedIn] Cleaned up temp file: {temp_file}")
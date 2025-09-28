import os
import requests
import logging

from app.services.database.database import get_db
from app.services.models.token_model import PlatformToken

TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET")

logger = logging.getLogger(__name__)  

def refresh_tiktok_token():
    """
    Refresh TikTok tokens using OAuth refresh flow.
    Logs each attempt and result.
    """
    db = next(get_db())
    tokens = db.query(PlatformToken).filter(
        PlatformToken.platform == "tiktok",
        PlatformToken.refresh_token.isnot(None)
    ).all()

    for token in tokens:
        try:
            payload = {
                "client_key": TIKTOK_CLIENT_KEY,
                "client_secret": TIKTOK_CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": token.refresh_token
            }

            res = requests.post(
                "https://open-api.tiktok.com/oauth/refresh_token/",
                data=payload,
                timeout=15
            )
            res.raise_for_status()
            data = res.json()

            if "access_token" in data:
                token.access_token = data["access_token"]
                token.refresh_token = data.get("refresh_token", token.refresh_token)  # If TikTok returns new RT
                db.add(token)
                logger.info(f"[TikTok Refresh] Token refreshed for user_id={token.user_id}")
            else:
                logger.warning(f"[TikTok Refresh] No access_token in response for user_id={token.user_id} — Response: {data}")

        except Exception as e:
            logger.exception(f"[TikTok Refresh] Failed for user_id={token.user_id}: {e}")

    db.commit()
    logger.info("[TikTok Refresh] All TikTok tokens refreshed & committed.")
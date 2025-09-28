import os
import requests
import logging

from app.services.database.database import get_db
from app.services.models.token_model import PlatformToken

YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID")
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET")

logger = logging.getLogger(__name__)  

def refresh_youtube_token():
    """
    Refresh YouTube access tokens using Google's OAuth2 refresh flow.
    Stores updated access tokens.
    """
    db = next(get_db())
    tokens = db.query(PlatformToken).filter(
        PlatformToken.platform == "youtube",
        PlatformToken.refresh_token.isnot(None)
    ).all()

    for token in tokens:
        try:
            data = {
                "client_id": YOUTUBE_CLIENT_ID,
                "client_secret": YOUTUBE_CLIENT_SECRET,
                "refresh_token": token.refresh_token,
                "grant_type": "refresh_token"
            }

            res = requests.post(
                "https://oauth2.googleapis.com/token",
                data=data,
                timeout=15
            )
            res.raise_for_status()
            resp_data = res.json()

            if "access_token" in resp_data:
                token.access_token = resp_data["access_token"]
                db.add(token)
                logger.info(f"[YouTube Refresh] Token refreshed for user_id={token.user_id}")
            else:
                logger.warning(f"[YouTube Refresh] No access_token in response for user_id={token.user_id} — Response: {resp_data}")

        except Exception as e:
            logger.exception(f"[YouTube Refresh] Failed for user_id={token.user_id}: {e}")

    db.commit()
    logger.info("[YouTube Refresh] All YouTube tokens refreshed & committed.")
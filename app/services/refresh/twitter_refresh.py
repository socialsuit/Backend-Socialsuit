import os
import requests
import logging

from app.services.database.database import get_db
from app.services.models.token_model import PlatformToken

TWITTER_CLIENT_ID = os.getenv("TWITTER_CLIENT_ID")
TWITTER_CLIENT_SECRET = os.getenv("TWITTER_CLIENT_SECRET")

logger = logging.getLogger(__name__)  

def refresh_twitter_token():
    """
    Refresh Twitter tokens using OAuth2 PKCE refresh flow.
    Logs attempts & results.
    """
    db = next(get_db())
    tokens = db.query(PlatformToken).filter(
        PlatformToken.platform == "twitter",
        PlatformToken.refresh_token.isnot(None)
    ).all()

    for token in tokens:
        try:
            data = {
                "client_id": TWITTER_CLIENT_ID,
                "grant_type": "refresh_token",
                "refresh_token": token.refresh_token
            }

            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }

            res = requests.post(
                "https://api.twitter.com/2/oauth2/token",
                data=data,
                headers=headers,
                auth=(TWITTER_CLIENT_ID, TWITTER_CLIENT_SECRET),
                timeout=15
            )
            res.raise_for_status()
            resp_data = res.json()

            if "access_token" in resp_data:
                token.access_token = resp_data["access_token"]
                token.refresh_token = resp_data.get("refresh_token", token.refresh_token)
                db.add(token)
                logger.info(f"[Twitter Refresh] Token refreshed for user_id={token.user_id}")
            else:
                logger.warning(f"[Twitter Refresh] No access_token in response for user_id={token.user_id} — Response: {resp_data}")

        except Exception as e:
            logger.exception(f"[Twitter Refresh] Failed for user_id={token.user_id}: {e}")

    db.commit()
    logger.info("[Twitter Refresh] All Twitter tokens refreshed & committed.")
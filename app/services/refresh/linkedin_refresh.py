import os
import requests
import logging

from app.services.database.database import get_db
from app.services.models.token_model import PlatformToken

LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")

logger = logging.getLogger(__name__)  

def refresh_linkedin_token():
    """
    Refresh LinkedIn OAuth tokens for all stored users.
    Logs each refresh attempt + result.
    """
    db = next(get_db())
    tokens = db.query(PlatformToken).filter(
        PlatformToken.platform == "linkedin",
        PlatformToken.refresh_token.isnot(None)
    ).all()

    for token in tokens:
        try:
            data = {
                "grant_type": "refresh_token",
                "refresh_token": token.refresh_token,
                "client_id": LINKEDIN_CLIENT_ID,
                "client_secret": LINKEDIN_CLIENT_SECRET
            }

            res = requests.post(
                "https://www.linkedin.com/oauth/v2/accessToken",
                data=data,
                timeout=15
            )

            res.raise_for_status()
            response_json = res.json()

            if "access_token" in response_json:
                token.access_token = response_json["access_token"]
                db.add(token)
                logger.info(f"[LinkedIn Refresh] Token refreshed for user_id={token.user_id}")

            else:
                logger.warning(f"[LinkedIn Refresh] No access_token in response for user_id={token.user_id} — Response: {response_json}")

        except Exception as e:
            logger.exception(f"[LinkedIn Refresh] Failed for user_id={token.user_id}: {e}")

    db.commit()
    logger.info("[LinkedIn Refresh] All tokens refreshed and committed.")
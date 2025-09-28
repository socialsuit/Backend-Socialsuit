import os
import requests
from datetime import datetime, timedelta

from app.services.database.database import get_db
from app.services.models.token_model import PlatformToken
from app.services.utils.logger_config import setup_logger

META_APP_ID = os.getenv("META_APP_ID")
META_APP_SECRET = os.getenv("META_APP_SECRET")

logger = setup_logger("meta_refresh")  
def refresh_meta_token():
    """
    Refresh Facebook + Instagram tokens.
    Uses long-lived token exchange for Facebook Graph API.
    Logs each step and updates token expiration times.
    """
    logger.info("[META_REFRESH] Starting Meta token refresh process")
    
    if not META_APP_ID or not META_APP_SECRET:
        logger.error("[META_REFRESH] Missing META_APP_ID or META_APP_SECRET environment variables")
        return False
        
    db = next(get_db())
    try:
        # Get tokens that need refreshing (expire within 24 hours or have no expiration set)
        tomorrow = datetime.utcnow() + timedelta(days=1)
        
        tokens = db.query(PlatformToken).filter(
            PlatformToken.platform.in_(["facebook", "instagram"]),
            PlatformToken.refresh_token.isnot(None),
            (PlatformToken.expires_at.is_(None) | (PlatformToken.expires_at <= tomorrow))
        ).all()
        
        logger.info(f"[META_REFRESH] Found {len(tokens)} tokens to refresh")

        refresh_count = 0
        error_count = 0
        
        for token in tokens:
            try:
                logger.info(f"[META_REFRESH] Refreshing token for user_id={token.user_id} ({token.platform})")
                
                res = requests.get(
                    "https://graph.facebook.com/v18.0/oauth/access_token",
                    params={
                        "grant_type": "fb_exchange_token",
                        "client_id": META_APP_ID,
                        "client_secret": META_APP_SECRET,
                        "fb_exchange_token": token.refresh_token
                    },
                    timeout=15
                )

                res.raise_for_status()
                data = res.json()

                if "access_token" in data:
                    token.access_token = data["access_token"]
                    
                    # Set expiration time (60 days from now for long-lived tokens)
                    token.expires_at = datetime.utcnow() + timedelta(days=60)
                    
                    # Update the token in the database
                    token.updated_at = datetime.utcnow()
                    db.add(token)
                    refresh_count += 1
                    logger.info(f"[META_REFRESH] Token refreshed for user_id={token.user_id} ({token.platform})")
                else:
                    error_count += 1
                    logger.warning(f"[META_REFRESH] No access_token for user_id={token.user_id} — Response: {data}")

            except requests.exceptions.RequestException as e:
                error_count += 1
                logger.error(f"[META_REFRESH] API request failed for user_id={token.user_id} ({token.platform}): {e}")
            except Exception as e:
                error_count += 1
                logger.exception(f"[META_REFRESH] Failed for user_id={token.user_id} ({token.platform}): {e}")

        # Commit all changes at once
        try:
            db.commit()
            logger.info(f"[META_REFRESH] All tokens refreshed and committed. Success: {refresh_count}, Errors: {error_count}")
            return True
        except Exception as e:
            db.rollback()
            logger.exception(f"[META_REFRESH] Failed to commit token updates: {e}")
            return False
    except Exception as e:
        logger.exception(f"[META_REFRESH] Unexpected error during token refresh: {e}")
        return False
    finally:
        db.close()
        logger.info("[META_REFRESH] DB session closed.")
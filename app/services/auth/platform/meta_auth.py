# services/auth/meta_auth.py

import os
import requests
from fastapi import Request
from app.services.database.database import get_db
from app.services.models.token_model import PlatformToken

META_APP_ID = os.getenv("META_APP_ID")
META_APP_SECRET = os.getenv("META_APP_SECRET")
REDIRECT_URI = os.getenv("META_REDIRECT_URI")

AUTH_URL = (
    "https://www.facebook.com/v19.0/dialog/oauth"
    "?client_id={app_id}&redirect_uri={redirect_uri}"
    "&scope=pages_manage_posts,pages_read_engagement,instagram_basic,pages_show_list"
)

TOKEN_URL = "https://graph.facebook.com/v19.0/oauth/access_token"
LONG_LIVED_URL = "https://graph.facebook.com/v19.0/oauth/access_token"


def get_meta_login_url() -> str:
    return AUTH_URL.format(app_id=META_APP_ID, redirect_uri=REDIRECT_URI)


def exchange_code(code: str, user_id: str):
    """
    1) Exchange short-lived code for access token
    2) Exchange short-lived token for long-lived token (Meta best practice)
    3) Save to DB
    """
    params = {
        "client_id": META_APP_ID,
        "client_secret": META_APP_SECRET,
        "redirect_uri": REDIRECT_URI,
        "code": code
    }

    res = requests.get(TOKEN_URL, params=params)
    res_json = res.json()

    short_token = res_json.get("access_token")
    if not short_token:
        return {"error": "Meta code exchange failed"}

    # Now exchange short-lived for long-lived token
    long_res = requests.get(
        LONG_LIVED_URL,
        params={
            "grant_type": "fb_exchange_token",
            "client_id": META_APP_ID,
            "client_secret": META_APP_SECRET,
            "fb_exchange_token": short_token
        }
    )
    long_json = long_res.json()
    access_token = long_json.get("access_token")

    if not access_token:
        return {"error": "Long-lived token exchange failed"}

    # Save in DB
    db = next(get_db())

    new_token = PlatformToken(
        user_id=user_id,
        platform="meta",
        access_token=access_token,
        refresh_token=None  # Meta uses long-lived access tokens instead of refresh_token
    )
    db.add(new_token)
    db.commit()

    return {"msg": "Meta connected!", "access_token": access_token}


def refresh_token(old_token: str) -> dict:
    """
    Meta tokens: refresh means repeat long-lived step.
    """
    res = requests.get(
        LONG_LIVED_URL,
        params={
            "grant_type": "fb_exchange_token",
            "client_id": META_APP_ID,
            "client_secret": META_APP_SECRET,
            "fb_exchange_token": old_token
        }
    )
    res.raise_for_status()
    return res.json()


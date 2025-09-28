# services/auth/tiktok_auth.py

import os
import requests
from app.services.database.database import get_db
from app.services.models.token_model import PlatformToken

TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET")
TIKTOK_REDIRECT_URI = os.getenv("TIKTOK_REDIRECT_URI")

AUTH_URL = (
    "https://www.tiktok.com/v2/auth/authorize/"
    "?client_key={client_key}"
    "&response_type=code"
    "&scope=user.info.basic,video.upload"
    "&redirect_uri={redirect_uri}"
)

TOKEN_URL = "https://open-api.tiktok.com/v2/oauth/token/"


def get_tiktok_login_url() -> str:
    return AUTH_URL.format(client_key=TIKTOK_CLIENT_KEY, redirect_uri=TIKTOK_REDIRECT_URI)


def exchange_code(code: str, user_id: str) -> dict:
    """
    Exchange TikTok OAuth code for access & refresh tokens.
    """
    data = {
        "client_key": TIKTOK_CLIENT_KEY,
        "client_secret": TIKTOK_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": TIKTOK_REDIRECT_URI
    }

    res = requests.post(TOKEN_URL, data=data)
    res_json = res.json()

    access_token = res_json.get("data", {}).get("access_token")
    refresh_token = res_json.get("data", {}).get("refresh_token")
    expires_in = res_json.get("data", {}).get("expires_in")

    if not access_token:
        return {"error": "No access token returned", "raw": res_json}

    db = next(get_db())
    new_token = PlatformToken(
        user_id=user_id,
        platform="tiktok",
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in
    )
    db.add(new_token)
    db.commit()

    return {
        "msg": "TikTok connected!",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": expires_in
    }


def refresh_tiktok_token(refresh_token: str) -> dict:
    """
    Refresh TikTok access token using refresh_token.
    """
    data = {
        "client_key": TIKTOK_CLIENT_KEY,
        "client_secret": TIKTOK_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }

    res = requests.post(TOKEN_URL, data=data)
    res_json = res.json()

    new_access_token = res_json.get("data", {}).get("access_token")
    new_refresh_token = res_json.get("data", {}).get("refresh_token")
    expires_in = res_json.get("data", {}).get("expires_in")

    if not new_access_token:
        return {"error": "No new access token returned", "raw": res_json}

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "expires_in": expires_in
    }

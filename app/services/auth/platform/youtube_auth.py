# services/auth/youtube_auth.py

import os
import requests
from app.services.database.database import get_db
from app.services.models.token_model import PlatformToken

YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID")
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET")
YOUTUBE_REDIRECT_URI = os.getenv("YOUTUBE_REDIRECT_URI")

AUTH_URL = (
    "https://accounts.google.com/o/oauth2/v2/auth"
    "?client_id={client_id}"
    "&redirect_uri={redirect_uri}"
    "&response_type=code"
    "&scope=https://www.googleapis.com/auth/youtube.upload"
    "&access_type=offline"
    "&prompt=consent"
)

TOKEN_URL = "https://oauth2.googleapis.com/token"


def get_youtube_login_url() -> str:
    return AUTH_URL.format(client_id=YOUTUBE_CLIENT_ID, redirect_uri=YOUTUBE_REDIRECT_URI)


def exchange_code(code: str, user_id: str) -> dict:
    """
    Exchange YouTube OAuth code for access & refresh token.
    """
    data = {
        "code": code,
        "client_id": YOUTUBE_CLIENT_ID,
        "client_secret": YOUTUBE_CLIENT_SECRET,
        "redirect_uri": YOUTUBE_REDIRECT_URI,
        "grant_type": "authorization_code"
    }

    res = requests.post(TOKEN_URL, data=data)
    res_json = res.json()

    access_token = res_json.get("access_token")
    refresh_token = res_json.get("refresh_token")
    expires_in = res_json.get("expires_in")

    if not access_token:
        return {"error": "No access token returned", "raw": res_json}

    db = next(get_db())
    new_token = PlatformToken(
        user_id=user_id,
        platform="youtube",
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in
    )
    db.add(new_token)
    db.commit()

    return {
        "msg": "YouTube connected!",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": expires_in
    }


def refresh_youtube_token(refresh_token: str) -> dict:
    """
    Refresh YouTube access token using refresh_token.
    """
    data = {
        "client_id": YOUTUBE_CLIENT_ID,
        "client_secret": YOUTUBE_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }

    res = requests.post(TOKEN_URL, data=data)
    res_json = res.json()

    new_access_token = res_json.get("access_token")
    new_refresh_token = res_json.get("refresh_token")
    expires_in = res_json.get("expires_in")

    if not new_access_token:
        return {"error": "No new access token returned", "raw": res_json}

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "expires_in": expires_in
    }

# services/auth/twitter_auth.py

import os
import requests
from app.services.database.database import get_db
from app.services.models.token_model import PlatformToken

TWITTER_CLIENT_ID = os.getenv("TWITTER_CLIENT_ID")
TWITTER_CLIENT_SECRET = os.getenv("TWITTER_CLIENT_SECRET")
TWITTER_REDIRECT_URI = os.getenv("TWITTER_REDIRECT_URI")

AUTH_URL = (
    "https://twitter.com/i/oauth2/authorize"
    "?response_type=code"
    f"&client_id={TWITTER_CLIENT_ID}"
    f"&redirect_uri={TWITTER_REDIRECT_URI}"
    "&scope=tweet.read%20tweet.write%20users.read%20offline.access"
    "&state=state"
    "&code_challenge=challenge"
    "&code_challenge_method=plain"
)

TOKEN_URL = "https://api.twitter.com/2/oauth2/token"

def get_twitter_login_url() -> str:
    return AUTH_URL


def exchange_code(code: str, user_id: str) -> dict:
    """
    Exchange Twitter OAuth code for access & refresh token.
    """
    data = {
        "client_id": TWITTER_CLIENT_ID,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": TWITTER_REDIRECT_URI,
        "code_verifier": "challenge"
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {TWITTER_CLIENT_ID}:{TWITTER_CLIENT_SECRET}"
    }

    res = requests.post(TOKEN_URL, data=data, headers=headers)
    res_json = res.json()

    access_token = res_json.get("access_token")
    refresh_token = res_json.get("refresh_token")
    expires_in = res_json.get("expires_in")

    if not access_token:
        return {"error": "No access token returned", "raw": res_json}

    db = next(get_db())
    new_token = PlatformToken(
        user_id=user_id,
        platform="twitter",
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in
    )
    db.add(new_token)
    db.commit()

    return {
        "msg": "Twitter connected!",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": expires_in
    }


def refresh_twitter_token(refresh_token: str) -> dict:
    """
    Refresh Twitter access token using refresh_token.
    """
    data = {
        "client_id": TWITTER_CLIENT_ID,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {TWITTER_CLIENT_ID}:{TWITTER_CLIENT_SECRET}"
    }

    res = requests.post(TOKEN_URL, data=data, headers=headers)
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

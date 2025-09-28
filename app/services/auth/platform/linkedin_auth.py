# services/auth/linkedin_auth.py

import os
import requests
from app.services.database.database import get_db
from app.services.models.token_model import PlatformToken

LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
LINKEDIN_REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI")

AUTH_URL = (
    "https://www.linkedin.com/oauth/v2/authorization"
    "?response_type=code"
    f"&client_id={LINKEDIN_CLIENT_ID}"
    f"&redirect_uri={LINKEDIN_REDIRECT_URI}"
    "&scope=w_member_social%20r_liteprofile%20r_emailaddress%20rw_organization_admin"
)

TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"

def get_linkedin_login_url() -> str:
    return AUTH_URL


def exchange_code(code: str, user_id: str) -> dict:
    """
    Exchange authorization code for access + refresh token.
    Save token in DB.
    """
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": LINKEDIN_REDIRECT_URI,
        "client_id": LINKEDIN_CLIENT_ID,
        "client_secret": LINKEDIN_CLIENT_SECRET
    }

    res = requests.post(TOKEN_URL, data=data)
    res_json = res.json()

    access_token = res_json.get("access_token")
    expires_in = res_json.get("expires_in")

    if not access_token:
        return {"error": "No access token returned", "raw": res_json}

    # Save in DB
    db = next(get_db())
    new_token = PlatformToken(
        user_id=user_id,
        platform="linkedin",
        access_token=access_token,
        expires_in=expires_in
    )
    db.add(new_token)
    db.commit()

    return {"msg": "LinkedIn connected!", "access_token": access_token, "expires_in": expires_in}


def refresh_token(refresh_token: str) -> dict:
    """
    Refresh LinkedIn token using refresh_token.
    """
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": LINKEDIN_CLIENT_ID,
        "client_secret": LINKEDIN_CLIENT_SECRET
    }

    res = requests.post(TOKEN_URL, data=data)
    res_json = res.json()

    new_access_token = res_json.get("access_token")
    expires_in = res_json.get("expires_in")

    if not new_access_token:
        return {"error": "No new access token returned", "raw": res_json}

    return {
        "access_token": new_access_token,
        "expires_in": expires_in
    }

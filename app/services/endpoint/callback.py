# endpoints/callback.py

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional

from app.services.auth.platform.meta_auth import exchange_code as exchange_meta
from app.services.auth.platform.linkedin_auth import exchange_code as exchange_linkedin
from app.services.auth.platform.twitter_auth import exchange_code as exchange_twitter
from app.services.auth.platform.youtube_auth import exchange_code as exchange_youtube
from app.services.auth.platform.tiktok_auth import exchange_code as exchange_tiktok
from app.services.auth.platform.farcaster_auth import handle_farcaster_callback as exchange_farcaster
from app.services.auth.platform.telegram_auth import handle_telegram_callback as exchange_telegram

class PlatformAuthResponse(BaseModel):
    success: bool
    platform: str
    user_id: str
    token_info: Optional[Dict[str, Any]] = None
    message: Optional[str] = None

router = APIRouter(tags=["Platform Callback"])

# ✅ Meta Callback (Facebook/Instagram)
@router.get("/meta", response_model=PlatformAuthResponse, summary="Meta authentication callback", description="Handles the OAuth callback from Meta (Facebook/Instagram)")
async def callback_meta(
    code: str = Query(..., description="Authorization code from Meta"),
    user_id: str = Query(..., description="User ID for the authentication")
):
    """
    Meta (FB/IG) redirects here with ?code=&user_id=
    """
    try:
        result = exchange_meta(code, user_id)
        return PlatformAuthResponse(
            success=True,
            platform="meta",
            user_id=user_id,
            token_info=result
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ✅ LinkedIn Callback
@router.get("/linkedin", response_model=PlatformAuthResponse, summary="LinkedIn authentication callback", description="Handles the OAuth callback from LinkedIn")
async def callback_linkedin(
    code: str = Query(..., description="Authorization code from LinkedIn"),
    user_id: str = Query(..., description="User ID for the authentication")
):
    """
    LinkedIn redirects here with ?code=
    """
    try:
        result = exchange_linkedin(code, user_id)
        return PlatformAuthResponse(
            success=True,
            platform="linkedin",
            user_id=user_id,
            token_info=result
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ✅ Twitter Callback
@router.get("/twitter", response_model=PlatformAuthResponse, summary="Twitter authentication callback", description="Handles the OAuth callback from Twitter")
async def callback_twitter(
    code: str = Query(..., description="Authorization code from Twitter"),
    user_id: str = Query(..., description="User ID for the authentication")
):
    """
    Twitter redirects here with ?code=
    """
    try:
        result = exchange_twitter(code, user_id)
        return PlatformAuthResponse(
            success=True,
            platform="twitter",
            user_id=user_id,
            token_info=result
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
# ✅ YouTube Callback
@router.get("/youtube")
async def callback_youtube(
    code: str = Query(...),
    user_id: str = Query(...)
):
    """
    YouTube redirects here with ?code=
    """
    try:
        result = exchange_youtube(code, user_id)
        return JSONResponse(content={"success": True, "details": result})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
# ✅ TikTok Callback
@router.get("/tiktok")
async def callback_tiktok(
    code: str = Query(...),
    user_id: str = Query(...)
):
    """
    TikTok redirects here with ?code=
    """
    try:
        result = exchange_tiktok(code, user_id)
        return JSONResponse(content={"success": True, "details": result})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
# ✅ Farcaster Callback
@router.get("/farcaster")
async def callback_farcaster(
    signature: str = Query(...),
    address: str = Query(...),
    nonce: str = Query(...)
):
    try:
        result = exchange_farcaster(signature=signature, address=address, nonce=nonce)
        return JSONResponse(content={"success": True, "details": result})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ✅ Telegram does not redirect with ?code — uses hash verification
@router.post("/telegram")
async def callback_telegram(
    bot_token: str = Query(...),
    channel_id: str = Query(...)
):
    try:
        result = exchange_telegram(bot_token=bot_token, channel_id=channel_id)
        return JSONResponse(content={"success": True, "details": result})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

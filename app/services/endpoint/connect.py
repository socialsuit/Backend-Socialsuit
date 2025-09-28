from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import JSONResponse

from app.services.auth.platform.meta_auth import exchange_code as exchange_meta
from app.services.auth.platform.twitter_auth import exchange_code as exchange_twitter
from app.services.auth.platform.linkedin_auth import exchange_code as exchange_linkedin
from app.services.auth.platform.youtube_auth import exchange_code as exchange_youtube
from app.services.auth.platform.tiktok_auth import exchange_code as exchange_tiktok
from app.services.auth.platform.farcaster_auth import handle_farcaster_callback
from app.services.auth.platform.telegram_auth import handle_telegram_callback

router = APIRouter(prefix="/callback")

@router.get("/meta")
async def callback_meta(code: str = Query(...), user_id: str = Query(...)):
    return exchange_meta(code, user_id)

@router.get("/twitter")
async def callback_twitter(code: str = Query(...), user_id: str = Query(...)):
    return exchange_twitter(code, user_id)

@router.get("/linkedin")
async def callback_linkedin(code: str = Query(...), user_id: str = Query(...)):
    return exchange_linkedin(code, user_id)

@router.get("/youtube")
async def callback_youtube(code: str = Query(...), user_id: str = Query(...)):
    return exchange_youtube(code, user_id)

@router.get("/tiktok")
async def callback_tiktok(code: str = Query(...), user_id: str = Query(...)):
    return exchange_tiktok(code, user_id)

@router.get("/farcaster")
async def callback_farcaster(signature: str = Query(...), address: str = Query(...)):
    return handle_farcaster_callback(signature=signature, address=address)

@router.post("/telegram")
async def callback_telegram(bot_token: str = Query(...), channel_id: str = Query(...)):
    return handle_telegram_callback(bot_token=bot_token, channel_id=channel_id)
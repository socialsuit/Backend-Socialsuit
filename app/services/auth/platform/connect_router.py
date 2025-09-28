from fastapi import APIRouter, Request, HTTPException 
from fastapi.responses import RedirectResponse 
import os

router = APIRouter(prefix="/connect", tags=["Platform Connect"])

@router.get("/meta") 
def connect_meta(): 
    redirect_uri = os.getenv("META_REDIRECT_URI") 
    client_id = os.getenv("META_CLIENT_ID") 
    meta_auth_url = ( f"https://www.facebook.com/v19.0/dialog/oauth?client_id={client_id}" f"&redirect_uri={redirect_uri}&scope=pages_manage_posts,pages_read_engagement,pages_show_list,instagram_basic" ) 
    return RedirectResponse(meta_auth_url)

@router.get("/twitter") 
def connect_twitter(): 
    twitter_oauth_url = "https://twitter.com/i/oauth2/authorize"  # Replace with real logic 
    return RedirectResponse(twitter_oauth_url)

@router.get("/linkedin") 
def connect_linkedin(): 
    client_id = os.getenv("LINKEDIN_CLIENT_ID") 
    redirect_uri = os.getenv("LINKEDIN_REDIRECT_URI") 
    linkedin_auth_url = ( f"https://www.linkedin.com/oauth/v2/authorization?response_type=code" f"&client_id={client_id}&redirect_uri={redirect_uri}&scope=r_liteprofile%20r_emailaddress%20w_member_social" ) 
    return RedirectResponse(linkedin_auth_url)

@router.get("/youtube") 
def connect_youtube(): 
    client_id = os.getenv("YOUTUBE_CLIENT_ID") 
    redirect_uri = os.getenv("YOUTUBE_REDIRECT_URI") 
    youtube_auth_url = ( f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}" f"&redirect_uri={redirect_uri}&response_type=code&scope=https://www.googleapis.com/auth/youtube.upload" ) 
    return RedirectResponse(youtube_auth_url)

@router.get("/tiktok") 
def connect_tiktok(): 
    client_key = os.getenv("TIKTOK_CLIENT_KEY") 
    redirect_uri = os.getenv("TIKTOK_REDIRECT_URI") 
    tiktok_auth_url = ( f"https://www.tiktok.com/v2/auth/authorize/?client_key={client_key}" f"&response_type=code&scope=user.info.basic,video.list,video.upload&redirect_uri={redirect_uri}" ) 
    return RedirectResponse(tiktok_auth_url)

@router.get("/farcaster") 
def connect_farcaster(): 
    farcaster_url = "https://farcaster-auth.vercel.app/auth"  # Example URL 
    return RedirectResponse(farcaster_url)
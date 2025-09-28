# services/scheduler/platform_post.py

from app.services.platforms.facebook_post import call_facebook_post
from app.services.platforms.instagram_post import call_instagram_post
from app.services.platforms.twitter_post import call_twitter_post
from app.services.platforms.linkedin_post import call_linkedin_post
from app.services.platforms.youtube_post import call_youtube_post
from app.services.platforms.tiktok_post import call_tiktok_post
from app.services.platforms.telegram_post import call_telegram_api
from app.services.platforms.farcaster_post import call_farcaster_post

def post_to_platform(platform: str, user_token: dict, post_payload: dict):
    """
    Unified interface for posting to any supported platform.
    Returns a standardized response with success/error info and retry flag.
    
    Returns:
        dict: {
            "success": bool,
            "error": str (optional),
            "retry": bool (optional),
            "data": dict (optional platform-specific response data)
        }
    """
    platform = platform.lower()
    
    try:
        # Call the appropriate platform-specific function
        if platform == "facebook":
            result = call_facebook_post(user_token, post_payload)
        elif platform == "instagram":
            result = call_instagram_post(user_token, post_payload)
        elif platform == "twitter":
            result = call_twitter_post(user_token, post_payload)
        elif platform == "linkedin":
            result = call_linkedin_post(user_token, post_payload)
        elif platform == "youtube":
            result = call_youtube_post(user_token, post_payload)
        elif platform == "tiktok":
            result = call_tiktok_post(user_token, post_payload)
        elif platform == "telegram":
            result = call_telegram_api(user_token, post_payload)
        elif platform == "farcaster":
            result = call_farcaster_post(user_token, post_payload)
        else:
            return {
                "success": False,
                "error": f"Unsupported platform: {platform}",
                "retry": False
            }
        
        # Standardize the response format
        if "error" in result:
            return {
                "success": False,
                "error": result["error"],
                "retry": result.get("retry", True),  # Default to retry=True if not specified
                "data": result
            }
        else:
            return {
                "success": True,
                "data": result
            }
            
    except Exception as e:
        # Catch any unexpected exceptions from platform functions
        return {
            "success": False,
            "error": f"Unexpected error in post_to_platform: {str(e)}",
            "retry": True,
            "data": None
        }
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, Dict, Any, List
import pytz  # for timezone validation
from app.services.smart_schedule import smart_schedule
from pydantic import BaseModel

VALID_PLATFORMS = ["facebook", "instagram", "twitter", "linkedin"]

class ScheduleResponse(BaseModel):
    best_times: List[Dict[str, Any]]
    platform: str
    timezone: str

router = APIRouter(prefix="/schedule", tags=["Smart Scheduling"])

@router.get("/best-times", response_model=ScheduleResponse, summary="Get optimal posting times", description="Determines the best times to post content based on platform, content type, and audience location")
def get_schedule(
    platform: str = Query(..., min_length=1, description="Social media platform (facebook, instagram, twitter, linkedin)"),
    content_type: Optional[str] = Query("post", description="Type of content (post, video, story, etc.)"),
    timezone: Optional[str] = Query("UTC", description="Timezone for scheduling (e.g., UTC, America/New_York)"),
    audience_location: Optional[str] = Query(None, description="Primary audience location for better targeting")
):
    # Validate platform
    if platform.lower() not in VALID_PLATFORMS:
        raise HTTPException(status_code=400, detail="Invalid platform provided.")

    # Validate timezone
    if timezone not in pytz.all_timezones:
        raise HTTPException(status_code=400, detail="Invalid timezone provided.")

    try:
        result = smart_schedule(
            platform=platform,
            content_type=content_type,
            timezone=timezone,
            audience_location=audience_location
        )
        
        # Format response to match the response model
        return {
            "best_times": result.get("best_times", []),
            "platform": platform,
            "timezone": timezone
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


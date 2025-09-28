# endpoints/scheduled_post.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.services.database.database import get_db
from app.services.models.scheduled_post_model import ScheduledPost, PostStatus

class SchedulePostRequest(BaseModel):
    user_id: str = Field(..., description="User ID of the post owner")
    platform: str = Field(..., description="Social media platform to post to (facebook, instagram, twitter, etc.)")
    post_payload: Dict[str, Any] = Field(..., description="Content payload for the post")  # caption, image_url, etc.
    scheduled_time: datetime = Field(..., description="Datetime for when to publish the post")
    
class SchedulePostResponse(BaseModel):
    message: str
    post_id: str
    scheduled_time: datetime
    platform: str

router = APIRouter(prefix="/post", tags=["Post Scheduling"])

@router.post("/schedule", response_model=SchedulePostResponse, summary="Schedule a social media post", description="Creates a scheduled post for publishing at a specified time")
def schedule_post(data: SchedulePostRequest, db: Session = Depends(get_db)):
    try:
        post = ScheduledPost(
            user_id=data.user_id,
            platform=data.platform,
            post_payload=data.post_payload,
            scheduled_time=data.scheduled_time,
            status=PostStatus.pending
        )
        db.add(post)
        db.commit()
        db.refresh(post)
        
        return {
            "message": "Post scheduled successfully", 
            "post_id": str(post.id),
            "scheduled_time": post.scheduled_time,
            "platform": post.platform
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to schedule post: {str(e)}")

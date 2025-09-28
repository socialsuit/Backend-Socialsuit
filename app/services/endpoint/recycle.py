from fastapi import APIRouter, HTTPException
from app.services.post_recycler import RecyclePostRequest, recycle_post
from pydantic import BaseModel
from typing import Dict, Any, List

class RecycleResponse(BaseModel):
    success: bool
    recycled_post_ids: List[str]
    scheduled_times: Dict[str, str]

router = APIRouter(prefix="/recycle", tags=["Content Recycling"])

@router.post("/post", response_model=RecycleResponse, summary="Recycle existing post", description="Creates new versions of an existing post optimized for different platforms")
def recycle_endpoint(request: RecyclePostRequest):
    try:
        result = recycle_post(
            request.post_id,
            request.platforms,
            request.schedule_time,
            request.optimization_params,
            request.creator_id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to recycle post: {str(e)}")



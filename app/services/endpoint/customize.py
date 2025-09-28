from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services.post_customizer import customize
from typing import Dict, Any

class CustomizeRequest(BaseModel):
    content: str = Field(..., description="Original content to be customized")
    platform: str = Field(..., description="Target platform for customization (facebook, instagram, twitter, etc.)")

class CustomizeResponse(BaseModel):
    customized_content: str
    platform_specific_data: Dict[str, Any]

router = APIRouter(prefix="/customize", tags=["Content Customization"])

@router.post("/platform", response_model=CustomizeResponse, summary="Customize content for platform", description="Adapts content to be optimized for a specific social media platform")
def customize_post(req: CustomizeRequest):
    try:
        result = customize(req.content, req.platform)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to customize content: {str(e)}")

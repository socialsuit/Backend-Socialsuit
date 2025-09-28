from fastapi import APIRouter, Form
from pydantic import BaseModel
from typing import Optional
from app.services.thumbnail import SDXLThumbnailGenerator

router = APIRouter()
generator = SDXLThumbnailGenerator()

class ThumbnailRequest(BaseModel):
    prompt: str
    platform: str = "universal"
    logo_base64: Optional[str] = None

@router.post("/generate-thumbnail")
async def generate_image(req: ThumbnailRequest):
    result = generator.generate_thumbnail(
        prompt=req.prompt,
        platform=req.platform,
        logo_base64=req.logo_base64
    )
    return result
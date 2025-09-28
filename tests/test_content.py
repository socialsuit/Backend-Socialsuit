import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import APIRouter
from app.services.ai_client import ai_client

router = APIRouter()

@router.get("/generate")
def gen(prompt: str):
    # Test AI client initialization
    assert ai_client is not None
    caption = ai_client.generate_caption(topic=prompt, style="casual", hashtag_count=3)
    return {"caption": caption}  # ✅ wrap the result in a JSON-friendly format
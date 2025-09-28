from fastapi import APIRouter, Body, Depends
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from app.services.auto_engagement import auto_engage
from app.services.auth.auth_guard import auth_required
from app.services.models.user_model import User

class EngagementRequest(BaseModel):
    """Request model for auto-engagement processing.
    
    Contains the message to be processed and optional context information.
    """
    message: str = Field(..., description="The message to process for auto-engagement")
    platform: Optional[str] = Field(None, description="The platform where the message originated")
    context: Optional[Dict[str, Any]] = Field({}, description="Additional context for processing")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "What are the pricing options for Social Suit?",
                "platform": "twitter",
                "context": {
                    "user_tier": "premium",
                    "previous_interactions": 3
                }
            }
        }

class EngagementResponse(BaseModel):
    """Response model for auto-engagement processing.
    
    Contains the generated reply and metadata about the engagement.
    """
    reply: str = Field(..., description="The auto-generated reply message")
    intent: str = Field(..., description="The detected intent of the original message")
    sentiment: str = Field(..., description="The detected sentiment of the original message")
    confidence: float = Field(..., description="Confidence score of the intent detection")
    suggested_actions: Optional[List[str]] = Field([], description="Suggested follow-up actions")
    
    class Config:
        json_schema_extra = {
            "example": {
                "reply": "Thanks for your interest in Social Suit! Our Premium plan starts at $29/month and includes all core features plus advanced analytics. Would you like me to send you our full pricing guide?",
                "intent": "pricing",
                "sentiment": "neutral",
                "confidence": 0.92,
                "suggested_actions": ["send_pricing_pdf", "offer_demo"]
            }
        }

# Create router with appropriate tag and description
router = APIRouter(
    prefix="/engage",
    tags=["Engagement"]
)

@router.post(
    "/reply",
    response_model=EngagementResponse,
    summary="Generate Auto-Reply",
    description="Processes a message and generates an appropriate automated response based on intent detection",
    response_description="Returns the generated reply and engagement metadata"
)
async def reply(
    engagement_data: EngagementRequest = Body(
        ...,
        description="The message and context for auto-engagement processing"
    ),
    current_user: User = Depends(auth_required)
):
    """Generate an automated reply to a message.
    
    This endpoint processes an incoming message, detects its intent and sentiment,
    and generates an appropriate response. The response is personalized based on
    the user's tier and platform context.
    
    Args:
        engagement_data: The message and context information
        current_user: The authenticated user (injected by dependency)
        
    Returns:
        A JSON object with the generated reply and engagement metadata
    """
    # Process the message using the auto_engage service
    result = auto_engage(
        message=engagement_data.message,
        platform=engagement_data.platform,
        context=engagement_data.context,
        user_id=str(current_user.id)
    )
    
    return result

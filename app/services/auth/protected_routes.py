from fastapi import APIRouter, Depends, HTTPException
from app.services.auth.auth_guard import auth_required
from typing import Any, Dict, Optional
from pydantic import BaseModel

class UserProfileResponse(BaseModel):
    id: str
    email: Optional[str] = None
    wallet: Optional[str] = None
    network: Optional[str] = None
    verified: bool = False

router = APIRouter(prefix="/secure", tags=["Protected"])

@router.get("/me", response_model=UserProfileResponse, summary="Get user profile", description="Returns the authenticated user's profile information")
def get_profile(current_user: Any = Depends(auth_required)):
    try:
        from app.services.models.user_model import User  # ✅ local import to break circular dependency

        return {
            "id": str(current_user.id),
            "email": current_user.email,
            "wallet": current_user.wallet_address,
            "network": current_user.network,
            "verified": current_user.is_verified
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user profile: {str(e)}")

"""Response wrapper utilities for API endpoints."""

from functools import wraps
from typing import Any, Dict, Optional
from fastapi import HTTPException
from .response_envelope import ResponseEnvelope

def envelope_response(func):
    """Decorator to wrap responses in ResponseEnvelope."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            result = await func(*args, **kwargs)
            return ResponseEnvelope(success=True, data=result)
        except HTTPException as e:
            return ResponseEnvelope(
                success=False,
                message=e.detail,
                errors={"status_code": e.status_code}
            )
        except Exception as e:
            return ResponseEnvelope(
                success=False,
                message="Internal server error",
                errors={"error": str(e)}
            )
    return wrapper

def create_error_response(message: str, errors: Optional[Dict[str, Any]] = None) -> ResponseEnvelope:
    """Create an error response envelope."""
    return ResponseEnvelope(
        success=False,
        message=message,
        errors=errors or {}
    )
"""Response envelope utilities for consistent API responses."""

from typing import Generic, TypeVar, Optional, Any, Dict
from pydantic import BaseModel

T = TypeVar('T')

class ResponseEnvelope(BaseModel, Generic[T]):
    """Generic response envelope for API responses."""
    success: bool = True
    data: Optional[T] = None
    message: Optional[str] = None
    errors: Optional[Dict[str, Any]] = None
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True
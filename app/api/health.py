from fastapi import APIRouter, FastAPI
import os
import platform
import time

router = APIRouter()

@router.get("/healthz")
def health_check():
    """Basic health check endpoint that returns service status."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "social-suit-api",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "system": platform.system()
    }

@router.get("/ping")
def ping():
    """Simple ping endpoint for basic connectivity testing."""
    return {"ping": "pong"}

def add_health_routes(app: FastAPI):
    """Add health check routes to the FastAPI application."""
    app.include_router(router, tags=["health"])
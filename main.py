import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import security components
from app.services.security.rate_limiter import RateLimiter, RateLimitConfig
from app.services.security.security_middleware import SecurityMiddleware
from app.services.security.security_config import (
    get_security_settings,
    RATE_LIMIT_CONFIG,
    get_security_middleware_config
)

# Auth routers
from app.services.auth.platform.connect_router import router as connect_router
from app.services.auth.wallet.auth_router import router as wallet_auth_router
from app.services.auth.email.auth_router import router as email_auth_router
from app.services.auth.protected_routes import router as protected_router

# Endpoint routers - using secure versions where available
from app.services.endpoint.recycle import router as recycle_router
from app.services.endpoint.analytics import router as analytics_router
from app.services.endpoint.secure_analytics_api import router as analytics_api_router
from app.services.endpoint.secure_scheduled_post_api import router as scheduled_post_router
from app.services.endpoint.schedule import router as schedule_router
from app.services.endpoint.thumbnail import router as thumbnail_router
from app.services.endpoint.content import router as content_router
from app.services.endpoint.ab_test import router as ab_test_router
from app.services.endpoint.engage import router as engage_router
from app.services.endpoint.customize import router as customize_router
from app.services.endpoint.media import router as media_router
from app.services.endpoint import connect, callback, schedule

# Health routes
from app.api.health import add_health_routes
from app.services.database.database import Base, engine
from app.services.database.postgresql import init_db_pool, get_db_connection
from app.services.database.mongodb import MongoDBManager
from app.services.database.redis import RedisManager
from middleware.sanitization_middleware import SanitizationMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Social Suit API",
    description="A comprehensive social media management platform",
    version="1.0.0",
    docs_url="/docs" if not get_security_settings().cors_allow_origins else None,  # Disable docs in production
    redoc_url="/redoc" if not get_security_settings().cors_allow_origins else None
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok"}

# -------------------------------
# 🔌 Connect to External Services
# -------------------------------
@app.on_event("startup")
async def connect_services():
    """Connect to external services on startup."""
    try:
        # Initialize database connection pool
        print("🔄 Initializing database connection...")
        # await init_db_pool()  # Commented out for now - no local PostgreSQL
        print("✅ Database connection skipped (development mode)")
        
        # Initialize Redis connection
        print("🔄 Initializing Redis connection...")
        # await init_redis()  # Commented out for now - no local Redis
        print("✅ Redis connection skipped (development mode)")
        
        print("🚀 All services initialized successfully!")
    except Exception as e:
        print(f"❌ Failed to initialize services: {e}")
        # Don't raise the exception to allow the app to start without external services

# Initialize security components
async def initialize_security():
    """Initialize security components."""
    try:
        # Initialize Redis for rate limiting
        await RedisManager.initialize()
        logger.info("Redis initialized for security features")
        
        # Create rate limiter
        rate_limit_config = RateLimitConfig(**RATE_LIMIT_CONFIG)
        rate_limiter = RateLimiter(rate_limit_config)
        
        # Add comprehensive security middleware
        security_config = get_security_middleware_config()
        app.add_middleware(
            SecurityMiddleware,
            rate_limiter=rate_limiter,
            **security_config
        )
        
        # Add sanitization middleware
        app.add_middleware(
            SanitizationMiddleware,
            exclude_paths=["/docs", "/redoc", "/openapi.json"]
        )
        
        logger.info("Security middleware initialized")
        
    except Exception as e:
        logger.error(f"Failed to initialize security components: {e}")
        # Continue without security features in development
        logger.warning("Running without enhanced security features")

# -------------------------------
# ❌ Disconnect All Services
# -------------------------------
@app.on_event("shutdown")
async def shutdown_services():
    from app.services.database.postgresql import close_db_pool
    await close_db_pool()
    print("🔌 PostgreSQL Connection Closed")

    await MongoDBManager.close_connection()
    print("🔌 MongoDB Connection Closed")

    await RedisManager.close()
    print("🔌 Redis Connection Closed")

# -------------------------------
# Database Table Initialization
# -------------------------------


# -------------------------------
# Enable CORS for Frontend
# -------------------------------
# Add CORS middleware (after security middleware)
security_config = get_security_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=security_config.cors_allow_origins,
    allow_credentials=security_config.cors_allow_credentials,
    allow_methods=security_config.cors_allow_methods,
    allow_headers=security_config.cors_allow_headers,
)

# -------------------------------
# Include Routers
# -------------------------------
# Social Suit API v1 Endpoint Routers
app.include_router(content_router, prefix="/api/v1/social-suit")
app.include_router(schedule_router, prefix="/api/v1/social-suit")
app.include_router(scheduled_post_router, prefix="/api/v1/social-suit")
app.include_router(analytics_router, prefix="/api/v1/social-suit")
app.include_router(analytics_api_router, prefix="/api/v1/social-suit")
app.include_router(recycle_router, prefix="/api/v1/social-suit")
app.include_router(ab_test_router, prefix="/api/v1/social-suit")
app.include_router(thumbnail_router, prefix="/api/v1/social-suit")
app.include_router(engage_router, prefix="/api/v1/social-suit")
app.include_router(customize_router, prefix="/api/v1/social-suit")
app.include_router(media_router, prefix="/api/v1/social-suit")
app.include_router(connect.router, prefix="/api/v1/social-suit")
app.include_router(callback.router, prefix="/api/v1/social-suit")

# Social Suit Auth routes
app.include_router(wallet_auth_router, prefix="/api/v1/social-suit")
app.include_router(email_auth_router, prefix="/api/v1/social-suit")
app.include_router(protected_router, prefix="/api/v1/social-suit/auth")
app.include_router(connect_router, prefix="/api/v1/social-suit")

# Social Suit API v1 Endpoint Routers (continued)

# Add health routes
add_health_routes(app)

# -------------------------------
# Root Endpoint
# -------------------------------
@app.get("/")
def home():
    return {
        "msg": "🚀 Social Suit API",
        "version": "2.0.0",
        "services": [
            {
                "name": "social-suit",
                "prefix": "/api/v1/social-suit",
                "docs": "/docs"
            }
        ],
        "health_check": "/health"
    }

# -------------------------------
# Health Check Endpoint
# -------------------------------
@app.get("/health")
def health_check():
    return {"status": "ok"}
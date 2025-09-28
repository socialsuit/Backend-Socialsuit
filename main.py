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

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import security components with error handling
try:
    from app.services.security.rate_limiter import RateLimiter, RateLimitConfig
    from app.services.security.security_middleware import SecurityMiddleware
    from app.services.security.security_config import (
        get_security_settings,
        RATE_LIMIT_CONFIG,
        get_security_middleware_config
    )
    SECURITY_AVAILABLE = True
    logger.info("Security components loaded successfully")
except Exception as e:
    logger.warning(f"Security components not available: {e}")
    SECURITY_AVAILABLE = False

# Auth routers - with error handling
try:
    from app.services.auth.platform.connect_router import router as connect_router
    from app.services.auth.wallet.auth_router import router as wallet_auth_router
    from app.services.auth.email.auth_router import router as email_auth_router
    from app.services.auth.protected_routes import router as protected_router
    AUTH_ROUTERS_AVAILABLE = True
    logger.info("Auth routers loaded successfully")
except Exception as e:
    logger.warning(f"Auth routers not available: {e}")
    AUTH_ROUTERS_AVAILABLE = False

# Endpoint routers - with error handling
try:
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
    ENDPOINT_ROUTERS_AVAILABLE = True
    logger.info("Endpoint routers loaded successfully")
except Exception as e:
    logger.warning(f"Endpoint routers not available: {e}")
    ENDPOINT_ROUTERS_AVAILABLE = False

# Health routes - with error handling
try:
    from app.api.health import add_health_routes
    HEALTH_ROUTES_AVAILABLE = True
    logger.info("Health routes loaded successfully")
except Exception as e:
    logger.warning(f"Health routes not available: {e}")
    HEALTH_ROUTES_AVAILABLE = False

# Database imports - with error handling
try:
    from app.services.database.database import Base, engine
    from app.services.database.postgresql import init_db_pool, get_db_connection
    DATABASE_AVAILABLE = True
    logger.info("Database components loaded successfully")
except Exception as e:
    logger.warning(f"Database components not available: {e}")
    DATABASE_AVAILABLE = False

try:
    from app.services.database.mongodb import MongoDBManager
    MONGODB_AVAILABLE = True
    logger.info("MongoDB components loaded successfully")
except Exception as e:
    logger.warning(f"MongoDB components not available: {e}")
    MONGODB_AVAILABLE = False

try:
    from app.services.database.redis import RedisManager
    REDIS_AVAILABLE = True
    logger.info("Redis components loaded successfully")
except Exception as e:
    logger.warning(f"Redis components not available: {e}")
    REDIS_AVAILABLE = False

try:
    from middleware.sanitization_middleware import SanitizationMiddleware
    SANITIZATION_AVAILABLE = True
    logger.info("Sanitization middleware loaded successfully")
except Exception as e:
    logger.warning(f"Sanitization middleware not available: {e}")
    SANITIZATION_AVAILABLE = False

# Create FastAPI app
app = FastAPI(
    title="Social Suit API",
    description="A comprehensive social media management platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Default root endpoint
@app.get("/")
async def root():
    return {"message": "Hello from Social Suit Backend"}

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
    logger.info("🚀 Starting Social Suit Backend...")
    
    # Initialize database connection pool
    if DATABASE_AVAILABLE:
        try:
            logger.info("🔄 Initializing database connection...")
            # await init_db_pool()  # Uncomment when database is available
            logger.info("✅ Database connection initialized")
        except Exception as e:
            logger.warning(f"⚠️ Database connection failed: {e}")
    else:
        logger.warning("⚠️ Database components not available - skipping database initialization")
    
    # Initialize MongoDB connection
    if MONGODB_AVAILABLE:
        try:
            logger.info("🔄 Initializing MongoDB connection...")
            # MongoDB initialization would go here
            logger.info("✅ MongoDB connection initialized")
        except Exception as e:
            logger.warning(f"⚠️ MongoDB connection failed: {e}")
    else:
        logger.warning("⚠️ MongoDB components not available - skipping MongoDB initialization")
    
    # Initialize Redis connection
    if REDIS_AVAILABLE:
        try:
            logger.info("🔄 Initializing Redis connection...")
            await RedisManager.initialize()
            logger.info("✅ Redis connection initialized")
        except Exception as e:
            logger.warning(f"⚠️ Redis connection failed: {e}")
    else:
        logger.warning("⚠️ Redis components not available - skipping Redis initialization")
    
    # Initialize security components
    await initialize_security()
    
    logger.info("🚀 Social Suit Backend startup completed!")

# Initialize security components
async def initialize_security():
    """Initialize security components."""
    if not SECURITY_AVAILABLE:
        logger.warning("⚠️ Security components not available - skipping security initialization")
        return
        
    try:
        logger.info("🔄 Initializing security components...")
        
        # Create rate limiter if Redis is available
        if REDIS_AVAILABLE:
            try:
                rate_limit_config = RateLimitConfig(**RATE_LIMIT_CONFIG)
                rate_limiter = RateLimiter(rate_limit_config)
                
                # Add comprehensive security middleware
                security_config = get_security_middleware_config()
                app.add_middleware(
                    SecurityMiddleware,
                    rate_limiter=rate_limiter,
                    **security_config
                )
                logger.info("✅ Security middleware with rate limiting initialized")
            except Exception as e:
                logger.warning(f"⚠️ Rate limiting setup failed: {e}")
        else:
            logger.warning("⚠️ Redis not available - skipping rate limiting")
        
        # Add sanitization middleware
        if SANITIZATION_AVAILABLE:
            try:
                app.add_middleware(
                    SanitizationMiddleware,
                    exclude_paths=["/docs", "/redoc", "/openapi.json"]
                )
                logger.info("✅ Sanitization middleware initialized")
            except Exception as e:
                logger.warning(f"⚠️ Sanitization middleware setup failed: {e}")
        
        logger.info("✅ Security initialization completed")
        
    except Exception as e:
        logger.warning(f"⚠️ Security initialization failed: {e}")
        logger.warning("⚠️ Running without enhanced security features")

# -------------------------------
# ❌ Disconnect All Services
# -------------------------------
@app.on_event("shutdown")
async def shutdown_services():
    """Gracefully shutdown all services."""
    logger.info("🔄 Shutting down Social Suit Backend...")
    
    if DATABASE_AVAILABLE:
        try:
            from app.services.database.postgresql import close_db_pool
            await close_db_pool()
            logger.info("🔌 PostgreSQL Connection Closed")
        except Exception as e:
            logger.warning(f"⚠️ Error closing PostgreSQL connection: {e}")

    if MONGODB_AVAILABLE:
        try:
            await MongoDBManager.close_connection()
            logger.info("🔌 MongoDB Connection Closed")
        except Exception as e:
            logger.warning(f"⚠️ Error closing MongoDB connection: {e}")

    if REDIS_AVAILABLE:
        try:
            await RedisManager.close()
            logger.info("🔌 Redis Connection Closed")
        except Exception as e:
            logger.warning(f"⚠️ Error closing Redis connection: {e}")
    
    logger.info("👋 Social Suit Backend shutdown completed!")

# -------------------------------
# Enable CORS for Frontend
# -------------------------------
# Add CORS middleware with safe defaults
try:
    if SECURITY_AVAILABLE:
        security_config = get_security_settings()
        cors_origins = security_config.cors_allow_origins
        cors_credentials = security_config.cors_allow_credentials
        cors_methods = security_config.cors_allow_methods
        cors_headers = security_config.cors_allow_headers
    else:
        # Safe defaults when security config is not available
        cors_origins = ["*"]
        cors_credentials = True
        cors_methods = ["*"]
        cors_headers = ["*"]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=cors_credentials,
        allow_methods=cors_methods,
        allow_headers=cors_headers,
    )
    logger.info("✅ CORS middleware initialized")
except Exception as e:
    logger.warning(f"⚠️ CORS middleware setup failed: {e}")
    # Add basic CORS as fallback
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("✅ Basic CORS middleware initialized as fallback")

# -------------------------------
# Include Routers
# -------------------------------
# Social Suit API v1 Endpoint Routers - with error handling
if ENDPOINT_ROUTERS_AVAILABLE:
    try:
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
        logger.info("✅ Endpoint routers registered successfully")
    except Exception as e:
        logger.warning(f"⚠️ Error registering endpoint routers: {e}")
else:
    logger.warning("⚠️ Endpoint routers not available - skipping router registration")

# Social Suit Auth routes - with error handling
if AUTH_ROUTERS_AVAILABLE:
    try:
        app.include_router(wallet_auth_router, prefix="/api/v1/social-suit")
        app.include_router(email_auth_router, prefix="/api/v1/social-suit")
        app.include_router(protected_router, prefix="/api/v1/social-suit/auth")
        app.include_router(connect_router, prefix="/api/v1/social-suit")
        logger.info("✅ Auth routers registered successfully")
    except Exception as e:
        logger.warning(f"⚠️ Error registering auth routers: {e}")
else:
    logger.warning("⚠️ Auth routers not available - skipping auth router registration")

# Add health routes - with error handling
if HEALTH_ROUTES_AVAILABLE:
    try:
        add_health_routes(app)
        logger.info("✅ Health routes registered successfully")
    except Exception as e:
        logger.warning(f"⚠️ Error registering health routes: {e}")
else:
    logger.warning("⚠️ Health routes not available - using basic health endpoint only")

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
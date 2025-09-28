"""
Rate Limiting Middleware for FastAPI

This module provides comprehensive rate limiting functionality using Redis as the backend.
It supports different rate limiting strategies including IP-based, user-based, and endpoint-specific limits.
"""

import time
import json
import hashlib
from typing import Dict, Optional, Tuple, Callable, Any
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.services.database.redis import RedisManager
from app.services.utils.logger_config import setup_logger
import asyncio

logger = setup_logger("rate_limiter")

class RateLimitExceeded(HTTPException):
    """Custom exception for rate limit exceeded."""
    def __init__(self, detail: str, retry_after: int):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers={"Retry-After": str(retry_after)}
        )

class RateLimitConfig:
    """Configuration for rate limiting rules."""
    
    def __init__(self):
        # Default rate limits (requests per time window)
        self.default_limits = {
            "global": {"requests": 1000, "window": 3600},  # 1000 requests per hour
            "per_ip": {"requests": 100, "window": 3600},   # 100 requests per hour per IP
            "per_user": {"requests": 500, "window": 3600}, # 500 requests per hour per user
        }
        
        # Endpoint-specific rate limits
        self.endpoint_limits = {
            # Authentication endpoints - stricter limits
            "/auth/login": {"requests": 5, "window": 300},     # 5 attempts per 5 minutes
            "/auth/register": {"requests": 3, "window": 300},   # 3 attempts per 5 minutes
            "/auth/refresh": {"requests": 10, "window": 300},   # 10 refreshes per 5 minutes
            
            # Analytics endpoints - moderate limits
            "/api/v1/analytics/collect": {"requests": 20, "window": 3600},  # 20 collections per hour
            "/api/v1/analytics/overview": {"requests": 100, "window": 3600}, # 100 overviews per hour
            
            # Content creation endpoints - moderate limits
            "/api/v1/schedule": {"requests": 50, "window": 3600},    # 50 posts per hour
            "/api/v1/content": {"requests": 100, "window": 3600},    # 100 content requests per hour
            
            # A/B testing endpoints - stricter limits
            "/api/v1/ab-testing/create": {"requests": 10, "window": 3600},  # 10 tests per hour
            
            # File upload endpoints - stricter limits
            "/api/v1/generate-thumbnail": {"requests": 20, "window": 3600}, # 20 thumbnails per hour
        }
        
        # Burst limits (short-term limits)
        self.burst_limits = {
            "per_ip": {"requests": 20, "window": 60},    # 20 requests per minute per IP
            "per_user": {"requests": 30, "window": 60},  # 30 requests per minute per user
        }
        
        # Whitelist for IPs that bypass rate limiting
        self.whitelist_ips = {
            "127.0.0.1",  # localhost
            "::1",        # localhost IPv6
        }
        
        # Paths that bypass rate limiting
        self.whitelist_paths = {
            "/",
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
        }

class RateLimiter:
    """Redis-based rate limiter with sliding window algorithm."""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.redis_manager = None
    
    async def initialize(self):
        """Initialize Redis connection."""
        if not self.redis_manager:
            self.redis_manager = RedisManager
            await self.redis_manager.initialize()
    
    def _get_client_identifier(self, request: Request) -> Tuple[str, Optional[str]]:
        """Extract client IP and user ID from request."""
        # Get real IP address (considering proxies)
        client_ip = request.headers.get("X-Forwarded-For")
        if client_ip:
            client_ip = client_ip.split(",")[0].strip()
        else:
            client_ip = request.headers.get("X-Real-IP") or request.client.host
        
        # Extract user ID from JWT token if available
        user_id = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from app.services.auth.jwt_handler import decode_token
                token = auth_header.split(" ")[1]
                payload = decode_token(token)
                user_id = payload.get("sub")
            except Exception:
                pass  # Invalid token, continue without user ID
        
        return client_ip, user_id
    
    def _generate_key(self, identifier: str, limit_type: str, endpoint: str = None) -> str:
        """Generate Redis key for rate limiting."""
        if endpoint:
            # Hash endpoint to avoid key length issues
            endpoint_hash = hashlib.md5(endpoint.encode()).hexdigest()[:8]
            return f"rate_limit:{limit_type}:{identifier}:{endpoint_hash}"
        return f"rate_limit:{limit_type}:{identifier}"
    
    async def _check_limit(self, key: str, limit: int, window: int) -> Tuple[bool, int, int]:
        """
        Check if request is within rate limit using sliding window.
        
        Returns:
            (is_allowed, current_count, retry_after_seconds)
        """
        try:
            async with self.redis_manager.get_connection() as redis:
                current_time = int(time.time())
                window_start = current_time - window
                
                # Use Redis pipeline for atomic operations
                pipe = redis.pipeline()
                
                # Remove expired entries
                pipe.zremrangebyscore(key, 0, window_start)
                
                # Count current requests in window
                pipe.zcard(key)
                
                # Add current request
                pipe.zadd(key, {str(current_time): current_time})
                
                # Set expiration
                pipe.expire(key, window + 10)  # Add buffer for cleanup
                
                results = await pipe.execute()
                current_count = results[1]
                
                if current_count >= limit:
                    # Calculate retry after time
                    oldest_request = await redis.zrange(key, 0, 0, withscores=True)
                    if oldest_request:
                        oldest_time = int(oldest_request[0][1])
                        retry_after = window - (current_time - oldest_time)
                        return False, current_count, max(retry_after, 1)
                    return False, current_count, window
                
                return True, current_count + 1, 0
                
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            # Fail open - allow request if Redis is down
            return True, 0, 0
    
    async def check_rate_limit(self, request: Request) -> Optional[RateLimitExceeded]:
        """
        Check if request should be rate limited.
        
        Returns:
            RateLimitExceeded exception if rate limit exceeded, None otherwise
        """
        if not self.redis_manager:
            await self.initialize()
        
        path = request.url.path
        method = request.method
        
        # Skip rate limiting for whitelisted paths
        if path in self.config.whitelist_paths:
            return None
        
        client_ip, user_id = self._get_client_identifier(request)
        
        # Skip rate limiting for whitelisted IPs
        if client_ip in self.config.whitelist_ips:
            return None
        
        # Check endpoint-specific limits first
        endpoint_key = f"{method} {path}"
        if path in self.config.endpoint_limits:
            limit_config = self.config.endpoint_limits[path]
            key = self._generate_key(client_ip, "endpoint", path)
            
            is_allowed, count, retry_after = await self._check_limit(
                key, limit_config["requests"], limit_config["window"]
            )
            
            if not is_allowed:
                logger.warning(f"Endpoint rate limit exceeded for {client_ip} on {path}: {count} requests")
                return RateLimitExceeded(
                    detail=f"Rate limit exceeded for endpoint {path}. Try again in {retry_after} seconds.",
                    retry_after=retry_after
                )
        
        # Check burst limits
        if client_ip:
            burst_config = self.config.burst_limits["per_ip"]
            key = self._generate_key(client_ip, "burst_ip")
            
            is_allowed, count, retry_after = await self._check_limit(
                key, burst_config["requests"], burst_config["window"]
            )
            
            if not is_allowed:
                logger.warning(f"Burst rate limit exceeded for IP {client_ip}: {count} requests")
                return RateLimitExceeded(
                    detail=f"Too many requests. Try again in {retry_after} seconds.",
                    retry_after=retry_after
                )
        
        # Check per-IP limits
        if client_ip:
            ip_config = self.config.default_limits["per_ip"]
            key = self._generate_key(client_ip, "ip")
            
            is_allowed, count, retry_after = await self._check_limit(
                key, ip_config["requests"], ip_config["window"]
            )
            
            if not is_allowed:
                logger.warning(f"IP rate limit exceeded for {client_ip}: {count} requests")
                return RateLimitExceeded(
                    detail=f"Rate limit exceeded for your IP address. Try again in {retry_after} seconds.",
                    retry_after=retry_after
                )
        
        # Check per-user limits (if authenticated)
        if user_id:
            user_config = self.config.default_limits["per_user"]
            key = self._generate_key(user_id, "user")
            
            is_allowed, count, retry_after = await self._check_limit(
                key, user_config["requests"], user_config["window"]
            )
            
            if not is_allowed:
                logger.warning(f"User rate limit exceeded for user {user_id}: {count} requests")
                return RateLimitExceeded(
                    detail=f"Rate limit exceeded for your account. Try again in {retry_after} seconds.",
                    retry_after=retry_after
                )
            
            # Check user burst limits
            burst_config = self.config.burst_limits["per_user"]
            key = self._generate_key(user_id, "burst_user")
            
            is_allowed, count, retry_after = await self._check_limit(
                key, burst_config["requests"], burst_config["window"]
            )
            
            if not is_allowed:
                logger.warning(f"User burst rate limit exceeded for user {user_id}: {count} requests")
                return RateLimitExceeded(
                    detail=f"Too many requests. Try again in {retry_after} seconds.",
                    retry_after=retry_after
                )
        
        return None

class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""
    
    def __init__(self, app, config: RateLimitConfig = None):
        super().__init__(app)
        self.rate_limiter = RateLimiter(config or RateLimitConfig())
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through rate limiter."""
        try:
            # Check rate limit
            rate_limit_error = await self.rate_limiter.check_rate_limit(request)
            
            if rate_limit_error:
                return JSONResponse(
                    status_code=rate_limit_error.status_code,
                    content={"detail": rate_limit_error.detail},
                    headers=rate_limit_error.headers
                )
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers to response
            client_ip, user_id = self.rate_limiter._get_client_identifier(request)
            
            # Add informational headers
            response.headers["X-RateLimit-Policy"] = "sliding-window"
            if client_ip:
                response.headers["X-Client-IP"] = client_ip
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limit middleware error: {e}")
            # Continue processing if rate limiter fails
            return await call_next(request)

# Utility functions for manual rate limiting
async def check_rate_limit_manual(
    identifier: str, 
    limit: int, 
    window: int, 
    limit_type: str = "manual"
) -> bool:
    """
    Manual rate limit check for use in endpoints.
    
    Args:
        identifier: Unique identifier (IP, user ID, etc.)
        limit: Number of requests allowed
        window: Time window in seconds
        limit_type: Type of limit for key generation
    
    Returns:
        True if within limit, False if exceeded
    """
    rate_limiter = RateLimiter(RateLimitConfig())
    await rate_limiter.initialize()
    
    key = rate_limiter._generate_key(identifier, limit_type)
    is_allowed, _, _ = await rate_limiter._check_limit(key, limit, window)
    
    return is_allowed

async def get_rate_limit_status(identifier: str, limit_type: str = "manual") -> Dict[str, Any]:
    """
    Get current rate limit status for an identifier.
    
    Returns:
        Dictionary with current count and limit information
    """
    try:
        rate_limiter = RateLimiter(RateLimitConfig())
        await rate_limiter.initialize()
        
        key = rate_limiter._generate_key(identifier, limit_type)
        
        async with rate_limiter.redis_manager.get_connection() as redis:
            current_count = await redis.zcard(key)
            ttl = await redis.ttl(key)
            
            return {
                "current_count": current_count,
                "ttl_seconds": ttl,
                "identifier": identifier,
                "limit_type": limit_type
            }
    except Exception as e:
        logger.error(f"Error getting rate limit status: {e}")
        return {"error": str(e)}
"""
Comprehensive Security Middleware for Social Suit Application

This module provides a unified security middleware that combines:
- Rate limiting
- Security headers
- Input validation
- IP filtering
- Content Security Policy
- Audit logging
"""

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
import logging
import json
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
import ipaddress

from .rate_limiter import RateLimiter, RateLimitConfig
from .security_config import (
    get_security_settings,
    get_security_middleware_config,
    get_validation_rules,
    get_audit_config,
    is_whitelisted_ip,
    is_blacklisted_ip,
    validate_file_upload
)

logger = logging.getLogger(__name__)

class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware."""
    
    def __init__(
        self,
        app: ASGIApp,
        rate_limiter: Optional[RateLimiter] = None,
        enable_rate_limiting: bool = True,
        enable_security_headers: bool = True,
        enable_input_validation: bool = True,
        enable_ip_filtering: bool = True,
        enable_audit_logging: bool = True
    ):
        super().__init__(app)
        self.rate_limiter = rate_limiter
        
        # Get security settings
        settings = get_security_settings()
        validation_rules = get_validation_rules()
        audit_config = get_audit_config()
        
        self.enable_rate_limiting = enable_rate_limiting and settings.rate_limit_enabled
        self.enable_security_headers = enable_security_headers and settings.security_headers_enabled
        self.enable_input_validation = enable_input_validation
        self.enable_ip_filtering = enable_ip_filtering
        self.enable_audit_logging = enable_audit_logging and audit_config["enabled"]
        
        # Compile regex patterns for performance
        self.dangerous_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in validation_rules["dangerous_patterns"]]
        self.sql_injection_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in validation_rules["sql_injection_patterns"]]
        self.nosql_injection_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in validation_rules["nosql_injection_patterns"]]
        
        # Whitelist paths that bypass security checks
        self.bypass_paths = {
            "/health",
            "/docs",
            "/openapi.json",
            "/favicon.ico",
            "/static"
        }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Main middleware dispatch method."""
        start_time = time.time()
        
        try:
            # Get client IP
            client_ip = self._get_client_ip(request)
            
            # Check if path should bypass security checks
            if self._should_bypass_security(request.url.path):
                response = await call_next(request)
                self._add_security_headers(response)
                return response
            
            # IP filtering
            if self.enable_ip_filtering:
                ip_check_result = self._check_ip_filtering(client_ip)
                if not ip_check_result["allowed"]:
                    self._log_security_event("ip_blocked", {
                        "client_ip": client_ip,
                        "reason": ip_check_result["reason"],
                        "path": request.url.path
                    })
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "Access denied"}
                    )
            
            # Rate limiting
            if self.enable_rate_limiting and self.rate_limiter:
                rate_limit_result = await self._check_rate_limiting(request, client_ip)
                if not rate_limit_result["allowed"]:
                    self._log_security_event("rate_limit_exceeded", {
                        "client_ip": client_ip,
                        "path": request.url.path,
                        "limit": rate_limit_result.get("limit"),
                        "current": rate_limit_result.get("current")
                    })
                    return JSONResponse(
                        status_code=429,
                        content={
                            "detail": "Rate limit exceeded",
                            "retry_after": rate_limit_result.get("retry_after", 60)
                        },
                        headers={"Retry-After": str(rate_limit_result.get("retry_after", 60))}
                    )
            
            # Input validation for POST/PUT requests
            if self.enable_input_validation and request.method in ["POST", "PUT", "PATCH"]:
                validation_result = await self._validate_request_input(request)
                if not validation_result["valid"]:
                    self._log_security_event("input_validation_failed", {
                        "client_ip": client_ip,
                        "path": request.url.path,
                        "reason": validation_result["reason"],
                        "method": request.method
                    })
                    return JSONResponse(
                        status_code=400,
                        content={"detail": f"Invalid input: {validation_result['reason']}"}
                    )
            
            # Process request
            response = await call_next(request)
            
            # Add security headers
            if self.enable_security_headers:
                self._add_security_headers(response)
            
            # Log successful request
            if self.enable_audit_logging:
                processing_time = time.time() - start_time
                self._log_request(request, response, client_ip, processing_time)
            
            return response
            
        except Exception as e:
            # Log error
            self._log_security_event("middleware_error", {
                "client_ip": client_ip if 'client_ip' in locals() else "unknown",
                "path": request.url.path,
                "error": str(e),
                "method": request.method
            })
            
            # Return generic error response
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers (reverse proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Fallback to direct connection
        return request.client.host if request.client else "unknown"
    
    def _should_bypass_security(self, path: str) -> bool:
        """Check if path should bypass security checks."""
        return any(path.startswith(bypass_path) for bypass_path in self.bypass_paths)
    
    def _check_ip_filtering(self, client_ip: str) -> Dict[str, Any]:
        """Check IP against whitelist/blacklist."""
        try:
            # Parse IP address
            ip_obj = ipaddress.ip_address(client_ip)
            
            # Check blacklist first
            if is_blacklisted_ip(client_ip):
                return {"allowed": False, "reason": "IP is blacklisted"}
            
            # Check if whitelist is configured and IP is not whitelisted
            settings = get_security_settings()
            if settings.ip_whitelist and not is_whitelisted_ip(client_ip):
                return {"allowed": False, "reason": "IP not in whitelist"}
            
            return {"allowed": True}
            
        except ValueError:
            # Invalid IP address
            return {"allowed": False, "reason": "Invalid IP address"}
    
    async def _check_rate_limiting(self, request: Request, client_ip: str) -> Dict[str, Any]:
        """Check rate limiting for the request."""
        try:
            # Get user ID from JWT if available
            user_id = None
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                # Extract user ID from JWT (simplified)
                # In production, you'd properly decode and validate the JWT
                try:
                    from app.services.auth.jwt_handler import decode_jwt
                    token = auth_header.split(" ")[1]
                    payload = decode_jwt(token)
                    user_id = payload.get("user_id")
                except Exception:
                    pass  # Continue without user ID
            
            # Check rate limit
            is_allowed = await self.rate_limiter.is_allowed(
                client_ip=client_ip,
                path=request.url.path,
                user_id=user_id
            )
            
            if not is_allowed:
                # Get current usage for better error message
                status = await self.rate_limiter.get_limit_status(client_ip, request.url.path, user_id)
                return {
                    "allowed": False,
                    "limit": status.get("limit"),
                    "current": status.get("current"),
                    "retry_after": status.get("reset_time", 60)
                }
            
            return {"allowed": True}
            
        except Exception as e:
            logger.error(f"Rate limiting check failed: {e}")
            # Allow request if rate limiting fails
            return {"allowed": True}
    
    async def _validate_request_input(self, request: Request) -> Dict[str, Any]:
        """Validate request input for security threats."""
        try:
            # Get request body
            body = await request.body()
            if not body:
                return {"valid": True}
            
            # Decode body
            try:
                body_str = body.decode("utf-8")
            except UnicodeDecodeError:
                return {"valid": False, "reason": "Invalid character encoding"}
            
            # Check content length
            if len(body_str) > VALIDATION_RULES["max_content_length"]:
                return {"valid": False, "reason": "Content too large"}
            
            # Check for dangerous patterns
            for pattern in self.dangerous_patterns:
                if pattern.search(body_str):
                    return {"valid": False, "reason": "Potentially dangerous content detected"}
            
            # Check for SQL injection patterns
            for pattern in self.sql_injection_patterns:
                if pattern.search(body_str):
                    return {"valid": False, "reason": "Potential SQL injection detected"}
            
            # Check for NoSQL injection patterns
            for pattern in self.nosql_injection_patterns:
                if pattern.search(body_str):
                    return {"valid": False, "reason": "Potential NoSQL injection detected"}
            
            # Validate JSON structure if content-type is JSON
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    json_data = json.loads(body_str)
                    # Additional JSON-specific validation can be added here
                except json.JSONDecodeError:
                    return {"valid": False, "reason": "Invalid JSON format"}
            
            return {"valid": True}
            
        except Exception as e:
            logger.error(f"Input validation failed: {e}")
            # Be conservative - reject if validation fails
            return {"valid": False, "reason": "Validation error"}
    
    def _add_security_headers(self, response: Response) -> None:
        """Add security headers to response."""
        # Add standard security headers
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value
        
        # Add Content Security Policy
        csp_header = get_csp_header()
        if csp_header:
            response.headers["Content-Security-Policy"] = csp_header
        
        # Add custom headers
        response.headers["X-Security-Middleware"] = "Social-Suit-v1.0"
        response.headers["X-Request-ID"] = str(int(time.time() * 1000))
    
    def _log_security_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Log security events for audit purposes."""
        if not self.enable_audit_logging:
            return
        
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "details": details
        }
        
        logger.warning(f"SECURITY_EVENT: {json.dumps(event)}")
    
    def _log_request(self, request: Request, response: Response, client_ip: str, processing_time: float) -> None:
        """Log request for audit purposes."""
        if not self.enable_audit_logging:
            return
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "client_ip": client_ip,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "processing_time": round(processing_time, 3),
            "user_agent": request.headers.get("user-agent", ""),
            "referer": request.headers.get("referer", "")
        }
        
        logger.info(f"REQUEST_LOG: {json.dumps(log_entry)}")

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Lightweight middleware for adding security headers only."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        # Add security headers
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value
        
        # Add Content Security Policy
        csp_header = get_csp_header()
        if csp_header:
            response.headers["Content-Security-Policy"] = csp_header
        
        return response

def create_security_middleware(
    rate_limiter: Optional[RateLimiter] = None,
    enable_rate_limiting: bool = True,
    enable_security_headers: bool = True,
    enable_input_validation: bool = True,
    enable_ip_filtering: bool = True,
    enable_audit_logging: bool = True
) -> SecurityMiddleware:
    """Factory function to create security middleware with configuration."""
    
    def middleware_factory(app: ASGIApp) -> SecurityMiddleware:
        return SecurityMiddleware(
            app=app,
            rate_limiter=rate_limiter,
            enable_rate_limiting=enable_rate_limiting,
            enable_security_headers=enable_security_headers,
            enable_input_validation=enable_input_validation,
            enable_ip_filtering=enable_ip_filtering,
            enable_audit_logging=enable_audit_logging
        )
    
    return middleware_factory

# Export main classes and functions
__all__ = [
    "SecurityMiddleware",
    "SecurityHeadersMiddleware",
    "create_security_middleware"
]
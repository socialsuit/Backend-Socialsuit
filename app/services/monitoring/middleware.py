"""
Monitoring Middleware for FastAPI

This middleware provides automatic logging and monitoring for:
- HTTP requests and responses
- Performance metrics
- Error tracking
- Security events
"""

import time
import uuid
import asyncio
from typing import Callable, Optional
from datetime import datetime
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import json

from .logger_config import structured_logger, LogContext, LogLevel, EventType
from .alerting import alert_manager

class MonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for comprehensive request/response monitoring."""
    
    def __init__(
        self,
        app: ASGIApp,
        exclude_paths: Optional[list] = None,
        log_request_body: bool = False,
        log_response_body: bool = False,
        max_body_size: int = 1024
    ):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/favicon.ico"]
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.max_body_size = max_body_size
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and response with monitoring."""
        # Skip monitoring for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Generate request ID
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Extract request information
        method = request.method
        url = str(request.url)
        path = request.url.path
        query_params = dict(request.query_params)
        headers = dict(request.headers)
        client_ip = self._get_client_ip(request)
        user_agent = headers.get("user-agent", "")
        
        # Set logging context
        context = LogContext(
            request_id=request_id,
            ip_address=client_ip,
            user_agent=user_agent,
            operation=f"{method} {path}"
        )
        structured_logger.set_context(context)
        
        # Log request body if enabled
        request_body = None
        if self.log_request_body and method in ["POST", "PUT", "PATCH"]:
            try:
                body_bytes = await request.body()
                if len(body_bytes) <= self.max_body_size:
                    request_body = body_bytes.decode('utf-8')
                else:
                    request_body = f"<body too large: {len(body_bytes)} bytes>"
            except Exception:
                request_body = "<unable to read body>"
        
        # Log request
        structured_logger.log_api_request(
            method=method,
            endpoint=path,
            request_id=request_id,
            query_params=query_params,
            client_ip=client_ip,
            user_agent=user_agent,
            request_body=request_body
        )
        
        # Process request
        response = None
        error = None
        
        try:
            response = await call_next(request)
            
        except Exception as e:
            error = e
            duration_ms = (time.time() - start_time) * 1000
            
            # Log error
            structured_logger.log_error(
                e,
                context=f"{method} {path}",
                request_id=request_id,
                duration_ms=duration_ms
            )
            
            # Create error response
            response = JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "request_id": request_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        status_code = response.status_code
        
        # Log response body if enabled
        response_body = None
        if self.log_response_body and hasattr(response, 'body'):
            try:
                if hasattr(response.body, 'decode'):
                    body_str = response.body.decode('utf-8')
                    if len(body_str) <= self.max_body_size:
                        response_body = body_str
                    else:
                        response_body = f"<body too large: {len(body_str)} bytes>"
            except Exception:
                response_body = "<unable to read response body>"
        
        # Log response
        structured_logger.log_api_response(
            method=method,
            endpoint=path,
            status_code=status_code,
            duration_ms=duration_ms,
            request_id=request_id,
            response_body=response_body
        )
        
        # Record metrics for alerting
        alert_manager.record_metric("api_response_time", duration_ms)
        alert_manager.record_metric("api_requests_total", 1)
        
        if status_code >= 400:
            alert_manager.record_metric("api_errors_total", 1)
            
            # Check for security events
            await self._check_security_events(request, status_code, client_ip)
        
        # Check for performance issues
        if duration_ms > 5000:  # 5 seconds
            structured_logger.log_structured(
                LogLevel.WARNING,
                f"Slow API response: {method} {path} took {duration_ms:.2f}ms",
                EventType.PERFORMANCE,
                method=method,
                endpoint=path,
                duration_ms=duration_ms,
                request_id=request_id
            )
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to client host
        if hasattr(request.client, 'host'):
            return request.client.host
        
        return "unknown"
    
    async def _check_security_events(self, request: Request, status_code: int, client_ip: str):
        """Check for potential security events."""
        path = request.url.path
        method = request.method
        
        # Check for common attack patterns
        suspicious_patterns = [
            "admin", "wp-admin", "phpmyadmin", "config", "backup",
            "sql", "union", "select", "drop", "insert", "update",
            "script", "alert", "javascript:", "data:",
            "../", "..\\", "/etc/", "\\windows\\",
            "cmd", "powershell", "bash", "sh"
        ]
        
        path_lower = path.lower()
        is_suspicious = any(pattern in path_lower for pattern in suspicious_patterns)
        
        # Log security events
        if status_code == 401:
            structured_logger.log_security_event(
                "unauthorized_access_attempt",
                "medium",
                ip_address=client_ip,
                endpoint=path,
                method=method
            )
        elif status_code == 403:
            structured_logger.log_security_event(
                "forbidden_access_attempt",
                "medium",
                ip_address=client_ip,
                endpoint=path,
                method=method
            )
        elif status_code == 404 and is_suspicious:
            structured_logger.log_security_event(
                "suspicious_path_access",
                "low",
                ip_address=client_ip,
                endpoint=path,
                method=method
            )
        elif status_code >= 500:
            structured_logger.log_security_event(
                "server_error",
                "high",
                ip_address=client_ip,
                endpoint=path,
                method=method,
                status_code=status_code
            )

class BackgroundTaskMonitoringMixin:
    """Mixin for monitoring background tasks."""
    
    @staticmethod
    def monitor_task(task_name: str):
        """Decorator for monitoring background tasks."""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                task_id = str(uuid.uuid4())
                
                # Set context
                context = LogContext(
                    request_id=task_id,
                    operation=task_name
                )
                structured_logger.set_context(context)
                
                # Log task start
                structured_logger.log_background_task(
                    task_name=task_name,
                    status="started",
                    task_id=task_id
                )
                
                try:
                    # Execute task
                    if asyncio.iscoroutinefunction(func):
                        result = await func(*args, **kwargs)
                    else:
                        result = func(*args, **kwargs)
                    
                    duration_ms = (time.time() - start_time) * 1000
                    
                    # Log success
                    structured_logger.log_background_task(
                        task_name=task_name,
                        status="completed",
                        duration_ms=duration_ms,
                        task_id=task_id
                    )
                    
                    return result
                    
                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    
                    # Log failure
                    structured_logger.log_background_task(
                        task_name=task_name,
                        status="failed",
                        duration_ms=duration_ms,
                        task_id=task_id,
                        error=str(e)
                    )
                    
                    # Trigger alert
                    from .alerting import alert_background_task_failure
                    await alert_background_task_failure(
                        task_name=task_name,
                        error=str(e),
                        task_id=task_id,
                        duration_ms=duration_ms
                    )
                    
                    raise
            
            return wrapper
        return decorator

class HealthCheckMiddleware:
    """Health check endpoint for monitoring."""
    
    def __init__(self):
        self.start_time = datetime.utcnow()
    
    async def health_check(self) -> dict:
        """Return system health status."""
        uptime = datetime.utcnow() - self.start_time
        
        # Get performance summary
        perf_summary = structured_logger.get_performance_summary(hours=1)
        error_summary = structured_logger.get_error_summary()
        
        # Calculate health score
        health_score = self._calculate_health_score(perf_summary, error_summary)
        
        return {
            "status": "healthy" if health_score > 0.8 else "degraded" if health_score > 0.5 else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": int(uptime.total_seconds()),
            "health_score": health_score,
            "performance": {
                "avg_response_time_ms": perf_summary.get("avg_duration_ms", 0),
                "total_requests": perf_summary.get("total_operations", 0)
            },
            "errors": {
                "total_errors": sum(error_summary.values()),
                "error_types": len(error_summary)
            },
            "alerts": {
                "active_alerts": len(alert_manager.get_active_alerts()),
                "total_alerts_24h": len(alert_manager.get_alert_history())
            }
        }
    
    def _calculate_health_score(self, perf_summary: dict, error_summary: dict) -> float:
        """Calculate overall health score (0-1)."""
        score = 1.0
        
        # Penalize for high response times
        avg_response_time = perf_summary.get("avg_duration_ms", 0)
        if avg_response_time > 1000:  # 1 second
            score -= min(0.3, (avg_response_time - 1000) / 10000)
        
        # Penalize for errors
        total_errors = sum(error_summary.values())
        total_operations = perf_summary.get("total_operations", 1)
        error_rate = total_errors / total_operations
        
        if error_rate > 0.01:  # 1% error rate
            score -= min(0.5, error_rate * 10)
        
        # Penalize for active alerts
        active_alerts = len(alert_manager.get_active_alerts())
        if active_alerts > 0:
            score -= min(0.2, active_alerts * 0.1)
        
        return max(0.0, score)

# Export main components
__all__ = [
    'MonitoringMiddleware',
    'BackgroundTaskMonitoringMixin',
    'HealthCheckMiddleware'
]
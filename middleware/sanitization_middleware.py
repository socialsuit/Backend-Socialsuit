"""Middleware for automatically sanitizing incoming requests in Social Suit.

This middleware intercepts incoming requests and sanitizes their content
to protect against common security vulnerabilities like HTML/script injections,
XSS attacks, and other malicious inputs.
"""

import json
from typing import Callable, Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app_utils.sanitization import sanitize_dict


class SanitizationMiddleware(BaseHTTPMiddleware):
    """Middleware for sanitizing request data.
    
    This middleware intercepts incoming requests and sanitizes their content
    to protect against common security vulnerabilities.
    """
    
    def __init__(self, app: ASGIApp, exclude_paths: list = None):
        """Initialize the middleware.
        
        Args:
            app: The ASGI application
            exclude_paths: List of paths to exclude from sanitization
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or []
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and sanitize its content.
        
        Args:
            request: The incoming request
            call_next: The next middleware or route handler
            
        Returns:
            The response from the next middleware or route handler
        """
        # Skip sanitization for excluded paths
        for path in self.exclude_paths:
            if request.url.path.startswith(path):
                return await call_next(request)
        
        # Skip sanitization for non-JSON content types
        content_type = request.headers.get("content-type", "")
        if not content_type.startswith("application/json"):
            return await call_next(request)
        
        # Create a modified request with sanitized body
        body = await self._get_body_as_dict(request)
        if body:
            sanitized_body = sanitize_dict(body)
            request = await self._set_body_as_dict(request, sanitized_body)
        
        # Process the request and return the response
        return await call_next(request)
    
    async def _get_body_as_dict(self, request: Request) -> Dict[str, Any]:
        """Get the request body as a dictionary.
        
        Args:
            request: The incoming request
            
        Returns:
            The request body as a dictionary
        """
        try:
            body = await request.body()
            if not body:
                return {}
            return json.loads(body)
        except Exception:
            return {}
    
    async def _set_body_as_dict(self, request: Request, body_dict: Dict[str, Any]) -> Request:
        """Set the request body from a dictionary.
        
        Args:
            request: The incoming request
            body_dict: The dictionary to set as the request body
            
        Returns:
            The modified request
        """
        # Convert the dictionary to a JSON string
        body_str = json.dumps(body_dict).encode("utf-8")
        
        # Create a new request with the modified body
        async def receive():
            return {"type": "http.request", "body": body_str}
        
        request._receive = receive
        return request
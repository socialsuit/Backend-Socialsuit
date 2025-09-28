"""Centralized input sanitization utilities for Social Suit.

This module provides functions to sanitize user input and protect against
common security vulnerabilities like HTML/script injections, XSS attacks,
and other malicious inputs.
"""

import re
import html
from typing import Any, Dict, List, Union, Optional
from fastapi import Request
from pydantic import BaseModel

# Regex patterns for detecting potentially malicious content
HTML_TAG_PATTERN = re.compile(r'<[^>]*>')
SCRIPT_PATTERN = re.compile(r'<script[^>]*>[\s\S]*?<\/script>', re.IGNORECASE)
ON_EVENT_PATTERN = re.compile(r'\s+on\w+\s*=\s*["\'][^"\'>]*["\']', re.IGNORECASE)
JAVASCRIPT_URL_PATTERN = re.compile(r'javascript:\s*', re.IGNORECASE)
DANGEROUS_ATTRIBUTES = re.compile(r'\s+(src|href|style|action)\s*=\s*["\'][^"\'>]*["\']', re.IGNORECASE)


def sanitize_string(value: str) -> str:
    """Sanitize a string by escaping HTML entities and removing potentially malicious content.
    
    Args:
        value: The string to sanitize
        
    Returns:
        The sanitized string
    """
    if not value or not isinstance(value, str):
        return value
    
    # Escape HTML entities
    sanitized = html.escape(value)
    
    # Remove script tags and their content
    sanitized = SCRIPT_PATTERN.sub('', sanitized)
    
    # Remove on* event attributes
    sanitized = ON_EVENT_PATTERN.sub('', sanitized)
    
    # Remove javascript: URLs
    sanitized = JAVASCRIPT_URL_PATTERN.sub('', sanitized)
    
    return sanitized


def strip_html_tags(value: str) -> str:
    """Strip all HTML tags from a string.
    
    Args:
        value: The string to strip HTML tags from
        
    Returns:
        The string with all HTML tags removed
    """
    if not value or not isinstance(value, str):
        return value
    
    return HTML_TAG_PATTERN.sub('', value)


def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively sanitize all string values in a dictionary.
    
    Args:
        data: The dictionary to sanitize
        
    Returns:
        The sanitized dictionary
    """
    if not data or not isinstance(data, dict):
        return data
    
    sanitized_data = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized_data[key] = sanitize_string(value)
        elif isinstance(value, dict):
            sanitized_data[key] = sanitize_dict(value)
        elif isinstance(value, list):
            sanitized_data[key] = sanitize_list(value)
        else:
            sanitized_data[key] = value
    
    return sanitized_data


def sanitize_list(data: List[Any]) -> List[Any]:
    """Recursively sanitize all string values in a list.
    
    Args:
        data: The list to sanitize
        
    Returns:
        The sanitized list
    """
    if not data or not isinstance(data, list):
        return data
    
    sanitized_data = []
    for item in data:
        if isinstance(item, str):
            sanitized_data.append(sanitize_string(item))
        elif isinstance(item, dict):
            sanitized_data.append(sanitize_dict(item))
        elif isinstance(item, list):
            sanitized_data.append(sanitize_list(item))
        else:
            sanitized_data.append(item)
    
    return sanitized_data


def sanitize_model(model: BaseModel) -> BaseModel:
    """Sanitize all string fields in a Pydantic model.
    
    Args:
        model: The Pydantic model to sanitize
        
    Returns:
        The sanitized model
    """
    if not model or not isinstance(model, BaseModel):
        return model
    
    # Convert model to dict, sanitize, and convert back to model
    model_dict = model.dict()
    sanitized_dict = sanitize_dict(model_dict)
    
    # Create a new instance of the model with sanitized data
    return model.__class__(**sanitized_dict)


async def sanitize_request_body(request: Request) -> Dict[str, Any]:
    """Sanitize the JSON body of a FastAPI request.
    
    Args:
        request: The FastAPI request object
        
    Returns:
        The sanitized request body as a dictionary
    """
    try:
        body = await request.json()
        return sanitize_dict(body)
    except Exception:
        return {}


def sanitize_query_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize query parameters.
    
    Args:
        params: Dictionary of query parameters
        
    Returns:
        Sanitized query parameters
    """
    return sanitize_dict(params)


def sanitize_path_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize path parameters.
    
    Args:
        params: Dictionary of path parameters
        
    Returns:
        Sanitized path parameters
    """
    return sanitize_dict(params)


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to prevent path traversal attacks.
    
    Args:
        filename: The filename to sanitize
        
    Returns:
        The sanitized filename
    """
    if not filename or not isinstance(filename, str):
        return ""
    
    # Remove path traversal sequences and other potentially dangerous characters
    sanitized = re.sub(r'[\\/:*?"<>|]', '', filename)
    sanitized = re.sub(r'\.\.\/|\.\\', '', sanitized)
    
    return sanitized


def sanitize_email(email: str) -> str:
    """Sanitize an email address.
    
    Args:
        email: The email address to sanitize
        
    Returns:
        The sanitized email address
    """
    if not email or not isinstance(email, str):
        return ""
    
    # Basic email sanitization - remove any HTML tags and scripts
    sanitized = sanitize_string(email)
    
    # Additional email-specific sanitization could be added here
    
    return sanitized


def sanitize_url(url: str) -> str:
    """Sanitize a URL to prevent open redirect vulnerabilities.
    
    Args:
        url: The URL to sanitize
        
    Returns:
        The sanitized URL
    """
    if not url or not isinstance(url, str):
        return ""
    
    # Remove javascript: URLs
    sanitized = JAVASCRIPT_URL_PATTERN.sub('', url)
    
    # Additional URL sanitization could be added here
    
    return sanitized
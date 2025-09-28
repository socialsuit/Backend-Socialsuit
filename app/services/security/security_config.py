"""
Security Configuration for Social Suit Application

This module provides centralized security configuration including:
- Rate limiting settings
- Validation rules
- Security headers
- CORS configuration
- Authentication settings
"""

from typing import Dict, List, Optional, Set
from pydantic_settings import BaseSettings
from pydantic import Field
import os
from datetime import timedelta

class SecuritySettings(BaseSettings):
    """Security settings configuration."""
    
    # JWT Settings
    jwt_secret_key: str = Field(default="development-secret-key", env="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(default=30, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_refresh_token_expire_days: int = Field(default=7, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    
    # Rate Limiting Settings
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    rate_limit_default_requests_per_minute: int = Field(default=60, env="RATE_LIMIT_DEFAULT_RPM")
    rate_limit_default_burst_size: int = Field(default=10, env="RATE_LIMIT_DEFAULT_BURST")
    
    # CORS Settings
    cors_allow_origins: List[str] = Field(default=["http://localhost:3000"], env="CORS_ALLOW_ORIGINS")
    cors_allow_credentials: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: List[str] = Field(default=["GET", "POST", "PUT", "DELETE", "OPTIONS"], env="CORS_ALLOW_METHODS")
    cors_allow_headers: List[str] = Field(default=["*"], env="CORS_ALLOW_HEADERS")
    
    # Security Headers
    security_headers_enabled: bool = Field(default=True, env="SECURITY_HEADERS_ENABLED")
    hsts_max_age: int = Field(default=31536000, env="HSTS_MAX_AGE")  # 1 year
    
    # Content Security Policy
    csp_enabled: bool = Field(default=True, env="CSP_ENABLED")
    csp_default_src: List[str] = Field(default=["'self'"], env="CSP_DEFAULT_SRC")
    csp_script_src: List[str] = Field(default=["'self'", "'unsafe-inline'"], env="CSP_SCRIPT_SRC")
    csp_style_src: List[str] = Field(default=["'self'", "'unsafe-inline'"], env="CSP_STYLE_SRC")
    csp_img_src: List[str] = Field(default=["'self'", "data:", "https:"], env="CSP_IMG_SRC")
    
    # Input Validation Settings
    max_content_length: int = Field(default=10000, env="MAX_CONTENT_LENGTH")
    max_file_size_mb: int = Field(default=10, env="MAX_FILE_SIZE_MB")
    allowed_file_extensions: Set[str] = Field(
        default={".jpg", ".jpeg", ".png", ".gif", ".pdf", ".txt", ".docx"},
        env="ALLOWED_FILE_EXTENSIONS"
    )
    blocked_file_extensions: Set[str] = Field(
        default={".exe", ".bat", ".cmd", ".scr", ".vbs", ".js", ".jar"},
        env="BLOCKED_FILE_EXTENSIONS"
    )
    
    # IP Whitelist/Blacklist
    ip_whitelist: List[str] = Field(default=[], env="IP_WHITELIST")
    ip_blacklist: List[str] = Field(default=[], env="IP_BLACKLIST")
    
    # Admin Settings
    admin_emails: List[str] = Field(default=[], env="ADMIN_EMAILS")
    admin_ips: List[str] = Field(default=[], env="ADMIN_IPS")
    
    # Audit Settings
    audit_enabled: bool = Field(default=True, env="AUDIT_ENABLED")
    audit_log_file: str = Field(default="security_audit.log", env="AUDIT_LOG_FILE")
    audit_retention_days: int = Field(default=90, env="AUDIT_RETENTION_DAYS")
    
    # Database Security
    db_connection_timeout: int = Field(default=30, env="DB_CONNECTION_TIMEOUT")
    db_query_timeout: int = Field(default=60, env="DB_QUERY_TIMEOUT")
    db_max_connections: int = Field(default=20, env="DB_MAX_CONNECTIONS")
    
    # Session Security
    session_timeout_minutes: int = Field(default=60, env="SESSION_TIMEOUT_MINUTES")
    session_secure_cookies: bool = Field(default=True, env="SESSION_SECURE_COOKIES")
    session_httponly_cookies: bool = Field(default=True, env="SESSION_HTTPONLY_COOKIES")
    session_samesite: str = Field(default="lax", env="SESSION_SAMESITE")
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore",
        "env_file_encoding": "utf-8"
    }

# Global security settings instance
# Lazy initialization to avoid import-time issues
security_settings = None

def get_security_settings():
    """Get security settings instance with proper environment loading."""
    global security_settings
    if security_settings is None:
        from dotenv import load_dotenv
        load_dotenv()
        security_settings = SecuritySettings()
    return security_settings

# Rate limiting configuration
RATE_LIMIT_CONFIG = {
    "enabled": True,  # Will be updated by get_security_settings()
    "default_requests_per_minute": 60,  # Will be updated by get_security_settings()
    "default_burst_size": 10,  # Will be updated by get_security_settings()
    "redis_url": "redis://localhost:6379/1",  # Will be updated by get_security_settings()
    "endpoint_limits": {
        # Authentication endpoints - stricter limits
        "/auth/login": 5,
        "/auth/register": 3,
        "/auth/forgot-password": 3,
        "/auth/reset-password": 3,
        
        # Data collection endpoints - moderate limits
        "/analytics/collect": 10,
        "/scheduled-posts/bulk": 15,
        
        # Regular API endpoints - standard limits
        "/analytics/overview": 30,
        "/analytics/chart": 40,
        "/scheduled-posts/create": 20,
        "/scheduled-posts/update": 25,
        "/ab-test/create": 10,
        "/ab-test/details": 30,
        
        # Search and listing endpoints - higher limits
        "/scheduled-posts/search": 50,
        "/scheduled-posts/list": 60,
        "/analytics/recommendations": 20,
    },
    "whitelist_ips": [],  # Will be updated by get_security_settings()
    "whitelist_paths": [
        "/health",
        "/docs",
        "/openapi.json",
        "/favicon.ico"
    ]
}

def update_rate_limit_config():
    """Update rate limit config with actual security settings."""
    settings = get_security_settings()
    RATE_LIMIT_CONFIG.update({
        "enabled": settings.rate_limit_enabled,
        "default_requests_per_minute": settings.rate_limit_default_requests_per_minute,
        "default_burst_size": settings.rate_limit_default_burst_size,
        "redis_url": settings.rate_limit_redis_url,
        "whitelist_ips": settings.ip_whitelist + settings.admin_ips
    })

# Security headers configuration
def get_security_headers():
    """Get security headers configuration."""
    settings = get_security_settings()
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        "Strict-Transport-Security": f"max-age={settings.hsts_max_age}; includeSubDomains"
    }

# Content Security Policy
def get_csp_header() -> str:
    """Generate Content Security Policy header."""
    settings = get_security_settings()
    if not settings.csp_enabled:
        return ""
    
    csp_directives = [
        f"default-src {' '.join(settings.csp_default_src)}",
        f"script-src {' '.join(settings.csp_script_src)}",
        f"style-src {' '.join(settings.csp_style_src)}",
        f"img-src {' '.join(settings.csp_img_src)}",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'"
    ]
    
    return "; ".join(csp_directives)

# Input validation rules
def get_validation_rules():
    """Get input validation rules."""
    settings = get_security_settings()
    return {
        "max_content_length": settings.max_content_length,
        "max_file_size_bytes": settings.max_file_size_mb * 1024 * 1024,
        "allowed_file_extensions": settings.allowed_file_extensions,
        "blocked_file_extensions": settings.blocked_file_extensions,
        "dangerous_patterns": [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"vbscript:",
            r"onload\s*=",
            r"onerror\s*=",
            r"onclick\s*=",
        r"eval\s*\(",
        r"document\.cookie",
        r"document\.write",
        r"window\.location"
        ],
        "sql_injection_patterns": [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
            r"(\b(OR|AND)\s+['\"].*['\"])",
            r"(--|#|/\*|\*/)",
            r"(\bxp_cmdshell\b)",
            r"(\bsp_executesql\b)"
        ],
        "nosql_injection_patterns": [
            r"\$where",
            r"\$ne",
            r"\$gt",
            r"\$lt",
            r"\$regex",
            r"\$or",
            r"\$and",
            r"function\s*\(",
            r"this\.",
            r"sleep\s*\("
        ]
    }

# Audit configuration
def get_audit_config():
    """Get audit configuration."""
    settings = get_security_settings()
    return {
        "enabled": settings.audit_enabled,
        "log_file": settings.audit_log_file,
        "retention_days": settings.audit_retention_days,
        "events_to_log": [
            "authentication",
            "authorization_failure",
            "data_access",
            "data_modification",
            "admin_action",
            "security_violation",
            "rate_limit_exceeded",
            "suspicious_activity"
        ]
    }

# Database security configuration
def get_database_security():
    """Get database security configuration."""
    settings = get_security_settings()
    return {
        "connection_timeout": settings.db_connection_timeout,
        "query_timeout": settings.db_query_timeout,
        "max_connections": settings.db_max_connections,
        "enable_query_logging": True,
        "log_slow_queries": True,
        "slow_query_threshold_seconds": 5
    }

# Session security configuration
def get_session_config():
    """Get session security configuration."""
    settings = get_security_settings()
    return {
        "timeout_minutes": settings.session_timeout_minutes,
        "secure_cookies": settings.session_secure_cookies,
        "httponly_cookies": settings.session_httponly_cookies,
        "samesite": settings.session_samesite,
        "cookie_name": "social_suit_session",
        "cookie_path": "/",
        "cookie_domain": None  # Set based on environment
    }

def get_security_middleware_config() -> Dict:
    """Get configuration for security middleware."""
    update_rate_limit_config()  # Ensure rate limit config is updated
    return {
        "rate_limiting": RATE_LIMIT_CONFIG,
        "security_headers": get_security_headers(),
        "csp_header": get_csp_header(),
        "validation_rules": get_validation_rules(),
        "audit_config": get_audit_config(),
        "session_config": get_session_config()
    }

def is_admin_user(user_email: str, user_ip: str = None) -> bool:
    """Check if user is an admin based on email and/or IP."""
    settings = get_security_settings()
    is_admin_email = user_email in settings.admin_emails
    is_admin_ip = user_ip in settings.admin_ips if user_ip else False
    
    return is_admin_email or is_admin_ip

def is_whitelisted_ip(ip: str) -> bool:
    """Check if IP is whitelisted."""
    settings = get_security_settings()
    return ip in settings.ip_whitelist

def is_blacklisted_ip(ip: str) -> bool:
    """Check if IP is blacklisted."""
    settings = get_security_settings()
    return ip in settings.ip_blacklist

def validate_file_upload(filename: str, content_type: str, file_size: int) -> Dict[str, any]:
    """Validate file upload based on security rules."""
    import os
    
    validation_rules = get_validation_rules()
    settings = get_security_settings()
    
    # Check file size
    if file_size > validation_rules["max_file_size_bytes"]:
        return {
            "valid": False,
            "error": f"File size exceeds maximum allowed size of {settings.max_file_size_mb}MB"
        }
    
    # Check file extension
    file_ext = os.path.splitext(filename)[1].lower()
    
    if file_ext in validation_rules["blocked_file_extensions"]:
        return {
            "valid": False,
            "error": f"File type '{file_ext}' is not allowed"
        }
    
    if file_ext not in validation_rules["allowed_file_extensions"]:
        return {
            "valid": False,
            "error": f"File type '{file_ext}' is not in allowed extensions"
        }
    
    # Check content type
    dangerous_content_types = [
        "application/x-executable",
        "application/x-msdownload",
        "application/x-msdos-program",
        "application/javascript",
        "text/javascript"
    ]
    
    if content_type in dangerous_content_types:
        return {
            "valid": False,
            "error": f"Content type '{content_type}' is not allowed"
        }
    
    return {"valid": True}

# Export main configuration
__all__ = [
    "get_security_settings",
    "RATE_LIMIT_CONFIG",
    "get_security_headers",
    "get_validation_rules",
    "get_audit_config",
    "get_database_security",
    "get_session_config",
    "get_security_middleware_config",
    "get_csp_header",
    "is_admin_user",
    "is_whitelisted_ip",
    "is_blacklisted_ip",
    "validate_file_upload"
]
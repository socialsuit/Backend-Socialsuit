import logging
import logging.config
import os
import json
import sys
from typing import Dict, Any, Optional, Union
from datetime import datetime

# Default logging configuration
DEFAULT_LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
        "json": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "class": "app_utils.logging_utils.JsonFormatter"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "standard",
            "filename": "app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf8"
        },
    },
    "loggers": {
        "": {  # root logger
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True
        }
    }
}

class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def __init__(self, fmt=None, datefmt=None, style='%', extra_fields=None):
        super().__init__(fmt, datefmt, style)
        self.extra_fields = extra_fields or {}
    
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        
        # Add exception info if available
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        
        # Add configured extra fields
        log_data.update(self.extra_fields)
        
        # Add any extra attributes from the LogRecord
        for key, value in record.__dict__.items():
            if key not in ["args", "asctime", "created", "exc_info", "exc_text", "filename",
                          "funcName", "id", "levelname", "levelno", "lineno", "module",
                          "msecs", "message", "msg", "name", "pathname", "process",
                          "processName", "relativeCreated", "stack_info", "thread", "threadName"]:
                log_data[key] = value
        
        return json.dumps(log_data)

class ContextAdapter(logging.LoggerAdapter):
    """Logger adapter that adds context to log messages."""
    
    def process(self, msg, kwargs):
        # Add extra context to the record
        kwargs.setdefault("extra", {}).update(self.extra)
        return msg, kwargs

def setup_logging(
    config_path: Optional[str] = None,
    default_level: str = "INFO",
    env_key: str = "LOG_CONFIG",
    log_format: str = "standard",  # "standard" or "json"
    log_file: Optional[str] = None,
    extra_handlers: Optional[Dict[str, Dict[str, Any]]] = None
) -> None:
    """Set up logging configuration.
    
    Args:
        config_path: Path to logging configuration file (JSON or YAML)
        default_level: Default logging level if config file is not found
        env_key: Environment variable that can specify config file path
        log_format: Format for logs ("standard" or "json")
        log_file: Path to log file (if None, only console logging is enabled)
        extra_handlers: Additional logging handlers to configure
    """
    config = DEFAULT_LOGGING_CONFIG.copy()
    
    # Check environment variable for config path
    env_path = os.getenv(env_key, None)
    if env_path:
        config_path = env_path
    
    # Load config from file if available
    if config_path and os.path.exists(config_path):
        with open(config_path, 'rt') as f:
            try:
                if config_path.endswith('.json'):
                    file_config = json.load(f)
                    config.update(file_config)
                elif config_path.endswith(('.yaml', '.yml')):
                    import yaml
                    file_config = yaml.safe_load(f.read())
                    config.update(file_config)
            except Exception as e:
                print(f"Error loading logging configuration from {config_path}: {e}")
    
    # Update log level
    config["loggers"][""]["level"] = default_level
    
    # Configure log format
    if log_format == "json":
        for handler in config["handlers"].values():
            handler["formatter"] = "json"
    
    # Configure log file if specified
    if log_file:
        config["handlers"]["file"]["filename"] = log_file
        if "file" not in config["loggers"][""]["handlers"]:
            config["loggers"][""]["handlers"].append("file")
    else:
        # Remove file handler if no log file specified
        if "file" in config["handlers"]:
            if "file" in config["loggers"][""]["handlers"]:
                config["loggers"][""]["handlers"].remove("file")
    
    # Add extra handlers if specified
    if extra_handlers:
        for name, handler_config in extra_handlers.items():
            config["handlers"][name] = handler_config
            if name not in config["loggers"][""]["handlers"]:
                config["loggers"][""]["handlers"].append(name)
    
    # Apply configuration
    logging.config.dictConfig(config)

def get_logger(name: str, context: Optional[Dict[str, Any]] = None) -> Union[logging.Logger, logging.LoggerAdapter]:
    """Get a logger with optional context.
    
    Args:
        name: Logger name
        context: Optional context dictionary to add to all log messages
        
    Returns:
        Logger or LoggerAdapter with context
    """
    logger = logging.getLogger(name)
    
    if context:
        return ContextAdapter(logger, context)
    
    return logger

# Request ID middleware for web frameworks
class RequestIdMiddleware:
    """Middleware to add request ID to logging context.
    
    This is a generic implementation that can be adapted for different web frameworks.
    """
    
    def __init__(self, app, header_name="X-Request-ID", attribute_name="request_id"):
        self.app = app
        self.header_name = header_name
        self.attribute_name = attribute_name
    
    def __call__(self, environ, start_response):
        # This implementation is for WSGI
        # For FastAPI, you would use a middleware with Request and Response objects
        request_id = environ.get(f"HTTP_{self.header_name.replace('-', '_').upper()}", None)
        
        if not request_id:
            import uuid
            request_id = str(uuid.uuid4())
        
        # Store request ID in environment
        environ[self.attribute_name] = request_id
        
        # Add request ID to logging context
        old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.request_id = request_id
            return record
        
        logging.setLogRecordFactory(record_factory)
        
        # Add request ID to response headers
        def custom_start_response(status, headers, exc_info=None):
            headers.append((self.header_name, request_id))
            return start_response(status, headers, exc_info)
        
        return self.app(environ, custom_start_response)

# FastAPI specific request ID middleware
try:
    from fastapi import Request, Response
    from starlette.middleware.base import BaseHTTPMiddleware
    
    class FastAPIRequestIdMiddleware(BaseHTTPMiddleware):
        """FastAPI middleware to add request ID to logging context."""
        
        def __init__(self, app, header_name="X-Request-ID"):
            super().__init__(app)
            self.header_name = header_name
        
        async def dispatch(self, request: Request, call_next):
            # Get or generate request ID
            request_id = request.headers.get(self.header_name)
            if not request_id:
                import uuid
                request_id = str(uuid.uuid4())
            
            # Add request ID to request state
            request.state.request_id = request_id
            
            # Set up logging context for this request
            logger = logging.getLogger()
            old_factory = logging.getLogRecordFactory()
            
            def record_factory(*args, **kwargs):
                record = old_factory(*args, **kwargs)
                record.request_id = request_id
                return record
            
            logging.setLogRecordFactory(record_factory)
            
            # Process the request
            response = await call_next(request)
            
            # Add request ID to response headers
            response.headers[self.header_name] = request_id
            
            return response
            
except ImportError:
    # FastAPI not available, skip this middleware
    pass
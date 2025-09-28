"""
Structured Logging Configuration with Performance Monitoring

This module provides a comprehensive logging setup using loguru with:
- Structured JSON logging
- Performance monitoring
- Error tracking
- Request/response logging
- Background task monitoring
"""

import sys
import json
import time
import functools
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger
from contextlib import contextmanager
import asyncio
import threading
from dataclasses import dataclass, asdict
from enum import Enum

# Create logs directory
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

class LogLevel(str, Enum):
    """Log levels for structured logging."""
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class EventType(str, Enum):
    """Event types for categorizing log entries."""
    API_REQUEST = "api_request"
    API_RESPONSE = "api_response"
    BACKGROUND_TASK = "background_task"
    DATABASE_QUERY = "database_query"
    EXTERNAL_API = "external_api"
    SECURITY_EVENT = "security_event"
    PERFORMANCE = "performance"
    ERROR = "error"
    SYSTEM = "system"

@dataclass
class PerformanceMetrics:
    """Performance metrics data structure."""
    operation: str
    duration_ms: float
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

@dataclass
class LogContext:
    """Context information for structured logging."""
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    operation: Optional[str] = None
    platform: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class StructuredLogger:
    """Enhanced logger with structured logging capabilities."""
    
    def __init__(self):
        self.setup_logger()
        self._context = threading.local()
        self._performance_metrics = []
        self._error_counts = {}
        
    def setup_logger(self):
        """Configure loguru with multiple outputs and formats."""
        # Remove default handler
        logger.remove()
        
        # Console handler with colored output
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                   "<level>{level: <8}</level> | "
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                   "<level>{message}</level>",
            level="INFO",
            colorize=True
        )
        
        # JSON file handler for structured logs
        logger.add(
            LOGS_DIR / "app_{time:YYYY-MM-DD}.json",
            format=self._json_formatter,
            level="DEBUG",
            rotation="1 day",
            retention="30 days",
            compression="gz",
            serialize=True
        )
        
        # Error file handler
        logger.add(
            LOGS_DIR / "errors_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
            level="ERROR",
            rotation="1 day",
            retention="30 days",
            compression="gz"
        )
        
        # Performance metrics file
        logger.add(
            LOGS_DIR / "performance_{time:YYYY-MM-DD}.json",
            format=self._json_formatter,
            level="INFO",
            rotation="1 day",
            retention="7 days",
            filter=lambda record: record["extra"].get("event_type") == EventType.PERFORMANCE
        )
    
    def _json_formatter(self, record):
        """Custom JSON formatter for structured logging."""
        # Extract structured data
        structured_data = {
            "timestamp": record["time"].isoformat(),
            "level": record["level"].name,
            "logger": record["name"],
            "function": record["function"],
            "line": record["line"],
            "message": record["message"],
            "module": record["module"],
            "process_id": record["process"].id,
            "thread_id": record["thread"].id,
        }
        
        # Add extra fields
        if record["extra"]:
            structured_data.update(record["extra"])
        
        # Add exception info if present
        if record["exception"]:
            structured_data["exception"] = {
                "type": record["exception"].type.__name__,
                "value": str(record["exception"].value),
                "traceback": record["exception"].traceback
            }
        
        return json.dumps(structured_data, default=str, ensure_ascii=False)
    
    def set_context(self, context: LogContext):
        """Set logging context for current thread."""
        self._context.data = asdict(context)
    
    def get_context(self) -> Dict[str, Any]:
        """Get current logging context."""
        return getattr(self._context, 'data', {})
    
    def log_structured(
        self, 
        level: LogLevel, 
        message: str, 
        event_type: EventType,
        **kwargs
    ):
        """Log with structured data."""
        extra_data = {
            "event_type": event_type.value,
            **self.get_context(),
            **kwargs
        }
        
        logger.bind(**extra_data).log(level.value, message)
    
    def log_api_request(
        self, 
        method: str, 
        endpoint: str, 
        request_id: str,
        user_id: Optional[str] = None,
        **kwargs
    ):
        """Log API request."""
        self.log_structured(
            LogLevel.INFO,
            f"API Request: {method} {endpoint}",
            EventType.API_REQUEST,
            method=method,
            endpoint=endpoint,
            request_id=request_id,
            user_id=user_id,
            **kwargs
        )
    
    def log_api_response(
        self, 
        method: str, 
        endpoint: str, 
        status_code: int,
        duration_ms: float,
        request_id: str,
        **kwargs
    ):
        """Log API response."""
        self.log_structured(
            LogLevel.INFO,
            f"API Response: {method} {endpoint} - {status_code} ({duration_ms:.2f}ms)",
            EventType.API_RESPONSE,
            method=method,
            endpoint=endpoint,
            status_code=status_code,
            duration_ms=duration_ms,
            request_id=request_id,
            **kwargs
        )
    
    def log_background_task(
        self, 
        task_name: str, 
        status: str,
        duration_ms: Optional[float] = None,
        **kwargs
    ):
        """Log background task execution."""
        message = f"Background Task: {task_name} - {status}"
        if duration_ms:
            message += f" ({duration_ms:.2f}ms)"
            
        self.log_structured(
            LogLevel.INFO if status == "completed" else LogLevel.ERROR,
            message,
            EventType.BACKGROUND_TASK,
            task_name=task_name,
            status=status,
            duration_ms=duration_ms,
            **kwargs
        )
    
    def log_performance(self, metrics: PerformanceMetrics):
        """Log performance metrics."""
        self.log_structured(
            LogLevel.INFO,
            f"Performance: {metrics.operation} took {metrics.duration_ms:.2f}ms",
            EventType.PERFORMANCE,
            **asdict(metrics)
        )
        
        # Store metrics for monitoring
        self._performance_metrics.append(metrics)
        
        # Keep only last 1000 metrics in memory
        if len(self._performance_metrics) > 1000:
            self._performance_metrics = self._performance_metrics[-1000:]
    
    def log_security_event(
        self, 
        event: str, 
        severity: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        **kwargs
    ):
        """Log security events."""
        level = LogLevel.WARNING if severity == "medium" else LogLevel.ERROR
        
        self.log_structured(
            level,
            f"Security Event: {event}",
            EventType.SECURITY_EVENT,
            event=event,
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            **kwargs
        )
    
    def log_error(
        self, 
        error: Exception, 
        context: Optional[str] = None,
        **kwargs
    ):
        """Log errors with context."""
        error_type = type(error).__name__
        
        # Track error counts
        self._error_counts[error_type] = self._error_counts.get(error_type, 0) + 1
        
        message = f"Error: {error_type}"
        if context:
            message += f" in {context}"
        
        self.log_structured(
            LogLevel.ERROR,
            message,
            EventType.ERROR,
            error_type=error_type,
            error_message=str(error),
            context=context,
            error_count=self._error_counts[error_type],
            **kwargs
        )
    
    def get_performance_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get performance summary for the last N hours."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_metrics = [
            m for m in self._performance_metrics 
            if m.timestamp >= cutoff_time
        ]
        
        if not recent_metrics:
            return {"message": "No metrics available"}
        
        durations = [m.duration_ms for m in recent_metrics]
        operations = {}
        
        for metric in recent_metrics:
            if metric.operation not in operations:
                operations[metric.operation] = []
            operations[metric.operation].append(metric.duration_ms)
        
        return {
            "total_operations": len(recent_metrics),
            "avg_duration_ms": sum(durations) / len(durations),
            "max_duration_ms": max(durations),
            "min_duration_ms": min(durations),
            "operations_summary": {
                op: {
                    "count": len(times),
                    "avg_ms": sum(times) / len(times),
                    "max_ms": max(times)
                }
                for op, times in operations.items()
            }
        }
    
    def get_error_summary(self) -> Dict[str, int]:
        """Get error count summary."""
        return self._error_counts.copy()

# Global logger instance
structured_logger = StructuredLogger()

# Decorators for automatic logging
def log_performance(operation_name: Optional[str] = None):
    """Decorator to automatically log function performance."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                metrics = PerformanceMetrics(
                    operation=op_name,
                    duration_ms=duration_ms
                )
                structured_logger.log_performance(metrics)
                
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                structured_logger.log_error(e, context=op_name)
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                metrics = PerformanceMetrics(
                    operation=op_name,
                    duration_ms=duration_ms
                )
                structured_logger.log_performance(metrics)
                
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                structured_logger.log_error(e, context=op_name)
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

@contextmanager
def log_operation(operation_name: str, **context):
    """Context manager for logging operations."""
    start_time = time.time()
    
    structured_logger.log_structured(
        LogLevel.INFO,
        f"Starting operation: {operation_name}",
        EventType.SYSTEM,
        operation=operation_name,
        **context
    )
    
    try:
        yield
        duration_ms = (time.time() - start_time) * 1000
        
        structured_logger.log_structured(
            LogLevel.SUCCESS,
            f"Completed operation: {operation_name} ({duration_ms:.2f}ms)",
            EventType.SYSTEM,
            operation=operation_name,
            duration_ms=duration_ms,
            **context
        )
        
        # Log performance metrics
        metrics = PerformanceMetrics(
            operation=operation_name,
            duration_ms=duration_ms
        )
        structured_logger.log_performance(metrics)
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        
        structured_logger.log_structured(
            LogLevel.ERROR,
            f"Failed operation: {operation_name} ({duration_ms:.2f}ms) - {str(e)}",
            EventType.ERROR,
            operation=operation_name,
            duration_ms=duration_ms,
            error=str(e),
            **context
        )
        raise

# Export main components
__all__ = [
    'structured_logger',
    'LogLevel',
    'EventType',
    'LogContext',
    'PerformanceMetrics',
    'log_performance',
    'log_operation'
]
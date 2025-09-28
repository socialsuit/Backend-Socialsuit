"""
Monitoring Package

Comprehensive monitoring and logging solution for the Social Suit application.
Includes structured logging, alerting, performance monitoring, and middleware.
"""

from .logger_config import (
    structured_logger,
    LogLevel,
    EventType,
    LogContext,
    PerformanceMetrics,
    log_performance,
    log_operation
)

from .alerting import (
    alert_manager,
    AlertManager,
    AlertRule,
    Alert,
    AlertSeverity,
    AlertType,
    EmailAlertChannel,
    WebhookAlertChannel,
    alert_background_task_failure,
    alert_api_downtime
)

from .middleware import (
    MonitoringMiddleware,
    BackgroundTaskMonitoringMixin,
    HealthCheckMiddleware
)

# Version info
__version__ = "1.0.0"

# Quick setup function
def setup_monitoring(
    app=None,
    email_config: dict = None,
    webhook_url: str = None,
    enable_middleware: bool = True
):
    """
    Quick setup function for monitoring.
    
    Args:
        app: FastAPI application instance
        email_config: Email configuration dict with keys:
            - smtp_host, smtp_port, username, password, from_email, to_emails
        webhook_url: Webhook URL for alerts (Slack, Discord, etc.)
        enable_middleware: Whether to add monitoring middleware
    
    Returns:
        Configured monitoring components
    """
    # Setup alert channels
    if email_config:
        email_channel = EmailAlertChannel(**email_config)
        alert_manager.add_channel(email_channel)
    
    if webhook_url:
        webhook_channel = WebhookAlertChannel(webhook_url)
        alert_manager.add_channel(webhook_channel)
    
    # Setup middleware
    if app and enable_middleware:
        app.add_middleware(MonitoringMiddleware)
        
        # Add health check endpoint
        health_check = HealthCheckMiddleware()
        
        @app.get("/health")
        async def health_endpoint():
            return await health_check.health_check()
        
        @app.get("/metrics")
        async def metrics_endpoint():
            return {
                "performance": structured_logger.get_performance_summary(),
                "errors": structured_logger.get_error_summary(),
                "alerts": {
                    "active": len(alert_manager.get_active_alerts()),
                    "recent": len(alert_manager.get_alert_history(24))
                }
            }
    
    # Start alert monitoring
    import asyncio
    asyncio.create_task(alert_manager.start_monitoring())
    
    structured_logger.log_structured(
        LogLevel.INFO,
        "Monitoring system initialized",
        EventType.SYSTEM,
        email_enabled=bool(email_config),
        webhook_enabled=bool(webhook_url),
        middleware_enabled=enable_middleware
    )
    
    return {
        "logger": structured_logger,
        "alert_manager": alert_manager,
        "health_check": health_check if app else None
    }

__all__ = [
    # Logger components
    'structured_logger',
    'LogLevel',
    'EventType', 
    'LogContext',
    'PerformanceMetrics',
    'log_performance',
    'log_operation',
    
    # Alerting components
    'alert_manager',
    'AlertManager',
    'AlertRule',
    'Alert',
    'AlertSeverity',
    'AlertType',
    'EmailAlertChannel',
    'WebhookAlertChannel',
    'alert_background_task_failure',
    'alert_api_downtime',
    
    # Middleware components
    'MonitoringMiddleware',
    'BackgroundTaskMonitoringMixin',
    'HealthCheckMiddleware',
    
    # Setup function
    'setup_monitoring'
]
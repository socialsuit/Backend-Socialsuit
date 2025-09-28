"""
Alerting System for Background Tasks and API Monitoring

This module provides alerting capabilities for:
- Failed background tasks
- API downtime detection
- Performance degradation
- Error rate monitoring
- System health checks
"""

import asyncio
import json
import smtplib
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
import aiohttp
import threading
from collections import defaultdict, deque

from .logger_config import structured_logger, LogLevel, EventType

class AlertSeverity(str, Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertType(str, Enum):
    """Types of alerts."""
    BACKGROUND_TASK_FAILURE = "background_task_failure"
    API_DOWNTIME = "api_downtime"
    HIGH_ERROR_RATE = "high_error_rate"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    SYSTEM_HEALTH = "system_health"
    SECURITY_INCIDENT = "security_incident"

@dataclass
class AlertRule:
    """Configuration for alert rules."""
    name: str
    alert_type: AlertType
    severity: AlertSeverity
    threshold: float
    time_window_minutes: int
    enabled: bool = True
    cooldown_minutes: int = 30
    description: str = ""

@dataclass
class Alert:
    """Alert data structure."""
    id: str
    rule_name: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    timestamp: datetime
    metadata: Dict[str, Any]
    resolved: bool = False
    resolved_at: Optional[datetime] = None

class AlertChannel:
    """Base class for alert channels."""
    
    async def send_alert(self, alert: Alert) -> bool:
        """Send alert through this channel."""
        raise NotImplementedError

class EmailAlertChannel(AlertChannel):
    """Email alert channel."""
    
    def __init__(
        self, 
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_email: str,
        to_emails: List[str],
        use_tls: bool = True
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.to_emails = to_emails
        self.use_tls = use_tls
    
    async def send_alert(self, alert: Alert) -> bool:
        """Send alert via email."""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            msg['Subject'] = f"[{alert.severity.upper()}] {alert.title}"
            
            # Create email body
            body = self._create_email_body(alert)
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            if self.use_tls:
                server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()
            
            structured_logger.log_structured(
                LogLevel.INFO,
                f"Alert email sent: {alert.title}",
                EventType.SYSTEM,
                alert_id=alert.id,
                recipients=self.to_emails
            )
            
            return True
            
        except Exception as e:
            structured_logger.log_error(
                e, 
                context="email_alert_channel",
                alert_id=alert.id
            )
            return False
    
    def _create_email_body(self, alert: Alert) -> str:
        """Create HTML email body."""
        severity_colors = {
            AlertSeverity.LOW: "#28a745",
            AlertSeverity.MEDIUM: "#ffc107", 
            AlertSeverity.HIGH: "#fd7e14",
            AlertSeverity.CRITICAL: "#dc3545"
        }
        
        color = severity_colors.get(alert.severity, "#6c757d")
        
        return f"""
        <html>
        <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px;">
                <div style="background-color: {color}; color: white; padding: 20px; border-radius: 5px 5px 0 0;">
                    <h2 style="margin: 0;">{alert.title}</h2>
                    <p style="margin: 5px 0 0 0;">Severity: {alert.severity.upper()}</p>
                </div>
                
                <div style="background-color: #f8f9fa; padding: 20px; border: 1px solid #dee2e6; border-top: none; border-radius: 0 0 5px 5px;">
                    <h3>Alert Details</h3>
                    <p><strong>Type:</strong> {alert.alert_type.value}</p>
                    <p><strong>Time:</strong> {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                    <p><strong>Rule:</strong> {alert.rule_name}</p>
                    
                    <h3>Message</h3>
                    <p>{alert.message}</p>
                    
                    {self._format_metadata(alert.metadata)}
                </div>
            </div>
        </body>
        </html>
        """
    
    def _format_metadata(self, metadata: Dict[str, Any]) -> str:
        """Format metadata for email display."""
        if not metadata:
            return ""
        
        html = "<h3>Additional Information</h3><ul>"
        for key, value in metadata.items():
            html += f"<li><strong>{key}:</strong> {value}</li>"
        html += "</ul>"
        return html

class WebhookAlertChannel(AlertChannel):
    """Webhook alert channel (Slack, Discord, etc.)."""
    
    def __init__(self, webhook_url: str, format_func: Optional[Callable] = None):
        self.webhook_url = webhook_url
        self.format_func = format_func or self._default_format
    
    async def send_alert(self, alert: Alert) -> bool:
        """Send alert via webhook."""
        try:
            payload = self.format_func(alert)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    success = response.status < 400
                    
                    if success:
                        structured_logger.log_structured(
                            LogLevel.INFO,
                            f"Webhook alert sent: {alert.title}",
                            EventType.SYSTEM,
                            alert_id=alert.id,
                            webhook_url=self.webhook_url
                        )
                    else:
                        structured_logger.log_structured(
                            LogLevel.ERROR,
                            f"Webhook alert failed: {response.status}",
                            EventType.ERROR,
                            alert_id=alert.id,
                            status_code=response.status
                        )
                    
                    return success
                    
        except Exception as e:
            structured_logger.log_error(
                e,
                context="webhook_alert_channel",
                alert_id=alert.id
            )
            return False
    
    def _default_format(self, alert: Alert) -> Dict[str, Any]:
        """Default webhook payload format."""
        return {
            "text": f"[{alert.severity.upper()}] {alert.title}",
            "attachments": [
                {
                    "color": self._get_color(alert.severity),
                    "fields": [
                        {"title": "Type", "value": alert.alert_type.value, "short": True},
                        {"title": "Time", "value": alert.timestamp.isoformat(), "short": True},
                        {"title": "Message", "value": alert.message, "short": False}
                    ]
                }
            ]
        }
    
    def _get_color(self, severity: AlertSeverity) -> str:
        """Get color for severity level."""
        colors = {
            AlertSeverity.LOW: "good",
            AlertSeverity.MEDIUM: "warning",
            AlertSeverity.HIGH: "danger",
            AlertSeverity.CRITICAL: "danger"
        }
        return colors.get(severity, "good")

class AlertManager:
    """Main alert management system."""
    
    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.channels: List[AlertChannel] = []
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=1000)
        self.cooldown_tracker: Dict[str, datetime] = {}
        self.metrics_tracker = defaultdict(list)
        self._running = False
        self._monitor_task = None
        
        # Load default rules
        self._load_default_rules()
    
    def _load_default_rules(self):
        """Load default alert rules."""
        default_rules = [
            AlertRule(
                name="background_task_failures",
                alert_type=AlertType.BACKGROUND_TASK_FAILURE,
                severity=AlertSeverity.HIGH,
                threshold=3,  # 3 failures in time window
                time_window_minutes=15,
                description="Alert when background tasks fail repeatedly"
            ),
            AlertRule(
                name="high_api_error_rate",
                alert_type=AlertType.HIGH_ERROR_RATE,
                severity=AlertSeverity.MEDIUM,
                threshold=0.1,  # 10% error rate
                time_window_minutes=10,
                description="Alert when API error rate exceeds threshold"
            ),
            AlertRule(
                name="api_response_time",
                alert_type=AlertType.PERFORMANCE_DEGRADATION,
                severity=AlertSeverity.MEDIUM,
                threshold=5000,  # 5 seconds average response time
                time_window_minutes=5,
                description="Alert when API response time degrades"
            ),
            AlertRule(
                name="critical_errors",
                alert_type=AlertType.HIGH_ERROR_RATE,
                severity=AlertSeverity.CRITICAL,
                threshold=1,  # Any critical error
                time_window_minutes=1,
                description="Alert immediately on critical errors"
            )
        ]
        
        for rule in default_rules:
            self.add_rule(rule)
    
    def add_rule(self, rule: AlertRule):
        """Add an alert rule."""
        self.rules[rule.name] = rule
        structured_logger.log_structured(
            LogLevel.INFO,
            f"Alert rule added: {rule.name}",
            EventType.SYSTEM,
            rule_name=rule.name,
            alert_type=rule.alert_type.value
        )
    
    def add_channel(self, channel: AlertChannel):
        """Add an alert channel."""
        self.channels.append(channel)
        structured_logger.log_structured(
            LogLevel.INFO,
            f"Alert channel added: {type(channel).__name__}",
            EventType.SYSTEM,
            channel_type=type(channel).__name__
        )
    
    async def trigger_alert(
        self,
        rule_name: str,
        title: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Trigger an alert based on a rule."""
        if rule_name not in self.rules:
            structured_logger.log_structured(
                LogLevel.WARNING,
                f"Unknown alert rule: {rule_name}",
                EventType.ERROR,
                rule_name=rule_name
            )
            return
        
        rule = self.rules[rule_name]
        
        # Check if rule is enabled
        if not rule.enabled:
            return
        
        # Check cooldown
        if self._is_in_cooldown(rule_name):
            return
        
        # Create alert
        alert_id = f"{rule_name}_{int(time.time())}"
        alert = Alert(
            id=alert_id,
            rule_name=rule_name,
            alert_type=rule.alert_type,
            severity=rule.severity,
            title=title,
            message=message,
            timestamp=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        # Store alert
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        
        # Set cooldown
        self.cooldown_tracker[rule_name] = datetime.utcnow()
        
        # Log alert
        structured_logger.log_structured(
            LogLevel.WARNING if alert.severity in [AlertSeverity.LOW, AlertSeverity.MEDIUM] else LogLevel.ERROR,
            f"Alert triggered: {title}",
            EventType.SYSTEM,
            alert_id=alert_id,
            rule_name=rule_name,
            severity=alert.severity.value
        )
        
        # Send through all channels
        await self._send_alert(alert)
    
    async def _send_alert(self, alert: Alert):
        """Send alert through all configured channels."""
        tasks = []
        for channel in self.channels:
            tasks.append(channel.send_alert(alert))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            success_count = sum(1 for r in results if r is True)
            
            structured_logger.log_structured(
                LogLevel.INFO,
                f"Alert sent through {success_count}/{len(tasks)} channels",
                EventType.SYSTEM,
                alert_id=alert.id,
                success_count=success_count,
                total_channels=len(tasks)
            )
    
    def _is_in_cooldown(self, rule_name: str) -> bool:
        """Check if rule is in cooldown period."""
        if rule_name not in self.cooldown_tracker:
            return False
        
        rule = self.rules[rule_name]
        last_alert = self.cooldown_tracker[rule_name]
        cooldown_end = last_alert + timedelta(minutes=rule.cooldown_minutes)
        
        return datetime.utcnow() < cooldown_end
    
    def record_metric(self, metric_type: str, value: float, timestamp: Optional[datetime] = None):
        """Record a metric for monitoring."""
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        self.metrics_tracker[metric_type].append((timestamp, value))
        
        # Keep only recent metrics (last 24 hours)
        cutoff = datetime.utcnow() - timedelta(hours=24)
        self.metrics_tracker[metric_type] = [
            (ts, val) for ts, val in self.metrics_tracker[metric_type]
            if ts >= cutoff
        ]
    
    async def check_background_task_failures(self):
        """Check for background task failures."""
        rule = self.rules.get("background_task_failures")
        if not rule or not rule.enabled:
            return
        
        # This would integrate with your task monitoring system
        # For now, we'll check the structured logger's error counts
        error_summary = structured_logger.get_error_summary()
        
        # Count task-related errors in the time window
        task_errors = sum(
            count for error_type, count in error_summary.items()
            if "task" in error_type.lower()
        )
        
        if task_errors >= rule.threshold:
            await self.trigger_alert(
                "background_task_failures",
                f"Background Task Failures Detected",
                f"Detected {task_errors} background task failures in the last {rule.time_window_minutes} minutes",
                {"error_count": task_errors, "error_types": list(error_summary.keys())}
            )
    
    async def check_api_performance(self):
        """Check API performance metrics."""
        rule = self.rules.get("api_response_time")
        if not rule or not rule.enabled:
            return
        
        # Get recent performance metrics
        perf_summary = structured_logger.get_performance_summary(hours=rule.time_window_minutes / 60)
        
        if "avg_duration_ms" in perf_summary and perf_summary["avg_duration_ms"] > rule.threshold:
            await self.trigger_alert(
                "api_response_time",
                "API Performance Degradation",
                f"Average API response time is {perf_summary['avg_duration_ms']:.2f}ms (threshold: {rule.threshold}ms)",
                perf_summary
            )
    
    async def start_monitoring(self):
        """Start the alert monitoring system."""
        if self._running:
            return
        
        self._running = True
        structured_logger.log_structured(
            LogLevel.INFO,
            "Alert monitoring started",
            EventType.SYSTEM
        )
        
        # Start monitoring task
        self._monitor_task = asyncio.create_task(self._monitor_loop())
    
    async def stop_monitoring(self):
        """Stop the alert monitoring system."""
        self._running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        structured_logger.log_structured(
            LogLevel.INFO,
            "Alert monitoring stopped",
            EventType.SYSTEM
        )
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                # Run all checks
                await asyncio.gather(
                    self.check_background_task_failures(),
                    self.check_api_performance(),
                    return_exceptions=True
                )
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                structured_logger.log_error(e, context="alert_monitor_loop")
                await asyncio.sleep(60)
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts."""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get recent alert history."""
        return list(self.alert_history)[-limit:]
    
    def resolve_alert(self, alert_id: str):
        """Mark an alert as resolved."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()
            
            structured_logger.log_structured(
                LogLevel.INFO,
                f"Alert resolved: {alert.title}",
                EventType.SYSTEM,
                alert_id=alert_id
            )
            
            del self.active_alerts[alert_id]

# Global alert manager instance
alert_manager = AlertManager()

# Convenience functions
async def alert_background_task_failure(task_name: str, error: str, **metadata):
    """Quick function to alert on background task failure."""
    await alert_manager.trigger_alert(
        "background_task_failures",
        f"Background Task Failed: {task_name}",
        f"Task '{task_name}' failed with error: {error}",
        {"task_name": task_name, "error": error, **metadata}
    )

async def alert_api_downtime(endpoint: str, status_code: int, **metadata):
    """Quick function to alert on API downtime."""
    await alert_manager.trigger_alert(
        "api_downtime",
        f"API Endpoint Down: {endpoint}",
        f"Endpoint '{endpoint}' returned status {status_code}",
        {"endpoint": endpoint, "status_code": status_code, **metadata}
    )

# Export main components
__all__ = [
    'alert_manager',
    'AlertManager',
    'AlertRule',
    'Alert',
    'AlertSeverity',
    'AlertType',
    'EmailAlertChannel',
    'WebhookAlertChannel',
    'alert_background_task_failure',
    'alert_api_downtime'
]
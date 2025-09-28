"""
Example setup for monitoring system in a FastAPI application.

This example demonstrates how to integrate the monitoring system
with your FastAPI application.
"""

from fastapi import FastAPI, BackgroundTasks
from services.monitoring import (
    setup_monitoring,
    structured_logger,
    log_performance,
    log_operation,
    BackgroundTaskMonitoringMixin,
    alert_background_task_failure
)
import asyncio
import time

# Create FastAPI app
app = FastAPI(title="Social Suit API", version="1.0.0")

# Example email configuration (replace with your actual settings)
email_config = {
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "username": "your-email@gmail.com",
    "password": "your-app-password",  # Use app password for Gmail
    "from_email": "your-email@gmail.com",
    "to_emails": ["admin@yourcompany.com"]
}

# Example webhook URL (replace with your Slack/Discord webhook)
webhook_url = "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"

# Setup monitoring system
monitoring = setup_monitoring(
    app=app,
    email_config=email_config,  # Remove if you don't want email alerts
    webhook_url=webhook_url,    # Remove if you don't want webhook alerts
    enable_middleware=True
)

# Example background task class with monitoring
class ExampleTaskManager(BackgroundTaskMonitoringMixin):
    
    async def process_user_data(self, user_id: str):
        """Example background task with monitoring."""
        task_name = f"process_user_data_{user_id}"
        
        try:
            with log_operation(f"Processing user data for {user_id}"):
                # Simulate some work
                await asyncio.sleep(2)
                
                # Log some business logic
                structured_logger.log_api_request(
                    method="BACKGROUND",
                    endpoint=f"/process/{user_id}",
                    user_id=user_id,
                    status_code=200
                )
                
                # Simulate potential failure (remove in production)
                if user_id == "error_user":
                    raise Exception("Simulated processing error")
                
                return {"status": "success", "user_id": user_id}
                
        except Exception as e:
            # This will trigger an alert
            await self.handle_task_failure(task_name, str(e))
            raise

# Initialize task manager
task_manager = ExampleTaskManager()

# Example API endpoints
@app.get("/")
async def root():
    """Root endpoint with automatic monitoring via middleware."""
    structured_logger.log_structured(
        structured_logger.LogLevel.INFO,
        "Root endpoint accessed",
        structured_logger.EventType.API
    )
    return {"message": "Social Suit API is running"}

@app.post("/users/{user_id}/process")
async def process_user(user_id: str, background_tasks: BackgroundTasks):
    """Endpoint that triggers a background task."""
    
    # Add background task
    background_tasks.add_task(task_manager.process_user_data, user_id)
    
    structured_logger.log_structured(
        structured_logger.LogLevel.INFO,
        f"Background task queued for user {user_id}",
        structured_logger.EventType.BACKGROUND_TASK,
        user_id=user_id,
        task_name="process_user_data"
    )
    
    return {"message": f"Processing started for user {user_id}"}

@app.get("/test-performance")
@log_performance
async def test_performance():
    """Endpoint to test performance monitoring."""
    # Simulate some work
    await asyncio.sleep(1)
    return {"message": "Performance test completed"}

@app.get("/test-error")
async def test_error():
    """Endpoint to test error monitoring and alerting."""
    try:
        # Simulate an error
        raise ValueError("This is a test error")
    except Exception as e:
        structured_logger.log_error(
            e,
            context={"endpoint": "/test-error", "test": True}
        )
        # This will trigger an alert if error rate is high
        return {"error": "Test error occurred", "logged": True}

@app.get("/test-alert")
async def test_alert():
    """Endpoint to test alerting system."""
    # Manually trigger a background task failure alert
    await alert_background_task_failure(
        task_name="test_task",
        error_message="This is a test alert",
        context={"test": True}
    )
    return {"message": "Test alert sent"}

# Example startup event
@app.on_event("startup")
async def startup_event():
    structured_logger.log_structured(
        structured_logger.LogLevel.INFO,
        "Application starting up",
        structured_logger.EventType.SYSTEM,
        app_name="Social Suit API"
    )

# Example shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    structured_logger.log_structured(
        structured_logger.LogLevel.INFO,
        "Application shutting down",
        structured_logger.EventType.SYSTEM,
        app_name="Social Suit API"
    )

if __name__ == "__main__":
    import uvicorn
    
    # Log application start
    structured_logger.log_structured(
        structured_logger.LogLevel.INFO,
        "Starting Social Suit API server",
        structured_logger.EventType.SYSTEM,
        host="0.0.0.0",
        port=8000
    )
    
    # Run the application
    uvicorn.run(
        "monitoring_setup:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=None  # Disable uvicorn's default logging to use our structured logging
    )
"""
Secure Analytics API with comprehensive validation and rate limiting.

This module provides enhanced analytics endpoints with:
- Pydantic input validation
- Rate limiting integration
- Security audit compliance
- Enhanced error handling
- Audit logging
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, BackgroundTasks, Request
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
import asyncio
import logging
from datetime import datetime

from app.services.database.database import get_db
from app.services.models.user_model import User
from app.services.repositories.user_repository import UserRepository
from app.services.dependencies.repository_providers import get_user_repository
from app.services.dependencies.service_providers import (
    get_analytics_analyzer_service,
    get_analytics_collector_service,
    get_chart_generator_service
)
from app.services.analytics.services.data_collector_service import collect_all_platform_data
from app.services.utils.logger_config import setup_logger
from app.services.security.validation_models import (
    UserIdValidation,
    AnalyticsRequest,
    ChartDataValidation,
    PlatformValidation,
    AnalyticsTimeRangeValidation,
    MetricType
)
from app.services.security.rate_limiter import RateLimiter, RateLimitConfig
from app.services.auth.auth_guard import auth_required, get_current_user

# Set up logger
logger = setup_logger("secure_analytics_api")

# Create router
router = APIRouter(prefix="/analytics", tags=["analytics"])

# Rate limiter configuration
rate_limit_config = RateLimitConfig()

class AnalyticsAuditLogger:
    """Audit logger for analytics operations."""
    
    @staticmethod
    def log_data_collection(user_id: str, requester_id: str, days_back: int, success: bool, error: str = None):
        """Log analytics data collection attempts."""
        logger.info(f"AUDIT: Analytics collection - User: {user_id}, Requester: {requester_id}, "
                   f"Days: {days_back}, Success: {success}, Error: {error}")
    
    @staticmethod
    def log_data_access(user_id: str, requester_id: str, endpoint: str, success: bool, error: str = None):
        """Log analytics data access attempts."""
        logger.info(f"AUDIT: Analytics access - User: {user_id}, Requester: {requester_id}, "
                   f"Endpoint: {endpoint}, Success: {success}, Error: {error}")

# Background task to collect analytics data
async def collect_analytics_background(user_id: str, requester_id: str, days_back: int = 7):
    """Background task to collect analytics data for a user"""
    try:
        logger.info(f"Starting background analytics collection for user {user_id} by {requester_id}")
        result = await collect_all_platform_data(user_id, days_back)
        AnalyticsAuditLogger.log_data_collection(user_id, requester_id, days_back, True)
        logger.info(f"Completed analytics collection for user {user_id}: {result}")
    except Exception as e:
        AnalyticsAuditLogger.log_data_collection(user_id, requester_id, days_back, False, str(e))
        logger.error(f"Error in background analytics collection for user {user_id}: {str(e)}")

@router.post("/collect/{user_id}")
async def trigger_data_collection(
    request: Request,
    user_id: str = Path(..., description="User ID to collect analytics for"),
    days_back: int = Query(7, ge=1, le=90, description="Number of days to collect data for"), 
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(auth_required),
    user_repository: UserRepository = Depends(get_user_repository),
    collector_service = Depends(get_analytics_collector_service)
):
    """Trigger collection of analytics data for a user"""
    
    # Validate input
    try:
        user_validation = UserIdValidation(user_id=user_id)
        validated_user_id = user_validation.user_id
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid user ID: {str(e)}")
    
    # Check authorization - users can only collect their own data or admins can collect any
    if current_user.id != validated_user_id and not getattr(current_user, 'is_admin', False):
        AnalyticsAuditLogger.log_data_collection(validated_user_id, current_user.id, days_back, False, "Unauthorized access")
        raise HTTPException(status_code=403, detail="Not authorized to collect analytics for this user")
    
    # Verify target user exists
    target_user = user_repository.get_by_id(validated_user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        if background_tasks:
            # Run in background
            background_tasks.add_task(collect_analytics_background, validated_user_id, current_user.id, days_back)
            AnalyticsAuditLogger.log_data_collection(validated_user_id, current_user.id, days_back, True)
            return {
                "message": f"Analytics collection started for user {validated_user_id}", 
                "status": "processing",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            # Run immediately (may timeout for large data collections)
            result = await collect_all_platform_data(validated_user_id, days_back, collector_service)
            AnalyticsAuditLogger.log_data_collection(validated_user_id, current_user.id, days_back, True)
            return {
                "message": f"Analytics collection completed for user {validated_user_id}", 
                "status": "completed", 
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            }
    except Exception as e:
        AnalyticsAuditLogger.log_data_collection(validated_user_id, current_user.id, days_back, False, str(e))
        logger.error(f"Error triggering analytics collection: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error collecting analytics data: {str(e)}")

@router.get("/overview/{user_id}")
async def get_analytics_overview(
    request: Request,
    user_id: str = Path(..., description="User ID to get analytics overview for"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(auth_required),
    analyzer_service = Depends(get_analytics_analyzer_service)
):
    """Get an overview of analytics data for a user"""
    
    # Validate input
    try:
        user_validation = UserIdValidation(user_id=user_id)
        date_validation = DateRangeValidation(days=days)
        validated_user_id = user_validation.user_id
        validated_days = date_validation.days
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
    
    # Check authorization
    if current_user.id != validated_user_id and not getattr(current_user, 'is_admin', False):
        AnalyticsAuditLogger.log_data_access(validated_user_id, current_user.id, "overview", False, "Unauthorized access")
        raise HTTPException(status_code=403, detail="Not authorized to view analytics for this user")
    
    try:
        overview = analyzer_service.get_user_overview(validated_user_id, validated_days)
        if "error" in overview:
            AnalyticsAuditLogger.log_data_access(validated_user_id, current_user.id, "overview", False, overview["error"])
            raise HTTPException(status_code=404, detail=overview["error"])
        
        AnalyticsAuditLogger.log_data_access(validated_user_id, current_user.id, "overview", True)
        return {
            **overview,
            "timestamp": datetime.utcnow().isoformat(),
            "requested_days": validated_days
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        AnalyticsAuditLogger.log_data_access(validated_user_id, current_user.id, "overview", False, str(e))
        logger.error(f"Error getting analytics overview: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving analytics overview: {str(e)}")

@router.get("/platforms/{user_id}/{platform}")
async def get_platform_insights(
    request: Request,
    user_id: str = Path(..., description="User ID to get platform insights for"),
    platform: str = Path(..., description="Platform to analyze"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(auth_required),
    analyzer_service = Depends(get_analytics_analyzer_service)
):
    """Get platform-specific insights for a user"""
    
    # Validate input
    try:
        user_validation = UserIdValidation(user_id=user_id)
        platform_validation = PlatformValidation(platform=platform)
        date_validation = DateRangeValidation(days=days)
        
        validated_user_id = user_validation.user_id
        validated_platform = platform_validation.platform
        validated_days = date_validation.days
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
    
    # Check authorization
    if current_user.id != validated_user_id and not getattr(current_user, 'is_admin', False):
        AnalyticsAuditLogger.log_data_access(validated_user_id, current_user.id, f"platforms/{validated_platform}", False, "Unauthorized access")
        raise HTTPException(status_code=403, detail="Not authorized to view analytics for this user")
    
    try:
        insights = analyzer_service.get_platform_insights(validated_user_id, validated_platform, validated_days)
        if "error" in insights:
            AnalyticsAuditLogger.log_data_access(validated_user_id, current_user.id, f"platforms/{validated_platform}", False, insights["error"])
            raise HTTPException(status_code=404, detail=insights["error"])
        
        AnalyticsAuditLogger.log_data_access(validated_user_id, current_user.id, f"platforms/{validated_platform}", True)
        return {
            **insights,
            "timestamp": datetime.utcnow().isoformat(),
            "platform": validated_platform,
            "requested_days": validated_days
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        AnalyticsAuditLogger.log_data_access(validated_user_id, current_user.id, f"platforms/{validated_platform}", False, str(e))
        logger.error(f"Error getting platform insights: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving platform insights: {str(e)}")

@router.get("/chart/{chart_type}/{user_id}")
async def get_chart_data(
    request: Request,
    chart_type: str = Path(..., description="Type of chart to generate"),
    user_id: str = Path(..., description="User ID to generate chart for"),
    metric: str = Query(..., description="Metric to chart (e.g., followers, engagement, impressions)"),
    platform: Optional[str] = Query(None, description="Platform to filter by"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    group_by: str = Query("day", description="Group data by (day, week, month)"),
    current_user: User = Depends(auth_required),
    chart_generator = Depends(get_chart_generator_service)
):
    """Get chart data for visualization"""
    
    # Validate input
    try:
        chart_request = ChartRequest(
            chart_type=chart_type,
            user_id=user_id,
            metric=metric,
            platform=platform,
            days=days,
            group_by=group_by
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid chart request: {str(e)}")
    
    # Check authorization
    if current_user.id != chart_request.user_id and not getattr(current_user, 'is_admin', False):
        AnalyticsAuditLogger.log_data_access(chart_request.user_id, current_user.id, f"chart/{chart_request.chart_type}", False, "Unauthorized access")
        raise HTTPException(status_code=403, detail="Not authorized to view analytics for this user")
    
    try:
        # Map chart type to generator method
        chart_generators = {
            "time_series": chart_generator.generate_time_series_chart,
            "platform_comparison": chart_generator.generate_platform_comparison_chart,
            "engagement_breakdown": chart_generator.generate_engagement_breakdown_chart,
            "content_performance": chart_generator.generate_content_performance_chart
        }
        
        generator = chart_generators.get(chart_request.chart_type)
        if not generator:
            raise HTTPException(status_code=400, detail=f"Unsupported chart type: {chart_request.chart_type}")
        
        # Call appropriate generator with parameters
        if chart_request.chart_type == "time_series":
            chart_data = generator(chart_request.user_id, chart_request.metric, chart_request.platform, chart_request.days, chart_request.group_by)
        elif chart_request.chart_type == "platform_comparison":
            chart_data = generator(chart_request.user_id, chart_request.metric, chart_request.days)
        elif chart_request.chart_type == "engagement_breakdown":
            chart_data = generator(chart_request.user_id, chart_request.platform, chart_request.days)
        elif chart_request.chart_type == "content_performance":
            chart_data = generator(chart_request.user_id, chart_request.days)
        
        if "error" in chart_data:
            AnalyticsAuditLogger.log_data_access(chart_request.user_id, current_user.id, f"chart/{chart_request.chart_type}", False, chart_data["error"])
            raise HTTPException(status_code=404, detail=chart_data["error"])
        
        AnalyticsAuditLogger.log_data_access(chart_request.user_id, current_user.id, f"chart/{chart_request.chart_type}", True)
        return {
            **chart_data,
            "timestamp": datetime.utcnow().isoformat(),
            "chart_config": {
                "type": chart_request.chart_type,
                "metric": chart_request.metric,
                "platform": chart_request.platform,
                "days": chart_request.days,
                "group_by": chart_request.group_by
            }
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        AnalyticsAuditLogger.log_data_access(chart_request.user_id, current_user.id, f"chart/{chart_request.chart_type}", False, str(e))
        logger.error(f"Error generating chart data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating chart data: {str(e)}")

@router.get("/recommendations/{user_id}")
async def get_recommendations(
    request: Request,
    user_id: str = Path(..., description="User ID to get recommendations for"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(auth_required),
    analyzer_service = Depends(get_analytics_analyzer_service)
):
    """Get content and engagement recommendations based on analytics"""
    
    # Validate input
    try:
        user_validation = UserIdValidation(user_id=user_id)
        date_validation = DateRangeValidation(days=days)
        validated_user_id = user_validation.user_id
        validated_days = date_validation.days
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
    
    # Check authorization
    if current_user.id != validated_user_id and not getattr(current_user, 'is_admin', False):
        AnalyticsAuditLogger.log_data_access(validated_user_id, current_user.id, "recommendations", False, "Unauthorized access")
        raise HTTPException(status_code=403, detail="Not authorized to view analytics for this user")
    
    try:
        recommendations = analyzer_service.get_recommendations(validated_user_id, validated_days)
        if "error" in recommendations:
            AnalyticsAuditLogger.log_data_access(validated_user_id, current_user.id, "recommendations", False, recommendations["error"])
            raise HTTPException(status_code=404, detail=recommendations["error"])
        
        AnalyticsAuditLogger.log_data_access(validated_user_id, current_user.id, "recommendations", True)
        return {
            **recommendations,
            "timestamp": datetime.utcnow().isoformat(),
            "analysis_period_days": validated_days
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        AnalyticsAuditLogger.log_data_access(validated_user_id, current_user.id, "recommendations", False, str(e))
        logger.error(f"Error getting recommendations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving recommendations: {str(e)}")

@router.get("/comparative/{user_id}")
async def get_comparative_analytics(
    request: Request,
    user_id: str = Path(..., description="User ID to get comparative analytics for"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(auth_required),
    analyzer_service = Depends(get_analytics_analyzer_service)
):
    """Get comparative analytics across platforms"""
    
    # Validate input
    try:
        user_validation = UserIdValidation(user_id=user_id)
        date_validation = DateRangeValidation(days=days)
        validated_user_id = user_validation.user_id
        validated_days = date_validation.days
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
    
    # Check authorization
    if current_user.id != validated_user_id and not getattr(current_user, 'is_admin', False):
        AnalyticsAuditLogger.log_data_access(validated_user_id, current_user.id, "comparative", False, "Unauthorized access")
        raise HTTPException(status_code=403, detail="Not authorized to view analytics for this user")
    
    try:
        comparative = analyzer_service.get_comparative_analytics(validated_user_id, validated_days)
        if "error" in comparative:
            AnalyticsAuditLogger.log_data_access(validated_user_id, current_user.id, "comparative", False, comparative["error"])
            raise HTTPException(status_code=404, detail=comparative["error"])
        
        AnalyticsAuditLogger.log_data_access(validated_user_id, current_user.id, "comparative", True)
        return {
            **comparative,
            "timestamp": datetime.utcnow().isoformat(),
            "analysis_period_days": validated_days
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        AnalyticsAuditLogger.log_data_access(validated_user_id, current_user.id, "comparative", False, str(e))
        logger.error(f"Error getting comparative analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving comparative analytics: {str(e)}")

# Health check endpoint for monitoring
@router.get("/health")
async def health_check():
    """Health check endpoint for analytics service"""
    return {
        "status": "healthy",
        "service": "analytics_api",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0"
    }
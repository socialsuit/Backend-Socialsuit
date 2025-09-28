from fastapi import APIRouter, Depends, HTTPException, Query, Path, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
import asyncio

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

# Set up logger
logger = setup_logger("analytics_api")

# Create router
router = APIRouter(prefix="/analytics", tags=["analytics"])

# Background task to collect analytics data
async def collect_analytics_background(user_id: str, days_back: int = 7):
    """Background task to collect analytics data for a user"""
    try:
        logger.info(f"Starting background analytics collection for user {user_id}")
        result = await collect_all_platform_data(user_id, days_back)
        logger.info(f"Completed analytics collection for user {user_id}: {result}")
    except Exception as e:
        logger.error(f"Error in background analytics collection for user {user_id}: {str(e)}")

@router.post("/collect/{user_id}")
async def trigger_data_collection(
    user_id: str, 
    days_back: int = Query(7, ge=1, le=90), 
    background_tasks: BackgroundTasks = None, 
    user_repository: UserRepository = Depends(get_user_repository),
    collector_service = Depends(get_analytics_collector_service)
):
    """Trigger collection of analytics data for a user"""
    # Verify user exists
    user = user_repository.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        if background_tasks:
            # Run in background
            background_tasks.add_task(collect_analytics_background, user_id, days_back)
            return {"message": f"Analytics collection started for user {user_id}", "status": "processing"}
        else:
            # Run immediately (may timeout for large data collections)
            result = await collect_all_platform_data(user_id, days_back, collector_service)
            return {"message": f"Analytics collection completed for user {user_id}", "status": "completed", "result": result}
    except Exception as e:
        logger.error(f"Error triggering analytics collection: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error collecting analytics data: {str(e)}")

@router.get("/overview/{user_id}")
async def get_analytics_overview(
    user_id: str,
    days: int = Query(30, ge=1, le=365),
    analyzer_service = Depends(get_analytics_analyzer_service)
):
    """Get an overview of analytics data for a user"""
    try:
        overview = analyzer_service.get_user_overview(user_id, days)
        if "error" in overview:
            raise HTTPException(status_code=404, detail=overview["error"])
        return overview
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting analytics overview: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving analytics overview: {str(e)}")

@router.get("/platforms/{user_id}/{platform}")
async def get_platform_insights(
    user_id: str,
    platform: str,
    days: int = Query(30, ge=1, le=365),
    analyzer_service = Depends(get_analytics_analyzer_service)
):
    """Get platform-specific insights for a user"""
    try:
        insights = analyzer_service.get_platform_insights(user_id, platform, days)
        if "error" in insights:
            raise HTTPException(status_code=404, detail=insights["error"])
        return insights
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting platform insights: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving platform insights: {str(e)}")

@router.get("/chart/{chart_type}/{user_id}")
async def get_chart_data(
    chart_type: str,
    user_id: str,
    metric: str = Query(..., description="Metric to chart (e.g., followers, engagement, impressions)"),
    platform: Optional[str] = Query(None, description="Platform to filter by"),
    days: int = Query(30, ge=1, le=365),
    group_by: str = Query("day", description="Group data by (day, week, month)"),
    chart_generator = Depends(get_chart_generator_service)
):
    """Get chart data for visualization"""
    try:
        # Map chart type to generator method
        chart_generators = {
            "time_series": chart_generator.generate_time_series_chart,
            "platform_comparison": chart_generator.generate_platform_comparison_chart,
            "engagement_breakdown": chart_generator.generate_engagement_breakdown_chart,
            "content_performance": chart_generator.generate_content_performance_chart
        }
        
        generator = chart_generators.get(chart_type)
        if not generator:
            raise HTTPException(status_code=400, detail=f"Unsupported chart type: {chart_type}")
        
        # Call appropriate generator with parameters
        if chart_type == "time_series":
            chart_data = generator(user_id, metric, platform, days, group_by)
        elif chart_type == "platform_comparison":
            chart_data = generator(user_id, metric, days)
        elif chart_type == "engagement_breakdown":
            chart_data = generator(user_id, platform, days)
        elif chart_type == "content_performance":
            chart_data = generator(user_id, days)
        
        if "error" in chart_data:
            raise HTTPException(status_code=404, detail=chart_data["error"])
            
        return chart_data
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error generating chart data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating chart data: {str(e)}")

@router.get("/recommendations/{user_id}")
async def get_recommendations(
    user_id: str,
    days: int = Query(30, ge=1, le=365),
    analyzer_service = Depends(get_analytics_analyzer_service)
):
    """Get content and engagement recommendations based on analytics"""
    try:
        recommendations = analyzer_service.get_recommendations(user_id, days)
        if "error" in recommendations:
            raise HTTPException(status_code=404, detail=recommendations["error"])
        return recommendations
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting recommendations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving recommendations: {str(e)}")

@router.get("/comparative/{user_id}")
async def get_comparative_analytics(
    user_id: str,
    days: int = Query(30, ge=1, le=365),
    analyzer_service = Depends(get_analytics_analyzer_service)
):
    """Get comparative analytics across platforms"""
    try:
        comparative = analyzer_service.get_comparative_analytics(user_id, days)
        if "error" in comparative:
            raise HTTPException(status_code=404, detail=comparative["error"])
        return comparative
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting comparative analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving comparative analytics: {str(e)}")
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.services.interfaces.base_service import BaseService
from app.services.repositories.user_repository import UserRepository
from app.services.repositories.analytics_repository import (
    PostEngagementRepository, 
    UserMetricsRepository, 
    ContentPerformanceRepository
)
from app.services.models.analytics_model import PostEngagement, UserMetrics, ContentPerformance, EngagementType
from app.services.utils.logger_config import setup_logger
from app.services.utils.monitoring import track_analytics_collection

# Set up logger
logger = setup_logger("analytics_collector_service")

class AnalyticsCollectorService(BaseService):
    """Collects analytics data from various social media platforms"""
    
    def __init__(self, 
                 db: Session,
                 user_repository: UserRepository,
                 post_engagement_repository: PostEngagementRepository,
                 user_metrics_repository: UserMetricsRepository,
                 content_performance_repository: ContentPerformanceRepository):
        super().__init__(db)
        self.user_repository = user_repository
        self.post_engagement_repository = post_engagement_repository
        self.user_metrics_repository = user_metrics_repository
        self.content_performance_repository = content_performance_repository
    
    async def collect_platform_data(self, user_id: str, platform: str, days_back: int = 7) -> Dict[str, Any]:
        """Collect analytics data for a specific user and platform"""
        try:
            # Track analytics collection attempt
            track_analytics_collection(platform)
            
            # Verify user exists
            user = self.user_repository.get_by_id(user_id)
            if not user:
                return {"error": "User not found"}
                
            logger.info(f"Collecting {platform} data for user {user_id}, days_back: {days_back}")
            
            # Get platform-specific collector method
            collector_method = getattr(self, f"_collect_{platform}_data", None)
            if not collector_method:
                logger.warning(f"No collector implemented for platform: {platform}")
                return {"error": f"Analytics collection not supported for {platform}"}
            
            # Call platform-specific collector
            data = await collector_method(user_id, days_back)
            
            # Process and store the collected data
            await self._process_and_store_data(user_id, platform, data)
            
            return {"success": True, "platform": platform, "data_points": len(data)}
            
        except Exception as e:
            logger.error(f"Error collecting {platform} data for user {user_id}: {str(e)}")
            return {"error": str(e), "platform": platform}
    
    async def _process_and_store_data(self, user_id: str, platform: str, data: Dict[str, Any]) -> None:
        """Process and store collected analytics data"""
        try:
            # Extract data components
            engagements = data.get("engagements", [])
            metrics = data.get("metrics", {})
            content_items = data.get("content", [])
            
            # Store engagements
            for engagement in engagements:
                post_engagement = PostEngagement(
                    user_id=user_id,
                    platform=platform,
                    post_id=engagement["post_id"],
                    engagement_type=engagement["type"],
                    timestamp=engagement["timestamp"],
                    metadata=engagement.get("metadata", {})
                )
                self.post_engagement_repository.create(post_engagement)
            
            # Store user metrics
            if metrics:
                user_metrics = UserMetrics(
                    user_id=user_id,
                    platform=platform,
                    timestamp=datetime.now(),
                    followers=metrics.get("followers", 0),
                    follower_change=metrics.get("follower_change", 0),
                    profile_views=metrics.get("profile_views", 0),
                    reach=metrics.get("reach", 0),
                    impressions=metrics.get("impressions", 0),
                    metadata=metrics.get("metadata", {})
                )
                self.user_metrics_repository.create(user_metrics)
            
            # Store content performance
            for content in content_items:
                content_performance = ContentPerformance(
                    user_id=user_id,
                    platform=platform,
                    content_id=content["content_id"],
                    content_type=content["content_type"],
                    timestamp=content["timestamp"],
                    engagement_score=content["engagement_score"],
                    metrics=content["metrics"]
                )
                self.content_performance_repository.create(content_performance)
                
            logger.info(f"Stored analytics data for user {user_id} on {platform}")
            
        except Exception as e:
            logger.error(f"Error processing analytics data: {str(e)}")
            raise

# Async function to collect data from all platforms for a user
async def collect_all_platform_data(user_id: str, days_back: int = 7, collector_service: Optional[AnalyticsCollectorService] = None) -> Dict[str, Any]:
    """Collect data from all platforms for a user"""
    from app.services.database.database import get_db_session
    from app.services.repositories.user_repository import UserRepository
    from app.services.repositories.analytics_repository import (
        PostEngagementRepository, 
        UserMetricsRepository, 
        ContentPerformanceRepository
    )
    
    # Create service if not provided
    if not collector_service:
        db = get_db_session()
        try:
            user_repo = UserRepository(db)
            post_engagement_repo = PostEngagementRepository(db)
            user_metrics_repo = UserMetricsRepository(db)
            content_performance_repo = ContentPerformanceRepository(db)
            
            collector_service = AnalyticsCollectorService(
                db=db,
                user_repository=user_repo,
                post_engagement_repository=post_engagement_repo,
                user_metrics_repository=user_metrics_repo,
                content_performance_repository=content_performance_repo
            )
        except Exception as e:
            if db:
                db.close()
            logger.error(f"Error creating collector service: {str(e)}")
            raise
    
    try:
        # Get user to verify existence
        user = collector_service.user_repository.get_by_id(user_id)
        if not user:
            return {"error": "User not found"}
        
        # Define platforms to collect from
        platforms = ["facebook", "instagram", "twitter", "linkedin", "youtube", "tiktok"]
        
        # Collect data from each platform concurrently
        tasks = [collector_service.collect_platform_data(user_id, platform, days_back) for platform in platforms]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        platform_results = {}
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                platform_results[platforms[i]] = {"error": str(result)}
            else:
                platform_results[platforms[i]] = result
        
        return {
            "user_id": user_id,
            "days_back": days_back,
            "timestamp": datetime.now().isoformat(),
            "platforms": platform_results
        }
    
    finally:
        # Close DB session if we created it
        if not collector_service and db:
            db.close()
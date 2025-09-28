from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_

from app.services.interfaces.base_service import BaseService
from app.services.repositories.user_repository import UserRepository
from app.services.repositories.analytics_repository import (
    PostEngagementRepository, 
    UserMetricsRepository, 
    ContentPerformanceRepository
)
from app.services.models.analytics_model import PostEngagement, UserMetrics, ContentPerformance, EngagementType
from app.services.utils.logger_config import setup_logger

# Set up logger
logger = setup_logger("analytics_analyzer_service")

class AnalyticsAnalyzerService(BaseService):
    """Analyzes collected analytics data to generate insights"""
    
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
    
    def get_user_overview(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get an overview of user analytics across all platforms"""
        try:
            # Verify user exists
            user = self.user_repository.get_by_id(user_id)
            if not user:
                return {"error": "User not found"}
                
            start_date = datetime.now() - timedelta(days=days)
            
            # Get platforms the user is active on
            platforms = self._get_user_platforms(user_id)
            
            # Get metrics for each platform
            platform_metrics = {}
            total_followers = 0
            total_engagement = 0
            
            for platform in platforms:
                metrics = self._get_platform_metrics(user_id, platform, start_date)
                platform_metrics[platform] = metrics
                
                # Add to totals
                total_followers += metrics.get("current_followers", 0)
                total_engagement += metrics.get("total_engagements", 0)
            
            # Get top performing content
            top_content = self._get_top_performing_content(user_id, start_date, limit=5)
            
            # Calculate engagement rate
            engagement_rate = 0
            if total_followers > 0:
                engagement_rate = (total_engagement / total_followers) * 100
            
            return {
                "user_id": user_id,
                "period_days": days,
                "total_followers": total_followers,
                "total_engagement": total_engagement,
                "engagement_rate": round(engagement_rate, 2),
                "platforms": platforms,
                "platform_metrics": platform_metrics,
                "top_content": top_content
            }
            
        except Exception as e:
            logger.error(f"Error getting user overview: {str(e)}")
            return {"error": str(e)}
    
    def _get_user_platforms(self, user_id: str) -> List[str]:
        """Get the list of platforms a user is active on"""
        # Get distinct platforms from user metrics
        metrics = self.user_metrics_repository.get_metrics_history(user_id)
        platforms = set(metric.platform for metric in metrics)
        return list(platforms)
    
    def _get_platform_metrics(self, user_id: str, platform: str, start_date: datetime) -> Dict[str, Any]:
        """Get metrics for a specific platform"""
        # Get latest metrics for the platform
        latest_metrics = self.user_metrics_repository.get_latest_by_user_id(user_id, platform)
        
        # Get engagement counts
        engagement_counts = self.post_engagement_repository.get_engagement_counts(user_id, days=(datetime.now() - start_date).days)
        
        # Get content performance
        content_items = self.content_performance_repository.get_by_platform(user_id, platform, days=(datetime.now() - start_date).days)
        
        # Calculate metrics
        total_engagements = sum(count for engagement_type, count in engagement_counts.items())
        
        return {
            "platform": platform,
            "current_followers": latest_metrics.followers if latest_metrics else 0,
            "follower_change": latest_metrics.follower_change if latest_metrics else 0,
            "total_engagements": total_engagements,
            "engagement_breakdown": engagement_counts,
            "content_count": len(content_items)
        }
    
    def _get_top_performing_content(self, user_id: str, start_date: datetime, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top performing content items"""
        top_content = self.content_performance_repository.get_top_performing(user_id, days=(datetime.now() - start_date).days, limit=limit)
        
        return [
            {
                "content_id": str(content.content_id),
                "platform": content.platform,
                "content_type": content.content_type,
                "engagement_score": content.engagement_score,
                "timestamp": content.timestamp.isoformat(),
                "metrics": content.metrics
            }
            for content in top_content
        ]
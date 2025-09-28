from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc, and_, or_, text, case
from datetime import datetime, timedelta
import asyncio

from app.services.interfaces.base_repository import BaseRepository
from app.services.models.analytics_models import PostEngagement, UserMetrics, ContentPerformance
from app.services.database.query_optimizer import query_performance_tracker
from app.services.database.redis import RedisManager

class PostEngagementRepository(BaseRepository[PostEngagement]):
    """
    Optimized Repository for PostEngagement entity operations with caching and performance monitoring
    """
    def __init__(self, db: Session):
        super().__init__(db, PostEngagement)
    
    @query_performance_tracker("postgresql", "get_by_user_and_platform")
    def get_by_user_and_platform(self, user_id: str, platform: str, limit: int = 100, offset: int = 0) -> List[PostEngagement]:
        """
        Get engagement data for a specific user and platform with pagination
        """
        cache_key = f"engagement:user_platform:{user_id}:{platform}:{limit}:{offset}"
        
        result = (self.db.query(PostEngagement)
                 .filter(and_(
                     PostEngagement.user_id == user_id, 
                     PostEngagement.platform == platform
                 ))
                 .order_by(desc(PostEngagement.created_at))
                 .limit(limit)
                 .offset(offset)
                 .all())
        
        return result
    
    @query_performance_tracker("postgresql", "get_engagement_count")
    def get_engagement_count(self, user_id: str, start_date: datetime, end_date: datetime) -> int:
        """
        Get total engagement count for a user within a date range with caching
        """
        cache_key = f"engagement:count:{user_id}:{start_date.date()}:{end_date.date()}"
        
        result = self.db.query(func.sum(PostEngagement.total_engagement)).filter(
            and_(
                PostEngagement.user_id == user_id,
                PostEngagement.created_at >= start_date,
                PostEngagement.created_at <= end_date
            )
        ).scalar()
        
        return result or 0
    
    @query_performance_tracker("postgresql", "get_engagement_trends")
    def get_engagement_trends(self, user_id: str, days: int = 30, platform: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get engagement trends over time with aggregation
        """
        cache_key = f"engagement:trends:{user_id}:{days}:{platform or 'all'}"
        
        start_date = datetime.now() - timedelta(days=days)
        
        query = (self.db.query(
                    func.date(PostEngagement.created_at).label('date'),
                    func.sum(PostEngagement.total_engagement).label('total_engagement'),
                    func.avg(PostEngagement.engagement_rate).label('avg_engagement_rate'),
                    func.count(PostEngagement.id).label('post_count')
                )
                .filter(and_(
                    PostEngagement.user_id == user_id,
                    PostEngagement.created_at >= start_date
                ))
                .group_by(func.date(PostEngagement.created_at))
                .order_by(asc(func.date(PostEngagement.created_at))))
        
        if platform:
            query = query.filter(PostEngagement.platform == platform)
        
        results = query.all()
        
        return [
            {
                'date': result.date,
                'total_engagement': result.total_engagement or 0,
                'avg_engagement_rate': float(result.avg_engagement_rate or 0),
                'post_count': result.post_count
            }
            for result in results
        ]
    
    @query_performance_tracker("postgresql", "get_platform_performance")
    def get_platform_performance(self, user_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get performance metrics by platform
        """
        cache_key = f"engagement:platform_performance:{user_id}:{days}"
        
        start_date = datetime.now() - timedelta(days=days)
        
        results = (self.db.query(
                      PostEngagement.platform,
                      func.sum(PostEngagement.total_engagement).label('total_engagement'),
                      func.avg(PostEngagement.engagement_rate).label('avg_engagement_rate'),
                      func.count(PostEngagement.id).label('post_count'),
                      func.max(PostEngagement.total_engagement).label('best_engagement')
                  )
                  .filter(and_(
                      PostEngagement.user_id == user_id,
                      PostEngagement.created_at >= start_date
                  ))
                  .group_by(PostEngagement.platform)
                  .order_by(desc('total_engagement'))
                  .all())
        
        return [
            {
                'platform': result.platform,
                'total_engagement': result.total_engagement or 0,
                'avg_engagement_rate': float(result.avg_engagement_rate or 0),
                'post_count': result.post_count,
                'best_engagement': result.best_engagement or 0
            }
            for result in results
        ]

class UserMetricsRepository(BaseRepository[UserMetrics]):
    """
    Optimized Repository for UserMetrics entity operations with caching and performance monitoring
    """
    def __init__(self, db: Session):
        super().__init__(db, UserMetrics)
    
    @query_performance_tracker("postgresql", "get_latest_metrics")
    def get_latest_metrics(self, user_id: str) -> Optional[UserMetrics]:
        """
        Get the latest metrics for a user with caching
        """
        cache_key = f"metrics:latest:{user_id}"
        
        result = (self.db.query(UserMetrics)
                 .filter(UserMetrics.user_id == user_id)
                 .order_by(desc(UserMetrics.created_at))
                 .first())
        
        return result
    
    @query_performance_tracker("postgresql", "get_metrics_history")
    def get_metrics_history(self, user_id: str, days: int = 30, limit: int = 100) -> List[UserMetrics]:
        """
        Get metrics history for a user over the last N days with pagination
        """
        cache_key = f"metrics:history:{user_id}:{days}:{limit}"
        
        start_date = datetime.now() - timedelta(days=days)
        
        result = (self.db.query(UserMetrics)
                 .filter(and_(
                     UserMetrics.user_id == user_id,
                     UserMetrics.created_at >= start_date
                 ))
                 .order_by(desc(UserMetrics.created_at))
                 .limit(limit)
                 .all())
        
        return result
    
    @query_performance_tracker("postgresql", "get_metrics_comparison")
    def get_metrics_comparison(self, user_id: str, current_days: int = 30, previous_days: int = 30) -> Dict[str, Any]:
        """
        Compare metrics between two time periods
        """
        cache_key = f"metrics:comparison:{user_id}:{current_days}:{previous_days}"
        
        current_end = datetime.now()
        current_start = current_end - timedelta(days=current_days)
        previous_end = current_start
        previous_start = previous_end - timedelta(days=previous_days)
        
        # Current period metrics
        current_metrics = (self.db.query(
                              func.avg(UserMetrics.follower_count).label('avg_followers'),
                              func.avg(UserMetrics.engagement_rate).label('avg_engagement'),
                              func.sum(UserMetrics.total_posts).label('total_posts')
                          )
                          .filter(and_(
                              UserMetrics.user_id == user_id,
                              UserMetrics.created_at >= current_start,
                              UserMetrics.created_at <= current_end
                          ))
                          .first())
        
        # Previous period metrics
        previous_metrics = (self.db.query(
                               func.avg(UserMetrics.follower_count).label('avg_followers'),
                               func.avg(UserMetrics.engagement_rate).label('avg_engagement'),
                               func.sum(UserMetrics.total_posts).label('total_posts')
                           )
                           .filter(and_(
                               UserMetrics.user_id == user_id,
                               UserMetrics.created_at >= previous_start,
                               UserMetrics.created_at <= previous_end
                           ))
                           .first())
        
        # Calculate growth rates
        def calculate_growth(current, previous):
            if previous and previous > 0:
                return ((current - previous) / previous) * 100
            return 0
        
        current_followers = current_metrics.avg_followers or 0
        previous_followers = previous_metrics.avg_followers or 0
        current_engagement = current_metrics.avg_engagement or 0
        previous_engagement = previous_metrics.avg_engagement or 0
        
        return {
            'current_period': {
                'avg_followers': current_followers,
                'avg_engagement': current_engagement,
                'total_posts': current_metrics.total_posts or 0
            },
            'previous_period': {
                'avg_followers': previous_followers,
                'avg_engagement': previous_engagement,
                'total_posts': previous_metrics.total_posts or 0
            },
            'growth_rates': {
                'follower_growth': calculate_growth(current_followers, previous_followers),
                'engagement_growth': calculate_growth(current_engagement, previous_engagement)
            }
        }

class ContentPerformanceRepository(BaseRepository[ContentPerformance]):
    """
    Optimized Repository for ContentPerformance entity operations with caching and performance monitoring
    """
    def __init__(self, db: Session):
        super().__init__(db, ContentPerformance)
    
    @query_performance_tracker("postgresql", "get_top_performing_content")
    def get_top_performing_content(self, user_id: str, limit: int = 10, platform: Optional[str] = None, 
                                  days: Optional[int] = None) -> List[ContentPerformance]:
        """
        Get top performing content for a user with enhanced filtering
        """
        cache_key = f"content:top:{user_id}:{limit}:{platform or 'all'}:{days or 'all'}"
        
        query = self.db.query(ContentPerformance).filter(ContentPerformance.user_id == user_id)
        
        if platform:
            query = query.filter(ContentPerformance.platform == platform)
        
        if days:
            start_date = datetime.now() - timedelta(days=days)
            query = query.filter(ContentPerformance.created_at >= start_date)
        
        result = (query.order_by(desc(ContentPerformance.engagement_rate))
                 .limit(limit)
                 .all())
        
        return result
    
    @query_performance_tracker("postgresql", "get_content_analytics")
    def get_content_analytics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get comprehensive content analytics
        """
        cache_key = f"content:analytics:{user_id}:{days}"
        
        start_date = datetime.now() - timedelta(days=days)
        
        # Basic statistics
        basic_stats = (self.db.query(
                          func.count(ContentPerformance.id).label('total_content'),
                          func.avg(ContentPerformance.engagement_rate).label('avg_engagement_rate'),
                          func.max(ContentPerformance.engagement_rate).label('best_engagement_rate'),
                          func.min(ContentPerformance.engagement_rate).label('worst_engagement_rate')
                      )
                      .filter(and_(
                          ContentPerformance.user_id == user_id,
                          ContentPerformance.created_at >= start_date
                      ))
                      .first())
        
        # Content type performance
        content_type_stats = (self.db.query(
                                 ContentPerformance.content_type,
                                 func.count(ContentPerformance.id).label('count'),
                                 func.avg(ContentPerformance.engagement_rate).label('avg_engagement')
                             )
                             .filter(and_(
                                 ContentPerformance.user_id == user_id,
                                 ContentPerformance.created_at >= start_date
                             ))
                             .group_by(ContentPerformance.content_type)
                             .order_by(desc('avg_engagement'))
                             .all())
        
        # Platform performance
        platform_stats = (self.db.query(
                              ContentPerformance.platform,
                              func.count(ContentPerformance.id).label('count'),
                              func.avg(ContentPerformance.engagement_rate).label('avg_engagement')
                          )
                          .filter(and_(
                              ContentPerformance.user_id == user_id,
                              ContentPerformance.created_at >= start_date
                          ))
                          .group_by(ContentPerformance.platform)
                          .order_by(desc('avg_engagement'))
                          .all())
        
        return {
            'basic_stats': {
                'total_content': basic_stats.total_content or 0,
                'avg_engagement_rate': float(basic_stats.avg_engagement_rate or 0),
                'best_engagement_rate': float(basic_stats.best_engagement_rate or 0),
                'worst_engagement_rate': float(basic_stats.worst_engagement_rate or 0)
            },
            'content_type_performance': [
                {
                    'content_type': stat.content_type,
                    'count': stat.count,
                    'avg_engagement': float(stat.avg_engagement or 0)
                }
                for stat in content_type_stats
            ],
            'platform_performance': [
                {
                    'platform': stat.platform,
                    'count': stat.count,
                    'avg_engagement': float(stat.avg_engagement or 0)
                }
                for stat in platform_stats
            ]
        }
    
    @query_performance_tracker("postgresql", "get_content_recommendations")
    def get_content_recommendations(self, user_id: str, limit: int = 5) -> Dict[str, Any]:
        """
        Get content recommendations based on performance data
        """
        cache_key = f"content:recommendations:{user_id}:{limit}"
        
        # Find best performing content types
        best_content_types = (self.db.query(
                                 ContentPerformance.content_type,
                                 func.avg(ContentPerformance.engagement_rate).label('avg_engagement')
                             )
                             .filter(ContentPerformance.user_id == user_id)
                             .group_by(ContentPerformance.content_type)
                             .order_by(desc('avg_engagement'))
                             .limit(limit)
                             .all())
        
        # Find best performing platforms
        best_platforms = (self.db.query(
                             ContentPerformance.platform,
                             func.avg(ContentPerformance.engagement_rate).label('avg_engagement')
                         )
                         .filter(ContentPerformance.user_id == user_id)
                         .group_by(ContentPerformance.platform)
                         .order_by(desc('avg_engagement'))
                         .limit(limit)
                         .all())
        
        # Find optimal posting times (if timestamp data is available)
        optimal_times = (self.db.query(
                            func.extract('hour', ContentPerformance.created_at).label('hour'),
                            func.avg(ContentPerformance.engagement_rate).label('avg_engagement')
                        )
                        .filter(ContentPerformance.user_id == user_id)
                        .group_by(func.extract('hour', ContentPerformance.created_at))
                        .order_by(desc('avg_engagement'))
                        .limit(5)
                        .all())
        
        return {
            'recommended_content_types': [
                {
                    'content_type': ct.content_type,
                    'avg_engagement': float(ct.avg_engagement or 0)
                }
                for ct in best_content_types
            ],
            'recommended_platforms': [
                {
                    'platform': p.platform,
                    'avg_engagement': float(p.avg_engagement or 0)
                }
                for p in best_platforms
            ],
            'optimal_posting_hours': [
                {
                    'hour': int(ot.hour),
                    'avg_engagement': float(ot.avg_engagement or 0)
                }
                for ot in optimal_times
            ]
        }
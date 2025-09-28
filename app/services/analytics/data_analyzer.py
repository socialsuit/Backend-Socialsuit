import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_

from app.services.database.database import get_db_session
from app.services.models.analytics_model import PostEngagement, UserMetrics, ContentPerformance, EngagementType
from app.services.models.user_model import User
from app.services.utils.logger_config import setup_logger
from app.services.interfaces.base_services import BaseService
from app.services.database.query_optimizer import query_performance_tracker
from app.services.database.redis import RedisManager
import asyncio

class AnalyticsAnalyzer:
    """Analyzes collected analytics data to generate insights"""
    def __init__(self, db: Optional[Session] = None):
        self.db = db or get_db_session()
        self.redis_manager = RedisManager()
        self.logger = logging.getLogger(__name__)

    @query_performance_tracker("postgresql", "get_user_overview")
    async def get_user_overview(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Get comprehensive user analytics overview with caching
        """
        cache_key = f"analytics:overview:{user_id}:{days}"
        
        # Check cache first
        cached_overview = await self.redis_manager.cache_get(cache_key)
        if cached_overview:
            return cached_overview
        
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Get engagement metrics with optimized aggregation
            engagement_metrics = await self._get_engagement_metrics(user_id, start_date, end_date)
            
            # Get user metrics trends
            user_metrics = await self._get_user_metrics_trends(user_id, start_date, end_date)
            
            # Get content performance
            content_performance = await self._get_content_performance_summary(user_id, start_date, end_date)
            
            # Get platform comparison
            platform_comparison = await self._get_platform_comparison(user_id, start_date, end_date)
            
            overview = {
                'user_id': user_id,
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': days
                },
                'engagement_metrics': engagement_metrics,
                'user_metrics': user_metrics,
                'content_performance': content_performance,
                'platform_comparison': platform_comparison,
                'generated_at': datetime.utcnow().isoformat()
            }
            
            # Cache the overview
            await self.redis_manager.cache_set(cache_key, overview, ttl=1800)  # 30 minutes cache
            
            return overview
            
        except Exception as e:
            self.logger.error(f"Error getting user overview: {e}")
            raise

    async def _get_engagement_metrics(self, user_id: int, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get optimized engagement metrics"""
        try:
            # Use single query with multiple aggregations
            engagement_data = self.db.query(PostEngagement).filter(
                PostEngagement.user_id == user_id,
                PostEngagement.created_at >= start_date,
                PostEngagement.created_at <= end_date
            ).with_entities(
                func.count(PostEngagement.id).label('total_posts'),
                func.sum(PostEngagement.total_engagement).label('total_engagement'),
                func.avg(PostEngagement.engagement_rate).label('avg_engagement_rate'),
                func.max(PostEngagement.engagement_rate).label('max_engagement_rate'),
                func.sum(PostEngagement.likes).label('total_likes'),
                func.sum(PostEngagement.comments).label('total_comments'),
                func.sum(PostEngagement.shares).label('total_shares')
            ).first()
            
            # Get daily trends with optimized query
            daily_trends = self.db.query(PostEngagement).filter(
                PostEngagement.user_id == user_id,
                PostEngagement.created_at >= start_date,
                PostEngagement.created_at <= end_date
            ).with_entities(
                func.date(PostEngagement.created_at).label('date'),
                func.count(PostEngagement.id).label('posts'),
                func.avg(PostEngagement.engagement_rate).label('avg_rate'),
                func.sum(PostEngagement.total_engagement).label('total_engagement')
            ).group_by(func.date(PostEngagement.created_at)).order_by(func.date(PostEngagement.created_at)).all()
            
            return {
                'total_posts': engagement_data.total_posts or 0,
                'total_engagement': engagement_data.total_engagement or 0,
                'avg_engagement_rate': float(engagement_data.avg_engagement_rate or 0),
                'max_engagement_rate': float(engagement_data.max_engagement_rate or 0),
                'total_likes': engagement_data.total_likes or 0,
                'total_comments': engagement_data.total_comments or 0,
                'total_shares': engagement_data.total_shares or 0,
                'daily_trends': [
                    {
                        'date': trend.date.isoformat(),
                        'posts': trend.posts,
                        'avg_engagement_rate': float(trend.avg_rate or 0),
                        'total_engagement': trend.total_engagement or 0
                    }
                    for trend in daily_trends
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting engagement metrics: {e}")
            raise

    async def _get_user_metrics_trends(self, user_id: int, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get user metrics trends with optimization"""
        try:
            # Get latest metrics
            latest_metrics = self.db.query(UserMetrics).filter(
                UserMetrics.user_id == user_id,
                UserMetrics.created_at >= start_date,
                UserMetrics.created_at <= end_date
            ).order_by(UserMetrics.created_at.desc()).first()
            
            # Get metrics trends by platform
            platform_trends = self.db.query(UserMetrics).filter(
                UserMetrics.user_id == user_id,
                UserMetrics.created_at >= start_date,
                UserMetrics.created_at <= end_date
            ).with_entities(
                UserMetrics.platform,
                func.avg(UserMetrics.follower_count).label('avg_followers'),
                func.max(UserMetrics.follower_count).label('max_followers'),
                func.avg(UserMetrics.engagement_rate).label('avg_engagement_rate'),
                func.sum(UserMetrics.total_posts).label('total_posts')
            ).group_by(UserMetrics.platform).all()
            
            # Calculate growth rates
            growth_data = await self._calculate_growth_rates(user_id, start_date, end_date)
            
            return {
                'latest_metrics': {
                    'follower_count': latest_metrics.follower_count if latest_metrics else 0,
                    'following_count': latest_metrics.following_count if latest_metrics else 0,
                    'total_posts': latest_metrics.total_posts if latest_metrics else 0,
                    'engagement_rate': float(latest_metrics.engagement_rate or 0) if latest_metrics else 0,
                    'reach': latest_metrics.reach if latest_metrics else 0,
                    'impressions': latest_metrics.impressions if latest_metrics else 0
                },
                'platform_trends': [
                    {
                        'platform': trend.platform,
                        'avg_followers': trend.avg_followers or 0,
                        'max_followers': trend.max_followers or 0,
                        'avg_engagement_rate': float(trend.avg_engagement_rate or 0),
                        'total_posts': trend.total_posts or 0
                    }
                    for trend in platform_trends
                ],
                'growth_rates': growth_data
            }
            
        except Exception as e:
            self.logger.error(f"Error getting user metrics trends: {e}")
            raise

    async def _calculate_growth_rates(self, user_id: int, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        """Calculate growth rates for various metrics"""
        try:
            # Get metrics at start and end of period
            start_metrics = self.db.query(UserMetrics).filter(
                UserMetrics.user_id == user_id,
                UserMetrics.created_at >= start_date,
                UserMetrics.created_at <= start_date + timedelta(days=1)
            ).order_by(UserMetrics.created_at.asc()).first()
            
            end_metrics = self.db.query(UserMetrics).filter(
                UserMetrics.user_id == user_id,
                UserMetrics.created_at >= end_date - timedelta(days=1),
                UserMetrics.created_at <= end_date
            ).order_by(UserMetrics.created_at.desc()).first()
            
            if not start_metrics or not end_metrics:
                return {
                    'follower_growth_rate': 0.0,
                    'engagement_growth_rate': 0.0,
                    'post_growth_rate': 0.0
                }
            
            # Calculate growth rates
            follower_growth = ((end_metrics.follower_count - start_metrics.follower_count) / 
                             max(start_metrics.follower_count, 1)) * 100
            
            engagement_growth = ((end_metrics.engagement_rate - start_metrics.engagement_rate) / 
                               max(start_metrics.engagement_rate, 0.01)) * 100
            
            post_growth = ((end_metrics.total_posts - start_metrics.total_posts) / 
                         max(start_metrics.total_posts, 1)) * 100
            
            return {
                'follower_growth_rate': round(follower_growth, 2),
                'engagement_growth_rate': round(engagement_growth, 2),
                'post_growth_rate': round(post_growth, 2)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating growth rates: {e}")
            return {
                'follower_growth_rate': 0.0,
                'engagement_growth_rate': 0.0,
                'post_growth_rate': 0.0
            }

    @query_performance_tracker("postgresql", "get_platform_insights")
    async def get_platform_insights(self, user_id: int, platform: str, days: int = 30) -> Dict[str, Any]:
        """
        Get platform-specific insights with caching and optimization
        """
        cache_key = f"analytics:platform_insights:{user_id}:{platform}:{days}"
        
        # Check cache first
        cached_insights = await self.redis_manager.cache_get(cache_key)
        if cached_insights:
            return cached_insights
        
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Get platform-specific engagement data
            engagement_insights = await self._get_platform_engagement_insights(user_id, platform, start_date, end_date)
            
            # Get content type performance
            content_type_performance = await self._get_content_type_performance(user_id, platform, start_date, end_date)
            
            # Get optimal posting times
            optimal_times = await self._get_optimal_posting_times(user_id, platform, start_date, end_date)
            
            # Get competitor analysis (if available)
            competitor_analysis = await self._get_competitor_analysis(user_id, platform, start_date, end_date)
            
            insights = {
                'user_id': user_id,
                'platform': platform,
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': days
                },
                'engagement_insights': engagement_insights,
                'content_type_performance': content_type_performance,
                'optimal_posting_times': optimal_times,
                'competitor_analysis': competitor_analysis,
                'generated_at': datetime.utcnow().isoformat()
            }
            
            # Cache the insights
            await self.redis_manager.cache_set(cache_key, insights, ttl=3600)  # 1 hour cache
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error getting platform insights: {e}")
            raise

    @query_performance_tracker("postgresql", "get_content_recommendations")
    async def get_content_recommendations(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get AI-powered content recommendations with caching
        """
        cache_key = f"analytics:recommendations:{user_id}:{limit}"
        
        # Check cache first
        cached_recommendations = await self.redis_manager.cache_get(cache_key)
        if cached_recommendations:
            return cached_recommendations
        
        try:
            # Get top performing content types
            top_content_types = self.db.query(ContentPerformance).filter(
                ContentPerformance.user_id == user_id,
                ContentPerformance.created_at >= datetime.utcnow() - timedelta(days=90)
            ).with_entities(
                ContentPerformance.content_type,
                ContentPerformance.platform,
                func.avg(ContentPerformance.engagement_rate).label('avg_engagement'),
                func.count(ContentPerformance.id).label('content_count')
            ).group_by(
                ContentPerformance.content_type, 
                ContentPerformance.platform
            ).having(
                func.count(ContentPerformance.id) >= 3  # At least 3 posts for statistical significance
            ).order_by(
                func.avg(ContentPerformance.engagement_rate).desc()
            ).limit(limit).all()
            
            # Get optimal posting patterns
            posting_patterns = await self._analyze_posting_patterns(user_id)
            
            # Generate recommendations
            recommendations = []
            for content in top_content_types:
                recommendation = {
                    'content_type': content.content_type,
                    'platform': content.platform,
                    'avg_engagement_rate': float(content.avg_engagement),
                    'sample_size': content.content_count,
                    'confidence_score': min(content.content_count / 10.0, 1.0),  # Confidence based on sample size
                    'recommendation_reason': f"This content type shows {content.avg_engagement:.2%} average engagement rate",
                    'optimal_posting_time': posting_patterns.get(content.platform, {}).get('best_hour', 12),
                    'suggested_frequency': posting_patterns.get(content.platform, {}).get('optimal_frequency', 'daily')
                }
                recommendations.append(recommendation)
            
            # Cache the recommendations
            await self.redis_manager.cache_set(cache_key, recommendations, ttl=7200)  # 2 hours cache
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error getting content recommendations: {e}")
            raise

    async def _analyze_posting_patterns(self, user_id: int) -> Dict[str, Dict]:
        """Analyze optimal posting patterns by platform"""
        try:
            # Get posting patterns by hour and day of week
            posting_analysis = self.db.query(PostEngagement).filter(
                PostEngagement.user_id == user_id,
                PostEngagement.created_at >= datetime.utcnow() - timedelta(days=90)
            ).with_entities(
                PostEngagement.platform,
                func.extract('hour', PostEngagement.created_at).label('hour'),
                func.extract('dow', PostEngagement.created_at).label('day_of_week'),
                func.avg(PostEngagement.engagement_rate).label('avg_engagement'),
                func.count(PostEngagement.id).label('post_count')
            ).group_by(
                PostEngagement.platform,
                func.extract('hour', PostEngagement.created_at),
                func.extract('dow', PostEngagement.created_at)
            ).having(
                func.count(PostEngagement.id) >= 2  # At least 2 posts for pattern
            ).all()
            
            # Analyze patterns by platform
            patterns = {}
            for analysis in posting_analysis:
                platform = analysis.platform
                if platform not in patterns:
                    patterns[platform] = {
                        'hourly_performance': {},
                        'daily_performance': {},
                        'best_hour': 12,
                        'best_day': 1,
                        'optimal_frequency': 'daily'
                    }
                
                hour = int(analysis.hour)
                day = int(analysis.day_of_week)
                engagement = float(analysis.avg_engagement)
                
                # Track hourly performance
                if hour not in patterns[platform]['hourly_performance']:
                    patterns[platform]['hourly_performance'][hour] = []
                patterns[platform]['hourly_performance'][hour].append(engagement)
                
                # Track daily performance
                if day not in patterns[platform]['daily_performance']:
                    patterns[platform]['daily_performance'][day] = []
                patterns[platform]['daily_performance'][day].append(engagement)
            
            # Calculate best times for each platform
            for platform in patterns:
                # Best hour
                hourly_avg = {
                    hour: sum(engagements) / len(engagements)
                    for hour, engagements in patterns[platform]['hourly_performance'].items()
                }
                if hourly_avg:
                    patterns[platform]['best_hour'] = max(hourly_avg, key=hourly_avg.get)
                
                # Best day
                daily_avg = {
                    day: sum(engagements) / len(engagements)
                    for day, engagements in patterns[platform]['daily_performance'].items()
                }
                if daily_avg:
                    patterns[platform]['best_day'] = max(daily_avg, key=daily_avg.get)
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"Error analyzing posting patterns: {e}")
            return {}

    def __del__(self):
        if self.db:
            self.db.close()
    
    def get_user_overview(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get an overview of user analytics across all platforms"""
        try:
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
            
            # Get engagement trends
            engagement_trends = self._get_engagement_trends(user_id, start_date)
            
            return {
                "user_id": user_id,
                "time_period": f"Last {days} days",
                "total_followers": total_followers,
                "total_engagement": total_engagement,
                "average_engagement_rate": self._calculate_average_engagement_rate(platform_metrics),
                "platform_metrics": platform_metrics,
                "top_content": top_content,
                "engagement_trends": engagement_trends,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating user overview for {user_id}: {str(e)}")
            return {"error": str(e)}
    
    def get_platform_insights(self, user_id: str, platform: str, days: int = 30) -> Dict[str, Any]:
        """Get detailed insights for a specific platform"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            # Get platform metrics
            metrics = self._get_platform_metrics(user_id, platform, start_date)
            
            # Get content performance
            content_performance = self._get_content_performance(user_id, platform, start_date)
            
            # Get engagement breakdown
            engagement_breakdown = self._get_engagement_breakdown(user_id, platform, start_date)
            
            # Get daily metrics
            daily_metrics = self._get_daily_metrics(user_id, platform, start_date)
            
            # Get best posting times
            best_posting_times = self._analyze_best_posting_times(user_id, platform, start_date)
            
            # Get content type performance
            content_type_performance = self._analyze_content_type_performance(user_id, platform, start_date)
            
            return {
                "user_id": user_id,
                "platform": platform,
                "time_period": f"Last {days} days",
                "metrics": metrics,
                "content_performance": content_performance,
                "engagement_breakdown": engagement_breakdown,
                "daily_metrics": daily_metrics,
                "best_posting_times": best_posting_times,
                "content_type_performance": content_type_performance,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating platform insights for {user_id} on {platform}: {str(e)}")
            return {"error": str(e)}
    
    def get_content_analytics(self, user_id: str, platform_post_id: str, platform: str) -> Dict[str, Any]:
        """Get detailed analytics for a specific content piece"""
        try:
            # Get content performance data
            content = self.db.query(ContentPerformance).filter(
                ContentPerformance.user_id == user_id,
                ContentPerformance.platform == platform,
                ContentPerformance.platform_post_id == platform_post_id
            ).first()
            
            if not content:
                return {"error": "Content not found"}
            
            # Get engagement data
            engagements = self.db.query(PostEngagement).filter(
                PostEngagement.user_id == user_id,
                PostEngagement.platform == platform,
                PostEngagement.platform_post_id == platform_post_id
            ).all()
            
            # Process engagement data
            engagement_data = defaultdict(int)
            for engagement in engagements:
                engagement_data[engagement.engagement_type] += engagement.engagement_count
            
            # Compare to user average
            comparison = self._compare_to_user_average(user_id, platform, content)
            
            return {
                "user_id": user_id,
                "platform": platform,
                "post_id": platform_post_id,
                "post_date": content.post_date.isoformat() if content.post_date else None,
                "content_type": content.content_type,
                "performance": {
                    "impressions": content.impressions,
                    "reach": content.reach,
                    "engagement_count": content.engagement_count,
                    "engagement_rate": content.engagement_rate,
                    "likes": content.likes,
                    "comments": content.comments,
                    "shares": content.shares,
                    "saves": content.saves,
                    "clicks": content.clicks
                },
                "engagement_breakdown": dict(engagement_data),
                "metadata": content.content_metadata,
                "comparison_to_average": comparison,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting content analytics for post {platform_post_id}: {str(e)}")
            return {"error": str(e)}
    
    def generate_recommendations(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Generate content and posting recommendations based on analytics"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            # Get platforms the user is active on
            platforms = self._get_user_platforms(user_id)
            
            recommendations = {}
            for platform in platforms:
                # Get best posting times
                best_times = self._analyze_best_posting_times(user_id, platform, start_date)
                
                # Get best performing content types
                content_types = self._analyze_content_type_performance(user_id, platform, start_date)
                
                # Get top performing content features
                content_features = self._analyze_content_features(user_id, platform, start_date)
                
                recommendations[platform] = {
                    "best_posting_times": best_times,
                    "recommended_content_types": self._get_recommended_content_types(content_types),
                    "content_features": content_features,
                    "engagement_strategies": self._generate_engagement_strategies(user_id, platform, start_date)
                }
            
            return {
                "user_id": user_id,
                "time_period": f"Last {days} days",
                "recommendations": recommendations,
                "general_recommendations": self._generate_general_recommendations(user_id, start_date),
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating recommendations for {user_id}: {str(e)}")
            return {"error": str(e)}
    
    def get_comparative_analytics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get comparative analytics across platforms"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            # Get platforms the user is active on
            platforms = self._get_user_platforms(user_id)
            
            # Get metrics for each platform
            platform_metrics = {}
            for platform in platforms:
                metrics = self._get_platform_metrics(user_id, platform, start_date)
                platform_metrics[platform] = metrics
            
            # Compare engagement rates
            engagement_comparison = self._compare_platform_engagement_rates(platform_metrics)
            
            # Compare growth rates
            growth_comparison = self._compare_platform_growth_rates(user_id, platforms, start_date)
            
            # Compare content performance
            content_comparison = self._compare_content_performance_across_platforms(user_id, platforms, start_date)
            
            return {
                "user_id": user_id,
                "time_period": f"Last {days} days",
                "platform_metrics": platform_metrics,
                "engagement_comparison": engagement_comparison,
                "growth_comparison": growth_comparison,
                "content_comparison": content_comparison,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating comparative analytics for {user_id}: {str(e)}")
            return {"error": str(e)}
    
    def get_chart_data(self, user_id: str, metric: str, platform: Optional[str] = None, 
                      days: int = 30, group_by: str = "day") -> Dict[str, Any]:
        """Get data formatted for charts"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            # Validate metric
            valid_metrics = ["followers", "engagement", "engagement_rate", "posts", 
                           "likes", "comments", "shares", "impressions", "reach"]
            if metric not in valid_metrics:
                return {"error": f"Invalid metric. Valid options are: {', '.join(valid_metrics)}"}
            
            # Get platforms if not specified
            platforms = [platform] if platform else self._get_user_platforms(user_id)
            
            # Get data for each platform
            chart_data = {}
            for p in platforms:
                data = self._get_metric_time_series(user_id, p, metric, start_date, group_by)
                chart_data[p] = data
            
            return {
                "user_id": user_id,
                "metric": metric,
                "time_period": f"Last {days} days",
                "group_by": group_by,
                "data": chart_data,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating chart data for {user_id}, metric {metric}: {str(e)}")
            return {"error": str(e)}
    
    # Helper methods
    def _get_user_platforms(self, user_id: str) -> List[str]:
        """Get list of platforms the user is active on"""
        platforms = self.db.query(UserMetrics.platform).filter(
            UserMetrics.user_id == user_id
        ).distinct().all()
        return [p[0] for p in platforms]
    
    def _get_platform_metrics(self, user_id: str, platform: str, start_date: datetime) -> Dict[str, Any]:
        """Get aggregated metrics for a platform"""
        # Get most recent metrics
        latest_metrics = self.db.query(UserMetrics).filter(
            UserMetrics.user_id == user_id,
            UserMetrics.platform == platform,
            UserMetrics.date >= start_date
        ).order_by(desc(UserMetrics.date)).first()
        
        # Get earliest metrics in the period for comparison
        earliest_metrics = self.db.query(UserMetrics).filter(
            UserMetrics.user_id == user_id,
            UserMetrics.platform == platform,
            UserMetrics.date >= start_date
        ).order_by(UserMetrics.date).first()
        
        # Calculate totals
        total_engagements = self.db.query(func.sum(UserMetrics.total_engagements)).filter(
            UserMetrics.user_id == user_id,
            UserMetrics.platform == platform,
            UserMetrics.date >= start_date
        ).scalar() or 0
        
        # Calculate average engagement rate
        avg_engagement_rate = self.db.query(func.avg(UserMetrics.engagement_rate)).filter(
            UserMetrics.user_id == user_id,
            UserMetrics.platform == platform,
            UserMetrics.date >= start_date,
            UserMetrics.engagement_rate != None
        ).scalar() or 0
        
        # Count posts in period
        posts_count = self.db.query(func.sum(UserMetrics.posts_count)).filter(
            UserMetrics.user_id == user_id,
            UserMetrics.platform == platform,
            UserMetrics.date >= start_date
        ).scalar() or 0
        
        # Calculate follower growth
        follower_growth = 0
        growth_percentage = 0
        
        if latest_metrics and earliest_metrics and earliest_metrics.followers_count:
            follower_growth = (latest_metrics.followers_count or 0) - (earliest_metrics.followers_count or 0)
            growth_percentage = (follower_growth / earliest_metrics.followers_count) * 100 if earliest_metrics.followers_count else 0
        
        return {
            "current_followers": latest_metrics.followers_count if latest_metrics else 0,
            "follower_growth": follower_growth,
            "follower_growth_percentage": growth_percentage,
            "total_engagements": total_engagements,
            "average_engagement_rate": avg_engagement_rate,
            "posts_count": posts_count
        }
    
    def _get_top_performing_content(self, user_id: str, start_date: datetime, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top performing content across all platforms"""
        top_content = self.db.query(ContentPerformance).filter(
            ContentPerformance.user_id == user_id,
            ContentPerformance.post_date >= start_date
        ).order_by(desc(ContentPerformance.engagement_rate)).limit(limit).all()
        
        result = []
        for content in top_content:
            result.append({
                "platform": content.platform,
                "post_id": content.platform_post_id,
                "content_type": content.content_type,
                "post_date": content.post_date.isoformat() if content.post_date else None,
                "engagement_rate": content.engagement_rate,
                "total_engagements": content.engagement_count,
                "impressions": content.impressions,
                "likes": content.likes,
                "comments": content.comments
            })
        
        return result
    
    def _get_engagement_trends(self, user_id: str, start_date: datetime) -> Dict[str, Any]:
        """Get engagement trends over time"""
        # Get daily metrics for all platforms
        platforms = self._get_user_platforms(user_id)
        
        trends = {}
        for platform in platforms:
            daily_metrics = self._get_daily_metrics(user_id, platform, start_date)
            trends[platform] = {
                "engagement_rate": [m.get("engagement_rate", 0) for m in daily_metrics],
                "dates": [m.get("date") for m in daily_metrics]
            }
        
        return trends
    
    def _calculate_average_engagement_rate(self, platform_metrics: Dict[str, Dict[str, Any]]) -> float:
        """Calculate overall average engagement rate across platforms"""
        total_rate = 0
        count = 0
        
        for platform, metrics in platform_metrics.items():
            if metrics.get("average_engagement_rate"):
                total_rate += metrics["average_engagement_rate"]
                count += 1
        
        return total_rate / count if count > 0 else 0
    
    def _get_content_performance(self, user_id: str, platform: str, start_date: datetime) -> List[Dict[str, Any]]:
        """Get performance data for all content on a platform"""
        content = self.db.query(ContentPerformance).filter(
            ContentPerformance.user_id == user_id,
            ContentPerformance.platform == platform,
            ContentPerformance.post_date >= start_date
        ).order_by(desc(ContentPerformance.post_date)).all()
        
        result = []
        for item in content:
            result.append({
                "post_id": item.platform_post_id,
                "content_type": item.content_type,
                "post_date": item.post_date.isoformat() if item.post_date else None,
                "engagement_rate": item.engagement_rate,
                "total_engagements": item.engagement_count,
                "impressions": item.impressions,
                "reach": item.reach,
                "likes": item.likes,
                "comments": item.comments,
                "shares": item.shares,
                "saves": item.saves,
                "clicks": item.clicks
            })
        
        return result
    
    def _get_engagement_breakdown(self, user_id: str, platform: str, start_date: datetime) -> Dict[str, int]:
        """Get breakdown of engagement types"""
        # Get all user metrics for the platform in the period
        metrics = self.db.query(UserMetrics).filter(
            UserMetrics.user_id == user_id,
            UserMetrics.platform == platform,
            UserMetrics.date >= start_date
        ).all()
        
        # Combine engagement breakdowns
        breakdown = defaultdict(int)
        for metric in metrics:
            if metric.engagement_breakdown:
                for engagement_type, count in metric.engagement_breakdown.items():
                    breakdown[engagement_type] += count
        
        return dict(breakdown)
    
    def _get_daily_metrics(self, user_id: str, platform: str, start_date: datetime) -> List[Dict[str, Any]]:
        """Get daily metrics for a platform"""
        metrics = self.db.query(UserMetrics).filter(
            UserMetrics.user_id == user_id,
            UserMetrics.platform == platform,
            UserMetrics.date >= start_date
        ).order_by(UserMetrics.date).all()
        
        result = []
        for metric in metrics:
            result.append({
                "date": metric.date.isoformat() if metric.date else None,
                "followers": metric.followers_count,
                "posts": metric.posts_count,
                "total_engagements": metric.total_engagements,
                "engagement_rate": metric.engagement_rate
            })
        
        return result
    
    def _analyze_best_posting_times(self, user_id: str, platform: str, start_date: datetime) -> Dict[str, Any]:
        """Analyze best times to post based on engagement"""
        # This would analyze content performance by time of day and day of week
        # For now, return sample data
        return {
            "days": {
                "monday": 0.8,
                "tuesday": 0.7,
                "wednesday": 0.9,
                "thursday": 0.85,
                "friday": 0.75,
                "saturday": 0.6,
                "sunday": 0.5
            },
            "hours": {
                "morning": 0.8,  # 6am-12pm
                "afternoon": 0.9,  # 12pm-6pm
                "evening": 0.7,  # 6pm-12am
                "night": 0.4  # 12am-6am
            },
            "best_times": [
                {"day": "wednesday", "time": "2pm", "score": 0.95},
                {"day": "thursday", "time": "11am", "score": 0.9},
                {"day": "monday", "time": "3pm", "score": 0.85}
            ]
        }
    
    def _analyze_content_type_performance(self, user_id: str, platform: str, start_date: datetime) -> Dict[str, Any]:
        """Analyze performance by content type"""
        # Get content performance grouped by type
        content_types = self.db.query(
            ContentPerformance.content_type,
            func.avg(ContentPerformance.engagement_rate).label("avg_engagement_rate"),
            func.avg(ContentPerformance.impressions).label("avg_impressions"),
            func.count(ContentPerformance.id).label("count")
        ).filter(
            ContentPerformance.user_id == user_id,
            ContentPerformance.platform == platform,
            ContentPerformance.post_date >= start_date
        ).group_by(ContentPerformance.content_type).all()
        
        result = {}
        for content_type in content_types:
            result[content_type.content_type] = {
                "avg_engagement_rate": content_type.avg_engagement_rate,
                "avg_impressions": content_type.avg_impressions,
                "count": content_type.count
            }
        
        return result
    
    def _analyze_content_features(self, user_id: str, platform: str, start_date: datetime) -> Dict[str, Any]:
        """Analyze which content features perform best"""
        # This would analyze metadata like hashtags, caption length, media types, etc.
        # For now, return sample data
        return {
            "hashtags": {
                "optimal_count": 5,
                "top_performing": ["#trending", "#viral", "#content"]
            },
            "caption": {
                "optimal_length": "medium",  # short, medium, long
                "engagement_by_length": {
                    "short": 0.7,  # <50 chars
                    "medium": 0.9,  # 50-200 chars
                    "long": 0.6  # >200 chars
                }
            },
            "media": {
                "types": {
                    "image": 0.7,
                    "video": 0.9,
                    "carousel": 0.85,
                    "text_only": 0.5
                }
            }
        }
    
    def _get_recommended_content_types(self, content_type_performance: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get recommended content types based on performance"""
        recommendations = []
        
        for content_type, metrics in content_type_performance.items():
            recommendations.append({
                "type": content_type,
                "engagement_rate": metrics.get("avg_engagement_rate", 0),
                "impressions": metrics.get("avg_impressions", 0),
                "sample_size": metrics.get("count", 0)
            })
        
        # Sort by engagement rate
        recommendations.sort(key=lambda x: x["engagement_rate"], reverse=True)
        
        return recommendations
    
    def _generate_engagement_strategies(self, user_id: str, platform: str, start_date: datetime) -> List[str]:
        """Generate engagement strategies based on analytics"""
        # This would analyze engagement patterns and suggest strategies
        # For now, return sample strategies
        return [
            "Respond to comments within 1 hour to boost engagement",
            "Ask questions in your captions to encourage comments",
            "Use call-to-actions to increase shares and saves",
            "Post consistently at optimal times for your audience"
        ]
    
    def _generate_general_recommendations(self, user_id: str, start_date: datetime) -> List[str]:
        """Generate general recommendations across platforms"""
        # This would analyze cross-platform patterns
        # For now, return sample recommendations
        return [
            "Cross-promote your content across platforms to maximize reach",
            "Maintain consistent branding across all platforms",
            "Focus more resources on platforms with highest engagement rates",
            "Repurpose high-performing content across different platforms"
        ]
    
    def _compare_to_user_average(self, user_id: str, platform: str, content: ContentPerformance) -> Dict[str, Any]:
        """Compare content performance to user average"""
        # Get user averages
        avg_metrics = self.db.query(
            func.avg(ContentPerformance.engagement_rate).label("avg_engagement_rate"),
            func.avg(ContentPerformance.impressions).label("avg_impressions"),
            func.avg(ContentPerformance.likes).label("avg_likes"),
            func.avg(ContentPerformance.comments).label("avg_comments")
        ).filter(
            ContentPerformance.user_id == user_id,
            ContentPerformance.platform == platform
        ).first()
        
        # Calculate percentage differences
        engagement_diff = ((content.engagement_rate or 0) / avg_metrics.avg_engagement_rate - 1) * 100 if avg_metrics.avg_engagement_rate else 0
        impressions_diff = ((content.impressions or 0) / avg_metrics.avg_impressions - 1) * 100 if avg_metrics.avg_impressions else 0
        likes_diff = ((content.likes or 0) / avg_metrics.avg_likes - 1) * 100 if avg_metrics.avg_likes else 0
        comments_diff = ((content.comments or 0) / avg_metrics.avg_comments - 1) * 100 if avg_metrics.avg_comments else 0
        
        return {
            "engagement_rate": {
                "value": content.engagement_rate,
                "avg": avg_metrics.avg_engagement_rate,
                "diff_percentage": engagement_diff
            },
            "impressions": {
                "value": content.impressions,
                "avg": avg_metrics.avg_impressions,
                "diff_percentage": impressions_diff
            },
            "likes": {
                "value": content.likes,
                "avg": avg_metrics.avg_likes,
                "diff_percentage": likes_diff
            },
            "comments": {
                "value": content.comments,
                "avg": avg_metrics.avg_comments,
                "diff_percentage": comments_diff
            }
        }
    
    def _compare_platform_engagement_rates(self, platform_metrics: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Compare engagement rates across platforms"""
        engagement_rates = {}
        best_platform = None
        highest_rate = 0
        
        for platform, metrics in platform_metrics.items():
            rate = metrics.get("average_engagement_rate", 0)
            engagement_rates[platform] = rate
            
            if rate > highest_rate:
                highest_rate = rate
                best_platform = platform
        
        return {
            "rates": engagement_rates,
            "best_platform": best_platform,
            "highest_rate": highest_rate
        }
    
    def _compare_platform_growth_rates(self, user_id: str, platforms: List[str], start_date: datetime) -> Dict[str, Any]:
        """Compare follower growth rates across platforms"""
        growth_rates = {}
        best_platform = None
        highest_growth = 0
        
        for platform in platforms:
            metrics = self._get_platform_metrics(user_id, platform, start_date)
            growth = metrics.get("follower_growth_percentage", 0)
            growth_rates[platform] = growth
            
            if growth > highest_growth:
                highest_growth = growth
                best_platform = platform
        
        return {
            "rates": growth_rates,
            "best_platform": best_platform,
            "highest_growth": highest_growth
        }
    
    def _compare_content_performance_across_platforms(self, user_id: str, platforms: List[str], start_date: datetime) -> Dict[str, Any]:
        """Compare content performance metrics across platforms"""
        avg_engagement_by_platform = {}
        avg_impressions_by_platform = {}
        
        for platform in platforms:
            # Get average metrics for the platform
            avg_metrics = self.db.query(
                func.avg(ContentPerformance.engagement_rate).label("avg_engagement_rate"),
                func.avg(ContentPerformance.impressions).label("avg_impressions")
            ).filter(
                ContentPerformance.user_id == user_id,
                ContentPerformance.platform == platform,
                ContentPerformance.post_date >= start_date
            ).first()
            
            avg_engagement_by_platform[platform] = avg_metrics.avg_engagement_rate or 0
            avg_impressions_by_platform[platform] = avg_metrics.avg_impressions or 0
        
        return {
            "engagement_rates": avg_engagement_by_platform,
            "impressions": avg_impressions_by_platform
        }
    
    def _get_metric_time_series(self, user_id: str, platform: str, metric: str, 
                              start_date: datetime, group_by: str = "day") -> List[Dict[str, Any]]:
        """Get time series data for a specific metric"""
        # Map metric to database fields
        metric_mapping = {
            "followers": UserMetrics.followers_count,
            "engagement": UserMetrics.total_engagements,
            "engagement_rate": UserMetrics.engagement_rate,
            "posts": UserMetrics.posts_count
        }
        
        # For content-specific metrics, we need to query ContentPerformance
        content_metrics = ["likes", "comments", "shares", "impressions", "reach"]
        
        result = []
        
        if metric in metric_mapping:
            # Query UserMetrics for user-level metrics
            metrics = self.db.query(UserMetrics).filter(
                UserMetrics.user_id == user_id,
                UserMetrics.platform == platform,
                UserMetrics.date >= start_date
            ).order_by(UserMetrics.date).all()
            
            for m in metrics:
                value = getattr(m, metric_mapping[metric].key, 0)
                result.append({
                    "date": m.date.isoformat() if m.date else None,
                    "value": value or 0
                })
                
        elif metric in content_metrics:
            # For content metrics, we need to aggregate by day
            # This is a simplified version - in a real implementation, you'd use SQL date functions
            # to properly group by day, week, or month
            content_items = self.db.query(ContentPerformance).filter(
                ContentPerformance.user_id == user_id,
                ContentPerformance.platform == platform,
                ContentPerformance.post_date >= start_date
            ).order_by(ContentPerformance.post_date).all()
            
            # Group by date
            date_groups = defaultdict(list)
            for item in content_items:
                if item.post_date:
                    date_key = item.post_date.date().isoformat()
                    date_groups[date_key].append(item)
            
            # Calculate daily averages
            for date, items in date_groups.items():
                total = sum(getattr(item, metric, 0) or 0 for item in items)
                avg = total / len(items) if items else 0
                
                result.append({
                    "date": date,
                    "value": avg
                })
        
        return result
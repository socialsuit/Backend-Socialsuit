import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.services.database.database import get_db_session
from app.services.models.analytics_model import PostEngagement, UserMetrics, ContentPerformance, EngagementType
from app.services.models.user_model import User
from app.services.utils.logger_config import setup_logger
from app.services.utils.monitoring import track_analytics_collection
from app.services.database.query_optimizer import query_performance_tracker
from app.services.database.redis import RedisManager

# Set up logger
logger = setup_logger("analytics_collector")

class AnalyticsCollector:
    """Collects analytics data from various social media platforms"""
    
    def __init__(self):
        self.db = get_db_session()
        
    def __del__(self):
        if self.db:
            self.db.close()
    
    async def collect_platform_data(self, user_id: str, platform: str, days_back: int = 7) -> Dict[str, Any]:
        """Collect analytics data for a specific user and platform"""
        try:
            # Track analytics collection attempt
            track_analytics_collection(platform)
            
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
        
    async def _collect_facebook_data(self, user_id: str, days_back: int) -> List[Dict[str, Any]]:
        """Collect Facebook analytics data"""
        # This would use the Facebook Graph API to collect real data
        # For now, we'll implement a placeholder that returns sample data
        return self._generate_sample_data("facebook", days_back)
    
    async def _collect_instagram_data(self, user_id: str, days_back: int) -> List[Dict[str, Any]]:
        """Collect Instagram analytics data"""
        # This would use the Instagram Graph API to collect real data
        return self._generate_sample_data("instagram", days_back)
    
    async def _collect_twitter_data(self, user_id: str, days_back: int) -> List[Dict[str, Any]]:
        """Collect Twitter analytics data"""
        # This would use the Twitter API to collect real data
        return self._generate_sample_data("twitter", days_back)
    
    async def _collect_linkedin_data(self, user_id: str, days_back: int) -> List[Dict[str, Any]]:
        """Collect LinkedIn analytics data"""
        # This would use the LinkedIn API to collect real data
        return self._generate_sample_data("linkedin", days_back)
    
    async def _collect_tiktok_data(self, user_id: str, days_back: int) -> List[Dict[str, Any]]:
        """Collect TikTok analytics data"""
        # This would use the TikTok API to collect real data
        return self._generate_sample_data("tiktok", days_back)
    
    async def _process_and_store_data(self, user_id: str, platform: str, data: List[Dict[str, Any]]) -> None:
        """Process and store collected analytics data"""
        try:
            # Process post engagements
            for item in data:
                if item.get("type") == "post_engagement":
                    self._store_post_engagement(user_id, platform, item)
                elif item.get("type") == "content_performance":
                    self._store_content_performance(user_id, platform, item)
            
            # Aggregate and store user metrics
            self._aggregate_user_metrics(user_id, platform, data)
            
            # Commit all changes
            self.db.commit()
            logger.info(f"Successfully processed and stored {platform} data for user {user_id}")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error processing {platform} data for user {user_id}: {str(e)}")
            raise
    
    def _store_post_engagement(self, user_id: str, platform: str, data: Dict[str, Any]) -> None:
        """Store post engagement data"""
        engagement = PostEngagement(
            user_id=user_id,
            platform=platform,
            platform_post_id=data.get("post_id"),
            engagement_type=data.get("engagement_type"),
            engagement_count=data.get("count", 1),
            engagement_date=data.get("date"),
            metadata=data.get("metadata")
        )
        self.db.add(engagement)
    
    def _store_content_performance(self, user_id: str, platform: str, data: Dict[str, Any]) -> None:
        """Store content performance data"""
        # Check if we already have a record for this post
        existing = self.db.query(ContentPerformance).filter(
            ContentPerformance.user_id == user_id,
            ContentPerformance.platform == platform,
            ContentPerformance.platform_post_id == data.get("post_id")
        ).first()
        
        if existing:
            # Update existing record
            existing.impressions = data.get("impressions", existing.impressions)
            existing.reach = data.get("reach", existing.reach)
            existing.engagement_count = data.get("engagement_count", existing.engagement_count)
            existing.engagement_rate = data.get("engagement_rate", existing.engagement_rate)
            existing.likes = data.get("likes", existing.likes)
            existing.comments = data.get("comments", existing.comments)
            existing.shares = data.get("shares", existing.shares)
            existing.saves = data.get("saves", existing.saves)
            existing.clicks = data.get("clicks", existing.clicks)
            existing.content_metadata = data.get("metadata", existing.content_metadata)
            existing.updated_at = datetime.now()
        else:
            # Create new record
            performance = ContentPerformance(
                user_id=user_id,
                platform=platform,
                platform_post_id=data.get("post_id"),
                content_type=data.get("content_type", "post"),
                impressions=data.get("impressions"),
                reach=data.get("reach"),
                engagement_count=data.get("engagement_count"),
                engagement_rate=data.get("engagement_rate"),
                likes=data.get("likes"),
                comments=data.get("comments"),
                shares=data.get("shares"),
                saves=data.get("saves"),
                clicks=data.get("clicks"),
                post_date=data.get("post_date"),
                content_metadata=data.get("metadata")
            )
            self.db.add(performance)
    
    def _aggregate_user_metrics(self, user_id: str, platform: str, data: List[Dict[str, Any]]) -> None:
        """Aggregate and store user metrics by day"""
        # Group data by date
        dates = {}
        for item in data:
            date_str = item.get("date")
            if not date_str:
                continue
                
            date = datetime.strptime(date_str, "%Y-%m-%d").date() if isinstance(date_str, str) else date_str.date()
            if date not in dates:
                dates[date] = []
            dates[date].append(item)
        
        # Process each day's data
        for date, items in dates.items():
            # Check if we already have metrics for this day
            existing = self.db.query(UserMetrics).filter(
                UserMetrics.user_id == user_id,
                UserMetrics.platform == platform,
                func.date(UserMetrics.date) == date
            ).first()
            
            # Calculate metrics
            followers = next((item.get("followers") for item in items if item.get("followers")), None)
            posts_count = len([item for item in items if item.get("type") == "content_performance"])
            
            # Calculate engagement breakdown
            engagement_breakdown = {}
            for engagement_type in EngagementType:
                count = sum(item.get("count", 0) for item in items 
                           if item.get("type") == "post_engagement" and item.get("engagement_type") == engagement_type)
                if count > 0:
                    engagement_breakdown[engagement_type] = count
            
            total_engagements = sum(engagement_breakdown.values())
            
            if existing:
                # Update existing record
                existing.followers_count = followers if followers is not None else existing.followers_count
                existing.posts_count = posts_count if posts_count > 0 else existing.posts_count
                existing.total_engagements = total_engagements if total_engagements > 0 else existing.total_engagements
                
                # Update engagement breakdown
                if engagement_breakdown:
                    existing_breakdown = existing.engagement_breakdown or {}
                    for k, v in engagement_breakdown.items():
                        existing_breakdown[k] = v
                    existing.engagement_breakdown = existing_breakdown
                
                # Calculate engagement rate if we have both engagements and followers
                if total_engagements > 0 and followers:
                    existing.engagement_rate = (total_engagements / followers) * 100
                
                existing.updated_at = datetime.now()
            else:
                # Create new metrics record
                metrics = UserMetrics(
                    user_id=user_id,
                    platform=platform,
                    date=date,
                    followers_count=followers,
                    posts_count=posts_count,
                    total_engagements=total_engagements,
                    engagement_breakdown=engagement_breakdown,
                    engagement_rate=(total_engagements / followers * 100) if followers and total_engagements else None
                )
                self.db.add(metrics)
    
    def _generate_sample_data(self, platform: str, days_back: int) -> List[Dict[str, Any]]:
        """Generate sample analytics data for testing"""
        data = []
        today = datetime.now()
        
        # Generate sample post data
        for i in range(1, 4):  # 3 sample posts
            post_id = f"{platform}_post_{i}"
            post_date = (today - timedelta(days=i % days_back)).strftime("%Y-%m-%d")
            
            # Add content performance data
            data.append({
                "type": "content_performance",
                "post_id": post_id,
                "content_type": "post",
                "post_date": post_date,
                "impressions": 1000 + (i * 500),
                "reach": 800 + (i * 300),
                "engagement_count": 150 + (i * 50),
                "engagement_rate": 3.5 + (i * 0.5),
                "likes": 100 + (i * 30),
                "comments": 20 + i,
                "shares": 15 + (i * 2),
                "saves": 10 + i,
                "clicks": 5 + i,
                "date": post_date,
                "metadata": {
                    "hashtags": ["#sample", f"#{platform}"],
                    "caption_length": 100 + (i * 20),
                    "has_image": True,
                    "has_video": i % 2 == 0
                }
            })
            
            # Add engagement data for each post
            for engagement_type in ["like", "comment", "share", "save"]:
                data.append({
                    "type": "post_engagement",
                    "post_id": post_id,
                    "engagement_type": engagement_type,
                    "count": 50 - (i * 10) if engagement_type == "like" else 10 - i,
                    "date": post_date,
                    "metadata": {
                        "source": "mobile" if i % 2 == 0 else "web",
                        "country": "US" if i % 3 == 0 else ("UK" if i % 3 == 1 else "CA")
                    }
                })
        
        # Add follower data for each day
        for i in range(days_back):
            date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            data.append({
                "type": "user_metrics",
                "date": date,
                "followers": 1000 + (i * 10),  # Increasing followers as we go back in time
                "platform": platform
            })
            
        return data

# Async function to collect data for all platforms for a user
async def collect_all_platform_data(user_id: str, days_back: int = 7) -> Dict[str, Any]:
    """Collect data from all platforms for a specific user"""
    collector = AnalyticsCollector()
    platforms = ["facebook", "instagram", "twitter", "linkedin", "tiktok"]
    
    tasks = [collector.collect_platform_data(user_id, platform, days_back) for platform in platforms]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    platform_results = {}
    for platform, result in zip(platforms, results):
        if isinstance(result, Exception):
            platform_results[platform] = {"error": str(result)}
        else:
            platform_results[platform] = result
    
    return {
        "user_id": user_id,
        "days_back": days_back,
        "timestamp": datetime.now().isoformat(),
        "results": platform_results
    }

class AnalyticsCollector:
    def __init__(self, db_session):
        self.db = db_session
        self.redis_manager = RedisManager()
        self.logger = logging.getLogger(__name__)

    @query_performance_tracker("postgresql", "collect_analytics")
    async def collect_analytics(self, user_id: int, platform: str) -> Dict[str, Any]:
        """
        Collect analytics data from platform with caching and optimization
        """
        cache_key = f"analytics:collected:{user_id}:{platform}:{datetime.now().strftime('%Y-%m-%d-%H')}"
        
        # Check cache first
        cached_data = await self.redis_manager.cache_get(cache_key)
        if cached_data:
            return cached_data
        
        try:
            # Collect data based on platform
            if platform == 'facebook':
                data = await self._collect_facebook_analytics(user_id)
            elif platform == 'instagram':
                data = await self._collect_instagram_analytics(user_id)
            elif platform == 'twitter':
                data = await self._collect_twitter_analytics(user_id)
            elif platform == 'linkedin':
                data = await self._collect_linkedin_analytics(user_id)
            elif platform == 'tiktok':
                data = await self._collect_tiktok_analytics(user_id)
            else:
                raise ValueError(f"Unsupported platform: {platform}")
            
            # Store in database with batch operations
            await self._store_analytics_batch(user_id, platform, data)
            
            # Cache the results
            await self.redis_manager.cache_set(cache_key, data, ttl=3600)  # 1 hour cache
            
            # Invalidate related caches
            await self._invalidate_analytics_cache(user_id, platform)
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error collecting analytics for user {user_id} on {platform}: {e}")
            raise

    @query_performance_tracker("postgresql", "store_analytics_batch")
    async def _store_analytics_batch(self, user_id: int, platform: str, data: Dict[str, Any]):
        """
        Store analytics data using batch operations for better performance
        """
        try:
            # Prepare batch data
            engagement_data = []
            metrics_data = []
            performance_data = []
            
            # Process engagement data
            if 'engagements' in data:
                for engagement in data['engagements']:
                    engagement_data.append({
                        'user_id': user_id,
                        'platform': platform,
                        'post_id': engagement.get('post_id'),
                        'likes': engagement.get('likes', 0),
                        'comments': engagement.get('comments', 0),
                        'shares': engagement.get('shares', 0),
                        'total_engagement': engagement.get('total_engagement', 0),
                        'engagement_rate': engagement.get('engagement_rate', 0.0),
                        'created_at': engagement.get('created_at', datetime.utcnow())
                    })
            
            # Process metrics data
            if 'metrics' in data:
                metrics = data['metrics']
                metrics_data.append({
                    'user_id': user_id,
                    'platform': platform,
                    'follower_count': metrics.get('follower_count', 0),
                    'following_count': metrics.get('following_count', 0),
                    'total_posts': metrics.get('total_posts', 0),
                    'engagement_rate': metrics.get('engagement_rate', 0.0),
                    'reach': metrics.get('reach', 0),
                    'impressions': metrics.get('impressions', 0),
                    'created_at': datetime.utcnow()
                })
            
            # Process performance data
            if 'content_performance' in data:
                for content in data['content_performance']:
                    performance_data.append({
                        'user_id': user_id,
                        'platform': platform,
                        'content_type': content.get('content_type'),
                        'content_id': content.get('content_id'),
                        'engagement_rate': content.get('engagement_rate', 0.0),
                        'reach': content.get('reach', 0),
                        'impressions': content.get('impressions', 0),
                        'clicks': content.get('clicks', 0),
                        'created_at': content.get('created_at', datetime.utcnow())
                    })
            
            # Batch insert operations
            if engagement_data:
                await self._batch_insert_engagement(engagement_data)
            
            if metrics_data:
                await self._batch_insert_metrics(metrics_data)
            
            if performance_data:
                await self._batch_insert_performance(performance_data)
                
        except Exception as e:
            self.logger.error(f"Error in batch store analytics: {e}")
            raise

    async def _batch_insert_engagement(self, engagement_data: List[Dict]):
        """Batch insert engagement data"""
        try:
            # Use bulk insert for better performance
            self.db.bulk_insert_mappings(PostEngagement, engagement_data)
            self.db.commit()
            self.logger.info(f"Batch inserted {len(engagement_data)} engagement records")
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Error in batch insert engagement: {e}")
            raise

    async def _batch_insert_metrics(self, metrics_data: List[Dict]):
        """Batch insert metrics data"""
        try:
            self.db.bulk_insert_mappings(UserMetrics, metrics_data)
            self.db.commit()
            self.logger.info(f"Batch inserted {len(metrics_data)} metrics records")
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Error in batch insert metrics: {e}")
            raise

    async def _batch_insert_performance(self, performance_data: List[Dict]):
        """Batch insert performance data"""
        try:
            self.db.bulk_insert_mappings(ContentPerformance, performance_data)
            self.db.commit()
            self.logger.info(f"Batch inserted {len(performance_data)} performance records")
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Error in batch insert performance: {e}")
            raise

    async def _invalidate_analytics_cache(self, user_id: int, platform: str):
        """Invalidate related analytics caches"""
        try:
            cache_patterns = [
                f"analytics:*:{user_id}:*",
                f"analytics:*:*:{platform}:*",
                f"engagement:*:{user_id}:*",
                f"metrics:*:{user_id}:*",
                f"performance:*:{user_id}:*"
            ]
            
            for pattern in cache_patterns:
                await self.redis_manager.delete_pattern(pattern)
                
        except Exception as e:
            self.logger.warning(f"Error invalidating analytics cache: {e}")

    @query_performance_tracker("postgresql", "get_analytics_summary")
    async def get_analytics_summary(self, user_id: int, platform: str = None, 
                                  days: int = 30) -> Dict[str, Any]:
        """
        Get analytics summary with caching
        """
        cache_key = f"analytics:summary:{user_id}:{platform or 'all'}:{days}"
        
        # Check cache first
        cached_summary = await self.redis_manager.cache_get(cache_key)
        if cached_summary:
            return cached_summary
        
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Build optimized query with proper indexing
            query = self.db.query(PostEngagement).filter(
                PostEngagement.user_id == user_id,
                PostEngagement.created_at >= start_date,
                PostEngagement.created_at <= end_date
            )
            
            if platform:
                query = query.filter(PostEngagement.platform == platform)
            
            # Use aggregation for better performance
            summary_data = query.with_entities(
                func.count(PostEngagement.id).label('total_posts'),
                func.sum(PostEngagement.total_engagement).label('total_engagement'),
                func.avg(PostEngagement.engagement_rate).label('avg_engagement_rate'),
                func.max(PostEngagement.engagement_rate).label('max_engagement_rate'),
                func.min(PostEngagement.engagement_rate).label('min_engagement_rate')
            ).first()
            
            # Get platform breakdown
            platform_breakdown = query.with_entities(
                PostEngagement.platform,
                func.count(PostEngagement.id).label('post_count'),
                func.avg(PostEngagement.engagement_rate).label('avg_rate')
            ).group_by(PostEngagement.platform).all()
            
            summary = {
                'total_posts': summary_data.total_posts or 0,
                'total_engagement': summary_data.total_engagement or 0,
                'avg_engagement_rate': float(summary_data.avg_engagement_rate or 0),
                'max_engagement_rate': float(summary_data.max_engagement_rate or 0),
                'min_engagement_rate': float(summary_data.min_engagement_rate or 0),
                'platform_breakdown': [
                    {
                        'platform': p.platform,
                        'post_count': p.post_count,
                        'avg_engagement_rate': float(p.avg_rate or 0)
                    }
                    for p in platform_breakdown
                ],
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': days
                }
            }
            
            # Cache the summary
            await self.redis_manager.cache_set(cache_key, summary, ttl=1800)  # 30 minutes cache
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting analytics summary: {e}")
            raise
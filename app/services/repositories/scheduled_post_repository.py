from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc, text
from datetime import datetime, timedelta
import asyncio

from app.services.interfaces.base_repository import BaseRepository
from app.services.models.scheduled_post_model import ScheduledPost
from app.services.database.query_optimizer import query_performance_tracker
from app.services.database.redis import RedisManager

class ScheduledPostRepository(BaseRepository[ScheduledPost]):
    """
    Optimized Repository for ScheduledPost entity operations with caching and performance monitoring
    """
    def __init__(self, db: Session):
        super().__init__(db, ScheduledPost)
    
    @query_performance_tracker("postgresql", "get_by_user_id")
    def get_by_user_id(self, user_id: str, limit: int = 100, offset: int = 0, status: Optional[str] = None) -> List[ScheduledPost]:
        """
        Get scheduled posts for a specific user with pagination and optional status filter
        """
        cache_key = f"posts:user:{user_id}:{limit}:{offset}:{status or 'all'}"
        
        query = self.db.query(ScheduledPost).filter(ScheduledPost.user_id == user_id)
        
        if status:
            query = query.filter(ScheduledPost.status == status)
        
        result = (query.order_by(desc(ScheduledPost.scheduled_time))
                 .limit(limit)
                 .offset(offset)
                 .all())
        
        return result
    
    @query_performance_tracker("postgresql", "get_pending_posts")
    def get_pending_posts(self, limit: int = 1000) -> List[ScheduledPost]:
        """
        Get posts that are pending to be published with optimized query
        """
        cache_key = f"posts:pending:{limit}"
        
        # Optimized query for pending posts ready to be published
        current_time = datetime.now()
        
        result = (self.db.query(ScheduledPost)
                 .filter(and_(
                     ScheduledPost.status == "pending",
                     ScheduledPost.scheduled_time <= current_time
                 ))
                 .order_by(asc(ScheduledPost.scheduled_time))
                 .limit(limit)
                 .all())
        
        return result
    
    @query_performance_tracker("postgresql", "get_posts_by_platform")
    def get_posts_by_platform(self, user_id: str, platform: str, limit: int = 100, offset: int = 0) -> List[ScheduledPost]:
        """
        Get posts for a specific user and platform with pagination
        """
        cache_key = f"posts:platform:{user_id}:{platform}:{limit}:{offset}"
        
        result = (self.db.query(ScheduledPost)
                 .filter(and_(
                     ScheduledPost.user_id == user_id, 
                     ScheduledPost.platform == platform
                 ))
                 .order_by(desc(ScheduledPost.created_at))
                 .limit(limit)
                 .offset(offset)
                 .all())
        
        return result
    
    @query_performance_tracker("postgresql", "update_post_status")
    def update_post_status(self, post_id: str, status: str, error_message: Optional[str] = None) -> bool:
        """
        Update the status of a scheduled post with error handling
        """
        try:
            post = self.get_by_id(post_id)
            if post:
                post.status = status
                post.updated_at = datetime.now()
                
                if error_message:
                    post.error_message = error_message
                
                if status == "published":
                    post.published_at = datetime.now()
                
                self.db.commit()
                
                # Invalidate related cache
                asyncio.create_task(self._invalidate_post_cache(post_id, post.user_id, post.platform))
                return True
        except Exception as e:
            self.db.rollback()
            raise e
        return False
    
    @query_performance_tracker("postgresql", "get_posts_by_status")
    def get_posts_by_status(self, status: str, limit: int = 100, offset: int = 0) -> List[ScheduledPost]:
        """
        Get posts by status with pagination
        """
        cache_key = f"posts:status:{status}:{limit}:{offset}"
        
        result = (self.db.query(ScheduledPost)
                 .filter(ScheduledPost.status == status)
                 .order_by(desc(ScheduledPost.created_at))
                 .limit(limit)
                 .offset(offset)
                 .all())
        
        return result
    
    @query_performance_tracker("postgresql", "get_posts_in_timerange")
    def get_posts_in_timerange(self, start_time: datetime, end_time: datetime, 
                              user_id: Optional[str] = None, platform: Optional[str] = None) -> List[ScheduledPost]:
        """
        Get posts scheduled within a specific time range
        """
        cache_key = f"posts:timerange:{start_time.isoformat()}:{end_time.isoformat()}:{user_id or 'all'}:{platform or 'all'}"
        
        query = self.db.query(ScheduledPost).filter(
            and_(
                ScheduledPost.scheduled_time >= start_time,
                ScheduledPost.scheduled_time <= end_time
            )
        )
        
        if user_id:
            query = query.filter(ScheduledPost.user_id == user_id)
        
        if platform:
            query = query.filter(ScheduledPost.platform == platform)
        
        result = query.order_by(asc(ScheduledPost.scheduled_time)).all()
        
        return result
    
    @query_performance_tracker("postgresql", "get_post_statistics")
    def get_post_statistics(self, user_id: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        """
        Get post statistics with aggregation
        """
        cache_key = f"posts:stats:{user_id or 'all'}:{days}"
        
        base_query = self.db.query(ScheduledPost)
        
        if user_id:
            base_query = base_query.filter(ScheduledPost.user_id == user_id)
        
        # Date filter for recent posts
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_query = base_query.filter(ScheduledPost.created_at >= cutoff_date)
        
        # Aggregate statistics
        total_posts = base_query.count()
        recent_posts = recent_query.count()
        
        # Status distribution
        status_stats = (base_query
                       .with_entities(ScheduledPost.status, func.count(ScheduledPost.id))
                       .group_by(ScheduledPost.status)
                       .all())
        
        # Platform distribution
        platform_stats = (base_query
                         .with_entities(ScheduledPost.platform, func.count(ScheduledPost.id))
                         .group_by(ScheduledPost.platform)
                         .all())
        
        # Success rate calculation
        published_count = base_query.filter(ScheduledPost.status == "published").count()
        failed_count = base_query.filter(ScheduledPost.status == "failed").count()
        
        success_rate = (published_count / (published_count + failed_count) * 100) if (published_count + failed_count) > 0 else 0
        
        stats = {
            "total_posts": total_posts,
            "recent_posts": recent_posts,
            "status_distribution": dict(status_stats),
            "platform_distribution": dict(platform_stats),
            "success_rate": success_rate,
            "published_count": published_count,
            "failed_count": failed_count
        }
        
        return stats
    
    @query_performance_tracker("postgresql", "get_failed_posts")
    def get_failed_posts(self, user_id: Optional[str] = None, limit: int = 50) -> List[ScheduledPost]:
        """
        Get failed posts for analysis and retry
        """
        cache_key = f"posts:failed:{user_id or 'all'}:{limit}"
        
        query = self.db.query(ScheduledPost).filter(ScheduledPost.status == "failed")
        
        if user_id:
            query = query.filter(ScheduledPost.user_id == user_id)
        
        result = (query.order_by(desc(ScheduledPost.updated_at))
                 .limit(limit)
                 .all())
        
        return result
    
    @query_performance_tracker("postgresql", "bulk_update_status")
    def bulk_update_status(self, post_ids: List[str], status: str) -> int:
        """
        Bulk update status for multiple posts
        """
        try:
            updated_count = (self.db.query(ScheduledPost)
                           .filter(ScheduledPost.id.in_(post_ids))
                           .update({
                               "status": status,
                               "updated_at": datetime.now()
                           }, synchronize_session=False))
            
            self.db.commit()
            
            # Invalidate cache for affected posts
            asyncio.create_task(self._invalidate_bulk_cache(post_ids))
            
            return updated_count
        except Exception as e:
            self.db.rollback()
            raise e
    
    @query_performance_tracker("postgresql", "search_posts")
    def search_posts(self, search_term: str, user_id: Optional[str] = None, limit: int = 50) -> List[ScheduledPost]:
        """
        Search posts by content with text search optimization
        """
        cache_key = f"posts:search:{search_term}:{user_id or 'all'}:{limit}"
        
        search_pattern = f"%{search_term}%"
        
        query = self.db.query(ScheduledPost).filter(
            or_(
                ScheduledPost.content.ilike(search_pattern),
                ScheduledPost.title.ilike(search_pattern) if hasattr(ScheduledPost, 'title') else False
            )
        )
        
        if user_id:
            query = query.filter(ScheduledPost.user_id == user_id)
        
        result = (query.order_by(desc(ScheduledPost.created_at))
                 .limit(limit)
                 .all())
        
        return result
    
    async def _invalidate_post_cache(self, post_id: str, user_id: str, platform: str):
        """
        Invalidate post-related cache entries
        """
        patterns = [
            f"posts:user:{user_id}:*",
            f"posts:platform:{user_id}:{platform}:*",
            f"posts:pending:*",
            f"posts:status:*",
            f"posts:stats:*"
        ]
        
        for pattern in patterns:
            await RedisManager.cache_delete_pattern(pattern)
    
    async def _invalidate_bulk_cache(self, post_ids: List[str]):
        """
        Invalidate cache for bulk operations
        """
        patterns = [
            "posts:*"  # Invalidate all post-related cache
        ]
        
        for pattern in patterns:
            await RedisManager.cache_delete_pattern(pattern)
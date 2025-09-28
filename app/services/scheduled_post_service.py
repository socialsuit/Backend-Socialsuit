from datetime import datetime, timedelta
import logging
import asyncio
from typing import Dict, List, Optional, Any, Union

from app.services.models.scheduled_post_model import ScheduledPost, PostStatus
from app.services.repositories.scheduled_post_repository import ScheduledPostRepository
from app.services.repositories.user_repository import UserRepository
from app.services.utils.logger_config import setup_logger
from app.services.database.query_optimizer import query_performance_tracker
from app.services.database.redis import RedisManager

logger = setup_logger("scheduled_post_service")

class ScheduledPostService:
    """
    Service for managing scheduled posts across different social media platforms.
    Handles creation, retrieval, updating, deletion, and publishing of scheduled posts.
    """
    
    def __init__(self, scheduled_post_repository: ScheduledPostRepository, user_repository: UserRepository):
        self.scheduled_post_repository = scheduled_post_repository
        self.user_repository = user_repository
        self.redis_manager = RedisManager()
    
    @query_performance_tracker("postgresql", "create_scheduled_post")
    def create_scheduled_post(
        self, 
        user_id: str, 
        platform: str, 
        post_payload: Dict[str, Any], 
        scheduled_time: datetime
    ) -> ScheduledPost:
        """
        Create a new scheduled post for a user on a specific platform.
        
        Args:
            user_id: The ID of the user creating the post
            platform: The social media platform (twitter, facebook, etc.)
            post_payload: The content and metadata for the post
            scheduled_time: When the post should be published
            
        Returns:
            The created ScheduledPost object
        """
        # Verify user exists
        user = self.user_repository.get_by_id(user_id)
        if not user:
            logger.error(f"User with ID {user_id} not found")
            raise ValueError(f"User with ID {user_id} not found")
        
        # Create the scheduled post
        post = ScheduledPost(
            user_id=user_id,
            platform=platform,
            post_payload=post_payload,
            scheduled_time=scheduled_time,
            status=PostStatus.PENDING,
            retries=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        created_post = self.scheduled_post_repository.create(post)
        
        # Invalidate related caches asynchronously
        asyncio.create_task(self._invalidate_user_post_cache(user_id))
        
        return created_post
    
    @query_performance_tracker("postgresql", "get_scheduled_post")
    def get_scheduled_post(self, post_id: int) -> Optional[ScheduledPost]:
        """
        Get a specific scheduled post by ID with caching.
        
        Args:
            post_id: The ID of the post to retrieve
            
        Returns:
            The ScheduledPost object if found, None otherwise
        """
        # Try cache first
        cache_key = f"scheduled_post:{post_id}"
        cached_post = self.redis_manager.get(cache_key)
        if cached_post:
            return ScheduledPost(**cached_post)
        
        # Get from database
        post = self.scheduled_post_repository.get_by_id(post_id)
        if post:
            # Cache for 30 minutes
            self.redis_manager.set(cache_key, post.__dict__, ttl=1800)
        
        return post
    
    @query_performance_tracker("postgresql", "get_user_scheduled_posts")
    def get_user_scheduled_posts(
        self, 
        user_id: str, 
        platform: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ScheduledPost]:
        """
        Get all scheduled posts for a user with optional filtering and pagination.
        
        Args:
            user_id: The ID of the user
            platform: Filter by platform (optional)
            status: Filter by post status (optional)
            start_date: Filter by posts scheduled after this date (optional)
            end_date: Filter by posts scheduled before this date (optional)
            limit: Maximum number of posts to return
            offset: Number of posts to skip
            
        Returns:
            List of ScheduledPost objects matching the criteria
        """
        # Create cache key based on parameters
        cache_key = f"user_posts:{user_id}:{platform or 'all'}:{status or 'all'}:{limit}:{offset}"
        if start_date:
            cache_key += f":{start_date.isoformat()}"
        if end_date:
            cache_key += f":{end_date.isoformat()}"
        
        # Try cache first
        cached_posts = self.redis_manager.get(cache_key)
        if cached_posts:
            return [ScheduledPost(**post) for post in cached_posts]
        
        # Get from database with pagination
        posts = self.scheduled_post_repository.get_by_user_id(
            user_id, platform=platform, status=status, 
            start_date=start_date, end_date=end_date,
            limit=limit, offset=offset
        )
        
        # Cache for 10 minutes
        if posts:
            self.redis_manager.set(cache_key, [post.__dict__ for post in posts], ttl=600)
        
        return posts
    
    def update_scheduled_post(
        self, 
        post_id: int, 
        post_payload: Optional[Dict[str, Any]] = None, 
        scheduled_time: Optional[datetime] = None
    ) -> ScheduledPost:
        """
        Update an existing scheduled post.
        
        Args:
            post_id: The ID of the post to update
            post_payload: New content and metadata (optional)
            scheduled_time: New scheduled time (optional)
            
        Returns:
            The updated ScheduledPost object
            
        Raises:
            ValueError: If the post doesn't exist or is already published
        """
        post = self.scheduled_post_repository.get_by_id(post_id)
        if not post:
            logger.error(f"Post with ID {post_id} not found")
            raise ValueError(f"Post with ID {post_id} not found")
        
        if post.status not in [PostStatus.PENDING, PostStatus.FAILED]:
            logger.error(f"Cannot update post with status {post.status}")
            raise ValueError(f"Cannot update post with status {post.status}")
        
        if post_payload is not None:
            post.post_payload = post_payload
        
        if scheduled_time is not None:
            post.scheduled_time = scheduled_time
        
        post.updated_at = datetime.utcnow()
        updated_post = self.scheduled_post_repository.update(post)
        
        # Invalidate related caches asynchronously
        asyncio.create_task(self._invalidate_post_cache(post_id))
        asyncio.create_task(self._invalidate_user_post_cache(post.user_id))
        
        return updated_post
    
    def delete_scheduled_post(self, post_id: int) -> bool:
        """
        Delete a scheduled post.
        
        Args:
            post_id: The ID of the post to delete
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            ValueError: If the post doesn't exist
        """
        post = self.scheduled_post_repository.get_by_id(post_id)
        if not post:
            logger.error(f"Post with ID {post_id} not found")
            raise ValueError(f"Post with ID {post_id} not found")
        
        self.scheduled_post_repository.delete(post)
        
        # Invalidate related caches asynchronously
        asyncio.create_task(self._invalidate_post_cache(post_id))
        asyncio.create_task(self._invalidate_user_post_cache(post.user_id))
        
        return True
    
    def publish_post(self, post_id: int) -> bool:
        """
        Manually publish a scheduled post immediately.
        
        Args:
            post_id: The ID of the post to publish
            
        Returns:
            True if successful, False otherwise
        """
        post = self.scheduled_post_repository.get_by_id(post_id)
        if not post:
            logger.error(f"Post with ID {post_id} not found")
            return False
        
        # Update status to publishing
        self.scheduled_post_repository.update_post_status(post_id, PostStatus.PUBLISHING.value)
        
        # Attempt to publish based on platform
        success = False
        try:
            if post.platform == "twitter":
                success = self._publish_to_twitter(post)
            elif post.platform == "facebook":
                success = self._publish_to_facebook(post)
            elif post.platform == "instagram":
                success = self._publish_to_instagram(post)
            elif post.platform == "linkedin":
                success = self._publish_to_linkedin(post)
            else:
                logger.error(f"Unsupported platform: {post.platform}")
                success = False
        except Exception as e:
            logger.error(f"Error publishing post {post_id}: {str(e)}")
            success = False
        
        # Update status based on result
        if success:
            self.scheduled_post_repository.update_post_status(post_id, PostStatus.PUBLISHED.value)
        else:
            post = self.scheduled_post_repository.get_by_id(post_id)
            post.retries += 1
            self.scheduled_post_repository.update(post)
            self.scheduled_post_repository.update_post_status(post_id, PostStatus.FAILED.value)
        
        return success
    
    @query_performance_tracker("postgresql", "process_pending_posts")
    def process_pending_posts(self, limit: Optional[int] = None) -> int:
        """
        Process all pending posts that are due for publishing.
        
        Args:
            limit: Maximum number of posts to process (optional)
            
        Returns:
            Number of posts successfully published
        """
        now = datetime.utcnow()
        pending_posts = self.scheduled_post_repository.get_pending_posts(now, limit=limit)
        
        published_count = 0
        for post in pending_posts:
            if self.publish_post(post.id):
                published_count += 1
        
        return published_count
    
    def cancel_scheduled_post(self, post_id: int) -> bool:
        """
        Cancel a scheduled post that hasn't been published yet.
        
        Args:
            post_id: The ID of the post to cancel
            
        Returns:
            True if successful, False otherwise
        """
        post = self.scheduled_post_repository.get_by_id(post_id)
        if not post:
            logger.error(f"Post with ID {post_id} not found")
            return False
        
        if post.status not in [PostStatus.PENDING, PostStatus.FAILED]:
            logger.error(f"Cannot cancel post with status {post.status}")
            return False
        
        self.scheduled_post_repository.update_post_status(post_id, PostStatus.CANCELLED.value)
        return True
    
    def update_post_status(self, post_id: int, status: str) -> bool:
        """
        Update the status of a scheduled post.
        
        Args:
            post_id: The ID of the post
            status: The new status
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.scheduled_post_repository.update_post_status(post_id, status)
            return True
        except Exception as e:
            logger.error(f"Error updating post status: {str(e)}")
            return False
    
    # Platform-specific publishing methods
    def _publish_to_twitter(self, post: ScheduledPost) -> bool:
        """
        Publish a post to Twitter.
        
        Args:
            post: The ScheduledPost to publish
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Implementation would use Twitter API client
            logger.info(f"Publishing to Twitter: {post.id}")
            # TODO: Implement actual Twitter API integration
            return True  # Placeholder for actual implementation
        except Exception as e:
            logger.error(f"Twitter publishing error: {str(e)}")
            return False
    
    def _publish_to_facebook(self, post: ScheduledPost) -> bool:
        """
        Publish a post to Facebook.
        
        Args:
            post: The ScheduledPost to publish
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Implementation would use Facebook API client
            logger.info(f"Publishing to Facebook: {post.id}")
            # TODO: Implement actual Facebook API integration
            return True  # Placeholder for actual implementation
        except Exception as e:
            logger.error(f"Facebook publishing error: {str(e)}")
            return False
    
    def _publish_to_instagram(self, post: ScheduledPost) -> bool:
        """
        Publish a post to Instagram.
        
        Args:
            post: The ScheduledPost to publish
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Implementation would use Instagram API client
            logger.info(f"Publishing to Instagram: {post.id}")
            # TODO: Implement actual Instagram API integration
            return True  # Placeholder for actual implementation
        except Exception as e:
            logger.error(f"Instagram publishing error: {str(e)}")
            return False
    
    def _publish_to_linkedin(self, post: ScheduledPost) -> bool:
        """
        Publish a post to LinkedIn.
        
        Args:
            post: The ScheduledPost to publish
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Implementation would use LinkedIn API client
            logger.info(f"Publishing to LinkedIn: {post.id}")
            # TODO: Implement actual LinkedIn API integration
            return True  # Placeholder for actual implementation
        except Exception as e:
            logger.error(f"LinkedIn publishing error: {str(e)}")
            return False
    
    # New optimized methods for analytics and bulk operations
    
    @query_performance_tracker("postgresql", "get_post_statistics")
    def get_post_statistics(self, user_id: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        """
        Get comprehensive post statistics with caching.
        
        Args:
            user_id: Filter by user ID (optional)
            days: Number of days to analyze
            
        Returns:
            Dictionary containing post statistics
        """
        cache_key = f"post_stats:{user_id or 'all'}:{days}"
        cached_stats = self.redis_manager.get(cache_key)
        if cached_stats:
            return cached_stats
        
        stats = self.scheduled_post_repository.get_post_statistics(user_id, days)
        
        # Cache for 1 hour
        self.redis_manager.set(cache_key, stats, ttl=3600)
        return stats
    
    @query_performance_tracker("postgresql", "get_posts_by_timerange")
    def get_posts_by_timerange(
        self, 
        start_time: datetime, 
        end_time: datetime,
        user_id: Optional[str] = None,
        platform: Optional[str] = None,
        limit: int = 100
    ) -> List[ScheduledPost]:
        """
        Get posts within a specific time range with caching.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            user_id: Filter by user ID (optional)
            platform: Filter by platform (optional)
            limit: Maximum number of posts to return
            
        Returns:
            List of ScheduledPost objects
        """
        cache_key = f"posts_timerange:{user_id or 'all'}:{platform or 'all'}:{start_time.isoformat()}:{end_time.isoformat()}:{limit}"
        cached_posts = self.redis_manager.get(cache_key)
        if cached_posts:
            return [ScheduledPost(**post) for post in cached_posts]
        
        posts = self.scheduled_post_repository.get_posts_in_timerange(
            start_time, end_time, user_id, platform, limit
        )
        
        # Cache for 15 minutes
        if posts:
            self.redis_manager.set(cache_key, [post.__dict__ for post in posts], ttl=900)
        
        return posts
    
    @query_performance_tracker("postgresql", "bulk_update_status")
    def bulk_update_status(self, post_ids: List[int], status: str, error_message: Optional[str] = None) -> bool:
        """
        Update status for multiple posts in bulk.
        
        Args:
            post_ids: List of post IDs to update
            status: New status for all posts
            error_message: Error message if status is failed
            
        Returns:
            True if successful, False otherwise
        """
        try:
            success = self.scheduled_post_repository.bulk_update_status(post_ids, status, error_message)
            
            if success:
                # Invalidate caches for all affected posts
                for post_id in post_ids:
                    asyncio.create_task(self._invalidate_post_cache(post_id))
                
                # Invalidate bulk cache patterns
                asyncio.create_task(self._invalidate_bulk_cache())
            
            return success
        except Exception as e:
            logger.error(f"Error in bulk status update: {str(e)}")
            return False
    
    def get_failed_posts(self, user_id: Optional[str] = None, limit: int = 50) -> List[ScheduledPost]:
        """
        Get failed posts for retry processing.
        
        Args:
            user_id: Filter by user ID (optional)
            limit: Maximum number of posts to return
            
        Returns:
            List of failed ScheduledPost objects
        """
        cache_key = f"failed_posts:{user_id or 'all'}:{limit}"
        cached_posts = self.redis_manager.get(cache_key)
        if cached_posts:
            return [ScheduledPost(**post) for post in cached_posts]
        
        posts = self.scheduled_post_repository.get_failed_posts(user_id, limit)
        
        # Cache for 5 minutes (failed posts change frequently)
        if posts:
            self.redis_manager.set(cache_key, [post.__dict__ for post in posts], ttl=300)
        
        return posts
    
    def search_posts(
        self, 
        query: str, 
        user_id: Optional[str] = None,
        platform: Optional[str] = None,
        limit: int = 50
    ) -> List[ScheduledPost]:
        """
        Search posts by content with caching.
        
        Args:
            query: Search query
            user_id: Filter by user ID (optional)
            platform: Filter by platform (optional)
            limit: Maximum number of posts to return
            
        Returns:
            List of matching ScheduledPost objects
        """
        cache_key = f"search_posts:{query}:{user_id or 'all'}:{platform or 'all'}:{limit}"
        cached_posts = self.redis_manager.get(cache_key)
        if cached_posts:
            return [ScheduledPost(**post) for post in cached_posts]
        
        posts = self.scheduled_post_repository.search_posts(query, user_id, platform, limit)
        
        # Cache for 30 minutes
        if posts:
            self.redis_manager.set(cache_key, [post.__dict__ for post in posts], ttl=1800)
        
        return posts
    
    def get_platform_performance(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get platform-specific performance metrics.
        
        Args:
            user_id: User ID
            days: Number of days to analyze
            
        Returns:
            Dictionary containing platform performance data
        """
        cache_key = f"platform_performance:{user_id}:{days}"
        cached_performance = self.redis_manager.get(cache_key)
        if cached_performance:
            return cached_performance
        
        # Get posts by platform for the user
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        platforms = ['twitter', 'facebook', 'instagram', 'linkedin']
        performance_data = {}
        
        for platform in platforms:
            posts = self.get_user_scheduled_posts(
                user_id, platform=platform, 
                start_date=start_date, end_date=end_date
            )
            
            total_posts = len(posts)
            published_posts = len([p for p in posts if p.status == PostStatus.PUBLISHED.value])
            failed_posts = len([p for p in posts if p.status == PostStatus.FAILED.value])
            
            success_rate = (published_posts / total_posts * 100) if total_posts > 0 else 0
            
            performance_data[platform] = {
                'total_posts': total_posts,
                'published_posts': published_posts,
                'failed_posts': failed_posts,
                'success_rate': round(success_rate, 2)
            }
        
        # Cache for 2 hours
        self.redis_manager.set(cache_key, performance_data, ttl=7200)
        return performance_data
    
    # Private cache management methods
    
    async def _invalidate_post_cache(self, post_id: int):
        """Invalidate cache for a specific post."""
        try:
            await self.redis_manager.delete(f"scheduled_post:{post_id}")
        except Exception as e:
            logger.error(f"Error invalidating post cache: {str(e)}")
    
    async def _invalidate_user_post_cache(self, user_id: str):
        """Invalidate cache patterns for user posts."""
        try:
            patterns = [
                f"user_posts:{user_id}:*",
                f"post_stats:{user_id}:*",
                f"platform_performance:{user_id}:*",
                f"failed_posts:{user_id}:*",
                f"search_posts:*:{user_id}:*"
            ]
            
            for pattern in patterns:
                await self.redis_manager.delete_pattern(pattern)
        except Exception as e:
            logger.error(f"Error invalidating user post cache: {str(e)}")
    
    async def _invalidate_bulk_cache(self):
        """Invalidate bulk cache patterns."""
        try:
            patterns = [
                "user_posts:*",
                "post_stats:*",
                "posts_timerange:*",
                "failed_posts:*"
            ]
            
            for pattern in patterns:
                await self.redis_manager.delete_pattern(pattern)
        except Exception as e:
            logger.error(f"Error invalidating bulk cache: {str(e)}")
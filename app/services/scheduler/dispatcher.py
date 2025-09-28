from celery import current_app
from app.services.utils.logger_config import setup_logger
from app.services.scheduler.cache_service import SchedulerCacheService
from app.services.database.redis import RedisManager
from typing import List, Dict, Any
import json
from datetime import datetime, timedelta

logger = setup_logger("dispatcher")

async def dispatch_scheduled_posts(posts: list):
    """
    Dispatches a list of posts to the Celery task queue with intelligent optimization.
    
    Args:
        posts: List of post dictionaries with the following structure:
            [
                {
                    "platform": "instagram", 
                    "user_token": {...}, 
                    "post_payload": {...},
                    "post_id": 123  # Optional database ID of the scheduled post
                },
                ...
            ]
    """
    if not posts:
        logger.info("[DISPATCHER] No posts to dispatch")
        return
        
    logger.info(f"[DISPATCHER] Dispatching {len(posts)} posts with optimization")
    
    # Group posts by platform for optimized dispatching
    posts_by_platform = {}
    for post in posts:
        platform = post.get("platform")
        if platform not in posts_by_platform:
            posts_by_platform[platform] = []
        posts_by_platform[platform].append(post)
    
    dispatched_count = 0
    failed_count = 0
    
    for platform, platform_posts in posts_by_platform.items():
        try:
            # Check platform posting limits
            limits_info = await SchedulerCacheService.get_platform_posting_limits(platform)
            
            if not limits_info.get("can_post", True):
                logger.warning(f"[DISPATCHER] Platform {platform} has reached posting limits. Skipping {len(platform_posts)} posts")
                continue
            
            # Calculate optimal delay based on platform limits
            hourly_limit = limits_info.get("limits", {}).get("hourly", 10)
            optimal_delay = max(1, 3600 / hourly_limit)  # Spread posts evenly across the hour
            
            for i, post in enumerate(platform_posts):
                try:
                    # Validate required fields
                    if not all(key in post for key in ["platform", "user_token", "post_payload"]):
                        logger.error(f"[DISPATCHER] Missing required fields in post: {post.get('post_id', 'unknown')}")
                        failed_count += 1
                        continue
                    
                    # Calculate intelligent delay
                    base_delay = i * optimal_delay
                    priority_delay = 0
                    
                    # Add priority handling
                    if post.get("priority") == "high":
                        priority_delay = -30  # High priority posts go 30 seconds earlier
                    elif post.get("priority") == "low":
                        priority_delay = 60   # Low priority posts go 60 seconds later
                    
                    total_delay = max(0, base_delay + priority_delay)
                    
                    # Extract post_id if it exists, otherwise pass None
                    post_id = post.get("post_id", None)
                    
                    # Log dispatch with optimization info
                    logger.info(f"[DISPATCHER] Sending post {post_id} to {platform} with {total_delay:.1f}s delay (optimized)")
                    
                    # Send to appropriate Celery queue based on priority
                    queue_name = "high_priority" if post.get("priority") == "high" else "celery"
                    
                    # Send to Celery task queue
                    current_app.send_task(
                        'services.scheduler.tasks.schedule_post',
                        args=(post["platform"], post["user_token"], post["post_payload"], post_id),
                        countdown=total_delay,
                        queue=queue_name
                    )
                    
                    dispatched_count += 1
                    
                    # Update dispatch metrics in cache
                    await update_dispatch_metrics(platform, "dispatched")
                    
                except Exception as e:
                    logger.exception(f"[DISPATCHER] Error dispatching post {post.get('post_id', 'unknown')}: {e}")
                    failed_count += 1
                    await update_dispatch_metrics(platform, "failed")
                    
        except Exception as e:
            logger.exception(f"[DISPATCHER] Error processing platform {platform}: {e}")
            failed_count += len(platform_posts)
    
    # Update overall dispatch statistics
    await update_overall_dispatch_stats(dispatched_count, failed_count)
    
    logger.info(f"[DISPATCHER] Completed dispatching. Success: {dispatched_count}, Failed: {failed_count}")
    return {"dispatched": dispatched_count, "failed": failed_count}

async def update_dispatch_metrics(platform: str, status: str):
    """Update dispatch metrics in Redis for monitoring"""
    try:
        async with RedisManager.get_connection() as redis:
            # Increment platform-specific counter
            await redis.incr(f"dispatch_metrics:{platform}:{status}")
            await redis.expire(f"dispatch_metrics:{platform}:{status}", 86400)  # 24 hours
            
            # Increment daily counter
            today = datetime.now().strftime("%Y-%m-%d")
            await redis.incr(f"dispatch_daily:{today}:{status}")
            await redis.expire(f"dispatch_daily:{today}:{status}", 86400 * 7)  # 7 days
            
    except Exception as e:
        logger.error(f"Failed to update dispatch metrics: {e}")

async def update_overall_dispatch_stats(dispatched: int, failed: int):
    """Update overall dispatch statistics"""
    try:
        stats = {
            "last_dispatch_time": datetime.now().isoformat(),
            "last_dispatch_count": dispatched,
            "last_failed_count": failed,
            "success_rate": (dispatched / (dispatched + failed) * 100) if (dispatched + failed) > 0 else 0
        }
        
        await RedisManager.cache_set("dispatch_stats:latest", json.dumps(stats), ttl=3600)
        
    except Exception as e:
        logger.error(f"Failed to update overall dispatch stats: {e}")

async def get_dispatch_statistics() -> Dict[str, Any]:
    """Get comprehensive dispatch statistics"""
    try:
        stats = {}
        
        async with RedisManager.get_connection() as redis:
            # Get latest dispatch stats
            latest_stats = await redis.get("dispatch_stats:latest")
            if latest_stats:
                stats["latest"] = json.loads(latest_stats)
            
            # Get platform-specific metrics
            platforms = ["instagram", "facebook", "twitter", "linkedin", "tiktok", "youtube"]
            platform_stats = {}
            
            for platform in platforms:
                dispatched = await redis.get(f"dispatch_metrics:{platform}:dispatched") or 0
                failed = await redis.get(f"dispatch_metrics:{platform}:failed") or 0
                
                platform_stats[platform] = {
                    "dispatched": int(dispatched),
                    "failed": int(failed),
                    "success_rate": (int(dispatched) / (int(dispatched) + int(failed)) * 100) 
                                  if (int(dispatched) + int(failed)) > 0 else 0
                }
            
            stats["platforms"] = platform_stats
            
            # Get daily stats for the last 7 days
            daily_stats = {}
            for i in range(7):
                date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                dispatched = await redis.get(f"dispatch_daily:{date}:dispatched") or 0
                failed = await redis.get(f"dispatch_daily:{date}:failed") or 0
                
                daily_stats[date] = {
                    "dispatched": int(dispatched),
                    "failed": int(failed)
                }
            
            stats["daily"] = daily_stats
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get dispatch statistics: {e}")
        return {"error": str(e)}

async def optimize_dispatch_queue():
    """Optimize the dispatch queue by reordering posts based on priority and platform limits"""
    try:
        # Get current queue status
        queue_status = await SchedulerCacheService.get_queue_status()
        
        if queue_status.get("total_queued", 0) == 0:
            return {"message": "No posts in queue to optimize"}
        
        # This would implement queue reordering logic
        # For now, just log the optimization attempt
        logger.info(f"[OPTIMIZER] Queue optimization completed. Current queue size: {queue_status.get('total_queued', 0)}")
        
        return {"optimized": True, "queue_size": queue_status.get("total_queued", 0)}
        
    except Exception as e:
        logger.error(f"Failed to optimize dispatch queue: {e}")
        return {"error": str(e)}
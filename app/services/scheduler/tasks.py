from celery import shared_task
from app.services.scheduler.platform_post import post_to_platform
from app.services.refresh.meta_refresh import refresh_meta_token
from app.services.refresh.linkedin_refresh import refresh_linkedin_token
from app.services.refresh.twitter_refresh import refresh_twitter_token
from app.services.refresh.youtube_refresh import refresh_youtube_token
from app.services.refresh.tiktok_refresh import refresh_tiktok_token

from app.services.scheduler.dispatcher import dispatch_scheduled_posts  # ✅ Directly use dispatcher, no loop!
from app.services.utils.logger_config import setup_logger
from app.services.models.scheduled_post_model import ScheduledPost, PostStatus
from app.services.database.postgresql import get_db, get_db_connection
from app.services.database.optimization_service import DatabaseOptimizationService
from app.services.scheduler.cache_service import SchedulerCacheService
from app.services.database.redis import RedisManager
from app.services.platform.meta import MetaAPI
from app.services.platform.linkedin import LinkedInAPI
from app.services.platform.twitter import TwitterAPI
from app.services.platform.youtube import YouTubeAPI
from app.services.platform.tiktok import TikTokAPI
import json
import asyncio
import asyncpg
from datetime import datetime, timedelta
from typing import Dict, Any

logger = setup_logger("scheduler_tasks")  # ✅ FIX: Proper logger name


async def update_post_status(post_id, status, result=None):
    """
    Update the status of a scheduled post in the database with caching optimization.
    
    Args:
        post_id: ID of the ScheduledPost to update
        status: New status (success, failed, retry)
        result: Optional result data to store as JSON
    """
    try:
        # Update database
        async with get_db_connection() as conn:
            # Get current post data
            post_data = await conn.fetchrow(
                "SELECT * FROM scheduled_posts WHERE id = $1", post_id
            )
            
            if not post_data:
                logger.error(f"[UPDATE_STATUS] Post with ID {post_id} not found")
                return False
            
            # Prepare update data
            update_data = {
                "status": status,
                "updated_at": datetime.now()
            }
            
            # Increment retry count if status is 'retry'
            if status == "retry":
                update_data["retries"] = (post_data.get("retries", 0) or 0) + 1
            
            # Store result data if provided
            if result and isinstance(result, dict):
                current_payload = post_data.get("post_payload") or {}
                if "error" in result:
                    current_payload["last_error"] = result["error"]
                    current_payload["last_error_time"] = datetime.now().isoformat()
                if "platform_post_id" in result:
                    current_payload["platform_post_id"] = result["platform_post_id"]
                update_data["post_payload"] = json.dumps(current_payload)
            
            # Build dynamic update query
            set_clauses = []
            values = []
            param_count = 1
            
            for key, value in update_data.items():
                set_clauses.append(f"{key} = ${param_count}")
                values.append(value)
                param_count += 1
            
            values.append(post_id)  # For WHERE clause
            
            query = f"""
                UPDATE scheduled_posts 
                SET {', '.join(set_clauses)}
                WHERE id = ${param_count}
                RETURNING *
            """
            
            updated_post = await conn.fetchrow(query, *values)
            
            if updated_post:
                # Invalidate related caches
                user_id = updated_post.get("user_id")
                if user_id:
                    await SchedulerCacheService.invalidate_user_cache(user_id)
                
                # Update post status metrics in Redis
                await update_post_metrics(status, post_data.get("platform"))
                
                logger.info(f"[UPDATE_STATUS] Post {post_id} updated to status: {status}")
                return True
            
        return False
        
    except Exception as e:
        logger.exception(f"[UPDATE_STATUS] Failed to update post {post_id}: {e}")
        return False

async def update_post_metrics(status: str, platform: str):
    """Update post status metrics in Redis"""
    try:
        async with RedisManager.get_connection() as redis:
            # Update platform-specific metrics
            await redis.incr(f"post_metrics:{platform}:{status}")
            await redis.expire(f"post_metrics:{platform}:{status}", 86400)  # 24 hours
            
            # Update daily metrics
            today = datetime.now().strftime("%Y-%m-%d")
            await redis.incr(f"post_daily:{today}:{status}")
            await redis.expire(f"post_daily:{today}:{status}", 86400 * 7)  # 7 days
            
            # Update hourly metrics for real-time monitoring
            current_hour = datetime.now().strftime("%Y-%m-%d:%H")
            await redis.incr(f"post_hourly:{current_hour}:{status}")
            await redis.expire(f"post_hourly:{current_hour}:{status}", 3600 * 24)  # 24 hours
            
    except Exception as e:
        logger.error(f"Failed to update post metrics: {e}")

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def schedule_post(self, platform, user_token, post_payload, post_id=None):
    """
    Runs when a scheduled post needs to be published with optimization features.
    Retries up to 3 times if fails, based on platform-specific retry logic.
    
    Args:
        platform: The social platform to post to
        user_token: Authentication tokens for the platform
        post_payload: Content and media to post
        post_id: Optional ID of the ScheduledPost in the database
    """
    logger.info(f"[SCHEDULE_POST] Posting on platform: {platform} (optimized)")

    async def async_schedule_post():
        try:
            # Check platform posting limits before attempting
            limits_info = await SchedulerCacheService.get_platform_posting_limits(platform)
            if not limits_info.get("can_post", True):
                error_msg = f"Platform {platform} has reached posting limits"
                logger.warning(f"[SCHEDULE_POST] {error_msg}")
                return {"success": False, "error": error_msg, "retry": True}
            
            # Record posting attempt
            await record_posting_attempt(platform, post_id)
            
            # Call the platform-specific posting function
            result = post_to_platform(platform, user_token, post_payload)
            
            # Check if the post was successful
            if result.get("success", False):
                logger.info(f"[SCHEDULE_POST] Post success for {platform} — Response: {result}")
                
                # Update post status in database if post_id is provided
                if post_id:
                    await update_post_status(post_id, "success", result)
                
                # Update success metrics and cache
                await update_platform_success_metrics(platform)
                
                return result
            else:
                # Post failed, check if we should retry
                error_msg = result.get("error", "Unknown error")
                should_retry = result.get("retry", True)
                
                logger.error(f"[SCHEDULE_POST] Post failed for {platform}: {error_msg}")
                
                if should_retry and self.request.retries < self.max_retries:
                    # Intelligent retry delay based on platform and error type
                    retry_delay = calculate_retry_delay(platform, error_msg, self.request.retries)
                    logger.info(f"[SCHEDULE_POST] Retrying in {retry_delay}s (attempt {self.request.retries + 1}/{self.max_retries})")
                    
                    # Update post status in database if post_id is provided
                    if post_id:
                        await update_post_status(post_id, "retry", result)
                    
                    # Update retry metrics
                    await update_platform_retry_metrics(platform, error_msg)
                    
                    raise self.retry(countdown=retry_delay)
                else:
                    # Max retries exceeded or platform says don't retry
                    logger.critical(f"[SCHEDULE_POST] {'Max retries exceeded' if self.request.retries >= self.max_retries else 'Platform says do not retry'} for {platform}")
                    
                    # Update post status in database if post_id is provided
                    if post_id:
                        await update_post_status(post_id, "failed", result)
                    
                    # Update failure metrics
                    await update_platform_failure_metrics(platform, error_msg)
                    
                    return result

        except Exception as e:
            logger.exception(f"[SCHEDULE_POST] Unexpected error for {platform}: {e}")
            
            # Update post status in database if post_id is provided
            if post_id:
                await update_post_status(post_id, "retry", {"error": str(e), "retry": True})
            
            try:
                self.retry(exc=e)
            except self.MaxRetriesExceededError:
                logger.critical(f"[SCHEDULE_POST] Max retries exceeded for platform: {platform}")
                
                # Update post status in database if post_id is provided
                if post_id:
                    await update_post_status(post_id, "failed", {"error": str(e)})
                
                return {"success": False, "error": str(e), "retry": False}
    
    # Run the async function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(async_schedule_post())
    finally:
        loop.close()

async def record_posting_attempt(platform: str, post_id: int = None):
    """Record posting attempt for analytics"""
    try:
        async with RedisManager.get_connection() as redis:
            # Record attempt
            await redis.incr(f"posting_attempts:{platform}")
            await redis.expire(f"posting_attempts:{platform}", 86400)
            
            # Record hourly attempts
            current_hour = datetime.now().strftime("%Y-%m-%d:%H")
            await redis.incr(f"posting_attempts_hourly:{platform}:{current_hour}")
            await redis.expire(f"posting_attempts_hourly:{platform}:{current_hour}", 3600 * 24)
            
    except Exception as e:
        logger.error(f"Failed to record posting attempt: {e}")

def calculate_retry_delay(platform: str, error_msg: str, retry_count: int) -> int:
    """Calculate intelligent retry delay based on platform and error type"""
    base_delay = 60 * (2 ** retry_count)  # Exponential backoff: 60s, 120s, 240s
    
    # Platform-specific adjustments
    platform_multipliers = {
        "instagram": 1.5,  # Instagram is more strict
        "facebook": 1.2,
        "twitter": 1.0,
        "linkedin": 1.3,
        "tiktok": 1.4,
        "youtube": 2.0     # YouTube uploads take longer
    }
    
    # Error-specific adjustments
    if "rate limit" in error_msg.lower():
        base_delay *= 3  # Wait longer for rate limits
    elif "quota" in error_msg.lower():
        base_delay *= 2
    elif "network" in error_msg.lower() or "timeout" in error_msg.lower():
        base_delay *= 0.5  # Network errors can retry sooner
    
    multiplier = platform_multipliers.get(platform, 1.0)
    return int(base_delay * multiplier)

async def update_platform_success_metrics(platform: str):
    """Update success metrics for platform"""
    try:
        async with RedisManager.get_connection() as redis:
            await redis.incr(f"platform_success:{platform}")
            await redis.expire(f"platform_success:{platform}", 86400)
            
            # Update success rate cache
            await update_platform_success_rate(platform)
            
    except Exception as e:
        logger.error(f"Failed to update success metrics: {e}")

async def update_platform_retry_metrics(platform: str, error_msg: str):
    """Update retry metrics for platform"""
    try:
        async with RedisManager.get_connection() as redis:
            await redis.incr(f"platform_retries:{platform}")
            await redis.expire(f"platform_retries:{platform}", 86400)
            
            # Track error types
            error_type = "rate_limit" if "rate limit" in error_msg.lower() else "other"
            await redis.incr(f"platform_errors:{platform}:{error_type}")
            await redis.expire(f"platform_errors:{platform}:{error_type}", 86400)
            
    except Exception as e:
        logger.error(f"Failed to update retry metrics: {e}")

async def update_platform_failure_metrics(platform: str, error_msg: str):
    """Update failure metrics for platform"""
    try:
        async with RedisManager.get_connection() as redis:
            await redis.incr(f"platform_failures:{platform}")
            await redis.expire(f"platform_failures:{platform}", 86400)
            
            # Update success rate cache
            await update_platform_success_rate(platform)
            
    except Exception as e:
        logger.error(f"Failed to update failure metrics: {e}")

async def update_platform_success_rate(platform: str):
    """Calculate and cache platform success rate"""
    try:
        async with RedisManager.get_connection() as redis:
            success = int(await redis.get(f"platform_success:{platform}") or 0)
            failures = int(await redis.get(f"platform_failures:{platform}") or 0)
            
            total = success + failures
            success_rate = (success / total * 100) if total > 0 else 0
            
            await redis.set(f"platform_success_rate:{platform}", success_rate, ex=3600)
            
    except Exception as e:
        logger.error(f"Failed to update success rate: {e}")


@shared_task
def auto_refresh_tokens():
    """
    Periodic Celery Beat task:
    Refresh tokens for all supported platforms with optimization and caching.
    
    This task runs every 2 hours and refreshes tokens for all platforms.
    Each platform's refresh function handles its own errors and returns success/failure.
    """
    logger.info("[REFRESH] Starting optimized refresh of all platform tokens...")
    
    async def async_refresh_tokens():
        results = {}
        refresh_stats = {
            "start_time": datetime.now().isoformat(),
            "platforms": {}
        }

        try:
            # Check if refresh is needed based on cache
            refresh_needed = await check_refresh_needed()
            if not refresh_needed:
                logger.info("[REFRESH] Token refresh not needed based on cache")
                return {"skipped": True, "reason": "not_needed"}
            
            # Run each refresh function and track results with timing
            platforms = [
                ("meta", refresh_meta_token),
                ("linkedin", refresh_linkedin_token),
                ("twitter", refresh_twitter_token),
                ("youtube", refresh_youtube_token),
                ("tiktok", refresh_tiktok_token)
            ]
            
            for platform_name, refresh_func in platforms:
                start_time = datetime.now()
                try:
                    result = refresh_func()
                    results[platform_name] = result
                    
                    # Record timing and result
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    
                    refresh_stats["platforms"][platform_name] = {
                        "success": result,
                        "duration": duration,
                        "timestamp": end_time.isoformat()
                    }
                    
                    # Update platform-specific refresh metrics
                    await update_refresh_metrics(platform_name, result, duration)
                    
                except Exception as e:
                    logger.exception(f"[REFRESH] Error refreshing {platform_name}: {e}")
                    results[platform_name] = False
                    refresh_stats["platforms"][platform_name] = {
                        "success": False,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    }
                    await update_refresh_metrics(platform_name, False, 0)
            
            # Count successes and failures
            success_count = sum(1 for result in results.values() if result is True)
            failure_count = sum(1 for result in results.values() if result is False)
            
            refresh_stats["summary"] = {
                "total": len(results),
                "success": success_count,
                "failed": failure_count,
                "success_rate": (success_count / len(results) * 100) if results else 0,
                "end_time": datetime.now().isoformat()
            }
            
            # Cache refresh results
            await cache_refresh_results(refresh_stats)
            
            if failure_count == 0:
                logger.info(f"[REFRESH] All tokens refreshed successfully ({success_count}/{len(results)})")  
            else:
                logger.warning(f"[REFRESH] Token refresh completed with some failures. Success: {success_count}, Failed: {failure_count}")
                
            # Log individual platform results
            for platform, result in results.items():
                logger.info(f"[REFRESH] {platform}: {'Success' if result else 'Failed'}")
            
            # Update next refresh time in cache
            await update_next_refresh_time()
                
        except Exception as e:
            logger.exception(f"[REFRESH] Unexpected error during token refresh: {e}")
            refresh_stats["error"] = str(e)
            await cache_refresh_results(refresh_stats)
            
        return results
    
    # Run the async function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(async_refresh_tokens())
    finally:
        loop.close()

async def check_refresh_needed() -> bool:
    """Check if token refresh is needed based on cache and timing"""
    try:
        async with RedisManager.get_connection() as redis:
            last_refresh = await redis.get("token_refresh:last_time")
            if not last_refresh:
                return True
            
            last_refresh_time = datetime.fromisoformat(last_refresh)
            time_since_refresh = datetime.now() - last_refresh_time
            
            # Refresh every 2 hours, but allow early refresh if there were failures
            if time_since_refresh.total_seconds() < 7200:  # 2 hours
                last_stats = await redis.get("token_refresh:last_stats")
                if last_stats:
                    stats = json.loads(last_stats)
                    success_rate = stats.get("summary", {}).get("success_rate", 100)
                    if success_rate < 100:  # Had failures, allow early refresh
                        return time_since_refresh.total_seconds() > 1800  # 30 minutes
                return False
            
            return True
            
    except Exception as e:
        logger.error(f"Error checking refresh needed: {e}")
        return True  # Default to refresh if check fails

async def update_refresh_metrics(platform: str, success: bool, duration: float):
    """Update refresh metrics in Redis"""
    try:
        async with RedisManager.get_connection() as redis:
            # Update success/failure counters
            status = "success" if success else "failed"
            await redis.incr(f"refresh_metrics:{platform}:{status}")
            await redis.expire(f"refresh_metrics:{platform}:{status}", 86400 * 7)  # 7 days
            
            # Update timing metrics
            if success and duration > 0:
                await redis.lpush(f"refresh_timing:{platform}", duration)
                await redis.ltrim(f"refresh_timing:{platform}", 0, 99)  # Keep last 100 timings
                await redis.expire(f"refresh_timing:{platform}", 86400 * 7)
            
            # Update daily metrics
            today = datetime.now().strftime("%Y-%m-%d")
            await redis.incr(f"refresh_daily:{today}:{platform}:{status}")
            await redis.expire(f"refresh_daily:{today}:{platform}:{status}", 86400 * 30)  # 30 days
            
    except Exception as e:
        logger.error(f"Failed to update refresh metrics: {e}")

async def cache_refresh_results(stats: Dict[str, Any]):
    """Cache refresh results for monitoring"""
    try:
        await RedisManager.cache_set("token_refresh:last_stats", json.dumps(stats), ttl=86400 * 7)
        await RedisManager.cache_set("token_refresh:last_time", datetime.now().isoformat(), ttl=86400 * 7)
        
    except Exception as e:
        logger.error(f"Failed to cache refresh results: {e}")

async def update_next_refresh_time():
    """Update next scheduled refresh time"""
    try:
        next_refresh = datetime.now() + timedelta(hours=2)
        await RedisManager.cache_set("token_refresh:next_time", next_refresh.isoformat(), ttl=86400)
        
    except Exception as e:
        logger.error(f"Failed to update next refresh time: {e}")

async def get_refresh_statistics() -> Dict[str, Any]:
    """Get comprehensive refresh statistics"""
    try:
        stats = {}
        
        async with RedisManager.get_connection() as redis:
            # Get last refresh stats
            last_stats = await redis.get("token_refresh:last_stats")
            if last_stats:
                stats["last_refresh"] = json.loads(last_stats)
            
            # Get next refresh time
            next_time = await redis.get("token_refresh:next_time")
            if next_time:
                stats["next_refresh"] = next_time
            
            # Get platform-specific metrics
            platforms = ["meta", "linkedin", "twitter", "youtube", "tiktok"]
            platform_stats = {}
            
            for platform in platforms:
                success = int(await redis.get(f"refresh_metrics:{platform}:success") or 0)
                failed = int(await redis.get(f"refresh_metrics:{platform}:failed") or 0)
                
                # Get average timing
                timings = await redis.lrange(f"refresh_timing:{platform}", 0, -1)
                avg_timing = sum(float(t) for t in timings) / len(timings) if timings else 0
                
                platform_stats[platform] = {
                    "success_count": success,
                    "failed_count": failed,
                    "success_rate": (success / (success + failed) * 100) if (success + failed) > 0 else 0,
                    "avg_duration": round(avg_timing, 2)
                }
            
            stats["platforms"] = platform_stats
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get refresh statistics: {e}")
        return {"error": str(e)}


@shared_task
def scheduled_post_dispatcher():
    """
    Periodic Celery Beat task:
    Find & dispatch due scheduled posts with optimization and monitoring.
    """
    logger.info("[DISPATCHER] Running optimized scheduled post dispatcher job...")
    
    async def async_dispatcher():
        dispatch_stats = {
            "start_time": datetime.now().isoformat(),
            "posts_found": 0,
            "posts_dispatched": 0,
            "posts_skipped": 0,
            "errors": []
        }
        
        try:
            # Check if dispatcher should run based on queue status
            queue_status = await SchedulerCacheService.get_queue_status()
            if queue_status.get("total_queued", 0) > 1000:  # Too many queued posts
                logger.warning("[DISPATCHER] Queue overloaded, skipping this run")
                dispatch_stats["skipped_reason"] = "queue_overloaded"
                await cache_dispatcher_stats(dispatch_stats)
                return {"skipped": True, "reason": "queue_overloaded"}
            
            # Import here to avoid circular imports
            from app.services.scheduler.celery_beat_scheduler import beat_job
            
            # Run the async beat_job with monitoring
            start_time = datetime.now()
            result = await beat_job()
            end_time = datetime.now()
            
            # Extract results if beat_job returns them
            if isinstance(result, dict):
                dispatch_stats.update(result)
            
            dispatch_stats["duration"] = (end_time - start_time).total_seconds()
            dispatch_stats["end_time"] = end_time.isoformat()
            dispatch_stats["success"] = True
            
            # Update dispatcher metrics
            await update_dispatcher_metrics(dispatch_stats)
            
            # Cache results for monitoring
            await cache_dispatcher_stats(dispatch_stats)
            
            logger.info(f"[DISPATCHER] Completed successfully. Duration: {dispatch_stats['duration']:.2f}s")
            
            return dispatch_stats
            
        except Exception as e:
            logger.exception(f"[DISPATCHER] Error during dispatcher: {e}")
            dispatch_stats["error"] = str(e)
            dispatch_stats["success"] = False
            dispatch_stats["end_time"] = datetime.now().isoformat()
            
            await cache_dispatcher_stats(dispatch_stats)
            await update_dispatcher_error_metrics(str(e))
            
            return {"error": str(e)}
    
    # Run the async function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(async_dispatcher())
    finally:
        loop.close()

async def update_dispatcher_metrics(stats: Dict[str, Any]):
    """Update dispatcher performance metrics"""
    try:
        async with RedisManager.get_connection() as redis:
            # Update run counters
            await redis.incr("dispatcher_metrics:total_runs")
            await redis.expire("dispatcher_metrics:total_runs", 86400 * 30)  # 30 days
            
            if stats.get("success"):
                await redis.incr("dispatcher_metrics:successful_runs")
                await redis.expire("dispatcher_metrics:successful_runs", 86400 * 30)
                
                # Track timing
                duration = stats.get("duration", 0)
                await redis.lpush("dispatcher_timing", duration)
                await redis.ltrim("dispatcher_timing", 0, 99)  # Keep last 100 timings
                await redis.expire("dispatcher_timing", 86400 * 7)
                
                # Track posts processed
                posts_dispatched = stats.get("posts_dispatched", 0)
                if posts_dispatched > 0:
                    await redis.lpush("dispatcher_posts_count", posts_dispatched)
                    await redis.ltrim("dispatcher_posts_count", 0, 99)
                    await redis.expire("dispatcher_posts_count", 86400 * 7)
            else:
                await redis.incr("dispatcher_metrics:failed_runs")
                await redis.expire("dispatcher_metrics:failed_runs", 86400 * 30)
            
            # Update hourly metrics
            current_hour = datetime.now().strftime("%Y-%m-%d:%H")
            await redis.incr(f"dispatcher_hourly:{current_hour}")
            await redis.expire(f"dispatcher_hourly:{current_hour}", 3600 * 24)
            
    except Exception as e:
        logger.error(f"Failed to update dispatcher metrics: {e}")

async def update_dispatcher_error_metrics(error_msg: str):
    """Update dispatcher error metrics"""
    try:
        async with RedisManager.get_connection() as redis:
            # Categorize error types
            error_type = "unknown"
            if "connection" in error_msg.lower() or "network" in error_msg.lower():
                error_type = "network"
            elif "database" in error_msg.lower() or "sql" in error_msg.lower():
                error_type = "database"
            elif "timeout" in error_msg.lower():
                error_type = "timeout"
            elif "memory" in error_msg.lower():
                error_type = "memory"
            
            await redis.incr(f"dispatcher_errors:{error_type}")
            await redis.expire(f"dispatcher_errors:{error_type}", 86400 * 7)
            
    except Exception as e:
        logger.error(f"Failed to update dispatcher error metrics: {e}")

async def cache_dispatcher_stats(stats: Dict[str, Any]):
    """Cache dispatcher statistics for monitoring"""
    try:
        await RedisManager.cache_set("dispatcher:last_run", json.dumps(stats), ttl=86400)
        
        # Keep history of last 10 runs
        await RedisManager.cache_list_push("dispatcher:run_history", json.dumps(stats), max_length=10, ttl=86400 * 7)
        
    except Exception as e:
        logger.error(f"Failed to cache dispatcher stats: {e}")

async def get_dispatcher_statistics() -> Dict[str, Any]:
    """Get comprehensive dispatcher statistics"""
    try:
        stats = {}
        
        async with RedisManager.get_connection() as redis:
            # Get basic metrics
            total_runs = int(await redis.get("dispatcher_metrics:total_runs") or 0)
            successful_runs = int(await redis.get("dispatcher_metrics:successful_runs") or 0)
            failed_runs = int(await redis.get("dispatcher_metrics:failed_runs") or 0)
            
            stats["summary"] = {
                "total_runs": total_runs,
                "successful_runs": successful_runs,
                "failed_runs": failed_runs,
                "success_rate": (successful_runs / total_runs * 100) if total_runs > 0 else 0
            }
            
            # Get timing statistics
            timings = await redis.lrange("dispatcher_timing", 0, -1)
            if timings:
                timing_values = [float(t) for t in timings]
                stats["performance"] = {
                    "avg_duration": round(sum(timing_values) / len(timing_values), 2),
                    "min_duration": round(min(timing_values), 2),
                    "max_duration": round(max(timing_values), 2),
                    "recent_runs": len(timing_values)
                }
            
            # Get posts processed statistics
            posts_counts = await redis.lrange("dispatcher_posts_count", 0, -1)
            if posts_counts:
                count_values = [int(c) for c in posts_counts]
                stats["posts"] = {
                    "avg_posts_per_run": round(sum(count_values) / len(count_values), 1),
                    "max_posts_per_run": max(count_values),
                    "total_recent_posts": sum(count_values)
                }
            
            # Get error statistics
            error_types = ["network", "database", "timeout", "memory", "unknown"]
            error_stats = {}
            for error_type in error_types:
                count = int(await redis.get(f"dispatcher_errors:{error_type}") or 0)
                if count > 0:
                    error_stats[error_type] = count
            
            if error_stats:
                stats["errors"] = error_stats
            
            # Get last run info
            last_run = await redis.get("dispatcher:last_run")
            if last_run:
                stats["last_run"] = json.loads(last_run)
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get dispatcher statistics: {e}")
        return {"error": str(e)}
    logger.info("[DISPATCHER] Dispatcher finished.")
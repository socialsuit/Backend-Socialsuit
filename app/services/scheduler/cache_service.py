"""
Scheduler Cache Service
======================

This service provides intelligent caching for scheduler data with Redis,
optimizing scheduled post retrieval and reducing database load.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

from app.services.database.redis import RedisManager, redis_cache
from app.services.database.mongodb import MongoDBManager
from app.services.database.postgresql import get_db_connection
from app.services.database.optimization_service import DatabaseOptimizationService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SchedulerCacheService:
    """
    Intelligent caching service for scheduler data with different TTL strategies
    based on data type and access patterns.
    """
    
    # Cache TTL configurations (in seconds)
    CACHE_TTL = {
        "scheduled_posts": 300,    # 5 minutes for scheduled posts
        "user_schedule": 1800,     # 30 minutes for user schedule data
        "platform_limits": 3600,  # 1 hour for platform posting limits
        "optimal_times": 7200,    # 2 hours for optimal posting times
        "queue_status": 60,       # 1 minute for queue status
        "retry_posts": 300,       # 5 minutes for retry posts
        "posting_history": 1800   # 30 minutes for posting history
    }
    
    @classmethod
    @DatabaseOptimizationService.intelligent_cache("scheduled_posts")
    async def get_scheduled_posts(cls, user_id: str = None, platform: str = None, 
                                status: str = None, limit: int = 100) -> Dict[str, Any]:
        """Get cached scheduled posts with optimization"""
        return await DatabaseOptimizationService.get_optimized_scheduled_posts(
            user_id, platform, status, limit
        )
    
    @classmethod
    @redis_cache(ttl_seconds=CACHE_TTL["user_schedule"], key_prefix="scheduler:user_schedule")
    async def get_user_schedule_overview(cls, user_id: str, days: int = 7) -> Dict[str, Any]:
        """Get comprehensive user schedule overview"""
        
        # Advanced aggregation for user schedule
        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "scheduled_time": {
                        "$gte": datetime.now(),
                        "$lte": datetime.now() + timedelta(days=days)
                    }
                }
            },
            {
                "$facet": {
                    "posts_by_platform": [
                        {
                            "$group": {
                                "_id": "$platform",
                                "count": {"$sum": 1},
                                "next_post": {"$min": "$scheduled_time"}
                            }
                        },
                        {"$sort": {"count": -1}}
                    ],
                    "posts_by_day": [
                        {
                            "$group": {
                                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$scheduled_time"}},
                                "count": {"$sum": 1},
                                "platforms": {"$addToSet": "$platform"}
                            }
                        },
                        {"$sort": {"_id": 1}}
                    ],
                    "posts_by_status": [
                        {
                            "$group": {
                                "_id": "$status",
                                "count": {"$sum": 1}
                            }
                        }
                    ],
                    "upcoming_posts": [
                        {"$sort": {"scheduled_time": 1}},
                        {"$limit": 10},
                        {
                            "$project": {
                                "platform": 1,
                                "scheduled_time": 1,
                                "content_preview": {"$substr": ["$content", 0, 100]},
                                "status": 1
                            }
                        }
                    ]
                }
            }
        ]
        
        results = await MongoDBManager.aggregate("scheduled_posts", pipeline)
        
        if results:
            return {
                "user_id": user_id,
                "days": days,
                "posts_by_platform": results[0].get("posts_by_platform", []),
                "posts_by_day": results[0].get("posts_by_day", []),
                "posts_by_status": results[0].get("posts_by_status", []),
                "upcoming_posts": results[0].get("upcoming_posts", []),
                "timestamp": datetime.now().isoformat()
            }
        
        return {"error": "No schedule data found"}
    
    @classmethod
    @redis_cache(ttl_seconds=CACHE_TTL["platform_limits"], key_prefix="scheduler:platform_limits")
    async def get_platform_posting_limits(cls, platform: str) -> Dict[str, Any]:
        """Get cached platform posting limits and current usage"""
        
        # Platform-specific limits (these could be stored in database)
        platform_limits = {
            "instagram": {"daily": 25, "hourly": 5},
            "facebook": {"daily": 50, "hourly": 10},
            "twitter": {"daily": 300, "hourly": 50},
            "linkedin": {"daily": 20, "hourly": 3},
            "tiktok": {"daily": 10, "hourly": 2},
            "youtube": {"daily": 5, "hourly": 1}
        }
        
        limits = platform_limits.get(platform, {"daily": 10, "hourly": 2})
        
        # Get current usage from last 24 hours and last hour
        now = datetime.now()
        daily_pipeline = [
            {
                "$match": {
                    "platform": platform,
                    "posted_at": {"$gte": now - timedelta(days=1)},
                    "status": "success"
                }
            },
            {"$count": "daily_posts"}
        ]
        
        hourly_pipeline = [
            {
                "$match": {
                    "platform": platform,
                    "posted_at": {"$gte": now - timedelta(hours=1)},
                    "status": "success"
                }
            },
            {"$count": "hourly_posts"}
        ]
        
        daily_result = await MongoDBManager.aggregate("posted_content", daily_pipeline)
        hourly_result = await MongoDBManager.aggregate("posted_content", hourly_pipeline)
        
        daily_usage = daily_result[0]["daily_posts"] if daily_result else 0
        hourly_usage = hourly_result[0]["hourly_posts"] if hourly_result else 0
        
        return {
            "platform": platform,
            "limits": limits,
            "usage": {
                "daily": daily_usage,
                "hourly": hourly_usage
            },
            "remaining": {
                "daily": max(0, limits["daily"] - daily_usage),
                "hourly": max(0, limits["hourly"] - hourly_usage)
            },
            "can_post": daily_usage < limits["daily"] and hourly_usage < limits["hourly"],
            "timestamp": datetime.now().isoformat()
        }
    
    @classmethod
    @redis_cache(ttl_seconds=CACHE_TTL["optimal_times"], key_prefix="scheduler:optimal_times")
    async def get_optimal_posting_times(cls, user_id: str, platform: str) -> Dict[str, Any]:
        """Get cached optimal posting times based on historical performance"""
        
        # Analyze historical performance to find optimal times
        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "platform": platform,
                    "posted_at": {"$gte": datetime.now() - timedelta(days=90)}
                }
            },
            {
                "$addFields": {
                    "hour": {"$hour": "$posted_at"},
                    "day_of_week": {"$dayOfWeek": "$posted_at"}
                }
            },
            {
                "$group": {
                    "_id": {
                        "hour": "$hour",
                        "day_of_week": "$day_of_week"
                    },
                    "avg_engagement": {"$avg": "$engagement_score"},
                    "post_count": {"$sum": 1},
                    "total_engagement": {"$sum": "$engagement_score"}
                }
            },
            {
                "$match": {
                    "post_count": {"$gte": 3}  # Only consider times with at least 3 posts
                }
            },
            {
                "$sort": {"avg_engagement": -1}
            },
            {"$limit": 20}
        ]
        
        results = await MongoDBManager.aggregate("posted_content", pipeline)
        
        # Group by day of week
        optimal_times = {}
        day_names = ["", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        
        for result in results:
            day_of_week = result["_id"]["day_of_week"]
            hour = result["_id"]["hour"]
            day_name = day_names[day_of_week]
            
            if day_name not in optimal_times:
                optimal_times[day_name] = []
            
            optimal_times[day_name].append({
                "hour": hour,
                "avg_engagement": round(result["avg_engagement"], 2),
                "post_count": result["post_count"],
                "confidence": min(100, (result["post_count"] / 10) * 100)  # Confidence based on sample size
            })
        
        # Sort each day's times by engagement
        for day in optimal_times:
            optimal_times[day] = sorted(optimal_times[day], key=lambda x: x["avg_engagement"], reverse=True)[:5]
        
        return {
            "user_id": user_id,
            "platform": platform,
            "optimal_times": optimal_times,
            "analysis_period_days": 90,
            "timestamp": datetime.now().isoformat()
        }
    
    @classmethod
    @redis_cache(ttl_seconds=CACHE_TTL["queue_status"], key_prefix="scheduler:queue_status")
    async def get_queue_status(cls) -> Dict[str, Any]:
        """Get current scheduler queue status"""
        
        # Get queue statistics from Redis/Celery
        try:
            async with RedisManager.get_connection() as redis:
                # Get Celery queue information
                queue_info = {}
                
                # Check different queue lengths
                queues = ["celery", "scheduler", "high_priority", "low_priority"]
                for queue in queues:
                    length = await redis.llen(queue)
                    queue_info[queue] = length
                
                # Get active tasks count (approximate)
                active_tasks = await redis.get("celery:active_tasks") or 0
                
                # Get failed tasks count
                failed_tasks = await redis.get("celery:failed_tasks") or 0
                
                return {
                    "queue_lengths": queue_info,
                    "active_tasks": int(active_tasks),
                    "failed_tasks": int(failed_tasks),
                    "total_queued": sum(queue_info.values()),
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to get queue status: {e}")
            return {"error": str(e)}
    
    @classmethod
    @redis_cache(ttl_seconds=CACHE_TTL["retry_posts"], key_prefix="scheduler:retry_posts")
    async def get_retry_posts(cls, user_id: str = None) -> Dict[str, Any]:
        """Get posts that need to be retried"""
        
        match_query = {"status": "retry"}
        if user_id:
            match_query["user_id"] = user_id
        
        pipeline = [
            {"$match": match_query},
            {
                "$facet": {
                    "by_platform": [
                        {
                            "$group": {
                                "_id": "$platform",
                                "count": {"$sum": 1},
                                "avg_retries": {"$avg": "$retry_count"}
                            }
                        },
                        {"$sort": {"count": -1}}
                    ],
                    "by_error_type": [
                        {
                            "$group": {
                                "_id": "$last_error_type",
                                "count": {"$sum": 1}
                            }
                        },
                        {"$sort": {"count": -1}}
                    ],
                    "recent_failures": [
                        {"$sort": {"last_retry_at": -1}},
                        {"$limit": 10},
                        {
                            "$project": {
                                "platform": 1,
                                "retry_count": 1,
                                "last_error": 1,
                                "scheduled_time": 1,
                                "last_retry_at": 1
                            }
                        }
                    ]
                }
            }
        ]
        
        results = await MongoDBManager.aggregate("scheduled_posts", pipeline)
        
        if results:
            return {
                "user_id": user_id,
                "by_platform": results[0].get("by_platform", []),
                "by_error_type": results[0].get("by_error_type", []),
                "recent_failures": results[0].get("recent_failures", []),
                "timestamp": datetime.now().isoformat()
            }
        
        return {"error": "No retry posts found"}
    
    @classmethod
    @redis_cache(ttl_seconds=CACHE_TTL["posting_history"], key_prefix="scheduler:posting_history")
    async def get_posting_history(cls, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get posting history and success rates"""
        
        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "posted_at": {"$gte": datetime.now() - timedelta(days=days)}
                }
            },
            {
                "$facet": {
                    "success_rates": [
                        {
                            "$group": {
                                "_id": {
                                    "platform": "$platform",
                                    "status": "$status"
                                },
                                "count": {"$sum": 1}
                            }
                        },
                        {
                            "$group": {
                                "_id": "$_id.platform",
                                "statuses": {
                                    "$push": {
                                        "status": "$_id.status",
                                        "count": "$count"
                                    }
                                },
                                "total": {"$sum": "$count"}
                            }
                        }
                    ],
                    "daily_activity": [
                        {
                            "$group": {
                                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$posted_at"}},
                                "successful_posts": {
                                    "$sum": {"$cond": [{"$eq": ["$status", "success"]}, 1, 0]}
                                },
                                "failed_posts": {
                                    "$sum": {"$cond": [{"$eq": ["$status", "failed"]}, 1, 0]}
                                },
                                "total_posts": {"$sum": 1}
                            }
                        },
                        {"$sort": {"_id": 1}}
                    ],
                    "performance_metrics": [
                        {
                            "$group": {
                                "_id": null,
                                "total_posts": {"$sum": 1},
                                "successful_posts": {
                                    "$sum": {"$cond": [{"$eq": ["$status", "success"]}, 1, 0]}
                                },
                                "failed_posts": {
                                    "$sum": {"$cond": [{"$eq": ["$status", "failed"]}, 1, 0]}
                                },
                                "avg_engagement": {"$avg": "$engagement_score"}
                            }
                        }
                    ]
                }
            }
        ]
        
        results = await MongoDBManager.aggregate("posted_content", pipeline)
        
        if results:
            performance = results[0].get("performance_metrics", [{}])[0]
            success_rate = 0
            if performance.get("total_posts", 0) > 0:
                success_rate = (performance.get("successful_posts", 0) / performance.get("total_posts", 1)) * 100
            
            return {
                "user_id": user_id,
                "days": days,
                "success_rates": results[0].get("success_rates", []),
                "daily_activity": results[0].get("daily_activity", []),
                "overall_success_rate": round(success_rate, 2),
                "total_posts": performance.get("total_posts", 0),
                "avg_engagement": round(performance.get("avg_engagement", 0), 2),
                "timestamp": datetime.now().isoformat()
            }
        
        return {"error": "No posting history found"}
    
    @classmethod
    async def invalidate_user_cache(cls, user_id: str):
        """Invalidate all cache entries for a specific user"""
        patterns = [
            f"scheduler:user_schedule:*{user_id}*",
            f"scheduler:optimal_times:*{user_id}*",
            f"scheduler:retry_posts:*{user_id}*",
            f"scheduler:posting_history:*{user_id}*",
            f"scheduled_posts:*{user_id}*"
        ]
        
        for pattern in patterns:
            await RedisManager.cache_delete_pattern(pattern)
        
        logger.info(f"✅ Invalidated scheduler cache for user: {user_id}")
    
    @classmethod
    async def warm_cache_for_user(cls, user_id: str):
        """Pre-warm cache for a user's most common scheduler queries"""
        try:
            # Warm user schedule data
            await cls.get_user_schedule_overview(user_id, 7)
            await cls.get_user_schedule_overview(user_id, 30)
            
            # Get user's platforms and warm platform-specific data
            platforms = await MongoDBManager.find_with_options(
                "scheduled_posts",
                {"user_id": user_id},
                projection={"platform": 1},
                limit=10
            )
            
            unique_platforms = list(set([p.get("platform") for p in platforms if p.get("platform")]))
            
            for platform in unique_platforms:
                await cls.get_platform_posting_limits(platform)
                await cls.get_optimal_posting_times(user_id, platform)
            
            # Warm other data
            await cls.get_retry_posts(user_id)
            await cls.get_posting_history(user_id, 30)
            
            logger.info(f"✅ Scheduler cache warmed for user: {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to warm scheduler cache for user {user_id}: {e}")
    
    @classmethod
    async def get_cache_performance_stats(cls) -> Dict[str, Any]:
        """Get scheduler cache performance statistics"""
        try:
            redis_stats = await RedisManager.get_cache_stats()
            
            # Get scheduler-specific cache key counts
            scheduler_keys = 0
            async with RedisManager.get_connection() as redis:
                cursor = 0
                while True:
                    cursor, keys = await redis.scan(cursor=cursor, match="scheduler:*", count=100)
                    scheduler_keys += len(keys)
                    if cursor == 0:
                        break
            
            return {
                "scheduler_cache_keys": scheduler_keys,
                "redis_stats": redis_stats,
                "cache_ttl_config": cls.CACHE_TTL
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get scheduler cache stats: {e}")
            return {"error": str(e)}
    
    @classmethod
    async def batch_update_scheduler_cache(cls, updates: List[Dict[str, Any]]) -> int:
        """Batch update scheduler cache for multiple operations"""
        try:
            cache_operations = []
            
            for update in updates:
                cache_type = update.get("type")
                data = update.get("data")
                user_id = update.get("user_id")
                
                if cache_type and data:
                    cache_key = f"scheduler:{cache_type}:{user_id}" if user_id else f"scheduler:{cache_type}"
                    ttl = cls.CACHE_TTL.get(cache_type, 1800)
                    
                    cache_operations.append({
                        "key": cache_key,
                        "value": data,
                        "ttl": ttl
                    })
            
            count = await RedisManager.warm_cache_batch(cache_operations)
            logger.info(f"✅ Batch updated {count} scheduler cache entries")
            
            return count
            
        except Exception as e:
            logger.error(f"❌ Failed to batch update scheduler cache: {e}")
            return 0
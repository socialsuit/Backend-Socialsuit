"""
Analytics Cache Service
======================

This service provides intelligent caching for analytics data with Redis,
reducing database load and improving response times for frequently accessed data.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

from app.services.database.redis import RedisManager, redis_cache
from app.services.database.mongodb import MongoDBManager
from app.services.database.optimization_service import DatabaseOptimizationService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AnalyticsCacheService:
    """
    Intelligent caching service for analytics data with different TTL strategies
    based on data type and access patterns.
    """
    
    # Cache TTL configurations (in seconds)
    CACHE_TTL = {
        "overview": 3600,      # 1 hour for overview data
        "platform": 1800,     # 30 minutes for platform insights
        "chart": 1800,        # 30 minutes for chart data
        "content": 3600,      # 1 hour for content performance
        "realtime": 300,      # 5 minutes for real-time data
        "historical": 7200,   # 2 hours for historical data
        "user_metrics": 1800, # 30 minutes for user metrics
        "engagement": 900     # 15 minutes for engagement data
    }
    
    @classmethod
    @DatabaseOptimizationService.intelligent_cache("analytics_overview")
    async def get_user_overview(cls, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get cached user analytics overview with advanced optimization"""
        return await DatabaseOptimizationService.get_optimized_analytics_overview(user_id, days)
    
    @classmethod
    @DatabaseOptimizationService.intelligent_cache("platform_insights")
    async def get_platform_insights(cls, user_id: str, platform: str, days: int = 30) -> Dict[str, Any]:
        """Get cached platform-specific insights with optimization"""
        return await DatabaseOptimizationService.get_optimized_platform_insights(user_id, platform, days)
    
    @classmethod
    @redis_cache(ttl_seconds=CACHE_TTL["chart"], key_prefix="analytics:chart")
    async def get_chart_data(cls, user_id: str, chart_type: str, days: int = 30) -> Dict[str, Any]:
        """Get cached chart data for various visualization types"""
        
        if chart_type == "engagement_timeline":
            pipeline = [
                {
                    "$match": {
                        "user_id": user_id,
                        "timestamp": {"$gte": datetime.now() - timedelta(days=days)}
                    }
                },
                {
                    "$group": {
                        "_id": {
                            "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                            "platform": "$platform"
                        },
                        "daily_engagement": {"$sum": "$engagement_count"}
                    }
                },
                {
                    "$sort": {"_id.date": 1}
                }
            ]
        
        elif chart_type == "content_distribution":
            pipeline = [
                {
                    "$match": {
                        "user_id": user_id,
                        "timestamp": {"$gte": datetime.now() - timedelta(days=days)}
                    }
                },
                {
                    "$group": {
                        "_id": {
                            "content_type": "$content_type",
                            "platform": "$platform"
                        },
                        "count": {"$sum": 1},
                        "avg_engagement": {"$avg": "$engagement_count"}
                    }
                }
            ]
        
        elif chart_type == "hourly_engagement":
            pipeline = [
                {
                    "$match": {
                        "user_id": user_id,
                        "timestamp": {"$gte": datetime.now() - timedelta(days=days)}
                    }
                },
                {
                    "$group": {
                        "_id": {"$hour": "$timestamp"},
                        "avg_engagement": {"$avg": "$engagement_count"},
                        "total_posts": {"$sum": 1}
                    }
                },
                {
                    "$sort": {"_id": 1}
                }
            ]
        
        elif chart_type == "growth_trend":
            pipeline = [
                {
                    "$match": {
                        "user_id": user_id,
                        "timestamp": {"$gte": datetime.now() - timedelta(days=days)}
                    }
                },
                {
                    "$group": {
                        "_id": {
                            "week": {"$week": "$timestamp"},
                            "year": {"$year": "$timestamp"},
                            "platform": "$platform"
                        },
                        "weekly_engagement": {"$sum": "$engagement_count"},
                        "weekly_posts": {"$sum": 1}
                    }
                },
                {
                    "$sort": {"_id.year": 1, "_id.week": 1}
                }
            ]
        
        else:
            return {"error": f"Unknown chart type: {chart_type}"}
        
        results = await MongoDBManager.aggregate("analytics_data", pipeline)
        
        return {
            "user_id": user_id,
            "chart_type": chart_type,
            "days": days,
            "data": results,
            "timestamp": datetime.now().isoformat()
        }
    
    @classmethod
    @redis_cache(ttl_seconds=CACHE_TTL["content"], key_prefix="analytics:content")
    async def get_content_performance(cls, user_id: str, platform: str = None, 
                                    limit: int = 50) -> Dict[str, Any]:
        """Get cached content performance data with enhanced metrics"""
        
        match_query = {"user_id": user_id}
        if platform:
            match_query["platform"] = platform
        
        # Use optimized aggregation for content performance
        pipeline = [
            {"$match": match_query},
            {
                "$addFields": {
                    "engagement_rate": {
                        "$cond": [
                            {"$gt": ["$impressions", 0]},
                            {"$multiply": [{"$divide": ["$engagement_count", "$impressions"]}, 100]},
                            0
                        ]
                    }
                }
            },
            {
                "$sort": {"engagement_score": -1}
            },
            {"$limit": limit},
            {
                "$project": {
                    "content_id": 1,
                    "platform": 1,
                    "engagement_score": 1,
                    "engagement_rate": 1,
                    "content_type": 1,
                    "timestamp": 1,
                    "impressions": 1,
                    "engagement_count": 1
                }
            }
        ]
        
        results = await MongoDBManager.aggregate("content_performance", pipeline)
        
        return {
            "user_id": user_id,
            "platform": platform,
            "content": results,
            "timestamp": datetime.now().isoformat()
        }
    
    @classmethod
    @redis_cache(ttl_seconds=CACHE_TTL["user_metrics"], key_prefix="analytics:user_metrics")
    async def get_user_metrics_summary(cls, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive user metrics summary"""
        
        # Advanced aggregation for user metrics
        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "date": {"$gte": datetime.now() - timedelta(days=days)}
                }
            },
            {
                "$facet": {
                    "follower_growth": [
                        {
                            "$group": {
                                "_id": "$platform",
                                "current_followers": {"$last": "$followers_count"},
                                "initial_followers": {"$first": "$followers_count"},
                                "avg_daily_growth": {"$avg": "$daily_follower_change"}
                            }
                        },
                        {
                            "$addFields": {
                                "total_growth": {"$subtract": ["$current_followers", "$initial_followers"]},
                                "growth_rate": {
                                    "$cond": [
                                        {"$gt": ["$initial_followers", 0]},
                                        {"$multiply": [
                                            {"$divide": [
                                                {"$subtract": ["$current_followers", "$initial_followers"]},
                                                "$initial_followers"
                                            ]}, 100
                                        ]},
                                        0
                                    ]
                                }
                            }
                        }
                    ],
                    "engagement_trends": [
                        {
                            "$group": {
                                "_id": {
                                    "platform": "$platform",
                                    "week": {"$week": "$date"}
                                },
                                "avg_engagement_rate": {"$avg": "$engagement_rate"},
                                "total_posts": {"$sum": "$posts_count"}
                            }
                        },
                        {"$sort": {"_id.week": 1}}
                    ],
                    "platform_performance": [
                        {
                            "$group": {
                                "_id": "$platform",
                                "avg_engagement_rate": {"$avg": "$engagement_rate"},
                                "total_posts": {"$sum": "$posts_count"},
                                "total_followers": {"$last": "$followers_count"},
                                "avg_reach": {"$avg": "$reach"}
                            }
                        },
                        {"$sort": {"avg_engagement_rate": -1}}
                    ]
                }
            }
        ]
        
        results = await MongoDBManager.aggregate("user_metrics", pipeline)
        
        if results:
            return {
                "user_id": user_id,
                "days": days,
                "follower_growth": results[0].get("follower_growth", []),
                "engagement_trends": results[0].get("engagement_trends", []),
                "platform_performance": results[0].get("platform_performance", []),
                "timestamp": datetime.now().isoformat()
            }
        
        return {"error": "No metrics data found"}
    
    @classmethod
    @redis_cache(ttl_seconds=CACHE_TTL["engagement"], key_prefix="analytics:engagement")
    async def get_engagement_analytics(cls, user_id: str, platform: str = None, days: int = 7) -> Dict[str, Any]:
        """Get detailed engagement analytics with real-time insights"""
        
        match_query = {
            "user_id": user_id,
            "timestamp": {"$gte": datetime.now() - timedelta(days=days)}
        }
        
        if platform:
            match_query["platform"] = platform
        
        # Real-time engagement analysis
        pipeline = [
            {"$match": match_query},
            {
                "$facet": {
                    "engagement_by_type": [
                        {
                            "$group": {
                                "_id": "$engagement_type",
                                "count": {"$sum": "$engagement_count"},
                                "avg_per_post": {"$avg": "$engagement_count"}
                            }
                        },
                        {"$sort": {"count": -1}}
                    ],
                    "peak_hours": [
                        {
                            "$group": {
                                "_id": {"$hour": "$timestamp"},
                                "total_engagement": {"$sum": "$engagement_count"},
                                "post_count": {"$sum": 1}
                            }
                        },
                        {
                            "$addFields": {
                                "avg_engagement_per_post": {
                                    "$divide": ["$total_engagement", "$post_count"]
                                }
                            }
                        },
                        {"$sort": {"avg_engagement_per_post": -1}}
                    ],
                    "daily_trends": [
                        {
                            "$group": {
                                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                                "total_engagement": {"$sum": "$engagement_count"},
                                "unique_posts": {"$addToSet": "$content_id"},
                                "avg_engagement": {"$avg": "$engagement_count"}
                            }
                        },
                        {
                            "$addFields": {
                                "post_count": {"$size": "$unique_posts"}
                            }
                        },
                        {"$sort": {"_id": 1}}
                    ]
                }
            }
        ]
        
        results = await MongoDBManager.aggregate("user_engagements", pipeline)
        
        if results:
            return {
                "user_id": user_id,
                "platform": platform,
                "days": days,
                "engagement_by_type": results[0].get("engagement_by_type", []),
                "peak_hours": results[0].get("peak_hours", []),
                "daily_trends": results[0].get("daily_trends", []),
                "timestamp": datetime.now().isoformat()
            }
        
        return {"error": "No engagement data found"}
    
    @classmethod
    async def invalidate_user_cache(cls, user_id: str):
        """Invalidate all cache entries for a specific user"""
        patterns = [
            f"analytics:overview:*{user_id}*",
            f"analytics:platform:*{user_id}*",
            f"analytics:chart:*{user_id}*",
            f"analytics:content:*{user_id}*",
            f"analytics:user_metrics:*{user_id}*",
            f"analytics:engagement:*{user_id}*"
        ]
        
        for pattern in patterns:
            await RedisManager.cache_delete_pattern(pattern)
        
        logger.info(f"✅ Invalidated analytics cache for user: {user_id}")
    
    @classmethod
    async def warm_cache_for_user(cls, user_id: str):
        """Pre-warm cache for a user's most common analytics queries"""
        try:
            # Use the optimization service for cache warming
            await DatabaseOptimizationService.warm_cache_for_user(user_id)
            
            # Additional analytics-specific cache warming
            await cls.get_user_metrics_summary(user_id, 30)
            await cls.get_engagement_analytics(user_id, None, 7)
            
            # Get user's platforms and warm platform-specific data
            platforms = await MongoDBManager.find_with_options(
                "analytics_data",
                {"user_id": user_id},
                projection={"platform": 1},
                limit=10
            )
            
            unique_platforms = list(set([p.get("platform") for p in platforms if p.get("platform")]))
            
            for platform in unique_platforms:
                await cls.get_content_performance(user_id, platform, 20)
                await cls.get_engagement_analytics(user_id, platform, 7)
            
            # Warm chart data
            chart_types = ["engagement_timeline", "content_distribution", "hourly_engagement", "growth_trend"]
            for chart_type in chart_types:
                await cls.get_chart_data(user_id, chart_type, 30)
            
            logger.info(f"✅ Enhanced analytics cache warmed for user: {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to warm analytics cache for user {user_id}: {e}")
    
    @classmethod
    async def get_cache_performance_stats(cls) -> Dict[str, Any]:
        """Get analytics cache performance statistics"""
        try:
            redis_stats = await RedisManager.get_cache_stats()
            
            # Get analytics-specific cache key counts
            analytics_keys = 0
            async with RedisManager.get_connection() as redis:
                cursor = 0
                while True:
                    cursor, keys = await redis.scan(cursor=cursor, match="analytics:*", count=100)
                    analytics_keys += len(keys)
                    if cursor == 0:
                        break
            
            return {
                "analytics_cache_keys": analytics_keys,
                "redis_stats": redis_stats,
                "cache_ttl_config": cls.CACHE_TTL
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get analytics cache stats: {e}")
            return {"error": str(e)}
    
    @classmethod
    async def batch_update_analytics_cache(cls, user_updates: List[Dict[str, Any]]) -> int:
        """Batch update analytics cache for multiple users"""
        try:
            cache_operations = []
            
            for update in user_updates:
                user_id = update.get("user_id")
                data_type = update.get("data_type", "overview")
                data = update.get("data")
                
                if user_id and data:
                    cache_key = f"analytics:{data_type}:{user_id}"
                    ttl = cls.CACHE_TTL.get(data_type, 3600)
                    
                    cache_operations.append({
                        "key": cache_key,
                        "value": data,
                        "ttl": ttl
                    })
            
            count = await RedisManager.warm_cache_batch(cache_operations)
            logger.info(f"✅ Batch updated {count} analytics cache entries")
            
            return count
            
        except Exception as e:
            logger.error(f"❌ Failed to batch update analytics cache: {e}")
            return 0
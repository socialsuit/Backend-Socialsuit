"""
Advanced Database Query Optimizer
Provides optimized query patterns, caching strategies, and performance monitoring
for MongoDB, Supabase (PostgreSQL), and Redis across all modules.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from functools import wraps
from contextlib import asynccontextmanager

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import IndexModel, ASCENDING, DESCENDING, TEXT
from sqlalchemy.orm import Session
from sqlalchemy import text, func, and_, or_
import asyncpg

from app.services.database.mongodb import MongoDBManager
from app.services.database.postgresql import get_db_connection
from app.services.database.redis import RedisManager

logger = logging.getLogger(__name__)

class QueryPerformanceMonitor:
    """Monitor and track query performance across all databases"""
    
    def __init__(self):
        self.query_stats = {}
        self.slow_queries = []
        
    def track_query(self, db_type: str, operation: str, duration: float, query_info: str = ""):
        """Track query performance"""
        key = f"{db_type}:{operation}"
        if key not in self.query_stats:
            self.query_stats[key] = {
                "count": 0,
                "total_time": 0,
                "avg_time": 0,
                "max_time": 0,
                "min_time": float('inf')
            }
        
        stats = self.query_stats[key]
        stats["count"] += 1
        stats["total_time"] += duration
        stats["avg_time"] = stats["total_time"] / stats["count"]
        stats["max_time"] = max(stats["max_time"], duration)
        stats["min_time"] = min(stats["min_time"], duration)
        
        # Track slow queries (>500ms)
        if duration > 0.5:
            self.slow_queries.append({
                "db_type": db_type,
                "operation": operation,
                "duration": duration,
                "query_info": query_info,
                "timestamp": datetime.now()
            })
            logger.warning(f"Slow query detected: {db_type}:{operation} took {duration:.2f}s")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        return {
            "query_stats": self.query_stats,
            "slow_queries": self.slow_queries[-50:],  # Last 50 slow queries
            "total_queries": sum(stats["count"] for stats in self.query_stats.values()),
            "avg_query_time": sum(stats["avg_time"] for stats in self.query_stats.values()) / len(self.query_stats) if self.query_stats else 0
        }

# Global performance monitor
performance_monitor = QueryPerformanceMonitor()

def query_performance_tracker(db_type: str, operation: str):
    """Decorator to track query performance"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                performance_monitor.track_query(db_type, operation, duration, str(kwargs.get('query', '')))
                return result
            except Exception as e:
                duration = time.time() - start_time
                performance_monitor.track_query(db_type, f"{operation}_error", duration, str(e))
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                performance_monitor.track_query(db_type, operation, duration, str(kwargs.get('query', '')))
                return result
            except Exception as e:
                duration = time.time() - start_time
                performance_monitor.track_query(db_type, f"{operation}_error", duration, str(e))
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

class MongoQueryOptimizer:
    """Optimized MongoDB query patterns with caching"""
    
    @staticmethod
    async def create_optimized_indexes():
        """Create optimized indexes for all collections"""
        async with MongoDBManager.get_db() as db:
            # User collection indexes
            await db.users.create_indexes([
                IndexModel([("email", ASCENDING)], unique=True),
                IndexModel([("wallet_address", ASCENDING)], unique=True),
                IndexModel([("is_verified", ASCENDING)]),
                IndexModel([("created_at", DESCENDING)]),
                IndexModel([("last_login", DESCENDING)]),
                IndexModel([("email", TEXT), ("username", TEXT)])  # Text search
            ])
            
            # Scheduled posts indexes
            await db.scheduled_posts.create_indexes([
                IndexModel([("user_id", ASCENDING), ("platform", ASCENDING)]),
                IndexModel([("user_id", ASCENDING), ("status", ASCENDING)]),
                IndexModel([("scheduled_time", ASCENDING), ("status", ASCENDING)]),
                IndexModel([("platform", ASCENDING), ("status", ASCENDING)]),
                IndexModel([("created_at", DESCENDING)]),
                IndexModel([("user_id", ASCENDING), ("scheduled_time", ASCENDING)]),
                IndexModel([("status", ASCENDING), ("retries", ASCENDING)])
            ])
            
            # Analytics data indexes
            await db.analytics_data.create_indexes([
                IndexModel([("user_id", ASCENDING), ("platform", ASCENDING), ("timestamp", DESCENDING)]),
                IndexModel([("platform", ASCENDING), ("content_type", ASCENDING)]),
                IndexModel([("timestamp", DESCENDING)]),
                IndexModel([("user_id", ASCENDING), ("timestamp", DESCENDING)]),
                IndexModel([("engagement_score", DESCENDING)]),
                IndexModel([("user_id", ASCENDING), ("platform", ASCENDING), ("date", DESCENDING)])
            ])
            
            # Post engagement indexes
            await db.post_engagements.create_indexes([
                IndexModel([("user_id", ASCENDING), ("platform", ASCENDING), ("timestamp", DESCENDING)]),
                IndexModel([("platform_post_id", ASCENDING), ("platform", ASCENDING)]),
                IndexModel([("engagement_type", ASCENDING), ("timestamp", DESCENDING)]),
                IndexModel([("user_id", ASCENDING), ("engagement_date", DESCENDING)])
            ])
            
            # Content performance indexes
            await db.content_performance.create_indexes([
                IndexModel([("user_id", ASCENDING), ("platform", ASCENDING), ("timestamp", DESCENDING)]),
                IndexModel([("platform_post_id", ASCENDING), ("platform", ASCENDING)], unique=True),
                IndexModel([("engagement_score", DESCENDING)]),
                IndexModel([("content_type", ASCENDING), ("platform", ASCENDING)]),
                IndexModel([("post_date", DESCENDING)])
            ])
            
            # AB tests indexes
            await db.ab_tests.create_indexes([
                IndexModel([("user_id", ASCENDING), ("status", ASCENDING)]),
                IndexModel([("test_id", ASCENDING)], unique=True),
                IndexModel([("start_date", DESCENDING)]),
                IndexModel([("end_date", ASCENDING)]),
                IndexModel([("status", ASCENDING), ("end_date", ASCENDING)])
            ])
            
            logger.info("✅ MongoDB indexes created successfully")
    
    @staticmethod
    @query_performance_tracker("mongodb", "optimized_find")
    async def optimized_find(collection: str, query: Dict[str, Any], 
                           projection: Dict[str, Any] = None,
                           sort: List[Tuple[str, int]] = None,
                           limit: int = 0, skip: int = 0,
                           cache_key: str = None, cache_ttl: int = 300) -> List[Dict[str, Any]]:
        """Optimized find with caching"""
        
        # Try cache first
        if cache_key:
            cached_result = await RedisManager.cache_get(cache_key)
            if cached_result:
                return cached_result
        
        async with MongoDBManager.get_db() as db:
            cursor = db[collection].find(query, projection)
            
            if sort:
                cursor = cursor.sort(sort)
            if skip:
                cursor = cursor.skip(skip)
            if limit:
                cursor = cursor.limit(limit)
            
            result = await cursor.to_list(length=limit if limit else None)
            
            # Cache result
            if cache_key and result:
                await RedisManager.cache_set(cache_key, result, cache_ttl)
            
            return result
    
    @staticmethod
    @query_performance_tracker("mongodb", "optimized_aggregate")
    async def optimized_aggregate(collection: str, pipeline: List[Dict[str, Any]],
                                cache_key: str = None, cache_ttl: int = 300) -> List[Dict[str, Any]]:
        """Optimized aggregation with caching"""
        
        # Try cache first
        if cache_key:
            cached_result = await RedisManager.cache_get(cache_key)
            if cached_result:
                return cached_result
        
        async with MongoDBManager.get_db() as db:
            result = await db[collection].aggregate(pipeline).to_list(None)
            
            # Cache result
            if cache_key and result:
                await RedisManager.cache_set(cache_key, result, cache_ttl)
            
            return result

class PostgreSQLQueryOptimizer:
    """Optimized PostgreSQL query patterns with caching"""
    
    @staticmethod
    async def create_optimized_indexes():
        """Create optimized indexes for PostgreSQL tables"""
        indexes = [
            # Users table
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_wallet_address ON users(wallet_address)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_is_verified ON users(is_verified)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_created_at ON users(created_at DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_last_login ON users(last_login DESC)",
            
            # Scheduled posts table
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scheduled_posts_user_platform ON scheduled_posts(user_id, platform)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scheduled_posts_user_status ON scheduled_posts(user_id, status)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scheduled_posts_scheduled_time_status ON scheduled_posts(scheduled_time, status)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scheduled_posts_platform_status ON scheduled_posts(platform, status)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scheduled_posts_created_at ON scheduled_posts(created_at DESC)",
            
            # Post engagements table
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_post_engagements_user_platform_timestamp ON post_engagements(user_id, platform, timestamp DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_post_engagements_platform_post_id ON post_engagements(platform_post_id, platform)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_post_engagements_engagement_type_timestamp ON post_engagements(engagement_type, timestamp DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_post_engagements_user_engagement_date ON post_engagements(user_id, engagement_date DESC)",
            
            # User metrics table
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_metrics_user_platform_timestamp ON user_metrics(user_id, platform, timestamp DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_metrics_platform_date ON user_metrics(platform, date DESC)",
            
            # Content performance table
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_performance_user_platform_timestamp ON content_performance(user_id, platform, timestamp DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_performance_platform_post_id ON content_performance(platform_post_id, platform)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_performance_engagement_score ON content_performance(engagement_score DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_performance_content_type_platform ON content_performance(content_type, platform)",
        ]
        
        async with get_db_connection() as conn:
            for index_sql in indexes:
                try:
                    await conn.execute(index_sql)
                    logger.info(f"✅ Created index: {index_sql.split('idx_')[1].split(' ')[0] if 'idx_' in index_sql else 'unknown'}")
                except Exception as e:
                    logger.warning(f"⚠️ Index creation failed or already exists: {e}")
    
    @staticmethod
    @query_performance_tracker("postgresql", "optimized_query")
    async def optimized_query(query: str, params: List[Any] = None,
                            cache_key: str = None, cache_ttl: int = 300) -> List[Dict[str, Any]]:
        """Execute optimized query with caching"""
        
        # Try cache first
        if cache_key:
            cached_result = await RedisManager.cache_get(cache_key)
            if cached_result:
                return cached_result
        
        async with get_db_connection() as conn:
            if params:
                result = await conn.fetch(query, *params)
            else:
                result = await conn.fetch(query)
            
            # Convert to dict list
            result_list = [dict(row) for row in result]
            
            # Cache result
            if cache_key and result_list:
                await RedisManager.cache_set(cache_key, result_list, cache_ttl)
            
            return result_list

class CacheOptimizer:
    """Redis caching optimization strategies"""
    
    @staticmethod
    async def warm_analytics_cache(user_id: str, days: int = 30):
        """Pre-warm analytics cache for a user"""
        cache_keys = [
            f"analytics:user_overview:{user_id}:{days}",
            f"analytics:platform_insights:{user_id}:twitter:{days}",
            f"analytics:platform_insights:{user_id}:facebook:{days}",
            f"analytics:platform_insights:{user_id}:instagram:{days}",
            f"analytics:platform_insights:{user_id}:linkedin:{days}",
            f"analytics:engagement_trends:{user_id}:{days}",
            f"analytics:top_content:{user_id}:{days}"
        ]
        
        # Warm cache by executing queries
        for cache_key in cache_keys:
            # This would trigger the actual analytics queries
            # Implementation depends on specific analytics service
            pass
    
    @staticmethod
    async def warm_scheduler_cache(user_id: str):
        """Pre-warm scheduler cache for a user"""
        cache_keys = [
            f"scheduler:pending_posts:{user_id}",
            f"scheduler:user_posts:{user_id}",
            f"scheduler:platform_posts:{user_id}:twitter",
            f"scheduler:platform_posts:{user_id}:facebook",
            f"scheduler:platform_posts:{user_id}:instagram",
            f"scheduler:platform_posts:{user_id}:linkedin"
        ]
        
        # Warm cache by executing queries
        for cache_key in cache_keys:
            # This would trigger the actual scheduler queries
            # Implementation depends on specific scheduler service
            pass
    
    @staticmethod
    async def invalidate_user_cache(user_id: str):
        """Invalidate all cache entries for a user"""
        patterns = [
            f"analytics:*:{user_id}:*",
            f"scheduler:*:{user_id}*",
            f"user:*:{user_id}*",
            f"content:*:{user_id}*"
        ]
        
        for pattern in patterns:
            await RedisManager.cache_delete_pattern(pattern)

class DatabaseOptimizer:
    """Main database optimization coordinator"""
    
    def __init__(self):
        self.mongo_optimizer = MongoQueryOptimizer()
        self.postgres_optimizer = PostgreSQLQueryOptimizer()
        self.cache_optimizer = CacheOptimizer()
    
    async def optimize_all_databases(self) -> Dict[str, Any]:
        """Run comprehensive database optimization"""
        results = {
            "mongodb": {"status": "pending"},
            "postgresql": {"status": "pending"},
            "redis": {"status": "pending"},
            "performance": {"status": "pending"}
        }
        
        try:
            # MongoDB optimization
            await self.mongo_optimizer.create_optimized_indexes()
            results["mongodb"] = {"status": "success", "message": "Indexes created"}
            
            # PostgreSQL optimization
            await self.postgres_optimizer.create_optimized_indexes()
            results["postgresql"] = {"status": "success", "message": "Indexes created"}
            
            # Redis optimization
            await RedisManager.clear_expired_cache()
            results["redis"] = {"status": "success", "message": "Cache optimized"}
            
            # Performance monitoring
            results["performance"] = performance_monitor.get_performance_report()
            
            logger.info("✅ Database optimization completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Database optimization failed: {e}")
            results["error"] = str(e)
        
        return results
    
    async def get_optimization_recommendations(self) -> Dict[str, Any]:
        """Get optimization recommendations based on performance data"""
        performance_data = performance_monitor.get_performance_report()
        
        recommendations = {
            "slow_queries": [],
            "index_suggestions": [],
            "cache_suggestions": [],
            "general_recommendations": []
        }
        
        # Analyze slow queries
        for slow_query in performance_data["slow_queries"]:
            recommendations["slow_queries"].append({
                "query": f"{slow_query['db_type']}:{slow_query['operation']}",
                "duration": slow_query["duration"],
                "suggestion": "Consider adding indexes or optimizing query structure"
            })
        
        # General recommendations
        if performance_data["avg_query_time"] > 0.1:
            recommendations["general_recommendations"].append(
                "Average query time is high. Consider adding more indexes and caching."
            )
        
        return recommendations

# Global optimizer instance
database_optimizer = DatabaseOptimizer()
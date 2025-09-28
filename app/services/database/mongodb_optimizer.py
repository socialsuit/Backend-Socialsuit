"""
MongoDB-specific optimization service for Social Suit
Handles MongoDB query optimization, indexing, and aggregation pipelines
"""

from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo import IndexModel, ASCENDING, DESCENDING, TEXT
from pymongo.errors import DuplicateKeyError, OperationFailure

from app.services.database.mongodb import MongoDBManager
from app.services.database.redis import RedisManager
from app.services.database.query_optimizer import query_performance_tracker

logger = logging.getLogger(__name__)

class MongoDBOptimizer:
    """
    MongoDB-specific optimization service
    """
    
    def __init__(self):
        self.db_manager = MongoDBManager()
        self.redis_manager = RedisManager()
        
    async def create_optimized_indexes(self) -> Dict[str, List[str]]:
        """
        Create optimized indexes for all collections
        """
        results = {}
        
        try:
            db = await self.db_manager.get_database()
            
            # Analytics data indexes
            analytics_indexes = await self._create_analytics_indexes(db)
            results['analytics_data'] = analytics_indexes
            
            # User engagement indexes
            engagement_indexes = await self._create_engagement_indexes(db)
            results['user_engagements'] = engagement_indexes
            
            # Content performance indexes
            content_indexes = await self._create_content_indexes(db)
            results['content_performance'] = content_indexes
            
            # AB testing indexes
            ab_test_indexes = await self._create_ab_test_indexes(db)
            results['ab_tests'] = ab_test_indexes
            
            # Scheduled posts indexes
            scheduled_posts_indexes = await self._create_scheduled_posts_indexes(db)
            results['scheduled_posts'] = scheduled_posts_indexes
            
            # User activity indexes
            user_activity_indexes = await self._create_user_activity_indexes(db)
            results['user_activity'] = user_activity_indexes
            
            logger.info(f"Created optimized indexes for {len(results)} collections")
            
        except Exception as e:
            logger.error(f"Error creating optimized indexes: {e}")
            raise
            
        return results
    
    async def _create_analytics_indexes(self, db: AsyncIOMotorDatabase) -> List[str]:
        """Create indexes for analytics_data collection"""
        collection = db.analytics_data
        indexes = []
        
        index_definitions = [
            # Compound indexes for common queries
            IndexModel([("user_id", ASCENDING), ("platform", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("user_id", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("platform", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("timestamp", DESCENDING)]),
            
            # Indexes for aggregation pipelines
            IndexModel([("user_id", ASCENDING), ("engagement_type", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("platform", ASCENDING), ("engagement_type", ASCENDING)]),
            
            # Sparse indexes for optional fields
            IndexModel([("campaign_id", ASCENDING)], sparse=True),
            IndexModel([("post_id", ASCENDING)], sparse=True),
            
            # TTL index for data retention (30 days)
            IndexModel([("timestamp", ASCENDING)], expireAfterSeconds=2592000),
            
            # Text index for content search
            IndexModel([("content", TEXT), ("hashtags", TEXT)]),
        ]
        
        for index in index_definitions:
            try:
                result = await collection.create_index(index.document["key"], **{k: v for k, v in index.document.items() if k != "key"})
                indexes.append(result)
            except DuplicateKeyError:
                pass  # Index already exists
            except Exception as e:
                logger.warning(f"Failed to create analytics index: {e}")
        
        return indexes
    
    async def _create_engagement_indexes(self, db: AsyncIOMotorDatabase) -> List[str]:
        """Create indexes for user_engagements collection"""
        collection = db.user_engagements
        indexes = []
        
        index_definitions = [
            # Primary query patterns
            IndexModel([("user_id", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("user_id", ASCENDING), ("platform", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("post_id", ASCENDING), ("timestamp", DESCENDING)]),
            
            # Engagement analysis
            IndexModel([("engagement_type", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("user_id", ASCENDING), ("engagement_type", ASCENDING)]),
            
            # Performance tracking
            IndexModel([("platform", ASCENDING), ("engagement_rate", DESCENDING)]),
            IndexModel([("timestamp", DESCENDING), ("engagement_rate", DESCENDING)]),
            
            # Geolocation analysis (if available)
            IndexModel([("location", "2dsphere")], sparse=True),
            
            # TTL index
            IndexModel([("timestamp", ASCENDING)], expireAfterSeconds=7776000),  # 90 days
        ]
        
        for index in index_definitions:
            try:
                result = await collection.create_index(index.document["key"], **{k: v for k, v in index.document.items() if k != "key"})
                indexes.append(result)
            except DuplicateKeyError:
                pass
            except Exception as e:
                logger.warning(f"Failed to create engagement index: {e}")
        
        return indexes
    
    async def _create_content_indexes(self, db: AsyncIOMotorDatabase) -> List[str]:
        """Create indexes for content_performance collection"""
        collection = db.content_performance
        indexes = []
        
        index_definitions = [
            # Content analysis
            IndexModel([("user_id", ASCENDING), ("content_type", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("platform", ASCENDING), ("content_type", ASCENDING)]),
            IndexModel([("engagement_score", DESCENDING), ("timestamp", DESCENDING)]),
            
            # Performance ranking
            IndexModel([("user_id", ASCENDING), ("engagement_score", DESCENDING)]),
            IndexModel([("platform", ASCENDING), ("engagement_score", DESCENDING)]),
            
            # Time-based analysis
            IndexModel([("timestamp", DESCENDING)]),
            IndexModel([("user_id", ASCENDING), ("timestamp", DESCENDING)]),
            
            # Content categorization
            IndexModel([("hashtags", ASCENDING)], sparse=True),
            IndexModel([("category", ASCENDING)], sparse=True),
            
            # Full-text search
            IndexModel([("title", TEXT), ("description", TEXT), ("hashtags", TEXT)]),
        ]
        
        for index in index_definitions:
            try:
                result = await collection.create_index(index.document["key"], **{k: v for k, v in index.document.items() if k != "key"})
                indexes.append(result)
            except DuplicateKeyError:
                pass
            except Exception as e:
                logger.warning(f"Failed to create content index: {e}")
        
        return indexes
    
    async def _create_ab_test_indexes(self, db: AsyncIOMotorDatabase) -> List[str]:
        """Create indexes for ab_tests collection"""
        collection = db.ab_tests
        indexes = []
        
        index_definitions = [
            # Test management
            IndexModel([("user_id", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("test_name", ASCENDING), ("user_id", ASCENDING)]),
            IndexModel([("status", ASCENDING), ("end_date", ASCENDING)]),
            
            # Performance analysis
            IndexModel([("user_id", ASCENDING), ("conversion_rate", DESCENDING)]),
            IndexModel([("platform", ASCENDING), ("conversion_rate", DESCENDING)]),
            
            # Time-based queries
            IndexModel([("created_at", DESCENDING)]),
            IndexModel([("end_date", ASCENDING)]),
            
            # Test variants
            IndexModel([("test_id", ASCENDING), ("variant", ASCENDING)]),
        ]
        
        for index in index_definitions:
            try:
                result = await collection.create_index(index.document["key"], **{k: v for k, v in index.document.items() if k != "key"})
                indexes.append(result)
            except DuplicateKeyError:
                pass
            except Exception as e:
                logger.warning(f"Failed to create AB test index: {e}")
        
        return indexes
    
    async def _create_scheduled_posts_indexes(self, db: AsyncIOMotorDatabase) -> List[str]:
        """Create indexes for scheduled_posts collection"""
        collection = db.scheduled_posts
        indexes = []
        
        index_definitions = [
            # Scheduling queries
            IndexModel([("user_id", ASCENDING), ("scheduled_time", ASCENDING)]),
            IndexModel([("status", ASCENDING), ("scheduled_time", ASCENDING)]),
            IndexModel([("platform", ASCENDING), ("scheduled_time", ASCENDING)]),
            
            # Status management
            IndexModel([("user_id", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("status", ASCENDING), ("updated_at", DESCENDING)]),
            
            # Performance tracking
            IndexModel([("user_id", ASCENDING), ("platform", ASCENDING), ("status", ASCENDING)]),
            
            # Content search
            IndexModel([("content", TEXT), ("title", TEXT)]),
            
            # Time-based cleanup
            IndexModel([("created_at", ASCENDING)]),
        ]
        
        for index in index_definitions:
            try:
                result = await collection.create_index(index.document["key"], **{k: v for k, v in index.document.items() if k != "key"})
                indexes.append(result)
            except DuplicateKeyError:
                pass
            except Exception as e:
                logger.warning(f"Failed to create scheduled posts index: {e}")
        
        return indexes
    
    async def _create_user_activity_indexes(self, db: AsyncIOMotorDatabase) -> List[str]:
        """Create indexes for user_activity collection"""
        collection = db.user_activity
        indexes = []
        
        index_definitions = [
            # Activity tracking
            IndexModel([("user_id", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("activity_type", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("user_id", ASCENDING), ("activity_type", ASCENDING)]),
            
            # Session analysis
            IndexModel([("session_id", ASCENDING), ("timestamp", ASCENDING)]),
            IndexModel([("user_id", ASCENDING), ("session_id", ASCENDING)]),
            
            # Performance monitoring
            IndexModel([("timestamp", DESCENDING)]),
            
            # TTL index for activity data (180 days)
            IndexModel([("timestamp", ASCENDING)], expireAfterSeconds=15552000),
        ]
        
        for index in index_definitions:
            try:
                result = await collection.create_index(index.document["key"], **{k: v for k, v in index.document.items() if k != "key"})
                indexes.append(result)
            except DuplicateKeyError:
                pass
            except Exception as e:
                logger.warning(f"Failed to create user activity index: {e}")
        
        return indexes
    
    @query_performance_tracker("mongodb", "optimized_aggregate")
    async def optimized_aggregate(self, collection_name: str, pipeline: List[Dict], 
                                cache_key: Optional[str] = None, cache_ttl: int = 300) -> List[Dict]:
        """
        Execute optimized aggregation pipeline with caching
        """
        # Check cache first
        if cache_key:
            cached_result = await self.redis_manager.cache_get(cache_key)
            if cached_result:
                return cached_result
        
        try:
            db = await self.db_manager.get_database()
            collection = db[collection_name]
            
            # Add performance optimization hints
            optimized_pipeline = self._optimize_pipeline(pipeline)
            
            # Execute aggregation
            cursor = collection.aggregate(optimized_pipeline, allowDiskUse=True)
            results = await cursor.to_list(length=None)
            
            # Cache results
            if cache_key and results:
                await self.redis_manager.cache_set(cache_key, results, cache_ttl)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in optimized aggregation: {e}")
            raise
    
    def _optimize_pipeline(self, pipeline: List[Dict]) -> List[Dict]:
        """
        Optimize aggregation pipeline for better performance
        """
        optimized = []
        
        for stage in pipeline:
            # Move $match stages to the beginning
            if "$match" in stage:
                optimized.insert(0, stage)
            # Add $limit early if possible
            elif "$sort" in stage and len(optimized) > 0:
                optimized.append(stage)
                # Add limit after sort if not already present
                if not any("$limit" in s for s in pipeline[pipeline.index(stage):]):
                    optimized.append({"$limit": 1000})  # Default limit
            else:
                optimized.append(stage)
        
        return optimized
    
    async def get_analytics_aggregation(self, user_id: str, platform: Optional[str] = None, 
                                      days: int = 30) -> Dict[str, Any]:
        """
        Get analytics data using optimized aggregation pipeline
        """
        cache_key = f"analytics:agg:{user_id}:{platform or 'all'}:{days}"
        
        start_date = datetime.now() - timedelta(days=days)
        
        # Build aggregation pipeline
        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "timestamp": {"$gte": start_date}
                }
            }
        ]
        
        if platform:
            pipeline[0]["$match"]["platform"] = platform
        
        pipeline.extend([
            {
                "$group": {
                    "_id": {
                        "platform": "$platform",
                        "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}}
                    },
                    "total_engagement": {"$sum": "$engagement_count"},
                    "avg_engagement_rate": {"$avg": "$engagement_rate"},
                    "post_count": {"$sum": 1},
                    "unique_users": {"$addToSet": "$user_id"}
                }
            },
            {
                "$project": {
                    "platform": "$_id.platform",
                    "date": "$_id.date",
                    "total_engagement": 1,
                    "avg_engagement_rate": 1,
                    "post_count": 1,
                    "unique_user_count": {"$size": "$unique_users"}
                }
            },
            {
                "$sort": {"date": 1, "platform": 1}
            }
        ])
        
        return await self.optimized_aggregate("analytics_data", pipeline, cache_key)
    
    async def get_content_performance_aggregation(self, user_id: str, 
                                                content_type: Optional[str] = None,
                                                days: int = 30) -> Dict[str, Any]:
        """
        Get content performance using optimized aggregation
        """
        cache_key = f"content:agg:{user_id}:{content_type or 'all'}:{days}"
        
        start_date = datetime.now() - timedelta(days=days)
        
        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "timestamp": {"$gte": start_date}
                }
            }
        ]
        
        if content_type:
            pipeline[0]["$match"]["content_type"] = content_type
        
        pipeline.extend([
            {
                "$group": {
                    "_id": {
                        "content_type": "$content_type",
                        "platform": "$platform"
                    },
                    "avg_engagement_score": {"$avg": "$engagement_score"},
                    "max_engagement_score": {"$max": "$engagement_score"},
                    "total_posts": {"$sum": 1},
                    "avg_reach": {"$avg": "$reach"},
                    "total_impressions": {"$sum": "$impressions"}
                }
            },
            {
                "$project": {
                    "content_type": "$_id.content_type",
                    "platform": "$_id.platform",
                    "avg_engagement_score": 1,
                    "max_engagement_score": 1,
                    "total_posts": 1,
                    "avg_reach": 1,
                    "total_impressions": 1,
                    "engagement_per_post": {
                        "$divide": ["$avg_engagement_score", "$total_posts"]
                    }
                }
            },
            {
                "$sort": {"avg_engagement_score": -1}
            }
        ])
        
        return await self.optimized_aggregate("content_performance", pipeline, cache_key)
    
    async def get_user_engagement_trends(self, user_id: str, days: int = 30) -> List[Dict]:
        """
        Get user engagement trends using optimized aggregation
        """
        cache_key = f"engagement:trends:{user_id}:{days}"
        
        start_date = datetime.now() - timedelta(days=days)
        
        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "timestamp": {"$gte": start_date}
                }
            },
            {
                "$group": {
                    "_id": {
                        "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                        "engagement_type": "$engagement_type"
                    },
                    "count": {"$sum": 1},
                    "total_value": {"$sum": "$engagement_value"}
                }
            },
            {
                "$group": {
                    "_id": "$_id.date",
                    "engagements": {
                        "$push": {
                            "type": "$_id.engagement_type",
                            "count": "$count",
                            "total_value": "$total_value"
                        }
                    },
                    "total_engagements": {"$sum": "$count"}
                }
            },
            {
                "$project": {
                    "date": "$_id",
                    "engagements": 1,
                    "total_engagements": 1
                }
            },
            {
                "$sort": {"date": 1}
            }
        ]
        
        return await self.optimized_aggregate("user_engagements", pipeline, cache_key)
    
    async def cleanup_old_data(self, days_to_keep: int = 90) -> Dict[str, int]:
        """
        Clean up old data from collections
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        results = {}
        
        collections_to_clean = [
            "analytics_data",
            "user_engagements", 
            "user_activity",
            "content_performance"
        ]
        
        try:
            db = await self.db_manager.get_database()
            
            for collection_name in collections_to_clean:
                collection = db[collection_name]
                result = await collection.delete_many({
                    "timestamp": {"$lt": cutoff_date}
                })
                results[collection_name] = result.deleted_count
                logger.info(f"Cleaned {result.deleted_count} documents from {collection_name}")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            raise
        
        return results
    
    async def get_collection_stats(self) -> Dict[str, Dict]:
        """
        Get statistics for all collections
        """
        try:
            db = await self.db_manager.get_database()
            collection_names = await db.list_collection_names()
            
            stats = {}
            for name in collection_names:
                collection = db[name]
                collection_stats = await db.command("collStats", name)
                
                stats[name] = {
                    "document_count": collection_stats.get("count", 0),
                    "size_bytes": collection_stats.get("size", 0),
                    "avg_document_size": collection_stats.get("avgObjSize", 0),
                    "index_count": collection_stats.get("nindexes", 0),
                    "index_size_bytes": collection_stats.get("totalIndexSize", 0)
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            raise
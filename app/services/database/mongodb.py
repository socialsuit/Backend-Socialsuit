from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, ConfigurationError
import os
from typing import Optional, Dict, Any, List, Union
from contextlib import asynccontextmanager
import logging
from datetime import datetime, timedelta
from functools import wraps
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Performance monitoring decorator for MongoDB operations
def mongo_performance_monitor(operation_name=None):
    """Decorator to monitor MongoDB operation performance"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            op_name = operation_name or func.__name__
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                if execution_time > 0.5:  # Log slow operations (>500ms)
                    logger.warning(f"⚠️ Slow MongoDB operation: {op_name} took {execution_time:.2f}s")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"❌ MongoDB operation {op_name} failed after {execution_time:.2f}s: {str(e)}")
                raise
        return wrapper
    return decorator

class MongoDBManager:
    """
    Async MongoDB connection manager with error handling, connection pooling,
    and optimized query capabilities.
    """
    _client: Optional[AsyncIOMotorClient] = None  # type: ignore
    _db: Optional[AsyncIOMotorDatabase] = None  # type: ignore
    _indexes_created: bool = False
    
    @classmethod
    async def initialize(cls):
        """Initialize the MongoDB connection pool and create indexes"""
        MONGO_URI = os.getenv("MONGO_URI") or os.getenv("MONGO_URL")
        if not MONGO_URI:
            raise ConfigurationError("MONGO_URI environment variable not set")

        try:
            cls._client = AsyncIOMotorClient(
                MONGO_URI,
                maxPoolSize=100,          # Default connection pool size
                minPoolSize=10,           # Minimum connections
                connectTimeoutMS=5000,    # 5-second connection timeout
                socketTimeoutMS=30000,     # 30-second operation timeout
                serverSelectionTimeoutMS=5000,  # 5-second server selection timeout
                retryWrites=True,         # Enable retryable writes
                w="majority"              # Write concern for data durability
            )
            # Test the connection
            await cls._client.admin.command('ping')
            cls._db = cls._client["social_suit"]
            logger.info("✅ Successfully connected to MongoDB")
            
            # Create indexes for better query performance
            await cls.create_indexes()
        except ConnectionFailure as e:
            logger.error(f"🚨 MongoDB connection failed: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected MongoDB error: {e}")
            raise

    @classmethod
    async def create_indexes(cls):
        """Create indexes for collections to optimize query performance"""
        if cls._indexes_created:
            return
            
        try:
            # Analytics indexes
            await cls._db.analytics_data.create_index([('user_id', 1), ('platform', 1), ('timestamp', -1)])
            await cls._db.analytics_data.create_index([('platform', 1), ('content_type', 1)])
            await cls._db.analytics_data.create_index([('timestamp', -1)])
            
            # User engagement indexes
            await cls._db.user_engagements.create_index([('user_id', 1), ('timestamp', -1)])
            await cls._db.user_engagements.create_index([('platform', 1), ('engagement_type', 1)])
            
            # Content performance indexes
            await cls._db.content_performance.create_index([('user_id', 1), ('platform', 1), ('timestamp', -1)])
            await cls._db.content_performance.create_index([('content_id', 1)], unique=True)
            await cls._db.content_performance.create_index([('engagement_score', -1)])
            
            # AB test indexes
            await cls._db.ab_tests.create_index([('user_id', 1), ('status', 1)])
            await cls._db.ab_tests.create_index([('test_id', 1)], unique=True)
            await cls._db.ab_tests.create_index([('end_date', 1)])
            
            # Scheduled posts indexes (if using MongoDB for this)
            await cls._db.scheduled_posts.create_index([('user_id', 1), ('platform', 1)])
            await cls._db.scheduled_posts.create_index([('scheduled_time', 1), ('status', 1)])
            
            cls._indexes_created = True
            logger.info("✅ MongoDB indexes created successfully")
        except Exception as e:
            logger.error(f"❌ Failed to create MongoDB indexes: {e}")
            # Don't raise the exception - allow the application to continue
    
    @classmethod
    @asynccontextmanager
    async def get_db(cls):
        """Async context manager for database access"""
        if not cls._db:
            await cls.initialize()
        
        try:
            yield cls._db
        except Exception as e:
            logger.error(f"🔴 Database operation failed: {e}")
            raise
    
    @classmethod
    @mongo_performance_monitor("aggregate")
    async def aggregate(cls, collection: str, pipeline: List[Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
        """Execute an aggregation pipeline with performance monitoring"""
        if not cls._db:
            await cls.initialize()
            
        try:
            result = await cls._db[collection].aggregate(pipeline, **kwargs).to_list(None)
            return result
        except Exception as e:
            logger.error(f"❌ Aggregation failed on {collection}: {e}")
            raise
    
    @classmethod
    @mongo_performance_monitor("find_with_options")
    async def find_with_options(cls, collection: str, query: Dict[str, Any], projection: Dict[str, Any] = None, 
                               sort: List[tuple] = None, limit: int = 0, skip: int = 0) -> List[Dict[str, Any]]:
        """Optimized find operation with projection, sorting, and pagination"""
        if not cls._db:
            await cls.initialize()
            
        try:
            cursor = cls._db[collection].find(query, projection)
            
            if sort:
                cursor = cursor.sort(sort)
            if skip:
                cursor = cursor.skip(skip)
            if limit:
                cursor = cursor.limit(limit)
                
            return await cursor.to_list(length=limit if limit else None)
        except Exception as e:
            logger.error(f"❌ Find operation failed on {collection}: {e}")
            raise

    @classmethod
    async def close_connection(cls):
        """Cleanly close the connection"""
        if cls._client:
            cls._client.close()
            logger.info("🔌 MongoDB connection closed")

    @classmethod
    @mongo_performance_monitor("bulk_write")
    async def bulk_write(cls, collection: str, operations: List[Any], ordered: bool = False) -> Dict[str, Any]:
        """Execute bulk write operations efficiently"""
        if not cls._db:
            await cls.initialize()
            
        try:
            result = await cls._db[collection].bulk_write(operations, ordered=ordered)
            return {
                "inserted_count": result.inserted_count,
                "modified_count": result.modified_count,
                "deleted_count": result.deleted_count,
                "upserted_count": result.upserted_count
            }
        except Exception as e:
            logger.error(f"❌ Bulk write operation failed on {collection}: {e}")
            raise
    
    @classmethod
    @mongo_performance_monitor("update_with_options")
    async def update_with_options(cls, collection: str, filter_query: Dict[str, Any], 
                                update_query: Dict[str, Any], upsert: bool = False) -> Dict[str, Any]:
        """Optimized update operation with options"""
        if not cls._db:
            await cls.initialize()
            
        try:
            result = await cls._db[collection].update_one(filter_query, update_query, upsert=upsert)
            return {
                "matched_count": result.matched_count,
                "modified_count": result.modified_count,
                "upserted_id": result.upserted_id
            }
        except Exception as e:
            logger.error(f"❌ Update operation failed on {collection}: {e}")
            raise
    
    @classmethod
    @mongo_performance_monitor("count_documents")
    async def count_documents(cls, collection: str, query: Dict[str, Any]) -> int:
        """Count documents with performance monitoring"""
        if not cls._db:
            await cls.initialize()
            
        try:
            return await cls._db[collection].count_documents(query)
        except Exception as e:
            logger.error(f"❌ Count operation failed on {collection}: {e}")
            raise
    
    @classmethod
    async def create_time_series_collection(cls, collection_name: str, time_field: str = "timestamp", 
                                          meta_field: str = None, granularity: str = "seconds") -> bool:
        """Create a time series collection for efficient time-based queries"""
        if not cls._db:
            await cls.initialize()
            
        try:
            # Check if collection already exists
            collections = await cls._db.list_collection_names()
            if collection_name in collections:
                return True
                
            # Create time series collection
            options = {
                "timeseries": {
                    "timeField": time_field,
                    "granularity": granularity
                }
            }
            
            if meta_field:
                options["timeseries"]["metaField"] = meta_field
                
            await cls._db.create_collection(collection_name, **options)
            logger.info(f"✅ Created time series collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to create time series collection {collection_name}: {e}")
            return False
    
    @classmethod
    @mongo_performance_monitor("insert_time_series_data")
    async def insert_time_series_data(cls, collection_name: str, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Insert data into time series collection with optimizations"""
        if not cls._db:
            await cls.initialize()
            
        try:
            # Ensure timestamp field exists and is datetime
            for doc in data:
                if 'timestamp' not in doc:
                    doc['timestamp'] = datetime.now()
                elif isinstance(doc['timestamp'], str):
                    doc['timestamp'] = datetime.fromisoformat(doc['timestamp'])
            
            result = await cls._db[collection_name].insert_many(data, ordered=False)
            
            return {
                "inserted_count": len(result.inserted_ids),
                "inserted_ids": result.inserted_ids
            }
            
        except Exception as e:
            logger.error(f"❌ Time series insert failed on {collection_name}: {e}")
            raise
    
    @classmethod
    @mongo_performance_monitor("aggregate_time_series")
    async def aggregate_time_series(cls, collection_name: str, pipeline: List[Dict[str, Any]],
                                  time_range: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Optimized aggregation for time series data"""
        if not cls._db:
            await cls.initialize()
            
        try:
            # Add time range filter if provided
            if time_range:
                match_stage = {"$match": {"timestamp": time_range}}
                pipeline.insert(0, match_stage)
            
            return await cls.aggregate(collection_name, pipeline)
            
        except Exception as e:
            logger.error(f"❌ Time series aggregation failed on {collection_name}: {e}")
            raise
    
    @classmethod
    @mongo_performance_monitor("get_collection_stats")
    async def get_collection_stats(cls, collection_name: str) -> Dict[str, Any]:
        """Get detailed collection statistics"""
        if not cls._db:
            await cls.initialize()
            
        try:
            stats = await cls._db.command("collStats", collection_name)
            
            return {
                "collection": collection_name,
                "count": stats.get("count", 0),
                "size": stats.get("size", 0),
                "avg_obj_size": stats.get("avgObjSize", 0),
                "storage_size": stats.get("storageSize", 0),
                "total_index_size": stats.get("totalIndexSize", 0),
                "index_count": len(stats.get("indexSizes", {})),
                "capped": stats.get("capped", False)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get collection stats for {collection_name}: {e}")
            return {}
    
    @classmethod
    @mongo_performance_monitor("optimize_collection")
    async def optimize_collection(cls, collection_name: str) -> Dict[str, Any]:
        """Optimize collection performance"""
        if not cls._db:
            await cls.initialize()
            
        try:
            # Compact collection to reclaim space
            result = await cls._db.command("compact", collection_name)
            
            # Get updated stats
            stats = await cls.get_collection_stats(collection_name)
            
            return {
                "optimization_result": result,
                "collection_stats": stats
            }
            
        except Exception as e:
            logger.error(f"❌ Collection optimization failed for {collection_name}: {e}")
            return {"error": str(e)}
import os
import logging
import json
import time
from redis.asyncio import Redis
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional, Dict, Any, List, Union, Callable
from datetime import datetime, timedelta
from functools import wraps

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis cache decorator
def redis_cache(ttl_seconds: int = 300, key_prefix: str = ""):
    """Decorator to cache function results in Redis"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate a cache key based on function name, args, and kwargs
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Try to get cached result
            async with RedisManager.get_connection() as redis:
                cached_result = await redis.get(cache_key)
                
                if cached_result:
                    try:
                        return json.loads(cached_result)
                    except json.JSONDecodeError:
                        # If not JSON, return as is
                        return cached_result
            
            # If not cached, execute the function
            start_time = time.time()
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Cache the result
            try:
                serialized_result = json.dumps(result)
                async with RedisManager.get_connection() as redis:
                    await redis.set(cache_key, serialized_result, ex=ttl_seconds)
                    
                    # Log slow operations
                    if execution_time > 0.5:  # >500ms
                        logger.info(f"⚠️ Slow operation cached: {func.__name__} took {execution_time:.2f}s")
            except (TypeError, json.JSONDecodeError) as e:
                logger.warning(f"⚠️ Could not cache result for {func.__name__}: {e}")
                
            return result
        return wrapper
    return decorator

class RedisManager:
    _pool: Optional[Redis] = None
    _cache_stats: Dict[str, int] = {"hits": 0, "misses": 0}

    @classmethod
    async def initialize(cls):
        """Initialize Redis connection pool"""
        try:
            cls._pool = Redis.from_url(
                os.getenv("REDIS_URL", "redis://localhost:6379"),
                decode_responses=True,
                max_connections=50,  # Increased for higher throughput
                socket_timeout=5,
                socket_keepalive=True,
                health_check_interval=30  # Regular health checks
            )
            # Test connection
            await cls._pool.ping()
            logger.info("✅ Redis connection pool initialized")
            
            # Clear expired cache entries on startup
            await cls.clear_expired_cache()
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            raise

    @classmethod
    @asynccontextmanager
    async def get_connection(cls) -> AsyncIterator[Redis]:
        """Context manager for redis connection"""
        if not cls._pool:
            await cls.initialize()
        
        try:
            yield cls._pool
        except Exception as e:
            logger.error(f"🔴 Redis operation failed: {e}")
            raise

    @classmethod
    async def close(cls):
        """Properly close the Redis connection pool"""
        if cls._pool:
            await cls._pool.close()
            logger.info("🔌 Redis connection pool closed")
            
    @classmethod
    async def clear_expired_cache(cls):
        """Clear expired cache entries using SCAN for efficiency"""
        if not cls._pool:
            await cls.initialize()
            
        try:
            # Use SCAN instead of KEYS for production environments
            cursor = 0
            pattern = "*"
            count = 100
            
            while True:
                cursor, keys = await cls._pool.scan(cursor=cursor, match=pattern, count=count)
                
                # Process this batch of keys
                for key in keys:
                    # Check if key has TTL
                    ttl = await cls._pool.ttl(key)
                    if ttl == -1:  # No expiry set
                        # Set default expiry for keys without TTL
                        await cls._pool.expire(key, 86400)  # 24 hours
                
                # Exit when scan is complete
                if cursor == 0:
                    break
                    
            logger.info("✅ Redis cache maintenance completed")
        except Exception as e:
            logger.error(f"❌ Redis cache maintenance failed: {e}")
            # Don't raise - allow application to continue

    @classmethod
    async def cache_set(cls, key: str, value: Any, ttl_seconds: int = 300) -> bool:
        """Set a value in the cache with TTL"""
        if not cls._pool:
            await cls.initialize()
            
        try:
            # Serialize complex objects
            if not isinstance(value, (str, int, float, bool)):
                value = json.dumps(value)
                
            return await cls._pool.set(key, value, ex=ttl_seconds)
        except Exception as e:
            logger.error(f"❌ Failed to set cache key {key}: {e}")
            return False
    
    @classmethod
    async def cache_get(cls, key: str, default: Any = None) -> Any:
        """Get a value from the cache with automatic deserialization"""
        if not cls._pool:
            await cls.initialize()
            
        try:
            value = await cls._pool.get(key)
            if value is None:
                cls._cache_stats["misses"] += 1
                return default
                
            cls._cache_stats["hits"] += 1
            
            # Try to deserialize JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                # Return as is if not JSON
                return value
        except Exception as e:
            logger.error(f"❌ Failed to get cache key {key}: {e}")
            return default
    
    @classmethod
    async def cache_delete(cls, key: str) -> bool:
        """Delete a key from the cache"""
        if not cls._pool:
            await cls.initialize()
            
        try:
            return bool(await cls._pool.delete(key))
        except Exception as e:
            logger.error(f"❌ Failed to delete cache key {key}: {e}")
            return False
    
    @classmethod
    async def cache_delete_pattern(cls, pattern: str) -> int:
        """Delete all keys matching a pattern"""
        if not cls._pool:
            await cls.initialize()
            
        try:
            cursor = 0
            count = 0
            
            while True:
                cursor, keys = await cls._pool.scan(cursor=cursor, match=pattern, count=100)
                
                if keys:
                    count += await cls._pool.delete(*keys)
                
                if cursor == 0:
                    break
                    
            return count
        except Exception as e:
            logger.error(f"❌ Failed to delete cache keys with pattern {pattern}: {e}")
            return 0
    
    @classmethod
    async def cache_hash_set(cls, hash_key: str, field: str, value: Any, ttl_seconds: int = None) -> bool:
        """Set a field in a hash with optional TTL on the entire hash"""
        if not cls._pool:
            await cls.initialize()
            
        try:
            # Serialize complex objects
            if not isinstance(value, (str, int, float, bool)):
                value = json.dumps(value)
                
            # Set the hash field
            result = await cls._pool.hset(hash_key, field, value)
            
            # Set TTL if provided
            if ttl_seconds is not None:
                await cls._pool.expire(hash_key, ttl_seconds)
                
            return result > 0
        except Exception as e:
            logger.error(f"❌ Failed to set hash field {hash_key}.{field}: {e}")
            return False
    
    @classmethod
    async def cache_hash_get(cls, hash_key: str, field: str, default: Any = None) -> Any:
        """Get a field from a hash with automatic deserialization"""
        if not cls._pool:
            await cls.initialize()
            
        try:
            value = await cls._pool.hget(hash_key, field)
            if value is None:
                cls._cache_stats["misses"] += 1
                return default
                
            cls._cache_stats["hits"] += 1
            
            # Try to deserialize JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                # Return as is if not JSON
                return value
        except Exception as e:
            logger.error(f"❌ Failed to get hash field {hash_key}.{field}: {e}")
            return default
    
    @classmethod
    async def cache_hash_get_all(cls, hash_key: str) -> Dict[str, Any]:
        """Get all fields from a hash with automatic deserialization"""
        if not cls._pool:
            await cls.initialize()
            
        try:
            hash_data = await cls._pool.hgetall(hash_key)
            if not hash_data:
                cls._cache_stats["misses"] += 1
                return {}
                
            cls._cache_stats["hits"] += 1
            
            # Deserialize all values
            result = {}
            for field, value in hash_data.items():
                try:
                    result[field] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    result[field] = value
                    
            return result
        except Exception as e:
            logger.error(f"❌ Failed to get all hash fields for {hash_key}: {e}")
            return {}
    
    @classmethod
    async def cache_list_push(cls, list_key: str, value: Any, max_length: int = None, ttl_seconds: int = None) -> int:
        """Push value to a list with optional max length and TTL"""
        if not cls._pool:
            await cls.initialize()
            
        try:
            # Serialize complex objects
            if not isinstance(value, (str, int, float, bool)):
                value = json.dumps(value)
            
            # Push to list
            length = await cls._pool.lpush(list_key, value)
            
            # Trim list if max_length specified
            if max_length and length > max_length:
                await cls._pool.ltrim(list_key, 0, max_length - 1)
                length = max_length
            
            # Set TTL if provided
            if ttl_seconds is not None:
                await cls._pool.expire(list_key, ttl_seconds)
                
            return length
        except Exception as e:
            logger.error(f"❌ Failed to push to list {list_key}: {e}")
            return 0
    
    @classmethod
    async def cache_list_get_range(cls, list_key: str, start: int = 0, end: int = -1) -> List[Any]:
        """Get range of values from a list with automatic deserialization"""
        if not cls._pool:
            await cls.initialize()
            
        try:
            values = await cls._pool.lrange(list_key, start, end)
            if not values:
                cls._cache_stats["misses"] += 1
                return []
                
            cls._cache_stats["hits"] += 1
            
            # Deserialize all values
            result = []
            for value in values:
                try:
                    result.append(json.loads(value))
                except (json.JSONDecodeError, TypeError):
                    result.append(value)
                    
            return result
        except Exception as e:
            logger.error(f"❌ Failed to get list range for {list_key}: {e}")
            return []
    
    @classmethod
    async def cache_set_add(cls, set_key: str, *values: Any, ttl_seconds: int = None) -> int:
        """Add values to a set with optional TTL"""
        if not cls._pool:
            await cls.initialize()
            
        try:
            # Serialize complex objects
            serialized_values = []
            for value in values:
                if not isinstance(value, (str, int, float, bool)):
                    serialized_values.append(json.dumps(value))
                else:
                    serialized_values.append(value)
            
            # Add to set
            count = await cls._pool.sadd(set_key, *serialized_values)
            
            # Set TTL if provided
            if ttl_seconds is not None:
                await cls._pool.expire(set_key, ttl_seconds)
                
            return count
        except Exception as e:
            logger.error(f"❌ Failed to add to set {set_key}: {e}")
            return 0
    
    @classmethod
    async def cache_set_members(cls, set_key: str) -> List[Any]:
        """Get all members of a set with automatic deserialization"""
        if not cls._pool:
            await cls.initialize()
            
        try:
            members = await cls._pool.smembers(set_key)
            if not members:
                cls._cache_stats["misses"] += 1
                return []
                
            cls._cache_stats["hits"] += 1
            
            # Deserialize all members
            result = []
            for member in members:
                try:
                    result.append(json.loads(member))
                except (json.JSONDecodeError, TypeError):
                    result.append(member)
                    
            return result
        except Exception as e:
            logger.error(f"❌ Failed to get set members for {set_key}: {e}")
            return []
    
    @classmethod
    async def cache_increment(cls, key: str, amount: int = 1, ttl_seconds: int = None) -> int:
        """Increment a counter with optional TTL"""
        if not cls._pool:
            await cls.initialize()
            
        try:
            # Increment counter
            value = await cls._pool.incrby(key, amount)
            
            # Set TTL if provided and this is a new key
            if ttl_seconds is not None and value == amount:
                await cls._pool.expire(key, ttl_seconds)
                
            return value
        except Exception as e:
            logger.error(f"❌ Failed to increment counter {key}: {e}")
            return 0
    
    @classmethod
    async def cache_pipeline_execute(cls, operations: List[Dict[str, Any]]) -> List[Any]:
        """Execute multiple cache operations in a pipeline for better performance"""
        if not cls._pool:
            await cls.initialize()
            
        try:
            pipe = cls._pool.pipeline()
            
            for op in operations:
                operation = op.get("operation")
                args = op.get("args", [])
                kwargs = op.get("kwargs", {})
                
                if hasattr(pipe, operation):
                    getattr(pipe, operation)(*args, **kwargs)
                else:
                    logger.warning(f"Unknown pipeline operation: {operation}")
            
            return await pipe.execute()
        except Exception as e:
            logger.error(f"❌ Pipeline execution failed: {e}")
            return []
    
    @classmethod
    async def get_cache_stats(cls) -> Dict[str, Any]:
        """Get cache performance statistics"""
        if not cls._pool:
            await cls.initialize()
            
        try:
            info = await cls._pool.info()
            
            total_requests = cls._cache_stats["hits"] + cls._cache_stats["misses"]
            hit_rate = (cls._cache_stats["hits"] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "cache_hits": cls._cache_stats["hits"],
                "cache_misses": cls._cache_stats["misses"],
                "hit_rate_percentage": round(hit_rate, 2),
                "redis_info": {
                    "used_memory": info.get("used_memory", 0),
                    "used_memory_human": info.get("used_memory_human", "0B"),
                    "connected_clients": info.get("connected_clients", 0),
                    "total_commands_processed": info.get("total_commands_processed", 0),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                    "expired_keys": info.get("expired_keys", 0),
                    "evicted_keys": info.get("evicted_keys", 0)
                }
            }
        except Exception as e:
            logger.error(f"❌ Failed to get cache stats: {e}")
            return {"error": str(e)}
    
    @classmethod
    async def warm_cache_batch(cls, cache_operations: List[Dict[str, Any]]) -> int:
        """Warm cache with multiple operations in batch"""
        if not cls._pool:
            await cls.initialize()
            
        try:
            pipe = cls._pool.pipeline()
            count = 0
            
            for op in cache_operations:
                key = op.get("key")
                value = op.get("value")
                ttl = op.get("ttl", 3600)
                
                if key and value is not None:
                    if not isinstance(value, (str, int, float, bool)):
                        value = json.dumps(value)
                    
                    pipe.set(key, value, ex=ttl)
                    count += 1
            
            if count > 0:
                await pipe.execute()
                logger.info(f"✅ Cache warmed with {count} operations")
            
            return count
        except Exception as e:
            logger.error(f"❌ Cache warming failed: {e}")
            return 0

    # Rate limiting operations
    @classmethod
    async def increment_rate_limit(cls, key: str, window_seconds: int, limit: int) -> tuple[int, int]:
        """
        Increment rate limit counter using sliding window.
        Returns (current_count, remaining_requests).
        """
        if not cls._pool:
            await cls.initialize()
            
        try:
            # Use sliding window with sorted sets
            now = datetime.utcnow().timestamp()
            window_start = now - window_seconds
            
            pipe = cls._pool.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Add current request
            pipe.zadd(key, {str(now): now})
            
            # Count current requests
            pipe.zcard(key)
            
            # Set expiration
            pipe.expire(key, window_seconds)
            
            results = await pipe.execute()
            current_count = results[2]  # Result from zcard
            
            remaining = max(0, limit - current_count)
            return current_count, remaining
        except Exception as e:
            logger.error(f"❌ Rate limit increment failed for {key}: {e}")
            return 0, 0
    
    @classmethod
    async def get_rate_limit_status(cls, key: str, window_seconds: int, limit: int) -> Dict[str, Any]:
        """Get current rate limit status."""
        if not cls._pool:
            await cls.initialize()
            
        try:
            now = datetime.utcnow().timestamp()
            window_start = now - window_seconds
            
            # Clean old entries and count current
            pipe = cls._pool.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            pipe.ttl(key)
            
            results = await pipe.execute()
            current_count = results[1]
            ttl = results[2]
            
            return {
                'current_count': current_count,
                'limit': limit,
                'remaining': max(0, limit - current_count),
                'reset_time': datetime.utcnow() + timedelta(seconds=max(0, ttl)),
                'window_seconds': window_seconds
            }
        except Exception as e:
            logger.error(f"❌ Rate limit status check failed for {key}: {e}")
            return {
                'current_count': 0,
                'limit': limit,
                'remaining': limit,
                'reset_time': datetime.utcnow() + timedelta(seconds=window_seconds),
                'window_seconds': window_seconds
            }
    
    # Security event logging
    @classmethod
    async def log_security_event(cls, event_type: str, data: Dict[str, Any], expire_days: int = 30) -> bool:
        """Log security event."""
        if not cls._pool:
            await cls.initialize()
            
        try:
            timestamp = datetime.utcnow().isoformat()
            event_data = {
                'timestamp': timestamp,
                'event_type': event_type,
                'data': data
            }
            
            # Store in a sorted set for time-based queries
            key = f"security_events:{event_type}"
            score = datetime.utcnow().timestamp()
            
            await cls._pool.zadd(key, {json.dumps(event_data): score})
            await cls._pool.expire(key, expire_days * 86400)
            
            return True
        except Exception as e:
            logger.error(f"❌ Failed to log security event: {e}")
            return False
    
    @classmethod
    async def get_security_events(cls, event_type: str, hours: int = 24) -> list:
        """Get recent security events."""
        if not cls._pool:
            await cls.initialize()
            
        try:
            key = f"security_events:{event_type}"
            
            # Get events from the last N hours
            since = (datetime.utcnow() - timedelta(hours=hours)).timestamp()
            events = await cls._pool.zrangebyscore(key, since, '+inf')
            
            return [json.loads(event) for event in events]
        except Exception as e:
            logger.error(f"❌ Failed to get security events: {e}")
            return []

# Nonce Functions with Redis caching
async def set_nonce(user_id: str, nonce: str, ttl: int = 300) -> bool:
    return await RedisManager.cache_set(f"nonce:{user_id}", nonce, ttl_seconds=ttl)

async def verify_nonce(user_id: str, nonce: str) -> bool:
    stored_nonce = await RedisManager.cache_get(f"nonce:{user_id}")
    return stored_nonce == nonce

# Convenience functions for rate limiting
async def get_redis() -> Redis:
    """Get Redis client instance."""
    if not RedisManager._pool:
        await RedisManager.initialize()
    return RedisManager._pool

async def is_redis_connected() -> bool:
    """Check if Redis is connected."""
    try:
        if not RedisManager._pool:
            return False
        await RedisManager._pool.ping()
        return True
    except Exception:
        return False

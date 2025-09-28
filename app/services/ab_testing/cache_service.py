from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
import json

from app.services.database.redis import RedisManager, redis_cache
from app.services.database.mongodb import MongoDBManager, mongo_performance_monitor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ABTestCacheService:
    """
    Service for caching A/B test data in Redis to improve performance
    and reduce database load for frequently accessed test data.
    """
    
    # Cache TTL constants
    TEST_DETAILS_CACHE_TTL = 1800  # 30 minutes for test details
    TEST_RESULTS_CACHE_TTL = 900   # 15 minutes for test results (updated more frequently)
    USER_TESTS_CACHE_TTL = 3600    # 1 hour for user's test list
    ACTIVE_TESTS_CACHE_TTL = 300   # 5 minutes for active tests (checked frequently)
    
    @staticmethod
    @redis_cache(ttl_seconds=TEST_DETAILS_CACHE_TTL, key_prefix="abtest:details")
    async def get_test_details(test_id: str) -> Dict[str, Any]:
        """
        Get A/B test details with Redis caching.
        This method is decorated with redis_cache to automatically cache results.
        """
        try:
            # This will only execute if cache miss
            test_data = await MongoDBManager.find_with_options(
                "ab_tests", 
                {"test_id": test_id},
                limit=1
            )
            
            if not test_data or len(test_data) == 0:
                return {"error": "Test not found"}
                
            return test_data[0]
            
        except Exception as e:
            logger.error(f"Error getting A/B test details: {e}")
            return {"error": str(e)}
    
    @staticmethod
    @redis_cache(ttl_seconds=TEST_RESULTS_CACHE_TTL, key_prefix="abtest:results")
    async def get_test_results(test_id: str) -> Dict[str, Any]:
        """
        Get A/B test results with Redis caching.
        """
        try:
            # Get test details first
            test_details = await ABTestCacheService.get_test_details(test_id)
            if "error" in test_details:
                return test_details
                
            # Get performance metrics for each variation
            pipeline = [
                {"$match": {"test_id": test_id}},
                {"$group": {
                    "_id": "$variation",
                    "impressions": {"$sum": "$impressions"},
                    "engagements": {"$sum": "$engagements"},
                    "clicks": {"$sum": "$clicks"},
                    "conversions": {"$sum": "$conversions"}
                }}
            ]
            
            results = await MongoDBManager.aggregate("ab_test_metrics", pipeline)
            
            # Calculate performance metrics
            variations_data = {}
            for variation in results:
                var_id = variation["_id"]
                impressions = variation.get("impressions", 0)
                engagements = variation.get("engagements", 0)
                clicks = variation.get("clicks", 0)
                conversions = variation.get("conversions", 0)
                
                # Calculate rates
                engagement_rate = (engagements / impressions * 100) if impressions > 0 else 0
                click_rate = (clicks / impressions * 100) if impressions > 0 else 0
                conversion_rate = (conversions / impressions * 100) if impressions > 0 else 0
                
                variations_data[var_id] = {
                    "impressions": impressions,
                    "engagements": engagements,
                    "clicks": clicks,
                    "conversions": conversions,
                    "engagement_rate": round(engagement_rate, 2),
                    "click_rate": round(click_rate, 2),
                    "conversion_rate": round(conversion_rate, 2)
                }
            
            # Determine winner if test is complete
            winner = None
            if test_details.get("status") == "completed":
                target_metric = test_details.get("target_metric", "engagement_rate")
                best_score = 0
                
                for var_id, metrics in variations_data.items():
                    score = metrics.get(target_metric, 0)
                    if score > best_score:
                        best_score = score
                        winner = var_id
            
            return {
                "test_id": test_id,
                "status": test_details.get("status"),
                "start_time": test_details.get("start_time"),
                "end_time": test_details.get("end_time"),
                "target_metric": test_details.get("target_metric"),
                "variations": variations_data,
                "winner": winner
            }
            
        except Exception as e:
            logger.error(f"Error getting A/B test results: {e}")
            return {"error": str(e)}
    
    @staticmethod
    @redis_cache(ttl_seconds=USER_TESTS_CACHE_TTL, key_prefix="abtest:user")
    async def get_user_tests(user_id: str, status: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get A/B tests for a specific user with Redis caching.
        """
        try:
            # Build query
            query = {"user_id": user_id}
            if status:
                query["status"] = status
                
            # Get tests
            tests = await MongoDBManager.find_with_options(
                "ab_tests",
                query,
                sort=[("start_time", -1)],
                limit=limit
            )
            
            return tests
            
        except Exception as e:
            logger.error(f"Error getting user A/B tests: {e}")
            return [{"error": str(e)}]
    
    @staticmethod
    @redis_cache(ttl_seconds=ACTIVE_TESTS_CACHE_TTL, key_prefix="abtest:active")
    async def get_active_tests() -> List[Dict[str, Any]]:
        """
        Get all active A/B tests with Redis caching.
        """
        try:
            # Get active tests
            active_tests = await MongoDBManager.find_with_options(
                "ab_tests",
                {"status": "running"},
                sort=[("start_time", 1)]
            )
            
            return active_tests
            
        except Exception as e:
            logger.error(f"Error getting active A/B tests: {e}")
            return [{"error": str(e)}]
    
    @staticmethod
    async def update_test_metrics(test_id: str, variation: str, metrics: Dict[str, int]) -> bool:
        """
        Update A/B test metrics and invalidate related caches.
        """
        try:
            # Update metrics in database
            metrics["timestamp"] = datetime.now()
            metrics["test_id"] = test_id
            metrics["variation"] = variation
            
            await MongoDBManager.update_with_options(
                "ab_test_metrics",
                {"test_id": test_id, "variation": variation, "timestamp": metrics["timestamp"]},
                {"$set": metrics},
                upsert=True
            )
            
            # Invalidate caches
            await RedisManager.cache_delete(f"abtest:results:{test_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating A/B test metrics: {e}")
            return False
    
    @staticmethod
    async def invalidate_test_cache(test_id: str) -> int:
        """
        Invalidate all cached data for a specific A/B test.
        Returns the number of cache keys deleted.
        """
        try:
            # Delete all keys matching the test pattern
            pattern = f"*:{test_id}*"
            deleted = await RedisManager.cache_delete_pattern(pattern)
            logger.info(f"Invalidated {deleted} cache entries for test {test_id}")
            return deleted
        except Exception as e:
            logger.error(f"Error invalidating test cache: {e}")
            return 0
    
    @staticmethod
    async def invalidate_user_test_cache(user_id: str) -> int:
        """
        Invalidate all cached A/B test data for a specific user.
        Returns the number of cache keys deleted.
        """
        try:
            # Delete all keys matching the user's pattern
            pattern = f"abtest:user:{user_id}*"
            deleted = await RedisManager.cache_delete_pattern(pattern)
            logger.info(f"Invalidated {deleted} cache entries for user {user_id}")
            return deleted
        except Exception as e:
            logger.error(f"Error invalidating user test cache: {e}")
            return 0
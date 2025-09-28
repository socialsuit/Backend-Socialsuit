from datetime import datetime, timedelta
import uuid
from typing import Dict, List, Union, Any, Optional
import logging

from app.services.database.mongodb import MongoDBManager
from app.services.ab_testing.cache_service import ABTestCacheService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_ab_test(
    content_a: str,
    content_b: str,
    test_name: str = None,
    target_metric: str = "engagement_rate",
    audience_percentage: float = 0.5,
    platforms: List[str] = None,
    user_id: str = None
) -> Dict[str, Union[str, Dict]]:
    """
    Advanced A/B testing function for Social Suit with complete test tracking
    
    Args:
        content_a: First content variant
        content_b: Second content variant
        test_name: Optional test identifier
        target_metric: Primary metric to measure (engagement_rate/conversions/clicks)
        audience_percentage: Traffic split between variants (0.1 to 0.9)
        platforms: List of platforms to run the test on
        user_id: User ID who created the test
    
    Returns:
        Complete test configuration with metadata
    """
    # Validate inputs
    if not 0.1 <= audience_percentage <= 0.9:
        raise ValueError("Audience percentage must be between 0.1 and 0.9")
    
    if target_metric not in ["engagement_rate", "conversions", "clicks"]:
        raise ValueError("Invalid target metric specified")
    
    # Generate test ID if not provided
    test_id = f"ab_test_{uuid.uuid4().hex[:8]}"
    
    # Set default platforms if not provided
    if not platforms or platforms == ["all"]:
        platforms = ["facebook", "instagram", "twitter", "linkedin"]
    
    # Calculate audience sizes based on percentage
    # This is a simplified calculation - in a real system, you'd use actual user counts
    base_audience = 1000  # Example base audience size per platform
    total_audience = base_audience * len(platforms)
    audience_a = int(total_audience * audience_percentage)
    audience_b = total_audience - audience_a
    
    # Calculate estimated completion date (typically 3 days for A/B tests)
    start_time = datetime.now()
    end_time = start_time + timedelta(days=3)
    
    # Create test configuration
    test_config = {
        "test_id": test_id,
        "status": "running",
        "start_time": start_time.isoformat(),
        "estimated_completion": end_time.isoformat(),
        "end_time": None,
        "user_id": user_id,
        "test_name": test_name or f"Test {test_id}",
        "target_metric": target_metric,
        "platforms": platforms,
        "audience_split": {
            "A": audience_percentage,
            "B": round(1 - audience_percentage, 2)
        },
        "variations": {
            "A": {
                "content": content_a,
                "audience_size": audience_a,
                "current_performance": {
                    "impressions": 0,
                    "engagement_rate": 0,
                    "clicks": 0,
                    "conversions": 0,
                    "confidence_level": None
                }
            },
            "B": {
                "content": content_b,
                "audience_size": audience_b,
                "current_performance": {
                    "impressions": 0,
                    "engagement_rate": 0,
                    "clicks": 0,
                    "conversions": 0,
                    "confidence_level": None
                }
            }
        },
        "metadata": {
            "platform": "SocialSuit",
            "version": "2.1",
            "created_at": start_time.isoformat(),
            "updated_at": start_time.isoformat()
        }
    }
    
    # Store test in MongoDB
    try:
        await MongoDBManager.update_with_options(
            "ab_tests",
            {"test_id": test_id},
            {"$set": test_config},
            upsert=True
        )
        
        # Initialize metrics for each variation
        for variation in ["A", "B"]:
            initial_metrics = {
                "test_id": test_id,
                "variation": variation,
                "timestamp": start_time,
                "impressions": 0,
                "engagements": 0,
                "clicks": 0,
                "conversions": 0
            }
            
            await MongoDBManager.update_with_options(
                "ab_test_metrics",
                {"test_id": test_id, "variation": variation, "timestamp": start_time},
                {"$set": initial_metrics},
                upsert=True
            )
        
        # Invalidate user tests cache
        if user_id:
            await ABTestCacheService.invalidate_user_test_cache(user_id)
        
        # Format response for API
        response = {
            "test_id": test_id,
            "status": "running",
            "estimated_completion": end_time.isoformat(),
            "variations": {
                "A": {
                    "content": content_a,
                    "audience_size": audience_a,
                    "current_performance": {
                        "engagement_rate": 0,
                        "click_through_rate": 0
                    }
                },
                "B": {
                    "content": content_b,
                    "audience_size": audience_b,
                    "current_performance": {
                        "engagement_rate": 0,
                        "click_through_rate": 0
                    }
                }
            }
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error creating A/B test: {e}")
        raise

async def get_test_details(test_id: str) -> Dict[str, Any]:
    """
    Get details for a specific A/B test
    
    Args:
        test_id: The ID of the test to retrieve
        
    Returns:
        Test details and current performance metrics
    """
    try:
        # Use the cache service to get test details
        test_details = await ABTestCacheService.get_test_details(test_id)
        
        if "error" in test_details:
            return test_details
            
        # Get the latest results
        test_results = await ABTestCacheService.get_test_results(test_id)
        
        # Format response for API
        response = {
            "test_id": test_id,
            "status": test_details.get("status"),
            "test_name": test_details.get("test_name"),
            "start_time": test_details.get("start_time"),
            "estimated_completion": test_details.get("estimated_completion"),
            "end_time": test_details.get("end_time"),
            "target_metric": test_details.get("target_metric"),
            "platforms": test_details.get("platforms"),
            "variations": {}
        }
        
        # Add variation details
        for var_id, var_details in test_details.get("variations", {}).items():
            var_metrics = test_results.get("variations", {}).get(var_id, {})
            
            response["variations"][var_id] = {
                "content": var_details.get("content"),
                "audience_size": var_details.get("audience_size"),
                "current_performance": var_metrics
            }
            
        # Add winner if available
        if test_results.get("winner"):
            response["winner"] = test_results.get("winner")
            
        return response
        
    except Exception as e:
        logger.error(f"Error getting A/B test details: {e}")
        return {"error": str(e)}

async def get_user_tests(user_id: str, status: str = None, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get A/B tests for a specific user
    
    Args:
        user_id: The ID of the user
        status: Optional filter for test status (running, completed, etc.)
        limit: Maximum number of tests to return
        
    Returns:
        List of tests for the user
    """
    try:
        # Use the cache service to get user tests
        return await ABTestCacheService.get_user_tests(user_id, status, limit)
        
    except Exception as e:
        logger.error(f"Error getting user A/B tests: {e}")
        return [{"error": str(e)}]

async def update_test_metrics(test_id: str, variation: str, metrics: Dict[str, int]) -> bool:
    """
    Update metrics for a specific test variation
    
    Args:
        test_id: The ID of the test
        variation: The variation ID (A or B)
        metrics: Dictionary of metrics to update
        
    Returns:
        Success status
    """
    try:
        # Use the cache service to update metrics
        return await ABTestCacheService.update_test_metrics(test_id, variation, metrics)
        
    except Exception as e:
        logger.error(f"Error updating A/B test metrics: {e}")
        return False

async def complete_test(test_id: str) -> Dict[str, Any]:
    """
    Mark a test as completed and determine the winner
    
    Args:
        test_id: The ID of the test to complete
        
    Returns:
        Final test results with winner
    """
    try:
        # Get current test details
        test_details = await ABTestCacheService.get_test_details(test_id)
        
        if "error" in test_details:
            return test_details
            
        # Get current results
        test_results = await ABTestCacheService.get_test_results(test_id)
        
        # Determine winner based on target metric
        target_metric = test_details.get("target_metric", "engagement_rate")
        variations = test_results.get("variations", {})
        
        winner = None
        best_score = 0
        
        for var_id, metrics in variations.items():
            score = metrics.get(target_metric, 0)
            if score > best_score:
                best_score = score
                winner = var_id
        
        # Update test status
        end_time = datetime.now()
        
        await MongoDBManager.update_with_options(
            "ab_tests",
            {"test_id": test_id},
            {"$set": {
                "status": "completed",
                "end_time": end_time.isoformat(),
                "winner": winner,
                "metadata.updated_at": end_time.isoformat()
            }},
            upsert=False
        )
        
        # Invalidate caches
        await ABTestCacheService.invalidate_test_cache(test_id)
        
        # Get updated results
        updated_results = await ABTestCacheService.get_test_results(test_id)
        
        return updated_results
        
    except Exception as e:
        logger.error(f"Error completing A/B test: {e}")
        return {"error": str(e)}
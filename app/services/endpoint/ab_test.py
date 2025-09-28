from fastapi import APIRouter, Body, HTTPException, Depends, Query, Path, Request
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import logging
from app.services.ab_testing.ab_test_service import run_ab_test, get_test_details, get_user_tests, update_test_metrics, complete_test
from app.services.auth.auth_guard import auth_required, get_current_user
from app.services.models.user_model import User
from app.services.database.database import get_db
from app.services.repositories.user_repository import UserRepository
from app.services.dependencies.repository_providers import get_user_repository
from app.services.utils.logger_config import setup_logger
from app.services.security.validation_models import (
    UserIdValidation,
    ABTestRequest,
    ABTestContentValidation,
    ABTestConfigValidation,
    ContentValidation
)
from datetime import datetime, timedelta
import uuid

# Set up logger
logger = setup_logger("secure_ab_test_api")

class ABTestAuditLogger:
    """Audit logger for A/B test operations."""
    
    @staticmethod
    def log_test_creation(user_id: str, test_id: str, requester_id: str, success: bool, error: str = None):
        """Log A/B test creation attempts."""
        logger.info(f"AUDIT: AB Test creation - User: {user_id}, Test: {test_id}, "
                   f"Requester: {requester_id}, Success: {success}, Error: {error}")
    
    @staticmethod
    def log_test_access(user_id: str, test_id: str, requester_id: str, action: str, success: bool, error: str = None):
        """Log A/B test access attempts."""
        logger.info(f"AUDIT: AB Test access - User: {user_id}, Test: {test_id}, "
                   f"Requester: {requester_id}, Action: {action}, Success: {success}, Error: {error}")

class ABTestVariation(BaseModel):
    """Model representing a single A/B test variation."""
    content: str = Field(..., description="The content for this variation")
    audience_size: int = Field(..., description="Number of users who will see this variation")
    current_performance: Optional[Dict[str, float]] = Field(None, description="Current performance metrics")

class ABTestRequest(BaseModel):
    """Request model for creating an A/B test.
    
    Contains all parameters needed to set up a new A/B test between two content variations.
    """
    content_a: str = Field(..., description="First content variation to test")
    content_b: str = Field(..., description="Second content variation to test")
    test_name: Optional[str] = Field(None, description="Name of the test for tracking purposes")
    target_metric: str = Field(
        "engagement_rate", 
        description="Metric to optimize for",
        example="engagement_rate"
    )
    audience_percentage: float = Field(
        0.5, 
        ge=0.1, 
        le=1.0, 
        description="Percentage of audience to include in test (0.1-1.0)"
    )
    platforms: List[str] = Field(
        ["all"], 
        description="Platforms to run the test on",
        example=["instagram", "facebook"]
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "content_a": "Check out our new product launch! #innovation",
                "content_b": "Exciting news! Our revolutionary product is here! #gamechanger",
                "test_name": "Product Launch Announcement",
                "target_metric": "engagement_rate",
                "audience_percentage": 0.5,
                "platforms": ["instagram", "facebook"]
            }
        }

class ABTestResponse(BaseModel):
    """Response model for A/B test creation.
    
    Contains details about the created test and its variations.
    """
    test_id: str = Field(..., description="Unique identifier for the test")
    status: str = Field(..., description="Current status of the test")
    estimated_completion: str = Field(..., description="Estimated completion date/time")
    variations: Dict[str, ABTestVariation] = Field(..., description="Test variations and their details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "test_id": "ab_test_12345",
                "status": "running",
                "estimated_completion": "2023-06-18T15:30:00Z",
                "variations": {
                    "A": {
                        "content": "Check out our new product launch! #innovation",
                        "audience_size": 500,
                        "current_performance": {
                            "engagement_rate": 2.4,
                            "click_through_rate": 1.2
                        }
                    },
                    "B": {
                        "content": "Exciting news! Our revolutionary product is here! #gamechanger",
                        "audience_size": 500,
                        "current_performance": {
                            "engagement_rate": 3.1,
                            "click_through_rate": 1.8
                        }
                    }
                }
            }
        }

router = APIRouter(
    prefix="/ab-testing", 
    tags=["A/B Testing"]
)

class TestMetricsUpdate(BaseModel):
    """Model for updating test metrics."""
    impressions: Optional[int] = Field(0, description="Number of impressions")
    engagements: Optional[int] = Field(0, description="Number of engagements")
    clicks: Optional[int] = Field(0, description="Number of clicks")
    conversions: Optional[int] = Field(0, description="Number of conversions")
    
    class Config:
        json_schema_extra = {
            "example": {
                "impressions": 100,
                "engagements": 25,
                "clicks": 10,
                "conversions": 2
            }
        }

@router.post(
    "/create", 
    response_model=ABTestResponse, 
    summary="Create A/B Test",
    description="Creates a new A/B test with two content variations to determine which performs better across specified platforms",
    response_description="Returns the created A/B test details including test ID and variation information"
)
async def create_ab_test(
    request: Request,
    test_data: ABTestRequest = Body(...),
    current_user: User = Depends(auth_required)
):
    """Create a new A/B test for content optimization with enhanced validation and security.
    
    This endpoint sets up an A/B test between two content variations to determine
    which performs better according to the specified target metric.
    
    Args:
        request: The HTTP request object
        test_data: The A/B test configuration including content variations
        current_user: The authenticated user (injected by dependency)
        
    Returns:
        A JSON object containing the created test details
        
    Raises:
        HTTPException: If test creation fails
    """
    # Generate unique test ID for audit logging
    test_id = str(uuid.uuid4())
    
    try:
        # Validate the test request
        validated_request = ABTestRequest(**test_data.dict())
        
        # Additional security validation for content
        content_validation_a = ContentValidation(content=validated_request.content_a)
        content_validation_b = ContentValidation(content=validated_request.content_b)
        
        if not content_validation_a.is_safe or not content_validation_b.is_safe:
            ABTestAuditLogger.log_test_creation(str(current_user.id), test_id, str(current_user.id), False, "Unsafe content detected")
            raise HTTPException(status_code=400, detail="Content contains potentially unsafe elements")
        
        result = await run_ab_test(
            content_a=validated_request.content_a,
            content_b=validated_request.content_b,
            test_name=validated_request.test_name,
            target_metric=validated_request.target_metric,
            audience_percentage=validated_request.audience_percentage,
            platforms=validated_request.platforms,
            user_id=str(current_user.id)
        )
        
        ABTestAuditLogger.log_test_creation(str(current_user.id), test_id, str(current_user.id), True)
        
        return result
    except HTTPException as e:
        raise e
    except ValueError as e:
        ABTestAuditLogger.log_test_creation(str(current_user.id), test_id, str(current_user.id), False, str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        ABTestAuditLogger.log_test_creation(str(current_user.id), test_id, str(current_user.id), False, str(e))
        logger.error(f"Error creating A/B test: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create A/B test: {str(e)}")

@router.get(
    "/tests/{test_id}", 
    response_model=Dict[str, Any], 
    summary="Get A/B Test Details",
    description="Retrieves details and current performance metrics for a specific A/B test",
    response_description="Returns the A/B test details including performance metrics for each variation"
)
async def get_ab_test(
    request: Request,
    test_id: str = Path(..., description="The ID of the A/B test to retrieve"),
    current_user: User = Depends(auth_required)
):
    """Get details for a specific A/B test with enhanced security.
    
    Args:
        request: The HTTP request object
        test_id: The ID of the test to retrieve
        current_user: The authenticated user (injected by dependency)
        
    Returns:
        A JSON object containing the test details and performance metrics
        
    Raises:
        HTTPException: If test retrieval fails or test not found
    """
    try:
        # Validate test ID format
        if not test_id or len(test_id.strip()) == 0:
            raise HTTPException(status_code=400, detail="Invalid test ID")
        
        # Sanitize test ID
        sanitized_test_id = test_id.strip()
        
        result = await get_test_details(sanitized_test_id)
        
        if "error" in result:
            ABTestAuditLogger.log_test_access(str(current_user.id), sanitized_test_id, str(current_user.id), "get_details", False, result['error'])
            raise HTTPException(status_code=404, detail=f"A/B test not found: {result['error']}")
            
        # Verify user has access to this test
        if "user_id" in result and result["user_id"] != str(current_user.id):
            ABTestAuditLogger.log_test_access(str(current_user.id), sanitized_test_id, str(current_user.id), "get_details", False, "Access denied")
            raise HTTPException(status_code=403, detail="You do not have permission to access this test")
        
        ABTestAuditLogger.log_test_access(str(current_user.id), sanitized_test_id, str(current_user.id), "get_details", True)
        
        return {
            **result,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        ABTestAuditLogger.log_test_access(str(current_user.id), test_id, str(current_user.id), "get_details", False, str(e))
        logger.error(f"Error retrieving A/B test: {str(e)}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"A/B test not found: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve A/B test: {str(e)}")

@router.get(
    "/user/tests", 
    response_model=List[Dict[str, Any]], 
    summary="Get User's A/B Tests",
    description="Retrieves all A/B tests created by the authenticated user",
    response_description="Returns a list of A/B tests with basic information"
)
async def get_user_ab_tests(
    status: Optional[str] = Query(None, description="Filter tests by status (running, completed)"),
    limit: int = Query(10, description="Maximum number of tests to return"),
    current_user: User = Depends(auth_required)
):
    """Get all A/B tests for the authenticated user.
    
    Args:
        status: Optional filter for test status
        limit: Maximum number of tests to return
        current_user: The authenticated user (injected by dependency)
        
    Returns:
        A list of A/B tests with basic information
        
    Raises:
        HTTPException: If test retrieval fails
    """
    try:
        results = await get_user_tests(str(current_user.id), status, limit)
        
        if results and "error" in results[0]:
            raise Exception(results[0]["error"])
            
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve A/B tests: {str(e)}")

@router.post(
    "/tests/{test_id}/metrics/{variation}", 
    response_model=Dict[str, Any], 
    summary="Update Test Metrics",
    description="Updates performance metrics for a specific variation of an A/B test",
    response_description="Returns success status"
)
async def update_ab_test_metrics(
    test_id: str = Path(..., description="The ID of the A/B test"),
    variation: str = Path(..., description="The variation ID (A or B)"),
    metrics: TestMetricsUpdate = Body(...),
    current_user: User = Depends(auth_required)
):
    """Update metrics for a specific test variation.
    
    Args:
        test_id: The ID of the test
        variation: The variation ID (A or B)
        metrics: The metrics to update
        current_user: The authenticated user (injected by dependency)
        
    Returns:
        Success status
        
    Raises:
        HTTPException: If metrics update fails
    """
    try:
        # Verify user has access to this test
        test_details = await get_test_details(test_id)
        
        if "error" in test_details:
            raise HTTPException(status_code=404, detail=f"A/B test not found: {test_details['error']}")
            
        if "user_id" in test_details and test_details["user_id"] != str(current_user.id):
            raise HTTPException(status_code=403, detail="You do not have permission to update this test")
            
        # Update metrics
        metrics_dict = metrics.dict()
        success = await update_test_metrics(test_id, variation, metrics_dict)
        
        if not success:
            raise Exception("Failed to update metrics")
            
        return {"success": True, "message": "Metrics updated successfully"}
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"A/B test not found: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update metrics: {str(e)}")

@router.post(
    "/tests/{test_id}/complete", 
    response_model=Dict[str, Any], 
    summary="Complete A/B Test",
    description="Marks an A/B test as completed and determines the winner",
    response_description="Returns the final test results with winner"
)
async def complete_ab_test(
    test_id: str = Path(..., description="The ID of the A/B test to complete"),
    current_user: User = Depends(auth_required)
):
    """Complete an A/B test and determine the winner.
    
    Args:
        test_id: The ID of the test to complete
        current_user: The authenticated user (injected by dependency)
        
    Returns:
        Final test results with winner
        
    Raises:
        HTTPException: If test completion fails
    """
    try:
        # Verify user has access to this test
        test_details = await get_test_details(test_id)
        
        if "error" in test_details:
            raise HTTPException(status_code=404, detail=f"A/B test not found: {test_details['error']}")
            
        if "user_id" in test_details and test_details["user_id"] != str(current_user.id):
            raise HTTPException(status_code=403, detail="You do not have permission to complete this test")
            
        # Complete test
        result = await complete_test(test_id)
        
        if "error" in result:
            raise Exception(result["error"])
            
        return result
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"A/B test not found: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to complete A/B test: {str(e)}")

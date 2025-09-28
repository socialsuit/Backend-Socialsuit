import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.services.ab_testing.ab_test_service import (
    run_ab_test, get_test_details, get_user_tests, 
    update_test_metrics, complete_test
)
from app.services.ab_testing.cache_service import ABTestCacheService
from main import app

client = TestClient(app)

class TestABTestService:
    """Test cases for AB test service functions"""
    
    @pytest.fixture
    def mock_mongo_manager(self):
        with patch('app.services.ab_testing.ab_test_service.MongoDBManager') as mock:
            mock_instance = AsyncMock()
            mock.return_value = mock_instance
            yield mock_instance
    
    @pytest.fixture
    def mock_cache_service(self):
        with patch('app.services.ab_testing.ab_test_service.ABTestCacheService') as mock:
            yield mock
    
    @pytest.mark.asyncio
    async def test_run_ab_test_success(self, mock_mongo_manager, mock_cache_service):
        """Test successful AB test creation"""
        # Mock MongoDB operations
        mock_mongo_manager.insert_one.return_value = None
        mock_cache_service.invalidate_user_test_cache = AsyncMock()
        
        test_data = {
            "name": "Test Campaign",
            "description": "Testing button colors",
            "variations": [
                {"name": "Control", "content": {"button_color": "blue"}},
                {"name": "Variant", "content": {"button_color": "red"}}
            ],
            "target_metric": "conversion_rate",
            "duration_days": 7,
            "traffic_split": 50
        }
        
        result = await run_ab_test("user123", test_data)
        
        assert "test_id" in result
        assert result["name"] == "Test Campaign"
        assert result["status"] == "active"
        assert len(result["variations"]) == 2
        
        # Verify MongoDB insert was called
        mock_mongo_manager.insert_one.assert_called_once()
        
        # Verify cache invalidation was called
        mock_cache_service.invalidate_user_test_cache.assert_called_once_with("user123")
    
    @pytest.mark.asyncio
    async def test_run_ab_test_invalid_traffic_split(self):
        """Test AB test creation with invalid traffic split"""
        test_data = {
            "name": "Test Campaign",
            "description": "Testing button colors",
            "variations": [
                {"name": "Control", "content": {"button_color": "blue"}},
                {"name": "Variant", "content": {"button_color": "red"}}
            ],
            "target_metric": "conversion_rate",
            "duration_days": 7,
            "traffic_split": 150  # Invalid: > 100
        }
        
        with pytest.raises(ValueError, match="Traffic split must be between 1 and 100"):
            await run_ab_test("user123", test_data)
    
    @pytest.mark.asyncio
    async def test_get_test_details_success(self, mock_cache_service):
        """Test successful test details retrieval"""
        mock_test_data = {
            "test_id": "test123",
            "name": "Test Campaign",
            "status": "active",
            "variations": [
                {"name": "Control", "metrics": {"impressions": 1000, "conversions": 50}},
                {"name": "Variant", "metrics": {"impressions": 1000, "conversions": 75}}
            ]
        }
        
        mock_cache_service.get_test_details.return_value = mock_test_data
        
        result = await get_test_details("test123", "user123")
        
        assert result["test_id"] == "test123"
        assert result["name"] == "Test Campaign"
        mock_cache_service.get_test_details.assert_called_once_with("test123", "user123")
    
    @pytest.mark.asyncio
    async def test_complete_test_success(self, mock_mongo_manager, mock_cache_service):
        """Test successful test completion"""
        mock_test_data = {
            "test_id": "test123",
            "user_id": "user123",
            "status": "active",
            "target_metric": "conversion_rate",
            "variations": [
                {"name": "Control", "metrics": {"impressions": 1000, "conversions": 50}},
                {"name": "Variant", "metrics": {"impressions": 1000, "conversions": 75}}
            ]
        }
        
        mock_cache_service.get_test_details.return_value = mock_test_data
        mock_mongo_manager.update_one.return_value = None
        mock_cache_service.invalidate_test_cache = AsyncMock()
        mock_cache_service.invalidate_user_test_cache = AsyncMock()
        
        result = await complete_test("test123", "user123")
        
        assert result["status"] == "completed"
        assert result["winner"] == "Variant"  # Higher conversion rate
        assert "completion_date" in result
        
        # Verify cache invalidation
        mock_cache_service.invalidate_test_cache.assert_called_once_with("test123")
        mock_cache_service.invalidate_user_test_cache.assert_called_once_with("user123")


class TestABTestCacheService:
    """Test cases for AB test cache service"""
    
    @pytest.fixture
    def mock_redis_manager(self):
        with patch('app.services.ab_testing.cache_service.RedisManager') as mock:
            mock_instance = AsyncMock()
            mock.get_connection.return_value.__aenter__.return_value = mock_instance
            yield mock_instance
    
    @pytest.fixture
    def mock_mongo_manager(self):
        with patch('app.services.ab_testing.cache_service.MongoDBManager') as mock:
            mock_instance = AsyncMock()
            mock.return_value = mock_instance
            yield mock_instance
    
    @pytest.mark.asyncio
    async def test_get_test_details_cache_hit(self, mock_redis_manager):
        """Test cache hit for test details"""
        cached_data = {
            "test_id": "test123",
            "name": "Cached Test",
            "status": "active"
        }
        
        mock_redis_manager.cache_get.return_value = cached_data
        
        result = await ABTestCacheService.get_test_details("test123", "user123")
        
        assert result == cached_data
        mock_redis_manager.cache_get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_test_details_cache_miss(self, mock_redis_manager, mock_mongo_manager):
        """Test cache miss for test details"""
        # Cache miss
        mock_redis_manager.cache_get.return_value = None
        
        # MongoDB data
        mongo_data = {
            "test_id": "test123",
            "name": "DB Test",
            "status": "active",
            "user_id": "user123"
        }
        mock_mongo_manager.find_one.return_value = mongo_data
        mock_redis_manager.cache_set = AsyncMock()
        
        result = await ABTestCacheService.get_test_details("test123", "user123")
        
        assert result == mongo_data
        mock_redis_manager.cache_set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_invalidate_test_cache(self, mock_redis_manager):
        """Test cache invalidation for a specific test"""
        mock_redis_manager.cache_delete_pattern = AsyncMock()
        
        await ABTestCacheService.invalidate_test_cache("test123")
        
        mock_redis_manager.cache_delete_pattern.assert_called_once_with("ab_test:test123:*")


class TestABTestEndpoints:
    """Test cases for AB test API endpoints"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.test_token = "valid_jwt_token"
        self.headers = {"Authorization": f"Bearer {self.test_token}"}
    
    @patch('app.services.endpoint.ab_test.verify_token')
    @patch('app.services.endpoint.ab_test.run_ab_test')
    def test_create_ab_test_success(self, mock_run_ab_test, mock_verify_token):
        """Test successful AB test creation endpoint"""
        # Mock token verification
        mock_verify_token.return_value = {"user_id": "user123"}
        
        # Mock AB test creation
        mock_run_ab_test.return_value = {
            "test_id": "test123",
            "name": "Test Campaign",
            "status": "active"
        }
        
        test_data = {
            "name": "Test Campaign",
            "description": "Testing button colors",
            "variations": [
                {"name": "Control", "content": {"button_color": "blue"}},
                {"name": "Variant", "content": {"button_color": "red"}}
            ],
            "target_metric": "conversion_rate",
            "duration_days": 7,
            "traffic_split": 50
        }
        
        response = client.post(
            "/api/v1/ab-tests",
            json=test_data,
            headers=self.headers
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["test_id"] == "test123"
        assert result["name"] == "Test Campaign"
    
    @patch('app.services.endpoint.ab_test.verify_token')
    def test_create_ab_test_invalid_data(self, mock_verify_token):
        """Test AB test creation with invalid data"""
        mock_verify_token.return_value = {"user_id": "user123"}
        
        # Missing required fields
        test_data = {
            "name": "Test Campaign"
            # Missing other required fields
        }
        
        response = client.post(
            "/api/v1/ab-tests",
            json=test_data,
            headers=self.headers
        )
        
        assert response.status_code == 422  # Validation error
    
    @patch('app.services.endpoint.ab_test.verify_token')
    @patch('app.services.endpoint.ab_test.get_test_details')
    def test_get_test_details_success(self, mock_get_test_details, mock_verify_token):
        """Test successful test details retrieval endpoint"""
        mock_verify_token.return_value = {"user_id": "user123"}
        mock_get_test_details.return_value = {
            "test_id": "test123",
            "name": "Test Campaign",
            "status": "active"
        }
        
        response = client.get(
            "/api/v1/ab-tests/test123",
            headers=self.headers
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["test_id"] == "test123"
    
    @patch('app.services.endpoint.ab_test.verify_token')
    @patch('app.services.endpoint.ab_test.update_test_metrics')
    def test_update_test_metrics_success(self, mock_update_metrics, mock_verify_token):
        """Test successful test metrics update endpoint"""
        mock_verify_token.return_value = {"user_id": "user123"}
        mock_update_metrics.return_value = {"success": True}
        
        metrics_data = {
            "impressions": 100,
            "engagements": 25,
            "clicks": 15,
            "conversions": 5
        }
        
        response = client.post(
            "/api/v1/ab-tests/test123/metrics/control",
            json=metrics_data,
            headers=self.headers
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True


if __name__ == "__main__":
    pytest.main([__file__])
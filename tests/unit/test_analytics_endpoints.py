import pytest
from httpx import AsyncClient
from fastapi import status
from datetime import datetime, timedelta
import json

@pytest.mark.asyncio
async def test_get_user_analytics(async_client: AsyncClient):
    """Test retrieving user analytics"""
    # Login to get authentication token
    login_data = {
        "email": "test_user@example.com",
        "password": "securePassword123!"
    }
    
    login_response = await async_client.post("/auth/login", json=login_data)
    assert login_response.status_code == status.HTTP_200_OK
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test getting user analytics overview
    overview_response = await async_client.get("/analytics/overview", headers=headers)
    assert overview_response.status_code == status.HTTP_200_OK
    overview_data = overview_response.json()
    
    # Verify the structure of the response
    assert "total_followers" in overview_data
    assert "total_engagement" in overview_data
    assert "platforms" in overview_data
    
    # Test getting platform-specific analytics
    platforms = ["twitter", "facebook", "instagram", "linkedin"]
    
    for platform in platforms:
        platform_response = await async_client.get(f"/analytics/platforms/{platform}", headers=headers)
        assert platform_response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
        
        if platform_response.status_code == status.HTTP_200_OK:
            platform_data = platform_response.json()
            assert "followers" in platform_data
            assert "engagement_rate" in platform_data
            assert "post_count" in platform_data

@pytest.mark.asyncio
async def test_analytics_time_series(async_client: AsyncClient):
    """Test retrieving time series analytics data"""
    # Login to get authentication token
    login_data = {
        "email": "test_user@example.com",
        "password": "securePassword123!"
    }
    
    login_response = await async_client.post("/auth/login", json=login_data)
    assert login_response.status_code == status.HTTP_200_OK
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test getting time series data
    time_series_response = await async_client.get(
        "/analytics/time-series?metric=followers&platform=twitter", 
        headers=headers
    )
    assert time_series_response.status_code == status.HTTP_200_OK
    time_series_data = time_series_response.json()
    
    # Verify the structure of the response
    assert "labels" in time_series_data
    assert "datasets" in time_series_data
    assert len(time_series_data["datasets"]) > 0
    assert "label" in time_series_data["datasets"][0]
    assert "data" in time_series_data["datasets"][0]
    
    # Test with different metrics
    metrics = ["engagement", "impressions", "clicks"]
    
    for metric in metrics:
        metric_response = await async_client.get(
            f"/analytics/time-series?metric={metric}&platform=twitter", 
            headers=headers
        )
        assert metric_response.status_code == status.HTTP_200_OK
        metric_data = metric_response.json()
        assert "labels" in metric_data
        assert "datasets" in metric_data

@pytest.mark.asyncio
async def test_content_performance_analytics(async_client: AsyncClient):
    """Test retrieving content performance analytics"""
    # Login to get authentication token
    login_data = {
        "email": "test_user@example.com",
        "password": "securePassword123!"
    }
    
    login_response = await async_client.post("/auth/login", json=login_data)
    assert login_response.status_code == status.HTTP_200_OK
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test getting top performing content
    top_content_response = await async_client.get("/analytics/top-content", headers=headers)
    assert top_content_response.status_code == status.HTTP_200_OK
    top_content_data = top_content_response.json()
    
    # Verify the structure of the response
    assert isinstance(top_content_data, list)
    
    if len(top_content_data) > 0:
        assert "content_id" in top_content_data[0]
        assert "platform" in top_content_data[0]
        assert "engagement" in top_content_data[0]
        assert "content_type" in top_content_data[0]
    
    # Test filtering by platform
    platforms = ["twitter", "facebook", "instagram", "linkedin"]
    
    for platform in platforms:
        platform_content_response = await async_client.get(
            f"/analytics/top-content?platform={platform}", 
            headers=headers
        )
        assert platform_content_response.status_code == status.HTTP_200_OK
        platform_content_data = platform_content_response.json()
        
        # If there's data, verify it's for the correct platform
        if len(platform_content_data) > 0:
            for item in platform_content_data:
                assert item["platform"] == platform

@pytest.mark.asyncio
async def test_analytics_data_collection(async_client: AsyncClient):
    """Test triggering analytics data collection"""
    # Login to get authentication token
    login_data = {
        "email": "test_user@example.com",
        "password": "securePassword123!"
    }
    
    login_response = await async_client.post("/auth/login", json=login_data)
    assert login_response.status_code == status.HTTP_200_OK
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test triggering data collection for a specific platform
    platforms = ["twitter", "facebook", "instagram", "linkedin"]
    
    for platform in platforms:
        collect_response = await async_client.post(
            f"/analytics/collect/{platform}", 
            headers=headers
        )
        assert collect_response.status_code in [status.HTTP_200_OK, status.HTTP_202_ACCEPTED]
        collect_data = collect_response.json()
        assert "message" in collect_data
    
    # Test triggering data collection for all platforms
    collect_all_response = await async_client.post("/analytics/collect", headers=headers)
    assert collect_all_response.status_code in [status.HTTP_200_OK, status.HTTP_202_ACCEPTED]
    collect_all_data = collect_all_response.json()
    assert "message" in collect_all_data
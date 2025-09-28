import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import json

# Import the main app
# Note: Adjust imports based on actual project structure
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def auth_headers():
    # This fixture simulates a logged-in user
    # In a real test, you would actually perform the login
    client = TestClient(app)
    login_response = client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "testpassword"
        }
    )
    token = login_response.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def test_user_id():
    return "test-user-id"

class TestAnalyticsIntegration:
    def test_complete_analytics_workflow(self, client, auth_headers):
        """
        Test the complete workflow of the analytics feature:
        1. Trigger analytics collection
        2. Get user analytics overview
        3. Get time series data
        4. Get content performance
        5. Get platform-specific insights
        """
        # Step 1: Trigger analytics collection
        # This would typically be done by a scheduler, but we can trigger it manually for testing
        trigger_response = client.post(
            "/analytics/trigger-collection",
            headers=auth_headers,
            json={
                "platforms": ["instagram", "twitter", "facebook"]
            }
        )
        assert trigger_response.status_code == 202  # Accepted
        
        # Step 2: Get user analytics overview
        overview_response = client.get(
            "/analytics/overview",
            headers=auth_headers
        )
        assert overview_response.status_code == 200
        overview_data = overview_response.json()
        
        # Verify the structure of the overview data
        assert "total_followers" in overview_data
        assert "engagement_rate" in overview_data
        assert "platforms" in overview_data
        assert isinstance(overview_data["platforms"], list)
        
        # Step 3: Get time series data
        time_series_response = client.get(
            "/analytics/time-series",
            headers=auth_headers,
            params={
                "platform": "instagram",
                "metric": "followers",
                "start_date": (datetime.utcnow() - timedelta(days=30)).isoformat(),
                "end_date": datetime.utcnow().isoformat(),
                "interval": "day"
            }
        )
        assert time_series_response.status_code == 200
        time_series_data = time_series_response.json()
        
        # Verify the structure of the time series data
        assert "dates" in time_series_data
        assert "values" in time_series_data
        assert len(time_series_data["dates"]) == len(time_series_data["values"])
        
        # Step 4: Get content performance
        content_response = client.get(
            "/analytics/content-performance",
            headers=auth_headers,
            params={
                "platform": "instagram",
                "start_date": (datetime.utcnow() - timedelta(days=30)).isoformat(),
                "end_date": datetime.utcnow().isoformat(),
                "sort_by": "engagement",
                "limit": 10
            }
        )
        assert content_response.status_code == 200
        content_data = content_response.json()
        
        # Verify the structure of the content performance data
        assert isinstance(content_data, list)
        if content_data:  # If there's any content data
            assert "post_id" in content_data[0]
            assert "engagement" in content_data[0]
            assert "impressions" in content_data[0]
            assert "published_at" in content_data[0]
        
        # Step 5: Get platform-specific insights
        insights_response = client.get(
            "/analytics/insights",
            headers=auth_headers,
            params={"platform": "instagram"}
        )
        assert insights_response.status_code == 200
        insights_data = insights_response.json()
        
        # Verify the structure of the insights data
        assert "audience" in insights_data
        assert "best_posting_times" in insights_data
        assert "top_performing_content_types" in insights_data
    
    def test_analytics_filtering(self, client, auth_headers):
        """
        Test filtering analytics data by various parameters
        """
        # Test filtering time series data by different intervals
        intervals = ["day", "week", "month"]
        for interval in intervals:
            response = client.get(
                "/analytics/time-series",
                headers=auth_headers,
                params={
                    "platform": "instagram",
                    "metric": "followers",
                    "start_date": (datetime.utcnow() - timedelta(days=90)).isoformat(),
                    "end_date": datetime.utcnow().isoformat(),
                    "interval": interval
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert "dates" in data
            assert "values" in data
        
        # Test filtering content performance by different metrics
        sort_metrics = ["engagement", "impressions", "likes", "comments"]
        for metric in sort_metrics:
            response = client.get(
                "/analytics/content-performance",
                headers=auth_headers,
                params={
                    "platform": "instagram",
                    "start_date": (datetime.utcnow() - timedelta(days=30)).isoformat(),
                    "end_date": datetime.utcnow().isoformat(),
                    "sort_by": metric,
                    "limit": 5
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) <= 5  # Should respect the limit parameter
        
        # Test filtering by platform
        platforms = ["instagram", "twitter", "facebook"]
        for platform in platforms:
            response = client.get(
                "/analytics/overview",
                headers=auth_headers,
                params={"platform": platform}
            )
            assert response.status_code == 200
            data = response.json()
            if "platforms" in data:
                platform_data = next((p for p in data["platforms"] if p["name"] == platform), None)
                if platform_data:
                    assert platform_data["name"] == platform
    

    
    def test_analytics_comparison(self, client, auth_headers):
        """
        Test comparing analytics data between different time periods
        """
        comparison_response = client.get(
            "/analytics/comparison",
            headers=auth_headers,
            params={
                "platform": "instagram",
                "metric": "engagement_rate",
                "current_start": (datetime.utcnow() - timedelta(days=30)).isoformat(),
                "current_end": datetime.utcnow().isoformat(),
                "previous_start": (datetime.utcnow() - timedelta(days=60)).isoformat(),
                "previous_end": (datetime.utcnow() - timedelta(days=30)).isoformat()
            }
        )
        assert comparison_response.status_code == 200
        comparison_data = comparison_response.json()
        
        # Verify the structure of the comparison data
        assert "current_period" in comparison_data
        assert "previous_period" in comparison_data
        assert "change" in comparison_data
        assert "percentage_change" in comparison_data
    
    def test_unauthorized_access(self, client):
        """
        Test that analytics endpoints require authentication
        """
        # Try to access analytics overview without authentication
        response = client.get("/analytics/overview")
        assert response.status_code == 401  # Unauthorized
        
        # Try to trigger analytics collection without authentication
        response = client.post(
            "/analytics/trigger-collection",
            json={"platforms": ["instagram"]}
        )
        assert response.status_code == 401  # Unauthorized
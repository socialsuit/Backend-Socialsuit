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
    return {"Authorization": "Bearer test_token"}

@pytest.fixture
def test_user_id():
    return "test-user-id"

@pytest.fixture
def test_ab_test():
    return {
        "name": "Headline Test",
        "description": "Testing different headlines for engagement",
        "platform": "instagram",
        "start_date": datetime.utcnow().isoformat(),
        "end_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
        "variants": [
            {
                "name": "Variant A",
                "content_modifications": {
                    "headline": "Amazing New Feature!"
                }
            },
            {
                "name": "Variant B",
                "content_modifications": {
                    "headline": "You Won't Believe This New Feature!"
                }
            }
        ],
        "success_metrics": ["clicks", "engagement_rate"],
        "audience_targeting": {
            "age_range": [18, 35],
            "regions": ["US", "CA", "UK"]
        }
    }

class TestABTestingIntegration:
    def test_complete_ab_testing_workflow(self, client, auth_headers, test_user_id, test_ab_test):
        """
        Test the complete workflow of the AB testing feature:
        1. Create an AB test
        2. Get the test
        3. Update the test
        4. Start the test
        5. Record variant performance
        6. Get test results
        7. Stop the test
        8. Delete the test
        """
        # Step 1: Create an AB test
        test_response = client.post(
            "/ab-testing/tests/",
            headers=auth_headers,
            json=test_ab_test
        )
        assert test_response.status_code == 201
        test_data = test_response.json()
        test_id = test_data["id"]
        
        # Step 2: Get the test
        get_test_response = client.get(
            f"/ab-testing/tests/{test_id}",
            headers=auth_headers
        )
        assert get_test_response.status_code == 200
        get_test_data = get_test_response.json()
        assert get_test_data["name"] == test_ab_test["name"]
        assert get_test_data["platform"] == test_ab_test["platform"]
        assert len(get_test_data["variants"]) == 2
        
        # Step 3: Update the test
        update_data = {
            "name": "Updated Headline Test",
            "audience_targeting": {
                "age_range": [25, 45],
                "regions": ["US", "CA"]
            }
        }
        update_response = client.patch(
            f"/ab-testing/tests/{test_id}",
            headers=auth_headers,
            json=update_data
        )
        assert update_response.status_code == 200
        update_test_data = update_response.json()
        assert update_test_data["name"] == update_data["name"]
        assert update_test_data["audience_targeting"]["age_range"] == [25, 45]
        
        # Step 4: Start the test
        start_response = client.post(
            f"/ab-testing/tests/{test_id}/start",
            headers=auth_headers
        )
        assert start_response.status_code == 200
        start_data = start_response.json()
        assert start_data["status"] == "RUNNING"
        
        # Step 5: Record variant performance for both variants
        variant_ids = [variant["id"] for variant in get_test_data["variants"]]
        
        # Record for variant A
        performance_a = {
            "impressions": 1000,
            "clicks": 150,
            "engagement": 200,
            "conversions": 50
        }
        record_a_response = client.post(
            f"/ab-testing/variants/{variant_ids[0]}/performance",
            headers=auth_headers,
            json=performance_a
        )
        assert record_a_response.status_code == 200
        
        # Record for variant B
        performance_b = {
            "impressions": 1000,
            "clicks": 180,
            "engagement": 250,
            "conversions": 60
        }
        record_b_response = client.post(
            f"/ab-testing/variants/{variant_ids[1]}/performance",
            headers=auth_headers,
            json=performance_b
        )
        assert record_b_response.status_code == 200
        
        # Step 6: Get test results
        results_response = client.get(
            f"/ab-testing/tests/{test_id}/results",
            headers=auth_headers
        )
        assert results_response.status_code == 200
        results_data = results_response.json()
        assert "variants" in results_data
        assert "winner" in results_data
        assert len(results_data["variants"]) == 2
        
        # Step 7: Stop the test
        stop_response = client.post(
            f"/ab-testing/tests/{test_id}/stop",
            headers=auth_headers
        )
        assert stop_response.status_code == 200
        stop_data = stop_response.json()
        assert stop_data["status"] == "COMPLETED"
        
        # Step 8: Delete the test
        delete_response = client.delete(
            f"/ab-testing/tests/{test_id}",
            headers=auth_headers
        )
        assert delete_response.status_code == 204
        
        # Verify test is deleted
        get_deleted_test_response = client.get(
            f"/ab-testing/tests/{test_id}",
            headers=auth_headers
        )
        assert get_deleted_test_response.status_code == 404
    
    def test_get_user_ab_tests(self, client, auth_headers, test_user_id, test_ab_test):
        """
        Test retrieving all AB tests for a user with various filters
        """
        # First create a test
        test_response = client.post(
            "/ab-testing/tests/",
            headers=auth_headers,
            json=test_ab_test
        )
        assert test_response.status_code == 201
        
        # Get all tests
        all_tests_response = client.get(
            "/ab-testing/tests/",
            headers=auth_headers
        )
        assert all_tests_response.status_code == 200
        all_tests_data = all_tests_response.json()
        assert len(all_tests_data) >= 1
        
        # Get tests with platform filter
        platform_tests_response = client.get(
            "/ab-testing/tests/",
            headers=auth_headers,
            params={"platform": "instagram"}
        )
        assert platform_tests_response.status_code == 200
        platform_tests_data = platform_tests_response.json()
        assert len(platform_tests_data) >= 1
        assert all(test["platform"] == "instagram" for test in platform_tests_data)
        
        # Get tests with status filter
        status_tests_response = client.get(
            "/ab-testing/tests/",
            headers=auth_headers,
            params={"status": "DRAFT"}
        )
        assert status_tests_response.status_code == 200
        status_tests_data = status_tests_response.json()
        assert all(test["status"] == "DRAFT" for test in status_tests_data)
    
    def test_variant_performance_tracking(self, client, auth_headers, test_user_id, test_ab_test):
        """
        Test detailed performance tracking for AB test variants
        """
        # Create a test
        test_response = client.post(
            "/ab-testing/tests/",
            headers=auth_headers,
            json=test_ab_test
        )
        assert test_response.status_code == 201
        test_data = test_response.json()
        test_id = test_data["id"]
        
        # Start the test
        start_response = client.post(
            f"/ab-testing/tests/{test_id}/start",
            headers=auth_headers
        )
        assert start_response.status_code == 200
        
        # Get the variants
        get_test_response = client.get(
            f"/ab-testing/tests/{test_id}",
            headers=auth_headers
        )
        get_test_data = get_test_response.json()
        variant_ids = [variant["id"] for variant in get_test_data["variants"]]
        
        # Record performance data over multiple days
        for day in range(3):
            # Variant A performance
            performance_a = {
                "impressions": 1000 + (day * 100),
                "clicks": 150 + (day * 15),
                "engagement": 200 + (day * 20),
                "conversions": 50 + (day * 5),
                "timestamp": (datetime.utcnow() + timedelta(days=day)).isoformat()
            }
            record_a_response = client.post(
                f"/ab-testing/variants/{variant_ids[0]}/performance",
                headers=auth_headers,
                json=performance_a
            )
            assert record_a_response.status_code == 200
            
            # Variant B performance
            performance_b = {
                "impressions": 1000 + (day * 100),
                "clicks": 180 + (day * 18),
                "engagement": 250 + (day * 25),
                "conversions": 60 + (day * 6),
                "timestamp": (datetime.utcnow() + timedelta(days=day)).isoformat()
            }
            record_b_response = client.post(
                f"/ab-testing/variants/{variant_ids[1]}/performance",
                headers=auth_headers,
                json=performance_b
            )
            assert record_b_response.status_code == 200
        
        # Get time series performance data
        time_series_response = client.get(
            f"/ab-testing/tests/{test_id}/time-series",
            headers=auth_headers
        )
        assert time_series_response.status_code == 200
        time_series_data = time_series_response.json()
        
        assert "dates" in time_series_data
        assert "variants" in time_series_data
        assert len(time_series_data["dates"]) >= 3  # At least 3 days of data
        assert len(time_series_data["variants"]) == 2
        
        # Each variant should have metrics for each date
        for variant in time_series_data["variants"]:
            assert "metrics" in variant
            assert len(variant["metrics"]) >= 3  # At least 3 days of data
    
    def test_ab_test_validation(self, client, auth_headers):
        """
        Test validation of AB test parameters
        """
        # Test with invalid dates (end before start)
        invalid_test = {
            "name": "Invalid Test",
            "platform": "instagram",
            "start_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "end_date": datetime.utcnow().isoformat(),  # End before start
            "variants": [
                {
                    "name": "Variant A",
                    "content_modifications": {"headline": "Test A"}
                },
                {
                    "name": "Variant B",
                    "content_modifications": {"headline": "Test B"}
                }
            ],
            "success_metrics": ["clicks"]
        }
        
        invalid_response = client.post(
            "/ab-testing/tests/",
            headers=auth_headers,
            json=invalid_test
        )
        assert invalid_response.status_code == 422  # Validation error
        
        # Test with insufficient variants (need at least 2)
        invalid_test["start_date"] = datetime.utcnow().isoformat()
        invalid_test["end_date"] = (datetime.utcnow() + timedelta(days=7)).isoformat()
        invalid_test["variants"] = [
            {
                "name": "Variant A",
                "content_modifications": {"headline": "Test A"}
            }
        ]
        
        invalid_response = client.post(
            "/ab-testing/tests/",
            headers=auth_headers,
            json=invalid_test
        )
        assert invalid_response.status_code == 422  # Validation error
        
        # Test with invalid success metrics
        invalid_test["variants"] = [
            {
                "name": "Variant A",
                "content_modifications": {"headline": "Test A"}
            },
            {
                "name": "Variant B",
                "content_modifications": {"headline": "Test B"}
            }
        ]
        invalid_test["success_metrics"] = ["invalid_metric"]
        
        invalid_response = client.post(
            "/ab-testing/tests/",
            headers=auth_headers,
            json=invalid_test
        )
        assert invalid_response.status_code == 422  # Validation error
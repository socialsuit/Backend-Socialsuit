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
def test_post():
    return {
        "platform": "instagram",
        "content": "This is a test post for recycling #test #social",
        "media_urls": ["https://example.com/image.jpg"],
        "scheduled_time": (datetime.utcnow() + timedelta(hours=1)).isoformat()
    }

@pytest.fixture
def test_recycling_rule():
    return {
        "name": "Weekly Top Posts",
        "description": "Recycle top performing posts every week",
        "platform": "instagram",
        "frequency": "weekly",
        "day_of_week": 1,  # Monday
        "time_of_day": "09:00",
        "post_selection_criteria": {
            "min_engagement": 100,
            "max_age_days": 90
        },
        "content_modification": {
            "add_prefix": "[Encore] ",
            "regenerate_hashtags": True
        }
    }

class TestPostRecyclerIntegration:
    def test_complete_recycling_workflow(self, client, auth_headers, test_user_id, test_post, test_recycling_rule):
        """
        Test the complete workflow of the post recycler feature:
        1. Create a post
        2. Create a recycling rule
        3. Get the rule
        4. Update the rule
        5. Get posts eligible for recycling
        6. Manually trigger recycling
        7. Delete the rule
        """
        # Step 1: Create a post (using the scheduled post endpoint)
        post_response = client.post(
            "/scheduled-posts/",
            headers=auth_headers,
            json=test_post
        )
        assert post_response.status_code == 201
        post_data = post_response.json()
        post_id = post_data["id"]
        
        # Step 2: Create a recycling rule
        rule_response = client.post(
            "/post-recycler/rules/",
            headers=auth_headers,
            json=test_recycling_rule
        )
        assert rule_response.status_code == 201
        rule_data = rule_response.json()
        rule_id = rule_data["id"]
        
        # Step 3: Get the rule
        get_rule_response = client.get(
            f"/post-recycler/rules/{rule_id}",
            headers=auth_headers
        )
        assert get_rule_response.status_code == 200
        get_rule_data = get_rule_response.json()
        assert get_rule_data["name"] == test_recycling_rule["name"]
        assert get_rule_data["platform"] == test_recycling_rule["platform"]
        
        # Step 4: Update the rule
        update_data = {
            "name": "Updated Weekly Top Posts",
            "post_selection_criteria": {
                "min_engagement": 200,
                "max_age_days": 60
            }
        }
        update_response = client.patch(
            f"/post-recycler/rules/{rule_id}",
            headers=auth_headers,
            json=update_data
        )
        assert update_response.status_code == 200
        update_rule_data = update_response.json()
        assert update_rule_data["name"] == update_data["name"]
        assert update_rule_data["post_selection_criteria"]["min_engagement"] == 200
        
        # Step 5: Get posts eligible for recycling
        # Note: In a real test, we would need to simulate post engagement
        eligible_posts_response = client.get(
            "/post-recycler/eligible-posts/",
            headers=auth_headers,
            params={
                "platform": "instagram",
                "min_engagement": 0  # Set to 0 for testing purposes
            }
        )
        assert eligible_posts_response.status_code == 200
        
        # Step 6: Manually trigger recycling for a post
        recycle_response = client.post(
            f"/post-recycler/recycle/{post_id}",
            headers=auth_headers,
            json={
                "rule_id": rule_id
            }
        )
        assert recycle_response.status_code in [200, 201]
        
        # Step 7: Delete the rule
        delete_response = client.delete(
            f"/post-recycler/rules/{rule_id}",
            headers=auth_headers
        )
        assert delete_response.status_code == 204
        
        # Verify rule is deleted
        get_deleted_rule_response = client.get(
            f"/post-recycler/rules/{rule_id}",
            headers=auth_headers
        )
        assert get_deleted_rule_response.status_code == 404
    
    def test_get_user_recycling_rules(self, client, auth_headers, test_user_id, test_recycling_rule):
        """
        Test retrieving all recycling rules for a user with various filters
        """
        # First create a rule
        rule_response = client.post(
            "/post-recycler/rules/",
            headers=auth_headers,
            json=test_recycling_rule
        )
        assert rule_response.status_code == 201
        
        # Get all rules
        all_rules_response = client.get(
            "/post-recycler/rules/",
            headers=auth_headers
        )
        assert all_rules_response.status_code == 200
        all_rules_data = all_rules_response.json()
        assert len(all_rules_data) >= 1
        
        # Get rules with platform filter
        platform_rules_response = client.get(
            "/post-recycler/rules/",
            headers=auth_headers,
            params={"platform": "instagram"}
        )
        assert platform_rules_response.status_code == 200
        platform_rules_data = platform_rules_response.json()
        assert len(platform_rules_data) >= 1
        assert all(rule["platform"] == "instagram" for rule in platform_rules_data)
        
        # Get rules with status filter
        status_rules_response = client.get(
            "/post-recycler/rules/",
            headers=auth_headers,
            params={"status": "ACTIVE"}
        )
        assert status_rules_response.status_code == 200
        status_rules_data = status_rules_response.json()
        assert all(rule["status"] == "ACTIVE" for rule in status_rules_data)
    
    def test_process_due_recycling_rules(self, client, auth_headers):
        """
        Test the system endpoint that processes due recycling rules
        """
        # This endpoint would typically be called by a scheduler
        process_response = client.post(
            "/post-recycler/process-due-rules/",
            headers=auth_headers
        )
        assert process_response.status_code == 200
        process_data = process_response.json()
        assert "processed_count" in process_data
    
    def test_rule_validation(self, client, auth_headers):
        """
        Test validation of recycling rule parameters
        """
        # Test with invalid frequency
        invalid_rule = {
            "name": "Invalid Rule",
            "platform": "instagram",
            "frequency": "invalid_frequency",  # Invalid value
            "day_of_week": 1,
            "time_of_day": "09:00",
            "post_selection_criteria": {"min_engagement": 100},
            "content_modification": {"add_prefix": "[Encore] "}
        }
        
        invalid_response = client.post(
            "/post-recycler/rules/",
            headers=auth_headers,
            json=invalid_rule
        )
        assert invalid_response.status_code == 422  # Validation error
        
        # Test with invalid day_of_week
        invalid_rule["frequency"] = "weekly"
        invalid_rule["day_of_week"] = 8  # Invalid value (should be 0-6)
        
        invalid_response = client.post(
            "/post-recycler/rules/",
            headers=auth_headers,
            json=invalid_rule
        )
        assert invalid_response.status_code == 422  # Validation error
        
        # Test with invalid time format
        invalid_rule["day_of_week"] = 1
        invalid_rule["time_of_day"] = "25:00"  # Invalid time
        
        invalid_response = client.post(
            "/post-recycler/rules/",
            headers=auth_headers,
            json=invalid_rule
        )
        assert invalid_response.status_code == 422  # Validation error
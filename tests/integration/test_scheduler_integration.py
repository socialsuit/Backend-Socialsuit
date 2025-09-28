import pytest
from httpx import AsyncClient
from fastapi import status
from datetime import datetime, timedelta
import json

@pytest.mark.asyncio
async def test_scheduled_post_lifecycle(async_client: AsyncClient):
    """Test the complete lifecycle of a scheduled post from creation to publishing"""
    # Login to get authentication token
    login_data = {
        "email": "test_integration@example.com",
        "password": "securePassword123!"
    }
    
    login_response = await async_client.post("/auth/login", json=login_data)
    assert login_response.status_code == status.HTTP_200_OK
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create a scheduled post
    scheduled_time = (datetime.utcnow() + timedelta(minutes=5)).isoformat()
    post_data = {
        "content": "This is an integration test scheduled post",
        "platform": "twitter",
        "scheduled_time": scheduled_time,
        "media_urls": [],
        "metadata": {"test": True}
    }
    
    create_response = await async_client.post("/scheduled-posts/", json=post_data, headers=headers)
    assert create_response.status_code == status.HTTP_200_OK
    post_id = create_response.json()["post_id"]
    
    # Retrieve the created post
    get_response = await async_client.get(f"/scheduled-posts/{post_id}", headers=headers)
    assert get_response.status_code == status.HTTP_200_OK
    assert get_response.json()["content"] == "This is an integration test scheduled post"
    assert get_response.json()["platform"] == "twitter"
    
    # Update the scheduled post
    update_data = {
        "content": "Updated integration test scheduled post",
        "scheduled_time": (datetime.utcnow() + timedelta(minutes=10)).isoformat()
    }
    
    update_response = await async_client.put(f"/scheduled-posts/{post_id}", json=update_data, headers=headers)
    assert update_response.status_code == status.HTTP_200_OK
    
    # Verify the update
    get_updated_response = await async_client.get(f"/scheduled-posts/{post_id}", headers=headers)
    assert get_updated_response.status_code == status.HTTP_200_OK
    assert get_updated_response.json()["content"] == "Updated integration test scheduled post"
    
    # Publish the post immediately
    publish_response = await async_client.post(f"/scheduled-posts/{post_id}/publish", headers=headers)
    assert publish_response.status_code == status.HTTP_200_OK
    
    # Verify the post status changed
    get_published_response = await async_client.get(f"/scheduled-posts/{post_id}", headers=headers)
    assert get_published_response.status_code == status.HTTP_200_OK
    assert get_published_response.json()["status"] in ["PUBLISHING", "PUBLISHED"]
    
    # Delete the post
    delete_response = await async_client.delete(f"/scheduled-posts/{post_id}", headers=headers)
    assert delete_response.status_code == status.HTTP_200_OK
    
    # Verify the post is deleted
    get_deleted_response = await async_client.get(f"/scheduled-posts/{post_id}", headers=headers)
    assert get_deleted_response.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.asyncio
async def test_scheduled_post_filtering(async_client: AsyncClient):
    """Test filtering scheduled posts by various criteria"""
    # Login to get authentication token
    login_data = {
        "email": "test_integration@example.com",
        "password": "securePassword123!"
    }
    
    login_response = await async_client.post("/auth/login", json=login_data)
    assert login_response.status_code == status.HTTP_200_OK
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create multiple scheduled posts for different platforms
    platforms = ["twitter", "facebook", "instagram"]
    post_ids = []
    
    for platform in platforms:
        scheduled_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        post_data = {
            "content": f"Test post for {platform}",
            "platform": platform,
            "scheduled_time": scheduled_time
        }
        
        create_response = await async_client.post("/scheduled-posts/", json=post_data, headers=headers)
        assert create_response.status_code == status.HTTP_200_OK
        post_ids.append(create_response.json()["post_id"])
    
    # Test filtering by platform
    for platform in platforms:
        filter_response = await async_client.get(
            f"/scheduled-posts/?platform={platform}", 
            headers=headers
        )
        assert filter_response.status_code == status.HTTP_200_OK
        posts = filter_response.json()
        assert len(posts) >= 1
        for post in posts:
            assert post["platform"] == platform
    
    # Test filtering by status
    status_response = await async_client.get(
        "/scheduled-posts/?status=PENDING", 
        headers=headers
    )
    assert status_response.status_code == status.HTTP_200_OK
    status_posts = status_response.json()
    assert len(status_posts) >= len(platforms)
    
    # Test filtering by date range
    from_date = (datetime.utcnow() - timedelta(days=1)).isoformat()
    to_date = (datetime.utcnow() + timedelta(days=2)).isoformat()
    
    date_response = await async_client.get(
        f"/scheduled-posts/?from_date={from_date}&to_date={to_date}", 
        headers=headers
    )
    assert date_response.status_code == status.HTTP_200_OK
    date_posts = date_response.json()
    assert len(date_posts) >= len(platforms)
    
    # Clean up created posts
    for post_id in post_ids:
        await async_client.delete(f"/scheduled-posts/{post_id}", headers=headers)

@pytest.mark.asyncio
async def test_pending_posts_processing(async_client: AsyncClient):
    """Test the system endpoint for processing pending posts"""
    # This would typically be an admin/system endpoint
    response = await async_client.get("/scheduled-posts/pending/next")
    assert response.status_code == status.HTTP_200_OK
    assert "published_count" in response.json()
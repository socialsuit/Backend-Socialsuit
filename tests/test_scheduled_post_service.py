import pytest
from unittest.mock import MagicMock, patch
import uuid
from datetime import datetime, timedelta

from app.services.scheduled_post_service import ScheduledPostService
from app.services.repositories.scheduled_post_repository import ScheduledPostRepository
from app.services.repositories.user_repository import UserRepository
from app.services.models.scheduled_post_model import ScheduledPost, PostStatus
from app.services.models.user_model import User

# Fixtures
@pytest.fixture
def scheduled_post_repository():
    return MagicMock(spec=ScheduledPostRepository)

@pytest.fixture
def user_repository():
    return MagicMock(spec=UserRepository)

@pytest.fixture
def scheduled_post_service(scheduled_post_repository, user_repository):
    return ScheduledPostService(
        scheduled_post_repository=scheduled_post_repository,
        user_repository=user_repository
    )

@pytest.fixture
def sample_user():
    return User(
        id=str(uuid.uuid4()),
        email="test@example.com",
        username="testuser",
        is_verified=True
    )

@pytest.fixture
def sample_post(sample_user):
    return ScheduledPost(
        id=1,
        user_id=sample_user.id,
        platform="twitter",
        post_payload={"text": "Test post content"},
        scheduled_time=datetime.utcnow() + timedelta(days=1),
        status=PostStatus.PENDING,
        retries=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

@pytest.fixture
def sample_posts(sample_user):
    now = datetime.utcnow()
    return [
        ScheduledPost(
            id=1,
            user_id=sample_user.id,
            platform="twitter",
            post_payload={"text": "Twitter post"},
            scheduled_time=now + timedelta(days=1),
            status=PostStatus.PENDING,
            retries=0,
            created_at=now,
            updated_at=now
        ),
        ScheduledPost(
            id=2,
            user_id=sample_user.id,
            platform="facebook",
            post_payload={"text": "Facebook post"},
            scheduled_time=now + timedelta(days=2),
            status=PostStatus.PENDING,
            retries=0,
            created_at=now,
            updated_at=now
        ),
        ScheduledPost(
            id=3,
            user_id=sample_user.id,
            platform="instagram",
            post_payload={"text": "Instagram post", "image_url": "http://example.com/image.jpg"},
            scheduled_time=now - timedelta(days=1),  # Past post
            status=PostStatus.PUBLISHED,
            retries=0,
            created_at=now - timedelta(days=2),
            updated_at=now - timedelta(days=1)
        )
    ]

# Test cases
def test_create_scheduled_post(scheduled_post_service, sample_user, sample_post):
    # Setup
    user_id = sample_user.id
    platform = "twitter"
    post_payload = {"text": "Test post content"}
    scheduled_time = datetime.utcnow() + timedelta(days=1)
    
    scheduled_post_service.user_repository.get_by_id.return_value = sample_user
    scheduled_post_service.scheduled_post_repository.create.return_value = sample_post
    
    # Execute
    result = scheduled_post_service.create_scheduled_post(
        user_id=user_id,
        platform=platform,
        post_payload=post_payload,
        scheduled_time=scheduled_time
    )
    
    # Assert
    assert result == sample_post
    scheduled_post_service.user_repository.get_by_id.assert_called_once_with(user_id)
    scheduled_post_service.scheduled_post_repository.create.assert_called_once()

def test_get_scheduled_post(scheduled_post_service, sample_post):
    # Setup
    post_id = sample_post.id
    scheduled_post_service.scheduled_post_repository.get_by_id.return_value = sample_post
    
    # Execute
    result = scheduled_post_service.get_scheduled_post(post_id)
    
    # Assert
    assert result == sample_post
    scheduled_post_service.scheduled_post_repository.get_by_id.assert_called_once_with(post_id)

def test_get_user_scheduled_posts(scheduled_post_service, sample_user, sample_posts):
    # Setup
    user_id = sample_user.id
    scheduled_post_service.scheduled_post_repository.get_posts_by_user_id.return_value = sample_posts
    
    # Execute
    result = scheduled_post_service.get_user_scheduled_posts(user_id)
    
    # Assert
    assert result == sample_posts
    scheduled_post_service.scheduled_post_repository.get_posts_by_user_id.assert_called_once_with(
        user_id, platform=None, status=None, start_date=None, end_date=None
    )

def test_get_user_scheduled_posts_with_filters(scheduled_post_service, sample_user, sample_posts):
    # Setup
    user_id = sample_user.id
    platform = "twitter"
    status = PostStatus.PENDING.value
    start_date = datetime.utcnow() - timedelta(days=7)
    end_date = datetime.utcnow() + timedelta(days=7)
    
    filtered_posts = [p for p in sample_posts if p.platform == platform and p.status == status]
    scheduled_post_service.scheduled_post_repository.get_posts_by_user_id.return_value = filtered_posts
    
    # Execute
    result = scheduled_post_service.get_user_scheduled_posts(
        user_id, platform=platform, status=status, start_date=start_date, end_date=end_date
    )
    
    # Assert
    assert result == filtered_posts
    scheduled_post_service.scheduled_post_repository.get_posts_by_user_id.assert_called_once_with(
        user_id, platform=platform, status=status, start_date=start_date, end_date=end_date
    )

def test_update_scheduled_post(scheduled_post_service, sample_post):
    # Setup
    post_id = sample_post.id
    updated_payload = {"text": "Updated content"}
    updated_time = datetime.utcnow() + timedelta(days=2)
    
    scheduled_post_service.scheduled_post_repository.get_by_id.return_value = sample_post
    scheduled_post_service.scheduled_post_repository.update.return_value = sample_post
    
    # Execute
    result = scheduled_post_service.update_scheduled_post(
        post_id=post_id,
        post_payload=updated_payload,
        scheduled_time=updated_time
    )
    
    # Assert
    assert result == sample_post
    assert result.post_payload == updated_payload
    assert result.scheduled_time == updated_time
    scheduled_post_service.scheduled_post_repository.get_by_id.assert_called_once_with(post_id)
    scheduled_post_service.scheduled_post_repository.update.assert_called_once_with(sample_post)

def test_delete_scheduled_post(scheduled_post_service, sample_post):
    # Setup
    post_id = sample_post.id
    scheduled_post_service.scheduled_post_repository.get_by_id.return_value = sample_post
    scheduled_post_service.scheduled_post_repository.delete.return_value = None
    
    # Execute
    result = scheduled_post_service.delete_scheduled_post(post_id)
    
    # Assert
    assert result is True
    scheduled_post_service.scheduled_post_repository.get_by_id.assert_called_once_with(post_id)
    scheduled_post_service.scheduled_post_repository.delete.assert_called_once_with(sample_post)

def test_publish_post(scheduled_post_service, sample_post):
    # Setup
    post_id = sample_post.id
    scheduled_post_service.scheduled_post_repository.get_by_id.return_value = sample_post
    scheduled_post_service.scheduled_post_repository.update_post_status.return_value = sample_post
    
    # Mock the platform-specific publishing function
    with patch.object(scheduled_post_service, '_publish_to_twitter', return_value=True) as mock_publish:
        # Execute
        result = scheduled_post_service.publish_post(post_id)
        
        # Assert
        assert result is True
        scheduled_post_service.scheduled_post_repository.get_by_id.assert_called_once_with(post_id)
        mock_publish.assert_called_once_with(sample_post)
        scheduled_post_service.scheduled_post_repository.update_post_status.assert_called_once_with(
            post_id, PostStatus.PUBLISHED.value
        )

def test_publish_post_failure(scheduled_post_service, sample_post):
    # Setup
    post_id = sample_post.id
    scheduled_post_service.scheduled_post_repository.get_by_id.return_value = sample_post
    scheduled_post_service.scheduled_post_repository.update_post_status.return_value = sample_post
    
    # Mock the platform-specific publishing function to fail
    with patch.object(scheduled_post_service, '_publish_to_twitter', return_value=False) as mock_publish:
        # Execute
        result = scheduled_post_service.publish_post(post_id)
        
        # Assert
        assert result is False
        scheduled_post_service.scheduled_post_repository.get_by_id.assert_called_once_with(post_id)
        mock_publish.assert_called_once_with(sample_post)
        scheduled_post_service.scheduled_post_repository.update_post_status.assert_called_once_with(
            post_id, PostStatus.FAILED.value
        )

def test_process_pending_posts(scheduled_post_service, sample_posts):
    # Setup
    now = datetime.utcnow()
    pending_posts = [p for p in sample_posts if p.status == PostStatus.PENDING and p.scheduled_time <= now]
    
    scheduled_post_service.scheduled_post_repository.get_pending_posts.return_value = pending_posts
    scheduled_post_service.publish_post = MagicMock(return_value=True)
    
    # Execute
    result = scheduled_post_service.process_pending_posts()
    
    # Assert
    assert result == len(pending_posts)
    scheduled_post_service.scheduled_post_repository.get_pending_posts.assert_called_once_with(now, limit=None)
    assert scheduled_post_service.publish_post.call_count == len(pending_posts)

def test_cancel_scheduled_post(scheduled_post_service, sample_post):
    # Setup
    post_id = sample_post.id
    scheduled_post_service.scheduled_post_repository.get_by_id.return_value = sample_post
    scheduled_post_service.scheduled_post_repository.update_post_status.return_value = sample_post
    
    # Execute
    result = scheduled_post_service.cancel_scheduled_post(post_id)
    
    # Assert
    assert result is True
    scheduled_post_service.scheduled_post_repository.get_by_id.assert_called_once_with(post_id)
    scheduled_post_service.scheduled_post_repository.update_post_status.assert_called_once_with(
        post_id, PostStatus.CANCELLED.value
    )
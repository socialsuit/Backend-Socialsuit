import pytest
from unittest.mock import MagicMock, patch
import uuid
from datetime import datetime, timedelta

from app.services.models.scheduled_post_model import ScheduledPost, PostStatus
from app.services.repositories.scheduled_post_repository import ScheduledPostRepository
from tests.utils import mock_db_session, scheduled_post_repository

# Sample test data
@pytest.fixture
def sample_post():
    return ScheduledPost(
        id=1,
        user_id=str(uuid.uuid4()),
        platform="twitter",
        post_payload={"text": "Test post content"},
        scheduled_time=datetime.utcnow() + timedelta(days=1),
        status=PostStatus.PENDING,
        retries=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

@pytest.fixture
def sample_posts():
    user_id = str(uuid.uuid4())
    now = datetime.utcnow()
    return [
        ScheduledPost(
            id=1,
            user_id=user_id,
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
            user_id=user_id,
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
            user_id=user_id,
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
def test_get_by_id(scheduled_post_repository, sample_post):
    # Setup
    post_id = sample_post.id
    scheduled_post_repository.db.query().filter().first.return_value = sample_post
    
    # Execute
    result = scheduled_post_repository.get_by_id(post_id)
    
    # Assert
    assert result == sample_post
    scheduled_post_repository.db.query.assert_called_once_with(ScheduledPost)

def test_get_posts_by_user_id(scheduled_post_repository, sample_posts):
    # Setup
    user_id = sample_posts[0].user_id
    scheduled_post_repository.db.query().filter().all.return_value = sample_posts
    
    # Execute
    result = scheduled_post_repository.get_posts_by_user_id(user_id)
    
    # Assert
    assert result == sample_posts
    scheduled_post_repository.db.query.assert_called_once_with(ScheduledPost)

def test_get_posts_by_user_id_with_platform_filter(scheduled_post_repository, sample_posts):
    # Setup
    user_id = sample_posts[0].user_id
    platform = "twitter"
    filtered_posts = [post for post in sample_posts if post.platform == platform]
    scheduled_post_repository.db.query().filter().filter().all.return_value = filtered_posts
    
    # Execute
    result = scheduled_post_repository.get_posts_by_user_id(user_id, platform=platform)
    
    # Assert
    assert result == filtered_posts
    scheduled_post_repository.db.query.assert_called_once_with(ScheduledPost)

def test_get_posts_by_user_id_with_status_filter(scheduled_post_repository, sample_posts):
    # Setup
    user_id = sample_posts[0].user_id
    status = PostStatus.PENDING.value
    filtered_posts = [post for post in sample_posts if post.status == status]
    scheduled_post_repository.db.query().filter().filter().all.return_value = filtered_posts
    
    # Execute
    result = scheduled_post_repository.get_posts_by_user_id(user_id, status=status)
    
    # Assert
    assert result == filtered_posts
    scheduled_post_repository.db.query.assert_called_once_with(ScheduledPost)

def test_get_posts_by_user_id_with_date_filters(scheduled_post_repository, sample_posts):
    # Setup
    user_id = sample_posts[0].user_id
    start_date = datetime.utcnow() - timedelta(days=3)
    end_date = datetime.utcnow() + timedelta(days=3)
    scheduled_post_repository.db.query().filter().filter().filter().all.return_value = sample_posts
    
    # Execute
    result = scheduled_post_repository.get_posts_by_user_id(
        user_id, start_date=start_date, end_date=end_date
    )
    
    # Assert
    assert result == sample_posts
    scheduled_post_repository.db.query.assert_called_once_with(ScheduledPost)

def test_get_pending_posts(scheduled_post_repository, sample_posts):
    # Setup
    now = datetime.utcnow()
    pending_posts = [post for post in sample_posts if post.status == PostStatus.PENDING and post.scheduled_time <= now]
    scheduled_post_repository.db.query().filter().filter().order_by().limit().all.return_value = pending_posts
    
    # Execute
    result = scheduled_post_repository.get_pending_posts(now, limit=10)
    
    # Assert
    assert result == pending_posts
    scheduled_post_repository.db.query.assert_called_once_with(ScheduledPost)

def test_get_posts_by_platform(scheduled_post_repository, sample_posts):
    # Setup
    platform = "twitter"
    filtered_posts = [post for post in sample_posts if post.platform == platform]
    scheduled_post_repository.db.query().filter().all.return_value = filtered_posts
    
    # Execute
    result = scheduled_post_repository.get_posts_by_platform(platform)
    
    # Assert
    assert result == filtered_posts
    scheduled_post_repository.db.query.assert_called_once_with(ScheduledPost)

def test_update_post_status(scheduled_post_repository, sample_post):
    # Setup
    post_id = sample_post.id
    new_status = PostStatus.PUBLISHED.value
    scheduled_post_repository.get_by_id = MagicMock(return_value=sample_post)
    scheduled_post_repository.update = MagicMock(return_value=sample_post)
    
    # Execute
    result = scheduled_post_repository.update_post_status(post_id, new_status)
    
    # Assert
    assert result == sample_post
    assert result.status == new_status
    scheduled_post_repository.get_by_id.assert_called_once_with(post_id)
    scheduled_post_repository.update.assert_called_once_with(sample_post)

def test_create_post(scheduled_post_repository, sample_post):
    # Setup
    scheduled_post_repository.db.add = MagicMock()
    scheduled_post_repository.db.commit = MagicMock()
    scheduled_post_repository.db.refresh = MagicMock()
    
    # Execute
    result = scheduled_post_repository.create(sample_post)
    
    # Assert
    assert result == sample_post
    scheduled_post_repository.db.add.assert_called_once_with(sample_post)
    scheduled_post_repository.db.commit.assert_called_once()
    scheduled_post_repository.db.refresh.assert_called_once_with(sample_post)

def test_update_post(scheduled_post_repository, sample_post):
    # Setup
    scheduled_post_repository.db.add = MagicMock()
    scheduled_post_repository.db.commit = MagicMock()
    scheduled_post_repository.db.refresh = MagicMock()
    
    # Execute
    result = scheduled_post_repository.update(sample_post)
    
    # Assert
    assert result == sample_post
    scheduled_post_repository.db.add.assert_called_once_with(sample_post)
    scheduled_post_repository.db.commit.assert_called_once()
    scheduled_post_repository.db.refresh.assert_called_once_with(sample_post)

def test_delete_post(scheduled_post_repository, sample_post):
    # Setup
    scheduled_post_repository.db.delete = MagicMock()
    scheduled_post_repository.db.commit = MagicMock()
    
    # Execute
    scheduled_post_repository.delete(sample_post)
    
    # Assert
    scheduled_post_repository.db.delete.assert_called_once_with(sample_post)
    scheduled_post_repository.db.commit.assert_called_once()
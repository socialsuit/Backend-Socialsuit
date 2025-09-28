import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import json

from services.scheduled_post_service import ScheduledPostService
from services.models.scheduled_post_model import ScheduledPost, PostStatus
from services.models.user_model import User

@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = "test-user-id"
    user.email = "test@example.com"
    return user

@pytest.fixture
def mock_scheduled_post():
    post = MagicMock(spec=ScheduledPost)
    post.id = 1
    post.user_id = "test-user-id"
    post.platform = "twitter"
    post.post_payload = {
        "content": "Test scheduled post",
        "media_urls": [],
        "metadata": {}
    }
    post.scheduled_time = datetime.utcnow() + timedelta(hours=1)
    post.status = PostStatus.PENDING
    post.created_at = datetime.utcnow()
    post.updated_at = datetime.utcnow()
    return post

@pytest.fixture
def mock_scheduled_post_repository():
    repo = MagicMock()
    repo.create.return_value = None
    repo.get_by_id.return_value = None
    repo.get_posts_by_user_id.return_value = []
    repo.get_pending_posts.return_value = []
    repo.update.return_value = None
    repo.delete.return_value = None
    repo.update_post_status.return_value = True
    return repo

@pytest.fixture
def mock_user_repository():
    repo = MagicMock()
    repo.get_by_id.return_value = None
    return repo

@pytest.fixture
def scheduled_post_service(mock_scheduled_post_repository, mock_user_repository):
    return ScheduledPostService(
        scheduled_post_repository=mock_scheduled_post_repository,
        user_repository=mock_user_repository
    )

class TestScheduledPostService:
    def test_create_scheduled_post(self, scheduled_post_service, mock_scheduled_post_repository, mock_scheduled_post):
        # Setup
        mock_scheduled_post_repository.create.return_value = mock_scheduled_post
        
        # Execute
        post_payload = {
            "content": "Test scheduled post",
            "media_urls": [],
            "metadata": {}
        }
        result = scheduled_post_service.create_scheduled_post(
            user_id="test-user-id",
            platform="twitter",
            post_payload=post_payload,
            scheduled_time=datetime.utcnow() + timedelta(hours=1)
        )
        
        # Assert
        assert result == mock_scheduled_post
        mock_scheduled_post_repository.create.assert_called_once()
    
    def test_get_scheduled_post(self, scheduled_post_service, mock_scheduled_post_repository, mock_scheduled_post):
        # Setup
        mock_scheduled_post_repository.get_by_id.return_value = mock_scheduled_post
        
        # Execute
        result = scheduled_post_service.get_scheduled_post(1)
        
        # Assert
        assert result == mock_scheduled_post
        mock_scheduled_post_repository.get_by_id.assert_called_once_with(1)
    
    def test_get_scheduled_post_not_found(self, scheduled_post_service, mock_scheduled_post_repository):
        # Setup
        mock_scheduled_post_repository.get_by_id.return_value = None
        
        # Execute
        result = scheduled_post_service.get_scheduled_post(999)
        
        # Assert
        assert result is None
        mock_scheduled_post_repository.get_by_id.assert_called_once_with(999)
    
    def test_get_user_scheduled_posts(self, scheduled_post_service, mock_scheduled_post_repository, mock_scheduled_post):
        # Setup
        mock_scheduled_post_repository.get_posts_by_user_id.return_value = [mock_scheduled_post]
        
        # Execute
        result = scheduled_post_service.get_user_scheduled_posts("test-user-id")
        
        # Assert
        assert len(result) == 1
        assert result[0] == mock_scheduled_post
        mock_scheduled_post_repository.get_posts_by_user_id.assert_called_once_with(
            user_id="test-user-id",
            platform=None,
            status=None,
            start_date=None,
            end_date=None
        )
    
    def test_get_user_scheduled_posts_with_filters(self, scheduled_post_service, mock_scheduled_post_repository):
        # Setup
        mock_scheduled_post_repository.get_posts_by_user_id.return_value = []
        
        # Execute
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow() + timedelta(days=7)
        result = scheduled_post_service.get_user_scheduled_posts(
            user_id="test-user-id",
            platform="twitter",
            status="PENDING",
            start_date=start_date,
            end_date=end_date
        )
        
        # Assert
        assert len(result) == 0
        mock_scheduled_post_repository.get_posts_by_user_id.assert_called_once_with(
            user_id="test-user-id",
            platform="twitter",
            status="PENDING",
            start_date=start_date,
            end_date=end_date
        )
    
    def test_update_scheduled_post(self, scheduled_post_service, mock_scheduled_post_repository, mock_scheduled_post):
        # Setup
        mock_scheduled_post_repository.get_by_id.return_value = mock_scheduled_post
        mock_scheduled_post_repository.update.return_value = mock_scheduled_post
        
        # Execute
        new_payload = {
            "content": "Updated test post",
            "media_urls": ["http://example.com/image.jpg"],
            "metadata": {"updated": True}
        }
        new_time = datetime.utcnow() + timedelta(days=1)
        result = scheduled_post_service.update_scheduled_post(
            post_id=1,
            post_payload=new_payload,
            scheduled_time=new_time
        )
        
        # Assert
        assert result == mock_scheduled_post
        mock_scheduled_post_repository.get_by_id.assert_called_once_with(1)
        mock_scheduled_post_repository.update.assert_called_once()
    
    def test_update_scheduled_post_not_found(self, scheduled_post_service, mock_scheduled_post_repository):
        # Setup
        mock_scheduled_post_repository.get_by_id.return_value = None
        
        # Execute
        result = scheduled_post_service.update_scheduled_post(
            post_id=999,
            post_payload={"content": "Updated content"},
            scheduled_time=None
        )
        
        # Assert
        assert result is None
        mock_scheduled_post_repository.get_by_id.assert_called_once_with(999)
        mock_scheduled_post_repository.update.assert_not_called()
    
    def test_delete_scheduled_post(self, scheduled_post_service, mock_scheduled_post_repository, mock_scheduled_post):
        # Setup
        mock_scheduled_post_repository.get_by_id.return_value = mock_scheduled_post
        
        # Execute
        result = scheduled_post_service.delete_scheduled_post(1)
        
        # Assert
        assert result is True
        mock_scheduled_post_repository.get_by_id.assert_called_once_with(1)
        mock_scheduled_post_repository.delete.assert_called_once_with(mock_scheduled_post)
    
    def test_delete_scheduled_post_not_found(self, scheduled_post_service, mock_scheduled_post_repository):
        # Setup
        mock_scheduled_post_repository.get_by_id.return_value = None
        
        # Execute
        result = scheduled_post_service.delete_scheduled_post(999)
        
        # Assert
        assert result is False
        mock_scheduled_post_repository.get_by_id.assert_called_once_with(999)
        mock_scheduled_post_repository.delete.assert_not_called()
    
    @patch('services.scheduled_post_service.ScheduledPostService._publish_to_twitter')
    def test_publish_post_twitter(self, mock_publish_to_twitter, scheduled_post_service, mock_scheduled_post_repository, mock_scheduled_post):
        # Setup
        mock_scheduled_post.platform = "twitter"
        mock_scheduled_post_repository.get_by_id.return_value = mock_scheduled_post
        mock_publish_to_twitter.return_value = True
        
        # Execute
        result = scheduled_post_service.publish_post(1)
        
        # Assert
        assert result is True
        mock_scheduled_post_repository.get_by_id.assert_called_once_with(1)
        mock_publish_to_twitter.assert_called_once_with(mock_scheduled_post)
        mock_scheduled_post_repository.update_post_status.assert_called_once_with(
            post_id=1, 
            status=PostStatus.PUBLISHED
        )
    
    @patch('services.scheduled_post_service.ScheduledPostService._publish_to_facebook')
    def test_publish_post_facebook(self, mock_publish_to_facebook, scheduled_post_service, mock_scheduled_post_repository, mock_scheduled_post):
        # Setup
        mock_scheduled_post.platform = "facebook"
        mock_scheduled_post_repository.get_by_id.return_value = mock_scheduled_post
        mock_publish_to_facebook.return_value = True
        
        # Execute
        result = scheduled_post_service.publish_post(1)
        
        # Assert
        assert result is True
        mock_scheduled_post_repository.get_by_id.assert_called_once_with(1)
        mock_publish_to_facebook.assert_called_once_with(mock_scheduled_post)
        mock_scheduled_post_repository.update_post_status.assert_called_once_with(
            post_id=1, 
            status=PostStatus.PUBLISHED
        )
    
    def test_publish_post_not_found(self, scheduled_post_service, mock_scheduled_post_repository):
        # Setup
        mock_scheduled_post_repository.get_by_id.return_value = None
        
        # Execute
        result = scheduled_post_service.publish_post(999)
        
        # Assert
        assert result is False
        mock_scheduled_post_repository.get_by_id.assert_called_once_with(999)
        mock_scheduled_post_repository.update_post_status.assert_not_called()
    
    def test_publish_post_failure(self, scheduled_post_service, mock_scheduled_post_repository, mock_scheduled_post):
        # Setup - mock an unsupported platform
        mock_scheduled_post.platform = "unsupported_platform"
        mock_scheduled_post_repository.get_by_id.return_value = mock_scheduled_post
        
        # Execute
        result = scheduled_post_service.publish_post(1)
        
        # Assert
        assert result is False
        mock_scheduled_post_repository.get_by_id.assert_called_once_with(1)
        mock_scheduled_post_repository.update_post_status.assert_called_once_with(
            post_id=1, 
            status=PostStatus.FAILED
        )
    
    def test_process_pending_posts(self, scheduled_post_service, mock_scheduled_post_repository, mock_scheduled_post):
        # Setup
        mock_scheduled_post_repository.get_pending_posts.return_value = [mock_scheduled_post]
        
        # Mock the publish_post method to return True
        scheduled_post_service.publish_post = MagicMock(return_value=True)
        
        # Execute
        result = scheduled_post_service.process_pending_posts(limit=10)
        
        # Assert
        assert result == 1  # One post processed successfully
        mock_scheduled_post_repository.get_pending_posts.assert_called_once_with(
            datetime.utcnow(), 10
        )
        scheduled_post_service.publish_post.assert_called_once_with(mock_scheduled_post.id)
    
    def test_process_pending_posts_no_posts(self, scheduled_post_service, mock_scheduled_post_repository):
        # Setup
        mock_scheduled_post_repository.get_pending_posts.return_value = []
        
        # Execute
        result = scheduled_post_service.process_pending_posts()
        
        # Assert
        assert result == 0  # No posts processed
        mock_scheduled_post_repository.get_pending_posts.assert_called_once()
    
    def test_update_post_status(self, scheduled_post_service, mock_scheduled_post_repository):
        # Setup
        mock_scheduled_post_repository.update_post_status.return_value = True
        
        # Execute
        result = scheduled_post_service.update_post_status(1, PostStatus.CANCELLED)
        
        # Assert
        assert result is True
        mock_scheduled_post_repository.update_post_status.assert_called_once_with(
            post_id=1, 
            status=PostStatus.CANCELLED
        )
    
    def test_cancel_scheduled_post(self, scheduled_post_service, mock_scheduled_post_repository, mock_scheduled_post):
        # Setup
        mock_scheduled_post_repository.get_by_id.return_value = mock_scheduled_post
        mock_scheduled_post_repository.update_post_status.return_value = True
        
        # Execute
        result = scheduled_post_service.cancel_scheduled_post(1)
        
        # Assert
        assert result is True
        mock_scheduled_post_repository.get_by_id.assert_called_once_with(1)
        mock_scheduled_post_repository.update_post_status.assert_called_once_with(
            post_id=1, 
            status=PostStatus.CANCELLED
        )
    
    def test_cancel_scheduled_post_not_found(self, scheduled_post_service, mock_scheduled_post_repository):
        # Setup
        mock_scheduled_post_repository.get_by_id.return_value = None
        
        # Execute
        result = scheduled_post_service.cancel_scheduled_post(999)
        
        # Assert
        assert result is False
        mock_scheduled_post_repository.get_by_id.assert_called_once_with(999)
        mock_scheduled_post_repository.update_post_status.assert_not_called()
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import json

# Import the post recycler service and related models
# Note: Adjust imports based on actual project structure
from app.services.post_recycler import create_recycling_rule, get_rule, get_user_rules, update_rule, delete_rule, get_posts_for_recycling, recycle_post
from app.services.models.post_recycler_model import RecyclingRule, RecyclingStatus
from app.services.models.user_model import User

@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = "test-user-id"
    user.email = "test@example.com"
    return user

@pytest.fixture
def mock_recycling_rule():
    rule = MagicMock(spec=RecyclingRule)
    rule.id = "rule-1"
    rule.user_id = "test-user-id"
    rule.name = "Weekly Recycling"
    rule.description = "Recycle top performing posts weekly"
    rule.platform = "instagram"
    rule.frequency = "weekly"
    rule.day_of_week = 1  # Monday
    rule.time_of_day = "09:00"
    rule.post_selection_criteria = {"min_engagement": 100, "max_age_days": 90}
    rule.content_modification = {"add_prefix": "[Encore] ", "regenerate_hashtags": True}
    rule.status = RecyclingStatus.ACTIVE
    rule.last_run = datetime.utcnow() - timedelta(days=7)
    rule.next_run = datetime.utcnow() + timedelta(days=7)
    rule.created_at = datetime.utcnow() - timedelta(days=30)
    rule.updated_at = datetime.utcnow() - timedelta(days=1)
    return rule

@pytest.fixture
def mock_post():
    return {
        "id": "post-1",
        "user_id": "test-user-id",
        "platform": "instagram",
        "content": "This is a high-performing post #social #media",
        "media_urls": ["https://example.com/image.jpg"],
        "engagement": {
            "likes": 500,
            "comments": 50,
            "shares": 25
        },
        "posted_at": datetime.utcnow() - timedelta(days=30)
    }

@pytest.fixture
def mock_recycler_repository():
    repo = MagicMock()
    repo.create_rule.return_value = None
    repo.get_rule_by_id.return_value = None
    repo.get_rules_by_user_id.return_value = []
    repo.update_rule.return_value = None
    repo.delete_rule.return_value = None
    repo.get_posts_for_recycling.return_value = []
    repo.record_recycled_post.return_value = True
    return repo

@pytest.fixture
def mock_post_repository():
    repo = MagicMock()
    repo.get_user_posts.return_value = []
    repo.create_post.return_value = None
    return repo

@pytest.fixture
def mock_user_repository():
    repo = MagicMock()
    repo.get_by_id.return_value = None
    return repo

class TestPostRecyclerService:
    def test_create_recycling_rule(self, mock_recycler_repository, mock_recycling_rule):
        # Setup
        mock_recycler_repository.create_rule.return_value = mock_recycling_rule
        
        with patch('services.post_recycler.recycler_repository', mock_recycler_repository):
            # Execute
            result = create_recycling_rule(
                user_id="test-user-id",
                name="Weekly Recycling",
                description="Recycle top performing posts weekly",
                platform="instagram",
                frequency="weekly",
                day_of_week=1,
                time_of_day="09:00",
                post_selection_criteria={"min_engagement": 100, "max_age_days": 90},
                content_modification={"add_prefix": "[Encore] ", "regenerate_hashtags": True}
            )
            
            # Assert
            assert result == mock_recycling_rule
            mock_recycler_repository.create_rule.assert_called_once()
    
    def test_get_rule(self, mock_recycler_repository, mock_recycling_rule):
        # Setup
        mock_recycler_repository.get_rule_by_id.return_value = mock_recycling_rule
        
        with patch('services.post_recycler.recycler_repository', mock_recycler_repository):
            # Execute
            result = get_rule("rule-1")
            
            # Assert
            assert result == mock_recycling_rule
            mock_recycler_repository.get_rule_by_id.assert_called_once_with("rule-1")
    
    def test_get_rule_not_found(self, mock_recycler_repository):
        # Setup
        mock_recycler_repository.get_rule_by_id.return_value = None
        
        with patch('services.post_recycler.recycler_repository', mock_recycler_repository):
            # Execute
            result = get_rule("non-existent-rule")
            
            # Assert
            assert result is None
            mock_recycler_repository.get_rule_by_id.assert_called_once_with("non-existent-rule")
    
    def test_get_user_rules(self, mock_recycler_repository, mock_recycling_rule):
        # Setup
        mock_recycler_repository.get_rules_by_user_id.return_value = [mock_recycling_rule]
        
        with patch('services.post_recycler.recycler_repository', mock_recycler_repository):
            # Execute
            result = get_user_rules("test-user-id")
            
            # Assert
            assert len(result) == 1
            assert result[0] == mock_recycling_rule
            mock_recycler_repository.get_rules_by_user_id.assert_called_once_with(
                user_id="test-user-id",
                platform=None,
                status=None
            )
    
    def test_get_user_rules_with_filters(self, mock_recycler_repository):
        # Setup
        mock_recycler_repository.get_rules_by_user_id.return_value = []
        
        with patch('services.post_recycler.recycler_repository', mock_recycler_repository):
            # Execute
            result = get_user_rules(
                user_id="test-user-id",
                platform="instagram",
                status=RecyclingStatus.ACTIVE
            )
            
            # Assert
            assert len(result) == 0
            mock_recycler_repository.get_rules_by_user_id.assert_called_once_with(
                user_id="test-user-id",
                platform="instagram",
                status=RecyclingStatus.ACTIVE
            )
    
    def test_update_rule(self, mock_recycler_repository, mock_recycling_rule):
        # Setup
        mock_recycler_repository.get_rule_by_id.return_value = mock_recycling_rule
        mock_recycler_repository.update_rule.return_value = mock_recycling_rule
        
        with patch('services.post_recycler.recycler_repository', mock_recycler_repository):
            # Execute
            result = update_rule(
                rule_id="rule-1",
                name="Updated Weekly Recycling",
                description="Updated description",
                post_selection_criteria={"min_engagement": 200, "max_age_days": 60}
            )
            
            # Assert
            assert result == mock_recycling_rule
            mock_recycler_repository.get_rule_by_id.assert_called_once_with("rule-1")
            mock_recycler_repository.update_rule.assert_called_once()
    
    def test_update_rule_not_found(self, mock_recycler_repository):
        # Setup
        mock_recycler_repository.get_rule_by_id.return_value = None
        
        with patch('services.post_recycler.recycler_repository', mock_recycler_repository):
            # Execute
            result = update_rule(
                rule_id="non-existent-rule",
                name="Updated Rule"
            )
            
            # Assert
            assert result is None
            mock_recycler_repository.get_rule_by_id.assert_called_once_with("non-existent-rule")
            mock_recycler_repository.update_rule.assert_not_called()
    
    def test_delete_rule(self, mock_recycler_repository, mock_recycling_rule):
        # Setup
        mock_recycler_repository.get_rule_by_id.return_value = mock_recycling_rule
        
        with patch('services.post_recycler.recycler_repository', mock_recycler_repository):
            # Execute
            result = delete_rule("rule-1")
            
            # Assert
            assert result is True
            mock_recycler_repository.get_rule_by_id.assert_called_once_with("rule-1")
            mock_recycler_repository.delete_rule.assert_called_once_with(mock_recycling_rule)
    
    def test_delete_rule_not_found(self, mock_recycler_repository):
        # Setup
        mock_recycler_repository.get_rule_by_id.return_value = None
        
        with patch('services.post_recycler.recycler_repository', mock_recycler_repository):
            # Execute
            result = delete_rule("non-existent-rule")
            
            # Assert
            assert result is False
            mock_recycler_repository.get_rule_by_id.assert_called_once_with("non-existent-rule")
            mock_recycler_repository.delete_rule.assert_not_called()
    
    def test_get_posts_for_recycling(self, mock_recycler_repository, mock_post_repository, mock_post):
        # Setup
        mock_post_repository.get_user_posts.return_value = [mock_post]
        
        with patch('services.post_recycler.recycler_repository', mock_recycler_repository), \
             patch('services.post_recycler.post_repository', mock_post_repository):
            # Execute
            result = get_posts_for_recycling(
                user_id="test-user-id",
                platform="instagram",
                selection_criteria={"min_engagement": 100, "max_age_days": 90}
            )
            
            # Assert
            assert len(result) == 1
            assert result[0]["id"] == "post-1"
            mock_post_repository.get_user_posts.assert_called_once_with(
                user_id="test-user-id",
                platform="instagram"
            )
    
    def test_get_posts_for_recycling_no_matching_posts(self, mock_recycler_repository, mock_post_repository):
        # Setup
        mock_post_repository.get_user_posts.return_value = []
        
        with patch('services.post_recycler.recycler_repository', mock_recycler_repository), \
             patch('services.post_recycler.post_repository', mock_post_repository):
            # Execute
            result = get_posts_for_recycling(
                user_id="test-user-id",
                platform="instagram",
                selection_criteria={"min_engagement": 100, "max_age_days": 90}
            )
            
            # Assert
            assert len(result) == 0
            mock_post_repository.get_user_posts.assert_called_once_with(
                user_id="test-user-id",
                platform="instagram"
            )
    
    @patch('services.post_recycler.modify_post_content')
    def test_recycle_post(self, mock_modify_post_content, mock_recycler_repository, mock_post_repository, mock_post):
        # Setup
        modified_post = mock_post.copy()
        modified_post["content"] = "[Encore] This is a high-performing post #social #media #trending"
        mock_modify_post_content.return_value = modified_post
        
        new_post = modified_post.copy()
        new_post["id"] = "recycled-post-1"
        mock_post_repository.create_post.return_value = new_post
        
        with patch('services.post_recycler.recycler_repository', mock_recycler_repository), \
             patch('services.post_recycler.post_repository', mock_post_repository):
            # Execute
            result = recycle_post(
                post=mock_post,
                user_id="test-user-id",
                content_modification={"add_prefix": "[Encore] ", "regenerate_hashtags": True},
                rule_id="rule-1"
            )
            
            # Assert
            assert result == new_post
            mock_modify_post_content.assert_called_once_with(
                mock_post, {"add_prefix": "[Encore] ", "regenerate_hashtags": True}
            )
            mock_post_repository.create_post.assert_called_once()
            mock_recycler_repository.record_recycled_post.assert_called_once_with(
                original_post_id="post-1",
                new_post_id="recycled-post-1",
                rule_id="rule-1"
            )
    
    @patch('services.post_recycler.get_due_recycling_rules')
    @patch('services.post_recycler.get_posts_for_recycling')
    @patch('services.post_recycler.recycle_post')
    def test_process_due_recycling_rules(self, mock_recycle_post, mock_get_posts, mock_get_rules, 
                                        mock_recycler_repository, mock_recycling_rule, mock_post):
        # Import the function to test
        from services.post_recycler import process_due_recycling_rules
        
        # Setup
        mock_get_rules.return_value = [mock_recycling_rule]
        mock_get_posts.return_value = [mock_post]
        
        recycled_post = mock_post.copy()
        recycled_post["id"] = "recycled-post-1"
        mock_recycle_post.return_value = recycled_post
        
        with patch('services.post_recycler.recycler_repository', mock_recycler_repository):
            # Execute
            result = process_due_recycling_rules()
            
            # Assert
            assert result == 1  # One post recycled
            mock_get_rules.assert_called_once()
            mock_get_posts.assert_called_once_with(
                user_id="test-user-id",
                platform="instagram",
                selection_criteria={"min_engagement": 100, "max_age_days": 90}
            )
            mock_recycle_post.assert_called_once_with(
                post=mock_post,
                user_id="test-user-id",
                content_modification={"add_prefix": "[Encore] ", "regenerate_hashtags": True},
                rule_id="rule-1"
            )
            mock_recycler_repository.update_rule.assert_called_once()
    
    @patch('services.post_recycler.get_due_recycling_rules')
    def test_process_due_recycling_rules_no_rules(self, mock_get_rules, mock_recycler_repository):
        # Import the function to test
        from services.post_recycler import process_due_recycling_rules
        
        # Setup
        mock_get_rules.return_value = []
        
        with patch('services.post_recycler.recycler_repository', mock_recycler_repository):
            # Execute
            result = process_due_recycling_rules()
            
            # Assert
            assert result == 0  # No posts recycled
            mock_get_rules.assert_called_once()
            mock_recycler_repository.update_rule.assert_not_called()
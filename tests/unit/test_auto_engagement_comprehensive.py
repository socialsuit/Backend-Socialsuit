import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import json

# Import the auto engagement service and related models
# Note: Adjust imports based on actual project structure
from app.services.auto_engagement import create_engagement_rule, get_rule, get_user_rules, update_rule, delete_rule, process_engagement_rules
from app.services.models.auto_engagement_model import EngagementRule, EngagementAction, EngagementTrigger, EngagementStatus
from app.services.models.user_model import User

@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = "test-user-id"
    user.email = "test@example.com"
    return user

@pytest.fixture
def mock_engagement_rule():
    rule = MagicMock(spec=EngagementRule)
    rule.id = "rule-1"
    rule.user_id = "test-user-id"
    rule.name = "Auto Like Comments"
    rule.description = "Automatically like comments on my posts"
    rule.platform = "instagram"
    rule.trigger = EngagementTrigger.NEW_COMMENT
    rule.action = EngagementAction.LIKE
    rule.conditions = {"from_followers_only": True, "exclude_keywords": ["spam", "ad"]}
    rule.status = EngagementStatus.ACTIVE
    rule.created_at = datetime.utcnow() - timedelta(days=30)
    rule.updated_at = datetime.utcnow() - timedelta(days=1)
    return rule

@pytest.fixture
def mock_comment():
    return {
        "id": "comment-1",
        "post_id": "post-1",
        "user_id": "commenter-id",
        "content": "Great post! Love your content.",
        "created_at": datetime.utcnow() - timedelta(minutes=5)
    }

@pytest.fixture
def mock_engagement_repository():
    repo = MagicMock()
    repo.create_rule.return_value = None
    repo.get_rule_by_id.return_value = None
    repo.get_rules_by_user_id.return_value = []
    repo.update_rule.return_value = None
    repo.delete_rule.return_value = None
    repo.record_engagement_action.return_value = True
    repo.get_active_rules_by_trigger.return_value = []
    return repo

@pytest.fixture
def mock_social_api():
    api = MagicMock()
    api.like_comment.return_value = True
    api.reply_to_comment.return_value = True
    api.follow_user.return_value = True
    api.is_follower.return_value = True
    return api

class TestAutoEngagementService:
    def test_create_engagement_rule(self, mock_engagement_repository, mock_engagement_rule):
        # Setup
        mock_engagement_repository.create_rule.return_value = mock_engagement_rule
        
        with patch('services.auto_engagement.engagement_repository', mock_engagement_repository):
            # Execute
            result = create_engagement_rule(
                user_id="test-user-id",
                name="Auto Like Comments",
                description="Automatically like comments on my posts",
                platform="instagram",
                trigger=EngagementTrigger.NEW_COMMENT,
                action=EngagementAction.LIKE,
                conditions={"from_followers_only": True, "exclude_keywords": ["spam", "ad"]}
            )
            
            # Assert
            assert result == mock_engagement_rule
            mock_engagement_repository.create_rule.assert_called_once()
    
    def test_get_rule(self, mock_engagement_repository, mock_engagement_rule):
        # Setup
        mock_engagement_repository.get_rule_by_id.return_value = mock_engagement_rule
        
        with patch('services.auto_engagement.engagement_repository', mock_engagement_repository):
            # Execute
            result = get_rule("rule-1")
            
            # Assert
            assert result == mock_engagement_rule
            mock_engagement_repository.get_rule_by_id.assert_called_once_with("rule-1")
    
    def test_get_rule_not_found(self, mock_engagement_repository):
        # Setup
        mock_engagement_repository.get_rule_by_id.return_value = None
        
        with patch('services.auto_engagement.engagement_repository', mock_engagement_repository):
            # Execute
            result = get_rule("non-existent-rule")
            
            # Assert
            assert result is None
            mock_engagement_repository.get_rule_by_id.assert_called_once_with("non-existent-rule")
    
    def test_get_user_rules(self, mock_engagement_repository, mock_engagement_rule):
        # Setup
        mock_engagement_repository.get_rules_by_user_id.return_value = [mock_engagement_rule]
        
        with patch('services.auto_engagement.engagement_repository', mock_engagement_repository):
            # Execute
            result = get_user_rules("test-user-id")
            
            # Assert
            assert len(result) == 1
            assert result[0] == mock_engagement_rule
            mock_engagement_repository.get_rules_by_user_id.assert_called_once_with(
                user_id="test-user-id",
                platform=None,
                status=None,
                trigger=None
            )
    
    def test_get_user_rules_with_filters(self, mock_engagement_repository):
        # Setup
        mock_engagement_repository.get_rules_by_user_id.return_value = []
        
        with patch('services.auto_engagement.engagement_repository', mock_engagement_repository):
            # Execute
            result = get_user_rules(
                user_id="test-user-id",
                platform="instagram",
                status=EngagementStatus.ACTIVE,
                trigger=EngagementTrigger.NEW_COMMENT
            )
            
            # Assert
            assert len(result) == 0
            mock_engagement_repository.get_rules_by_user_id.assert_called_once_with(
                user_id="test-user-id",
                platform="instagram",
                status=EngagementStatus.ACTIVE,
                trigger=EngagementTrigger.NEW_COMMENT
            )
    
    def test_update_rule(self, mock_engagement_repository, mock_engagement_rule):
        # Setup
        mock_engagement_repository.get_rule_by_id.return_value = mock_engagement_rule
        mock_engagement_repository.update_rule.return_value = mock_engagement_rule
        
        with patch('services.auto_engagement.engagement_repository', mock_engagement_repository):
            # Execute
            result = update_rule(
                rule_id="rule-1",
                name="Updated Rule Name",
                description="Updated description",
                conditions={"from_followers_only": False, "exclude_keywords": ["spam", "ad", "scam"]}
            )
            
            # Assert
            assert result == mock_engagement_rule
            mock_engagement_repository.get_rule_by_id.assert_called_once_with("rule-1")
            mock_engagement_repository.update_rule.assert_called_once()
    
    def test_update_rule_not_found(self, mock_engagement_repository):
        # Setup
        mock_engagement_repository.get_rule_by_id.return_value = None
        
        with patch('services.auto_engagement.engagement_repository', mock_engagement_repository):
            # Execute
            result = update_rule(
                rule_id="non-existent-rule",
                name="Updated Rule Name"
            )
            
            # Assert
            assert result is None
            mock_engagement_repository.get_rule_by_id.assert_called_once_with("non-existent-rule")
            mock_engagement_repository.update_rule.assert_not_called()
    
    def test_delete_rule(self, mock_engagement_repository, mock_engagement_rule):
        # Setup
        mock_engagement_repository.get_rule_by_id.return_value = mock_engagement_rule
        
        with patch('services.auto_engagement.engagement_repository', mock_engagement_repository):
            # Execute
            result = delete_rule("rule-1")
            
            # Assert
            assert result is True
            mock_engagement_repository.get_rule_by_id.assert_called_once_with("rule-1")
            mock_engagement_repository.delete_rule.assert_called_once_with(mock_engagement_rule)
    
    def test_delete_rule_not_found(self, mock_engagement_repository):
        # Setup
        mock_engagement_repository.get_rule_by_id.return_value = None
        
        with patch('services.auto_engagement.engagement_repository', mock_engagement_repository):
            # Execute
            result = delete_rule("non-existent-rule")
            
            # Assert
            assert result is False
            mock_engagement_repository.get_rule_by_id.assert_called_once_with("non-existent-rule")
            mock_engagement_repository.delete_rule.assert_not_called()
    
    @patch('services.auto_engagement.get_social_api')
    def test_process_comment_trigger(self, mock_get_social_api, mock_engagement_repository, 
                                    mock_engagement_rule, mock_social_api, mock_comment):
        # Import the function to test
        from services.auto_engagement import process_comment_trigger
        
        # Setup
        mock_engagement_repository.get_active_rules_by_trigger.return_value = [mock_engagement_rule]
        mock_get_social_api.return_value = mock_social_api
        
        with patch('services.auto_engagement.engagement_repository', mock_engagement_repository):
            # Execute
            result = process_comment_trigger(
                user_id="test-user-id",
                platform="instagram",
                comment=mock_comment
            )
            
            # Assert
            assert result is True
            mock_engagement_repository.get_active_rules_by_trigger.assert_called_once_with(
                user_id="test-user-id",
                platform="instagram",
                trigger=EngagementTrigger.NEW_COMMENT
            )
            mock_social_api.is_follower.assert_called_once_with(
                user_id="commenter-id"
            )
            mock_social_api.like_comment.assert_called_once_with(
                comment_id="comment-1"
            )
            mock_engagement_repository.record_engagement_action.assert_called_once_with(
                rule_id="rule-1",
                action=EngagementAction.LIKE,
                target_id="comment-1",
                target_type="comment",
                success=True
            )
    
    @patch('services.auto_engagement.get_social_api')
    def test_process_comment_trigger_no_matching_rules(self, mock_get_social_api, 
                                                     mock_engagement_repository, mock_comment):
        # Import the function to test
        from services.auto_engagement import process_comment_trigger
        
        # Setup
        mock_engagement_repository.get_active_rules_by_trigger.return_value = []
        
        with patch('services.auto_engagement.engagement_repository', mock_engagement_repository):
            # Execute
            result = process_comment_trigger(
                user_id="test-user-id",
                platform="instagram",
                comment=mock_comment
            )
            
            # Assert
            assert result is False
            mock_engagement_repository.get_active_rules_by_trigger.assert_called_once_with(
                user_id="test-user-id",
                platform="instagram",
                trigger=EngagementTrigger.NEW_COMMENT
            )
            mock_get_social_api.assert_not_called()
            mock_engagement_repository.record_engagement_action.assert_not_called()
    
    @patch('services.auto_engagement.get_social_api')
    def test_process_comment_trigger_condition_not_met(self, mock_get_social_api, mock_engagement_repository, 
                                                     mock_engagement_rule, mock_social_api, mock_comment):
        # Import the function to test
        from services.auto_engagement import process_comment_trigger
        
        # Setup
        mock_engagement_repository.get_active_rules_by_trigger.return_value = [mock_engagement_rule]
        mock_get_social_api.return_value = mock_social_api
        
        # Set up the condition to fail - not a follower
        mock_social_api.is_follower.return_value = False
        
        with patch('services.auto_engagement.engagement_repository', mock_engagement_repository):
            # Execute
            result = process_comment_trigger(
                user_id="test-user-id",
                platform="instagram",
                comment=mock_comment
            )
            
            # Assert
            assert result is False
            mock_engagement_repository.get_active_rules_by_trigger.assert_called_once_with(
                user_id="test-user-id",
                platform="instagram",
                trigger=EngagementTrigger.NEW_COMMENT
            )
            mock_social_api.is_follower.assert_called_once_with(
                user_id="commenter-id"
            )
            mock_social_api.like_comment.assert_not_called()
            mock_engagement_repository.record_engagement_action.assert_not_called()
    
    @patch('services.auto_engagement.get_social_api')
    def test_process_comment_trigger_keyword_exclusion(self, mock_get_social_api, mock_engagement_repository, 
                                                     mock_engagement_rule, mock_social_api):
        # Import the function to test
        from services.auto_engagement import process_comment_trigger
        
        # Setup
        mock_engagement_repository.get_active_rules_by_trigger.return_value = [mock_engagement_rule]
        mock_get_social_api.return_value = mock_social_api
        
        # Create a comment with excluded keyword
        spam_comment = {
            "id": "comment-2",
            "post_id": "post-1",
            "user_id": "commenter-id",
            "content": "Check out this spam link!",
            "created_at": datetime.utcnow() - timedelta(minutes=5)
        }
        
        with patch('services.auto_engagement.engagement_repository', mock_engagement_repository):
            # Execute
            result = process_comment_trigger(
                user_id="test-user-id",
                platform="instagram",
                comment=spam_comment
            )
            
            # Assert
            assert result is False
            mock_engagement_repository.get_active_rules_by_trigger.assert_called_once_with(
                user_id="test-user-id",
                platform="instagram",
                trigger=EngagementTrigger.NEW_COMMENT
            )
            mock_social_api.is_follower.assert_called_once_with(
                user_id="commenter-id"
            )
            mock_social_api.like_comment.assert_not_called()
            mock_engagement_repository.record_engagement_action.assert_not_called()
    
    @patch('services.auto_engagement.process_comment_trigger')
    @patch('services.auto_engagement.process_mention_trigger')
    @patch('services.auto_engagement.process_follow_trigger')
    def test_process_engagement_rules(self, mock_process_follow, mock_process_mention, 
                                     mock_process_comment):
        # Setup
        mock_process_comment.return_value = True
        mock_process_mention.return_value = True
        mock_process_follow.return_value = False
        
        # Execute
        result = process_engagement_rules()
        
        # Assert
        assert result == 2  # Two successful engagements
        mock_process_comment.assert_called_once()
        mock_process_mention.assert_called_once()
        mock_process_follow.assert_called_once()
    
    @patch('services.auto_engagement.get_social_api')
    def test_reply_to_comment_action(self, mock_get_social_api, mock_engagement_repository, 
                                   mock_social_api, mock_comment):
        # Import the function to test
        from services.auto_engagement import process_comment_trigger
        
        # Setup
        reply_rule = MagicMock(spec=EngagementRule)
        reply_rule.id = "rule-2"
        reply_rule.user_id = "test-user-id"
        reply_rule.platform = "instagram"
        reply_rule.trigger = EngagementTrigger.NEW_COMMENT
        reply_rule.action = EngagementAction.REPLY
        reply_rule.conditions = {"from_followers_only": False, "reply_template": "Thanks for your comment, {username}!"}
        reply_rule.status = EngagementStatus.ACTIVE
        
        mock_engagement_repository.get_active_rules_by_trigger.return_value = [reply_rule]
        mock_get_social_api.return_value = mock_social_api
        
        # Add username to the comment
        comment_with_username = mock_comment.copy()
        comment_with_username["username"] = "commenter123"
        
        with patch('services.auto_engagement.engagement_repository', mock_engagement_repository):
            # Execute
            result = process_comment_trigger(
                user_id="test-user-id",
                platform="instagram",
                comment=comment_with_username
            )
            
            # Assert
            assert result is True
            mock_social_api.reply_to_comment.assert_called_once_with(
                comment_id="comment-1",
                reply_text="Thanks for your comment, commenter123!"
            )
            mock_engagement_repository.record_engagement_action.assert_called_once_with(
                rule_id="rule-2",
                action=EngagementAction.REPLY,
                target_id="comment-1",
                target_type="comment",
                success=True
            )
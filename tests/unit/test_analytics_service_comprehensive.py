import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import json

# Import the analytics service and related models
# Note: Adjust imports based on actual project structure
from app.services.analytics import get_insights, get_user_analytics, get_time_series_data, get_content_performance
from app.services.models.user_model import User

@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = "test-user-id"
    user.email = "test@example.com"
    return user

@pytest.fixture
def mock_user_repository():
    repo = MagicMock()
    repo.get_by_id.return_value = None
    return repo

@pytest.fixture
def mock_user_metrics_repository():
    repo = MagicMock()
    repo.get_metrics_by_user_id.return_value = {
        "followers": 1000,
        "following": 500,
        "posts": 100,
        "engagement_rate": 2.5
    }
    return repo

@pytest.fixture
def mock_content_performance_repository():
    repo = MagicMock()
    repo.get_performance_by_user_id.return_value = [
        {
            "post_id": "post1",
            "platform": "instagram",
            "likes": 150,
            "comments": 25,
            "shares": 10,
            "views": 1000,
            "posted_at": datetime.utcnow() - timedelta(days=5)
        },
        {
            "post_id": "post2",
            "platform": "twitter",
            "likes": 75,
            "comments": 15,
            "shares": 30,
            "views": 500,
            "posted_at": datetime.utcnow() - timedelta(days=2)
        }
    ]
    return repo

@pytest.fixture
def mock_time_series_repository():
    repo = MagicMock()
    
    # Create sample time series data for the last 30 days
    today = datetime.utcnow().date()
    time_series_data = []
    
    for i in range(30):
        date = today - timedelta(days=i)
        time_series_data.append({
            "date": date,
            "followers": 1000 - i * 10,
            "engagement": 2.5 + (i * 0.1),
            "impressions": 5000 - (i * 100),
            "platform": "instagram" if i % 2 == 0 else "twitter"
        })
    
    repo.get_time_series_data.return_value = time_series_data
    return repo

class TestAnalyticsService:
    @patch('services.analytics.get_platform_insights')
    def test_get_insights(self, mock_get_platform_insights):
        # Setup
        mock_get_platform_insights.return_value = {
            "followers": 1000,
            "posts": 100,
            "engagement_rate": 2.5
        }
        
        # Execute
        result = get_insights("instagram")
        
        # Assert
        assert result == {
            "followers": 1000,
            "posts": 100,
            "engagement_rate": 2.5
        }
        mock_get_platform_insights.assert_called_once_with("instagram")
    
    @patch('services.analytics.get_platform_insights')
    def test_get_insights_unsupported_platform(self, mock_get_platform_insights):
        # Setup
        mock_get_platform_insights.side_effect = ValueError("Unsupported platform")
        
        # Execute and Assert
        with pytest.raises(ValueError, match="Unsupported platform"):
            get_insights("unsupported_platform")
    
    def test_get_user_analytics(self, mock_user, mock_user_metrics_repository):
        # Setup - assuming get_user_analytics uses the user_metrics_repository
        with patch('services.analytics.user_metrics_repository', mock_user_metrics_repository):
            # Execute
            result = get_user_analytics(mock_user.id)
            
            # Assert
            assert result == {
                "followers": 1000,
                "following": 500,
                "posts": 100,
                "engagement_rate": 2.5
            }
            mock_user_metrics_repository.get_metrics_by_user_id.assert_called_once_with(mock_user.id)
    
    def test_get_user_analytics_with_platform(self, mock_user, mock_user_metrics_repository):
        # Setup - assuming get_user_analytics uses the user_metrics_repository
        mock_user_metrics_repository.get_metrics_by_user_id_and_platform.return_value = {
            "followers": 800,
            "following": 400,
            "posts": 75,
            "engagement_rate": 3.0
        }
        
        with patch('services.analytics.user_metrics_repository', mock_user_metrics_repository):
            # Execute
            result = get_user_analytics(mock_user.id, platform="instagram")
            
            # Assert
            assert result == {
                "followers": 800,
                "following": 400,
                "posts": 75,
                "engagement_rate": 3.0
            }
            mock_user_metrics_repository.get_metrics_by_user_id_and_platform.assert_called_once_with(
                mock_user.id, "instagram"
            )
    
    def test_get_time_series_data(self, mock_user, mock_time_series_repository):
        # Setup
        with patch('services.analytics.time_series_repository', mock_time_series_repository):
            # Execute
            result = get_time_series_data(
                user_id=mock_user.id,
                metric="followers",
                start_date=datetime.utcnow().date() - timedelta(days=7),
                end_date=datetime.utcnow().date()
            )
            
            # Assert
            assert len(result) > 0
            for item in result:
                assert "date" in item
                assert "value" in item
                assert "platform" in item
            
            mock_time_series_repository.get_time_series_data.assert_called_once()
    
    def test_get_time_series_data_with_platform(self, mock_user, mock_time_series_repository):
        # Setup
        with patch('services.analytics.time_series_repository', mock_time_series_repository):
            # Execute
            result = get_time_series_data(
                user_id=mock_user.id,
                metric="followers",
                platform="instagram",
                start_date=datetime.utcnow().date() - timedelta(days=7),
                end_date=datetime.utcnow().date()
            )
            
            # Assert
            assert len(result) > 0
            for item in result:
                assert item["platform"] == "instagram"
            
            mock_time_series_repository.get_time_series_data.assert_called_once()
    
    def test_get_content_performance(self, mock_user, mock_content_performance_repository):
        # Setup
        with patch('services.analytics.content_performance_repository', mock_content_performance_repository):
            # Execute
            result = get_content_performance(user_id=mock_user.id)
            
            # Assert
            assert len(result) == 2
            assert result[0]["post_id"] == "post1"
            assert result[0]["platform"] == "instagram"
            assert result[1]["post_id"] == "post2"
            assert result[1]["platform"] == "twitter"
            
            mock_content_performance_repository.get_performance_by_user_id.assert_called_once_with(
                user_id=mock_user.id,
                platform=None,
                limit=None,
                sort_by=None,
                sort_order=None
            )
    
    def test_get_content_performance_with_filters(self, mock_user, mock_content_performance_repository):
        # Setup
        filtered_results = [
            {
                "post_id": "post1",
                "platform": "instagram",
                "likes": 150,
                "comments": 25,
                "shares": 10,
                "views": 1000,
                "posted_at": datetime.utcnow() - timedelta(days=5)
            }
        ]
        mock_content_performance_repository.get_performance_by_user_id.return_value = filtered_results
        
        with patch('services.analytics.content_performance_repository', mock_content_performance_repository):
            # Execute
            result = get_content_performance(
                user_id=mock_user.id,
                platform="instagram",
                limit=10,
                sort_by="likes",
                sort_order="desc"
            )
            
            # Assert
            assert len(result) == 1
            assert result[0]["post_id"] == "post1"
            assert result[0]["platform"] == "instagram"
            
            mock_content_performance_repository.get_performance_by_user_id.assert_called_once_with(
                user_id=mock_user.id,
                platform="instagram",
                limit=10,
                sort_by="likes",
                sort_order="desc"
            )
    
    @patch('services.analytics.collect_analytics_data')
    def test_trigger_analytics_collection(self, mock_collect_analytics_data, mock_user):
        # Import the function to test
        from services.analytics import trigger_analytics_collection
        
        # Setup
        mock_collect_analytics_data.return_value = True
        
        # Execute
        result = trigger_analytics_collection(user_id=mock_user.id)
        
        # Assert
        assert result is True
        mock_collect_analytics_data.assert_called_once_with(user_id=mock_user.id)
    
    @patch('services.analytics.collect_analytics_data')
    def test_trigger_analytics_collection_failure(self, mock_collect_analytics_data, mock_user):
        # Import the function to test
        from services.analytics import trigger_analytics_collection
        
        # Setup
        mock_collect_analytics_data.side_effect = Exception("API Error")
        
        # Execute and Assert
        with pytest.raises(Exception, match="API Error"):
            trigger_analytics_collection(user_id=mock_user.id)
        
        mock_collect_analytics_data.assert_called_once_with(user_id=mock_user.id)
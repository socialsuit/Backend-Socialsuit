import pytest
from unittest.mock import MagicMock, patch
import uuid
from datetime import datetime, timedelta

from app.services.analytics.services.data_analyzer_service import AnalyticsAnalyzerService
from app.services.analytics.services.data_collector_service import AnalyticsCollectorService
from app.services.analytics.services.chart_generator_service import ChartGeneratorService
from app.services.repositories.user_repository import UserRepository
from app.services.repositories.analytics_repository import (
    PostEngagementRepository, 
    UserMetricsRepository, 
    ContentPerformanceRepository
)
from app.services.models.user_model import User
from app.services.models.analytics_models import PostEngagement, UserMetrics, ContentPerformance

# Fixtures
@pytest.fixture
def user_repository():
    return MagicMock(spec=UserRepository)

@pytest.fixture
def post_engagement_repository():
    return MagicMock(spec=PostEngagementRepository)

@pytest.fixture
def user_metrics_repository():
    return MagicMock(spec=UserMetricsRepository)

@pytest.fixture
def content_performance_repository():
    return MagicMock(spec=ContentPerformanceRepository)

@pytest.fixture
def analytics_analyzer_service(
    user_repository, 
    post_engagement_repository, 
    user_metrics_repository, 
    content_performance_repository
):
    return AnalyticsAnalyzerService(
        user_repository=user_repository,
        post_engagement_repository=post_engagement_repository,
        user_metrics_repository=user_metrics_repository,
        content_performance_repository=content_performance_repository
    )

@pytest.fixture
def analytics_collector_service(
    user_repository, 
    post_engagement_repository, 
    user_metrics_repository, 
    content_performance_repository
):
    return AnalyticsCollectorService(
        user_repository=user_repository,
        post_engagement_repository=post_engagement_repository,
        user_metrics_repository=user_metrics_repository,
        content_performance_repository=content_performance_repository
    )

@pytest.fixture
def chart_generator_service(analytics_analyzer_service):
    return ChartGeneratorService(
        analytics_analyzer_service=analytics_analyzer_service
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
def sample_users():
    return [
        User(id=str(uuid.uuid4()), email="user1@example.com", username="user1", is_verified=True),
        User(id=str(uuid.uuid4()), email="user2@example.com", username="user2", is_verified=True),
        User(id=str(uuid.uuid4()), email="user3@example.com", username="user3", is_verified=False)
    ]

@pytest.fixture
def sample_post_engagements(sample_user):
    now = datetime.utcnow()
    return [
        PostEngagement(
            id=1,
            user_id=sample_user.id,
            platform="twitter",
            post_id="tweet123",
            engagement_type="likes",
            count=10,
            timestamp=now - timedelta(days=1),
            created_at=now,
            updated_at=now
        ),
        PostEngagement(
            id=2,
            user_id=sample_user.id,
            platform="twitter",
            post_id="tweet123",
            engagement_type="retweets",
            count=5,
            timestamp=now - timedelta(days=1),
            created_at=now,
            updated_at=now
        ),
        PostEngagement(
            id=3,
            user_id=sample_user.id,
            platform="facebook",
            post_id="fb456",
            engagement_type="likes",
            count=20,
            timestamp=now - timedelta(days=2),
            created_at=now,
            updated_at=now
        )
    ]

@pytest.fixture
def sample_user_metrics(sample_user):
    now = datetime.utcnow()
    return [
        UserMetrics(
            id=1,
            user_id=sample_user.id,
            platform="twitter",
            metric_type="followers",
            count=1000,
            timestamp=now - timedelta(days=1),
            created_at=now,
            updated_at=now
        ),
        UserMetrics(
            id=2,
            user_id=sample_user.id,
            platform="twitter",
            metric_type="following",
            count=500,
            timestamp=now - timedelta(days=1),
            created_at=now,
            updated_at=now
        ),
        UserMetrics(
            id=3,
            user_id=sample_user.id,
            platform="facebook",
            metric_type="page_likes",
            count=2000,
            timestamp=now - timedelta(days=2),
            created_at=now,
            updated_at=now
        )
    ]

@pytest.fixture
def sample_content_performance(sample_user):
    now = datetime.utcnow()
    return [
        ContentPerformance(
            id=1,
            user_id=sample_user.id,
            platform="twitter",
            content_type="image",
            engagement_rate=0.05,
            reach=5000,
            timestamp=now - timedelta(days=1),
            created_at=now,
            updated_at=now
        ),
        ContentPerformance(
            id=2,
            user_id=sample_user.id,
            platform="twitter",
            content_type="text",
            engagement_rate=0.03,
            reach=3000,
            timestamp=now - timedelta(days=1),
            created_at=now,
            updated_at=now
        ),
        ContentPerformance(
            id=3,
            user_id=sample_user.id,
            platform="facebook",
            content_type="video",
            engagement_rate=0.07,
            reach=7000,
            timestamp=now - timedelta(days=2),
            created_at=now,
            updated_at=now
        )
    ]

# AnalyticsAnalyzerService Tests
def test_get_user_overview(analytics_analyzer_service, sample_user, sample_user_metrics):
    # Setup
    user_id = sample_user.id
    analytics_analyzer_service.user_repository.get_by_id.return_value = sample_user
    analytics_analyzer_service.user_metrics_repository.get_by_user_id.return_value = sample_user_metrics
    
    # Execute
    result = analytics_analyzer_service.get_user_overview(user_id)
    
    # Assert
    assert result["user_id"] == user_id
    assert "platforms" in result
    assert len(result["platforms"]) > 0
    analytics_analyzer_service.user_repository.get_by_id.assert_called_once_with(user_id)
    analytics_analyzer_service.user_metrics_repository.get_by_user_id.assert_called_once_with(user_id)

def test_get_platform_metrics(analytics_analyzer_service, sample_user, sample_user_metrics, sample_post_engagements):
    # Setup
    user_id = sample_user.id
    platform = "twitter"
    analytics_analyzer_service.user_metrics_repository.get_by_user_id.return_value = [
        m for m in sample_user_metrics if m.platform == platform
    ]
    analytics_analyzer_service.post_engagement_repository.get_by_user_id.return_value = [
        e for e in sample_post_engagements if e.platform == platform
    ]
    
    # Execute
    result = analytics_analyzer_service.get_platform_metrics(user_id, platform)
    
    # Assert
    assert result["platform"] == platform
    assert "metrics" in result
    assert "engagements" in result
    analytics_analyzer_service.user_metrics_repository.get_by_user_id.assert_called_once_with(
        user_id, platform=platform
    )
    analytics_analyzer_service.post_engagement_repository.get_by_user_id.assert_called_once_with(
        user_id, platform=platform
    )

def test_get_top_performing_content(analytics_analyzer_service, sample_user, sample_content_performance):
    # Setup
    user_id = sample_user.id
    platform = "twitter"
    limit = 2
    analytics_analyzer_service.content_performance_repository.get_top_performing_content.return_value = [
        p for p in sample_content_performance if p.platform == platform
    ][:limit]
    
    # Execute
    result = analytics_analyzer_service.get_top_performing_content(user_id, platform, limit=limit)
    
    # Assert
    assert len(result) <= limit
    for content in result:
        assert content["platform"] == platform
        assert "content_type" in content
        assert "engagement_rate" in content
        assert "reach" in content
    analytics_analyzer_service.content_performance_repository.get_top_performing_content.assert_called_once_with(
        user_id, platform, limit=limit
    )

# AnalyticsCollectorService Tests
@patch("app.services.analytics.services.data_collector_service.requests")
def test_collect_twitter_data(mock_requests, analytics_collector_service, sample_user):
    # Setup
    user_id = sample_user.id
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "followers": 1000,
        "following": 500,
        "tweets": [
            {"id": "tweet1", "likes": 10, "retweets": 5},
            {"id": "tweet2", "likes": 20, "retweets": 8}
        ]
    }
    mock_response.status_code = 200
    mock_requests.get.return_value = mock_response
    analytics_collector_service.post_engagement_repository.create = MagicMock()
    analytics_collector_service.user_metrics_repository.create = MagicMock()
    
    # Execute
    result = analytics_collector_service.collect_twitter_data(user_id)
    
    # Assert
    assert result is True
    assert mock_requests.get.called
    assert analytics_collector_service.post_engagement_repository.create.call_count == 4  # 2 tweets * 2 metrics
    assert analytics_collector_service.user_metrics_repository.create.call_count == 2  # followers + following

@patch("app.services.analytics.services.data_collector_service.requests")
def test_collect_facebook_data(mock_requests, analytics_collector_service, sample_user):
    # Setup
    user_id = sample_user.id
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "page_likes": 2000,
        "page_views": 1000,
        "posts": [
            {"id": "post1", "likes": 30, "shares": 10, "comments": 5},
            {"id": "post2", "likes": 40, "shares": 15, "comments": 8}
        ]
    }
    mock_response.status_code = 200
    mock_requests.get.return_value = mock_response
    analytics_collector_service.post_engagement_repository.create = MagicMock()
    analytics_collector_service.user_metrics_repository.create = MagicMock()
    
    # Execute
    result = analytics_collector_service.collect_facebook_data(user_id)
    
    # Assert
    assert result is True
    assert mock_requests.get.called
    assert analytics_collector_service.post_engagement_repository.create.call_count == 6  # 2 posts * 3 metrics
    assert analytics_collector_service.user_metrics_repository.create.call_count == 2  # page_likes + page_views

@patch("app.services.analytics.services.data_collector_service.asyncio")
def test_collect_all_platforms_data(mock_asyncio, analytics_collector_service, sample_user):
    # Setup
    user_id = sample_user.id
    analytics_collector_service.collect_twitter_data = MagicMock(return_value=True)
    analytics_collector_service.collect_facebook_data = MagicMock(return_value=True)
    analytics_collector_service.collect_instagram_data = MagicMock(return_value=True)
    mock_asyncio.gather.return_value = [True, True, True]
    mock_asyncio.run = MagicMock(return_value=[True, True, True])
    
    # Execute
    result = analytics_collector_service.collect_all_platforms_data(user_id)
    
    # Assert
    assert result is True
    assert mock_asyncio.gather.called or mock_asyncio.run.called

# ChartGeneratorService Tests
def test_generate_time_series_data(chart_generator_service, analytics_analyzer_service, sample_user):
    # Setup
    user_id = sample_user.id
    platform = "twitter"
    metric_type = "followers"
    time_period = "week"
    
    mock_data = [
        {"timestamp": datetime.utcnow() - timedelta(days=6), "count": 950},
        {"timestamp": datetime.utcnow() - timedelta(days=5), "count": 960},
        {"timestamp": datetime.utcnow() - timedelta(days=4), "count": 970},
        {"timestamp": datetime.utcnow() - timedelta(days=3), "count": 980},
        {"timestamp": datetime.utcnow() - timedelta(days=2), "count": 990},
        {"timestamp": datetime.utcnow() - timedelta(days=1), "count": 1000},
    ]
    
    analytics_analyzer_service.get_metric_time_series.return_value = mock_data
    
    # Execute
    result = chart_generator_service.generate_time_series_data(user_id, platform, metric_type, time_period)
    
    # Assert
    assert "labels" in result
    assert "datasets" in result
    assert len(result["labels"]) == len(mock_data)
    assert len(result["datasets"]) == 1
    assert len(result["datasets"][0]["data"]) == len(mock_data)
    analytics_analyzer_service.get_metric_time_series.assert_called_once_with(
        user_id, platform, metric_type, time_period
    )

def test_generate_platform_comparison_data(chart_generator_service, analytics_analyzer_service, sample_user):
    # Setup
    user_id = sample_user.id
    metric_type = "followers"
    
    mock_data = {
        "twitter": 1000,
        "facebook": 2000,
        "instagram": 3000
    }
    
    analytics_analyzer_service.get_platform_comparison.return_value = mock_data
    
    # Execute
    result = chart_generator_service.generate_platform_comparison_data(user_id, metric_type)
    
    # Assert
    assert "labels" in result
    assert "datasets" in result
    assert len(result["labels"]) == len(mock_data)
    assert len(result["datasets"]) == 1
    assert len(result["datasets"][0]["data"]) == len(mock_data)
    analytics_analyzer_service.get_platform_comparison.assert_called_once_with(user_id, metric_type)

def test_generate_engagement_breakdown_data(chart_generator_service, analytics_analyzer_service, sample_user):
    # Setup
    user_id = sample_user.id
    platform = "twitter"
    
    mock_data = {
        "likes": 100,
        "retweets": 50,
        "replies": 25
    }
    
    analytics_analyzer_service.get_engagement_breakdown.return_value = mock_data
    
    # Execute
    result = chart_generator_service.generate_engagement_breakdown_data(user_id, platform)
    
    # Assert
    assert "labels" in result
    assert "datasets" in result
    assert len(result["labels"]) == len(mock_data)
    assert len(result["datasets"]) == 1
    assert len(result["datasets"][0]["data"]) == len(mock_data)
    analytics_analyzer_service.get_engagement_breakdown.assert_called_once_with(user_id, platform)

def test_generate_content_performance_data(chart_generator_service, analytics_analyzer_service, sample_user):
    # Setup
    user_id = sample_user.id
    platform = "twitter"
    
    mock_data = [
        {"content_type": "image", "engagement_rate": 0.05, "reach": 5000},
        {"content_type": "text", "engagement_rate": 0.03, "reach": 3000},
        {"content_type": "video", "engagement_rate": 0.07, "reach": 7000}
    ]
    
    analytics_analyzer_service.get_top_performing_content.return_value = mock_data
    
    # Execute
    result = chart_generator_service.generate_content_performance_data(user_id, platform)
    
    # Assert
    assert "labels" in result
    assert "datasets" in result
    assert len(result["labels"]) == len(mock_data)
    assert len(result["datasets"]) == 2  # engagement_rate and reach
    assert len(result["datasets"][0]["data"]) == len(mock_data)
    assert len(result["datasets"][1]["data"]) == len(mock_data)
    analytics_analyzer_service.get_top_performing_content.assert_called_once_with(user_id, platform)
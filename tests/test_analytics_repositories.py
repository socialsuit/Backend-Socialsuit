import pytest
from unittest.mock import MagicMock, patch
import uuid
from datetime import datetime, timedelta

from app.services.models.analytics_models import PostEngagement, UserMetrics, ContentPerformance
from app.services.repositories.analytics_repository import (
    PostEngagementRepository, 
    UserMetricsRepository, 
    ContentPerformanceRepository
)
from tests.utils import (
    mock_db_session, 
    post_engagement_repository, 
    user_metrics_repository, 
    content_performance_repository
)

# Sample test data
@pytest.fixture
def sample_user_id():
    return str(uuid.uuid4())

@pytest.fixture
def sample_post_engagements(sample_user_id):
    now = datetime.utcnow()
    return [
        PostEngagement(
            id=1,
            user_id=sample_user_id,
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
            user_id=sample_user_id,
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
            user_id=sample_user_id,
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
def sample_user_metrics(sample_user_id):
    now = datetime.utcnow()
    return [
        UserMetrics(
            id=1,
            user_id=sample_user_id,
            platform="twitter",
            metric_type="followers",
            count=1000,
            timestamp=now - timedelta(days=1),
            created_at=now,
            updated_at=now
        ),
        UserMetrics(
            id=2,
            user_id=sample_user_id,
            platform="twitter",
            metric_type="following",
            count=500,
            timestamp=now - timedelta(days=1),
            created_at=now,
            updated_at=now
        ),
        UserMetrics(
            id=3,
            user_id=sample_user_id,
            platform="facebook",
            metric_type="page_likes",
            count=2000,
            timestamp=now - timedelta(days=2),
            created_at=now,
            updated_at=now
        )
    ]

@pytest.fixture
def sample_content_performance(sample_user_id):
    now = datetime.utcnow()
    return [
        ContentPerformance(
            id=1,
            user_id=sample_user_id,
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
            user_id=sample_user_id,
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
            user_id=sample_user_id,
            platform="facebook",
            content_type="video",
            engagement_rate=0.07,
            reach=7000,
            timestamp=now - timedelta(days=2),
            created_at=now,
            updated_at=now
        )
    ]

# PostEngagementRepository Tests
def test_post_engagement_get_by_user_id(post_engagement_repository, sample_user_id, sample_post_engagements):
    # Setup
    post_engagement_repository.db.query().filter().all.return_value = sample_post_engagements
    
    # Execute
    result = post_engagement_repository.get_by_user_id(sample_user_id)
    
    # Assert
    assert result == sample_post_engagements
    post_engagement_repository.db.query.assert_called_once_with(PostEngagement)

def test_post_engagement_get_by_user_id_with_platform(post_engagement_repository, sample_user_id, sample_post_engagements):
    # Setup
    platform = "twitter"
    filtered_engagements = [e for e in sample_post_engagements if e.platform == platform]
    post_engagement_repository.db.query().filter().filter().all.return_value = filtered_engagements
    
    # Execute
    result = post_engagement_repository.get_by_user_id(sample_user_id, platform=platform)
    
    # Assert
    assert result == filtered_engagements
    post_engagement_repository.db.query.assert_called_once_with(PostEngagement)

def test_post_engagement_get_by_user_id_with_date_range(post_engagement_repository, sample_user_id, sample_post_engagements):
    # Setup
    start_date = datetime.utcnow() - timedelta(days=3)
    end_date = datetime.utcnow()
    post_engagement_repository.db.query().filter().filter().filter().all.return_value = sample_post_engagements
    
    # Execute
    result = post_engagement_repository.get_by_user_id(
        sample_user_id, start_date=start_date, end_date=end_date
    )
    
    # Assert
    assert result == sample_post_engagements
    post_engagement_repository.db.query.assert_called_once_with(PostEngagement)

def test_post_engagement_get_by_user_id_with_engagement_type(post_engagement_repository, sample_user_id, sample_post_engagements):
    # Setup
    engagement_type = "likes"
    filtered_engagements = [e for e in sample_post_engagements if e.engagement_type == engagement_type]
    post_engagement_repository.db.query().filter().filter().all.return_value = filtered_engagements
    
    # Execute
    result = post_engagement_repository.get_by_user_id(sample_user_id, engagement_type=engagement_type)
    
    # Assert
    assert result == filtered_engagements
    post_engagement_repository.db.query.assert_called_once_with(PostEngagement)

def test_post_engagement_get_by_post_id(post_engagement_repository, sample_post_engagements):
    # Setup
    post_id = "tweet123"
    user_id = sample_post_engagements[0].user_id
    platform = "twitter"
    filtered_engagements = [e for e in sample_post_engagements if e.post_id == post_id and e.platform == platform]
    post_engagement_repository.db.query().filter().filter().filter().all.return_value = filtered_engagements
    
    # Execute
    result = post_engagement_repository.get_by_post_id(user_id, platform, post_id)
    
    # Assert
    assert result == filtered_engagements
    post_engagement_repository.db.query.assert_called_once_with(PostEngagement)

# UserMetricsRepository Tests
def test_user_metrics_get_by_user_id(user_metrics_repository, sample_user_id, sample_user_metrics):
    # Setup
    user_metrics_repository.db.query().filter().all.return_value = sample_user_metrics
    
    # Execute
    result = user_metrics_repository.get_by_user_id(sample_user_id)
    
    # Assert
    assert result == sample_user_metrics
    user_metrics_repository.db.query.assert_called_once_with(UserMetrics)

def test_user_metrics_get_by_user_id_with_platform(user_metrics_repository, sample_user_id, sample_user_metrics):
    # Setup
    platform = "twitter"
    filtered_metrics = [m for m in sample_user_metrics if m.platform == platform]
    user_metrics_repository.db.query().filter().filter().all.return_value = filtered_metrics
    
    # Execute
    result = user_metrics_repository.get_by_user_id(sample_user_id, platform=platform)
    
    # Assert
    assert result == filtered_metrics
    user_metrics_repository.db.query.assert_called_once_with(UserMetrics)

def test_user_metrics_get_by_user_id_with_date_range(user_metrics_repository, sample_user_id, sample_user_metrics):
    # Setup
    start_date = datetime.utcnow() - timedelta(days=3)
    end_date = datetime.utcnow()
    user_metrics_repository.db.query().filter().filter().filter().all.return_value = sample_user_metrics
    
    # Execute
    result = user_metrics_repository.get_by_user_id(
        sample_user_id, start_date=start_date, end_date=end_date
    )
    
    # Assert
    assert result == sample_user_metrics
    user_metrics_repository.db.query.assert_called_once_with(UserMetrics)

def test_user_metrics_get_by_user_id_with_metric_type(user_metrics_repository, sample_user_id, sample_user_metrics):
    # Setup
    metric_type = "followers"
    filtered_metrics = [m for m in sample_user_metrics if m.metric_type == metric_type]
    user_metrics_repository.db.query().filter().filter().all.return_value = filtered_metrics
    
    # Execute
    result = user_metrics_repository.get_by_user_id(sample_user_id, metric_type=metric_type)
    
    # Assert
    assert result == filtered_metrics
    user_metrics_repository.db.query.assert_called_once_with(UserMetrics)

def test_user_metrics_get_latest_by_platform(user_metrics_repository, sample_user_id, sample_user_metrics):
    # Setup
    platform = "twitter"
    metric_type = "followers"
    filtered_metric = next((m for m in sample_user_metrics if m.platform == platform and m.metric_type == metric_type), None)
    user_metrics_repository.db.query().filter().filter().filter().order_by().first.return_value = filtered_metric
    
    # Execute
    result = user_metrics_repository.get_latest_by_platform(sample_user_id, platform, metric_type)
    
    # Assert
    assert result == filtered_metric
    user_metrics_repository.db.query.assert_called_once_with(UserMetrics)

# ContentPerformanceRepository Tests
def test_content_performance_get_by_user_id(content_performance_repository, sample_user_id, sample_content_performance):
    # Setup
    content_performance_repository.db.query().filter().all.return_value = sample_content_performance
    
    # Execute
    result = content_performance_repository.get_by_user_id(sample_user_id)
    
    # Assert
    assert result == sample_content_performance
    content_performance_repository.db.query.assert_called_once_with(ContentPerformance)

def test_content_performance_get_by_user_id_with_platform(content_performance_repository, sample_user_id, sample_content_performance):
    # Setup
    platform = "twitter"
    filtered_performance = [p for p in sample_content_performance if p.platform == platform]
    content_performance_repository.db.query().filter().filter().all.return_value = filtered_performance
    
    # Execute
    result = content_performance_repository.get_by_user_id(sample_user_id, platform=platform)
    
    # Assert
    assert result == filtered_performance
    content_performance_repository.db.query.assert_called_once_with(ContentPerformance)

def test_content_performance_get_by_user_id_with_date_range(content_performance_repository, sample_user_id, sample_content_performance):
    # Setup
    start_date = datetime.utcnow() - timedelta(days=3)
    end_date = datetime.utcnow()
    content_performance_repository.db.query().filter().filter().filter().all.return_value = sample_content_performance
    
    # Execute
    result = content_performance_repository.get_by_user_id(
        sample_user_id, start_date=start_date, end_date=end_date
    )
    
    # Assert
    assert result == sample_content_performance
    content_performance_repository.db.query.assert_called_once_with(ContentPerformance)

def test_content_performance_get_by_user_id_with_content_type(content_performance_repository, sample_user_id, sample_content_performance):
    # Setup
    content_type = "image"
    filtered_performance = [p for p in sample_content_performance if p.content_type == content_type]
    content_performance_repository.db.query().filter().filter().all.return_value = filtered_performance
    
    # Execute
    result = content_performance_repository.get_by_user_id(sample_user_id, content_type=content_type)
    
    # Assert
    assert result == filtered_performance
    content_performance_repository.db.query.assert_called_once_with(ContentPerformance)

def test_content_performance_get_top_performing_content(content_performance_repository, sample_user_id, sample_content_performance):
    # Setup
    platform = "twitter"
    limit = 2
    sorted_performance = sorted(
        [p for p in sample_content_performance if p.platform == platform],
        key=lambda p: p.engagement_rate,
        reverse=True
    )[:limit]
    content_performance_repository.db.query().filter().filter().order_by().limit().all.return_value = sorted_performance
    
    # Execute
    result = content_performance_repository.get_top_performing_content(sample_user_id, platform, limit=limit)
    
    # Assert
    assert result == sorted_performance
    content_performance_repository.db.query.assert_called_once_with(ContentPerformance)
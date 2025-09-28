from typing import Generator, Any
from unittest.mock import MagicMock
import pytest
from sqlalchemy.orm import Session

from services.database.database import Base, get_db
from services.models.user_model import User
from services.models.scheduled_post_model import ScheduledPost
from services.models.analytics_models import PostEngagement, UserMetrics, ContentPerformance
from services.repositories.user_repository import UserRepository
from services.repositories.scheduled_post_repository import ScheduledPostRepository
from services.repositories.analytics_repository import (
    PostEngagementRepository,
    UserMetricsRepository,
    ContentPerformanceRepository
)

# Mock database session for testing
class MockDBSession:
    def __init__(self):
        self.db = MagicMock()
        self.db.query.return_value = self.db
        self.db.filter.return_value = self.db
        self.db.filter_by.return_value = self.db
        self.db.first.return_value = None
        self.db.all.return_value = []
        self.db.add.return_value = None
        self.db.commit.return_value = None
        self.db.refresh.return_value = None
        self.db.delete.return_value = None
        self.db.execute.return_value = MagicMock()
        self.db.scalar.return_value = None
    
    def get_db(self) -> Generator[Session, Any, None]:
        try:
            yield self.db
        finally:
            pass

# Repository test fixtures
@pytest.fixture
def mock_db_session() -> MockDBSession:
    return MockDBSession()

@pytest.fixture
def user_repository(mock_db_session: MockDBSession) -> UserRepository:
    return UserRepository(next(mock_db_session.get_db()))

@pytest.fixture
def scheduled_post_repository(mock_db_session: MockDBSession) -> ScheduledPostRepository:
    return ScheduledPostRepository(next(mock_db_session.get_db()))

@pytest.fixture
def post_engagement_repository(mock_db_session: MockDBSession) -> PostEngagementRepository:
    return PostEngagementRepository(next(mock_db_session.get_db()))

@pytest.fixture
def user_metrics_repository(mock_db_session: MockDBSession) -> UserMetricsRepository:
    return UserMetricsRepository(next(mock_db_session.get_db()))

@pytest.fixture
def content_performance_repository(mock_db_session: MockDBSession) -> ContentPerformanceRepository:
    return ContentPerformanceRepository(next(mock_db_session.get_db()))

# Mock dependency overrides for FastAPI testing
def get_test_db_override(mock_db_session: MockDBSession):
    def _get_test_db():
        return next(mock_db_session.get_db())
    return _get_test_db

def get_test_user_repository_override(user_repository: UserRepository):
    def _get_test_user_repository():
        return user_repository
    return _get_test_user_repository

def get_test_scheduled_post_repository_override(scheduled_post_repository: ScheduledPostRepository):
    def _get_test_scheduled_post_repository():
        return scheduled_post_repository
    return _get_test_scheduled_post_repository

def get_test_post_engagement_repository_override(post_engagement_repository: PostEngagementRepository):
    def _get_test_post_engagement_repository():
        return post_engagement_repository
    return _get_test_post_engagement_repository

def get_test_user_metrics_repository_override(user_metrics_repository: UserMetricsRepository):
    def _get_test_user_metrics_repository():
        return user_metrics_repository
    return _get_test_user_metrics_repository

def get_test_content_performance_repository_override(content_performance_repository: ContentPerformanceRepository):
    def _get_test_content_performance_repository():
        return content_performance_repository
    return _get_test_content_performance_repository
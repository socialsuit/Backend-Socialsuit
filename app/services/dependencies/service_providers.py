from fastapi import Depends
from sqlalchemy.orm import Session

from app.services.database.database import get_db
from app.services.dependencies.repository_providers import (
    get_user_repository,
    get_post_engagement_repository,
    get_user_metrics_repository,
    get_content_performance_repository
)
from app.services.analytics.services.data_analyzer_service import AnalyticsAnalyzerService
from app.services.analytics.services.data_collector_service import AnalyticsCollectorService
from app.services.analytics.services.chart_generator_service import ChartGeneratorService

# Analytics services providers
def get_analytics_analyzer_service(
    db: Session = Depends(get_db),
    user_repo = Depends(get_user_repository),
    post_engagement_repo = Depends(get_post_engagement_repository),
    user_metrics_repo = Depends(get_user_metrics_repository),
    content_performance_repo = Depends(get_content_performance_repository)
) -> AnalyticsAnalyzerService:
    """
    Dependency provider for AnalyticsAnalyzerService
    """
    return AnalyticsAnalyzerService(
        db=db,
        user_repository=user_repo,
        post_engagement_repository=post_engagement_repo,
        user_metrics_repository=user_metrics_repo,
        content_performance_repository=content_performance_repo
    )

def get_analytics_collector_service(
    db: Session = Depends(get_db),
    user_repo = Depends(get_user_repository),
    post_engagement_repo = Depends(get_post_engagement_repository),
    user_metrics_repo = Depends(get_user_metrics_repository),
    content_performance_repo = Depends(get_content_performance_repository)
) -> AnalyticsCollectorService:
    """
    Dependency provider for AnalyticsCollectorService
    """
    return AnalyticsCollectorService(
        db=db,
        user_repository=user_repo,
        post_engagement_repository=post_engagement_repo,
        user_metrics_repository=user_metrics_repo,
        content_performance_repository=content_performance_repo
    )

def get_chart_generator_service(
    analytics_analyzer_service = Depends(get_analytics_analyzer_service)
) -> ChartGeneratorService:
    """
    Dependency provider for ChartGeneratorService
    """
    return ChartGeneratorService(analyzer=analytics_analyzer_service)
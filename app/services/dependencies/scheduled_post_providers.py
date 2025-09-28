from fastapi import Depends
from sqlalchemy.orm import Session

from app.services.scheduled_post_service import ScheduledPostService
from app.services.dependencies.repository_providers import get_scheduled_post_repository, get_user_repository
from app.services.dependencies.external_services import get_db
from app.services.repositories.scheduled_post_repository import ScheduledPostRepository
from app.services.repositories.user_repository import UserRepository

def get_scheduled_post_service(
    scheduled_post_repository: ScheduledPostRepository = Depends(get_scheduled_post_repository),
    user_repository: UserRepository = Depends(get_user_repository)
) -> ScheduledPostService:
    """
    Dependency provider for ScheduledPostService.
    
    Args:
        scheduled_post_repository: Repository for scheduled post operations
        user_repository: Repository for user operations
        
    Returns:
        An instance of ScheduledPostService
    """
    return ScheduledPostService(
        scheduled_post_repository=scheduled_post_repository,
        user_repository=user_repository
    )
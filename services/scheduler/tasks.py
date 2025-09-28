"""
Celery tasks for Social Suit application.

This module contains background tasks for:
- Dispatching scheduled posts to social media platforms
- Refreshing social media platform tokens
"""

import logging
from celery import Celery
from datetime import datetime
from typing import Dict, Any

# Import the celery app from the main celery_app.py
from celery_app import celery_app

# Import scheduler functions
from app.services.scheduled_post_service import ScheduledPostService
from app.services.database.database import get_db_session
from app.services.repositories.user_repository import UserRepository
from app.services.repositories.scheduled_post_repository import ScheduledPostRepository
from app.services.repositories.platform_token_repository import PlatformTokenRepository

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="dispatch_scheduled_posts")
def dispatch_scheduled_posts(self) -> Dict[str, Any]:
    """
    Celery task to dispatch scheduled posts that are due for publishing.
    
    This task:
    1. Finds all pending scheduled posts that are due
    2. Attempts to publish them to their respective platforms
    3. Updates post status based on success/failure
    4. Returns summary of processed posts
    
    Returns:
        Dict containing task execution summary
    """
    try:
        logger.info("Starting dispatch_scheduled_posts task")
        
        # Get database session
        db_session = get_db_session()
        
        try:
            # Initialize repositories
            user_repo = UserRepository(db_session)
            scheduled_post_repo = ScheduledPostRepository(db_session)
            platform_token_repo = PlatformTokenRepository(db_session)
            
            # Initialize scheduler service
            scheduler_service = ScheduledPostService(
                user_repository=user_repo,
                scheduled_post_repository=scheduled_post_repo,
                platform_token_repository=platform_token_repo
            )
            
            # Process pending posts
            processed_count = scheduler_service.process_pending_posts()
            
            result = {
                "task": "dispatch_scheduled_posts",
                "status": "success",
                "processed_posts": processed_count,
                "timestamp": datetime.utcnow().isoformat(),
                "message": f"Successfully processed {processed_count} scheduled posts"
            }
            
            logger.info(f"dispatch_scheduled_posts completed: {result}")
            return result
            
        finally:
            db_session.close()
            
    except Exception as exc:
        logger.error(f"dispatch_scheduled_posts failed: {str(exc)}")
        
        # Retry the task with exponential backoff
        raise self.retry(
            exc=exc,
            countdown=60 * (2 ** self.request.retries),  # Exponential backoff
            max_retries=3
        )


@celery_app.task(bind=True, name="refresh_social_tokens")
def refresh_tokens(self) -> Dict[str, Any]:
    """
    Celery task to refresh expired social media platform tokens.
    
    This task:
    1. Finds all platform tokens that are near expiry
    2. Attempts to refresh them using platform APIs
    3. Updates token data in the database
    4. Returns summary of refreshed tokens
    
    Returns:
        Dict containing task execution summary
    """
    try:
        logger.info("Starting refresh_tokens task")
        
        # Get database session
        db_session = get_db_session()
        
        try:
            # Initialize repositories
            user_repo = UserRepository(db_session)
            scheduled_post_repo = ScheduledPostRepository(db_session)
            platform_token_repo = PlatformTokenRepository(db_session)
            
            # Initialize scheduler service
            scheduler_service = ScheduledPostService(
                user_repository=user_repo,
                scheduled_post_repository=scheduled_post_repo,
                platform_token_repository=platform_token_repo
            )
            
            # Get tokens that need refreshing (expire within 24 hours)
            tokens_to_refresh = platform_token_repo.get_tokens_expiring_soon(hours=24)
            
            refreshed_count = 0
            failed_count = 0
            
            for token in tokens_to_refresh:
                try:
                    # Attempt to refresh the token
                    # This would call the specific platform's token refresh API
                    success = scheduler_service.refresh_platform_token(token)
                    
                    if success:
                        refreshed_count += 1
                        logger.info(f"Successfully refreshed token for user {token.user_id}, platform {token.platform}")
                    else:
                        failed_count += 1
                        logger.warning(f"Failed to refresh token for user {token.user_id}, platform {token.platform}")
                        
                except Exception as token_exc:
                    failed_count += 1
                    logger.error(f"Error refreshing token for user {token.user_id}: {str(token_exc)}")
            
            result = {
                "task": "refresh_tokens",
                "status": "success",
                "refreshed_tokens": refreshed_count,
                "failed_tokens": failed_count,
                "total_processed": len(tokens_to_refresh),
                "timestamp": datetime.utcnow().isoformat(),
                "message": f"Refreshed {refreshed_count} tokens, {failed_count} failed"
            }
            
            logger.info(f"refresh_tokens completed: {result}")
            return result
            
        finally:
            db_session.close()
            
    except Exception as exc:
        logger.error(f"refresh_tokens failed: {str(exc)}")
        
        # Retry the task with exponential backoff
        raise self.retry(
            exc=exc,
            countdown=60 * (2 ** self.request.retries),  # Exponential backoff
            max_retries=3
        )


# Health check task for monitoring
@celery_app.task(name="health_check")
def health_check() -> Dict[str, Any]:
    """
    Simple health check task to verify Celery worker is functioning.
    
    Returns:
        Dict containing health status
    """
    return {
        "task": "health_check",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Celery worker is running normally"
    }
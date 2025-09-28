from datetime import datetime
import logging
from app.services.scheduler.dispatcher import dispatch_scheduled_posts
from app.services.database.database import get_db_session
from app.services.models.scheduled_post_model import ScheduledPost, PostStatus
from app.services.models.token_model import PlatformToken
from app.services.utils.logger_config import setup_logger
from app.services.utils.monitoring import update_scheduled_post_gauges

logger = setup_logger(__name__)

def get_user_tokens(db, user_id, platform):
    """
    Retrieve tokens for a specific user and platform
    
    Args:
        db: Database session
        user_id: User ID to fetch tokens for
        platform: Platform name (facebook, instagram, twitter, etc.)
        
    Returns:
        dict: Token information including access_token and platform-specific IDs
    """
    try:
        token = db.query(PlatformToken).filter(
            PlatformToken.user_id == user_id,
            PlatformToken.platform == platform
        ).first()
        
        if not token:
            logger.warning(f"[TOKEN_FETCH] No token found for user_id={user_id}, platform={platform}")
            return None
            
        # Build token dict based on platform
        token_dict = {"access_token": token.access_token}
        
        # Add platform-specific fields
        if platform == "facebook":
            # Extract page_id from channel_id if available
            if token.channel_id:
                token_dict["page_id"] = token.channel_id
        elif platform == "instagram":
            # Extract ig_user_id from channel_id if available
            if token.channel_id:
                token_dict["ig_user_id"] = token.channel_id
        elif platform == "twitter":
            # Twitter might store additional info in channel_id
            if token.channel_id:
                token_dict["user_id"] = token.channel_id
        elif platform == "linkedin":
            # LinkedIn might store organization ID in channel_id
            if token.channel_id:
                token_dict["organization_id"] = token.channel_id
        elif platform == "farcaster":
            # Farcaster needs specific token format
            if token.channel_id and "," in token.channel_id:
                signer_uuid, wallet_address = token.channel_id.split(",", 1)
                token_dict["signer_uuid"] = signer_uuid
                token_dict["wallet_address"] = wallet_address
                token_dict["signer_token"] = token.access_token
        
        return token_dict
        
    except Exception as e:
        logger.exception(f"[TOKEN_FETCH] Error fetching token for user_id={user_id}, platform={platform}: {e}")
        return None

async def beat_job():
    """
    Runs every X minutes: finds due scheduled posts and dispatches them.
    Runs inside Celery Beat.
    
    This is an async function that handles finding scheduled posts and dispatching them.
    """
    db = get_db_session()
    try:
        now = datetime.utcnow()

        posts = db.query(ScheduledPost).filter(
            ScheduledPost.status == PostStatus.pending,
            ScheduledPost.scheduled_time <= now
        ).all()

        logger.info(f"[BEAT_JOB] Found {len(posts)} scheduled posts to dispatch.")

        if posts:
            payload = []
            for post in posts:
                logger.info(f"[BEAT_JOB] Processing post ID: {post.id} — Platform: {post.platform} for user_id={post.user_id}")
                
                # Get user tokens for this platform
                user_token = get_user_tokens(db, post.user_id, post.platform)
                
                if not user_token:
                    logger.error(f"[BEAT_JOB] No valid token found for post ID: {post.id}, user_id={post.user_id}, platform={post.platform}")
                    # Mark as failed due to missing token
                    post.status = PostStatus.failed
                    if not post.post_payload:
                        post.post_payload = {}
                    post.post_payload["last_error"] = "No valid token found for this platform"
                    continue
                
                logger.info(f"[BEAT_JOB] Dispatching post ID: {post.id} — Platform: {post.platform}")
                
                payload.append({
                    "platform": post.platform,
                    "user_token": user_token,
                    "post_payload": post.post_payload,
                    "post_id": post.id  # Include the post ID for tracking
                })

                # Mark as in progress
                post.status = PostStatus.retry

            db.commit()
            logger.info(f"[BEAT_JOB] Committed status updates for {len(posts)} posts.")

            await dispatch_scheduled_posts(payload)  # This must also be async
            logger.info(f"[BEAT_JOB] Dispatch complete for batch.")

        else:
            logger.info("[BEAT_JOB] No pending posts at this time.")
            
        # Update monitoring metrics with post counts
        try:
            # Count posts by status
            pending_count = db.query(ScheduledPost).filter(ScheduledPost.status == PostStatus.pending).count()
            retry_count = db.query(ScheduledPost).filter(ScheduledPost.status == PostStatus.retry).count()
            failed_count = db.query(ScheduledPost).filter(ScheduledPost.status == PostStatus.failed).count()
            completed_count = db.query(ScheduledPost).filter(ScheduledPost.status == PostStatus.completed).count()
            
            # Update Prometheus gauges
            update_scheduled_post_gauges(pending_count, retry_count, failed_count, completed_count)
            
            logger.info(f"[BEAT_JOB] Updated metrics - Pending: {pending_count}, Retry: {retry_count}, Failed: {failed_count}, Completed: {completed_count}")
        except Exception as e:
            logger.error(f"[BEAT_JOB] Failed to update metrics: {e}")

    except Exception as e:
        logger.exception(f"[BEAT_JOB] Exception occurred: {e}")

    finally:
        db.close()
        logger.info("[BEAT_JOB] DB session closed.")
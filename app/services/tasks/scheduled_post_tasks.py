import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from app.services.scheduled_post_service import ScheduledPostService
from app.services.models.scheduled_post_model import PostStatus
from app.services.utils.logger_config import setup_logger

logger = setup_logger("scheduled_post_tasks")

class ScheduledPostTaskProcessor:
    """Task processor for scheduled posts"""
    
    def __init__(self, scheduled_post_service: ScheduledPostService):
        self.scheduled_post_service = scheduled_post_service
        self.running = False
        self.check_interval = 60  # seconds
    
    async def start(self):
        """Start the task processor"""
        if self.running:
            logger.warning("Task processor is already running")
            return
        
        self.running = True
        logger.info("Starting scheduled post task processor")
        
        while self.running:
            try:
                # Process pending posts
                published_count = self.scheduled_post_service.process_pending_posts()
                if published_count > 0:
                    logger.info(f"Published {published_count} scheduled posts")
                
                # Sleep for the check interval
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in scheduled post task processor: {str(e)}")
                # Sleep for a shorter interval on error
                await asyncio.sleep(10)
    
    def stop(self):
        """Stop the task processor"""
        logger.info("Stopping scheduled post task processor")
        self.running = False


async def start_scheduled_post_processor(scheduled_post_service: ScheduledPostService) -> ScheduledPostTaskProcessor:
    """Start the scheduled post processor as a background task"""
    processor = ScheduledPostTaskProcessor(scheduled_post_service)
    
    # Start the processor in the background
    asyncio.create_task(processor.start())
    
    return processor
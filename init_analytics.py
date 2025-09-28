# init_analytics.py
import asyncio
import sys
from services.analytics.init_analytics_db import init_analytics_db, generate_sample_analytics_data
from services.utils.logger_config import setup_logger

# Set up logger
logger = setup_logger("init_analytics_script")

async def main():
    if len(sys.argv) > 1:
        # If user ID is provided, generate data for that user only
        user_id = sys.argv[1]
        days_back = 30  # Default to 30 days
        
        # If days_back is provided as second argument
        if len(sys.argv) > 2:
            try:
                days_back = int(sys.argv[2])
            except ValueError:
                logger.error(f"Invalid days_back value: {sys.argv[2]}. Using default of 30 days.")
        
        logger.info(f"Generating sample analytics data for user {user_id} for the past {days_back} days")
        result = await generate_sample_analytics_data(user_id, days_back)
        if result:
            logger.info(f"Successfully generated sample analytics data for user {user_id}")
        else:
            logger.error(f"Failed to generate sample analytics data for user {user_id}")
    else:
        # Initialize analytics database for all users
        logger.info("Initializing analytics database for all users")
        await init_analytics_db()
        logger.info("Analytics database initialization completed")

if __name__ == "__main__":
    asyncio.run(main())
# services/analytics/init_analytics_db.py
import asyncio
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.services.database.database import get_db_session
from app.services.models.user_model import User
from app.services.models.analytics_model import (
    PostEngagement, 
    UserMetrics, 
    ContentPerformance,
    EngagementType
)
from app.services.analytics.data_collector import AnalyticsCollector
from app.services.utils.logger_config import setup_logger

# Set up logger
logger = setup_logger("init_analytics_db")

async def generate_sample_analytics_data(user_id: str, days_back: int = 30):
    """Generate sample analytics data for a user for testing purposes"""
    logger.info(f"Generating sample analytics data for user {user_id} for the past {days_back} days")
    
    db = get_db_session()
    try:
        # Check if user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"User {user_id} not found")
            return False
        
        # Create analytics collector
        collector = AnalyticsCollector(db)
        
        # Generate sample data for each day
        for day in range(days_back, 0, -1):
            date = datetime.now() - timedelta(days=day)
            
            # Generate sample post engagements
            platforms = ["facebook", "instagram", "twitter", "linkedin", "tiktok"]
            for platform in platforms:
                # Generate 1-3 posts per day per platform
                for _ in range(random.randint(1, 3)):
                    post_id = f"{platform}_post_{date.strftime('%Y%m%d')}_{random.randint(1000, 9999)}"
                    
                    # Generate engagements for this post
                    for engagement_type in EngagementType:
                        # Random number of engagements for each type
                        engagement_count = random.randint(5, 100)
                        
                        # Create engagement records
                        for _ in range(engagement_count):
                            engagement = PostEngagement(
                                user_id=user_id,
                                platform=platform,
                                post_id=post_id,
                                engagement_type=engagement_type,
                                engagement_time=date + timedelta(hours=random.randint(0, 23), minutes=random.randint(0, 59)),
                                source_country=random.choice(["US", "UK", "CA", "AU", "DE", "FR", "JP"]),
                                source_device=random.choice(["mobile", "desktop", "tablet"]),
                                metadata={
                                    "user_age_range": random.choice(["18-24", "25-34", "35-44", "45-54", "55+"]),
                                    "user_gender": random.choice(["male", "female", "other"]),
                                }
                            )
                            db.add(engagement)
                    
                    # Create content performance record for this post
                    content_type = random.choice(["image", "video", "carousel", "text", "link"])
                    content_performance = ContentPerformance(
                        user_id=user_id,
                        platform=platform,
                        post_id=post_id,
                        content_type=content_type,
                        posted_at=date,
                        reach=random.randint(500, 5000),
                        impressions=random.randint(600, 6000),
                        engagement_rate=round(random.uniform(1.0, 15.0), 2),
                        likes=random.randint(50, 500),
                        comments=random.randint(5, 100),
                        shares=random.randint(2, 50),
                        saves=random.randint(10, 200),
                        clicks=random.randint(20, 300),
                        video_views=random.randint(300, 3000) if content_type == "video" else 0,
                        video_completion_rate=round(random.uniform(20.0, 90.0), 2) if content_type == "video" else 0,
                        metadata={
                            "hashtags": [f"#{word}" for word in random.sample(["trending", "viral", "marketing", "socialmedia", "content", "digital", "growth"], k=random.randint(1, 5))],
                            "post_length": random.randint(50, 500),
                            "has_media": content_type != "text",
                            "media_count": random.randint(1, 5) if content_type == "carousel" else 1 if content_type in ["image", "video"] else 0,
                            "posting_time": date.strftime("%H:%M"),
                        }
                    )
                    db.add(content_performance)
                
                # Create daily user metrics for this platform
                user_metrics = UserMetrics(
                    user_id=user_id,
                    platform=platform,
                    date=date.date(),
                    followers=random.randint(1000, 10000),
                    following=random.randint(500, 2000),
                    posts_count=random.randint(50, 500),
                    profile_views=random.randint(100, 1000),
                    website_clicks=random.randint(10, 100),
                    reach=random.randint(1000, 10000),
                    impressions=random.randint(2000, 20000),
                    engagement_rate=round(random.uniform(1.0, 10.0), 2),
                    audience_demographics={
                        "age_ranges": {
                            "18-24": round(random.uniform(10.0, 30.0), 2),
                            "25-34": round(random.uniform(20.0, 40.0), 2),
                            "35-44": round(random.uniform(15.0, 30.0), 2),
                            "45-54": round(random.uniform(5.0, 20.0), 2),
                            "55+": round(random.uniform(5.0, 15.0), 2)
                        },
                        "gender": {
                            "male": round(random.uniform(30.0, 70.0), 2),
                            "female": round(random.uniform(30.0, 70.0), 2),
                            "other": round(random.uniform(0.0, 5.0), 2)
                        },
                        "top_locations": [
                            {"country": "US", "percentage": round(random.uniform(20.0, 50.0), 2)},
                            {"country": "UK", "percentage": round(random.uniform(5.0, 20.0), 2)},
                            {"country": "CA", "percentage": round(random.uniform(5.0, 15.0), 2)},
                            {"country": "AU", "percentage": round(random.uniform(3.0, 10.0), 2)},
                            {"country": "DE", "percentage": round(random.uniform(2.0, 8.0), 2)}
                        ]
                    }
                )
                db.add(user_metrics)
        
        # Commit all changes
        db.commit()
        logger.info(f"Successfully generated sample analytics data for user {user_id}")
        return True
    
    except IntegrityError as e:
        db.rollback()
        logger.error(f"IntegrityError while generating sample data: {str(e)}")
        return False
    except Exception as e:
        db.rollback()
        logger.error(f"Error generating sample data: {str(e)}")
        return False
    finally:
        db.close()

async def init_analytics_db():
    """Initialize the analytics database with sample data"""
    logger.info("Initializing analytics database with sample data")
    
    # Get all users
    db = get_db_session()
    try:
        users = db.query(User).all()
        for user in users:
            await generate_sample_analytics_data(user.id)
    except Exception as e:
        logger.error(f"Error initializing analytics database: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    # Run the initialization script
    asyncio.run(init_analytics_db())
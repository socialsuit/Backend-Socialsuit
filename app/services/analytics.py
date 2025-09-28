from typing import Dict, List, Union
from datetime import datetime, timedelta
import random

def get_insights(platform: str = "all") -> Dict[str, Union[Dict, List, str]]:
    """
    Advanced analytics for all social platforms with:
    - Platform-specific metrics
    - Comparative analysis
    - AI-powered recommendations
    - Real-time data simulation
    
    Args:
        platform: Social platform (instagram/twitter/youtube/all)
    
    Returns:
        Comprehensive insights dictionary
    """
    # Simulated real-time data (in production, this would come from APIs/database)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Base data structure
    insights = {
        "timestamp": timestamp,
        "platform": platform,
        "followers_growth": {
            "this_week": f"+{random.randint(50, 200)}",
            "last_week": f"+{random.randint(40, 180)}",
            "platform_comparison": {}
        },
        "engagement_metrics": {
            "average_engagement_rate": f"{random.uniform(2.5, 8.5):.1f}%",
            "best_performing_type": random.choice(["reels", "posts", "stories", "videos"])
        },
        "competitor_analysis": [],
        "ai_recommendations": []
    }

    # Platform-specific data
    platforms = ["instagram", "twitter", "youtube", "linkedin", "tiktok"] if platform == "all" else [platform]
    
    for platform in platforms:
        # Platform comparison data
        insights["followers_growth"]["platform_comparison"][platform] = {
            "growth": f"+{random.randint(30, 150)}",
            "trend": random.choice(["↑ improving", "↓ declining", "→ stable"])
        }

        # Competitor benchmarks (simulated)
        insights["competitor_analysis"].extend([
            {
                "platform": platform,
                "competitor": f"Competitor {chr(65+i)}",  # A, B, C...
                "growth": f"{random.randint(5, 15)}%",
                "gap": random.choice(["ahead", "behind", "on par"])
            } for i in range(3)
        ])

        # AI recommendations
        optimal_time = f"{random.randint(1, 12)} {random.choice(['AM', 'PM'])}"
        insights["ai_recommendations"].append({
            "platform": platform,
            "tip": f"Post {random.choice(['short videos', 'carousels', 'polls'])} at {optimal_time}",
            "confidence": f"{random.randint(70, 95)}%"
        })

    # Top performing content simulation
    content_types = ["post", "reel", "tweet", "video", "story"]
    insights["top_performing_content"] = {
        "id": random.randint(1, 100),
        "type": random.choice(content_types),
        "engagement": f"{random.randint(1, 10)}.{random.randint(0, 9)}K interactions",
        "platform": random.choice(platforms)
    }

    return insights
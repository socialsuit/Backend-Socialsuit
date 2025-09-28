from datetime import datetime
import uuid
from typing import Dict, Union

def run_ab_test(
    content_a: str,
    content_b: str,
    test_name: str = None,
    target_metric: str = "engagement_rate",
    audience_percentage: float = 0.5
) -> Dict[str, Union[str, Dict]]:
    """
    Advanced A/B testing function for Social Suit with complete test tracking
    
    Args:
        content_a: First content variant
        content_b: Second content variant
        test_name: Optional test identifier
        target_metric: Primary metric to measure (engagement_rate/conversions/clicks)
        audience_percentage: Traffic split between variants (0.1 to 0.9)
    
    Returns:
        Complete test configuration with metadata
    """
    # Validate inputs
    if not 0.1 <= audience_percentage <= 0.9:
        raise ValueError("Audience percentage must be between 0.1 and 0.9")
    
    if not target_metric in ["engagement_rate", "conversions", "clicks"]:
        raise ValueError("Invalid target metric specified")
    
    # Generate test ID if not provided
    test_id = test_name or f"ABTest_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
    
    return {
        "test_id": test_id,
        "status": "created",
        "start_time": datetime.now().isoformat(),
        "target_metric": target_metric,
        "audience_split": {
            "A": audience_percentage,
            "B": round(1 - audience_percentage, 2)
        },
        "variants": {
            "A": {
                "content": content_a,
                "performance": {
                    "impressions": 0,
                    target_metric: 0,
                    "confidence_level": None
                }
            },
            "B": {
                "content": content_b,
                "performance": {
                    "impressions": 0,
                    target_metric: 0,
                    "confidence_level": None
                }
            }
        },
        "metadata": {
            "platform": "SocialSuit",
            "version": "2.1",
            "owner": "automated_testing_system"
        }
    }
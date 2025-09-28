import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from services.smart_schedule import smart_schedule

def test_smart_schedule_with_multiple_inputs():
    test_cases = [
        {"platform": "instagram", "content_type": "post", "timezone": "UTC"},            # ✅ valid
        {"platform": "facebook", "content_type": "story", "timezone": "Asia/Karachi"},   # ✅ valid
        {"platform": "myspace", "content_type": "post", "timezone": "UTC"},              # ❌ invalid platform
        {"platform": "linkedin", "content_type": "dance", "timezone": "UTC"},            # ❌ invalid content_type
        {"platform": "twitter", "content_type": "post", "timezone": "MoonTime"},         # ❌ invalid timezone
        {"platform": "", "content_type": "post", "timezone": "UTC"},                     # ❌ empty platform
    ]

    for case in test_cases:
        print(f"\n📥 Testing: {case}")
        try:
            result = smart_schedule(
                platform=case["platform"],
                content_type=case["content_type"],
                timezone=case["timezone"]
            )
            print("✅ Success:", result)
        except Exception as e:
            print(f"❌ Error: ({type(e).__name__}) {str(e)}")

if __name__ == "__main__":
    test_smart_schedule_with_multiple_inputs()



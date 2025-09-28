# services/tests/test_analytics.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.services.analytics import get_insights

result = get_insights("instagram")
print("Analytics Summary:\n", result)

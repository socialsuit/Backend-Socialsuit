# services/tests/test_ab_testing.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from services.ab_testing import run_ab_test

def test_run_ab_test():
    result = run_ab_test("Post A content", "Post B content", test_name="Header Test")
    print("A/B Test Result:", result)


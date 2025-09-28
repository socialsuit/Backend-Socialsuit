# services/tests/test_post_recycler.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.post_recycler import recycle_post

def test_recycle_post():
    old_post = "Join our webinar about Web3!"
    recycled_post = recycle_post(old_post)
    print("♻️ Recycled Post:", recycled_post)

# 👇 This line ensures it runs
test_recycle_post()


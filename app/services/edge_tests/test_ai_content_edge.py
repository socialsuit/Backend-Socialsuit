import sys
import os
import pytest
from fastapi.testclient import TestClient

# Add root dir to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from main import app

client = TestClient(app)

# Add test functions below (jaise pehle likha tha)


# 1. Empty prompt
def test_empty_prompt():
    response = client.get("/api/v1/generate?prompt=&style=casual&hashtags=2")
    assert response.status_code == 422  # Validation error

# 2. Prompt too shore
def test_short_prompt():
    response = client.get("/api/v1/generate?prompt=Hi&style=casual&hashtags=2")
    assert response.status_code == 422

# 3. Prompt too long
def test_long_prompt():
    long_prompt = "a" * 501
    response = client.get(f"/api/v1/generate?prompt={long_prompt}&style=casual&hashtags=2")
    assert response.status_code == 422

# 4. Invalid style
def test_invalid_style():
    response = client.get("/api/v1/generate?prompt=test&style=funky&hashtags=2")
    assert response.status_code == 422

# 5. Negative hashtags
def test_negative_hashtags():
    response = client.get("/api/v1/generate?prompt=test caption&style=casual&hashtags=-3")
    assert response.status_code == 422

# 6. To
def test_excessive_hashtags():
    response = client.get("/api/v1/generate?prompt=test caption&style=casual&hashtags=15")
    assert response.status_code == 422

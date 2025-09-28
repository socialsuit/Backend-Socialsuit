import sys
import os

# Set path to root where main.py exists
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_home():
    response = client.get("/")
    assert response.status_code == 200
    assert "msg" in response.json()

def test_generate_caption():
    response = client.get("/generate", params={"prompt": "Boost engagement"})
    assert response.status_code == 200
    assert isinstance(response.json(), dict)

def test_customize_post():
    response = client.post("/customize", json={
        "content": "Check out our new tool!",
        "platform": "instagram"
    })
    assert response.status_code == 200

def test_reply():
    response = client.post("/reply", params={"message": "What's the price?"})
    assert response.status_code == 200

def test_ab_test():
    response = client.post("/ab_test", json={
        "content_a": "Sale 20% Off!",
        "content_b": "Limited Time Offer!",
        "test_name": "promo_test",
        "target_metric": "CTR",
        "audience_percentage": 0.5
    })
    assert response.status_code == 200

def test_recycle():
    response = client.post("/recycle", params={
        "post_id": "123",
        "platforms": "all"
    })
    assert response.status_code == 200

def test_schedule():
    response = client.get("/schedule", params={
        "platform": "instagram",
        "content_type": "post",
        "timezone": "Asia/Karachi"
    })
    assert response.status_code == 200

def test_analytics():
    response = client.get("/analytics", params={"platform": "all"})
    assert response.status_code == 200

def test_generate_thumbnail():
    response = client.post("/api/v1/generate-thumbnail", json={
        "prompt" : "AI tools",
        "platform": "instagram",
        "logo_base64" : None
    })
    assert response.status_code == 200
    assert isinstance(response.json(), dict)

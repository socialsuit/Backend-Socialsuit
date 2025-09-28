import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_valid_recycle():
    response = client.post("/api/v1/recycle", json={
        "platform": "facebook",
        "post_id": "12345"
    })
    assert response.status_code == 200
    assert "recycled" in response.json()

def test_missing_post_id():
    response = client.post("/api/v1/recycle", json={
        "platform": "facebook"
    })
    assert response.status_code == 422

def test_invalid_platform():
    response = client.post("/api/v1/recycle", json={
        "platform": "orkut",
        "post_id": "12345"
    })
    assert response.status_code == 400
    assert "Unsupported platform" in response.json()["detail"]

def test_empty_post_id():
    response = client.post("/api/v1/recycle", json={
        "platform": "facebook",
        "post_id": ""
    })
    assert response.status_code == 400
    assert "Post ID cannot be empty" in response.json()["detail"]

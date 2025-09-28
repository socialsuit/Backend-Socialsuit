import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_valid_schedule():
    response = client.get("/api/v1/schedule?platform=facebook&content_type=post&timezone=UTC")
    assert response.status_code == 200
    assert "optimal_time" in response.json()

def test_missing_platform():
    response = client.get("/api/v1/schedule?content_type=post&timezone=UTC")
    assert response.status_code == 422  # missing required query param

def test_invalid_platform():
    response = client.get("/api/v1/schedule?platform=myspace&content_type=post&timezone=UTC")
    assert response.status_code == 400
    assert "Invalid platform" in response.json()["detail"]

def test_invalid_timezone():
    response = client.get("/api/v1/schedule?platform=facebook&content_type=post&timezone=MoonTime")
    assert response.status_code == 400
    assert "Invalid timezone" in response.json()["detail"]

def test_with_audience_location():
    response = client.get("/api/v1/schedule?platform=facebook&audience_location=pakistan")
    assert response.status_code == 200
    assert "optimal_time" in response.json()
    assert response.json()["location_aware"] is True

def test_empty_platform():
    response = client.get("/api/v1/schedule?platform=&timezone=UTC")
    assert response.status_code == 422  # platform is empty string, FastAPI considers this invalid input


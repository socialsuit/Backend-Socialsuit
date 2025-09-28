# tests/test_analytics_api.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from app.services.database.database import Base, get_db
from app.services.models.user_model import User
from app.services.models.analytics_model import PostEngagement, UserMetrics, ContentPerformance
from app.services.analytics.init_analytics_db import generate_sample_analytics_data

import uuid
import asyncio

# Create test database
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the get_db dependency
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Test client
client = TestClient(app)

@pytest.fixture(scope="module")
def setup_test_db():
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create test user
    db = TestingSessionLocal()
    test_user_id = str(uuid.uuid4())
    test_user = User(
        id=test_user_id,
        email="test@example.com",
        hashed_password="hashed_password",
        wallet_address="0x123456789",
        network="ethereum",
        is_verified=True
    )
    db.add(test_user)
    db.commit()
    
    # Generate sample analytics data
    asyncio.run(generate_sample_analytics_data(test_user_id, days_back=7))
    
    yield test_user_id
    
    # Clean up
    Base.metadata.drop_all(bind=engine)

def test_get_analytics_overview(setup_test_db):
    user_id = setup_test_db
    response = client.get(f"/api/v1/analytics/overview/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert "platforms" in data
    assert "total_followers" in data
    assert "total_engagement" in data
    assert "growth_rate" in data

def test_get_platform_insights(setup_test_db):
    user_id = setup_test_db
    platforms = ["facebook", "instagram", "twitter", "linkedin", "tiktok"]
    
    for platform in platforms:
        response = client.get(f"/api/v1/analytics/platform/{user_id}/{platform}")
        assert response.status_code == 200
        data = response.json()
        assert "platform" in data
        assert data["platform"] == platform
        assert "metrics" in data
        assert "top_content" in data
        assert "audience" in data

def test_get_chart_data(setup_test_db):
    user_id = setup_test_db
    chart_types = ["time_series", "platform_comparison", "engagement_breakdown", 
                  "content_performance", "best_times", "content_type"]
    
    for chart_type in chart_types:
        response = client.get(f"/api/v1/analytics/visualization/{user_id}/{chart_type}")
        assert response.status_code == 200
        data = response.json()
        
        if chart_type == "time_series":
            assert "labels" in data
            assert "datasets" in data
        elif chart_type == "platform_comparison":
            assert "labels" in data
            assert "datasets" in data
        elif chart_type == "engagement_breakdown":
            assert "labels" in data
            assert "datasets" in data
        elif chart_type == "content_performance":
            assert "labels" in data
            assert "datasets" in data
        elif chart_type == "best_times":
            assert "labels" in data
            assert "datasets" in data
        elif chart_type == "content_type":
            assert "labels" in data
            assert "datasets" in data

def test_get_recommendations(setup_test_db):
    user_id = setup_test_db
    response = client.get(f"/api/v1/analytics/recommendations/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert "content_recommendations" in data
    assert "posting_recommendations" in data
    assert "platform_specific" in data

def test_collect_analytics(setup_test_db):
    user_id = setup_test_db
    response = client.post(f"/api/v1/analytics/collect/{user_id}?background=false")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "success" in data
    assert data["success"] == True

def test_get_comparative_analytics(setup_test_db):
    user_id = setup_test_db
    response = client.get(f"/api/v1/analytics/comparative/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert "platforms" in data
    assert "metrics" in data
    assert "best_performing" in data
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_abtesting():
    response = client.post("/ab_test", json={
        "content_a": "Caption for A",
        "content_b": "Caption for B",
        "test_name": "Test Campaign 1",
        "target_metric": "engagement_rate",
        "audience_percentage": 0.5
    })
    assert response.status_code == 200
    data = response.json()
    assert "test_id" in data
    assert data["status"] in ["running", "started"]

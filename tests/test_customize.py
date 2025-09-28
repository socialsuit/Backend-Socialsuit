import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_customize():
    response = client.post("/customize", json={"content": "test", "platform": "instagram"})
    assert response.status_code == 200

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_recycle():
    response = client.post("/recycle", json={"post_id": "123"})
    assert response.status_code == 200 or response.status_code == 422

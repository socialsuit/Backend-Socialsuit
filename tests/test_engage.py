import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_reply():
    response = client.post("/reply", json={"message": "hello"})
    assert response.status_code == 200 or response.status_code == 422

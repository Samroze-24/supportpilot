"""Test setup: isolated SQLite DB + trained model (if missing)."""
import os
import sys

# Point the app at a throwaway test DB BEFORE importing app modules.
TEST_DB = "/tmp/test_supportpilot.db"
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
import train_model  # noqa: E402

MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model.pkl")
if not os.path.exists(MODEL_PATH):
    train_model.main()


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Create a fresh workspace+owner per test, return (headers, user, token)."""
    import uuid

    suffix = uuid.uuid4().hex[:8]
    email = f"owner-{suffix}@test.store"
    r = client.post(
        "/auth/signup",
        json={"name": "Test Owner", "email": email, "password": "owner123", "workspace_name": f"Test Store {suffix}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    return {"Authorization": f"Bearer {data['access_token']}"}, data["user"], data["access_token"]

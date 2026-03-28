"""Integration test configuration — runs against the live deployment."""
import os
import uuid
import pytest
import httpx

BASE_URL = os.getenv("RELIC_BASE_URL", "http://localhost")
ADMIN_KEY = os.getenv("RELIC_ADMIN_KEY", "09d85e5f91316a66233d97e1b5936399")


@pytest.fixture
def http():
    """httpx client against the live deployment."""
    with httpx.Client(
        base_url=BASE_URL,
        timeout=15,
        follow_redirects=True,
        headers={"User-Agent": "curl/7.68.0"},
    ) as client:
        yield client


@pytest.fixture
def admin_key():
    return ADMIN_KEY


@pytest.fixture
def admin_headers():
    return {"X-Client-Key": ADMIN_KEY}


@pytest.fixture
def client_key():
    """A fresh unique client key (not registered)."""
    return uuid.uuid4().hex


@pytest.fixture
def registered_client(http):
    """Register a fresh client. Returns (key, public_id)."""
    key = uuid.uuid4().hex
    resp = http.post("/api/v1/client/register", headers={"X-Client-Key": key})
    assert resp.status_code == 200
    return key, resp.json()["public_id"]


@pytest.fixture
def test_file_content():
    return b"Hello, World! This is a test relic."


@pytest.fixture
def created_relic(http, registered_client):
    """Create a public relic. Cleans up after the test."""
    key, _ = registered_client
    resp = http.post(
        "/api/v1/relics",
        headers={"X-Client-Key": key},
        data={"name": "Test Relic", "access_level": "public"},
        files={"file": ("test.txt", b"Hello, World! This is a test relic.", "text/plain")},
    )
    assert resp.status_code == 200
    relic_id = resp.json()["id"]
    yield {"id": relic_id, "data": resp.json(), "client_key": key}
    http.delete(f"/api/v1/relics/{relic_id}", headers={"X-Client-Key": key})

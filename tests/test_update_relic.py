"""Integration tests for relic update endpoint."""
import uuid
import pytest
from conftest import ADMIN_KEY

ADMIN_HEADERS = {"X-Client-Key": ADMIN_KEY}


@pytest.fixture
def owned_relic(http, registered_client):
    """Create a relic owned by a registered client. Cleans up after."""
    key, _ = registered_client
    resp = http.post(
        "/api/v1/relics",
        headers={"X-Client-Key": key},
        data={"name": "Original Name", "access_level": "public"},
        files={"file": ("test.txt", b"content", "text/plain")},
    )
    relic_id = resp.json()["id"]
    yield relic_id, key
    http.delete(f"/api/v1/relics/{relic_id}", headers={"X-Client-Key": key})


@pytest.mark.integration
def test_update_relic_permissions(http, owned_relic):
    """Only owner or admin can update."""
    relic_id, owner_key = owned_relic
    other_key = uuid.uuid4().hex
    http.post("/api/v1/client/register", headers={"X-Client-Key": other_key})

    # No auth → 401
    assert http.put(f"/api/v1/relics/{relic_id}", json={"name": "x"}).status_code == 401

    # Non-owner → 403
    assert http.put(
        f"/api/v1/relics/{relic_id}",
        headers={"X-Client-Key": other_key},
        json={"name": "Hacked"},
    ).status_code == 403

    # Owner → 200
    resp = http.put(
        f"/api/v1/relics/{relic_id}",
        headers={"X-Client-Key": owner_key},
        json={"name": "Updated by Owner"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated by Owner"
    assert resp.json()["can_edit"] is True


@pytest.mark.integration
def test_update_relic_fields(http, owned_relic):
    """Various fields can be updated."""
    relic_id, owner_key = owned_relic

    resp = http.put(
        f"/api/v1/relics/{relic_id}",
        headers={"X-Client-Key": owner_key},
        json={
            "name": "New Name",
            "content_type": "text/markdown",
            "access_level": "private",
            "expires_in": "24h",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "New Name"
    assert data["content_type"] == "text/markdown"
    assert data["access_level"] == "private"
    assert data["expires_at"] is not None


@pytest.mark.integration
def test_admin_update_relic(http, owned_relic):
    """Admin can update any relic."""
    relic_id, _ = owned_relic

    resp = http.put(
        f"/api/v1/relics/{relic_id}",
        headers=ADMIN_HEADERS,
        json={"name": "Admin Edited"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Admin Edited"
    assert resp.json()["can_edit"] is True

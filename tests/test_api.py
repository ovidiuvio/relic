"""Tests for the relic API endpoints."""
import pytest
from io import BytesIO


@pytest.mark.unit
def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.unit
def test_create_relic(client):
    """Test creating a new relic."""
    content = b"Hello, World!"

    response = client.post(
        "/api/v1/relics",
        data={
            "name": "Test Relic",
            "language_hint": "text",
            "access_level": "public"
        },
        files={"file": ("test.txt", BytesIO(content), "text/plain")}
    )

    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "url" in data
    # assert data["version"] == 1 # Versioning removed in new API


@pytest.mark.unit
def test_get_relic(client):
    """Test retrieving a relic."""
    # Create a relic first
    create_response = client.post(
        "/api/v1/relics",
        data={"name": "Test Relic"},
        files={"file": ("test.txt", BytesIO(b"Test content"), "text/plain")}
    )
    relic_id = create_response.json()["id"]
    # Get the relic
    response = client.get(f"/api/v1/relics/{relic_id}")

    assert response.status_code == 200
    relic   = response.json()
    assert relic["id"] == relic_id
    assert relic["name"] == "Test Relic"
    assert relic["access_level"] == "public"

@pytest.mark.unit
def test_get_nonexistent_relic(client):
    """Test getting a relic that doesn't exist."""
    response = client.get("/api/v1/relics/nonexistent")
    assert response.status_code == 404


@pytest.mark.unit
def test_fork_relic(client):
    """Test forking a relic (new lineage)."""
    # Create original relic
    create_response = client.post(
        "/api/v1/relics",
        data={"name": "Original"},
        files={"file": ("test.txt", BytesIO(b"Original content"), "text/plain")}
    )
    original_id = create_response.json()["id"]

    # Fork the relic
    fork_response = client.post(
        f"/api/v1/relics/{original_id}/fork",
        files={"file": ("test.txt", BytesIO(b"Forked content"), "text/plain")}
    )

    assert fork_response.status_code == 200
    forked = fork_response.json()
    # assert forked["version"] == 1  # New lineage starts at 1
    assert forked["fork_of"] == original_id


@pytest.mark.unit
def test_list_relics(client):
    """Test listing recent relics."""
    # Create a few relics
    for i in range(3):
        client.post(
            "/api/v1/relics",
            data={"name": f"Relic {i}"},
            files={"file": (f"test{i}.txt", BytesIO(b"Content"), "text/plain")}
        )

    # List relics
    response = client.get("/api/v1/relics?limit=10")

    assert response.status_code == 200
    data = response.json()
    assert "relics" in data
    # assert "total" in data # Total is not in RelicListResponse anymore
    assert len(data["relics"]) >= 3


@pytest.mark.unit
def test_get_raw_content(client):
    """Test getting raw relic content."""
    content = b"Raw content here"

    # Create relic
    create_response = client.post(
        "/api/v1/relics",
        data={"name": "Raw Test"},
        files={"file": ("test.txt", BytesIO(content), "text/plain")}
    )
    relic_id = create_response.json()["id"]
    # Get raw
    response = client.get(f"/api/v1/relics/{relic_id}/raw") # Assuming raw endpoint is now here based on router

    assert response.status_code == 200
    assert response.content == content


@pytest.mark.unit
def test_delete_relic(client):
    """Test deleting a relic."""
    # Create client key
    client_key = "test-client-key"

    # Create relic with client key
    create_response = client.post(
        "/api/v1/relics",
        data={"name": "To Delete"},
        files={"file": ("test.txt", BytesIO(b"Content"), "text/plain")},
        headers={"X-Client-Key": client_key}
    )
    relic_id = create_response.json()["id"]

    # Delete relic
    delete_response = client.delete(
        f"/api/v1/relics/{relic_id}",
        headers={"X-Client-Key": client_key}
    )

    assert delete_response.status_code == 200

    # Verify relic is deleted (should be 404)
    get_response = client.get(f"/api/v1/relics/{relic_id}")
    assert get_response.status_code == 404

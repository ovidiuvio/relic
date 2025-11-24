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
    assert data["version"] == 1


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
def test_edit_relic(client):
    """Test editing a relic (creating new version)."""
    # Create original relic
    create_response = client.post(
        "/api/v1/relics",
        data={"name": "Original"},
        files={"file": ("test.txt", BytesIO(b"Original content"), "text/plain")}
    )
    original_id = create_response.json()["id"]

    # Edit the relic
    edit_response = client.post(
        f"/api/v1/relics/{original_id}/edit",
        files={"file": ("test.txt", BytesIO(b"Updated content"), "text/plain")}
    )

    assert edit_response.status_code == 200
    new_relic = edit_response.json()
    assert new_relic["id"] != original_id  # New ID
    assert new_relic["version"] == 2  # Version incremented
    assert new_relic["parent_id"] == original_id

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
    assert forked["version"] == 1  # New lineage starts at 1
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
    response = client.get("/api/v1/relics?limit=10&offset=0")

    assert response.status_code == 200
    data = response.json()
    assert "relics" in data
    assert "total" in data
    assert len(data["relics"]) >= 3


@pytest.mark.unit
def test_get_history(client):
    """Test getting version history."""
    # Create original relic
    create_response = client.post(
        "/api/v1/relics",
        data={"name": "Original"},
        files={"file": ("test.txt", BytesIO(b"v1"), "text/plain")}
    )
    original_id = create_response.json()["id"]

    # Create version 2
    v2_response = client.post(
        f"/api/v1/relics/{original_id}/edit",
        files={"file": ("test.txt", BytesIO(b"v2"), "text/plain")}
    )
    v2_id = v2_response.json()["id"]

    # Create version 3
    v3_response = client.post(
        f"/api/v1/relics/{v2_id}/edit",
        files={"file": ("test.txt", BytesIO(b"v3"), "text/plain")}
    )
    v3_id = v3_response.json()["id"]

    # Get history
    history_response = client.get(f"/api/v1/relics/{v3_id}/history")

    assert history_response.status_code == 200
    history = history_response.json()
    assert history["current_version"] == 3
    assert len(history["versions"]) == 3
    assert history["versions"][0]["version"] == 1
    assert history["versions"][2]["version"] == 3


@pytest.mark.unit
def test_diff_relics(client):
    """Test comparing two relics."""
    # Create original relic
    create_response = client.post(
        "/api/v1/relics",
        data={"name": "Original"},
        files={"file": ("test.txt", BytesIO(b"Line 1\nLine 2\n"), "text/plain")}
    )
    v1_id = create_response.json()["id"]

    # Create version 2 with changes
    v2_response = client.post(
        f"/api/v1/relics/{v1_id}/edit",
        files={"file": ("test.txt", BytesIO(b"Line 1\nLine 2 Modified\nLine 3\n"), "text/plain")}
    )
    v2_id = v2_response.json()["id"]

    # Get diff
    diff_response = client.get(f"/api/v1/diff?from={v1_id}&to={v2_id}")

    assert diff_response.status_code == 200
    diff = diff_response.json()
    assert diff["from_id"] == v1_id
    assert diff["to_id"] == v2_id
    assert "diff" in diff
    assert diff["additions"] > 0 or diff["deletions"] > 0


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
    response = client.get(f"/{relic_id}/raw")

    assert response.status_code == 200
    assert response.content == content


@pytest.mark.unit
def test_delete_relic(client):
    """Test deleting a relic."""
    # Create relic
    create_response = client.post(
        "/api/v1/relics",
        data={"name": "To Delete"},
        files={"file": ("test.txt", BytesIO(b"Content"), "text/plain")}
    )
    relic_id = create_response.json()["id"]
    # Delete relic
    delete_response = client.delete(f"/api/v1/relics/{relic_id}")

    assert delete_response.status_code == 200

    # Verify relic is deleted (should be 404)
    get_response = client.get(f"/api/v1/relics/{relic_id}")
    assert get_response.status_code == 404

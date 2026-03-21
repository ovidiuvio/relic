"""Tests for client registration and management endpoints."""
import pytest
import uuid


@pytest.fixture
def registered_client_key(client):
    """Register a client and return its key."""
    client_key = uuid.uuid4().hex
    headers = {"X-Client-Key": client_key}
    response = client.post("/api/v1/client/register", headers=headers)
    assert response.status_code == 200

    # Set a name so it can be used for actions like commenting or bookmarking if needed
    response = client.put("/api/v1/client/name", headers=headers, json={"name": "Test Client"})
    assert response.status_code == 200

    return client_key


# ── POST /api/v1/client/register ─────────────────────────────────────────────

@pytest.mark.unit
def test_register_client(client):
    """Registers a new client successfully."""
    # Arrange
    client_key = uuid.uuid4().hex

    # Act
    response = client.post(
        "/api/v1/client/register",
        headers={"X-Client-Key": client_key}
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["client_id"] == client_key
    assert "public_id" in data
    assert "created_at" in data
    assert data["relic_count"] == 0
    assert data["message"] == "Client registered successfully"


@pytest.mark.unit
def test_register_existing_client(client):
    """Returns the existing client if already registered."""
    # Arrange
    client_key = uuid.uuid4().hex

    # First registration
    client.post(
        "/api/v1/client/register",
        headers={"X-Client-Key": client_key}
    )

    # Act
    response = client.post(
        "/api/v1/client/register",
        headers={"X-Client-Key": client_key}
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["client_id"] == client_key
    assert "public_id" in data
    assert "created_at" in data
    assert "relic_count" in data
    assert "name" in data
    assert data["message"] == "Client already registered"


@pytest.mark.unit
def test_register_client_missing_key(client):
    """Returns 400 when missing valid client key."""
    # Act
    response = client.post("/api/v1/client/register")

    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == "X-Client-Key header required"


# ── GET /api/v1/client/relics ────────────────────────────────────────────────

@pytest.mark.unit
def test_get_client_relics(client, registered_client_key):
    """Returns all relics owned by the client."""
    # Arrange
    client.post(
        "/api/v1/relics",
        headers={"X-Client-Key": registered_client_key},
        data={"name": "Client Relic 1", "access_level": "public"},
        files={"file": ("test1.txt", b"content1", "text/plain")}
    )

    # Act
    response = client.get(
        "/api/v1/client/relics",
        headers={"X-Client-Key": registered_client_key}
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["client_id"] == registered_client_key
    assert data["relic_count"] == 1
    assert len(data["relics"]) == 1

    relic = data["relics"][0]
    assert relic["name"] == "Client Relic 1"
    assert "id" in relic
    assert "content_type" in relic
    assert "size_bytes" in relic
    assert "created_at" in relic
    assert "access_level" in relic
    assert "access_count" in relic
    assert "bookmark_count" in relic
    assert "comments_count" in relic
    assert "forks_count" in relic
    assert "tags" in relic


@pytest.mark.unit
def test_get_client_relics_missing_key(client):
    """Returns 401 when missing valid client key."""
    # Act
    response = client.get("/api/v1/client/relics")

    # Assert
    assert response.status_code == 401
    assert response.json()["detail"] == "Valid client key required"


# ── PUT /api/v1/client/name ──────────────────────────────────────────────────

@pytest.mark.unit
def test_update_client_name(client, registered_client_key):
    """Updates the client's display name."""
    # Act
    response = client.put(
        "/api/v1/client/name",
        headers={"X-Client-Key": registered_client_key},
        json={"name": "New Test Name"}
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "updated"
    assert data["name"] == "New Test Name"


@pytest.mark.unit
def test_update_client_name_missing_key(client):
    """Returns 401 when missing valid client key."""
    # Act
    response = client.put(
        "/api/v1/client/name",
        json={"name": "New Test Name"}
    )

    # Assert
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"

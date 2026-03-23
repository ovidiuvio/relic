"""Tests for spaces endpoints."""
import pytest


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def registered_client_key(client):
    """Register a client and return its key."""
    import uuid
    client_key = uuid.uuid4().hex
    headers = {"X-Client-Key": client_key}
    client.post("/api/v1/client/register", headers=headers)
    return client_key

@pytest.fixture
def created_relic(client, test_file_content, registered_client_key):
    """A relic created for use in tests that need an existing relic."""
    response = client.post(
        "/api/v1/relics",
        headers={"X-Client-Key": registered_client_key},
        data={"name": "Test Relic", "access_level": "public"},
        files={"file": ("test.txt", test_file_content, "text/plain")}
    )
    assert response.status_code == 200
    return response.json()


# ── Spaces ─────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_create_space_unauthorized(client):
    """Returns 401 when no client key is provided."""
    response = client.post(
        "/api/v1/spaces",
        json={"name": "My Space", "visibility": "public"}
    )
    assert response.status_code == 401


@pytest.mark.unit
def test_create_space(client, registered_client_key):
    """Creates a new space."""
    # Arrange
    headers = {"X-Client-Key": registered_client_key}

    # Act
    response = client.post(
        "/api/v1/spaces",
        headers=headers,
        json={"name": "My New Space", "visibility": "public"}
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "My New Space"
    assert data["visibility"] == "public"
    assert data["owner_client_id"] == registered_client_key
    assert "id" in data
    assert "created_at" in data
    assert "relic_count" in data
    assert data["role"] == "owner"


@pytest.mark.unit
def test_list_spaces(client, registered_client_key):
    """Returns a list of spaces."""
    # Arrange
    headers = {"X-Client-Key": registered_client_key}
    client.post(
        "/api/v1/spaces",
        headers=headers,
        json={"name": "My New Space", "visibility": "public"}
    )

    # Act
    response = client.get("/api/v1/spaces", headers=headers)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "spaces" in data
    assert isinstance(data["spaces"], list)
    assert len(data["spaces"]) > 0
    assert "total" in data
    assert "limit" in data
    assert "offset" in data


@pytest.mark.unit
def test_get_space(client, registered_client_key):
    """Returns details for a specific space."""
    # Arrange
    headers = {"X-Client-Key": registered_client_key}
    create_response = client.post(
        "/api/v1/spaces",
        headers=headers,
        json={"name": "My New Space", "visibility": "public"}
    )
    space_id = create_response.json()["id"]

    # Act
    response = client.get(f"/api/v1/spaces/{space_id}", headers=headers)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == space_id
    assert data["name"] == "My New Space"
    assert data["visibility"] == "public"


@pytest.mark.unit
def test_get_space_not_found(client, registered_client_key):
    """Returns 404 for a nonexistent space."""
    headers = {"X-Client-Key": registered_client_key}
    response = client.get("/api/v1/spaces/nonexistent_space", headers=headers)
    assert response.status_code == 404


@pytest.mark.unit
def test_update_space(client, registered_client_key):
    """Updates space metadata."""
    # Arrange
    headers = {"X-Client-Key": registered_client_key}
    create_response = client.post(
        "/api/v1/spaces",
        headers=headers,
        json={"name": "My New Space", "visibility": "public"}
    )
    space_id = create_response.json()["id"]

    # Act
    response = client.put(
        f"/api/v1/spaces/{space_id}",
        headers=headers,
        json={"name": "Updated Space Name"}
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Space Name"
    assert data["visibility"] == "public"


@pytest.mark.unit
def test_update_space_unauthorized(client, registered_client_key):
    """Returns 401/403 when unauthorized to update a space."""
    # Arrange
    headers = {"X-Client-Key": registered_client_key}
    create_response = client.post(
        "/api/v1/spaces",
        headers=headers,
        json={"name": "My New Space", "visibility": "public"}
    )
    space_id = create_response.json()["id"]

    # Act without any header -> 401
    response = client.put(
        f"/api/v1/spaces/{space_id}",
        json={"name": "Hacked Name"}
    )
    assert response.status_code == 401


@pytest.mark.unit
def test_delete_space(client, registered_client_key):
    """Deletes a space successfully."""
    # Arrange
    headers = {"X-Client-Key": registered_client_key}
    create_response = client.post(
        "/api/v1/spaces",
        headers=headers,
        json={"name": "My New Space", "visibility": "public"}
    )
    space_id = create_response.json()["id"]

    # Act
    response = client.delete(f"/api/v1/spaces/{space_id}", headers=headers)

    # Assert
    assert response.status_code == 200

    # Verify deletion
    get_response = client.get(f"/api/v1/spaces/{space_id}", headers=headers)
    assert get_response.status_code == 404


@pytest.mark.unit
def test_delete_space_unauthorized(client, registered_client_key):
    """Returns 401/403 when unauthorized to delete a space."""
    # Arrange
    headers = {"X-Client-Key": registered_client_key}
    create_response = client.post(
        "/api/v1/spaces",
        headers=headers,
        json={"name": "My New Space", "visibility": "public"}
    )
    space_id = create_response.json()["id"]

    # Act without any header -> 401
    response = client.delete(f"/api/v1/spaces/{space_id}")
    assert response.status_code == 401

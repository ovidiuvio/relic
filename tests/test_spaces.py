"""Tests for space endpoints."""
import pytest


@pytest.mark.unit
def test_create_space(client):
    """Test creating a new space."""
    response = client.post(
        "/api/v1/spaces",
        headers={"X-Client-Key": "test_owner_key"},
        json={"name": "Test Space", "visibility": "public"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["name"] == "Test Space"
    assert data["visibility"] == "public"
    assert data["owner_client_id"] == "test_owner_key"
    assert "created_at" in data
    assert data["relic_count"] == 0
    assert data["role"] == "owner"


@pytest.mark.unit
def test_list_spaces(client):
    """Test listing spaces."""
    # Create two spaces
    client.post(
        "/api/v1/spaces",
        headers={"X-Client-Key": "test_owner_key"},
        json={"name": "Test Space 1", "visibility": "public"}
    )
    client.post(
        "/api/v1/spaces",
        headers={"X-Client-Key": "test_owner_key"},
        json={"name": "Test Space 2", "visibility": "public"}
    )

    response = client.get("/api/v1/spaces")
    assert response.status_code == 200
    data = response.json()
    assert "spaces" in data
    assert isinstance(data["spaces"], list)
    assert len(data["spaces"]) >= 2

    space = data["spaces"][0]
    assert "id" in space
    assert "name" in space
    assert "visibility" in space
    assert "owner_client_id" in space
    assert "created_at" in space
    assert "relic_count" in space
    assert "role" in space

    assert "total" in data
    assert "limit" in data
    assert "offset" in data


@pytest.mark.unit
def test_get_space(client):
    """Test getting a specific space."""
    create_response = client.post(
        "/api/v1/spaces",
        headers={"X-Client-Key": "test_owner_key"},
        json={"name": "My Space", "visibility": "public"}
    )
    space_id = create_response.json()["id"]

    response = client.get(f"/api/v1/spaces/{space_id}")
    assert response.status_code == 200
    data = response.json()

    assert data["id"] == space_id
    assert data["name"] == "My Space"
    assert data["visibility"] == "public"
    assert data["owner_client_id"] == "test_owner_key"
    assert "created_at" in data
    assert data["relic_count"] == 0
    assert data["role"] is None  # Default if no client key provided


@pytest.mark.unit
def test_get_nonexistent_space(client):
    """Test getting a space that does not exist."""
    response = client.get("/api/v1/spaces/nonexistent_space_id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Space not found"

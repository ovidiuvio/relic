"""Tests for bookmark endpoints."""
import pytest


@pytest.fixture
def registered_client_key(client):
    """Register a client and return its key."""
    import uuid
    client_key = uuid.uuid4().hex
    headers = {"X-Client-Key": client_key}
    response = client.post("/api/v1/client/register", headers=headers)
    assert response.status_code == 200

    # Set a name so it can be used for actions like commenting or bookmarking if needed
    response = client.put("/api/v1/client/name", headers=headers, json={"name": "Test Client"})
    assert response.status_code == 200

    return client_key


@pytest.fixture
def created_relic(client, test_file_content):
    """A relic created for use in tests that need an existing relic."""
    response = client.post(
        "/api/v1/relics",
        data={"name": "Test Relic", "access_level": "public"},
        files={"file": ("test.txt", test_file_content, "text/plain")}
    )
    assert response.status_code == 200
    return response.json()


# ── POST /api/v1/bookmarks ───────────────────────────────────────────────────

@pytest.mark.unit
def test_add_bookmark(client, registered_client_key, created_relic):
    """Creates a bookmark for a relic."""
    # Arrange
    relic_id = created_relic["id"]

    # Act
    response = client.post(
        f"/api/v1/bookmarks?relic_id={relic_id}",
        headers={"X-Client-Key": registered_client_key}
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["relic_id"] == relic_id
    assert "id" in data
    assert data["message"] == "Bookmark added successfully"


@pytest.mark.unit
def test_add_bookmark_unauthorized(client, created_relic):
    """Returns 401 when missing valid client key."""
    relic_id = created_relic["id"]
    response = client.post(f"/api/v1/bookmarks?relic_id={relic_id}")
    assert response.status_code == 401
    assert response.json()["detail"] == "Valid client key required"


@pytest.mark.unit
def test_add_bookmark_not_found(client, registered_client_key):
    """Returns 404 when relic does not exist."""
    response = client.post(
        f"/api/v1/bookmarks?relic_id=nonexistent",
        headers={"X-Client-Key": registered_client_key}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Relic not found"


@pytest.mark.unit
def test_add_bookmark_already_exists(client, registered_client_key, created_relic):
    """Returns 409 when relic is already bookmarked."""
    relic_id = created_relic["id"]

    # First bookmark
    client.post(
        f"/api/v1/bookmarks?relic_id={relic_id}",
        headers={"X-Client-Key": registered_client_key}
    )

    # Second bookmark
    response = client.post(
        f"/api/v1/bookmarks?relic_id={relic_id}",
        headers={"X-Client-Key": registered_client_key}
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Relic already bookmarked"


# ── DELETE /api/v1/bookmarks/{relic_id} ──────────────────────────────────────

@pytest.mark.unit
def test_remove_bookmark(client, registered_client_key, created_relic):
    """Removes a bookmark for a relic."""
    relic_id = created_relic["id"]

    # Arrange: Create bookmark
    client.post(
        f"/api/v1/bookmarks?relic_id={relic_id}",
        headers={"X-Client-Key": registered_client_key}
    )

    # Act
    response = client.delete(
        f"/api/v1/bookmarks/{relic_id}",
        headers={"X-Client-Key": registered_client_key}
    )

    # Assert
    assert response.status_code == 200
    assert response.json()["message"] == "Bookmark removed successfully"


@pytest.mark.unit
def test_remove_bookmark_unauthorized(client, created_relic):
    """Returns 401 when missing valid client key."""
    relic_id = created_relic["id"]
    response = client.delete(f"/api/v1/bookmarks/{relic_id}")
    assert response.status_code == 401
    assert response.json()["detail"] == "Valid client key required"


@pytest.mark.unit
def test_remove_bookmark_not_found(client, registered_client_key, created_relic):
    """Returns 404 when bookmark does not exist."""
    relic_id = created_relic["id"]
    response = client.delete(
        f"/api/v1/bookmarks/{relic_id}",
        headers={"X-Client-Key": registered_client_key}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Bookmark not found"


# ── GET /api/v1/bookmarks/check/{relic_id} ───────────────────────────────────

@pytest.mark.unit
def test_check_bookmark_true(client, registered_client_key, created_relic):
    """Returns is_bookmarked=True when relic is bookmarked."""
    relic_id = created_relic["id"]

    # Arrange: Create bookmark
    bookmark_res = client.post(
        f"/api/v1/bookmarks?relic_id={relic_id}",
        headers={"X-Client-Key": registered_client_key}
    ).json()

    # Act
    response = client.get(
        f"/api/v1/bookmarks/check/{relic_id}",
        headers={"X-Client-Key": registered_client_key}
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["relic_id"] == relic_id
    assert data["is_bookmarked"] is True
    assert data["bookmark_id"] == bookmark_res["id"]


@pytest.mark.unit
def test_check_bookmark_false(client, registered_client_key, created_relic):
    """Returns is_bookmarked=False when relic is not bookmarked."""
    relic_id = created_relic["id"]

    # Act
    response = client.get(
        f"/api/v1/bookmarks/check/{relic_id}",
        headers={"X-Client-Key": registered_client_key}
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["relic_id"] == relic_id
    assert data["is_bookmarked"] is False
    assert data["bookmark_id"] is None


@pytest.mark.unit
def test_check_bookmark_unauthorized(client, created_relic):
    """Returns 401 when missing valid client key."""
    relic_id = created_relic["id"]
    response = client.get(f"/api/v1/bookmarks/check/{relic_id}")
    assert response.status_code == 401
    assert response.json()["detail"] == "Valid client key required"


# ── GET /api/v1/bookmarks ────────────────────────────────────────────────────

@pytest.mark.unit
def test_get_client_bookmarks(client, registered_client_key, created_relic):
    """Returns all bookmarks for the authenticated client."""
    relic_id = created_relic["id"]

    # Arrange: Create bookmark
    bookmark_res = client.post(
        f"/api/v1/bookmarks?relic_id={relic_id}",
        headers={"X-Client-Key": registered_client_key}
    ).json()

    # Act
    response = client.get(
        "/api/v1/bookmarks",
        headers={"X-Client-Key": registered_client_key}
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "client_id" in data
    assert data["bookmark_count"] == 1

    bookmarks = data["bookmarks"]
    assert len(bookmarks) == 1

    bookmark = bookmarks[0]
    assert bookmark["id"] == relic_id
    # created_relic may not have a "name" key directly, its structure comes from the POST /relics endpoint response.
    # The GET /api/v1/bookmarks response should return the actual string passed in the create request
    assert bookmark["name"] == "Test Relic"
    assert "content_type" in bookmark
    assert "size_bytes" in bookmark
    assert "access_level" in bookmark
    assert "bookmark_count" in bookmark
    assert "comments_count" in bookmark
    assert "forks_count" in bookmark
    assert bookmark["bookmark_id"] == bookmark_res["id"]
    assert "tags" in bookmark


@pytest.mark.unit
def test_get_client_bookmarks_unauthorized(client):
    """Returns 401 when missing valid client key."""
    response = client.get("/api/v1/bookmarks")
    assert response.status_code == 401
    assert response.json()["detail"] == "Valid client key required"

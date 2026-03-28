"""Integration tests for comment endpoints."""
import uuid
import pytest
from conftest import ADMIN_KEY


@pytest.fixture
def commenter(http):
    """Register a client with a display name. Returns (key, headers)."""
    key = uuid.uuid4().hex
    http.post("/api/v1/client/register", headers={"X-Client-Key": key})
    http.put("/api/v1/client/name", headers={"X-Client-Key": key}, json={"name": "Test Commenter"})
    return key, {"X-Client-Key": key}


@pytest.fixture
def relic_for_comments(http, commenter):
    """Create a relic for comment tests. Cleans up after."""
    key, headers = commenter
    resp = http.post(
        "/api/v1/relics",
        headers=headers,
        data={"name": "Comment Relic", "access_level": "public"},
        files={"file": ("test.txt", b"line1\nline2\nline3", "text/plain")},
    )
    assert resp.status_code == 200
    relic_id = resp.json()["id"]
    yield relic_id
    http.delete(f"/api/v1/relics/{relic_id}", headers=headers)


# ── POST /api/v1/relics/{id}/comments ────────────────────────────────────────

@pytest.mark.integration
def test_create_comment(http, commenter, relic_for_comments):
    _, headers = commenter
    resp = http.post(
        f"/api/v1/relics/{relic_for_comments}/comments",
        headers=headers,
        json={"line_number": 1, "content": "This is a comment"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "This is a comment"
    assert data["line_number"] == 1
    assert data["author_name"] == "Test Commenter"
    assert "id" in data


@pytest.mark.integration
def test_create_comment_no_auth(http, relic_for_comments):
    resp = http.post(
        f"/api/v1/relics/{relic_for_comments}/comments",
        json={"line_number": 1, "content": "No auth"},
    )
    assert resp.status_code == 401


@pytest.mark.integration
def test_create_comment_no_name(http, relic_for_comments, registered_client):
    key, _ = registered_client  # registered but no name set
    resp = http.post(
        f"/api/v1/relics/{relic_for_comments}/comments",
        headers={"X-Client-Key": key},
        json={"line_number": 1, "content": "I have no name"},
    )
    assert resp.status_code == 400
    assert "display name" in resp.json()["detail"]


@pytest.mark.integration
def test_create_comment_nonexistent_relic(http, commenter):
    _, headers = commenter
    resp = http.post(
        "/api/v1/relics/nonexistent_relic_comment/comments",
        headers=headers,
        json={"line_number": 1, "content": "Ghost"},
    )
    assert resp.status_code == 404


# ── GET /api/v1/relics/{id}/comments ─────────────────────────────────────────

@pytest.mark.integration
def test_get_comments(http, commenter, relic_for_comments):
    _, headers = commenter
    relic_id = relic_for_comments

    http.post(f"/api/v1/relics/{relic_id}/comments", headers=headers, json={"line_number": 1, "content": "First"})
    http.post(f"/api/v1/relics/{relic_id}/comments", headers=headers, json={"line_number": 2, "content": "Second"})

    resp = http.get(f"/api/v1/relics/{relic_id}/comments")
    assert resp.status_code == 200
    data = resp.json()
    assert "comments" in data
    assert "total" in data
    assert data["total"] >= 2


@pytest.mark.integration
def test_get_comments_by_line_number(http, commenter, relic_for_comments):
    _, headers = commenter
    relic_id = relic_for_comments

    http.post(f"/api/v1/relics/{relic_id}/comments", headers=headers, json={"line_number": 5, "content": "Line 5"})
    http.post(f"/api/v1/relics/{relic_id}/comments", headers=headers, json={"line_number": 6, "content": "Line 6"})

    resp = http.get(f"/api/v1/relics/{relic_id}/comments?line_number=5")
    assert resp.status_code == 200
    data = resp.json()
    assert all(c["line_number"] == 5 for c in data["comments"])


@pytest.mark.integration
def test_get_comments_nonexistent_relic(http):
    resp = http.get("/api/v1/relics/nonexistent_relic_id_comments/comments")
    assert resp.status_code == 404


# ── PUT /api/v1/relics/{id}/comments/{comment_id} ────────────────────────────

@pytest.mark.integration
def test_update_comment(http, commenter, relic_for_comments):
    key, headers = commenter
    relic_id = relic_for_comments

    create = http.post(
        f"/api/v1/relics/{relic_id}/comments",
        headers=headers,
        json={"line_number": 1, "content": "Original"},
    )
    comment_id = create.json()["id"]

    resp = http.put(
        f"/api/v1/relics/{relic_id}/comments/{comment_id}",
        headers=headers,
        json={"content": "Updated"},
    )
    assert resp.status_code == 200
    assert resp.json()["content"] == "Updated"


@pytest.mark.integration
def test_update_comment_not_author(http, commenter, relic_for_comments, registered_client):
    _, author_headers = commenter
    relic_id = relic_for_comments
    other_key, _ = registered_client

    create = http.post(
        f"/api/v1/relics/{relic_id}/comments",
        headers=author_headers,
        json={"line_number": 1, "content": "Mine"},
    )
    comment_id = create.json()["id"]

    resp = http.put(
        f"/api/v1/relics/{relic_id}/comments/{comment_id}",
        headers={"X-Client-Key": other_key},
        json={"content": "Hacked"},
    )
    assert resp.status_code == 403


@pytest.mark.integration
def test_update_comment_not_found(http, commenter, relic_for_comments):
    _, headers = commenter
    resp = http.put(
        f"/api/v1/relics/{relic_for_comments}/comments/nonexistent_comment_id",
        headers=headers,
        json={"content": "Ghost"},
    )
    assert resp.status_code == 404


@pytest.mark.integration
def test_update_comment_no_auth(http, relic_for_comments):
    resp = http.put(
        f"/api/v1/relics/{relic_for_comments}/comments/any_id",
        json={"content": "No auth"},
    )
    assert resp.status_code == 401


# ── DELETE /api/v1/relics/{id}/comments/{comment_id} ─────────────────────────

@pytest.mark.integration
def test_delete_comment(http, commenter, relic_for_comments):
    _, headers = commenter
    relic_id = relic_for_comments

    create = http.post(
        f"/api/v1/relics/{relic_id}/comments",
        headers=headers,
        json={"line_number": 1, "content": "Delete me"},
    )
    comment_id = create.json()["id"]

    resp = http.delete(f"/api/v1/relics/{relic_id}/comments/{comment_id}", headers=headers)
    assert resp.status_code == 200


@pytest.mark.integration
def test_delete_comment_not_author(http, commenter, relic_for_comments, registered_client):
    _, author_headers = commenter
    relic_id = relic_for_comments
    other_key, _ = registered_client

    create = http.post(
        f"/api/v1/relics/{relic_id}/comments",
        headers=author_headers,
        json={"line_number": 1, "content": "Not yours"},
    )
    comment_id = create.json()["id"]

    resp = http.delete(
        f"/api/v1/relics/{relic_id}/comments/{comment_id}",
        headers={"X-Client-Key": other_key},
    )
    assert resp.status_code == 403


@pytest.mark.integration
def test_delete_comment_not_found(http, commenter, relic_for_comments):
    _, headers = commenter
    resp = http.delete(
        f"/api/v1/relics/{relic_for_comments}/comments/nonexistent_comment_id",
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.integration
def test_delete_comment_no_auth(http, relic_for_comments):
    resp = http.delete(f"/api/v1/relics/{relic_for_comments}/comments/any_id")
    assert resp.status_code == 401


@pytest.mark.integration
def test_delete_comment_as_admin(http, commenter, relic_for_comments):
    _, author_headers = commenter
    relic_id = relic_for_comments

    create = http.post(
        f"/api/v1/relics/{relic_id}/comments",
        headers=author_headers,
        json={"line_number": 1, "content": "Admin deletes this"},
    )
    comment_id = create.json()["id"]

    resp = http.delete(
        f"/api/v1/relics/{relic_id}/comments/{comment_id}",
        headers={"X-Client-Key": ADMIN_KEY},
    )
    assert resp.status_code == 200

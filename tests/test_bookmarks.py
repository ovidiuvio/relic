"""Integration tests for bookmark endpoints."""
import uuid
import pytest


@pytest.fixture
def bookmarkable_relic(http, registered_client):
    """Create a public relic for bookmark tests. Cleans up after."""
    key, _ = registered_client
    resp = http.post(
        "/api/v1/relics",
        headers={"X-Client-Key": key},
        data={"name": "Bookmarkable Relic", "access_level": "public"},
        files={"file": ("test.txt", b"bookmark me", "text/plain")},
    )
    assert resp.status_code == 200
    relic_id = resp.json()["id"]
    yield relic_id
    http.delete(f"/api/v1/relics/{relic_id}", headers={"X-Client-Key": key})


# ── POST /api/v1/bookmarks ───────────────────────────────────────────────────

@pytest.mark.integration
def test_add_bookmark(http, registered_client, bookmarkable_relic):
    key, _ = registered_client
    relic_id = bookmarkable_relic

    resp = http.post(f"/api/v1/bookmarks?relic_id={relic_id}", headers={"X-Client-Key": key})
    assert resp.status_code == 200
    data = resp.json()
    assert data["relic_id"] == relic_id
    assert data["message"] == "Bookmark added successfully"
    assert "id" in data

    # Cleanup
    http.delete(f"/api/v1/bookmarks/{relic_id}", headers={"X-Client-Key": key})


@pytest.mark.integration
def test_add_bookmark_unauthorized(http, bookmarkable_relic):
    resp = http.post(f"/api/v1/bookmarks?relic_id={bookmarkable_relic}")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Valid client key required"


@pytest.mark.integration
def test_add_bookmark_not_found(http, registered_client):
    key, _ = registered_client
    resp = http.post("/api/v1/bookmarks?relic_id=nonexistent_relic_bm", headers={"X-Client-Key": key})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Relic not found"


@pytest.mark.integration
def test_add_bookmark_already_exists(http, registered_client, bookmarkable_relic):
    key, _ = registered_client
    relic_id = bookmarkable_relic

    http.post(f"/api/v1/bookmarks?relic_id={relic_id}", headers={"X-Client-Key": key})
    resp = http.post(f"/api/v1/bookmarks?relic_id={relic_id}", headers={"X-Client-Key": key})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Relic already bookmarked"

    http.delete(f"/api/v1/bookmarks/{relic_id}", headers={"X-Client-Key": key})


# ── DELETE /api/v1/bookmarks/{relic_id} ──────────────────────────────────────

@pytest.mark.integration
def test_remove_bookmark(http, registered_client, bookmarkable_relic):
    key, _ = registered_client
    relic_id = bookmarkable_relic

    http.post(f"/api/v1/bookmarks?relic_id={relic_id}", headers={"X-Client-Key": key})
    resp = http.delete(f"/api/v1/bookmarks/{relic_id}", headers={"X-Client-Key": key})
    assert resp.status_code == 200
    assert resp.json()["message"] == "Bookmark removed successfully"


@pytest.mark.integration
def test_remove_bookmark_unauthorized(http, bookmarkable_relic):
    resp = http.delete(f"/api/v1/bookmarks/{bookmarkable_relic}")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Valid client key required"


@pytest.mark.integration
def test_remove_bookmark_not_found(http, registered_client, bookmarkable_relic):
    key, _ = registered_client
    resp = http.delete(f"/api/v1/bookmarks/{bookmarkable_relic}", headers={"X-Client-Key": key})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Bookmark not found"


# ── GET /api/v1/bookmarks/check/{relic_id} ───────────────────────────────────

@pytest.mark.integration
def test_check_bookmark_true(http, registered_client, bookmarkable_relic):
    key, _ = registered_client
    relic_id = bookmarkable_relic

    bm = http.post(f"/api/v1/bookmarks?relic_id={relic_id}", headers={"X-Client-Key": key}).json()
    resp = http.get(f"/api/v1/bookmarks/check/{relic_id}", headers={"X-Client-Key": key})
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_bookmarked"] is True
    assert data["bookmark_id"] == bm["id"]

    http.delete(f"/api/v1/bookmarks/{relic_id}", headers={"X-Client-Key": key})


@pytest.mark.integration
def test_check_bookmark_false(http, registered_client, bookmarkable_relic):
    key, _ = registered_client
    resp = http.get(f"/api/v1/bookmarks/check/{bookmarkable_relic}", headers={"X-Client-Key": key})
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_bookmarked"] is False
    assert data["bookmark_id"] is None


@pytest.mark.integration
def test_check_bookmark_unauthorized(http, bookmarkable_relic):
    resp = http.get(f"/api/v1/bookmarks/check/{bookmarkable_relic}")
    assert resp.status_code == 401


# ── GET /api/v1/bookmarks ────────────────────────────────────────────────────

@pytest.mark.integration
def test_get_client_bookmarks(http, registered_client, bookmarkable_relic):
    key, _ = registered_client
    relic_id = bookmarkable_relic

    bm = http.post(f"/api/v1/bookmarks?relic_id={relic_id}", headers={"X-Client-Key": key}).json()
    resp = http.get("/api/v1/bookmarks", headers={"X-Client-Key": key})
    assert resp.status_code == 200
    data = resp.json()
    assert "bookmarks" in data
    assert data["bookmark_count"] >= 1
    ids = [b["id"] for b in data["bookmarks"]]
    assert relic_id in ids

    http.delete(f"/api/v1/bookmarks/{relic_id}", headers={"X-Client-Key": key})


@pytest.mark.integration
def test_get_client_bookmarks_unauthorized(http):
    resp = http.get("/api/v1/bookmarks")
    assert resp.status_code == 401


# ── GET /api/v1/bookmarks/{relic_id}/bookmarkers ─────────────────────────────

@pytest.mark.integration
def test_get_relic_bookmarkers(http, registered_client, bookmarkable_relic):
    key, _ = registered_client
    relic_id = bookmarkable_relic

    http.post(f"/api/v1/bookmarks?relic_id={relic_id}", headers={"X-Client-Key": key})
    resp = http.get(f"/api/v1/bookmarks/{relic_id}/bookmarkers")
    assert resp.status_code == 200
    data = resp.json()
    assert "bookmarkers" in data
    assert data["total"] >= 1
    assert "public_id" in data["bookmarkers"][0]
    assert "bookmarked_at" in data["bookmarkers"][0]

    http.delete(f"/api/v1/bookmarks/{relic_id}", headers={"X-Client-Key": key})


@pytest.mark.integration
def test_get_relic_bookmarkers_empty(http, bookmarkable_relic):
    resp = http.get(f"/api/v1/bookmarks/{bookmarkable_relic}/bookmarkers")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0

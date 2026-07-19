"""Integration tests for user registration and management endpoints."""
import uuid
import pytest


# ── POST /api/v1/user/register ─────────────────────────────────────────────

@pytest.mark.integration
def test_register_user(http):
    key = uuid.uuid4().hex
    resp = http.post("/api/v1/user/register", headers={"X-User-Key": key})
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == key
    assert "public_id" in data
    assert data["public_id"] is not None
    assert "created_at" in data
    assert data["relic_count"] == 0
    assert data["message"] == "User registered successfully"


@pytest.mark.integration
def test_register_existing_user(http):
    key = uuid.uuid4().hex
    http.post("/api/v1/user/register", headers={"X-User-Key": key})

    resp = http.post("/api/v1/user/register", headers={"X-User-Key": key})
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == key
    assert data["message"] == "User already registered"
    assert "public_id" in data


@pytest.mark.integration
def test_register_user_missing_key(http):
    resp = http.post("/api/v1/user/register")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "X-User-Key header required"


# ── GET /api/v1/user/relics ────────────────────────────────────────────────

@pytest.mark.integration
def test_get_user_relics(http, registered_user):
    key, _ = registered_user

    create = http.post(
        "/api/v1/relics",
        headers={"X-User-Key": key},
        data={"name": "My Relic", "access_level": "public"},
        files={"file": ("test.txt", b"content", "text/plain")},
    )
    relic_id = create.json()["id"]

    resp = http.get("/api/v1/user/relics", headers={"X-User-Key": key})
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == key
    assert data["relic_count"] >= 1
    ids = [r["id"] for r in data["relics"]]
    assert relic_id in ids

    relic = next(r for r in data["relics"] if r["id"] == relic_id)
    assert relic["name"] == "My Relic"
    assert "content_type" in relic
    assert "size_bytes" in relic
    assert "created_at" in relic
    assert "access_level" in relic
    assert "access_count" in relic
    assert "bookmark_count" in relic
    assert "comments_count" in relic
    assert "forks_count" in relic
    assert "tags" in relic

    http.delete(f"/api/v1/relics/{relic_id}", headers={"X-User-Key": key})


@pytest.mark.integration
def test_get_user_relics_missing_key(http):
    resp = http.get("/api/v1/user/relics")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Valid user key required"


# ── PUT /api/v1/user/name ──────────────────────────────────────────────────

@pytest.mark.integration
def test_update_user_name(http, registered_user):
    key, _ = registered_user
    resp = http.put(
        "/api/v1/user/name",
        headers={"X-User-Key": key},
        json={"name": "New Display Name"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "updated"
    assert data["name"] == "New Display Name"


@pytest.mark.integration
def test_update_user_name_missing_key(http):
    resp = http.put("/api/v1/user/name", json={"name": "Nobody"})
    assert resp.status_code == 401

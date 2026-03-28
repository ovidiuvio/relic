"""Integration tests for core relic endpoints."""
import uuid
import pytest


# ── Health / Version ──────────────────────────────────────────────────────────

@pytest.mark.integration
def test_health_check(http):
    resp = http.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.integration
def test_get_version(http):
    resp = http.get("/api/v1/version")
    assert resp.status_code == 200
    assert "version" in resp.json()


# ── Create ────────────────────────────────────────────────────────────────────

@pytest.mark.integration
def test_create_relic(http, registered_client):
    key, _ = registered_client
    content = b"Integration test content"

    resp = http.post(
        "/api/v1/relics",
        headers={"X-Client-Key": key},
        data={"name": "Create Test", "access_level": "public"},
        files={"file": ("test.txt", content, "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert "url" in data
    assert "created_at" in data
    assert data["size_bytes"] == len(content)

    http.delete(f"/api/v1/relics/{data['id']}", headers={"X-Client-Key": key})


@pytest.mark.integration
def test_create_relic_no_file(http):
    resp = http.post("/api/v1/relics", data={"name": "No File"})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "No content provided"


@pytest.mark.integration
def test_create_relic_invalid_access_level(http):
    resp = http.post(
        "/api/v1/relics",
        data={"access_level": "invalid"},
        files={"file": ("test.txt", b"content", "text/plain")},
    )
    assert resp.status_code == 400


@pytest.mark.integration
def test_create_relic_with_tags(http, registered_client):
    key, _ = registered_client
    resp = http.post(
        "/api/v1/relics",
        headers={"X-Client-Key": key},
        data={"name": "Tagged", "access_level": "public", "tags": "python,code"},
        files={"file": ("test.py", b"print('hi')", "text/plain")},
    )
    assert resp.status_code == 200
    relic_id = resp.json()["id"]

    meta = http.get(f"/api/v1/relics/{relic_id}").json()
    tag_names = [t["name"] for t in meta["tags"]]
    assert "python" in tag_names
    assert "code" in tag_names

    http.delete(f"/api/v1/relics/{relic_id}", headers={"X-Client-Key": key})


# ── Get ───────────────────────────────────────────────────────────────────────

@pytest.mark.integration
def test_get_relic(http, created_relic):
    relic_id = created_relic["id"]
    resp = http.get(f"/api/v1/relics/{relic_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == relic_id
    assert data["name"] == "Test Relic"
    assert data["access_level"] == "public"


@pytest.mark.integration
def test_get_nonexistent_relic(http):
    resp = http.get("/api/v1/relics/nonexistent_relic_id_000")
    assert resp.status_code == 404


# ── Raw content ───────────────────────────────────────────────────────────────

@pytest.mark.integration
def test_get_raw_content(http, created_relic):
    relic_id = created_relic["id"]
    resp = http.get(f"/{relic_id}/raw")
    assert resp.status_code == 200
    assert b"Hello, World!" in resp.content


@pytest.mark.integration
def test_get_raw_root_route(http, created_relic):
    relic_id = created_relic["id"]
    resp = http.get(f"/{relic_id}")
    assert resp.status_code == 200
    assert b"Hello, World!" in resp.content


# ── List ──────────────────────────────────────────────────────────────────────

@pytest.mark.integration
def test_list_relics(http, created_relic):
    resp = http.get("/api/v1/relics?limit=10&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert "relics" in data
    assert "total" in data
    relic_ids = [r["id"] for r in data["relics"]]
    assert created_relic["id"] in relic_ids


@pytest.mark.integration
def test_list_relics_with_tag_filter(http, registered_client):
    key, _ = registered_client
    tag = f"tag-{uuid.uuid4().hex[:8]}"
    resp = http.post(
        "/api/v1/relics",
        headers={"X-Client-Key": key},
        data={"name": "Tagged Relic", "access_level": "public", "tags": tag},
        files={"file": ("test.txt", b"content", "text/plain")},
    )
    relic_id = resp.json()["id"]

    resp_tag = http.get(f"/api/v1/relics?tag={tag}")
    assert resp_tag.status_code == 200
    assert resp_tag.json()["total"] >= 1

    resp_none = http.get("/api/v1/relics?tag=completely-nonexistent-tag-xyz-123")
    assert resp_none.status_code == 200
    assert resp_none.json()["total"] == 0

    http.delete(f"/api/v1/relics/{relic_id}", headers={"X-Client-Key": key})


@pytest.mark.integration
def test_list_relics_with_search(http, registered_client):
    key, _ = registered_client
    unique_name = f"SearchTarget-{uuid.uuid4().hex[:8]}"
    resp = http.post(
        "/api/v1/relics",
        headers={"X-Client-Key": key},
        data={"name": unique_name, "access_level": "public"},
        files={"file": ("test.txt", b"content", "text/plain")},
    )
    relic_id = resp.json()["id"]

    resp_search = http.get(f"/api/v1/relics?search={unique_name}")
    assert resp_search.status_code == 200
    assert resp_search.json()["total"] >= 1

    http.delete(f"/api/v1/relics/{relic_id}", headers={"X-Client-Key": key})


# ── Update ────────────────────────────────────────────────────────────────────

@pytest.mark.integration
def test_edit_relic(http, created_relic):
    relic_id = created_relic["id"]
    key = created_relic["client_key"]

    resp = http.put(
        f"/api/v1/relics/{relic_id}",
        headers={"X-Client-Key": key},
        json={"name": "Updated Name"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"
    assert resp.json()["id"] == relic_id


# ── Delete ────────────────────────────────────────────────────────────────────

@pytest.mark.integration
def test_delete_relic(http, registered_client):
    key, _ = registered_client
    create = http.post(
        "/api/v1/relics",
        headers={"X-Client-Key": key},
        data={"access_level": "public"},
        files={"file": ("test.txt", b"to delete", "text/plain")},
    )
    relic_id = create.json()["id"]

    resp = http.delete(f"/api/v1/relics/{relic_id}", headers={"X-Client-Key": key})
    assert resp.status_code == 200

    assert http.get(f"/api/v1/relics/{relic_id}").status_code == 404


@pytest.mark.integration
def test_delete_relic_no_auth(http, created_relic):
    resp = http.delete(f"/api/v1/relics/{created_relic['id']}")
    assert resp.status_code == 401


@pytest.mark.integration
def test_delete_relic_non_owner(http, created_relic):
    other_key = uuid.uuid4().hex
    http.post("/api/v1/client/register", headers={"X-Client-Key": other_key})
    resp = http.delete(
        f"/api/v1/relics/{created_relic['id']}",
        headers={"X-Client-Key": other_key},
    )
    assert resp.status_code == 403


@pytest.mark.integration
def test_delete_relic_not_found(http, registered_client):
    key, _ = registered_client
    resp = http.delete(
        "/api/v1/relics/nonexistent_relic_id_del",
        headers={"X-Client-Key": key},
    )
    assert resp.status_code == 404


# ── Fork ──────────────────────────────────────────────────────────────────────

@pytest.mark.integration
def test_fork_relic(http, created_relic, registered_client):
    key, _ = registered_client
    original_id = created_relic["id"]

    resp = http.post(
        f"/api/v1/relics/{original_id}/fork",
        headers={"X-Client-Key": key},
        files={"file": ("fork.txt", b"Forked content", "text/plain")},
    )
    assert resp.status_code == 200
    fork = resp.json()
    assert fork["fork_of"] == original_id
    assert "created_at" in fork

    http.delete(f"/api/v1/relics/{fork['id']}", headers={"X-Client-Key": key})


@pytest.mark.integration
def test_fork_nonexistent_relic(http):
    resp = http.post(
        "/api/v1/relics/nonexistent_relic_fork_id/fork",
        files={"file": ("test.txt", b"content", "text/plain")},
    )
    assert resp.status_code == 404


# ── Lineage ───────────────────────────────────────────────────────────────────

@pytest.mark.integration
def test_get_relic_lineage(http, created_relic, registered_client):
    key, _ = registered_client
    original_id = created_relic["id"]

    fork_resp = http.post(
        f"/api/v1/relics/{original_id}/fork",
        headers={"X-Client-Key": key},
        files={"file": ("fork.txt", b"Forked", "text/plain")},
    )
    fork_id = fork_resp.json()["id"]

    resp = http.get(f"/api/v1/relics/{fork_id}/lineage")
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_relic_id"] == fork_id
    assert data["root"]["id"] == original_id
    assert any(c["id"] == fork_id for c in data["root"]["children"])

    http.delete(f"/api/v1/relics/{fork_id}", headers={"X-Client-Key": key})


@pytest.mark.integration
def test_get_lineage_not_found(http):
    resp = http.get("/api/v1/relics/nonexistent_lineage_id_xyz/lineage")
    assert resp.status_code == 404


# ── Access level: restricted ──────────────────────────────────────────────────

@pytest.mark.integration
def test_access_level_restricted(http, registered_client):
    key, _ = registered_client

    create = http.post(
        "/api/v1/relics",
        headers={"X-Client-Key": key},
        data={"name": "Restricted", "access_level": "restricted"},
        files={"file": ("test.txt", b"secret", "text/plain")},
    )
    assert create.status_code == 200
    relic_id = create.json()["id"]

    # No key → 403
    assert http.get(f"/api/v1/relics/{relic_id}").status_code == 403

    # Wrong key → 403
    other_key, _ = (uuid.uuid4().hex, None)
    http.post("/api/v1/client/register", headers={"X-Client-Key": other_key})
    assert http.get(f"/api/v1/relics/{relic_id}", headers={"X-Client-Key": other_key}).status_code == 403

    # Owner → 200
    assert http.get(f"/api/v1/relics/{relic_id}", headers={"X-Client-Key": key}).status_code == 200

    http.delete(f"/api/v1/relics/{relic_id}", headers={"X-Client-Key": key})


# ── Relic access list (restricted access management) ─────────────────────────

@pytest.mark.integration
def test_relic_access_crud(http, registered_client):
    owner_key, _ = registered_client

    create = http.post(
        "/api/v1/relics",
        headers={"X-Client-Key": owner_key},
        data={"name": "Access Test", "access_level": "restricted"},
        files={"file": ("test.txt", b"secret", "text/plain")},
    )
    relic_id = create.json()["id"]

    # Register a second client
    target_key = uuid.uuid4().hex
    reg = http.post("/api/v1/client/register", headers={"X-Client-Key": target_key})
    target_public_id = reg.json()["public_id"]

    # GET — empty list
    resp = http.get(f"/api/v1/relics/{relic_id}/access", headers={"X-Client-Key": owner_key})
    assert resp.status_code == 200
    assert resp.json()["total"] == 0

    # POST — add target
    resp = http.post(
        f"/api/v1/relics/{relic_id}/access",
        headers={"X-Client-Key": owner_key},
        json={"public_id": target_public_id},
    )
    assert resp.status_code == 200
    assert resp.json()["public_id"] == target_public_id

    # Target can now access
    assert http.get(f"/api/v1/relics/{relic_id}", headers={"X-Client-Key": target_key}).status_code == 200

    # GET — 1 entry
    assert http.get(f"/api/v1/relics/{relic_id}/access", headers={"X-Client-Key": owner_key}).json()["total"] == 1

    # DELETE — remove target
    resp = http.delete(
        f"/api/v1/relics/{relic_id}/access/{target_public_id}",
        headers={"X-Client-Key": owner_key},
    )
    assert resp.status_code == 200

    # GET — empty again
    assert http.get(f"/api/v1/relics/{relic_id}/access", headers={"X-Client-Key": owner_key}).json()["total"] == 0

    http.delete(f"/api/v1/relics/{relic_id}", headers={"X-Client-Key": owner_key})


@pytest.mark.integration
def test_relic_access_unauthorized(http, created_relic):
    relic_id = created_relic["id"]
    other_key = uuid.uuid4().hex
    http.post("/api/v1/client/register", headers={"X-Client-Key": other_key})

    assert http.get(f"/api/v1/relics/{relic_id}/access").status_code == 401
    assert http.get(f"/api/v1/relics/{relic_id}/access", headers={"X-Client-Key": other_key}).status_code == 403


@pytest.mark.integration
def test_relic_access_duplicate(http, registered_client):
    key, _ = registered_client
    create = http.post(
        "/api/v1/relics",
        headers={"X-Client-Key": key},
        data={"access_level": "restricted"},
        files={"file": ("test.txt", b"content", "text/plain")},
    )
    relic_id = create.json()["id"]

    target_key = uuid.uuid4().hex
    reg = http.post("/api/v1/client/register", headers={"X-Client-Key": target_key})
    target_public_id = reg.json()["public_id"]

    http.post(f"/api/v1/relics/{relic_id}/access", headers={"X-Client-Key": key}, json={"public_id": target_public_id})
    resp = http.post(f"/api/v1/relics/{relic_id}/access", headers={"X-Client-Key": key}, json={"public_id": target_public_id})
    assert resp.status_code == 409

    http.delete(f"/api/v1/relics/{relic_id}", headers={"X-Client-Key": key})


@pytest.mark.integration
def test_relic_access_client_not_found(http, registered_client):
    key, _ = registered_client
    create = http.post(
        "/api/v1/relics",
        headers={"X-Client-Key": key},
        data={"access_level": "restricted"},
        files={"file": ("test.txt", b"content", "text/plain")},
    )
    relic_id = create.json()["id"]

    resp = http.post(
        f"/api/v1/relics/{relic_id}/access",
        headers={"X-Client-Key": key},
        json={"public_id": "nonexistent_public_id_xyz"},
    )
    assert resp.status_code == 404

    http.delete(f"/api/v1/relics/{relic_id}", headers={"X-Client-Key": key})

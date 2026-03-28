"""Integration tests for space endpoints."""
import uuid
import pytest
from conftest import ADMIN_KEY


@pytest.fixture
def space_owner(http):
    """Register a client and return (key, public_id)."""
    key = uuid.uuid4().hex
    resp = http.post("/api/v1/client/register", headers={"X-Client-Key": key})
    return key, resp.json()["public_id"]


@pytest.fixture
def public_space(http, space_owner):
    """Create a public space. Cleans up after."""
    key, _ = space_owner
    resp = http.post(
        "/api/v1/spaces",
        headers={"X-Client-Key": key},
        json={"name": "Public Test Space", "visibility": "public"},
    )
    assert resp.status_code == 200
    space_id = resp.json()["id"]
    yield space_id
    http.delete(f"/api/v1/spaces/{space_id}", headers={"X-Client-Key": key})


@pytest.fixture
def private_space(http, space_owner):
    """Create a private space. Cleans up after."""
    key, _ = space_owner
    resp = http.post(
        "/api/v1/spaces",
        headers={"X-Client-Key": key},
        json={"name": "Private Test Space", "visibility": "private"},
    )
    space_id = resp.json()["id"]
    yield space_id
    http.delete(f"/api/v1/spaces/{space_id}", headers={"X-Client-Key": key})


@pytest.fixture
def relic_in_space(http, space_owner):
    """Create a public relic owned by the space owner. Cleans up after."""
    key, _ = space_owner
    resp = http.post(
        "/api/v1/relics",
        headers={"X-Client-Key": key},
        data={"name": "Space Relic", "access_level": "public"},
        files={"file": ("test.txt", b"space content", "text/plain")},
    )
    relic_id = resp.json()["id"]
    yield relic_id
    http.delete(f"/api/v1/relics/{relic_id}", headers={"X-Client-Key": key})


# ── POST /api/v1/spaces ───────────────────────────────────────────────────────

@pytest.mark.integration
def test_create_space(http, space_owner):
    key, _ = space_owner
    resp = http.post(
        "/api/v1/spaces",
        headers={"X-Client-Key": key},
        json={"name": "My New Space", "visibility": "public"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "My New Space"
    assert data["visibility"] == "public"
    assert data["owner_client_id"] == key
    assert data["role"] == "owner"
    assert "id" in data

    http.delete(f"/api/v1/spaces/{data['id']}", headers={"X-Client-Key": key})


@pytest.mark.integration
def test_create_space_unauthorized(http):
    resp = http.post("/api/v1/spaces", json={"name": "No Auth Space", "visibility": "public"})
    assert resp.status_code == 401


# ── GET /api/v1/spaces ────────────────────────────────────────────────────────

@pytest.mark.integration
def test_list_spaces(http, space_owner, public_space):
    key, _ = space_owner
    resp = http.get("/api/v1/spaces", headers={"X-Client-Key": key})
    assert resp.status_code == 200
    data = resp.json()
    assert "spaces" in data
    assert "total" in data
    ids = [s["id"] for s in data["spaces"]]
    assert public_space in ids


# ── GET /api/v1/spaces/{space_id} ────────────────────────────────────────────

@pytest.mark.integration
def test_get_space(http, space_owner, public_space):
    key, _ = space_owner
    resp = http.get(f"/api/v1/spaces/{public_space}", headers={"X-Client-Key": key})
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == public_space
    assert data["name"] == "Public Test Space"


@pytest.mark.integration
def test_get_space_not_found(http):
    resp = http.get("/api/v1/spaces/nonexistent_space_id_xyz")
    assert resp.status_code == 404


@pytest.mark.integration
def test_get_private_space_no_access(http, space_owner, private_space):
    other_key = uuid.uuid4().hex
    http.post("/api/v1/client/register", headers={"X-Client-Key": other_key})
    resp = http.get(f"/api/v1/spaces/{private_space}", headers={"X-Client-Key": other_key})
    assert resp.status_code == 403


# ── PUT /api/v1/spaces/{space_id} ────────────────────────────────────────────

@pytest.mark.integration
def test_update_space(http, space_owner, public_space):
    key, _ = space_owner
    resp = http.put(
        f"/api/v1/spaces/{public_space}",
        headers={"X-Client-Key": key},
        json={"name": "Renamed Space"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed Space"


@pytest.mark.integration
def test_update_space_unauthorized(http, public_space):
    resp = http.put(f"/api/v1/spaces/{public_space}", json={"name": "Hacked"})
    assert resp.status_code == 401


@pytest.mark.integration
def test_update_space_non_owner(http, space_owner, public_space):
    other_key = uuid.uuid4().hex
    http.post("/api/v1/client/register", headers={"X-Client-Key": other_key})
    resp = http.put(
        f"/api/v1/spaces/{public_space}",
        headers={"X-Client-Key": other_key},
        json={"name": "Hacked"},
    )
    assert resp.status_code == 403


# ── DELETE /api/v1/spaces/{space_id} ─────────────────────────────────────────

@pytest.mark.integration
def test_delete_space(http, space_owner):
    key, _ = space_owner
    create = http.post(
        "/api/v1/spaces",
        headers={"X-Client-Key": key},
        json={"name": "To Delete", "visibility": "public"},
    )
    space_id = create.json()["id"]

    resp = http.delete(f"/api/v1/spaces/{space_id}", headers={"X-Client-Key": key})
    assert resp.status_code == 200
    assert http.get(f"/api/v1/spaces/{space_id}").status_code == 404


@pytest.mark.integration
def test_delete_space_unauthorized(http, public_space):
    resp = http.delete(f"/api/v1/spaces/{public_space}")
    assert resp.status_code == 401


@pytest.mark.integration
def test_delete_space_non_owner(http, space_owner, public_space):
    other_key = uuid.uuid4().hex
    http.post("/api/v1/client/register", headers={"X-Client-Key": other_key})
    resp = http.delete(f"/api/v1/spaces/{public_space}", headers={"X-Client-Key": other_key})
    assert resp.status_code == 403


# ── POST /api/v1/spaces/{space_id}/transfer-ownership ────────────────────────

@pytest.mark.integration
def test_transfer_space_ownership(http, space_owner):
    key, _ = space_owner

    create = http.post(
        "/api/v1/spaces",
        headers={"X-Client-Key": key},
        json={"name": "Transfer Space", "visibility": "public"},
    )
    space_id = create.json()["id"]

    new_owner_key = uuid.uuid4().hex
    reg = http.post("/api/v1/client/register", headers={"X-Client-Key": new_owner_key})
    new_owner_public_id = reg.json()["public_id"]

    resp = http.post(
        f"/api/v1/spaces/{space_id}/transfer-ownership",
        headers={"X-Client-Key": key},
        json={"public_id": new_owner_public_id},
    )
    assert resp.status_code == 200
    assert resp.json()["owner_client_id"] == new_owner_key

    http.delete(f"/api/v1/spaces/{space_id}", headers={"X-Client-Key": new_owner_key})


@pytest.mark.integration
def test_transfer_ownership_not_owner(http, space_owner, public_space):
    other_key = uuid.uuid4().hex
    reg = http.post("/api/v1/client/register", headers={"X-Client-Key": other_key})
    other_public_id = reg.json()["public_id"]

    resp = http.post(
        f"/api/v1/spaces/{public_space}/transfer-ownership",
        headers={"X-Client-Key": other_key},
        json={"public_id": other_public_id},
    )
    assert resp.status_code == 403


@pytest.mark.integration
def test_transfer_ownership_target_not_found(http, space_owner, public_space):
    key, _ = space_owner
    resp = http.post(
        f"/api/v1/spaces/{public_space}/transfer-ownership",
        headers={"X-Client-Key": key},
        json={"public_id": "nonexistent_public_id_xyz"},
    )
    assert resp.status_code == 404


# ── GET /api/v1/spaces/{space_id}/relics ─────────────────────────────────────

@pytest.mark.integration
def test_get_space_relics(http, space_owner, public_space):
    resp = http.get(f"/api/v1/spaces/{public_space}/relics")
    assert resp.status_code == 200
    data = resp.json()
    assert "relics" in data
    assert "total" in data


# ── POST /api/v1/spaces/{space_id}/relics ────────────────────────────────────

@pytest.mark.integration
def test_add_relic_to_space(http, space_owner, public_space, relic_in_space):
    key, _ = space_owner
    relic_id = relic_in_space

    resp = http.post(
        f"/api/v1/spaces/{public_space}/relics?relic_id={relic_id}",
        headers={"X-Client-Key": key},
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Relic added to space successfully"

    relics_resp = http.get(f"/api/v1/spaces/{public_space}/relics")
    ids = [r["id"] for r in relics_resp.json()["relics"]]
    assert relic_id in ids


@pytest.mark.integration
def test_add_relic_to_space_no_auth(http, public_space, relic_in_space):
    resp = http.post(f"/api/v1/spaces/{public_space}/relics?relic_id={relic_in_space}")
    assert resp.status_code == 401


# ── DELETE /api/v1/spaces/{space_id}/relics/{relic_id} ───────────────────────

@pytest.mark.integration
def test_remove_relic_from_space(http, space_owner, public_space, relic_in_space):
    key, _ = space_owner
    relic_id = relic_in_space

    http.post(f"/api/v1/spaces/{public_space}/relics?relic_id={relic_id}", headers={"X-Client-Key": key})

    resp = http.delete(
        f"/api/v1/spaces/{public_space}/relics/{relic_id}",
        headers={"X-Client-Key": key},
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Relic removed from space successfully"


# ── GET /api/v1/spaces/{space_id}/access ─────────────────────────────────────

@pytest.mark.integration
def test_get_space_access_list(http, space_owner, private_space):
    key, _ = space_owner
    resp = http.get(f"/api/v1/spaces/{private_space}/access", headers={"X-Client-Key": key})
    assert resp.status_code == 200
    data = resp.json()
    assert "owner" in data
    assert "access" in data
    assert data["owner"]["role"] == "owner"


@pytest.mark.integration
def test_get_space_access_list_unauthorized(http, space_owner, private_space):
    other_key = uuid.uuid4().hex
    http.post("/api/v1/client/register", headers={"X-Client-Key": other_key})
    resp = http.get(f"/api/v1/spaces/{private_space}/access", headers={"X-Client-Key": other_key})
    assert resp.status_code == 403


# ── POST /api/v1/spaces/{space_id}/access ────────────────────────────────────

@pytest.mark.integration
def test_add_space_access(http, space_owner, private_space):
    key, _ = space_owner

    target_key = uuid.uuid4().hex
    reg = http.post("/api/v1/client/register", headers={"X-Client-Key": target_key})
    target_public_id = reg.json()["public_id"]

    resp = http.post(
        f"/api/v1/spaces/{private_space}/access",
        headers={"X-Client-Key": key},
        json={"public_id": target_public_id, "role": "viewer"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["public_id"] == target_public_id
    assert data["role"] == "viewer"


@pytest.mark.integration
def test_add_space_access_not_authorized(http, space_owner, private_space):
    other_key = uuid.uuid4().hex
    reg = http.post("/api/v1/client/register", headers={"X-Client-Key": other_key})
    other_public_id = reg.json()["public_id"]

    resp = http.post(
        f"/api/v1/spaces/{private_space}/access",
        headers={"X-Client-Key": other_key},
        json={"public_id": other_public_id, "role": "viewer"},
    )
    assert resp.status_code == 403


# ── DELETE /api/v1/spaces/{space_id}/access/{access_id} ──────────────────────

@pytest.mark.integration
def test_remove_space_access(http, space_owner, private_space):
    key, _ = space_owner

    target_key = uuid.uuid4().hex
    reg = http.post("/api/v1/client/register", headers={"X-Client-Key": target_key})
    target_public_id = reg.json()["public_id"]

    add_resp = http.post(
        f"/api/v1/spaces/{private_space}/access",
        headers={"X-Client-Key": key},
        json={"public_id": target_public_id, "role": "viewer"},
    )
    access_id = add_resp.json()["id"]

    resp = http.delete(
        f"/api/v1/spaces/{private_space}/access/{access_id}",
        headers={"X-Client-Key": key},
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Access removed successfully"

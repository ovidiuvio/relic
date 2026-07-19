"""Integration tests for owner attribution (owner_name / owner_public_id).

These fields are computed properties on the Relic model, derived from the
owner's user row via joinedload(Relic.owner). They are surfaced
on every endpoint that returns relic metadata. This suite locks that contract
and the anonymous-owner behavior.
"""
import uuid
import pytest


@pytest.fixture
def named_owner(http):
    """A registered user with a display name set. Returns (key, public_id, name)."""
    key = uuid.uuid4().hex
    reg = http.post("/api/v1/user/register", headers={"X-User-Key": key})
    assert reg.status_code == 200
    public_id = reg.json()["public_id"]
    name = f"Owner {uuid.uuid4().hex[:8]}"
    resp = http.put(
        "/api/v1/user/name",
        headers={"X-User-Key": key},
        json={"name": name},
    )
    assert resp.status_code == 200
    return key, public_id, name


@pytest.fixture
def owned_relic(http, named_owner):
    """A public relic owned by the named user. Cleans up after."""
    key, public_id, name = named_owner
    resp = http.post(
        "/api/v1/relics",
        headers={"X-User-Key": key},
        data={"name": "Attributed Relic", "access_level": "public"},
        files={"file": ("test.txt", b"content", "text/plain")},
    )
    assert resp.status_code in (200, 201)
    relic_id = resp.json()["id"]
    yield relic_id, key, public_id, name
    http.delete(f"/api/v1/relics/{relic_id}", headers={"X-User-Key": key})


@pytest.mark.integration
def test_get_relic_includes_owner(http, owned_relic):
    relic_id, key, public_id, name = owned_relic
    data = http.get(f"/api/v1/relics/{relic_id}").json()
    assert data["owner_name"] == name
    assert data["owner_public_id"] == public_id


@pytest.mark.integration
def test_update_relic_response_includes_owner(http, owned_relic):
    """update_relic returns the ORM object after db.refresh(); the owner
    relationship must survive the refresh and serialize (fail-fast guard)."""
    relic_id, key, public_id, name = owned_relic
    resp = http.put(
        f"/api/v1/relics/{relic_id}",
        headers={"X-User-Key": key},
        json={"name": "Renamed"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["owner_name"] == name
    assert data["owner_public_id"] == public_id


@pytest.mark.integration
def test_list_relics_includes_owner(http, owned_relic):
    relic_id, key, public_id, name = owned_relic
    data = http.get("/api/v1/relics", params={"limit": 100}).json()
    relic = next((r for r in data["relics"] if r["id"] == relic_id), None)
    assert relic is not None, "relic missing from public list"
    assert relic["owner_name"] == name
    assert relic["owner_public_id"] == public_id


@pytest.mark.integration
def test_user_relics_includes_owner(http, owned_relic):
    relic_id, key, public_id, name = owned_relic
    data = http.get("/api/v1/user/relics", headers={"X-User-Key": key}).json()
    relic = next((r for r in data["relics"] if r["id"] == relic_id), None)
    assert relic is not None
    assert relic["owner_name"] == name
    assert relic["owner_public_id"] == public_id


@pytest.mark.integration
def test_bookmarks_include_owner(http, owned_relic):
    relic_id, key, public_id, name = owned_relic
    bookmarker = uuid.uuid4().hex
    http.post("/api/v1/user/register", headers={"X-User-Key": bookmarker})
    add = http.post(
        f"/api/v1/bookmarks?relic_id={relic_id}",
        headers={"X-User-Key": bookmarker},
    )
    assert add.status_code == 200

    data = http.get("/api/v1/bookmarks", headers={"X-User-Key": bookmarker}).json()
    bm = next((b for b in data["bookmarks"] if b["id"] == relic_id), None)
    assert bm is not None
    assert bm["owner_name"] == name
    assert bm["owner_public_id"] == public_id


@pytest.mark.integration
def test_space_relics_include_owner(http, owned_relic):
    relic_id, key, public_id, name = owned_relic
    space = http.post(
        "/api/v1/spaces",
        headers={"X-User-Key": key},
        json={"name": "Attribution Space", "visibility": "public"},
    )
    assert space.status_code in (200, 201)
    space_id = space.json()["id"]
    try:
        add = http.post(
            f"/api/v1/spaces/{space_id}/relics?relic_id={relic_id}",
            headers={"X-User-Key": key},
        )
        assert add.status_code in (200, 201)

        data = http.get(
            f"/api/v1/spaces/{space_id}/relics", headers={"X-User-Key": key}
        ).json()
        relic = next((r for r in data["relics"] if r["id"] == relic_id), None)
        assert relic is not None
        assert relic["owner_name"] == name
        assert relic["owner_public_id"] == public_id
    finally:
        http.delete(f"/api/v1/spaces/{space_id}", headers={"X-User-Key": key})


@pytest.mark.integration
def test_anonymous_relic_has_null_owner(http):
    """A relic with no user association reports null owner fields, not an error."""
    resp = http.post(
        "/api/v1/relics",
        data={"name": "Anon Relic", "access_level": "public"},
        files={"file": ("test.txt", b"content", "text/plain")},
    )
    assert resp.status_code in (200, 201)
    relic_id = resp.json()["id"]
    try:
        data = http.get(f"/api/v1/relics/{relic_id}").json()
        assert data["owner_name"] is None
        assert data["owner_public_id"] is None
    finally:
        http.delete(f"/api/v1/relics/{relic_id}")

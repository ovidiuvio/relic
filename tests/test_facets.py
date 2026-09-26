"""Integration tests for the relic list type filter (?types=) and facets (?facets=true).

Each test works on a fresh user's own relics via /api/v1/user/relics, so other data on the
deployment can't change the counts.
"""
import uuid
import pytest


@pytest.fixture
def facet_user(http):
    key = uuid.uuid4().hex
    headers = {"X-User-Key": key}
    http.post("/api/v1/user/register", headers=headers)
    return headers


@pytest.fixture
def make_relic(http, facet_user):
    """Create a relic with a content type and tags; deletes them afterwards."""
    created = []

    def make(name, content_type, tags=()):
        data = {"name": name, "access_level": "private"}
        if tags:
            data["tags"] = ",".join(tags)
        resp = http.post(
            "/api/v1/relics",
            headers=facet_user,
            data=data,
            files={"file": (name, b"content", content_type)},
        )
        assert resp.status_code == 200, resp.text
        created.append(resp.json()["id"])
        return resp.json()["id"]

    yield make
    for relic_id in created:
        http.delete(f"/api/v1/relics/{relic_id}", headers=facet_user)


def user_relics(http, headers, **params):
    resp = http.get("/api/v1/user/relics", headers=headers, params={"limit": 100, **params})
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.mark.integration
def test_types_filter(http, facet_user, make_relic):
    py = make_relic("a.py", "text/x-python")
    js = make_relic("b.js", "text/javascript")
    make_relic("c.png", "image/png")

    data = user_relics(http, facet_user, types="text/x-python,text/javascript")
    assert {r["id"] for r in data["relics"]} == {py, js}
    assert data["total"] == 2

    # Case and parameters in the filter value don't matter.
    data = user_relics(http, facet_user, types="TEXT/X-PYTHON; charset=utf-8")
    assert [r["id"] for r in data["relics"]] == [py]

    # No filter: everything.
    assert user_relics(http, facet_user)["total"] == 3


@pytest.mark.integration
def test_types_filter_matches_stored_parameters(http, facet_user, make_relic):
    """A relic stored as 'text/plain; charset=utf-8' is found by 'text/plain'."""
    plain = make_relic("notes.txt", "text/plain; charset=utf-8")
    data = user_relics(http, facet_user, types="text/plain")
    assert [r["id"] for r in data["relics"]] == [plain]


@pytest.mark.integration
def test_facets_count_types_and_tags(http, facet_user, make_relic):
    make_relic("a.py", "text/x-python", tags=("alpha", "beta"))
    make_relic("b.py", "text/x-python", tags=("alpha",))
    make_relic("c.txt", "text/plain; charset=utf-8", tags=("alpha",))

    data = user_relics(http, facet_user, facets="true")
    facets = data["facets"]
    # Parameters are dropped and merged into the bare type.
    assert facets["types"] == {"text/x-python": 2, "text/plain": 1}
    assert facets["tags"][0] == {"name": "alpha", "count": 3}
    assert {"name": "beta", "count": 1} in facets["tags"]

    # Facets describe the list before its type filter, so every facet shows what it would give.
    data = user_relics(http, facet_user, facets="true", types="text/plain")
    assert data["total"] == 1
    assert data["facets"]["types"] == {"text/x-python": 2, "text/plain": 1}

    # They follow the other filters (tag here).
    data = user_relics(http, facet_user, facets="true", tag="beta")
    assert data["facets"]["types"] == {"text/x-python": 1}


@pytest.mark.integration
def test_facets_only_when_asked(http, facet_user, make_relic):
    make_relic("a.py", "text/x-python")
    assert user_relics(http, facet_user).get("facets") is None


@pytest.mark.integration
def test_facets_on_recent(http):
    """The public list returns facets through its response schema."""
    resp = http.get("/api/v1/relics", params={"limit": 1, "facets": "true"})
    assert resp.status_code == 200
    facets = resp.json()["facets"]
    assert isinstance(facets["types"], dict)
    assert isinstance(facets["tags"], list)


@pytest.mark.integration
def test_owner_filter(http):
    """?owner= (a public ID) narrows a list to one owner's relics, and the facets follow it."""
    token = uuid.uuid4().hex[:12]
    users = []
    for content_type in ("text/x-python", "image/png"):
        key = uuid.uuid4().hex
        public_id = http.post("/api/v1/user/register", headers={"X-User-Key": key}).json()["public_id"]
        relic = http.post(
            "/api/v1/relics",
            headers={"X-User-Key": key},
            data={"name": f"owner-{token}", "access_level": "public"},
            files={"file": ("f", b"content", content_type)},
        ).json()["id"]
        users.append((key, public_id, relic))
    try:
        (_, alice, alice_relic), (_, bob, bob_relic) = users
        base = {"search": token, "limit": 100}
        both = http.get("/api/v1/relics", params=base).json()
        assert {r["id"] for r in both["relics"]} == {alice_relic, bob_relic}

        data = http.get("/api/v1/relics", params={**base, "owner": alice, "facets": "true"}).json()
        assert [r["id"] for r in data["relics"]] == [alice_relic]
        assert data["facets"]["types"] == {"text/x-python": 1}

        data = http.get("/api/v1/relics", params={**base, "owner": "0000000000000000"}).json()
        assert data["relics"] == [] and data["total"] == 0
    finally:
        for key, _, relic in users:
            http.delete(f"/api/v1/relics/{relic}", headers={"X-User-Key": key})


@pytest.mark.integration
def test_tag_counts_follow_the_type_filter(http, facet_user, make_relic):
    """Tag counts describe the list as shown; type counts still ignore the type filter."""
    make_relic("a.py", "text/x-python", tags=("shared", "py-only"))
    make_relic("b.txt", "text/plain", tags=("shared",))
    data = user_relics(http, facet_user, facets="true", types="text/x-python")
    assert data["facets"]["types"] == {"text/x-python": 1, "text/plain": 1}
    assert {t["name"]: t["count"] for t in data["facets"]["tags"]} == {"shared": 1, "py-only": 1}


@pytest.mark.integration
def test_size_and_date_filters(http, facet_user):
    from datetime import datetime, timedelta, timezone
    created = []
    for name, size in (("small.txt", 10), ("medium.txt", 2000), ("large.txt", 50000)):
        resp = http.post(
            "/api/v1/relics", headers=facet_user,
            data={"name": name, "access_level": "private"},
            files={"file": (name, b"x" * size, "text/plain")},
        )
        assert resp.status_code == 200, resp.text
        created.append(resp.json())
    try:
        names = lambda **p: sorted(r["name"] for r in user_relics(http, facet_user, **p)["relics"])
        assert names(min_size=2000) == ["large.txt", "medium.txt"]  # inclusive
        assert names(max_size=2000) == ["medium.txt", "small.txt"]  # inclusive
        assert names(min_size=11, max_size=49999) == ["medium.txt"]

        now = datetime.now(timezone.utc)
        hour = timedelta(hours=1)
        assert names(created_after=(now - hour).isoformat()) == ["large.txt", "medium.txt", "small.txt"]
        assert names(created_after=(now + hour).isoformat()) == []
        assert names(created_before=(now - hour).isoformat()) == []
        assert names(created_before=(now + hour).isoformat(), min_size=11) == ["large.txt", "medium.txt"]
        # A timezone offset is honoured: the same instant written in UTC+02:00.
        plus2 = (now - hour).astimezone(timezone(timedelta(hours=2))).isoformat()
        assert names(created_after=plus2) == ["large.txt", "medium.txt", "small.txt"]

        bad = http.get("/api/v1/user/relics", headers=facet_user, params={"created_after": "not a date"})
        assert bad.status_code == 422
        bad = http.get("/api/v1/user/relics", headers=facet_user, params={"min_size": -1})
        assert bad.status_code == 422

        # The public list and the facets take the same filters.
        public = http.get("/api/v1/relics", params={"limit": 1, "min_size": 10**12, "facets": "true"})
        assert public.status_code == 200 and public.json()["total"] == 0 and public.json()["facets"]["types"] == {}
    finally:
        for relic in created:
            http.delete(f"/api/v1/relics/{relic['id']}", headers=facet_user)

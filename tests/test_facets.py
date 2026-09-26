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

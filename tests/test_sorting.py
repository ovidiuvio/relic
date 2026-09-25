"""Integration tests for relic list sorting (shared by recent, user, bookmark and space lists).

Each test works on a fresh user's own relics via /api/v1/user/relics, so other data on the
deployment can't change the expected order.
"""
import uuid
import pytest
from conftest import ADMIN_KEY


@pytest.fixture
def sort_user(http):
    """A named user (commenting needs a display name). Returns request headers."""
    key = uuid.uuid4().hex
    headers = {"X-User-Key": key}
    http.post("/api/v1/user/register", headers=headers)
    http.put("/api/v1/user/name", headers=headers, json={"name": "Sort Tester"})
    return headers


@pytest.fixture
def make_relic(http, sort_user):
    """Create relics for the sort user; deletes them (forks first) afterwards."""
    created = []

    def make(name, fork_of=None):
        if fork_of:
            resp = http.post(
                f"/api/v1/relics/{fork_of}/fork",
                headers=sort_user,
                data={"name": name, "access_level": "public"},
                files={"file": ("f.txt", b"forked", "text/plain")},
            )
        else:
            resp = http.post(
                "/api/v1/relics",
                headers=sort_user,
                data={"name": name, "access_level": "public"},
                files={"file": ("t.txt", b"line1\nline2", "text/plain")},
            )
        assert resp.status_code == 200
        created.append(resp.json()["id"])
        return resp.json()["id"]

    yield make
    for relic_id in reversed(created):
        http.delete(f"/api/v1/relics/{relic_id}", headers=sort_user)


def user_relics(http, headers, **params):
    resp = http.get("/api/v1/user/relics", headers=headers, params={"limit": 100, **params})
    assert resp.status_code == 200
    return resp.json()["relics"]


@pytest.mark.integration
def test_sort_by_forks_count(http, sort_user, make_relic):
    none = make_relic("no forks")
    two = make_relic("two forks")
    one = make_relic("one fork")
    make_relic("fork a", fork_of=two)
    make_relic("fork b", fork_of=two)
    make_relic("fork c", fork_of=one)

    rows = user_relics(http, sort_user, sort_by="forks_count", sort_order="desc")
    order = [r["id"] for r in rows if r["id"] in (none, one, two)]
    assert order == [two, one, none]
    counts = {r["id"]: r["forks_count"] for r in rows}
    assert (counts[two], counts[one], counts[none]) == (2, 1, 0)

    rows = user_relics(http, sort_user, sort_by="forks_count", sort_order="asc")
    assert [r["id"] for r in rows if r["id"] in (none, one, two)] == [none, one, two]


@pytest.mark.integration
def test_sort_by_comments_count(http, sort_user, make_relic):
    quiet = make_relic("quiet")
    busy = make_relic("busy")
    some = make_relic("some")
    for relic_id, n in ((busy, 3), (some, 1)):
        for i in range(n):
            resp = http.post(
                f"/api/v1/relics/{relic_id}/comments",
                headers=sort_user,
                json={"line_number": 1, "content": f"comment {i}"},
            )
            assert resp.status_code == 200

    rows = user_relics(http, sort_user, sort_by="comments_count", sort_order="desc")
    assert [r["id"] for r in rows] == [busy, some, quiet]
    assert [r["comments_count"] for r in rows] == [3, 1, 0]


@pytest.mark.integration
def test_sort_by_name_ignores_case(http, sort_user, make_relic):
    make_relic("banana")
    make_relic("Apple")
    make_relic("cherry")

    rows = user_relics(http, sort_user, sort_by="name", sort_order="asc")
    assert [r["name"] for r in rows] == ["Apple", "banana", "cherry"]


@pytest.mark.integration
def test_tied_sort_pages_without_repeats(http, sort_user, make_relic):
    """Every relic ties on views; offset pages must still cover each relic exactly once."""
    ids = {make_relic(f"tie {i}") for i in range(7)}

    seen = []
    for offset in range(0, 7, 2):
        resp = http.get(
            "/api/v1/user/relics",
            headers=sort_user,
            params={"sort_by": "access_count", "sort_order": "desc", "limit": 2, "offset": offset},
        )
        assert resp.status_code == 200
        seen += [r["id"] for r in resp.json()["relics"]]

    assert len(seen) == len(set(seen)) == 7
    assert set(seen) == ids


@pytest.mark.integration
def test_sort_by_owner(http):
    """Owners sort by display name, ignoring case; anonymous relics come last either way."""
    token = f"ownersort-{uuid.uuid4().hex[:8]}"
    created = []  # (id, headers)

    def relic_by(name):
        headers = {}
        if name is not None:
            headers = {"X-User-Key": uuid.uuid4().hex}
            http.post("/api/v1/user/register", headers=headers)
            http.put("/api/v1/user/name", headers=headers, json={"name": name})
        resp = http.post(
            "/api/v1/relics",
            headers=headers,
            data={"name": f"{token} {name}", "access_level": "public"},
            files={"file": ("t.txt", b"owner sort", "text/plain")},
        )
        assert resp.status_code == 200
        created.append((resp.json()["id"], headers))
        return resp.json()["id"]

    try:
        bob = relic_by("bob")
        anon = relic_by(None)
        alice = relic_by("Alice")
        carol = relic_by("carol")

        def order(direction):
            resp = http.get(
                "/api/v1/relics",
                params={"search": token, "sort_by": "owner", "sort_order": direction, "limit": 10},
            )
            assert resp.status_code == 200
            return [r["id"] for r in resp.json()["relics"]]

        assert order("asc") == [alice, bob, carol, anon]
        assert order("desc") == [carol, bob, alice, anon]
    finally:
        for relic_id, headers in created:
            if headers:
                http.delete(f"/api/v1/relics/{relic_id}", headers=headers)
            else:
                http.delete(f"/api/v1/relics/{relic_id}", headers={"X-User-Key": ADMIN_KEY})

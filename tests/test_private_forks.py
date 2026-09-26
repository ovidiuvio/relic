"""Integration tests: the IDs of private relics must not leak through fork relationships.

A private relic's ID is its access token, so neither a lineage tree nor a fork's fork_of may
show it to someone who doesn't own it.
"""
import uuid
import pytest
from conftest import ADMIN_KEY


@pytest.fixture
def make_user(http):
    def make():
        key = uuid.uuid4().hex
        http.post("/api/v1/user/register", headers={"X-User-Key": key})
        return {"X-User-Key": key}
    return make


@pytest.fixture
def relics(http):
    """Create relics and forks; deletes them afterwards, forks first."""
    created = []

    def create(headers, access_level, name):
        resp = http.post(
            "/api/v1/relics",
            headers=headers,
            data={"name": name, "access_level": access_level},
            files={"file": ("a.txt", b"content", "text/plain")},
        )
        assert resp.status_code == 200, resp.text
        created.append((resp.json()["id"], headers))
        return resp.json()["id"]

    def fork(headers, parent, access_level, name):
        resp = http.post(
            f"/api/v1/relics/{parent}/fork",
            headers=headers,
            data={"name": name, "access_level": access_level},
        )
        assert resp.status_code == 200, resp.text
        created.append((resp.json()["id"], headers))
        return resp.json()["id"]

    yield create, fork
    for relic_id, headers in reversed(created):
        http.delete(f"/api/v1/relics/{relic_id}", headers=headers)


def lineage(http, relic_id, headers=None):
    resp = http.get(f"/api/v1/relics/{relic_id}/lineage", headers=headers or {})
    assert resp.status_code == 200, resp.text
    return resp


@pytest.mark.integration
def test_lineage_hides_private_forks(http, make_user, relics):
    create, fork = relics
    alice, bob = make_user(), make_user()
    parent = create(alice, "public", "parent")
    secret = fork(bob, parent, "private", "secret fork")
    shown = fork(bob, parent, "public", "public fork")

    resp = lineage(http, parent)
    assert secret not in resp.text
    assert "secret fork" not in resp.text
    children = resp.json()["root"]["children"]
    assert {c["id"] for c in children} == {shown, None}
    hidden = next(c for c in children if c["id"] is None)
    assert hidden["hidden"] is True and hidden["name"] is None and hidden["created_at"] is None
    assert resp.json()["total_nodes"] == 3

    # Its owner and admins see it.
    for headers in (bob, {"X-User-Key": ADMIN_KEY}):
        ids = {c["id"] for c in lineage(http, parent, headers).json()["root"]["children"]}
        assert ids == {shown, secret}


@pytest.mark.integration
def test_lineage_shows_the_relic_asked_about(http, make_user, relics):
    """Whoever has a private relic's ID sees it in its own tree, but not its private parent."""
    create, fork = relics
    alice, bob = make_user(), make_user()
    root = create(alice, "private", "private root")
    child = fork(alice, root, "private", "private child")

    data = lineage(http, child).json()
    assert root not in str(data)
    assert data["root"]["hidden"] is True
    assert data["root"]["children"][0]["id"] == child

    # A fork's owner sees the parent they forked from.
    mine = fork(bob, child, "private", "bob's fork")
    data = lineage(http, mine, bob).json()
    assert data["root"]["id"] is None
    assert data["root"]["children"][0]["id"] == child
    assert data["root"]["children"][0]["children"][0]["id"] == mine


@pytest.mark.integration
def test_fork_of_hides_private_parent(http, make_user, relics):
    create, fork = relics
    alice, bob = make_user(), make_user()
    parent = create(alice, "private", "private parent")
    child = fork(bob, parent, "public", "public child")

    anon = http.get(f"/api/v1/relics/{child}")
    assert anon.status_code == 200
    assert parent not in anon.text
    assert anon.json()["fork_of"] is None
    assert anon.json()["fork_of_hidden"] is True

    listed = http.get("/api/v1/relics", params={"search": child})
    assert listed.status_code == 200
    assert parent not in listed.text
    [row] = [r for r in listed.json()["relics"] if r["id"] == child]
    assert row["fork_of_hidden"] is True

    # The fork's owner, the parent's owner and admins see it.
    for headers in (bob, alice, {"X-User-Key": ADMIN_KEY}):
        data = http.get(f"/api/v1/relics/{child}", headers=headers).json()
        assert data["fork_of"] == parent
        assert data["fork_of_hidden"] is False


@pytest.mark.integration
def test_fork_of_public_parent_shown(http, make_user, relics):
    create, fork = relics
    alice, bob = make_user(), make_user()
    parent = create(alice, "public", "public parent")
    child = fork(bob, parent, "public", "public child")
    data = http.get(f"/api/v1/relics/{child}").json()
    assert data["fork_of"] == parent
    assert data["fork_of_hidden"] is False

"""Integration tests for universal search (/api/v1/search): it finds every relic the requester is
entitled to see, says why, and never anything else.

Each test uses fresh users and a unique token in names, so other data can't change the results.
"""
import uuid
import pytest
from conftest import ADMIN_KEY


def register(http):
    key = uuid.uuid4().hex
    public_id = http.post("/api/v1/user/register", headers={"X-User-Key": key}).json()["public_id"]
    return {"X-User-Key": key}, public_id


@pytest.fixture
def world(http):
    """Alice owns relics of every kind; Bob gets access to some of them in each possible way;
    Carol has no link to any of them."""
    token = uuid.uuid4().hex[:12]
    alice, alice_pid = register(http)
    bob, bob_pid = register(http)
    carol, _ = register(http)
    made, spaces = [], []

    def relic(name, access):
        resp = http.post(
            "/api/v1/relics", headers=alice,
            data={"name": f"{token} {name}", "access_level": access},
            files={"file": ("f.txt", b"x", "text/plain")},
        )
        assert resp.status_code == 200, resp.text
        made.append(resp.json()["id"])
        return resp.json()["id"]

    ids = {
        "public": relic("public", "public"),
        "private": relic("private", "private"),
        "bookmarked": relic("bookmarked", "private"),
        "shared": relic("shared", "restricted"),
        "restricted": relic("restricted", "restricted"),
        "in_space": relic("in space", "private"),
    }
    # Bob bookmarks one private relic (he had its link) and is on one restricted relic's list.
    assert http.post("/api/v1/bookmarks", headers=bob, params={"relic_id": ids["bookmarked"]}).status_code == 200
    assert http.post(f"/api/v1/relics/{ids['shared']}/access", headers=alice, json={"public_id": bob_pid}).status_code == 200
    # Alice's private space holds a private relic, and Bob is a member.
    space = http.post("/api/v1/spaces", headers=alice, json={"name": f"{token} space", "visibility": "private"}).json()
    spaces.append(space["id"])
    assert http.post(f"/api/v1/spaces/{space['id']}/relics", headers=alice, params={"relic_id": ids["in_space"]}).status_code == 200
    assert http.post(f"/api/v1/spaces/{space['id']}/access", headers=alice, json={"public_id": bob_pid, "role": "viewer"}).status_code == 200

    yield {"token": token, "ids": ids, "alice": alice, "bob": bob, "carol": carol, "space": space}
    for space_id in spaces:
        http.delete(f"/api/v1/spaces/{space_id}", headers=alice)
    for relic_id in made:
        http.delete(f"/api/v1/relics/{relic_id}", headers=alice)


def search(http, headers=None, **params):
    resp = http.get("/api/v1/search", headers=headers or {}, params={"limit": 100, **params})
    assert resp.status_code == 200, resp.text
    return resp.json()


def found(data, ids):
    """The fixture's names (public, private…) among the results."""
    by_id = {v: k for k, v in ids.items()}
    return {by_id[r["id"]] for r in data["relics"] if r["id"] in by_id}


@pytest.mark.integration
def test_everyone_sees_what_they_are_entitled_to(http, world):
    t, ids = world["token"], world["ids"]
    assert found(search(http, world["alice"], search=t), ids) == set(ids)  # all her own
    assert found(search(http, world["bob"], search=t), ids) == {"public", "bookmarked", "shared", "in_space"}
    assert found(search(http, world["carol"], search=t), ids) == {"public"}
    assert found(search(http, None, search=t), ids) == {"public"}  # anonymous


@pytest.mark.integration
def test_private_relics_never_leak_by_id(http, world):
    """A private relic's ID is its key: searching for it finds nothing without a right to it."""
    ids = world["ids"]
    for name in ("private", "restricted", "in_space", "bookmarked", "shared"):
        for who in (world["carol"], None):
            data = search(http, who, search=ids[name])
            assert ids[name] not in {r["id"] for r in data["relics"]}, name
            assert ids[name] not in str(data)
    # Bob can't find the ones he has no right to either.
    for name in ("private", "restricted"):
        assert ids[name] not in str(search(http, world["bob"], search=ids[name]))


@pytest.mark.integration
def test_each_result_says_why(http, world):
    t, ids = world["token"], world["ids"]
    rows = {r["id"]: r for r in search(http, world["bob"], search=t)["relics"]}
    assert rows[ids["public"]]["sources"] == ["public"]
    assert rows[ids["bookmarked"]]["sources"] == ["bookmarked"]
    assert rows[ids["shared"]]["sources"] == ["shared"]
    assert rows[ids["in_space"]]["sources"] == ["spaces"]
    assert rows[ids["in_space"]]["spaces"] == [{"id": world["space"]["id"], "name": world["space"]["name"]}]
    mine = {r["id"]: r for r in search(http, world["alice"], search=t)["relics"]}
    assert mine[ids["public"]]["sources"] == ["public", "yours"]
    assert "yours" in mine[ids["private"]]["sources"]


@pytest.mark.integration
def test_source_filter_and_counts(http, world):
    t, ids = world["token"], world["ids"]
    data = search(http, world["bob"], search=t, facets="true")
    assert data["facets"]["sources"] == {"public": 1, "yours": 0, "bookmarked": 1, "shared": 1, "spaces": 1}
    for source, expected in (("bookmarked", {"bookmarked"}), ("shared", {"shared"}), ("spaces", {"in_space"}), ("public", {"public"})):
        # Counts ignore the source filter, so every facet shows what it would give.
        narrowed = search(http, world["bob"], search=t, source=source, facets="true")
        assert found(narrowed, ids) == expected, source
        assert narrowed["facets"]["sources"]["bookmarked"] == 1
    assert search(http, None, search=t, source="yours")["total"] == 0  # anonymous has no "yours"


@pytest.mark.integration
def test_admins_get_the_user_view(http, world):
    """Admin rights don't widen search; the admin relic list is where admins see everything."""
    t, ids = world["token"], world["ids"]
    assert found(search(http, {"X-User-Key": ADMIN_KEY}, search=t), ids) == {"public"}


@pytest.mark.integration
def test_filters_apply(http, world):
    t, ids = world["token"], world["ids"]
    assert found(search(http, world["bob"], search=f"{t} space"), ids) == {"in_space"}
    assert found(search(http, world["bob"], search=t, types="application/zip"), ids) == set()
    assert search(http, world["bob"], search=t, min_size=10**9)["total"] == 0

"""Integration tests for pinned searches (/api/v1/user/searches)."""
import uuid
import pytest


@pytest.fixture
def user(http):
    key = uuid.uuid4().hex
    headers = {"X-User-Key": key}
    http.post("/api/v1/user/register", headers=headers)
    return headers


def pin(http, headers, path="/recent?search=queue&tag=work", query="queue tag:work", **extra):
    return http.post("/api/v1/user/searches", headers=headers, json={"query": query, "path": path, **extra})


@pytest.mark.integration
def test_pin_list_rename_unpin(http, user):
    resp = pin(http, user, name="  Work queue  ")
    assert resp.status_code == 200, resp.text
    saved = resp.json()
    assert saved["name"] == "Work queue"
    assert saved["query"] == "queue tag:work"
    assert saved["path"] == "/recent?search=queue&tag=work"

    second = pin(http, user, path="/my-relics?type=code", query="type:code").json()
    listed = http.get("/api/v1/user/searches", headers=user).json()["searches"]
    assert [s["id"] for s in listed] == [saved["id"], second["id"]]

    renamed = http.patch(f"/api/v1/user/searches/{saved['id']}", headers=user, json={"name": "Queue"})
    assert renamed.status_code == 200 and renamed.json()["name"] == "Queue"
    cleared = http.patch(f"/api/v1/user/searches/{saved['id']}", headers=user, json={"name": "  "})
    assert cleared.json()["name"] is None

    assert http.delete(f"/api/v1/user/searches/{saved['id']}", headers=user).status_code == 200
    listed = http.get("/api/v1/user/searches", headers=user).json()["searches"]
    assert [s["id"] for s in listed] == [second["id"]]


@pytest.mark.integration
def test_pinning_the_same_list_again_returns_the_pin(http, user):
    first = pin(http, user).json()
    again = pin(http, user, query="queue  tag:work").json()
    assert again["id"] == first["id"]
    assert len(http.get("/api/v1/user/searches", headers=user).json()["searches"]) == 1


@pytest.mark.integration
def test_pins_are_private(http, user):
    saved = pin(http, user).json()
    other = {"X-User-Key": uuid.uuid4().hex}
    http.post("/api/v1/user/register", headers=other)
    assert http.get("/api/v1/user/searches", headers=other).json()["searches"] == []
    assert http.patch(f"/api/v1/user/searches/{saved['id']}", headers=other, json={"name": "x"}).status_code == 404
    assert http.delete(f"/api/v1/user/searches/{saved['id']}", headers=other).status_code == 404


@pytest.mark.integration
@pytest.mark.parametrize("path", ["https://evil.example/", "//evil.example/x", "recent", "/\\evil.example"])
def test_only_app_paths(http, user, path):
    assert pin(http, user, path=path).status_code == 422


@pytest.mark.integration
def test_needs_a_user(http):
    assert http.get("/api/v1/user/searches").status_code == 401
    assert http.post("/api/v1/user/searches", json={"query": "x", "path": "/recent"}).status_code == 401


@pytest.mark.integration
def test_pin_limit(http, user):
    for i in range(50):
        assert pin(http, user, path=f"/recent?search=q{i}", query=f"q{i}").status_code == 200
    resp = pin(http, user, path="/recent?search=one-too-many", query="one-too-many")
    assert resp.status_code == 400

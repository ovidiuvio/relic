"""Integration tests for raw content endpoints."""
import pytest


@pytest.fixture
def relic_with_content(http, registered_client):
    key, _ = registered_client
    content = b"Raw content here"
    resp = http.post(
        "/api/v1/relics",
        headers={"X-Client-Key": key},
        data={"name": "Raw Test", "access_level": "public"},
        files={"file": ("test.txt", content, "text/plain")},
    )
    relic_id = resp.json()["id"]
    yield relic_id, content
    http.delete(f"/api/v1/relics/{relic_id}", headers={"X-Client-Key": key})


@pytest.mark.integration
def test_get_raw_via_raw_route(http, relic_with_content):
    relic_id, content = relic_with_content
    resp = http.get(f"/{relic_id}/raw")
    assert resp.status_code == 200
    assert resp.content == content


@pytest.mark.integration
def test_get_raw_via_root_route(http, relic_with_content):
    relic_id, content = relic_with_content
    resp = http.get(f"/{relic_id}")
    assert resp.status_code == 200
    assert resp.content == content

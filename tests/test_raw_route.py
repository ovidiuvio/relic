import pytest

@pytest.mark.unit
def test_get_raw_root_route(client):
    """Test getting raw relic content via /{relic_id}."""

    content = b"Raw content here"

    create_response = client.post(
        "/api/v1/relics",
        data={"name": "Raw Test"},
        files={"file": ("test.txt", content, "text/plain")}
    )
    assert create_response.status_code == 200
    relic_id = create_response.json()["id"]

    # Test getting raw content via /{relic_id}/raw (existing)
    response_raw = client.get(f"/{relic_id}/raw")
    assert response_raw.status_code == 200
    assert response_raw.content == content

    # Test getting raw content via /{relic_id} (new requirement)
    response_root = client.get(f"/{relic_id}")

    assert response_root.status_code == 200
    assert response_root.content == content

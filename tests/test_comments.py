import pytest

@pytest.mark.unit
def test_create_and_get_comment(client):
    # Register client
    import uuid
    client_key = uuid.uuid4().hex
    headers = {"X-Client-Key": client_key}
    response = client.post("/api/v1/client/register", headers=headers)
    assert response.status_code == 200

    # Set client name
    response = client.put("/api/v1/client/name", json={"name": "Test User"}, headers=headers)
    assert response.status_code == 200

    # Create a relic
    files = {"file": ("test.txt", b"test content")}
    response = client.post("/api/v1/relics", files=files, headers=headers)
    assert response.status_code == 200
    relic_id = response.json()["id"]

    # Create a comment
    comment_data = {"line_number": 1, "content": "This is a comment"}
    response = client.post(f"/api/v1/relics/{relic_id}/comments", json=comment_data, headers=headers)
    assert response.status_code == 200
    comment = response.json()
    assert comment["content"] == "This is a comment"
    assert comment["line_number"] == 1
    assert comment["author_name"] == "Test User"
    comment_id = comment["id"]

    # Get comments
    response = client.get(f"/api/v1/relics/{relic_id}/comments")
    assert response.status_code == 200
    data = response.json()
    comments = data["comments"]
    assert len(comments) == 1
    assert comments[0]["id"] == comment_id

    # Delete comment
    response = client.delete(f"/api/v1/relics/{relic_id}/comments/{comment_id}", headers=headers)
    assert response.status_code == 200

    # Verify deletion
    response = client.get(f"/api/v1/relics/{relic_id}/comments")
    assert response.status_code == 200
    assert len(response.json()["comments"]) == 0

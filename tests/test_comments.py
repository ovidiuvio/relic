from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_create_and_get_comment():
    # Create a relic first
    files = {"file": ("test.txt", "test content")}
    response = client.post("/api/v1/relics", files=files)
    assert response.status_code == 200
    relic_id = response.json()["id"]

    # Create a comment
    comment_data = {"line_number": 1, "content": "This is a comment"}
    response = client.post(f"/api/v1/relics/{relic_id}/comments", json=comment_data)
    assert response.status_code == 200
    comment = response.json()
    assert comment["content"] == "This is a comment"
    assert comment["line_number"] == 1
    comment_id = comment["id"]

    # Get comments
    response = client.get(f"/api/v1/relics/{relic_id}/comments")
    assert response.status_code == 200
    comments = response.json()
    assert len(comments) == 1
    assert comments[0]["id"] == comment_id

    # Delete comment
    response = client.delete(f"/api/v1/relics/{relic_id}/comments/{comment_id}")
    assert response.status_code == 200

    # Verify deletion
    response = client.get(f"/api/v1/relics/{relic_id}/comments")
    assert response.status_code == 200
    assert len(response.json()) == 0

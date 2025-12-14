from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.models import Relic, Comment
from backend.app.core.database import get_db
import pytest

client = TestClient(app)

def test_create_and_get_comment():
    # Setup client key
    headers = {"X-Client-Key": "test_client_key"}

    # Register client first to have a name
    client.put("/api/v1/client/name", json={"name": "Test User"}, headers=headers)

    # Create a relic first
    relic_data = {"content": "test content"}
    files = {"file": ("test.txt", "test content")}
    response = client.post("/api/v1/relics", files=files, headers=headers)
    assert response.status_code == 200
    relic_id = response.json()["id"]

    # Create a comment
    comment_data = {"line_number": 1, "content": "This is a comment"}
    response = client.post(f"/api/v1/relics/{relic_id}/comments", json=comment_data, headers=headers)

    # If 400 because name not set, set it (though we did above)
    if response.status_code == 400 and "display name" in response.text:
         client.put("/api/v1/client/name", json={"name": "Test User"}, headers=headers)
         response = client.post(f"/api/v1/relics/{relic_id}/comments", json=comment_data, headers=headers)

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
    response = client.delete(f"/api/v1/relics/{relic_id}/comments/{comment_id}", headers=headers)
    assert response.status_code == 200

    # Verify deletion
    response = client.get(f"/api/v1/relics/{relic_id}/comments")
    assert response.status_code == 200
    assert len(response.json()) == 0

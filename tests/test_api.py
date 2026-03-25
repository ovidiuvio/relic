"""Tests for the relic API endpoints."""
import pytest
from io import BytesIO


@pytest.mark.unit
def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.unit
def test_create_relic(client):
    """Test creating a new relic."""
    content = b"Hello, World!"

    response = client.post(
        "/api/v1/relics",
        data={
            "name": "Test Relic",
            "language_hint": "text",
            "access_level": "public"
        },
        files={"file": ("test.txt", BytesIO(content), "text/plain")}
    )

    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "url" in data
    assert "created_at" in data
    assert data["size_bytes"] == len(content)


@pytest.mark.unit
def test_get_relic(client, created_relic):
    """Test retrieving a relic."""
    relic_id = created_relic["id"]
    # Get the relic
    response = client.get(f"/api/v1/relics/{relic_id}")

    assert response.status_code == 200
    relic   = response.json()
    assert relic["id"] == relic_id
    assert relic["name"] == "Test Relic"
    assert relic["access_level"] == "public"


@pytest.mark.unit
def test_get_nonexistent_relic(client):
    """Test getting a relic that doesn't exist."""
    response = client.get("/api/v1/relics/nonexistent")
    assert response.status_code == 404
    assert "detail" in response.json()


@pytest.mark.unit
def test_edit_relic(client, created_relic):
    """Test editing a relic (updating metadata)."""
    original_id = created_relic["id"]
    client_key = created_relic["client_key"]

    # Edit the relic
    edit_response = client.put(
        f"/api/v1/relics/{original_id}",
        json={"name": "Updated Relic Name"},
        headers={"x-client-key": client_key}
    )

    assert edit_response.status_code == 200
    new_relic = edit_response.json()
    assert new_relic["id"] == original_id  # Same ID
    assert new_relic["name"] == "Updated Relic Name"


@pytest.mark.unit
def test_fork_relic(client, created_relic):
    """Test forking a relic (new lineage)."""
    original_id = created_relic["id"]

    # Fork the relic
    fork_response = client.post(
        f"/api/v1/relics/{original_id}/fork",
        files={"file": ("test.txt", BytesIO(b"Forked content"), "text/plain")}
    )

    assert fork_response.status_code == 200
    forked = fork_response.json()
    assert "created_at" in forked
    assert forked["fork_of"] == original_id


@pytest.mark.unit
def test_list_relics(client):
    """Test listing recent relics."""
    # Create a few relics
    for i in range(3):
        client.post(
            "/api/v1/relics",
            data={"name": f"Relic {i}"},
            files={"file": (f"test{i}.txt", BytesIO(b"Content"), "text/plain")}
        )

    # List relics
    response = client.get("/api/v1/relics?limit=10&offset=0")

    assert response.status_code == 200
    data = response.json()
    assert "relics" in data
    assert len(data["relics"]) >= 3




@pytest.mark.unit
def test_get_relic_lineage(client, created_relic):
    """Test getting version history (lineage)."""
    original_id = created_relic["id"]

    # Create a fork
    fork_response = client.post(
        f"/api/v1/relics/{original_id}/fork",
        files={"file": ("test.txt", BytesIO(b"Forked content"), "text/plain")}
    )
    fork_id = fork_response.json()["id"]

    # Get lineage
    history_response = client.get(f"/api/v1/relics/{fork_id}/lineage")

    assert history_response.status_code == 200
    history = history_response.json()
    assert history["current_relic_id"] == fork_id
    assert history["root"]["id"] == original_id
    assert len(history["root"]["children"]) == 1
    assert history["root"]["children"][0]["id"] == fork_id


@pytest.mark.unit
def test_get_raw_content(client, created_relic):
    """Test getting raw relic content."""
    relic_id = created_relic["id"]

    # Get raw
    response = client.get(f"/{relic_id}/raw")

    assert response.status_code == 200
    # Our mocked storage returns the original bytes "Hello, World! This is a test relic."
    assert b"Hello, World! This is a test relic." in response.content


@pytest.mark.unit
def test_delete_relic(client, created_relic):
    """Test deleting a relic."""
    relic_id = created_relic["id"]
    client_key = created_relic["client_key"]

    # Delete relic
    delete_response = client.delete(
        f"/api/v1/relics/{relic_id}",
        headers={"x-client-key": client_key}
    )

    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "Relic deleted successfully"

    # Verify relic is deleted (should be 404)
    get_response = client.get(f"/api/v1/relics/{relic_id}")
    assert get_response.status_code == 404


@pytest.mark.unit
def test_access_level_restricted(client):
    """Test restricted access level behavior."""
    # Create restricted relic
    create_response = client.post(
        "/api/v1/relics",
        headers={"x-client-key": "owner_key_123"},
        data={"name": "Restricted Relic", "access_level": "restricted"},
        files={"file": ("test.txt", b"secret", "text/plain")}
    )
    assert create_response.status_code == 200
    relic_id = create_response.json()["id"]

    # Access without key should fail
    response_no_key = client.get(f"/api/v1/relics/{relic_id}")
    assert response_no_key.status_code == 403
    assert response_no_key.json()["detail"] == "Access restricted"

    # Access with wrong key should fail
    response_wrong_key = client.get(
        f"/api/v1/relics/{relic_id}",
        headers={"x-client-key": "other_key_456"}
    )
    assert response_wrong_key.status_code == 403

    # Access with owner key should succeed
    response_owner_key = client.get(
        f"/api/v1/relics/{relic_id}",
        headers={"x-client-key": "owner_key_123"}
    )
    assert response_owner_key.status_code == 200
    assert response_owner_key.json()["name"] == "Restricted Relic"


@pytest.mark.unit
def test_password_protected_relic(client, db):
    """Test accessing a password-protected relic."""
    from backend.utils import hash_password
    from backend.models import Relic

    # Create relic
    create_response = client.post(
        "/api/v1/relics",
        data={"name": "Password Relic", "access_level": "public"},
        files={"file": ("test.txt", b"secret", "text/plain")}
    )
    assert create_response.status_code == 200
    relic_id = create_response.json()["id"]

    # Manually set password hash in db since create/update APIs don't seem to expose setting it directly right now
    relic = db.query(Relic).filter(Relic.id == relic_id).first()
    relic.password_hash = hash_password("secret123")
    db.commit()

    # Access without password should fail
    response_no_pass = client.get(f"/api/v1/relics/{relic_id}")
    assert response_no_pass.status_code == 403
    assert response_no_pass.json()["detail"] == "This relic requires a password"

    # Access with wrong password should fail
    response_wrong_pass = client.get(f"/api/v1/relics/{relic_id}?password=wrong")
    assert response_wrong_pass.status_code == 403
    assert response_wrong_pass.json()["detail"] == "Invalid password"

    # Access with correct password should succeed
    response_correct_pass = client.get(f"/api/v1/relics/{relic_id}?password=secret123")
    assert response_correct_pass.status_code == 200
    assert response_correct_pass.json()["name"] == "Password Relic"


@pytest.mark.unit
def test_expired_relic(client, db):
    """Test accessing an expired relic returns 410."""
    from backend.models import Relic
    from datetime import datetime, timedelta

    # Create relic
    create_response = client.post(
        "/api/v1/relics",
        data={"name": "Expired Relic", "access_level": "public"},
        files={"file": ("test.txt", b"expired", "text/plain")}
    )
    assert create_response.status_code == 200
    relic_id = create_response.json()["id"]

    # Manually set expiration date in the past
    relic = db.query(Relic).filter(Relic.id == relic_id).first()
    relic.expires_at = datetime.utcnow() - timedelta(days=1)
    db.commit()

    # Access should return 410 Gone
    response = client.get(f"/api/v1/relics/{relic_id}")
    assert response.status_code == 410
    assert response.json()["detail"] == "Relic has expired"

    # Raw access should also return 410
    raw_response = client.get(f"/{relic_id}/raw")
    assert raw_response.status_code == 410
    assert raw_response.json()["detail"] == "Relic has expired"

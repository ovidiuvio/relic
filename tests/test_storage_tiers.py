"""Tests for storage tiers."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from io import BytesIO
from backend.models import Relic
from backend.storage import storage_service

@pytest.fixture(autouse=True)
def mock_storage_methods():
    """Mock storage service methods for all tests in this module."""
    with patch.object(storage_service, 'ensure_bucket', MagicMock()) as mock_ensure, \
         patch.object(storage_service, 'upload', AsyncMock(return_value="mock_key")) as mock_upload, \
         patch.object(storage_service, 'download', AsyncMock(return_value=b"mock_content")) as mock_download, \
         patch.object(storage_service, 'delete', AsyncMock()) as mock_delete, \
         patch.object(storage_service, 'exists', AsyncMock(return_value=True)) as mock_exists:
        yield

@pytest.mark.unit
def test_storage_tiers_assignment(client, db):
    """Test that relics are assigned to the correct storage tier based on expiration."""

    # 1. Test ephemeral tier (with expiration)
    content_ephemeral = b"Ephemeral content"
    response_ephemeral = client.post(
        "/api/v1/relics",
        data={
            "name": "Ephemeral Relic",
            "expires_in": "1h"
        },
        files={"file": ("test_ephemeral.txt", BytesIO(content_ephemeral), "text/plain")}
    )

    assert response_ephemeral.status_code == 200
    relic_id_ephemeral = response_ephemeral.json()["id"]

    # Verify DB record
    relic_ephemeral = db.query(Relic).filter(Relic.id == relic_id_ephemeral).first()
    assert relic_ephemeral is not None
    assert relic_ephemeral.tier == "ephemeral"

    # Check that upload was called with correct tier
    storage_service.upload.assert_any_call(f"relics/{relic_id_ephemeral}", content_ephemeral, "text/plain", tier="ephemeral")

    # 2. Test standard tier (no expiration)
    content_standard = b"Standard content"
    response_standard = client.post(
        "/api/v1/relics",
        data={
            "name": "Standard Relic"
            # No expires_in
        },
        files={"file": ("test_standard.txt", BytesIO(content_standard), "text/plain")}
    )

    assert response_standard.status_code == 200
    relic_id_standard = response_standard.json()["id"]

    # Verify DB record
    relic_standard = db.query(Relic).filter(Relic.id == relic_id_standard).first()
    assert relic_standard is not None
    assert relic_standard.tier == "standard"

    storage_service.upload.assert_any_call(f"relics/{relic_id_standard}", content_standard, "text/plain", tier="standard")

@pytest.mark.unit
def test_storage_tiers_retrieval(client, db):
    """Test that relics can be retrieved from their respective tiers."""

    # Setup mock to return specific content
    storage_service.download.return_value = b"Retrievable Content"

    # Create ephemeral relic
    content = b"Retrievable Content"
    response = client.post(
        "/api/v1/relics",
        data={"name": "R", "expires_in": "1h"},
        files={"file": ("r.txt", BytesIO(content), "text/plain")}
    )
    relic_id = response.json()["id"]

    # Retrieve raw content
    raw_response = client.get(f"/{relic_id}/raw")
    assert raw_response.status_code == 200
    assert raw_response.content == content

    # Verify download was called with correct tier
    storage_service.download.assert_called_with(f"relics/{relic_id}", tier="ephemeral")

@pytest.mark.unit
def test_fork_storage_tier(client, db):
    """Test that forks respect the tier logic."""
    storage_service.download.return_value = b"Original Content"

    # Create original standard relic
    content = b"Original Content"
    create_response = client.post(
        "/api/v1/relics",
        data={"name": "Original"},
        files={"file": ("o.txt", BytesIO(content), "text/plain")}
    )
    original_id = create_response.json()["id"]

    # Fork with expiration (should be ephemeral)
    fork_response = client.post(
        f"/api/v1/relics/{original_id}/fork",
        data={"expires_in": "1h"}
    )
    assert fork_response.status_code == 200
    fork_id = fork_response.json()["id"]

    fork_relic = db.query(Relic).filter(Relic.id == fork_id).first()
    assert fork_relic.tier == "ephemeral"
    assert fork_relic.fork_of == original_id

    # Check upload call for fork. Using any order check.
    storage_service.upload.assert_any_call(f"relics/{fork_id}", content, "text/plain", tier="ephemeral")

    # Fork without expiration (should be standard)
    fork_response_2 = client.post(
        f"/api/v1/relics/{original_id}/fork",
        data={}
    )
    assert fork_response_2.status_code == 200
    fork_id_2 = fork_response_2.json()["id"]

    fork_relic_2 = db.query(Relic).filter(Relic.id == fork_id_2).first()
    assert fork_relic_2.tier == "standard"

    storage_service.upload.assert_any_call(f"relics/{fork_id_2}", content, "text/plain", tier="standard")

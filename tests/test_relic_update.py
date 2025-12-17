import pytest
from unittest.mock import MagicMock
from backend.models import Relic, ClientKey
from backend.storage import storage_service
from datetime import datetime, timedelta

# Mock storage service for this module
@pytest.fixture(autouse=True)
def mock_storage():
    storage_service.ensure_bucket = MagicMock()
    storage_service.upload = MagicMock()
    storage_service.download = MagicMock()
    storage_service.delete = MagicMock()

def test_update_relic(client, db):
    # Create owner
    owner_key = "owner_key_123"
    owner = ClientKey(id=owner_key, name="Owner")
    db.add(owner)

    # Create relic
    relic_id = "relic_to_update"
    relic = Relic(
        id=relic_id,
        client_id=owner_key,
        name="Original Name",
        content_type="text/plain",
        access_level="public",
        s3_key=f"relics/{relic_id}",
        size_bytes=100,
        created_at=datetime.utcnow()
    )
    db.add(relic)
    db.commit()

    # Test update as owner
    response = client.put(
        f"/api/v1/relics/{relic_id}",
        headers={"X-Client-Key": owner_key},
        json={
            "name": "Updated Name",
            "content_type": "application/json",
            "access_level": "private",
            "expires_in": "1h"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["content_type"] == "application/json"
    assert data["access_level"] == "private"
    assert data["expires_at"] is not None

    # Verify in DB - re-query to ensure fresh data
    updated_relic = db.query(Relic).filter(Relic.id == relic_id).first()
    assert updated_relic.name == "Updated Name"
    assert updated_relic.content_type == "application/json"
    assert updated_relic.access_level == "private"
    assert updated_relic.expires_at is not None

def test_update_relic_not_authorized(client, db):
    # Create owner
    owner_key = "owner_key_456"
    owner = ClientKey(id=owner_key, name="Owner")
    db.add(owner)

    # Create another user
    other_key = "other_key_789"
    other = ClientKey(id=other_key, name="Other")
    db.add(other)

    # Create relic
    relic_id = "relic_protected"
    relic = Relic(
        id=relic_id,
        client_id=owner_key,
        name="Protected Relic",
        s3_key=f"relics/{relic_id}",
        size_bytes=100,
        created_at=datetime.utcnow()
    )
    db.add(relic)
    db.commit()

    # Test update as other user
    response = client.put(
        f"/api/v1/relics/{relic_id}",
        headers={"X-Client-Key": other_key},
        json={"name": "Hacked Name"}
    )
    assert response.status_code == 403

def test_update_relic_expiry_never(client, db):
    # Create owner
    owner_key = "owner_key_never"
    owner = ClientKey(id=owner_key, name="Owner")
    db.add(owner)

    # Create relic with expiry
    relic_id = "relic_expiry"
    relic = Relic(
        id=relic_id,
        client_id=owner_key,
        name="Expiry Relic",
        s3_key=f"relics/{relic_id}",
        size_bytes=100,
        expires_at=datetime.utcnow() + timedelta(hours=1),
        created_at=datetime.utcnow()
    )
    db.add(relic)
    db.commit()

    # Update to never expire
    response = client.put(
        f"/api/v1/relics/{relic_id}",
        headers={"X-Client-Key": owner_key},
        json={"expires_in": "never"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["expires_at"] is None

    updated_relic = db.query(Relic).filter(Relic.id == relic_id).first()
    assert updated_relic.expires_at is None

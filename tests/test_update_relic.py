
import pytest
from datetime import datetime, timedelta
from backend.models import Relic, ClientKey
from backend.utils import generate_relic_id, parse_expiry_string

@pytest.mark.unit
def test_update_relic_permissions(client, db):
    """Test that only owner or admin can update relic."""
    # 1. Create a relic owned by client A
    client_a_id = "aaaa" * 8
    client_a = ClientKey(id=client_a_id, name="Client A")
    db.add(client_a)

    relic_id = generate_relic_id()
    relic = Relic(
        id=relic_id,
        client_id=client_a_id,
        name="Original Name",
        content_type="text/plain",
        access_level="public",
        created_at=datetime.utcnow(),
        size_bytes=100
    )
    db.add(relic)
    db.commit()

    # 2. Try to update as anonymous (should fail)
    resp = client.put(f"/api/v1/relics/{relic_id}", json={"name": "New Name"})
    assert resp.status_code == 401

    # 3. Try to update as client B (should fail)
    client_b_id = "bbbb" * 8
    client_b = ClientKey(id=client_b_id, name="Client B")
    db.add(client_b)
    db.commit()

    resp = client.put(
        f"/api/v1/relics/{relic_id}",
        json={"name": "New Name"},
        headers={"X-Client-Key": client_b_id}
    )
    assert resp.status_code == 403

    # 4. Update as client A (should succeed)
    resp = client.put(
        f"/api/v1/relics/{relic_id}",
        json={"name": "Updated Name"},
        headers={"X-Client-Key": client_a_id}
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"
    assert resp.json()["can_edit"] is True

    # Verify DB
    relic = db.query(Relic).filter(Relic.id == relic_id).first()
    assert relic.name == "Updated Name"


@pytest.mark.unit
def test_update_relic_fields(client, db):
    """Test updating various fields of a relic."""
    client_id = "cccc" * 8
    owner = ClientKey(id=client_id, name="Client C")
    db.add(owner)

    relic_id = generate_relic_id()

    relic = Relic(
        id=relic_id,
        client_id=client_id,
        name="Old Name",
        content_type="text/plain",
        access_level="public",
        created_at=datetime.utcnow(),
        size_bytes=200
    )
    db.add(relic)
    db.commit()

    # Update name, content_type, access_level, expires_in
    updates = {
        "name": "New Name",
        "content_type": "text/markdown",
        "access_level": "private",
        "expires_in": "1h"
    }

    resp = client.put(
        f"/api/v1/relics/{relic_id}",
        json=updates,
        headers={"X-Client-Key": client_id}
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "New Name"
    assert data["content_type"] == "text/markdown"
    assert data["access_level"] == "private"
    assert data["expires_at"] is not None

    # Verify expiration logic roughly
    expiry = datetime.fromisoformat(data["expires_at"])
    now = datetime.utcnow()
    assert now < expiry < now + timedelta(hours=2)


@pytest.mark.unit
def test_admin_update_relic(client, db, monkeypatch):
    """Test that admin can update any relic."""
    # Mock admin settings
    admin_id = "dddd" * 8
    monkeypatch.setattr("backend.config.settings.ADMIN_CLIENT_IDS", admin_id)

    # Create admin client
    admin_client = ClientKey(id=admin_id, name="Admin")
    db.add(admin_client)

    # Create relic owned by someone else
    other_id = "eeee" * 8
    relic_id = generate_relic_id()
    relic = Relic(
        id=relic_id,
        client_id=other_id,
        name="User Relic",
        created_at=datetime.utcnow(),
        content_type="text/plain",
        size_bytes=300,
        access_level="public"
    )
    db.add(relic)
    db.commit()

    # Admin updates it
    resp = client.put(
        f"/api/v1/relics/{relic_id}",
        json={"name": "Admin Edited"},
        headers={"X-Client-Key": admin_id}
    )

    assert resp.status_code == 200
    assert resp.json()["name"] == "Admin Edited"
    assert resp.json()["can_edit"] is True

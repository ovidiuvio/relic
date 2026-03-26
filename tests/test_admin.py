"""Tests for admin endpoints."""
import pytest
from backend.config import settings


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def created_relic(client, test_file_content):
    """A relic created for use in tests that need an existing relic."""
    response = client.post(
        "/api/v1/relics",
        data={"name": "Test Relic", "access_level": "public"},
        files={"file": ("test.txt", test_file_content, "text/plain")}
    )
    assert response.status_code == 200
    return response.json()


@pytest.fixture
def admin_client_key(client, monkeypatch):
    """Register a client and mock them as admin."""
    import uuid
    client_key = uuid.uuid4().hex
    headers = {"X-Client-Key": client_key}

    # Register client
    response = client.post("/api/v1/client/register", headers=headers)
    assert response.status_code == 200
    data = response.json()
    client_id = data["client_id"]

    # Mock settings to make this client an admin
    # Memory says: When mocking or patching Pydantic settings like ADMIN_CLIENT_IDS in FastAPI tests, assign strings (matching the expected OS environment variable format) rather than native Python lists
    monkeypatch.setattr(settings, "ADMIN_CLIENT_IDS", client_id)

    return client_key


@pytest.fixture
def normal_client_key(client):
    """Register a non-admin client."""
    import uuid
    client_key = uuid.uuid4().hex
    headers = {"X-Client-Key": client_key}

    response = client.post("/api/v1/client/register", headers=headers)
    assert response.status_code == 200
    return client_key


# ── Check ────────────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_admin_check(client, admin_client_key):
    """Returns true for is_admin when the client is an admin."""
    # Arrange
    headers = {"X-Client-Key": admin_client_key}

    # Act
    response = client.get("/api/v1/admin/check", headers=headers)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["is_admin"] is True
    assert "client_id" in data


@pytest.mark.unit
def test_admin_check_not_admin(client, normal_client_key):
    """Returns false for is_admin when the client is not an admin."""
    # Arrange
    headers = {"X-Client-Key": normal_client_key}

    # Act
    response = client.get("/api/v1/admin/check", headers=headers)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["is_admin"] is False


# ── Relics ───────────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_admin_list_relics(client, admin_client_key, created_relic):
    """Returns a paginated list of all relics for admins."""
    # Arrange
    headers = {"X-Client-Key": admin_client_key}

    # Act
    response = client.get("/api/v1/admin/relics", headers=headers)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "relics" in data
    assert len(data["relics"]) >= 1
    assert data["total"] >= 1
    relic_ids = [r["id"] for r in data["relics"]]
    assert created_relic["id"] in relic_ids
    assert "name" in data["relics"][0]
    assert "content_type" in data["relics"][0]


@pytest.mark.unit
def test_admin_list_relics_forbidden(client, normal_client_key):
    """Returns 403 when a non-admin client tries to list all relics."""
    # Arrange
    headers = {"X-Client-Key": normal_client_key}

    # Act
    response = client.get("/api/v1/admin/relics", headers=headers)

    # Assert
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin privileges required"


# ── Clients ──────────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_admin_list_clients(client, admin_client_key, normal_client_key):
    """Returns a list of all registered clients for admins."""
    # Arrange
    headers = {"X-Client-Key": admin_client_key}

    # Act
    response = client.get("/api/v1/admin/clients", headers=headers)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "clients" in data
    assert len(data["clients"]) >= 2  # The admin and the normal client
    assert data["total"] >= 2
    assert "id" in data["clients"][0]
    assert "name" in data["clients"][0]
    assert "relic_count" in data["clients"][0]


@pytest.mark.unit
def test_admin_list_clients_unauthorized(client):
    """Returns 401 when no client key is provided."""
    # Act
    response = client.get("/api/v1/admin/clients")

    # Assert
    assert response.status_code == 401


# ── Stats ────────────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_admin_stats(client, admin_client_key, created_relic):
    """Returns application statistics for admins."""
    # Arrange
    headers = {"X-Client-Key": admin_client_key}

    # Act
    response = client.get("/api/v1/admin/stats", headers=headers)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "total_relics" in data
    assert data["total_relics"] >= 1
    assert "total_clients" in data
    assert "total_size_bytes" in data


@pytest.mark.unit
def test_admin_stats_forbidden(client, normal_client_key):
    """Returns 403 when a non-admin client tries to get stats."""
    # Arrange
    headers = {"X-Client-Key": normal_client_key}

    # Act
    response = client.get("/api/v1/admin/stats", headers=headers)

    # Assert
    assert response.status_code == 403


# ── Config ───────────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_admin_config(client, admin_client_key):
    """Returns application configuration for admins."""
    # Arrange
    headers = {"X-Client-Key": admin_client_key}

    # Act
    response = client.get("/api/v1/admin/config", headers=headers)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "app" in data
    assert "database" in data
    assert "storage" in data
    assert "upload" in data
    assert "backup" in data
    assert "admin" in data
    assert "cors" in data


@pytest.mark.unit
def test_admin_config_forbidden(client, normal_client_key):
    """Returns 403 when a non-admin client tries to read config."""
    # Arrange
    headers = {"X-Client-Key": normal_client_key}

    # Act
    response = client.get("/api/v1/admin/config", headers=headers)

    # Assert
    assert response.status_code == 403


# ── Reports ──────────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_admin_list_reports(client, admin_client_key, created_relic):
    """Returns a list of reports for admins."""
    # Arrange
    # Create a report first
    report_response = client.post(
        "/api/v1/reports",
        json={"relic_id": created_relic["id"], "reason": "Test report"}
    )
    assert report_response.status_code == 200

    headers = {"X-Client-Key": admin_client_key}

    # Act
    response = client.get("/api/v1/admin/reports", headers=headers)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "reports" in data
    assert len(data["reports"]) >= 1
    assert data["total"] >= 1

    report_ids = [r["relic_id"] for r in data["reports"]]
    assert created_relic["id"] in report_ids

    report = next(r for r in data["reports"] if r["relic_id"] == created_relic["id"])
    assert report["reason"] == "Test report"
    assert "relic_name" in report


@pytest.mark.unit
def test_admin_list_reports_forbidden(client, normal_client_key):
    """Returns 403 when a non-admin client tries to list reports."""
    # Arrange
    headers = {"X-Client-Key": normal_client_key}

    # Act
    response = client.get("/api/v1/admin/reports", headers=headers)

    # Assert
    assert response.status_code == 403


@pytest.mark.unit
def test_admin_delete_report(client, admin_client_key, created_relic):
    """Allows admins to dismiss a report."""
    # Arrange
    # Create a report
    report_response = client.post(
        "/api/v1/reports",
        json={"relic_id": created_relic["id"], "reason": "To be deleted"}
    )
    assert report_response.status_code == 200

    headers = {"X-Client-Key": admin_client_key}

    # Get the report ID from the list
    list_response = client.get("/api/v1/admin/reports", headers=headers)
    assert list_response.status_code == 200
    reports = list_response.json()["reports"]
    report_id = next((r["id"] for r in reports if r["reason"] == "To be deleted"), None)
    assert report_id is not None

    # Act
    response = client.delete(f"/api/v1/admin/reports/{report_id}", headers=headers)

    # Assert
    assert response.status_code == 200
    assert response.json()["message"] == "Report dismissed successfully"

    # Verify it's gone
    list_response = client.get("/api/v1/admin/reports", headers=headers)
    assert list_response.status_code == 200
    # Make sure this specific report ID isn't in the list
    report_ids = [r["id"] for r in list_response.json()["reports"]]
    assert report_id not in report_ids


@pytest.mark.unit
def test_admin_delete_report_not_found(client, admin_client_key):
    """Returns 404 when trying to delete a non-existent report."""
    # Arrange
    headers = {"X-Client-Key": admin_client_key}

    import uuid
    report_id = str(uuid.uuid4())

    # Act
    response = client.delete(f"/api/v1/admin/reports/{report_id}", headers=headers)

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Report not found"
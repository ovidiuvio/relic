"""Integration tests for admin endpoints."""
import uuid
import pytest
from conftest import ADMIN_KEY

ADMIN_HEADERS = {"X-Client-Key": ADMIN_KEY}


@pytest.fixture
def disposable_client(http):
    """Register a fresh non-admin client. Returns client key."""
    key = uuid.uuid4().hex
    http.post("/api/v1/client/register", headers={"X-Client-Key": key})
    return key


@pytest.fixture
def disposable_relic(http, disposable_client):
    """Create a relic owned by a disposable client. Cleans up if still alive."""
    key = disposable_client
    resp = http.post(
        "/api/v1/relics",
        headers={"X-Client-Key": key},
        data={"name": "Admin Test Relic", "access_level": "public"},
        files={"file": ("test.txt", b"admin test content", "text/plain")},
    )
    relic_id = resp.json()["id"]
    yield relic_id
    http.delete(f"/api/v1/relics/{relic_id}", headers=ADMIN_HEADERS)


# ── GET /api/v1/admin/check ───────────────────────────────────────────────────

@pytest.mark.integration
def test_admin_check(http):
    resp = http.get("/api/v1/admin/check", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_admin"] is True
    assert "client_id" in data


@pytest.mark.integration
def test_admin_check_not_admin(http, disposable_client):
    resp = http.get("/api/v1/admin/check", headers={"X-Client-Key": disposable_client})
    assert resp.status_code == 200
    assert resp.json()["is_admin"] is False


# ── GET /api/v1/admin/relics ──────────────────────────────────────────────────

@pytest.mark.integration
def test_admin_list_relics(http, disposable_relic):
    resp = http.get("/api/v1/admin/relics", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "relics" in data
    assert data["total"] >= 1
    ids = [r["id"] for r in data["relics"]]
    assert disposable_relic in ids


@pytest.mark.integration
def test_admin_list_relics_forbidden(http, disposable_client):
    resp = http.get("/api/v1/admin/relics", headers={"X-Client-Key": disposable_client})
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Admin privileges required"


# ── GET /api/v1/admin/clients ─────────────────────────────────────────────────

@pytest.mark.integration
def test_admin_list_clients(http, disposable_client):
    resp = http.get("/api/v1/admin/clients", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "clients" in data
    assert data["total"] >= 1
    ids = [c["id"] for c in data["clients"]]
    assert disposable_client in ids
    assert "public_id" in data["clients"][0]
    assert "relic_count" in data["clients"][0]


@pytest.mark.integration
def test_admin_list_clients_unauthorized(http):
    resp = http.get("/api/v1/admin/clients")
    assert resp.status_code == 401


# ── GET /api/v1/admin/stats ───────────────────────────────────────────────────

@pytest.mark.integration
def test_admin_stats(http, disposable_relic):
    resp = http.get("/api/v1/admin/stats", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_relics" in data
    assert data["total_relics"] >= 1
    assert "total_clients" in data
    assert "total_size_bytes" in data
    assert "total_spaces" in data
    assert "total_comments" in data
    assert "total_bookmarks" in data


@pytest.mark.integration
def test_admin_stats_forbidden(http, disposable_client):
    resp = http.get("/api/v1/admin/stats", headers={"X-Client-Key": disposable_client})
    assert resp.status_code == 403


# ── GET /api/v1/admin/config ──────────────────────────────────────────────────

@pytest.mark.integration
def test_admin_config(http):
    resp = http.get("/api/v1/admin/config", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "app" in data
    assert "database" in data
    assert "storage" in data
    assert "upload" in data
    assert "backup" in data
    assert "admin" in data
    assert "cors" in data


@pytest.mark.integration
def test_admin_config_forbidden(http, disposable_client):
    resp = http.get("/api/v1/admin/config", headers={"X-Client-Key": disposable_client})
    assert resp.status_code == 403


# ── DELETE /api/v1/admin/clients/{client_id} ─────────────────────────────────

@pytest.mark.integration
def test_admin_delete_client(http):
    """Delete a client, relics get disassociated."""
    key = uuid.uuid4().hex
    http.post("/api/v1/client/register", headers={"X-Client-Key": key})

    relic = http.post(
        "/api/v1/relics",
        headers={"X-Client-Key": key},
        data={"access_level": "public"},
        files={"file": ("test.txt", b"content", "text/plain")},
    )
    relic_id = relic.json()["id"]

    resp = http.delete(f"/api/v1/admin/clients/{key}", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    assert "deleted successfully" in resp.json()["message"]

    # Client is gone
    clients = http.get("/api/v1/admin/clients", headers=ADMIN_HEADERS).json()["clients"]
    assert key not in [c["id"] for c in clients]

    # Cleanup orphaned relic
    http.delete(f"/api/v1/relics/{relic_id}", headers=ADMIN_HEADERS)


@pytest.mark.integration
def test_admin_delete_client_with_relics(http):
    """Delete a client and all their relics."""
    key = uuid.uuid4().hex
    http.post("/api/v1/client/register", headers={"X-Client-Key": key})
    relic = http.post(
        "/api/v1/relics",
        headers={"X-Client-Key": key},
        data={"access_level": "public"},
        files={"file": ("test.txt", b"content", "text/plain")},
    )
    relic_id = relic.json()["id"]

    resp = http.delete(f"/api/v1/admin/clients/{key}?delete_relics=true", headers=ADMIN_HEADERS)
    assert resp.status_code == 200

    assert http.get(f"/api/v1/relics/{relic_id}").status_code == 404


@pytest.mark.integration
def test_admin_delete_client_not_found(http):
    resp = http.delete("/api/v1/admin/clients/nonexistent_client_id_xyz", headers=ADMIN_HEADERS)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Client not found"


@pytest.mark.integration
def test_admin_delete_admin_client_forbidden(http):
    resp = http.delete(f"/api/v1/admin/clients/{ADMIN_KEY}", headers=ADMIN_HEADERS)
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Cannot delete admin client"


# ── GET /api/v1/admin/reports ─────────────────────────────────────────────────

@pytest.mark.integration
def test_admin_list_reports(http, disposable_relic):
    http.post("/api/v1/reports", json={"relic_id": disposable_relic, "reason": "Admin test report"})

    resp = http.get("/api/v1/admin/reports", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "reports" in data
    assert data["total"] >= 1
    relic_ids = [r["relic_id"] for r in data["reports"]]
    assert disposable_relic in relic_ids


@pytest.mark.integration
def test_admin_list_reports_forbidden(http, disposable_client):
    resp = http.get("/api/v1/admin/reports", headers={"X-Client-Key": disposable_client})
    assert resp.status_code == 403


# ── DELETE /api/v1/admin/reports/{report_id} ─────────────────────────────────

@pytest.mark.integration
def test_admin_delete_report(http, disposable_relic):
    http.post("/api/v1/reports", json={"relic_id": disposable_relic, "reason": "To dismiss"})

    reports = http.get("/api/v1/admin/reports", headers=ADMIN_HEADERS).json()["reports"]
    report_id = next(r["id"] for r in reports if r["relic_id"] == disposable_relic)

    resp = http.delete(f"/api/v1/admin/reports/{report_id}", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["message"] == "Report dismissed successfully"

    # Verify gone
    reports_after = http.get("/api/v1/admin/reports", headers=ADMIN_HEADERS).json()["reports"]
    assert report_id not in [r["id"] for r in reports_after]


@pytest.mark.integration
def test_admin_delete_report_not_found(http):
    resp = http.delete(f"/api/v1/admin/reports/{uuid.uuid4()}", headers=ADMIN_HEADERS)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Report not found"


# ── GET /api/v1/admin/backups ─────────────────────────────────────────────────

@pytest.mark.integration
def test_admin_list_backups(http):
    resp = http.get("/api/v1/admin/backups", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "backups" in data
    assert "total" in data


@pytest.mark.integration
def test_admin_list_backups_forbidden(http, disposable_client):
    resp = http.get("/api/v1/admin/backups", headers={"X-Client-Key": disposable_client})
    assert resp.status_code == 403


# ── POST /api/v1/admin/backups ────────────────────────────────────────────────

@pytest.mark.integration
def test_admin_create_backup(http):
    resp = http.post("/api/v1/admin/backups", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "success" in data
    assert "message" in data


# ── GET /api/v1/admin/backups/{filename}/download ─────────────────────────────

@pytest.mark.integration
def test_admin_download_backup_invalid_filename(http):
    resp = http.get("/api/v1/admin/backups/not-a-valid-file.txt/download", headers=ADMIN_HEADERS)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid backup filename"


@pytest.mark.integration
def test_admin_download_backup(http):
    """Create a backup then download it."""
    http.post("/api/v1/admin/backups", headers=ADMIN_HEADERS)

    backups = http.get("/api/v1/admin/backups", headers=ADMIN_HEADERS).json()["backups"]
    if not backups:
        pytest.skip("No backups available to download")

    filename = backups[0]["filename"]
    resp = http.get(f"/api/v1/admin/backups/{filename}/download", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/gzip"
    assert len(resp.content) > 0


# ── POST /api/v1/admin/backups/{filename}/restore ────────────────────────────

@pytest.mark.integration
def test_admin_restore_backup_invalid_filename(http):
    resp = http.post("/api/v1/admin/backups/invalid-file.tar/restore", headers=ADMIN_HEADERS)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid backup filename"


# ── POST /api/v1/admin/backups/restore-upload ─────────────────────────────────

@pytest.mark.integration
def test_admin_restore_from_upload_wrong_extension(http):
    resp = http.post(
        "/api/v1/admin/backups/restore-upload",
        headers=ADMIN_HEADERS,
        files={"file": ("backup.tar.gz", b"content", "application/gzip")},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "File must be a .sql.gz backup"

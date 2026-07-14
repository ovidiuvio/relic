"""Integration tests for admin endpoints."""
import time
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
    
    # Assert that the breakdown sum matches the total relics count
    assert data["public_relics"] + data["private_relics"] + data["restricted_relics"] == data["total_relics"]


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


# ── Runtime admin management ──────────────────────────────────────────────────

@pytest.fixture
def registered_pair(http):
    """Register a fresh client and return (client_key, public_id). Best-effort cleanup."""
    key = uuid.uuid4().hex
    public_id = http.post("/api/v1/client/register", headers={"X-Client-Key": key}).json()["public_id"]
    yield key, public_id
    # Revoke any admin grant, then delete the client.
    http.delete(f"/api/v1/admin/clients/{key}/admin", headers=ADMIN_HEADERS)
    http.delete(f"/api/v1/admin/clients/{key}", headers=ADMIN_HEADERS)


# GET /api/v1/admin/admins

@pytest.mark.integration
def test_admin_list_admins(http):
    resp = http.get("/api/v1/admin/admins", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "admins" in data
    # The env super-admin is present and flagged.
    me = next((a for a in data["admins"] if a["client_id"] == ADMIN_KEY), None)
    assert me is not None
    assert me["is_super_admin"] is True


@pytest.mark.integration
def test_admin_list_admins_forbidden(http, disposable_client):
    resp = http.get("/api/v1/admin/admins", headers={"X-Client-Key": disposable_client})
    assert resp.status_code == 403


@pytest.mark.integration
def test_admin_list_clients_exposes_super_admin_flag(http):
    # Locate the env super-admin via search (the client list is paginated).
    clients = http.get(
        "/api/v1/admin/clients",
        headers=ADMIN_HEADERS,
        params={"search": ADMIN_KEY},
    ).json()["clients"]
    me = next((c for c in clients if c["id"] == ADMIN_KEY), None)
    assert me is not None
    assert me["is_super_admin"] is True and me["is_admin"] is True


# POST /api/v1/admin/admins  (grant by Public ID / Client ID)

@pytest.mark.integration
def test_admin_add_admin_by_public_id(http, registered_pair):
    key, public_id = registered_pair
    assert http.get("/api/v1/admin/check", headers={"X-Client-Key": key}).json()["is_admin"] is False

    resp = http.post("/api/v1/admin/admins", headers=ADMIN_HEADERS, json={"public_id": public_id})
    assert resp.status_code == 200
    assert resp.json()["is_admin"] is True

    # Effective immediately, no restart.
    assert http.get("/api/v1/admin/check", headers={"X-Client-Key": key}).json()["is_admin"] is True

    # Appears in the admins list as a non-super (runtime) admin.
    admins = http.get("/api/v1/admin/admins", headers=ADMIN_HEADERS).json()["admins"]
    entry = next((a for a in admins if a["client_id"] == key), None)
    assert entry is not None and entry["is_super_admin"] is False


@pytest.mark.integration
def test_admin_add_admin_rejects_raw_client_id(http, registered_pair):
    """POST /admins no longer falls back to raw client_id; use POST /clients/{id}/admin instead."""
    key, _ = registered_pair
    resp = http.post("/api/v1/admin/admins", headers=ADMIN_HEADERS, json={"public_id": key})
    assert resp.status_code == 404


@pytest.mark.integration
def test_admin_add_admin_unknown_identifier(http):
    resp = http.post("/api/v1/admin/admins", headers=ADMIN_HEADERS, json={"public_id": "no-such-identifier"})
    assert resp.status_code == 404


@pytest.mark.integration
def test_admin_add_admin_forbidden(http, disposable_client):
    resp = http.post(
        "/api/v1/admin/admins",
        headers={"X-Client-Key": disposable_client},
        json={"public_id": "whatever"},
    )
    assert resp.status_code == 403


# POST/DELETE /api/v1/admin/clients/{id}/admin  (grant/revoke by Client ID)

@pytest.mark.integration
def test_admin_grant_and_revoke_by_client_id(http, registered_pair):
    key, _ = registered_pair
    grant = http.post(f"/api/v1/admin/clients/{key}/admin", headers=ADMIN_HEADERS)
    assert grant.status_code == 200 and grant.json()["is_admin"] is True
    assert http.get("/api/v1/admin/check", headers={"X-Client-Key": key}).json()["is_admin"] is True

    revoke = http.delete(f"/api/v1/admin/clients/{key}/admin", headers=ADMIN_HEADERS)
    assert revoke.status_code == 200 and revoke.json()["is_admin"] is False
    assert http.get("/api/v1/admin/check", headers={"X-Client-Key": key}).json()["is_admin"] is False


@pytest.mark.integration
def test_admin_grant_nonexistent_client(http):
    resp = http.post("/api/v1/admin/clients/nonexistent_client_xyz/admin", headers=ADMIN_HEADERS)
    assert resp.status_code == 404


@pytest.mark.integration
def test_admin_grant_forbidden_for_non_admin(http, disposable_client, registered_pair):
    key, _ = registered_pair
    resp = http.post(f"/api/v1/admin/clients/{key}/admin", headers={"X-Client-Key": disposable_client})
    assert resp.status_code == 403


@pytest.mark.integration
def test_admin_revoke_super_admin_forbidden(http):
    resp = http.delete(f"/api/v1/admin/clients/{ADMIN_KEY}/admin", headers=ADMIN_HEADERS)
    assert resp.status_code == 400
    assert "super-admin" in resp.json()["detail"].lower()


@pytest.mark.integration
def test_admin_cannot_revoke_own_admin(http, registered_pair):
    """Lockout protection: a runtime admin cannot revoke their own privileges."""
    key, _ = registered_pair
    http.post(f"/api/v1/admin/clients/{key}/admin", headers=ADMIN_HEADERS)

    resp = http.delete(f"/api/v1/admin/clients/{key}/admin", headers={"X-Client-Key": key})
    assert resp.status_code == 400
    assert "your own" in resp.json()["detail"].lower()


@pytest.mark.integration
def test_runtime_admin_protected_from_deletion(http, registered_pair):
    """A runtime-granted admin can't be deleted until admin is revoked."""
    key, _ = registered_pair
    http.post(f"/api/v1/admin/clients/{key}/admin", headers=ADMIN_HEADERS)

    blocked = http.delete(f"/api/v1/admin/clients/{key}", headers=ADMIN_HEADERS)
    assert blocked.status_code == 403
    assert blocked.json()["detail"] == "Cannot delete admin client"

    http.delete(f"/api/v1/admin/clients/{key}/admin", headers=ADMIN_HEADERS)
    ok = http.delete(f"/api/v1/admin/clients/{key}", headers=ADMIN_HEADERS)
    assert ok.status_code == 200


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


# ── GET /api/v1/admin/jobs ───────────────────────────────────────────────────

@pytest.mark.integration
def test_admin_list_jobs(http):
    resp = http.get("/api/v1/admin/jobs", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "jobs" in data
    assert "running" in data
    assert "history" in data
    assert isinstance(data["jobs"], list)
    assert isinstance(data["history"], list)
    job_ids = [j["id"] for j in data["jobs"]]
    assert "relic_cleanup" in job_ids
    # trigger_info is the structured payload added in the bug-fix pass; verify
    # it is present and exposes a recognisable "type" for each registered job.
    for j in data["jobs"]:
        assert "trigger_info" in j
        info = j["trigger_info"]
        assert "type" in info
        assert info["type"] in ("cron", "interval", "date", "unknown")
        if info["type"] == "interval":
            assert info["seconds"] is not None and info["seconds"] > 0
        if info["type"] == "cron":
            assert isinstance(info["fields"], dict)


@pytest.mark.integration
def test_admin_list_jobs_forbidden(http, disposable_client):
    resp = http.get("/api/v1/admin/jobs", headers={"X-Client-Key": disposable_client})
    assert resp.status_code == 403


# ── POST /api/v1/admin/jobs/{job_id}/run ──────────────────────────────────────

def _wait_for_manual_run(http, run_id, timeout=5.0):
    """Poll /admin/jobs until the given manual run is terminal; return entry."""
    deadline = time.time() + timeout
    last_entry = None
    while time.time() < deadline:
        data = http.get("/api/v1/admin/jobs", headers=ADMIN_HEADERS).json()
        for entry in data.get("history", []):
            if entry.get("run_id") == run_id:
                last_entry = entry
                if entry["status"] in ("success", "failed"):
                    return entry
        time.sleep(0.2)
    return last_entry


@pytest.mark.integration
def test_admin_run_job(http):
    resp = http.post("/api/v1/admin/jobs/relic_cleanup/run", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    run_id = body["run_id"]
    assert run_id

    # Synchronous creation: the entry should be visible immediately. It may
    # already be terminal if FastAPI's BackgroundTasks ran in between, which
    # is a valid outcome — the important thing is that the run_id exists in
    # history with trigger_type=manual before any waiting.
    list_resp = http.get("/api/v1/admin/jobs", headers=ADMIN_HEADERS)
    entry_now = next(
        (h for h in list_resp.json()["history"] if h["run_id"] == run_id), None
    )
    assert entry_now is not None
    assert entry_now["trigger_type"] == "manual"
    assert entry_now["status"] in ("running", "success", "failed")

    # Poll for terminal state instead of fixed sleep
    final = _wait_for_manual_run(http, run_id, timeout=5.0)
    assert final is not None
    assert final["status"] in ("success", "failed")
    assert isinstance(final["logs"], list)
    assert any("Starting expired relics cleanup..." in log for log in final["logs"])


@pytest.mark.integration
def test_admin_run_job_not_found(http):
    resp = http.post("/api/v1/admin/jobs/nonexistent_job/run", headers=ADMIN_HEADERS)
    assert resp.status_code == 404


@pytest.mark.integration
def test_admin_run_job_conflict(http):
    import concurrent.futures

    def trigger():
        return http.post("/api/v1/admin/jobs/relic_cleanup/run", headers=ADMIN_HEADERS)

    # We send multiple requests simultaneously to try and cause a 409 conflict.
    # relic_cleanup does a DB query, which is async and should take enough time
    # for the second request to hit the endpoint before the first finishes.
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(trigger) for _ in range(4)]
        responses = [f.result() for f in futures]

    status_codes = [r.status_code for r in responses]
    
    # At least one should be 409 if the job takes any time at all
    assert 409 in status_codes
    assert 200 in status_codes


@pytest.mark.integration
def test_admin_list_jobs_relics_cleanup_trigger_info_is_interval(http):
    """The relic_cleanup job is registered with an interval trigger, so its
    structured trigger_info should report type='interval' and seconds matching
    settings.RELIC_CLEANUP_INTERVAL. Documents the contract the frontend
    formatTriggerJob() depends on."""
    data = http.get("/api/v1/admin/jobs", headers=ADMIN_HEADERS).json()
    job = next((j for j in data["jobs"] if j["id"] == "relic_cleanup"), None)
    assert job is not None
    info = job["trigger_info"]
    assert info["type"] == "interval"
    assert info["seconds"] is not None
    assert info["seconds"] >= 60


# ── POST /api/v1/admin/jobs/{job_id}/pause & resume ───────────────────────────

@pytest.mark.integration
def test_admin_pause_resume_job(http):
    # 1. Pause the job
    resp = http.post("/api/v1/admin/jobs/relic_cleanup/pause", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # Verify it is paused in list
    list_resp = http.get("/api/v1/admin/jobs", headers=ADMIN_HEADERS)
    jobs = {j["id"]: j for j in list_resp.json()["jobs"]}
    assert jobs["relic_cleanup"]["paused"] is True

    # 2. Resume the job
    resp = http.post("/api/v1/admin/jobs/relic_cleanup/resume", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # Verify it is resumed
    list_resp = http.get("/api/v1/admin/jobs", headers=ADMIN_HEADERS)
    jobs = {j["id"]: j for j in list_resp.json()["jobs"]}
    assert jobs["relic_cleanup"]["paused"] is False


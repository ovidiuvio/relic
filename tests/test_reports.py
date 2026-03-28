"""Integration tests for the relic reporting endpoints."""
import uuid
import pytest
from conftest import ADMIN_KEY


@pytest.fixture
def reportable_relic(http, registered_client):
    """Create a relic to report against. Cleans up after."""
    key, _ = registered_client
    resp = http.post(
        "/api/v1/relics",
        headers={"X-Client-Key": key},
        data={"name": "Reportable Relic", "access_level": "public"},
        files={"file": ("test.txt", b"bad content", "text/plain")},
    )
    relic_id = resp.json()["id"]
    yield relic_id
    http.delete(f"/api/v1/relics/{relic_id}", headers={"X-Client-Key": key})


# ── POST /api/v1/reports ─────────────────────────────────────────────────────

@pytest.mark.integration
def test_create_report(http, reportable_relic):
    resp = http.post(
        "/api/v1/reports",
        json={"relic_id": reportable_relic, "reason": "Inappropriate content"},
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Report submitted successfully"


@pytest.mark.integration
def test_create_report_nonexistent_relic(http):
    resp = http.post(
        "/api/v1/reports",
        json={"relic_id": "nonexistent_relic_report", "reason": "Bad"},
    )
    assert resp.status_code == 404

"""Runtime settings: admin API and policy enforcement."""
import time
import pytest
import httpx

from conftest import ADMIN_KEY, BASE_URL

ADMIN_HEADERS = {"X-User-Key": ADMIN_KEY}

# The backend caches resolved settings briefly; wait past it before asserting
# that a change took effect. Kept slightly above the server-side TTL.
CACHE_TTL_WAIT = 6


def _settle():
    """Wait for a settings change to propagate past the server cache."""
    time.sleep(CACHE_TTL_WAIT)


@pytest.fixture
def settings_sandbox():
    """Reset all setting overrides after the test.

    These tests run against a live deployment with no transaction to roll back,
    so a leaked read_only_mode or maintenance_mode would break every test that
    follows. The reset runs even if the test fails.
    """
    yield
    with httpx.Client(base_url=BASE_URL, timeout=15) as client:
        client.post("/api/v1/admin/settings/reset", headers=ADMIN_HEADERS)
    _settle()


# ── GET /api/v1/admin/settings ──────────────────────────────────────────────

@pytest.mark.integration
def test_get_settings_returns_schema_and_values(http):
    """Schema is grouped into sections, each setting carrying its value."""
    resp = http.get("/api/v1/admin/settings", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    body = resp.json()

    assert "default" in body["presets"] and "hardened" in body["presets"]

    sections = {s["section"] for s in body["sections"]}
    assert {"features", "uploads", "quotas", "rate_limits"} <= sections

    every = [s for section in body["sections"] for s in section["settings"]]
    sample = next(s for s in every if s["key"] == "read_only_mode")
    assert sample["type"] == "bool"
    assert set(sample) >= {"key", "type", "default", "label", "help", "value", "overridden"}


@pytest.mark.integration
def test_get_settings_unauthorized(http):
    """No user key is rejected."""
    resp = http.get("/api/v1/admin/settings")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "User key required"


@pytest.mark.integration
def test_get_settings_forbidden(http, registered_user):
    """A non-admin user is rejected."""
    key, _ = registered_user
    resp = http.get("/api/v1/admin/settings", headers={"X-User-Key": key})
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Admin privileges required"


# ── PUT /api/v1/admin/settings ──────────────────────────────────────────────

@pytest.mark.integration
def test_update_setting_marks_it_overridden(http, settings_sandbox):
    """A written setting reports the new value and is flagged as overridden."""
    resp = http.put(
        "/api/v1/admin/settings",
        headers=ADMIN_HEADERS,
        json={"max_relics_per_user": 7},
    )
    assert resp.status_code == 200
    assert resp.json()["settings"]["max_relics_per_user"] == 7

    body = http.get("/api/v1/admin/settings", headers=ADMIN_HEADERS).json()
    every = [s for section in body["sections"] for s in section["settings"]]
    setting = next(s for s in every if s["key"] == "max_relics_per_user")
    assert setting["value"] == 7
    assert setting["overridden"] is True


@pytest.mark.integration
def test_update_rejects_unknown_key(http, settings_sandbox):
    """An unknown setting name is a 400, not a silently stored row."""
    resp = http.put(
        "/api/v1/admin/settings",
        headers=ADMIN_HEADERS,
        json={"not_a_real_setting": 1},
    )
    assert resp.status_code == 400
    assert "Unknown setting" in resp.json()["detail"]


@pytest.mark.integration
def test_update_rejects_out_of_range_value(http, settings_sandbox):
    """Registry bounds are enforced server-side."""
    resp = http.put(
        "/api/v1/admin/settings",
        headers=ADMIN_HEADERS,
        json={"max_upload_size_bytes": -5},
    )
    assert resp.status_code == 400
    assert "at least" in resp.json()["detail"]


@pytest.mark.integration
def test_update_is_all_or_nothing(http, settings_sandbox):
    """One invalid key in a bulk update leaves the valid ones unwritten."""
    resp = http.put(
        "/api/v1/admin/settings",
        headers=ADMIN_HEADERS,
        json={"max_relics_per_user": 3, "bogus_key": True},
    )
    assert resp.status_code == 400

    body = http.get("/api/v1/admin/settings", headers=ADMIN_HEADERS).json()
    every = [s for section in body["sections"] for s in section["settings"]]
    setting = next(s for s in every if s["key"] == "max_relics_per_user")
    assert setting["overridden"] is False


@pytest.mark.integration
def test_update_settings_forbidden(http, registered_user):
    """A non-admin cannot change policy."""
    key, _ = registered_user
    resp = http.put(
        "/api/v1/admin/settings",
        headers={"X-User-Key": key},
        json={"read_only_mode": True},
    )
    assert resp.status_code == 403


# ── Reset and presets ───────────────────────────────────────────────────────

@pytest.mark.integration
def test_reset_restores_defaults(http, settings_sandbox):
    """Reset clears overrides so values fall back to registry defaults."""
    http.put("/api/v1/admin/settings", headers=ADMIN_HEADERS, json={"max_relics_per_user": 9})

    resp = http.post("/api/v1/admin/settings/reset", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["reset"] >= 1

    body = http.get("/api/v1/admin/settings", headers=ADMIN_HEADERS).json()
    every = [s for section in body["sections"] for s in section["settings"]]
    setting = next(s for s in every if s["key"] == "max_relics_per_user")
    assert setting["overridden"] is False
    assert setting["value"] == setting["default"]


@pytest.mark.integration
def test_reset_unknown_section(http):
    """An unknown section name is rejected rather than resetting everything."""
    resp = http.post(
        "/api/v1/admin/settings/reset", headers=ADMIN_HEADERS, params={"section": "nope"}
    )
    assert resp.status_code == 400


@pytest.mark.integration
def test_apply_hardened_preset(http, settings_sandbox):
    """The hardened preset tightens the settings a public instance cares about."""
    resp = http.post("/api/v1/admin/settings/preset/hardened", headers=ADMIN_HEADERS)
    assert resp.status_code == 200

    body = http.get("/api/v1/admin/settings", headers=ADMIN_HEADERS).json()
    values = {
        s["key"]: s["value"]
        for section in body["sections"]
        for s in section["settings"]
    }
    assert values["require_auth_for_writes"] is True
    assert values["render_html"] is False
    assert values["force_download_raw"] is True
    assert values["force_expiry"] is True
    assert values["max_storage_bytes_per_user"] > 0


@pytest.mark.integration
def test_apply_unknown_preset(http):
    """An unknown preset name is a 400."""
    resp = http.post("/api/v1/admin/settings/preset/nonexistent", headers=ADMIN_HEADERS)
    assert resp.status_code == 400


# ── Enforcement round-trips ─────────────────────────────────────────────────

@pytest.mark.integration
def test_upload_size_limit_enforced(http, registered_user, settings_sandbox):
    """Lowering the upload limit rejects a file that was previously fine."""
    key, _ = registered_user
    http.put("/api/v1/admin/settings", headers=ADMIN_HEADERS, json={"max_upload_size_bytes": 10})
    _settle()

    resp = http.post(
        "/api/v1/relics",
        headers={"X-User-Key": key},
        files={"file": ("big.txt", b"x" * 500, "text/plain")},
    )
    assert resp.status_code == 413


@pytest.mark.integration
def test_blocked_content_type_enforced(http, registered_user, settings_sandbox):
    """A blocked content type is refused; others still work."""
    key, _ = registered_user
    http.put(
        "/api/v1/admin/settings",
        headers=ADMIN_HEADERS,
        json={"blocked_content_types": ["text/html"]},
    )
    _settle()

    blocked = http.post(
        "/api/v1/relics",
        headers={"X-User-Key": key},
        files={"file": ("x.html", b"<h1>hi</h1>", "text/html")},
    )
    assert blocked.status_code == 415

    allowed = http.post(
        "/api/v1/relics",
        headers={"X-User-Key": key},
        files={"file": ("x.txt", b"hi", "text/plain")},
    )
    assert allowed.status_code == 200
    http.delete(f"/api/v1/relics/{allowed.json()['id']}", headers=ADMIN_HEADERS)


@pytest.mark.integration
def test_allowed_content_type_allowlist(http, registered_user, settings_sandbox):
    """A non-empty allow list refuses everything outside it."""
    key, _ = registered_user
    http.put(
        "/api/v1/admin/settings",
        headers=ADMIN_HEADERS,
        json={"allowed_content_types": ["text/*"]},
    )
    _settle()

    resp = http.post(
        "/api/v1/relics",
        headers={"X-User-Key": key},
        files={"file": ("x.bin", b"\x00\x01", "application/octet-stream")},
    )
    assert resp.status_code == 415


@pytest.mark.integration
def test_read_only_mode_blocks_writes_not_reads(http, registered_user, settings_sandbox):
    """Read-only mode rejects writes while reads keep working."""
    key, _ = registered_user
    http.put("/api/v1/admin/settings", headers=ADMIN_HEADERS, json={"read_only_mode": True})
    _settle()

    write = http.post(
        "/api/v1/relics",
        headers={"X-User-Key": key},
        files={"file": ("x.txt", b"hi", "text/plain")},
    )
    assert write.status_code == 503

    assert http.get("/api/v1/relics").status_code == 200


@pytest.mark.integration
def test_admin_is_never_locked_out(http, settings_sandbox):
    """With every availability switch on, admins can still change settings.

    This is the property that makes the whole feature safe to use: a mistaken
    toggle must always be undoable through the API.
    """
    http.put(
        "/api/v1/admin/settings",
        headers=ADMIN_HEADERS,
        json={"read_only_mode": True, "maintenance_mode": True},
    )
    _settle()

    assert http.get("/api/v1/relics").status_code == 503

    recover = http.put(
        "/api/v1/admin/settings",
        headers=ADMIN_HEADERS,
        json={"read_only_mode": False, "maintenance_mode": False},
    )
    assert recover.status_code == 200
    _settle()
    assert http.get("/api/v1/relics").status_code == 200


@pytest.mark.integration
def test_maintenance_mode_exempts_admins(http, settings_sandbox):
    """Maintenance mode returns the configured message to everyone but admins."""
    message = "Back in ten minutes."
    http.put(
        "/api/v1/admin/settings",
        headers=ADMIN_HEADERS,
        json={"maintenance_mode": True, "maintenance_message": message},
    )
    _settle()

    anon = http.get("/api/v1/relics")
    assert anon.status_code == 503
    assert anon.json()["detail"] == message

    assert http.get("/api/v1/relics", headers=ADMIN_HEADERS).status_code == 200


@pytest.mark.integration
def test_require_auth_for_writes(http, settings_sandbox):
    """Anonymous writes are refused while reads stay open."""
    http.put(
        "/api/v1/admin/settings", headers=ADMIN_HEADERS, json={"require_auth_for_writes": True}
    )
    _settle()

    resp = http.post("/api/v1/relics", files={"file": ("x.txt", b"hi", "text/plain")})
    assert resp.status_code == 401
    assert http.get("/api/v1/relics").status_code == 200


@pytest.mark.integration
def test_feature_kill_switch_disables_comments(http, created_relic, settings_sandbox):
    """Turning a feature off makes its endpoint refuse with 403."""
    http.put("/api/v1/admin/settings", headers=ADMIN_HEADERS, json={"allow_comments": False})
    _settle()

    resp = http.post(
        f"/api/v1/relics/{created_relic['id']}/comments",
        headers={"X-User-Key": created_relic["user_key"]},
        json={"line_number": 1, "content": "hello"},
    )
    assert resp.status_code == 403
    assert "disabled" in resp.json()["detail"]


@pytest.mark.integration
def test_expiry_is_clamped(http, registered_user, settings_sandbox):
    """A max expiry clamps 'never' down to the configured ceiling."""
    key, _ = registered_user
    http.put(
        "/api/v1/admin/settings",
        headers=ADMIN_HEADERS,
        json={"force_expiry": True, "max_expiry": "1h"},
    )
    _settle()

    resp = http.post(
        "/api/v1/relics",
        headers={"X-User-Key": key},
        data={"expires_in": "never"},
        files={"file": ("x.txt", b"hi", "text/plain")},
    )
    assert resp.status_code == 200
    relic_id = resp.json()["id"]

    detail = http.get(f"/api/v1/relics/{relic_id}", headers={"X-User-Key": key}).json()
    assert detail["expires_at"] is not None
    http.delete(f"/api/v1/relics/{relic_id}", headers=ADMIN_HEADERS)


@pytest.mark.integration
def test_unparseable_expiry_rejected_when_forced(http, registered_user, settings_sandbox):
    """With expiry forced, a bad duration is a 400 rather than 'never'."""
    key, _ = registered_user
    http.put(
        "/api/v1/admin/settings",
        headers=ADMIN_HEADERS,
        json={"force_expiry": True, "max_expiry": "1h"},
    )
    _settle()

    resp = http.post(
        "/api/v1/relics",
        headers={"X-User-Key": key},
        data={"expires_in": "not-a-duration"},
        files={"file": ("x.txt", b"hi", "text/plain")},
    )
    assert resp.status_code == 400


@pytest.mark.integration
def test_comment_length_limit(http, created_relic, settings_sandbox):
    """Comment bodies longer than the limit are refused."""
    http.put("/api/v1/admin/settings", headers=ADMIN_HEADERS, json={"max_comment_length": 10})
    _settle()

    resp = http.post(
        f"/api/v1/relics/{created_relic['id']}/comments",
        headers={"X-User-Key": created_relic["user_key"]},
        json={"line_number": 1, "content": "x" * 50},
    )
    assert resp.status_code == 400


@pytest.mark.integration
def test_rate_limit_enforced_and_shared_across_workers(http, settings_sandbox):
    """The limit binds exactly, proving counters are not per-worker.

    The backend runs multiple gunicorn workers; with in-process counters this
    would allow roughly workers x limit requests before refusing.
    """
    limit = 5
    http.put(
        "/api/v1/admin/settings",
        headers=ADMIN_HEADERS,
        json={"rate_limit_enabled": True, "rate_limit_requests_per_minute": limit},
    )
    _settle()

    codes = [http.get("/api/v1/relics").status_code for _ in range(limit + 3)]
    assert codes[:limit] == [200] * limit
    assert all(code == 429 for code in codes[limit:])


@pytest.mark.integration
def test_rate_limit_cannot_be_bypassed_by_spoofing(http, settings_sandbox):
    """A forged X-Forwarded-For does not reset the caller's rate-limit bucket.

    nginx uses $proxy_add_x_forwarded_for, which appends to whatever the client
    sent, so the first entry is attacker controlled and must not be trusted.
    """
    http.put(
        "/api/v1/admin/settings",
        headers=ADMIN_HEADERS,
        json={"rate_limit_enabled": True, "rate_limit_requests_per_minute": 3},
    )
    _settle()

    for _ in range(4):
        http.get("/api/v1/relics")

    for spoofed in ("1.2.3.4", "5.6.7.8"):
        resp = http.get("/api/v1/relics", headers={"X-Forwarded-For": spoofed})
        assert resp.status_code == 429


# ── Public settings ─────────────────────────────────────────────────────────

@pytest.mark.integration
def test_public_settings_expose_only_client_keys(http):
    """The unauthenticated endpoint exposes render/limit hints and nothing else."""
    resp = http.get("/api/v1/settings")
    assert resp.status_code == 200
    body = resp.json()

    assert "render_html" in body
    assert "max_upload_size_bytes" in body
    # Security posture must not be enumerable without a key
    for leaked in ("read_only_mode", "require_auth_for_writes", "rate_limit_enabled"):
        assert leaked not in body


# ── GET /api/v1/admin/config ────────────────────────────────────────────────

@pytest.mark.integration
def test_config_masks_credentials(http):
    """The config dump must not hand back usable credentials."""
    resp = http.get("/api/v1/admin/config", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    body = resp.json()

    assert "*" in body["storage"]["S3_SECRET_KEY"]
    assert "********" in body["database"]["DATABASE_URL"]
    # Host and database name stay readable so admins can identify the deployment
    assert "postgres" in body["database"]["DATABASE_URL"]

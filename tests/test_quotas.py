"""Per-user quotas: overrides, inheritance, usage accounting, and enforcement."""
import time
import pytest
import httpx

from conftest import ADMIN_KEY, BASE_URL

ADMIN_HEADERS = {"X-User-Key": ADMIN_KEY}

CACHE_TTL_WAIT = 6


def _settle():
    """Wait for a settings change to propagate past the server cache."""
    time.sleep(CACHE_TTL_WAIT)


@pytest.fixture
def settings_sandbox():
    """Reset global setting overrides after the test.

    Per-user overrides live on the user row, so tests that set them use
    throwaway users rather than needing cleanup here.
    """
    yield
    with httpx.Client(base_url=BASE_URL, timeout=15) as client:
        client.post("/api/v1/admin/settings/reset", headers=ADMIN_HEADERS)
    _settle()


def _upload(http, key, content=b"hello", name="x.txt"):
    return http.post(
        "/api/v1/relics",
        headers={"X-User-Key": key},
        files={"file": (name, content, "text/plain")},
    )


# ── PUT /api/v1/admin/users/{id}/quotas ─────────────────────────────────────

@pytest.mark.integration
def test_set_and_clear_quota_override(http, registered_user):
    """A per-user override is stored, and null clears it back to inheritance."""
    key, _ = registered_user

    resp = http.put(
        f"/api/v1/admin/users/{key}/quotas",
        headers=ADMIN_HEADERS,
        json={"quota_max_relics": 5},
    )
    assert resp.status_code == 200
    assert resp.json()["quotas"]["quota_max_relics"] == 5

    resp = http.put(
        f"/api/v1/admin/users/{key}/quotas",
        headers=ADMIN_HEADERS,
        json={"quota_max_relics": None},
    )
    assert resp.status_code == 200
    assert resp.json()["quotas"]["quota_max_relics"] is None


@pytest.mark.integration
def test_quota_override_rejects_unknown_field(http, registered_user):
    """An unrecognised quota field is a 400."""
    key, _ = registered_user
    resp = http.put(
        f"/api/v1/admin/users/{key}/quotas",
        headers=ADMIN_HEADERS,
        json={"quota_max_bananas": 3},
    )
    assert resp.status_code == 400
    assert "Unknown quota field" in resp.json()["detail"]


@pytest.mark.integration
def test_quota_override_unknown_user(http):
    """Setting quotas on a nonexistent user is a 404."""
    resp = http.put(
        "/api/v1/admin/users/ffffffffffffffffffffffffffffffff/quotas",
        headers=ADMIN_HEADERS,
        json={"quota_max_relics": 1},
    )
    assert resp.status_code == 404


@pytest.mark.integration
def test_quota_override_forbidden(http, registered_user):
    """A non-admin cannot raise their own quota."""
    key, _ = registered_user
    resp = http.put(
        f"/api/v1/admin/users/{key}/quotas",
        headers={"X-User-Key": key},
        json={"quota_max_relics": 9999},
    )
    assert resp.status_code == 403


# ── Enforcement ─────────────────────────────────────────────────────────────

@pytest.mark.integration
def test_relic_count_quota_enforced(http, registered_user):
    """A user may create up to their quota and no further."""
    key, _ = registered_user
    http.put(
        f"/api/v1/admin/users/{key}/quotas", headers=ADMIN_HEADERS, json={"quota_max_relics": 2}
    )

    created = []
    for _ in range(2):
        resp = _upload(http, key)
        assert resp.status_code == 200
        created.append(resp.json()["id"])

    assert _upload(http, key).status_code == 429

    for relic_id in created:
        http.delete(f"/api/v1/relics/{relic_id}", headers=ADMIN_HEADERS)


@pytest.mark.integration
def test_override_beats_global_default(http, registered_user, settings_sandbox):
    """A per-user override wins over the instance-wide default."""
    key, _ = registered_user
    http.put("/api/v1/admin/settings", headers=ADMIN_HEADERS, json={"max_relics_per_user": 1})
    http.put(
        f"/api/v1/admin/users/{key}/quotas", headers=ADMIN_HEADERS, json={"quota_max_relics": 3}
    )
    _settle()

    created = []
    for _ in range(3):
        resp = _upload(http, key)
        assert resp.status_code == 200, "override should permit more than the global default"
        created.append(resp.json()["id"])

    assert _upload(http, key).status_code == 429

    for relic_id in created:
        http.delete(f"/api/v1/relics/{relic_id}", headers=ADMIN_HEADERS)


@pytest.mark.integration
def test_clearing_override_restores_global_default(http, registered_user, settings_sandbox):
    """Clearing an override makes the user follow the global default again."""
    key, _ = registered_user
    http.put("/api/v1/admin/settings", headers=ADMIN_HEADERS, json={"max_relics_per_user": 1})
    http.put(
        f"/api/v1/admin/users/{key}/quotas", headers=ADMIN_HEADERS, json={"quota_max_relics": 5}
    )
    _settle()

    first = _upload(http, key)
    assert first.status_code == 200

    http.put(
        f"/api/v1/admin/users/{key}/quotas",
        headers=ADMIN_HEADERS,
        json={"quota_max_relics": None},
    )

    # Now bound by the global default of 1, which is already used up
    assert _upload(http, key).status_code == 429
    http.delete(f"/api/v1/relics/{first.json()['id']}", headers=ADMIN_HEADERS)


@pytest.mark.integration
def test_zero_means_unlimited(http, registered_user, settings_sandbox):
    """A quota of 0 is unlimited, not 'nothing allowed'."""
    key, _ = registered_user
    http.put("/api/v1/admin/settings", headers=ADMIN_HEADERS, json={"max_relics_per_user": 0})
    _settle()

    resp = _upload(http, key)
    assert resp.status_code == 200
    http.delete(f"/api/v1/relics/{resp.json()['id']}", headers=ADMIN_HEADERS)


@pytest.mark.integration
def test_storage_quota_enforced(http, registered_user):
    """An upload that would cross the storage quota is refused."""
    key, _ = registered_user
    http.put(
        f"/api/v1/admin/users/{key}/quotas",
        headers=ADMIN_HEADERS,
        json={"quota_max_storage_bytes": 100},
    )

    ok = _upload(http, key, content=b"x" * 60)
    assert ok.status_code == 200

    # 60 already used, so another 60 crosses the 100-byte ceiling
    assert _upload(http, key, content=b"x" * 60).status_code == 413

    http.delete(f"/api/v1/relics/{ok.json()['id']}", headers=ADMIN_HEADERS)


@pytest.mark.integration
def test_admin_is_exempt_from_quotas(http, settings_sandbox):
    """Global quotas do not apply to admins, who must stay able to operate."""
    http.put("/api/v1/admin/settings", headers=ADMIN_HEADERS, json={"max_relics_per_user": 1})
    _settle()

    created = []
    for _ in range(3):
        resp = _upload(http, ADMIN_KEY)
        assert resp.status_code == 200
        created.append(resp.json()["id"])

    for relic_id in created:
        http.delete(f"/api/v1/relics/{relic_id}", headers=ADMIN_HEADERS)


@pytest.mark.integration
def test_fork_counts_against_storage_quota(http, registered_user, created_relic):
    """A fork duplicates stored bytes, so it must consume the forker's quota."""
    key, _ = registered_user
    http.put(
        f"/api/v1/admin/users/{key}/quotas",
        headers=ADMIN_HEADERS,
        json={"quota_max_storage_bytes": 10},
    )

    resp = http.post(
        f"/api/v1/relics/{created_relic['id']}/fork", headers={"X-User-Key": key}
    )
    assert resp.status_code == 413


# ── GET /api/v1/user/usage ──────────────────────────────────────────────────

@pytest.mark.integration
def test_usage_reflects_actual_uploads(http, registered_user):
    """Reported usage matches what the user actually stored."""
    key, _ = registered_user
    content = b"x" * 42
    resp = _upload(http, key, content=content)
    assert resp.status_code == 200

    usage = http.get("/api/v1/user/usage", headers={"X-User-Key": key}).json()["usage"]
    assert usage["relics"]["used"] == 1
    assert usage["storage_bytes"]["used"] == len(content)

    http.delete(f"/api/v1/relics/{resp.json()['id']}", headers=ADMIN_HEADERS)


@pytest.mark.integration
def test_usage_reports_limits_and_unlimited(http, registered_user, settings_sandbox):
    """Each dimension reports a limit, with 0 surfaced as unlimited."""
    key, _ = registered_user
    http.put(
        f"/api/v1/admin/users/{key}/quotas", headers=ADMIN_HEADERS, json={"quota_max_relics": 4}
    )
    _settle()

    usage = http.get("/api/v1/user/usage", headers={"X-User-Key": key}).json()["usage"]
    assert usage["relics"] == {"used": 0, "limit": 4, "unlimited": False}
    assert usage["storage_bytes"]["unlimited"] is True
    assert usage["storage_bytes"]["limit"] is None


@pytest.mark.integration
def test_usage_requires_authentication(http):
    """Usage is per-user, so anonymous callers get a 401."""
    assert http.get("/api/v1/user/usage").status_code == 401


@pytest.mark.integration
def test_usage_marks_admins_exempt(http):
    """Admins are flagged exempt so the UI can explain why nothing binds."""
    body = http.get("/api/v1/user/usage", headers=ADMIN_HEADERS).json()
    assert body["exempt"] is True


# ── Admin user listing ──────────────────────────────────────────────────────

@pytest.mark.integration
def test_admin_user_listing_includes_usage_and_quotas(http, registered_user):
    """The listing carries usage and effective quotas for the quota editor."""
    key, _ = registered_user
    http.put(
        f"/api/v1/admin/users/{key}/quotas", headers=ADMIN_HEADERS, json={"quota_max_relics": 6}
    )

    resp = http.get("/api/v1/admin/users", headers=ADMIN_HEADERS, params={"search": key})
    assert resp.status_code == 200
    user = next(u for u in resp.json()["users"] if u["id"] == key)

    assert user["storage_bytes"] == 0
    assert user["relic_count"] == 0
    assert user["quotas"]["max_relics"] == 6
    assert user["quota_overrides"]["quota_max_relics"] == 6
    # Untouched dimensions stay inherited
    assert user["quota_overrides"]["quota_max_storage_bytes"] is None

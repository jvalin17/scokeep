"""Unit tests for prod smoke SW cache-name validation, cold start, and cleanup."""

from unittest.mock import MagicMock

import pytest

from scripts.prod_smoke import (
    HEALTH_WAKE_ATTEMPTS,
    SmokeError,
    _fetch_health_past_wake,
    _is_render_waking,
    check_health,
    cleanup_smoke_playground,
    validate_sw_cache_name,
)

RENDER_INTERSTITIAL = (
    '<!doctype html>\n<html lang="en" data-theme="dark">\n  <head>\n'
    "    <title>Render - Application loading</title>\n  </head>\n</html>"
)
APP_DB_OUTAGE = {"status": "unhealthy", "database": "unavailable"}
APP_HEALTHY = {"status": "healthy", "database": "connected"}


def test_validate_sw_cache_name_accepts_content_hash():
    validate_sw_cache_name("scokeep-b9f3b2a2ef51")


def test_validate_sw_cache_name_rejects_legacy_manual_version():
    with pytest.raises(SmokeError, match="content-hash"):
        validate_sw_cache_name("scokeep-v82")


def test_validate_sw_cache_name_rejects_garbage():
    with pytest.raises(SmokeError):
        validate_sw_cache_name("not-a-cache")
    with pytest.raises(SmokeError):
        validate_sw_cache_name("scokeep-short")
    with pytest.raises(SmokeError):
        validate_sw_cache_name("scokeep-b9f3b2a2ef51XXXX")


def test_cleanup_smoke_playground_deletes_room(monkeypatch):
    calls: list[tuple] = []

    def fake_request(opener, base, path, *, method="GET", body=None, timeout=45):
        calls.append((method, path, body))
        return 200, {"deleted": body["name"] if body else None}

    monkeypatch.setattr("scripts.prod_smoke._request", fake_request)
    cleanup_smoke_playground(MagicMock(), "https://example.test", "CISmoke123456", "4321")
    assert len(calls) == 1
    method, path, body = calls[0]
    assert method == "DELETE"
    assert path == "/api/playground"
    assert body == {"name": "CISmoke123456", "pin": "4321"}


def test_cleanup_smoke_playground_tolerates_delete_failure(monkeypatch):
    def fake_request(opener, base, path, *, method="GET", body=None, timeout=45):
        return 500, {"detail": "boom"}

    monkeypatch.setattr("scripts.prod_smoke._request", fake_request)
    cleanup_smoke_playground(MagicMock(), "https://example.test", "CISmokeX", "4321")


def test_is_render_waking_detects_interstitial_html():
    assert _is_render_waking(RENDER_INTERSTITIAL) is True


def test_is_render_waking_ignores_app_db_outage_json():
    """A real DB outage is also 503 — it must never look like a cold start."""
    assert _is_render_waking(APP_DB_OUTAGE) is False


def test_is_render_waking_ignores_unrelated_html():
    assert _is_render_waking("<html><title>Bad Gateway</title></html>") is False


def test_fetch_health_past_wake_retries_cold_start_then_succeeds(monkeypatch):
    responses = [
        (503, RENDER_INTERSTITIAL),
        (503, RENDER_INTERSTITIAL),
        (200, APP_HEALTHY),
    ]
    slept: list[float] = []
    monkeypatch.setattr("scripts.prod_smoke.time.sleep", lambda s: slept.append(s))
    monkeypatch.setattr(
        "scripts.prod_smoke._request",
        lambda *a, **k: responses.pop(0),
    )

    status, body = _fetch_health_past_wake(MagicMock(), "https://example.test")

    assert status == 200
    assert body == APP_HEALTHY
    assert len(slept) == 2, "should sleep once per cold-start retry"


def test_fetch_health_past_wake_gives_up_after_ceiling(monkeypatch):
    attempts = {"n": 0}

    def fake_request(*a, **k):
        attempts["n"] += 1
        return 503, RENDER_INTERSTITIAL

    monkeypatch.setattr("scripts.prod_smoke.time.sleep", lambda s: None)
    monkeypatch.setattr("scripts.prod_smoke._request", fake_request)

    status, _body = _fetch_health_past_wake(MagicMock(), "https://example.test")

    assert status == 503
    assert attempts["n"] == HEALTH_WAKE_ATTEMPTS, "bounded — must not retry forever"


def test_check_health_retries_render_cold_start(monkeypatch):
    responses = [(503, RENDER_INTERSTITIAL), (200, APP_HEALTHY)]
    monkeypatch.setattr("scripts.prod_smoke.time.sleep", lambda s: None)
    monkeypatch.setattr("scripts.prod_smoke._request", lambda *a, **k: responses.pop(0))

    check_health(MagicMock(), "https://example.test")

    assert responses == [], "both responses consumed — cold start was retried"


def test_check_health_fails_fast_on_db_outage_503(monkeypatch):
    """Regression guard: cold-start retry must not mask a real DB outage."""
    attempts = {"n": 0}

    def fake_request(*a, **k):
        attempts["n"] += 1
        return 503, APP_DB_OUTAGE

    monkeypatch.setattr("scripts.prod_smoke.time.sleep", lambda s: None)
    monkeypatch.setattr("scripts.prod_smoke._request", fake_request)

    with pytest.raises(SmokeError, match="health HTTP 503"):
        check_health(MagicMock(), "https://example.test")
    assert attempts["n"] == 1, "a real outage must fail on the first response"


def test_check_health_fails_on_sustained_503(monkeypatch):
    monkeypatch.setattr("scripts.prod_smoke.time.sleep", lambda s: None)
    monkeypatch.setattr(
        "scripts.prod_smoke._request",
        lambda *a, **k: (503, RENDER_INTERSTITIAL),
    )

    with pytest.raises(SmokeError, match="health HTTP 503"):
        check_health(MagicMock(), "https://example.test")


def test_check_health_still_rejects_disconnected_database(monkeypatch):
    monkeypatch.setattr("scripts.prod_smoke.time.sleep", lambda s: None)
    monkeypatch.setattr(
        "scripts.prod_smoke._request",
        lambda *a, **k: (200, {"status": "healthy", "database": "unavailable"}),
    )

    with pytest.raises(SmokeError, match="database not connected"):
        check_health(MagicMock(), "https://example.test")

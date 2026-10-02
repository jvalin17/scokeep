"""Unit tests for prod smoke SW cache-name validation and room cleanup."""

from unittest.mock import MagicMock

import pytest

from scripts.prod_smoke import (
    SmokeError,
    cleanup_smoke_playground,
    validate_sw_cache_name,
)


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

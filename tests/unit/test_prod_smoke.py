"""Unit tests for prod smoke SW cache-name validation (content-hash era)."""

import pytest

from scripts.prod_smoke import SmokeError, validate_sw_cache_name


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

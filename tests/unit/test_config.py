"""Unit tests for app configuration."""

import pytest
from pydantic import ValidationError


def test_default_environment_is_development():
    """Without ENVIRONMENT env var, default to development."""
    from app.config import Settings

    s = Settings(database_url="sqlite+aiosqlite:///./test.db")
    assert s.environment == "development"


def test_environment_accepts_valid_values(monkeypatch):
    """ENVIRONMENT must accept development, staging, production."""
    for env in ("development", "staging", "production"):
        monkeypatch.setenv("ENVIRONMENT", env)
        from app.config import Settings

        s = Settings(database_url="sqlite+aiosqlite:///./test.db")
        assert s.environment == env


def test_environment_rejects_invalid_value(monkeypatch):
    """ENVIRONMENT with a typo or invalid value must raise at startup."""
    monkeypatch.setenv("ENVIRONMENT", "prod")
    from app.config import Settings

    with pytest.raises(ValidationError):
        Settings(database_url="sqlite+aiosqlite:///./test.db")

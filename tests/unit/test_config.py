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
        if env == "production":
            monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-production")
        from app.config import Settings

        s = Settings(database_url="sqlite+aiosqlite:///./test.db")
        assert s.environment == env


def test_environment_rejects_invalid_value(monkeypatch):
    """ENVIRONMENT with a typo or invalid value must raise at startup."""
    monkeypatch.setenv("ENVIRONMENT", "prod")
    from app.config import Settings

    with pytest.raises(ValidationError):
        Settings(database_url="sqlite+aiosqlite:///./test.db")


def test_production_without_secret_key_raises(monkeypatch):
    """Production environment must have an explicit SECRET_KEY — random default is unsafe."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    from app.config import Settings

    with pytest.raises(ValueError, match="SECRET_KEY.*production"):
        Settings(database_url="sqlite+aiosqlite:///./test.db")


def test_production_with_secret_key_succeeds(monkeypatch):
    """Production with an explicit SECRET_KEY works fine."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY", "my-secure-key-here-1234567890abcdef")
    from app.config import Settings

    s = Settings(database_url="sqlite+aiosqlite:///./test.db")
    assert s.secret_key == "my-secure-key-here-1234567890abcdef"

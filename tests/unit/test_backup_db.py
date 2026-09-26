"""Unit tests for scripts/backup_db.py helpers (no live DB)."""

from scripts.backup_db import default_backup_path, resolve_database_url, write_backup


def test_resolve_database_url_prefers_explicit(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://env/db")
    url = resolve_database_url("postgresql+asyncpg://explicit/db?sslmode=require")
    assert url == "postgresql://explicit/db"


def test_default_backup_path_includes_label(tmp_path):
    path = default_backup_path("prod", tmp_path)
    assert path.parent == tmp_path
    assert "prod" in path.name
    assert path.suffix == ".json"


def test_write_backup_creates_json_file(tmp_path):
    out = tmp_path / "sample.json"
    payload = {"tables": {"game": [], "game_count": 0}}
    written = write_backup(payload, out)
    assert written == out
    assert out.is_file()
    assert '"game_count": 0' in out.read_text(encoding="utf-8")

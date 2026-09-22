"""Unit tests for database layer — query safety, error handling."""

import inspect

from app import database as db_module
from app.services import analytics, insights


class TestQueryLimits:
    def test_analytics_load_data_has_limit(self):
        """Analytics _load_data query must include .limit() to prevent unbounded reads."""
        source = inspect.getsource(analytics.AnalyticsService._load_data)
        assert ".limit(" in source, "AnalyticsService._load_data must use .limit() on game query"

    def test_insights_load_game_data_has_limit(self):
        """Insights _load_game_data query must include .limit()."""
        source = inspect.getsource(insights._load_game_data)
        assert ".limit(" in source, "insights._load_game_data must use .limit() on game query"


class TestMigrationCoverage:
    def test_all_game_model_columns_have_migration(self):
        """Every column added after initial schema must have an ALTER TABLE."""
        source = inspect.getsource(db_module.create_tables)
        # Columns added after the initial create_all:
        late_columns = ["client_game_id", "source", "updated_at"]
        for col in late_columns:
            assert col in source, (
                f"game.{col} is in the model but has no ALTER TABLE migration in create_tables()"
            )


class TestDatabaseErrorHandling:
    def test_alter_table_suppress_is_narrow(self):
        """ALTER TABLE migrations must suppress only DB-specific errors, not bare Exception."""
        source = inspect.getsource(db_module.create_tables)
        assert "suppress(Exception)" not in source, (
            "init_db uses suppress(Exception) which swallows connection errors — "
            "must use suppress(ProgrammingError, OperationalError) instead"
        )
        assert "ProgrammingError" in source, "Must suppress ProgrammingError (PostgreSQL)"
        assert "OperationalError" in source, "Must suppress OperationalError (SQLite)"

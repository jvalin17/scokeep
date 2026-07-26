"""Tests for playground service logic.

Fixtures are synthetic — designed to test PIN hashing, share code generation,
and player management.
"""

import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.playground import PlaygroundService


class TestCreatePlayground:

    async def test_creates_playground_with_hashed_pin(self, db_session: AsyncSession):
        playground = await PlaygroundService.create(
            db=db_session,
            name="The Cardinals",
            pin="1234",
            players=["Alice", "Bob", "Charlie"],
        )

        assert playground.name == "The Cardinals"
        assert playground.players == ["Alice", "Bob", "Charlie"]
        assert bcrypt.checkpw(b"1234", playground.pin_hash.encode())

    async def test_pin_is_never_stored_plain(self, db_session: AsyncSession):
        playground = await PlaygroundService.create(
            db=db_session, name="Test", pin="5678", players=["A"]
        )

        assert playground.pin_hash != "5678"
        assert len(playground.pin_hash) > 50  # bcrypt hashes are ~60 chars

    async def test_share_code_is_4_chars_alphanumeric(self, db_session: AsyncSession):
        playground = await PlaygroundService.create(
            db=db_session, name="Test", pin="1234", players=["A"]
        )

        assert len(playground.share_code) == 4
        assert playground.share_code.isalnum()

    async def test_two_playgrounds_get_different_share_codes(self, db_session: AsyncSession):
        pg1 = await PlaygroundService.create(
            db=db_session, name="Group A", pin="1111", players=["A"]
        )
        pg2 = await PlaygroundService.create(
            db=db_session, name="Group B", pin="2222", players=["B"]
        )

        assert pg1.share_code != pg2.share_code


class TestVerifyPin:

    async def test_correct_pin_returns_true(self, db_session: AsyncSession):
        playground = await PlaygroundService.create(
            db=db_session, name="Test", pin="9876", players=["A"]
        )

        assert PlaygroundService.verify_pin(playground, "9876") is True

    async def test_wrong_pin_returns_false(self, db_session: AsyncSession):
        playground = await PlaygroundService.create(
            db=db_session, name="Test", pin="9876", players=["A"]
        )

        assert PlaygroundService.verify_pin(playground, "0000") is False


class TestGetByShareCode:

    async def test_returns_playground_when_found(self, db_session: AsyncSession):
        created = await PlaygroundService.create(
            db=db_session, name="Finders", pin="1234", players=["X", "Y"]
        )

        found = await PlaygroundService.get_by_share_code(db_session, created.share_code)
        assert found is not None
        assert found.id == created.id
        assert found.name == "Finders"

    async def test_returns_none_when_not_found(self, db_session: AsyncSession):
        found = await PlaygroundService.get_by_share_code(db_session, "ZZZZZZZZ")
        assert found is None


class TestTimestampDefaults:
    """Timestamp defaults must use SQL func.now(), not Python datetime, for asyncpg compat."""

    def test_created_at_default_is_sql_expression(self):
        """Column default must be a SQL expression (func.now), not a Python callable.

        Python datetime.utcnow defaults get converted to tz-aware by SQLAlchemy's
        asyncpg dialect, which asyncpg rejects for TIMESTAMP WITHOUT TIME ZONE columns.
        Using func.now() generates server-side now() in SQL, bypassing the issue.
        """
        from sqlalchemy.sql.functions import Function

        from app.models.playground import Playground

        col = Playground.__table__.c.created_at
        assert col.default is not None, "created_at must have a default"
        assert isinstance(col.default.arg, Function), (
            f"created_at default must be a SQL function (func.now()), not {type(col.default.arg)}. "
            "Python datetime defaults break asyncpg on PostgreSQL."
        )

    def test_updated_at_default_is_sql_expression(self):
        from sqlalchemy.sql.functions import Function

        from app.models.playground import Playground

        col = Playground.__table__.c.updated_at
        assert col.default is not None, "updated_at must have a default"
        assert isinstance(col.default.arg, Function), (
            f"updated_at default must be a SQL function (func.now()), not {type(col.default.arg)}. "
            "Python datetime defaults break asyncpg on PostgreSQL."
        )

    def test_insert_sql_uses_now_not_bind_params(self):
        """The INSERT SQL must use now() for timestamps, not bind parameters."""
        from sqlalchemy.dialects import postgresql

        from app.models.playground import Playground

        stmt = Playground.__table__.insert().values(
            name="test", pin_hash="hash", share_code="ABCD1234", players=[]
        )
        compiled = str(stmt.compile(dialect=postgresql.dialect()))
        assert "now()" in compiled, (
            f"INSERT must use now() for timestamps, got: {compiled}"
        )

    async def test_created_at_is_populated_after_insert(self, db_session: AsyncSession):
        playground = await PlaygroundService.create(
            db=db_session, name="TZ Test", pin="1234", players=["A"]
        )

        assert playground.created_at is not None
        assert playground.updated_at is not None


class TestGetByName:

    async def test_returns_playground_when_found(self, db_session: AsyncSession):
        await PlaygroundService.create(
            db=db_session, name="The Aces", pin="1234", players=["A"]
        )

        found = await PlaygroundService.get_by_name(db_session, "The Aces")
        assert found is not None
        assert found.name == "The Aces"

    async def test_returns_none_when_not_found(self, db_session: AsyncSession):
        found = await PlaygroundService.get_by_name(db_session, "Nonexistent")
        assert found is None

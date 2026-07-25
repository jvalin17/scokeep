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

    async def test_share_code_is_8_chars_alphanumeric(self, db_session: AsyncSession):
        playground = await PlaygroundService.create(
            db=db_session, name="Test", pin="1234", players=["A"]
        )

        assert len(playground.share_code) == 8
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

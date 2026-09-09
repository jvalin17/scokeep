"""Tests for game service logic.

Fixtures are synthetic — designed to test game creation, phase transitions,
dealer rotation, and game ending.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.game import GameService
from app.services.playground import PlaygroundService


async def _create_playground(db: AsyncSession):
    return await PlaygroundService.create(
        db=db, name="Test Group", pin="1234", players=["Alice", "Bob", "Charlie", "Dave"]
    )


class TestCreateGame:
    async def test_creates_game_with_default_settings(self, db_session: AsyncSession):
        playground = await _create_playground(db_session)
        game = await GameService.create(
            db=db_session,
            playground_id=playground.id,
            players=["Alice", "Bob", "Charlie", "Dave"],
            settings={},
        )

        assert game.playground_id == playground.id
        assert game.players == ["Alice", "Bob", "Charlie", "Dave"]
        assert game.current_round == 1
        assert game.phase == "bidding"
        assert game.dealer_index == 0
        assert game.status == "active"

    async def test_total_rounds_equals_sets_times_8(self, db_session: AsyncSession):
        playground = await _create_playground(db_session)
        game = await GameService.create(
            db=db_session,
            playground_id=playground.id,
            players=["A", "B"],
            settings={"num_sets": 3},
        )

        assert game.total_rounds == 24  # 3 sets × 8 rounds

    async def test_custom_num_sets(self, db_session: AsyncSession):
        playground = await _create_playground(db_session)
        game = await GameService.create(
            db=db_session,
            playground_id=playground.id,
            players=["A", "B"],
            settings={"num_sets": 5},
        )

        assert game.total_rounds == 40  # 5 sets × 8

    async def test_settings_stored_in_game(self, db_session: AsyncSession):
        playground = await _create_playground(db_session)
        game = await GameService.create(
            db=db_session,
            playground_id=playground.id,
            players=["A", "B"],
            settings={"mode": "friendly", "must_lose": True, "timer_seconds": 5},
        )

        assert game.settings["mode"] == "friendly"
        assert game.settings["must_lose"] is True
        assert game.settings["timer_seconds"] == 5


class TestGetGame:
    async def test_get_by_id(self, db_session: AsyncSession):
        playground = await _create_playground(db_session)
        created = await GameService.create(
            db=db_session,
            playground_id=playground.id,
            players=["A", "B"],
            settings={},
        )

        found = await GameService.get_by_id(db_session, created.id)
        assert found is not None
        assert found.id == created.id

    async def test_get_nonexistent_returns_none(self, db_session: AsyncSession):
        found = await GameService.get_by_id(db_session, 9999)
        assert found is None


class TestAdvanceRound:
    async def test_advances_round_and_dealer(self, db_session: AsyncSession):
        playground = await _create_playground(db_session)
        game = await GameService.create(
            db=db_session,
            playground_id=playground.id,
            players=["A", "B", "C", "D"],
            settings={},
        )

        await GameService.advance_round(db_session, game)

        assert game.current_round == 2
        assert game.dealer_index == 1
        assert game.phase == "bidding"

    async def test_dealer_wraps_around(self, db_session: AsyncSession):
        playground = await _create_playground(db_session)
        game = await GameService.create(
            db=db_session,
            playground_id=playground.id,
            players=["A", "B", "C"],
            settings={},
        )

        # Advance 3 times — dealer should wrap: 0→1→2→0
        for _ in range(3):
            await GameService.advance_round(db_session, game)

        assert game.dealer_index == 0  # wrapped back

    async def test_finishes_game_at_last_round(self, db_session: AsyncSession):
        playground = await _create_playground(db_session)
        game = await GameService.create(
            db=db_session,
            playground_id=playground.id,
            players=["A", "B"],
            settings={"num_sets": 1},  # 8 rounds total
        )

        # Advance through all 8 rounds
        for _ in range(8):
            await GameService.advance_round(db_session, game)

        assert game.status == "finished"
        assert game.phase == "final"
        assert game.finished_at is not None


class TestEndGameEarly:
    async def test_ends_active_game(self, db_session: AsyncSession):
        playground = await _create_playground(db_session)
        game = await GameService.create(
            db=db_session,
            playground_id=playground.id,
            players=["A", "B"],
            settings={},
        )

        await GameService.end_game(db_session, game)

        assert game.status == "finished"
        assert game.phase == "final"
        assert game.finished_at is not None


class TestUpdatePhase:
    async def test_updates_phase(self, db_session: AsyncSession):
        playground = await _create_playground(db_session)
        game = await GameService.create(
            db=db_session,
            playground_id=playground.id,
            players=["A", "B"],
            settings={},
        )

        await GameService.update_phase(db_session, game, "playing")
        assert game.phase == "playing"

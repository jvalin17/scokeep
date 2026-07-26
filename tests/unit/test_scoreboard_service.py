"""Tests for scoreboard and undo logic.

Fixtures are synthetic — designed to verify cumulative score calculation,
round history retrieval, and undo correctness.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.game import GameService
from app.services.playground import PlaygroundService
from app.services.round import RoundService
from app.services.scoreboard import ScoreboardService


async def _setup_game_with_rounds(db: AsyncSession, num_rounds: int = 3):
    """Helper: create playground + game + play N rounds with known data."""
    playground = await PlaygroundService.create(
        db=db, name="Score Test", pin="1234",
        players=["Alice", "Bob", "Charlie"],
    )
    game = await GameService.create(
        db=db,
        playground_id=playground.id,
        players=["Alice", "Bob", "Charlie"],
        settings={"num_sets": 1},
    )

    # Round data: (bids, hands_won)
    round_data = [
        ({"0": 2, "1": 0, "2": 1}, {"0": 2, "1": 0, "2": 1}),   # P0=20, P1=10, P2=11
        ({"0": 0, "1": 3, "2": 0}, {"0": 1, "1": 3, "2": 0}),   # P0=-10, P1=30, P2=10
        ({"0": 1, "1": 1, "2": 0}, {"0": 1, "1": 0, "2": 0}),   # P0=11, P1=-11, P2=10
    ]

    for i in range(min(num_rounds, len(round_data))):
        round_obj = await RoundService.create_round(db, game)
        bids, hands = round_data[i]
        round_obj.bids = bids
        round_obj.hands_won = hands
        round_obj.status = "round_end"
        await db.commit()
        await RoundService.end_round(db, round_obj, player_count=3, formula="kachuful_standard")
        await GameService.advance_round(db, game)

    return game


class TestGetScoreboard:

    async def test_cumulative_scores_after_3_rounds(self, db_session: AsyncSession):
        game = await _setup_game_with_rounds(db_session, num_rounds=3)

        scoreboard = await ScoreboardService.get_scoreboard(
            db_session, game.id, player_count=len(game.players),
        )

        # Round 1: 20, 10, 11  |  Round 2: -10, 30, 10  |  Round 3: 11, -11, 10
        assert scoreboard["totals"] == {"0": 21, "1": 29, "2": 31}

    async def test_scoreboard_with_no_rounds(self, db_session: AsyncSession):
        playground = await PlaygroundService.create(
            db=db_session, name="Empty", pin="1234", players=["A", "B"],
        )
        game = await GameService.create(
            db=db_session, playground_id=playground.id,
            players=["A", "B"], settings={"num_sets": 1},
        )

        scoreboard = await ScoreboardService.get_scoreboard(
            db_session, game.id, player_count=len(game.players),
        )

        assert scoreboard["totals"] == {"0": 0, "1": 0}
        assert scoreboard["rounds"] == []

    async def test_scoreboard_includes_per_round_scores(self, db_session: AsyncSession):
        game = await _setup_game_with_rounds(db_session, num_rounds=2)

        scoreboard = await ScoreboardService.get_scoreboard(
            db_session, game.id, player_count=len(game.players),
        )

        assert len(scoreboard["rounds"]) == 2
        assert scoreboard["rounds"][0]["scores"] == {"0": 20, "1": 10, "2": 11}
        assert scoreboard["rounds"][1]["scores"] == {"0": -10, "1": 30, "2": 10}


class TestGetHistory:

    async def test_history_shows_bids_and_actuals(self, db_session: AsyncSession):
        game = await _setup_game_with_rounds(db_session, num_rounds=2)

        history = await ScoreboardService.get_history(db_session, game.id)

        assert len(history) == 2
        assert history[0]["bids"] == {"0": 2, "1": 0, "2": 1}
        assert history[0]["hands_won"] == {"0": 2, "1": 0, "2": 1}
        assert history[0]["scores"] == {"0": 20, "1": 10, "2": 11}


class TestUndoLastRound:

    async def test_undo_clears_round_and_decrements(self, db_session: AsyncSession):
        game = await _setup_game_with_rounds(db_session, num_rounds=2)

        assert game.current_round == 3  # after 2 scored rounds + advance, next is 3

        await ScoreboardService.undo_last_round(db_session, game)

        assert game.current_round == 1
        assert game.phase == "scoreboard"

    async def test_undo_restores_correct_totals(self, db_session: AsyncSession):
        game = await _setup_game_with_rounds(db_session, num_rounds=3)

        # Before undo: totals = {0: 21, 1: 29, 2: 31}
        await ScoreboardService.undo_last_round(db_session, game)

        # After undo round 3: totals should be round 1+2 only
        scoreboard = await ScoreboardService.get_scoreboard(
            db_session, game.id, player_count=len(game.players),
        )
        assert scoreboard["totals"] == {"0": 10, "1": 40, "2": 21}

    async def test_undo_then_redo_produces_same_scores(self, db_session: AsyncSession):
        game = await _setup_game_with_rounds(db_session, num_rounds=2)

        scoreboard_before = await ScoreboardService.get_scoreboard(
            db_session, game.id, player_count=len(game.players),
        )

        # Undo round 2
        await ScoreboardService.undo_last_round(db_session, game)

        # Advance from scoreboard to re-enter round 2
        await GameService.advance_round(db_session, game)

        # Re-enter same data for round 2
        round_obj = await RoundService.create_round(db_session, game)
        round_obj.bids = {"0": 0, "1": 3, "2": 0}
        round_obj.hands_won = {"0": 1, "1": 3, "2": 0}
        round_obj.status = "round_end"
        await db_session.commit()
        await RoundService.end_round(
            db_session, round_obj, player_count=3, formula="kachuful_standard"
        )
        await GameService.advance_round(db_session, game)

        scoreboard_after = await ScoreboardService.get_scoreboard(
            db_session, game.id, player_count=len(game.players),
        )
        assert scoreboard_after["totals"] == scoreboard_before["totals"]

    async def test_undo_with_no_rounds_raises(self, db_session: AsyncSession):
        playground = await PlaygroundService.create(
            db=db_session, name="No Rounds", pin="1234", players=["A", "B"],
        )
        game = await GameService.create(
            db=db_session, playground_id=playground.id,
            players=["A", "B"], settings={"num_sets": 1},
        )

        with pytest.raises(ValueError, match="No rounds to undo"):
            await ScoreboardService.undo_last_round(db_session, game)

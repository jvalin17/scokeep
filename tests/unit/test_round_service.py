"""Tests for round service logic.

Covers: bid submission, phase enforcement, must-lose mode,
hands entry, scoring calculation, round advancement.
Fixtures are synthetic — designed to cover all phase gates and edge cases.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.game import GameService
from app.services.playground import PlaygroundService
from app.services.round import RoundService


async def _setup_game(db: AsyncSession, num_sets: int = 1, must_lose: bool = False):
    """Helper: create playground + game, return game."""
    playground = await PlaygroundService.create(
        db=db, name="Round Test", pin="1234",
        players=["Alice", "Bob", "Charlie", "Dave"],
    )
    game = await GameService.create(
        db=db,
        playground_id=playground.id,
        players=["Alice", "Bob", "Charlie", "Dave"],
        settings={"num_sets": num_sets, "must_lose": must_lose},
    )
    return game


class TestCreateRound:

    async def test_creates_round_for_game(self, db_session: AsyncSession):
        game = await _setup_game(db_session)
        round_obj = await RoundService.create_round(db_session, game)

        assert round_obj.game_id == game.id
        assert round_obj.round_num == 1
        assert round_obj.cards_dealt == 8
        assert round_obj.trump_suit == "spades"
        assert round_obj.bids == {}
        assert round_obj.hands_won == {}
        assert round_obj.status == "bidding"


class TestSubmitBid:

    async def test_submit_bid_stores_value(self, db_session: AsyncSession):
        game = await _setup_game(db_session)
        round_obj = await RoundService.create_round(db_session, game)

        await RoundService.submit_bid(db_session, round_obj, player_index=0, value=3)

        assert round_obj.bids["0"] == 3

    async def test_reject_duplicate_bid(self, db_session: AsyncSession):
        game = await _setup_game(db_session)
        round_obj = await RoundService.create_round(db_session, game)

        await RoundService.submit_bid(db_session, round_obj, player_index=0, value=3)
        with pytest.raises(ValueError, match="already submitted"):
            await RoundService.submit_bid(db_session, round_obj, player_index=0, value=2)

    async def test_reject_bid_when_not_bidding_phase(self, db_session: AsyncSession):
        game = await _setup_game(db_session)
        round_obj = await RoundService.create_round(db_session, game)
        round_obj.status = "playing"
        await db_session.commit()

        with pytest.raises(ValueError, match="not in bidding phase"):
            await RoundService.submit_bid(db_session, round_obj, player_index=0, value=1)


class TestMustLoseMode:

    async def test_rejects_bid_that_equals_cards_dealt(self, db_session: AsyncSession):
        game = await _setup_game(db_session, must_lose=True)
        round_obj = await RoundService.create_round(db_session, game)

        # 8 cards dealt, 4 players. Bids so far: 2+3+1=6. Bid 2 would make total=8=cards
        await RoundService.submit_bid(db_session, round_obj, player_index=0, value=2)
        await RoundService.submit_bid(db_session, round_obj, player_index=1, value=3)
        await RoundService.submit_bid(db_session, round_obj, player_index=2, value=1)

        with pytest.raises(ValueError, match="must-lose"):
            await RoundService.submit_bid(
                db_session, round_obj, player_index=3, value=2,
                must_lose=True, cards_dealt=8, player_count=4,
            )

    async def test_allows_bid_that_doesnt_equal_cards(self, db_session: AsyncSession):
        game = await _setup_game(db_session, must_lose=True)
        round_obj = await RoundService.create_round(db_session, game)

        await RoundService.submit_bid(db_session, round_obj, player_index=0, value=2)
        await RoundService.submit_bid(db_session, round_obj, player_index=1, value=3)
        await RoundService.submit_bid(db_session, round_obj, player_index=2, value=1)

        # Bid 0 → total=6 ≠ 8, allowed
        await RoundService.submit_bid(
            db_session, round_obj, player_index=3, value=0,
            must_lose=True, cards_dealt=8, player_count=4,
        )
        assert round_obj.bids["3"] == 0

    async def test_must_lose_only_blocks_last_player(self, db_session: AsyncSession):
        """Must-lose only applies to the last player to bid."""
        game = await _setup_game(db_session, must_lose=True)
        round_obj = await RoundService.create_round(db_session, game)

        # With 8 cards, first player bids 8 — allowed (not last player)
        await RoundService.submit_bid(
            db_session, round_obj, player_index=0, value=8,
            must_lose=True, cards_dealt=8, player_count=4,
        )
        assert round_obj.bids["0"] == 8

    async def test_must_lose_blocks_last_player(self, db_session: AsyncSession):
        """Last player cannot make total equal cards dealt."""
        game = await _setup_game(db_session, must_lose=True)
        round_obj = await RoundService.create_round(db_session, game)

        await RoundService.submit_bid(db_session, round_obj, player_index=0, value=2)
        await RoundService.submit_bid(db_session, round_obj, player_index=1, value=3)
        await RoundService.submit_bid(db_session, round_obj, player_index=2, value=1)

        # Last player: bid 2 → total=8=cards, blocked
        with pytest.raises(ValueError, match="must-lose"):
            await RoundService.submit_bid(
                db_session, round_obj, player_index=3, value=2,
                must_lose=True, cards_dealt=8, player_count=4,
            )


class TestConfirmBids:

    async def test_confirm_bids_changes_phase(self, db_session: AsyncSession):
        game = await _setup_game(db_session)
        round_obj = await RoundService.create_round(db_session, game)

        for i in range(4):
            await RoundService.submit_bid(db_session, round_obj, player_index=i, value=1)

        await RoundService.confirm_bids(db_session, round_obj, player_count=4)
        assert round_obj.status == "playing"

    async def test_reject_confirm_with_missing_bids(self, db_session: AsyncSession):
        game = await _setup_game(db_session)
        round_obj = await RoundService.create_round(db_session, game)

        await RoundService.submit_bid(db_session, round_obj, player_index=0, value=1)

        with pytest.raises(ValueError, match="missing"):
            await RoundService.confirm_bids(db_session, round_obj, player_count=4)


class TestSubmitHands:

    async def test_submit_hands_stores_value(self, db_session: AsyncSession):
        game = await _setup_game(db_session)
        round_obj = await RoundService.create_round(db_session, game)
        round_obj.status = "round_end"
        await db_session.commit()

        await RoundService.submit_hands(db_session, round_obj, player_index=0, value=2)
        assert round_obj.hands_won["0"] == 2

    async def test_reject_hands_when_not_round_end(self, db_session: AsyncSession):
        game = await _setup_game(db_session)
        round_obj = await RoundService.create_round(db_session, game)

        with pytest.raises(ValueError, match="not in round_end phase"):
            await RoundService.submit_hands(db_session, round_obj, player_index=0, value=1)


class TestEndRound:

    async def test_calculates_scores_and_stores(self, db_session: AsyncSession):
        game = await _setup_game(db_session)
        round_obj = await RoundService.create_round(db_session, game)

        # Set up a round with bids and hands
        round_obj.bids = {"0": 2, "1": 0, "2": 3, "3": 1}
        round_obj.hands_won = {"0": 2, "1": 0, "2": 1, "3": 1}
        round_obj.status = "round_end"
        await db_session.commit()

        scores = await RoundService.end_round(
            db_session, round_obj, player_count=4, formula="kachuful_standard"
        )

        assert scores == {"0": 20, "1": 10, "2": -30, "3": 11}
        assert round_obj.scores == {"0": 20, "1": 10, "2": -30, "3": 11}
        assert round_obj.status == "scored"

    async def test_reject_end_round_with_missing_hands(self, db_session: AsyncSession):
        game = await _setup_game(db_session)
        round_obj = await RoundService.create_round(db_session, game)
        round_obj.bids = {"0": 1, "1": 1, "2": 1, "3": 1}
        round_obj.hands_won = {"0": 1}  # only 1 of 4
        round_obj.status = "round_end"
        await db_session.commit()

        with pytest.raises(ValueError, match="missing"):
            await RoundService.end_round(
                db_session, round_obj, player_count=4, formula="kachuful_standard"
            )

    async def test_allows_flexible_totals(self, db_session: AsyncSession):
        """Hands that don't sum to cards_dealt should still be scored (warn but allow)."""
        game = await _setup_game(db_session)
        round_obj = await RoundService.create_round(db_session, game)

        round_obj.bids = {"0": 2, "1": 1, "2": 0, "3": 0}
        round_obj.hands_won = {"0": 3, "1": 3, "2": 3, "3": 3}  # total=12 ≠ 8
        round_obj.status = "round_end"
        await db_session.commit()

        scores = await RoundService.end_round(
            db_session, round_obj, player_count=4, formula="kachuful_standard"
        )
        # Still calculates: P0 bid 2 got 3=miss=-20, P1 bid 1 got 3=miss=-11, etc.
        assert scores == {"0": -20, "1": -11, "2": -10, "3": -10}


class TestEditBid:

    async def test_edit_existing_bid(self, db_session: AsyncSession):
        game = await _setup_game(db_session)
        round_obj = await RoundService.create_round(db_session, game)

        await RoundService.submit_bid(db_session, round_obj, player_index=0, value=3)
        await RoundService.edit_bid(db_session, round_obj, player_index=0, value=5)

        assert round_obj.bids["0"] == 5

    async def test_reject_edit_nonexistent_bid(self, db_session: AsyncSession):
        game = await _setup_game(db_session)
        round_obj = await RoundService.create_round(db_session, game)

        with pytest.raises(ValueError, match="No bid exists"):
            await RoundService.edit_bid(db_session, round_obj, player_index=0, value=5)

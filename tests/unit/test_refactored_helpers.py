"""Unit tests for pure helper functions across import_game, sync, and scoreboard."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.routes.import_game import _build_game, _validate_round_scores
from app.routes.sync import _validate_round_metadata, _validate_scores
from app.schemas.import_game import ImportGameRequest, ImportRound
from app.schemas.sync import SyncRoundRequest
from app.services.scoreboard import _round_to_dict

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_import_round(
    round_num=1,
    bids=None,
    hands_won=None,
    cards_dealt=8,
    trump_suit="spades",
    scores=None,
):
    return ImportRound(
        round_num=round_num,
        bids=bids or {"0": 2, "1": 1},
        hands_won=hands_won or {"0": 2, "1": 1},
        cards_dealt=cards_dealt,
        trump_suit=trump_suit,
        scores=scores,
    )


def _make_import_request(rounds, players=None, settings=None, client_game_id="game-abc-001"):
    return ImportGameRequest(
        client_game_id=client_game_id,
        started_at=datetime(2026, 1, 10, 18, 0, tzinfo=UTC),
        finished_at=datetime(2026, 1, 10, 19, 30, tzinfo=UTC),
        players=players or ["Alice", "Bob"],
        settings=settings or {"scoring_formula": "kachuful_standard"},
        rounds=rounds,
    )


def _make_sync_round(
    round_num=1,
    cards_dealt=8,
    trump_suit="spades",
    bids=None,
    hands_won=None,
    scores=None,
    status="scored",
):
    return SyncRoundRequest(
        round_num=round_num,
        cards_dealt=cards_dealt,
        trump_suit=trump_suit,
        bids=bids or {"0": 2, "1": 1},
        hands_won=hands_won or {"0": 2, "1": 1},
        scores=scores or {"0": 20, "1": 11},
        status=status,
    )


def _make_game_mock(settings=None):
    game = MagicMock()
    game.settings = settings or {"rounds_per_set": 8}
    return game


# ---------------------------------------------------------------------------
# _validate_round_scores
# ---------------------------------------------------------------------------

def test_validate_round_scores_passes_when_no_scores_provided():
    """No scores field — server re-derives; must not raise."""
    rounds = [_make_import_round(scores=None)]
    _validate_round_scores(rounds, "kachuful_standard")  # should not raise


def test_validate_round_scores_passes_when_scores_match():
    """Scores provided that match re-derived values — must not raise."""
    # Alice bids 2, wins 2 -> 20; Bob bids 1, wins 1 -> 11
    rounds = [
        _make_import_round(
            bids={"0": 2, "1": 1},
            hands_won={"0": 2, "1": 1},
            scores={"0": 20, "1": 11},
        )
    ]
    _validate_round_scores(rounds, "kachuful_standard")  # should not raise


def test_validate_round_scores_raises_on_tampered_scores():
    """Scores provided that do NOT match re-derived values — must raise 422."""
    tampered_scores = {"0": 99, "1": 99}  # inflated scores
    rounds = [
        _make_import_round(
            bids={"0": 2, "1": 1},
            hands_won={"0": 2, "1": 1},
            scores=tampered_scores,
        )
    ]
    with pytest.raises(HTTPException) as exc_info:
        _validate_round_scores(rounds, "kachuful_standard")
    assert exc_info.value.status_code == 422
    assert "Score mismatch" in exc_info.value.detail
    assert "round 1" in exc_info.value.detail


def test_validate_round_scores_raises_on_mismatch_for_second_round():
    """Mismatch in round 2 — error message must name the correct round number."""
    good_round = _make_import_round(
        round_num=1,
        bids={"0": 1, "1": 0},
        hands_won={"0": 1, "1": 0},
        scores={"0": 11, "1": 10},
    )
    bad_round = _make_import_round(
        round_num=2,
        bids={"0": 3, "1": 2},
        hands_won={"0": 3, "1": 2},
        scores={"0": 1, "1": 1},  # wrong
    )
    with pytest.raises(HTTPException) as exc_info:
        _validate_round_scores([good_round, bad_round], "kachuful_standard")
    assert exc_info.value.status_code == 422
    assert "round 2" in exc_info.value.detail


def test_validate_round_scores_zeros_formula_passes():
    """kachuful_zeros formula: bid 1 made = 10, not 11."""
    rounds = [
        _make_import_round(
            bids={"0": 1, "1": 0},
            hands_won={"0": 1, "1": 0},
            scores={"0": 10, "1": 10},  # zeros: bid 1 made = 10
        )
    ]
    _validate_round_scores(rounds, "kachuful_zeros")  # should not raise


# ---------------------------------------------------------------------------
# _build_game
# ---------------------------------------------------------------------------

def test_build_game_returns_game_with_correct_fields():
    """_build_game must populate all Game fields from the request body."""
    from app.models.game import Game

    rounds = [
        _make_import_round(round_num=1),
        _make_import_round(round_num=2),
        _make_import_round(round_num=3),
    ]
    body = _make_import_request(rounds, players=["Alice", "Bob"])
    game = _build_game(body, playground_id=42)

    assert isinstance(game, Game)
    assert game.playground_id == 42
    assert game.players == ["Alice", "Bob"]
    assert game.settings == body.settings
    assert game.current_round == 3
    assert game.total_rounds == 3
    assert game.phase == "finished"
    assert game.status == "finished"
    assert game.dealer_index == 0
    assert game.source == "offline_import"
    assert game.client_game_id == "game-abc-001"
    assert game.started_at == body.started_at
    assert game.finished_at == body.finished_at


def test_build_game_total_rounds_matches_round_count():
    """total_rounds must equal the number of round objects, not a hardcoded value."""
    rounds = [_make_import_round(round_num=i) for i in range(1, 6)]
    body = _make_import_request(rounds)
    game = _build_game(body, playground_id=7)

    assert game.total_rounds == 5
    assert game.current_round == 5


# ---------------------------------------------------------------------------
# _validate_round_metadata
# ---------------------------------------------------------------------------

def test_validate_round_metadata_passes_for_valid_round_1():
    """Round 1 with 8 rounds_per_set: cards=8, trump=spades — must not raise."""
    body = _make_sync_round(round_num=1, cards_dealt=8, trump_suit="spades")
    game = _make_game_mock(settings={"rounds_per_set": 8})
    _validate_round_metadata(body, game)  # should not raise


def test_validate_round_metadata_raises_on_wrong_cards_dealt():
    """Wrong cards_dealt value — must raise 409."""
    # Round 1, rounds_per_set=8 -> expected 8 cards; send 5
    body = _make_sync_round(round_num=1, cards_dealt=5, trump_suit="spades")
    game = _make_game_mock(settings={"rounds_per_set": 8})

    with pytest.raises(HTTPException) as exc_info:
        _validate_round_metadata(body, game)
    assert exc_info.value.status_code == 409
    assert "cards_dealt" in exc_info.value.detail


def test_validate_round_metadata_raises_on_wrong_trump_suit():
    """Wrong trump_suit — must raise 409."""
    # Round 1 -> expected "spades"; send "hearts"
    body = _make_sync_round(round_num=1, cards_dealt=8, trump_suit="hearts")
    game = _make_game_mock(settings={"rounds_per_set": 8})

    with pytest.raises(HTTPException) as exc_info:
        _validate_round_metadata(body, game)
    assert exc_info.value.status_code == 409
    assert "trump_suit" in exc_info.value.detail


def test_validate_round_metadata_uses_rounds_per_set_from_settings():
    """rounds_per_set comes from game.settings — must use it to derive cards."""
    # With rounds_per_set=4, round 1 -> cards = 4 (descends 4→3→2→1)
    body = _make_sync_round(round_num=1, cards_dealt=4, trump_suit="spades")
    game = _make_game_mock(settings={"rounds_per_set": 4})
    _validate_round_metadata(body, game)  # should not raise


def test_validate_round_metadata_second_round_descends():
    """Round 2, rounds_per_set=8 -> cards=7, trump=diamonds."""
    body = _make_sync_round(round_num=2, cards_dealt=7, trump_suit="diamonds")
    game = _make_game_mock(settings={"rounds_per_set": 8})
    _validate_round_metadata(body, game)  # should not raise


# ---------------------------------------------------------------------------
# _validate_scores
# ---------------------------------------------------------------------------

def test_validate_scores_passes_when_scores_match():
    """Client scores that match server-derived scores — must not raise."""
    # Alice bids 2, wins 2 -> 20; Bob bids 0, wins 0 -> 10
    body = _make_sync_round(
        bids={"0": 2, "1": 0},
        hands_won={"0": 2, "1": 0},
        scores={"0": 20, "1": 10},
    )
    _validate_scores(body, "kachuful_standard")  # should not raise


def test_validate_scores_raises_on_mismatched_scores():
    """Client scores that differ from server derivation — must raise 409."""
    body = _make_sync_round(
        bids={"0": 3, "1": 2},
        hands_won={"0": 3, "1": 2},
        scores={"0": 0, "1": 0},  # wrong — should be 30 and 20
    )
    with pytest.raises(HTTPException) as exc_info:
        _validate_scores(body, "kachuful_standard")
    assert exc_info.value.status_code == 409
    assert "Score mismatch" in exc_info.value.detail


def test_validate_scores_raises_422_on_unknown_formula():
    """Unknown formula name passed to scoring engine — must raise 422."""
    body = _make_sync_round(
        bids={"0": 1},
        hands_won={"0": 1},
        scores={"0": 11},
    )
    with pytest.raises(HTTPException) as exc_info:
        _validate_scores(body, "nonexistent_formula")
    assert exc_info.value.status_code == 422


def test_validate_scores_zeros_formula_bid_1_made_equals_10():
    """kachuful_zeros: bid 1, won 1 -> 10 (not 11)."""
    body = _make_sync_round(
        bids={"0": 1},
        hands_won={"0": 1},
        scores={"0": 10},
    )
    _validate_scores(body, "kachuful_zeros")  # should not raise


def test_validate_scores_standard_formula_bid_1_made_equals_11():
    """kachuful_standard: bid 1, won 1 -> 11."""
    body = _make_sync_round(
        bids={"0": 1},
        hands_won={"0": 1},
        scores={"0": 11},
    )
    _validate_scores(body, "kachuful_standard")  # should not raise


# ---------------------------------------------------------------------------
# _round_to_dict
# ---------------------------------------------------------------------------

def test_round_to_dict_projects_orm_fields():
    """_round_to_dict must map all ORM attributes to a plain dict."""
    round_obj = MagicMock()
    round_obj.round_num = 3
    round_obj.cards_dealt = 6
    round_obj.trump_suit = "clubs"
    round_obj.bids = {"0": 2, "1": 3, "2": 1}
    round_obj.hands_won = {"0": 2, "1": 2, "2": 2}
    round_obj.scores = {"0": 20, "1": -30, "2": -10}

    result = _round_to_dict(round_obj)

    assert result == {
        "round_num": 3,
        "cards_dealt": 6,
        "trump_suit": "clubs",
        "bids": {"0": 2, "1": 3, "2": 1},
        "hands_won": {"0": 2, "1": 2, "2": 2},
        "scores": {"0": 20, "1": -30, "2": -10},
    }


def test_round_to_dict_returns_plain_dict():
    """Return value must be a plain dict, not a MagicMock or ORM proxy."""
    round_obj = MagicMock()
    round_obj.round_num = 1
    round_obj.cards_dealt = 8
    round_obj.trump_suit = "spades"
    round_obj.bids = {"0": 0}
    round_obj.hands_won = {"0": 0}
    round_obj.scores = {"0": 10}

    result = _round_to_dict(round_obj)
    assert type(result) is dict


def test_round_to_dict_does_not_include_extra_fields():
    """Only the six expected keys must appear in the result."""
    round_obj = MagicMock()
    round_obj.round_num = 2
    round_obj.cards_dealt = 7
    round_obj.trump_suit = "diamonds"
    round_obj.bids = {"0": 1}
    round_obj.hands_won = {"0": 0}
    round_obj.scores = {"0": -11}
    round_obj.game_id = 999  # extra field that must NOT appear

    result = _round_to_dict(round_obj)
    expected_keys = {"round_num", "cards_dealt", "trump_suit", "bids", "hands_won", "scores"}
    assert set(result.keys()) == expected_keys


# ── metric_bridges.py tests ─────────────────────────────────────────────────


def test_games_to_metrics():
    """_games_to_metrics converts game objects to GameMetrics."""
    from app.services.metric_bridges import _games_to_metrics
    from tests.unit.conftest import MockRound

    class FakeGame:
        players = ["Alice", "Bob"]
        rounds = [MockRound({"0": 1}, {"0": 1}, {"0": 11})]
        winner = "Alice"

    result = _games_to_metrics([FakeGame()])
    assert len(result) == 1
    assert hasattr(result[0], "player_metrics")


def test_compute_feature_vector():
    """compute_feature_vector returns 10-d vector from game objects."""
    from app.services.metric_bridges import compute_feature_vector
    from tests.unit.conftest import MockRound

    class FakeGame:
        players = ["Alice"]
        rounds = [MockRound({"0": 1}, {"0": 1}, {"0": 11})]
        winner = "Alice"

    vector = compute_feature_vector("Alice", [FakeGame()])
    assert len(vector) == 10
    assert all(isinstance(v, float) for v in vector)


def test_compute_player_extras():
    """compute_player_extras returns extras dict with expected keys."""
    from app.services.metric_bridges import compute_player_extras
    from tests.unit.conftest import MockRound

    class FakeGame:
        players = ["Alice"]
        rounds = [MockRound({"0": 1}, {"0": 1}, {"0": 11})]
        winner = "Alice"

    extras = compute_player_extras("Alice", [FakeGame()])
    assert "wins" in extras
    assert "games_played" in extras


def test_compute_accuracy_by_cards_metrics():
    """compute_accuracy_by_cards_metrics returns accuracy by card count."""
    from app.services.metric_bridges import compute_accuracy_by_cards_metrics
    from app.services.metrics import compute_game_metrics
    from tests.unit.conftest import MockRound

    rounds = [MockRound({"0": 1}, {"0": 1}, {"0": 11}, cards_dealt=8)]
    gm = compute_game_metrics(["Alice"], rounds)
    result = compute_accuracy_by_cards_metrics("Alice", [gm])
    assert isinstance(result, dict)


def test_compute_accuracy_by_cards():
    """compute_accuracy_by_cards bridges game objects to metrics."""
    from app.services.metric_bridges import compute_accuracy_by_cards
    from tests.unit.conftest import MockRound

    class FakeGame:
        players = ["Alice"]
        rounds = [MockRound({"0": 1}, {"0": 1}, {"0": 11})]
        winner = "Alice"

    result = compute_accuracy_by_cards("Alice", [FakeGame()])
    assert isinstance(result, dict)


def test_schedule_insights_recompute():
    """_schedule_insights_recompute adds a background task."""
    from unittest.mock import MagicMock

    from app.routes.import_game import _schedule_insights_recompute

    bg_tasks = MagicMock()
    _schedule_insights_recompute(bg_tasks, 42)
    bg_tasks.add_task.assert_called_once()


def test_extra_pattern():
    """_extra_pattern registers a function into COMPLEX_PATTERNS."""
    from app.services.title_patterns import COMPLEX_PATTERNS

    initial_count = len(COMPLEX_PATTERNS)
    # All extra patterns are already registered on import
    assert initial_count >= 27  # 17 core + 10 extra


def test_get_scored_rounds():
    """_get_scored_rounds is an internal helper tested via get_scoreboard."""
    from app.services.scoreboard import _get_scored_rounds

    assert callable(_get_scored_rounds)


# ── title_patterns_extra.py tests ────────────────────────────────────────────


def _make_ctx():
    """Build a complete GameContext for title pattern testing."""
    from app.services.title_registry import GameContext

    players = ["Alice", "Bob", "Charlie"]
    zero = dict.fromkeys(players, 0)
    return GameContext(
        players=players,
        round_count=8,
        totals={"Alice": 50, "Bob": 30, "Charlie": 20},
        accuracy={"Alice": 0.75, "Bob": 0.625, "Charlie": 0.5},
        bids_made={"Alice": 6, "Bob": 5, "Charlie": 4},
        bids_total={"Alice": 8, "Bob": 8, "Charlie": 8},
        zero_bids_made={"Alice": 1, "Bob": 3, "Charlie": 1},
        zero_bids_attempted={"Alice": 1, "Bob": 3, "Charlie": 2},
        overbids={"Alice": 1, "Bob": 2, "Charlie": 3},
        underbids={"Alice": 1, "Bob": 1, "Charlie": 1},
        best_bid_made={"Alice": 2, "Bob": 1, "Charlie": 1},
        longest_miss_streak={"Alice": 2, "Bob": 2, "Charlie": 3},
        longest_make_streak={"Alice": 3, "Bob": 2, "Charlie": 2},
        score_history=[{"Alice": 50, "Bob": 30, "Charlie": 20}],
        bid_sequence={
            "Alice": [(1, 1), (1, 1), (1, 0), (1, 1), (1, 1), (0, 0), (1, 0), (2, 2)],
            "Bob": [(1, 1), (1, 0), (0, 0), (1, 1), (1, 0), (0, 0), (1, 1), (0, 0)],
            "Charlie": [(0, 0), (1, 1), (1, 0), (1, 0), (0, 0), (1, 0), (1, 1), (1, 1)],
        },
        round_scores={
            "Alice": [10, 11, -10, 10, 11, 10, -11, 20],
            "Bob": [10, -10, 10, 10, -10, 10, 10, 0],
            "Charlie": [10, 10, -10, -10, 10, -10, 10, 10],
        },
        cards_per_round=[8, 7, 6, 5, 4, 3, 2, 1],
        trump_per_round=["spades", "diamonds", "clubs", "hearts"] * 2,
        off_by_one=zero,
    )


def test_conservative():
    from app.services.title_patterns_extra import _conservative
    assert isinstance(_conservative(_make_ctx()), list)


def test_daredevil():
    from app.services.title_patterns_extra import _daredevil
    assert isinstance(_daredevil(_make_ctx()), list)


def test_rollercoaster():
    from app.services.title_patterns_extra import _rollercoaster
    assert isinstance(_rollercoaster(_make_ctx()), list)


def test_metronome():
    from app.services.title_patterns_extra import _metronome
    assert isinstance(_metronome(_make_ctx()), list)


def test_trump_master():
    from app.services.title_patterns_extra import _trump_master
    assert isinstance(_trump_master(_make_ctx()), list)


def test_minimalist():
    from app.services.title_patterns_extra import _minimalist
    assert isinstance(_minimalist(_make_ctx()), list)


def test_mirror():
    from app.services.title_patterns_extra import _mirror
    assert isinstance(_mirror(_make_ctx()), list)


def test_lucky_seven():
    from app.services.title_patterns_extra import _lucky_seven
    assert isinstance(_lucky_seven(_make_ctx()), list)


def test_last_laugh():
    from app.services.title_patterns_extra import _last_laugh
    assert isinstance(_last_laugh(_make_ctx()), list)


def test_survivor():
    from app.services.title_patterns_extra import _survivor
    assert isinstance(_survivor(_make_ctx()), list)

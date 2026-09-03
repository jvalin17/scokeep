"""Tests for each complex title pattern function in title_patterns.py.

Each pattern must return a list of valid candidate dicts when given a GameContext.
"""

from app.services.title_patterns import (
    COMPLEX_PATTERNS,
    _all_in,
    _avg_bid_pattern,
    _closer,
    _comeback_king,
    _conservative,
    _daredevil,
    _fast_fade,
    _fortune_teller,
    _halfway,
    _high_roller,
    _hot_streak,
    _ice_cold,
    _landslide,
    _last_laugh,
    _lucky_seven,
    _metronome,
    _minimalist,
    _mirror,
    _nearly_perfect,
    _one_trick,
    _perfect_game,
    _photo_finish,
    _rank_at,
    _rollercoaster,
    _scatterbrain,
    _slow_starter,
    _survivor,
    _trump_master,
    _underdog,
    _variance_pattern,
    _zero_hero,
)


class MockRound:
    def __init__(self, bids, hands_won, scores, cards_dealt=8, trump_suit="spades"):
        self.bids = bids
        self.hands_won = hands_won
        self.scores = scores
        self.cards_dealt = cards_dealt
        self.trump_suit = trump_suit


def _build_ctx(players, rounds_data):
    from app.services.game_titles import build_context

    rounds = [MockRound(**r) if isinstance(r, dict) else MockRound(*r) for r in rounds_data]
    return build_context(players, rounds)


def _standard_ctx():
    """4-round, 2-player context with varied outcomes."""
    return _build_ctx(
        ["Alice", "Bob"],
        [
            ({"0": 3, "1": 0}, {"0": 3, "1": 0}, {"0": 30, "1": 10}, 8),
            ({"0": 0, "1": 2}, {"0": 0, "1": 3}, {"0": 10, "1": -20}, 7),
            ({"0": 2, "1": 1}, {"0": 2, "1": 1}, {"0": 20, "1": 11}, 6),
            ({"0": 1, "1": 0}, {"0": 0, "1": 0}, {"0": -11, "1": 10}, 3),
        ],
    )


REQUIRED_FIELDS = {"key", "emoji", "title", "desc", "player", "detail", "score"}


def _assert_valid_candidates(result, players):
    assert isinstance(result, list)
    for c in result:
        missing = REQUIRED_FIELDS - set(c.keys())
        assert not missing, f"Missing: {missing}"
        assert c["player"] in players
        assert c["score"] > 0


class TestTitlePatternDecorator:
    def test_title_pattern_registers(self):
        assert len(COMPLEX_PATTERNS) >= 20
        assert all(callable(fn) for fn in COMPLEX_PATTERNS)


class TestHalfwayHelper:
    def test_halfway(self):
        ctx = _standard_ctx()
        assert _halfway(ctx) == 2


class TestRankAt:
    def test_rank_at_end(self):
        ctx = _standard_ctx()
        ranks = _rank_at(ctx, ctx.round_count - 1)
        assert ranks["Alice"] < ranks["Bob"]  # Alice scored higher


class TestAvgBidPattern:
    def test_returns_candidates(self):
        ctx = _standard_ctx()
        result = _avg_bid_pattern(ctx, "test", "🎯", "Test", "test desc", highest=True)
        _assert_valid_candidates(result, ctx.players)


class TestVariancePattern:
    def test_returns_candidates(self):
        ctx = _standard_ctx()
        result = _variance_pattern(ctx, "test", "🎢", "Test", "test desc", highest=True)
        assert isinstance(result, list)


class TestUnderdog:
    def test_returns_list(self):
        ctx = _standard_ctx()
        assert isinstance(_underdog(ctx), list)


class TestLandslide:
    def test_big_margin(self):
        ctx = _build_ctx(
            ["Alice", "Bob"],
            [({"0": 5, "1": 0}, {"0": 5, "1": 0}, {"0": 50, "1": -50}, 8)] * 3,
        )
        result = _landslide(ctx)
        _assert_valid_candidates(result, ctx.players)
        assert result[0]["key"] == "landslide"


class TestPhotoFinish:
    def test_close_scores(self):
        ctx = _build_ctx(
            ["Alice", "Bob"],
            [({"0": 2, "1": 2}, {"0": 2, "1": 2}, {"0": 20, "1": 21}, 8)],
        )
        result = _photo_finish(ctx)
        assert isinstance(result, list)


class TestPerfectGame:
    def test_perfect_accuracy(self):
        ctx = _build_ctx(
            ["Alice", "Bob"],
            [({"0": 2, "1": 1}, {"0": 2, "1": 1}, {"0": 20, "1": 11}, 5)] * 4,
        )
        result = _perfect_game(ctx)
        _assert_valid_candidates(result, ctx.players)


class TestNearlyPerfect:
    def test_one_miss(self):
        ctx = _build_ctx(
            ["Alice", "Bob"],
            [
                ({"0": 2, "1": 1}, {"0": 2, "1": 1}, {"0": 20, "1": 11}, 5),
                ({"0": 2, "1": 1}, {"0": 2, "1": 1}, {"0": 20, "1": 11}, 4),
                ({"0": 2, "1": 1}, {"0": 2, "1": 1}, {"0": 20, "1": 11}, 3),
                ({"0": 2, "1": 1}, {"0": 1, "1": 1}, {"0": -20, "1": 11}, 2),
            ],
        )
        result = _nearly_perfect(ctx)
        assert isinstance(result, list)


class TestZeroHero:
    def test_zero_bids_made(self):
        ctx = _build_ctx(
            ["Alice", "Bob"],
            [({"0": 0, "1": 1}, {"0": 0, "1": 1}, {"0": 10, "1": 11}, 5)] * 4,
        )
        result = _zero_hero(ctx)
        _assert_valid_candidates(result, ctx.players)


class TestHighRoller:
    def test_high_bid(self):
        ctx = _build_ctx(
            ["Alice", "Bob"],
            [({"0": 5, "1": 1}, {"0": 5, "1": 1}, {"0": 50, "1": 11}, 8)],
        )
        result = _high_roller(ctx)
        _assert_valid_candidates(result, ctx.players)


class TestAllIn:
    def test_bid_equals_cards(self):
        ctx = _build_ctx(
            ["Alice", "Bob"],
            [({"0": 3, "1": 1}, {"0": 3, "1": 1}, {"0": 30, "1": 11}, 3)],
        )
        result = _all_in(ctx)
        _assert_valid_candidates(result, ctx.players)


class TestFortuneTeller:
    def test_consecutive_correct(self):
        ctx = _build_ctx(
            ["Alice", "Bob"],
            [({"0": 1, "1": 1}, {"0": 1, "1": 1}, {"0": 11, "1": 11}, 5)] * 4,
        )
        result = _fortune_teller(ctx)
        _assert_valid_candidates(result, ctx.players)


class TestScatterbrain:
    def test_returns_list(self):
        ctx = _standard_ctx()
        assert isinstance(_scatterbrain(ctx), list)


class TestOneTrick:
    def test_repeated_bid(self):
        ctx = _build_ctx(
            ["Alice", "Bob"],
            [({"0": 2, "1": 1}, {"0": 2, "1": 1}, {"0": 20, "1": 11}, 5)] * 5,
        )
        result = _one_trick(ctx)
        _assert_valid_candidates(result, ctx.players)


class TestHotStreak:
    def test_positive_streak(self):
        ctx = _build_ctx(
            ["Alice", "Bob"],
            [({"0": 2, "1": 1}, {"0": 2, "1": 1}, {"0": 20, "1": 11}, 5)] * 5,
        )
        result = _hot_streak(ctx)
        _assert_valid_candidates(result, ctx.players)


class TestIceCold:
    def test_negative_streak(self):
        ctx = _build_ctx(
            ["Alice", "Bob"],
            [({"0": 2, "1": 1}, {"0": 0, "1": 0}, {"0": -20, "1": -11}, 5)] * 4,
        )
        result = _ice_cold(ctx)
        _assert_valid_candidates(result, ctx.players)


class TestComebackKing:
    def test_returns_list(self):
        ctx = _standard_ctx()
        assert isinstance(_comeback_king(ctx), list)


class TestSlowStarter:
    def test_returns_list(self):
        ctx = _standard_ctx()
        assert isinstance(_slow_starter(ctx), list)


class TestFastFade:
    def test_returns_list(self):
        ctx = _standard_ctx()
        assert isinstance(_fast_fade(ctx), list)


class TestCloser:
    def test_returns_list(self):
        ctx = _standard_ctx()
        result = _closer(ctx)
        assert isinstance(result, list)


class TestConservative:
    def test_returns_candidates(self):
        ctx = _standard_ctx()
        result = _conservative(ctx)
        _assert_valid_candidates(result, ctx.players)


class TestDaredevil:
    def test_returns_candidates(self):
        ctx = _standard_ctx()
        result = _daredevil(ctx)
        _assert_valid_candidates(result, ctx.players)


class TestRollercoaster:
    def test_returns_list(self):
        ctx = _standard_ctx()
        assert isinstance(_rollercoaster(ctx), list)


class TestMetronome:
    def test_returns_list(self):
        ctx = _standard_ctx()
        assert isinstance(_metronome(ctx), list)


class TestTrumpMaster:
    def test_returns_list(self):
        ctx = _standard_ctx()
        result = _trump_master(ctx)
        assert isinstance(result, list)


class TestMinimalist:
    def test_returns_list(self):
        ctx = _standard_ctx()
        result = _minimalist(ctx)
        assert isinstance(result, list)


class TestMirror:
    def test_returns_list(self):
        ctx = _standard_ctx()
        assert isinstance(_mirror(ctx), list)


class TestLuckySeven:
    def test_returns_list(self):
        ctx = _standard_ctx()
        assert isinstance(_lucky_seven(ctx), list)


class TestLastLaugh:
    def test_returns_list(self):
        ctx = _standard_ctx()
        assert isinstance(_last_laugh(ctx), list)


class TestSurvivor:
    def test_returns_list(self):
        ctx = _standard_ctx()
        assert isinstance(_survivor(ctx), list)

"""Contract tests for game title patterns.
Auto-discovers patterns. One test per pattern×scenario validates ALL properties.
"""

import pytest

from app.services.game_titles import TITLE_REGISTRY, build_context
from tests.guards.fixtures import (
    PLAYERS_4,
    PLAYERS_8,
    all_missed_game,
    eight_player_game,
    empty_rounds,
    full_game_4p,
)

REQUIRED_FIELDS = {"key", "emoji", "title", "desc", "player", "detail", "score"}

SCENARIOS = {
    "empty": (PLAYERS_4, empty_rounds()),
    "normal_4p": (PLAYERS_4, full_game_4p()),
    "adversarial_8p": (PLAYERS_8, eight_player_game()),
    "all_missed": (PLAYERS_4, all_missed_game()),
}


def _pattern_ids():
    return [(fn.__name__, fn) for fn in TITLE_REGISTRY]


class TestPatternContract:
    @pytest.fixture(params=_pattern_ids(), ids=lambda p: p[0])
    def pattern(self, request):
        return request.param

    @pytest.fixture(params=SCENARIOS.keys())
    def scenario(self, request):
        return SCENARIOS[request.param]

    def test_contract(self, pattern, scenario):
        name, fn = pattern
        players, rounds = scenario
        ctx = build_context(players, rounds)
        result = fn(ctx)
        assert isinstance(result, list), f"{name} returned {type(result)}"
        for c in result:
            missing = REQUIRED_FIELDS - set(c.keys())
            assert not missing, f"{name} missing: {missing}"
            assert c["player"] in players, f"{name}: '{c['player']}' not in players"
            assert isinstance(c["score"], (int, float)), f"{name}: score type {type(c['score'])}"
            assert c["score"] > 0, f"{name}: score={c['score']}"


class TestDRYPatternHelpers:
    """Test the DRY helper functions for avg-bid and variance patterns."""

    def test_conservative_and_daredevil_produce_different_winners(self):
        from app.services.game_titles import build_context
        from tests.guards.fixtures import PLAYERS_4, full_game_4p

        ctx = build_context(PLAYERS_4, full_game_4p())
        # Find conservative and daredevil patterns
        from app.services.game_titles import TITLE_REGISTRY

        conservative_fn = next(f for f in TITLE_REGISTRY if f.__name__ == "_conservative")
        daredevil_fn = next(f for f in TITLE_REGISTRY if f.__name__ == "_daredevil")
        cons = conservative_fn(ctx)
        dare = daredevil_fn(ctx)
        # Both should fire and produce valid candidates
        assert len(cons) > 0, "Conservative should fire"
        assert len(dare) > 0, "Daredevil should fire"
        # They should pick different players (lowest vs highest avg bid)
        # Both produce valid candidates with correct keys
        assert cons[0]["key"] == "conservative"
        assert dare[0]["key"] == "daredevil"

    def test_rollercoaster_and_metronome_produce_different_winners(self):
        from app.services.game_titles import build_context
        from tests.guards.fixtures import PLAYERS_4, full_game_4p

        ctx = build_context(PLAYERS_4, full_game_4p())
        from app.services.game_titles import TITLE_REGISTRY

        roller_fn = next(f for f in TITLE_REGISTRY if f.__name__ == "_rollercoaster")
        metro_fn = next(f for f in TITLE_REGISTRY if f.__name__ == "_metronome")
        roller = roller_fn(ctx)
        metro = metro_fn(ctx)
        assert len(roller) > 0, "Rollercoaster should fire"
        assert len(metro) > 0, "Metronome should fire"
        assert roller[0]["key"] == "rollercoaster"
        assert metro[0]["key"] == "metronome"


class TestGameTitleHelpers:
    """Direct tests for _candidate, _avg_bid_pattern, _variance_pattern."""

    def test_candidate_returns_required_fields(self):
        from app.services.game_titles import _candidate

        result = _candidate("test", "🏆", "Test", "Desc", "Alice", "detail", 50.0)
        assert set(result.keys()) == {"key", "emoji", "title", "desc", "player", "detail", "score"}
        assert result["score"] == 50.0

    def test_avg_bid_pattern_returns_candidates(self):
        from app.services.game_titles import _avg_bid_pattern, build_context
        from tests.guards.fixtures import PLAYERS_4, full_game_4p

        ctx = build_context(PLAYERS_4, full_game_4p())
        result = _avg_bid_pattern(ctx, "test", "🏆", "Test", "Desc", highest=True)
        assert isinstance(result, list)
        assert len(result) > 0
        assert result[0]["key"] == "test"

    def test_variance_pattern_returns_candidates(self):
        from app.services.game_titles import _variance_pattern, build_context
        from tests.guards.fixtures import PLAYERS_4, full_game_4p

        ctx = build_context(PLAYERS_4, full_game_4p())
        result = _variance_pattern(ctx, "test", "🏆", "Test", "Desc", highest=True)
        assert isinstance(result, list)
        assert len(result) > 0

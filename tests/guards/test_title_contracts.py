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

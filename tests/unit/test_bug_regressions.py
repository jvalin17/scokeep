"""Regression tests for specific bugs in metric pipeline and analytics.

BUG-029: 1-round game tempo skew — tempo must be neutral for single-round games
BUG-027: Accumulators count games where player has 0 rounds — must skip
BUG-025/026: Cache staleness with empty games — _resolve_highlights must filter to
             games_with_rounds before comparing against cached total_games count
"""

import math

import pytest

from app.services.analytics import _resolve_highlights
from app.services.metric_aggregator import aggregate_career, compute_display_extras
from app.services.metrics import compute_game_metrics
from tests.unit.conftest import MockRound

# ---------------------------------------------------------------------------
# Shared helpers (mirror style of test_insights.py)
# ---------------------------------------------------------------------------


def _make_round(cards_dealt, bids, hands_won, scores, trump_suit="spades"):
    return MockRound(bids, hands_won, scores, cards_dealt, trump_suit)


def _make_game(players, rounds_data, winner=None):
    class MockGame:
        def __init__(self, players, rounds, winner):
            self.players = players
            self.rounds = rounds
            self.winner = winner

    rounds = []
    for r in rounds_data:
        if len(r) == 5:
            rounds.append(_make_round(*r))
        else:
            rounds.append(_make_round(*r, trump_suit="spades"))
    return MockGame(players, rounds, winner)


# ---------------------------------------------------------------------------
# BUG-029: 1-round game must not crash or skew tempo dimensions
# ---------------------------------------------------------------------------


class TestBug029OnRoundGameTempoSkew:
    """A 1-round game has halfway = 0 // 2 = 0 (< 1).
    Tempo must be neutral (0.5 normalized) for single-round games.
    Bug: if the guard was missing, round_idx=0 would be counted in the first
    half and second-half would be empty, producing an asymmetric tempo reading."""

    def _single_round_metrics(self):
        """GameMetrics from one 5-card round, Nandini bids 3 and makes 3."""
        rnd = _make_round(5, {"0": 3, "1": 2}, {"0": 3, "1": 2}, {"0": 30, "1": 20})
        return compute_game_metrics(["Nandini", "Rahul"], [rnd])

    def test_feature_vector_does_not_crash(self):
        """aggregate_career on a 1-round game must not raise."""
        gm = self._single_round_metrics()
        career = aggregate_career("Nandini", [gm] * 3)
        assert len(career.feature_vector) == 10
        for v in career.feature_vector:
            assert math.isfinite(v), f"Non-finite value in vector: {v}"

    def test_tempo_dimensions_neutral_for_single_round_game(self):
        """Tempo dims (7 and 8) must be 0.5 (neutral) for 1-round games.
        When halfway=0, no half accumulates → raw avg is 0 → normalized to 0.5."""
        gm = self._single_round_metrics()
        career = aggregate_career("Nandini", [gm] * 3)
        assert career.feature_vector[7] == pytest.approx(0.5), (
            f"tempo_first_half should be 0.5 for 1-round game, got {career.feature_vector[7]}"
        )
        assert career.feature_vector[8] == pytest.approx(0.5), (
            f"tempo_second_half should be 0.5 for 1-round game, got {career.feature_vector[8]}"
        )

    def test_extras_tempo_is_even_for_single_round_game(self):
        """compute_display_extras must return tempo='even' for a 1-round game."""
        gm = self._single_round_metrics()
        extras = compute_display_extras("Nandini", [gm] * 3)
        assert extras["tempo"] == "even", (
            f"Expected tempo='even' for 1-round game, got '{extras['tempo']}'"
        )

    def test_accuracy_still_computed_for_single_round(self):
        """Bid accuracy (dim 0) must still reflect the single round even though
        tempo is skipped."""
        gm = self._single_round_metrics()
        career = aggregate_career("Nandini", [gm] * 3)
        # Nandini bids 3 and makes 3 → perfect accuracy
        assert career.feature_vector[0] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# BUG-027: Accumulators must skip games where the player has 0 valid rounds
# ---------------------------------------------------------------------------


class TestBug027AccumulatorsZeroRoundGames:
    """A player listed in game.players but with no bid/hand entries in any round
    must not increment games_played, wins, or game_scores.

    Bug: if the early-return guard was missing, the pipeline would count phantom
    games, inflating the game count and skewing variance."""

    def _metrics_player_listed_but_no_rounds(self):
        """Priya is in the players list but has no bid/hand in any round."""
        rnd1 = _make_round(5, {"1": 3}, {"1": 3}, {"1": 30})
        rnd2 = _make_round(4, {"1": 2}, {"1": 2}, {"1": 20})
        return compute_game_metrics(["Priya", "Vikram"], [rnd1, rnd2])

    def _metrics_player_plays_normally(self):
        """A normal game where Priya has rounds."""
        rnd = _make_round(5, {"0": 2, "1": 3}, {"0": 2, "1": 3}, {"0": 20, "1": 30})
        return compute_game_metrics(["Priya", "Vikram"], [rnd])

    def test_career_does_not_count_zero_round_game(self):
        """aggregate_career must not count games where player has 0 bids."""
        gm = self._metrics_player_listed_but_no_rounds()
        career = aggregate_career("Priya", [gm])
        assert career.games_played == 0

    def test_career_vector_all_zeros_for_zero_round_game(self):
        """No bid data → feature vector must be all zeros."""
        gm = self._metrics_player_listed_but_no_rounds()
        career = aggregate_career("Priya", [gm])
        assert all(v == pytest.approx(0.0) for v in career.feature_vector)

    def test_career_skips_game_with_no_player_rounds(self):
        """1 normal game + 1 zero-round game → career reflects only 1 game."""
        normal = self._metrics_player_plays_normally()
        empty = self._metrics_player_listed_but_no_rounds()
        career = aggregate_career("Priya", [normal, empty])
        # Only 1 game of data → score_variance (dim 3) must be 0
        assert career.feature_vector[3] == pytest.approx(0.0), (
            "score_variance must be 0 with a single scored game"
        )
        assert career.feature_vector[0] == pytest.approx(1.0)

    def test_display_extras_does_not_count_zero_round_game(self):
        """compute_display_extras must not count games where player has 0 bids."""
        gm = self._metrics_player_listed_but_no_rounds()
        extras = compute_display_extras("Priya", [gm])
        assert extras["games_played"] == 0

    def test_display_extras_only_counts_real_games(self):
        """1 real game + 2 zero-round games → games_played=1."""
        normal = self._metrics_player_plays_normally()
        empty = self._metrics_player_listed_but_no_rounds()
        extras = compute_display_extras("Priya", [normal, empty, empty])
        assert extras["games_played"] == 1


# ---------------------------------------------------------------------------
# BUG-025/026: _resolve_highlights cache count must use only games with rounds
# ---------------------------------------------------------------------------


class TestBug025026CacheStalenessWithEmptyGames:
    """The insights blob stores total_games as the count of games that were
    used when highlights were last computed.  If a finished game has no scored
    rounds it must not be counted — otherwise the cache comparison uses the
    wrong denominator and either:
      (a) returns stale highlights when it should recompute, or
      (b) always recomputes because the empty game keeps shifting the count.

    The fix in _resolve_highlights:
        games_with_rounds = [g for g in games if g.id in rounds_by_game]
    and the cache comparison is:
        cached_total == len(games_with_rounds)
    """

    def _make_simple_game(self, game_id, has_rounds=True):
        """Minimal mock of a DB Game row."""

        class MockGame:
            def __init__(self, gid):
                self.id = gid
                self.players = ["Sunita", "Manoj"]
                self.started_at = None
                self.settings = {}
                self.winner = "Sunita"

        return MockGame(game_id)

    def _rounds_by_game(self, game_ids_with_rounds):
        """rounds_by_game dict: only games in the list have entries."""

        class MockRound:
            def __init__(self, game_id):
                self.game_id = game_id
                self.bids = {"0": 2, "1": 3}
                self.hands_won = {"0": 2, "1": 3}
                self.scores = {"0": 20, "1": 30}
                self.cards_dealt = 5
                self.trump_suit = "spades"

        return {gid: [MockRound(gid)] for gid in game_ids_with_rounds}

    def test_cache_hit_when_total_matches_games_with_rounds(self):
        """If blob.total_games == len(games_with_rounds), return cached highlights."""
        real_games = [self._make_simple_game(i) for i in range(1, 4)]
        empty_game = self._make_simple_game(99)  # no rounds
        # rounds_by_game only has entries for real games 1-3
        rounds_by_game = self._rounds_by_game([1, 2, 3])

        # Blob was computed from 3 games (not 4)
        cached_highlights = {
            "career": {
                "sniper": [],
                "zero_master": [],
                "high_roller": [],
                "all_in": [],
                "jinxed": [],
                "perfect_set": [],
            },
            "last_game": None,
        }
        blob = {"total_games": 3, "highlights": cached_highlights}

        all_games = real_games + [empty_game]
        result = _resolve_highlights(blob, all_games, rounds_by_game)

        # Should have returned the cached dict, not recomputed
        assert result is cached_highlights, (
            "_resolve_highlights must return cached highlights when total_games "
            "matches the count of games-with-rounds (empty game excluded)"
        )

    def test_cache_miss_when_total_uses_all_games_including_empty(self):
        """Demonstrate the bug: if the cache comparison incorrectly used
        len(all_games) instead of len(games_with_rounds), a stale cache hit
        would occur here and the returned highlights would be wrong.

        This test verifies that _resolve_highlights does NOT serve cached
        highlights when cached_total == len(all_games) != len(games_with_rounds).
        """
        real_games = [self._make_simple_game(i) for i in range(1, 4)]
        empty_game = self._make_simple_game(99)
        rounds_by_game = self._rounds_by_game([1, 2, 3])

        # Bug scenario: blob was somehow stored with total_games=4 (all games
        # including empty), but only 3 games have rounds
        stale_highlights = {
            "career": {
                "sniper": [{"name": "Sunita", "count": 999}],
                "zero_master": [],
                "high_roller": [],
                "all_in": [],
                "jinxed": [],
                "perfect_set": [],
            },
            "last_game": None,
        }
        blob = {"total_games": 4, "highlights": stale_highlights}

        all_games = real_games + [empty_game]
        result = _resolve_highlights(blob, all_games, rounds_by_game)

        # cached_total=4 != len(games_with_rounds)=3 → must recompute
        # Recomputed highlights will NOT have sniper count=999
        assert result is not stale_highlights, (
            "_resolve_highlights must recompute when cached total_games (4) "
            "does not match games_with_rounds count (3)"
        )

    def test_empty_game_excluded_from_games_with_rounds(self):
        """games_with_rounds must only include games whose id is in rounds_by_game."""
        real_games = [self._make_simple_game(i) for i in range(1, 6)]
        empty_games = [self._make_simple_game(i) for i in range(100, 103)]
        rounds_by_game = self._rounds_by_game([1, 2, 3, 4, 5])

        # Cache matches real game count exactly
        cached = {
            "career": {
                "sniper": [],
                "zero_master": [],
                "high_roller": [],
                "all_in": [],
                "jinxed": [],
                "perfect_set": [],
            },
            "last_game": None,
        }
        blob = {"total_games": 5, "highlights": cached}

        all_games = real_games + empty_games
        result = _resolve_highlights(blob, all_games, rounds_by_game)

        # 5 real + 3 empty, but cache total=5=len(games_with_rounds) → cache hit
        assert result is cached

    def test_recompute_includes_only_games_with_rounds(self):
        """When highlights are recomputed, only games_with_rounds are passed in.
        The recomputed result must be a dict with 'career' key."""
        real_game = self._make_simple_game(1)
        empty_game = self._make_simple_game(2)
        rounds_by_game = self._rounds_by_game([1])

        # No cached blob → recompute
        result = _resolve_highlights(None, [real_game, empty_game], rounds_by_game)

        assert isinstance(result, dict)
        assert "career" in result
        assert "last_game" in result

    def test_all_empty_games_returns_recomputed_empty_highlights(self):
        """All finished games have no rounds → games_with_rounds is empty.
        _resolve_highlights must not crash; must return a highlights dict."""
        empty_games = [self._make_simple_game(i) for i in range(1, 4)]
        rounds_by_game = {}  # no scored rounds anywhere

        result = _resolve_highlights(None, empty_games, rounds_by_game)

        assert isinstance(result, dict)
        assert "career" in result
        # last_game should be None (no rounds to compute from)
        assert result["last_game"] is None

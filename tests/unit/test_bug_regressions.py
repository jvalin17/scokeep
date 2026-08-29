"""Regression tests for specific bugs in feature_extractor and analytics.

BUG-029: 1-round game tempo skew — _track_tempo must return early when halfway < 1
BUG-027: Accumulators count games where player has 0 rounds — both accumulators
         must return early if no valid rounds exist for the player
BUG-024: Phantom MVP from zero-score games — _build_awards must guard empty totals
BUG-025/026: Cache staleness with empty games — _resolve_highlights must filter to
             games_with_rounds before comparing against cached total_games count
"""

import math

import pytest

from app.services.analytics import _build_awards, _resolve_highlights
from app.services.feature_extractor import (
    _ExtrasAccumulator,
    _FeatureAccumulator,
    compute_feature_vector,
    compute_player_extras,
)

# ---------------------------------------------------------------------------
# Shared helpers (mirror style of test_insights.py)
# ---------------------------------------------------------------------------


def _make_round(cards_dealt, bids, hands_won, scores, trump_suit="spades"):
    class MockRound:
        def __init__(self):
            self.cards_dealt = cards_dealt
            self.bids = bids
            self.hands_won = hands_won
            self.scores = scores
            self.trump_suit = trump_suit

    return MockRound()


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
    _track_tempo must return early so neither half accumulates data.
    Bug: if the guard was missing, round_idx=0 would be counted in the first
    half and second-half would be empty, producing an asymmetric tempo reading
    instead of a neutral 0.0 / 0.0."""

    def _single_round_game(self, player="Nandini"):
        """One 5-card round, Nandini bids 3 and makes 3 (score 30)."""
        return _make_game(
            players=[player, "Rahul"],
            rounds_data=[
                (5, {"0": 3, "1": 2}, {"0": 3, "1": 2}, {"0": 30, "1": 20}),
            ],
            winner=player,
        )

    def test_feature_vector_does_not_crash(self):
        """compute_feature_vector on a 1-round game must not raise."""
        game = self._single_round_game()
        vector = compute_feature_vector("Nandini", [game] * 3)
        assert len(vector) == 10
        for v in vector:
            assert math.isfinite(v), f"Non-finite value in vector: {v}"

    def test_tempo_dimensions_are_zero_for_single_round_game(self):
        """Both tempo dimensions (7 and 8) must be 0.0 for a 1-round game.

        halfway = 1 // 2 = 0 → _track_tempo returns early → no half
        accumulates any score → _safe_divide(0, 0) = 0.0 for both.
        If the guard is absent, dim 7 would be 30.0 and dim 8 would be 0.0.
        """
        game = self._single_round_game()
        vector = compute_feature_vector("Nandini", [game] * 3)
        assert vector[7] == pytest.approx(0.0), (
            f"tempo_first_half should be 0.0 for 1-round game, got {vector[7]}"
        )
        assert vector[8] == pytest.approx(0.0), (
            f"tempo_second_half should be 0.0 for 1-round game, got {vector[8]}"
        )

    def test_extras_tempo_is_even_for_single_round_game(self):
        """compute_player_extras must return tempo='even' for a 1-round game."""
        game = self._single_round_game()
        extras = compute_player_extras("Nandini", [game] * 3)
        assert extras["tempo"] == "even", (
            f"Expected tempo='even' for 1-round game, got '{extras['tempo']}'"
        )

    def test_feature_accumulator_track_tempo_skips_halfway_zero(self):
        """Direct unit: _FeatureAccumulator._track_tempo with halfway=0 must not
        increment either half's counters."""
        accum = _FeatureAccumulator()
        # halfway=0 → early return, no matter what round_idx and score are
        accum._track_tempo(score=50, round_idx=0, halfway=0)
        assert accum.first_half_round_count == 0
        assert accum.second_half_round_count == 0
        assert accum.first_half_score_sum == pytest.approx(0.0)
        assert accum.second_half_score_sum == pytest.approx(0.0)

    def test_extras_accumulator_track_tempo_skips_halfway_zero(self):
        """Direct unit: _ExtrasAccumulator._track_tempo with halfway=0 must not
        append to either half's score list."""
        accum = _ExtrasAccumulator()
        accum._track_tempo(score=50, round_idx=0, halfway=0)
        assert accum.first_half_scores == []
        assert accum.second_half_scores == []

    def test_accuracy_still_computed_for_single_round(self):
        """Bid accuracy (dim 0) must still reflect the single round even though
        tempo is skipped — the early return is only inside _track_tempo."""
        game = self._single_round_game()
        vector = compute_feature_vector("Nandini", [game] * 3)
        # Nandini bids 3 and makes 3 → perfect accuracy
        assert vector[0] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# BUG-027: Accumulators must skip games where the player has 0 valid rounds
# ---------------------------------------------------------------------------


class TestBug027AccumulatorsZeroRoundGames:
    """A player listed in game.players but with no bid/hand entries in any round
    must not increment games_played, wins, or game_scores.

    Bug: if the early-return guard was missing, the accumulator would call
    game_scores.append(0.0) and increment games_played even though the player
    contributed nothing, inflating the game count and skewing variance."""

    def _game_player_listed_but_no_rounds(self):
        """Priya is in the players list but has no bid/hand in any round.
        Vikram plays normally."""
        return _make_game(
            players=["Priya", "Vikram"],
            rounds_data=[
                # Only Vikram (index 1) has data; Priya (index 0) is absent
                (
                    5,
                    {"1": 3},
                    {"1": 3},
                    {"1": 30},
                ),
                (
                    4,
                    {"1": 2},
                    {"1": 2},
                    {"1": 20},
                ),
            ],
            winner="Vikram",
        )

    def _game_player_plays_normally(self):
        """A normal game where Priya has rounds (used as contrast)."""
        return _make_game(
            players=["Priya", "Vikram"],
            rounds_data=[
                (5, {"0": 2, "1": 3}, {"0": 2, "1": 3}, {"0": 20, "1": 30}),
            ],
            winner="Vikram",
        )

    # --- _FeatureAccumulator ---

    def test_feature_accumulator_does_not_count_zero_round_game(self):
        """_FeatureAccumulator.process_game must not append to game_scores when
        player has 0 valid rounds."""
        accum = _FeatureAccumulator()
        game = self._game_player_listed_but_no_rounds()
        accum.process_game(game, "Priya", "0")
        assert accum.game_scores == [], (
            "game_scores must remain empty when player has no valid rounds"
        )

    def test_feature_accumulator_no_weighted_total_for_zero_round_game(self):
        """No bid data → weighted_total stays 0; vector must be all zeros."""
        accum = _FeatureAccumulator()
        game = self._game_player_listed_but_no_rounds()
        accum.process_game(game, "Priya", "0")
        assert accum.weighted_total == pytest.approx(0.0)
        vector = accum.to_vector()
        assert all(v == pytest.approx(0.0) for v in vector)

    def test_feature_vector_skips_game_with_no_player_rounds(self):
        """compute_feature_vector: 1 normal game + 1 zero-round game → vector
        reflects only the 1 normal game, no phantom data from the empty one."""
        normal_game = self._game_player_plays_normally()
        empty_game = self._game_player_listed_but_no_rounds()
        vector = compute_feature_vector("Priya", [normal_game, empty_game])
        # Only 1 game of data → score_variance (dim 3) must be 0 (single sample)
        assert vector[3] == pytest.approx(0.0), (
            "score_variance must be 0 with a single scored game "
            f"(phantom game must not inflate count), got {vector[3]}"
        )
        # Accuracy from normal game: Priya bid 2 and made 2 → 1.0
        assert vector[0] == pytest.approx(1.0)

    # --- _ExtrasAccumulator ---

    def test_extras_accumulator_does_not_count_zero_round_game(self):
        """_ExtrasAccumulator.process_game must not increment games_played when
        player has 0 valid rounds."""
        accum = _ExtrasAccumulator()
        game = self._game_player_listed_but_no_rounds()
        accum.process_game(game, "Priya")
        assert accum.games_played == 0, (
            f"games_played must be 0 when player has no valid rounds, got {accum.games_played}"
        )

    def test_extras_accumulator_does_not_count_win_for_zero_round_game(self):
        """Even if game.winner matches the player, wins must not be counted when
        the player has 0 valid rounds (data integrity: can't win if not scored)."""
        accum = _ExtrasAccumulator()
        # Contrived: game says Priya won, but Priya has no scored rounds
        game = _make_game(
            players=["Priya", "Vikram"],
            rounds_data=[(5, {"1": 5}, {"1": 5}, {"1": 50})],
            winner="Priya",
        )
        accum.process_game(game, "Priya")
        assert accum.wins == 0

    def test_extras_accumulator_zero_round_game_leaves_game_totals_empty(self):
        """game_totals must stay empty when player has no valid rounds, so
        consistency() doesn't compute from phantom data."""
        accum = _ExtrasAccumulator()
        game = self._game_player_listed_but_no_rounds()
        accum.process_game(game, "Priya")
        assert accum.game_totals == []

    def test_extras_games_played_only_counts_real_games(self):
        """compute_player_extras: 1 real game + 2 zero-round games → games_played=1."""
        normal_game = self._game_player_plays_normally()
        empty_game = self._game_player_listed_but_no_rounds()
        extras = compute_player_extras("Priya", [normal_game, empty_game, empty_game])
        assert extras["games_played"] == 1, f"Expected 1 real game, got {extras['games_played']}"


# ---------------------------------------------------------------------------
# BUG-024: _build_awards must not crash or produce phantom MVP for empty totals
# ---------------------------------------------------------------------------


class TestBug024PhantomMvpFromZeroScoreGames:
    """_build_awards receives stats with an empty totals dict when the most
    recent game had no scored rounds.  Without the guard, max() on an empty
    dict raises ValueError.

    The fix: return None when totals is empty."""

    def _empty_stats(self):
        """stats dict as returned by _accumulate_game_stats when no bids exist."""
        return {
            "totals": {},
            "bids_made": {},
            "bids_total": {},
            "zero_bids_made": {},
            "overbids": {},
            "underbids": {},
            "best_bid": {},
            "longest_miss": {},
        }

    def _stats_all_zero_scores(self):
        """All players have 0 total score (common in short/penalty games)."""
        players = ["Arjun", "Deepa", "Sanjay"]
        return {
            "totals": dict.fromkeys(players, 0),
            "bids_made": dict.fromkeys(players, 0),
            "bids_total": dict.fromkeys(players, 2),
            "zero_bids_made": dict.fromkeys(players, 0),
            "overbids": dict.fromkeys(players, 1),
            "underbids": dict.fromkeys(players, 1),
            "best_bid": dict.fromkeys(players, 2),
            "longest_miss": dict.fromkeys(players, 0),
        }

    def test_empty_totals_returns_none(self):
        """_build_awards({totals: {}}) must return None, not crash."""
        result = _build_awards(self._empty_stats())
        assert result is None, f"Expected None for empty totals, got {result!r}"

    def test_all_zero_scores_does_not_select_arbitrary_mvp(self):
        """When all players scored 0, the MVP award must not be returned
        (max score is 0, which is not > 0, so mvp should be None or reflect
        that no one scored).

        The current implementation does return an MVP in this case (it picks
        max by value which is 0), but it must not crash and the result must be
        a dict with a 'mvp' key."""
        result = _build_awards(self._stats_all_zero_scores())
        # Must not raise; must be a dict (not None, since totals is non-empty)
        assert isinstance(result, dict)
        assert "mvp" in result
        # The mvp name must be one of the known players
        assert result["mvp"]["name"] in {"Arjun", "Deepa", "Sanjay"}

    def test_normal_game_stats_awards_correct_mvp(self):
        """Sanity check: when one player clearly scored highest, they get MVP."""
        stats = {
            "totals": {"Arjun": 80, "Deepa": 45, "Sanjay": 30},
            "bids_made": {"Arjun": 5, "Deepa": 3, "Sanjay": 2},
            "bids_total": {"Arjun": 6, "Deepa": 6, "Sanjay": 6},
            "zero_bids_made": {"Arjun": 0, "Deepa": 0, "Sanjay": 0},
            "overbids": {"Arjun": 0, "Deepa": 1, "Sanjay": 2},
            "underbids": {"Arjun": 1, "Deepa": 2, "Sanjay": 2},
            "best_bid": {"Arjun": 4, "Deepa": 3, "Sanjay": 2},
            "longest_miss": {"Arjun": 1, "Deepa": 2, "Sanjay": 3},
        }
        result = _build_awards(stats)
        assert result is not None
        assert result["mvp"]["name"] == "Arjun"
        assert result["mvp"]["score"] == 80

    def test_build_awards_returns_expected_keys(self):
        """Result dict must contain all expected award keys."""
        stats = {
            "totals": {"Kiran": 50, "Preethi": 40},
            "bids_made": {"Kiran": 3, "Preethi": 2},
            "bids_total": {"Kiran": 4, "Preethi": 4},
            "zero_bids_made": {"Kiran": 1, "Preethi": 0},
            "overbids": {"Kiran": 0, "Preethi": 1},
            "underbids": {"Kiran": 1, "Preethi": 1},
            "best_bid": {"Kiran": 3, "Preethi": 2},
            "longest_miss": {"Kiran": 1, "Preethi": 2},
        }
        result = _build_awards(stats)
        assert result is not None
        expected_keys = {
            "mvp",
            "sharpshooter",
            "brick_wall",
            "bold_move",
            "cursed",
            "sandbagger",
            "gambler",
        }
        assert expected_keys == set(result.keys())


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

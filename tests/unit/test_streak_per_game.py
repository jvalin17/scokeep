"""TDD: Streaks must be per-game, not span across games.

A player who makes all bids in game 1 (8 rounds) and all bids in
game 2 (8 rounds) should have longest_positive_streak = 8, not 16.
"""

from tests.unit.conftest import MockRound


def _make_game(game_id, players, rounds_data, settings=None):
    class FakeGame:
        def __init__(self):
            self.id = game_id
            self.players = players
            self.settings = settings or {"rounds_per_set": 8}
            self.started_at = None

    return FakeGame(), rounds_data


class TestStreakPerGame:
    def test_positive_streak_does_not_span_games(self):
        """8 made in game 1 + 8 made in game 2 → longest = 8, not 16."""
        from app.services.analytics import _init_career, _process_game_for_career

        players = ["Lala"]
        career = _init_career(players)

        # Game 1: 8 rounds, all made
        g1_rounds = [MockRound({"0": 1}, {"0": 1}, {"0": 11}) for _ in range(8)]
        g1, _ = _make_game(1, players, g1_rounds)

        # Game 2: 8 rounds, all made
        g2_rounds = [MockRound({"0": 1}, {"0": 1}, {"0": 11}) for _ in range(8)]
        g2, _ = _make_game(2, players, g2_rounds)

        _process_game_for_career(g1, {1: g1_rounds}, career)
        _process_game_for_career(g2, {2: g2_rounds}, career)

        assert career["Lala"]["longest_positive_streak"] == 8, (
            f"Expected 8 (per game), got {career['Lala']['longest_positive_streak']}"
        )

    def test_zero_streak_does_not_span_games(self):
        """Zero-bid streaks must also reset between games."""
        from app.services.analytics import _init_career, _process_game_for_career

        players = ["Lala"]
        career = _init_career(players)

        g1_rounds = [MockRound({"0": 0}, {"0": 0}, {"0": 10}) for _ in range(4)]
        g1, _ = _make_game(1, players, g1_rounds)

        g2_rounds = [MockRound({"0": 0}, {"0": 0}, {"0": 10}) for _ in range(4)]
        g2, _ = _make_game(2, players, g2_rounds)

        _process_game_for_career(g1, {1: g1_rounds}, career)
        _process_game_for_career(g2, {2: g2_rounds}, career)

        assert career["Lala"]["longest_zero_streak"] == 4, (
            f"Expected 4 (per game), got {career['Lala']['longest_zero_streak']}"
        )

    def test_streak_within_single_game_still_works(self):
        """A streak within one game should still be counted correctly."""
        from app.services.analytics import _init_career, _process_game_for_career

        players = ["Lala"]
        career = _init_career(players)

        rounds = [
            MockRound({"0": 1}, {"0": 0}, {"0": -11}),  # miss
            MockRound({"0": 1}, {"0": 1}, {"0": 11}),  # made
            MockRound({"0": 1}, {"0": 1}, {"0": 11}),  # made
            MockRound({"0": 1}, {"0": 1}, {"0": 11}),  # made
            MockRound({"0": 1}, {"0": 0}, {"0": -11}),  # miss
        ]
        g1, _ = _make_game(1, players, rounds)
        _process_game_for_career(g1, {1: rounds}, career)

        assert career["Lala"]["longest_positive_streak"] == 3

    def test_best_streak_across_games(self):
        """Longest streak is the best single-game streak across all games."""
        from app.services.analytics import _init_career, _process_game_for_career

        players = ["Lala"]
        career = _init_career(players)

        # Game 1: streak of 3
        g1_rounds = [
            MockRound({"0": 1}, {"0": 1}, {"0": 11}),
            MockRound({"0": 1}, {"0": 1}, {"0": 11}),
            MockRound({"0": 1}, {"0": 1}, {"0": 11}),
            MockRound({"0": 1}, {"0": 0}, {"0": -11}),
        ]
        g1, _ = _make_game(1, players, g1_rounds)

        # Game 2: streak of 5
        g2_rounds = [
            MockRound({"0": 1}, {"0": 1}, {"0": 11}),
            MockRound({"0": 1}, {"0": 1}, {"0": 11}),
            MockRound({"0": 1}, {"0": 1}, {"0": 11}),
            MockRound({"0": 1}, {"0": 1}, {"0": 11}),
            MockRound({"0": 1}, {"0": 1}, {"0": 11}),
        ]
        g2, _ = _make_game(2, players, g2_rounds)

        _process_game_for_career(g1, {1: g1_rounds}, career)
        _process_game_for_career(g2, {2: g2_rounds}, career)

        assert career["Lala"]["longest_positive_streak"] == 5

    def test_miss_streak_does_not_span_games(self):
        """Miss streaks must also reset between games."""
        from app.services.analytics import _init_career, _process_game_for_career

        players = ["Lala"]
        career = _init_career(players)

        # Game 1: 4 misses
        g1_rounds = [MockRound({"0": 1}, {"0": 0}, {"0": -11}) for _ in range(4)]
        g1, _ = _make_game(1, players, g1_rounds)

        # Game 2: 4 misses
        g2_rounds = [MockRound({"0": 1}, {"0": 0}, {"0": -11}) for _ in range(4)]
        g2, _ = _make_game(2, players, g2_rounds)

        _process_game_for_career(g1, {1: g1_rounds}, career)
        _process_game_for_career(g2, {2: g2_rounds}, career)

        assert career["Lala"]["longest_miss_streak"] == 4, (
            f"Expected 4 (per game), got {career['Lala']['longest_miss_streak']}"
        )

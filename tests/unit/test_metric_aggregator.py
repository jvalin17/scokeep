"""TDD: Tests for career metric aggregation.
Written BEFORE metric_aggregator.py exists.
"""


class MockRound:
    def __init__(self, bids, hands_won, scores, cards_dealt=8, trump_suit="spades"):
        self.bids = bids
        self.hands_won = hands_won
        self.scores = scores
        self.cards_dealt = cards_dealt
        self.trump_suit = trump_suit


class TestAggregateCareer:
    """aggregate_career must combine per-game metrics into a career feature vector."""

    def _make_games(self):
        """Two games with different outcomes."""
        from app.services.metrics import compute_game_metrics

        # Game 1: Alice accurate, Bob misses
        g1 = compute_game_metrics(
            ["Alice", "Bob"],
            [
                MockRound({"0": 3, "1": 0}, {"0": 3, "1": 0}, {"0": 30, "1": 10}, 8),
                MockRound({"0": 0, "1": 2}, {"0": 0, "1": 3}, {"0": 10, "1": -20}, 7),
            ],
        )
        # Game 2: Alice misses, Bob accurate
        g2 = compute_game_metrics(
            ["Alice", "Bob"],
            [
                MockRound({"0": 1, "1": 2}, {"0": 0, "1": 2}, {"0": -11, "1": 20}, 6),
                MockRound({"0": 0, "1": 0}, {"0": 0, "1": 0}, {"0": 10, "1": 10}, 5),
            ],
        )
        return [g1, g2]

    def test_returns_feature_vector_of_correct_length(self):
        from app.services.metric_aggregator import aggregate_career

        games = self._make_games()
        career = aggregate_career("Alice", games)
        assert len(career.feature_vector) == 10

    def test_feature_vector_values_between_0_and_1(self):
        from app.services.metric_aggregator import aggregate_career

        games = self._make_games()
        career = aggregate_career("Alice", games)
        for i, v in enumerate(career.feature_vector):
            assert 0.0 <= v <= 1.0, f"dim {i} = {v} out of range"

    def test_games_played_count(self):
        from app.services.metric_aggregator import aggregate_career

        games = self._make_games()
        career = aggregate_career("Alice", games)
        assert career.games_played == 2

    def test_accuracy_reflects_career_average(self):
        from app.services.metric_aggregator import aggregate_career

        games = self._make_games()
        career = aggregate_career("Alice", games)
        # Alice: game1 made 2/2, game2 made 1/2 → career 3/4 = 0.75
        # Feature vector dim 0 = bid_accuracy (weighted)
        assert career.feature_vector[0] > 0.5  # above average

    def test_player_not_in_game_skipped(self):
        from app.services.metric_aggregator import aggregate_career
        from app.services.metrics import compute_game_metrics

        g1 = compute_game_metrics(
            ["Alice", "Bob"],
            [
                MockRound({"0": 1, "1": 0}, {"0": 1, "1": 0}, {"0": 11, "1": 10}, 8),
            ],
        )
        # Charlie not in game 1
        career = aggregate_career("Charlie", [g1])
        assert career.games_played == 0
        assert career.feature_vector == [0.0] * 10

    def test_extras_dict_has_expected_keys(self):
        from app.services.metric_aggregator import aggregate_career

        games = self._make_games()
        career = aggregate_career("Alice", games)
        assert "wins" in career.extras
        assert "games_played" in career.extras
        assert "bidding_style" in career.extras
        assert "consistency" in career.extras
        assert "trend" in career.extras

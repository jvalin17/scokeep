"""TDD: Tests for display extras and accuracy-by-cards in metric_aggregator.

Written BEFORE compute_display_extras / compute_accuracy_by_cards exist.
These functions replace feature_extractor.compute_player_extras and
feature_extractor.compute_accuracy_by_cards, consuming GameMetrics instead
of raw game objects.
"""


class MockRound:
    def __init__(self, bids, hands_won, scores, cards_dealt=8, trump_suit="spades"):
        self.bids = bids
        self.hands_won = hands_won
        self.scores = scores
        self.cards_dealt = cards_dealt
        self.trump_suit = trump_suit


def _make_two_games():
    """Two games: Alice accurate in g1, misses in g2; Bob opposite."""
    from app.services.metrics import compute_game_metrics

    g1 = compute_game_metrics(
        ["Alice", "Bob"],
        [
            MockRound({"0": 3, "1": 0}, {"0": 3, "1": 0}, {"0": 30, "1": 10}, 8, "spades"),
            MockRound({"0": 0, "1": 2}, {"0": 0, "1": 3}, {"0": 10, "1": -20}, 7, "hearts"),
            MockRound({"0": 2, "1": 1}, {"0": 2, "1": 1}, {"0": 20, "1": 11}, 6, "spades"),
            MockRound({"0": 1, "1": 0}, {"0": 1, "1": 0}, {"0": 11, "1": 10}, 3, "clubs"),
        ],
    )
    g2 = compute_game_metrics(
        ["Alice", "Bob"],
        [
            MockRound({"0": 1, "1": 2}, {"0": 0, "1": 2}, {"0": -11, "1": 20}, 6, "diamonds"),
            MockRound({"0": 0, "1": 0}, {"0": 0, "1": 0}, {"0": 10, "1": 10}, 5, "hearts"),
            MockRound({"0": 2, "1": 1}, {"0": 3, "1": 1}, {"0": -20, "1": 11}, 4, "spades"),
            MockRound({"0": 0, "1": 0}, {"0": 1, "1": 0}, {"0": -10, "1": 10}, 2, "clubs"),
        ],
    )
    return [g1, g2]


class TestComputeDisplayExtras:
    """compute_display_extras replaces feature_extractor.compute_player_extras."""

    def test_returns_expected_keys(self):
        from app.services.metric_aggregator import compute_display_extras

        games = _make_two_games()
        extras = compute_display_extras("Alice", games)
        expected_keys = {
            "wins",
            "games_played",
            "total_rounds",
            "best_trump",
            "best_trump_pct",
            "trend",
            "favorite_bid",
            "biggest_round_score",
            "fun_facts",
            "bidding_style",
            "overbid_pct",
            "zero_bid_rate",
            "clutch_wins",
            "clutch_opportunities",
            "tempo",
            "consistency",
        }
        assert set(extras.keys()) == expected_keys

    def test_games_played_count(self):
        from app.services.metric_aggregator import compute_display_extras

        games = _make_two_games()
        extras = compute_display_extras("Alice", games)
        assert extras["games_played"] == 2

    def test_total_rounds_count(self):
        from app.services.metric_aggregator import compute_display_extras

        games = _make_two_games()
        extras = compute_display_extras("Alice", games)
        assert extras["total_rounds"] == 8  # 4 rounds × 2 games

    def test_wins_count(self):
        from app.services.metric_aggregator import compute_display_extras

        games = _make_two_games()
        extras = compute_display_extras("Alice", games)
        # Alice wins game 1 (71 pts), loses game 2 (-31 pts)
        assert extras["wins"] == 1

    def test_biggest_round_score(self):
        from app.services.metric_aggregator import compute_display_extras

        games = _make_two_games()
        extras = compute_display_extras("Alice", games)
        assert extras["biggest_round_score"] == 30

    def test_favorite_bid(self):
        from app.services.metric_aggregator import compute_display_extras

        games = _make_two_games()
        extras = compute_display_extras("Alice", games)
        # Alice bids: 3,0,2,1, 1,0,2,0 → 0 appears 3 times (most)
        assert extras["favorite_bid"] == 0

    def test_zero_bid_rate(self):
        from app.services.metric_aggregator import compute_display_extras

        games = _make_two_games()
        extras = compute_display_extras("Alice", games)
        # Alice zero bids: round 2 (made), round 6 (made), round 8 (missed) → 2/3
        assert extras["zero_bid_rate"] == 67  # round(2/3 * 100)

    def test_bidding_style(self):
        from app.services.metric_aggregator import compute_display_extras

        games = _make_two_games()
        extras = compute_display_extras("Alice", games)
        # Alice has more underbids than overbids → conservative
        assert extras["bidding_style"] == "conservative"

    def test_consistency(self):
        from app.services.metric_aggregator import compute_display_extras

        games = _make_two_games()
        extras = compute_display_extras("Alice", games)
        # Alice game totals: 71 and -31 → stddev ~51 → medium (30-60 range)
        assert extras["consistency"] == "medium"

    def test_tempo(self):
        from app.services.metric_aggregator import compute_display_extras

        games = _make_two_games()
        extras = compute_display_extras("Alice", games)
        # Alice 1st half avg > 2nd half avg → "1st half"
        assert extras["tempo"] == "1st half"

    def test_trend(self):
        from app.services.metric_aggregator import compute_display_extras

        games = _make_two_games()
        extras = compute_display_extras("Alice", games)
        # Only 2 games, need >=4 for trend detection → "steady"
        assert extras["trend"] == "steady"

    def test_fun_facts_is_list_with_content(self):
        from app.services.metric_aggregator import compute_display_extras

        games = _make_two_games()
        extras = compute_display_extras("Alice", games)
        assert isinstance(extras["fun_facts"], list)
        assert all(isinstance(f, str) for f in extras["fun_facts"])

    def test_player_not_in_game(self):
        from app.services.metric_aggregator import compute_display_extras

        games = _make_two_games()
        extras = compute_display_extras("Charlie", games)
        assert extras["games_played"] == 0

    def test_empty_games_list(self):
        from app.services.metric_aggregator import compute_display_extras

        extras = compute_display_extras("Alice", [])
        assert extras["games_played"] == 0
        assert extras["wins"] == 0
        assert extras["total_rounds"] == 0

    def test_clutch_tracking(self):
        from app.services.metric_aggregator import compute_display_extras

        games = _make_two_games()
        extras = compute_display_extras("Alice", games)
        assert 0 <= extras["clutch_wins"] <= extras["clutch_opportunities"]


class TestComputeAccuracyByCards:
    """compute_accuracy_by_cards replaces feature_extractor.compute_accuracy_by_cards."""

    def test_returns_dict_keyed_by_card_count(self):
        from app.services.metric_aggregator import (
            compute_accuracy_by_cards_metrics as compute_accuracy_by_cards,
        )

        games = _make_two_games()
        result = compute_accuracy_by_cards("Alice", games)
        assert isinstance(result, dict)
        # Keys should be string card counts
        for key in result:
            assert key.isdigit()

    def test_each_entry_has_pct_and_rounds(self):
        from app.services.metric_aggregator import (
            compute_accuracy_by_cards_metrics as compute_accuracy_by_cards,
        )

        games = _make_two_games()
        result = compute_accuracy_by_cards("Alice", games)
        for entry in result.values():
            assert "pct" in entry
            assert "rounds" in entry

    def test_accuracy_values(self):
        from app.services.metric_aggregator import (
            compute_accuracy_by_cards_metrics as compute_accuracy_by_cards,
        )

        games = _make_two_games()
        result = compute_accuracy_by_cards("Alice", games)
        # 8-card round: Alice bid 3, made 3 → 100% (1 round)
        assert result["8"]["pct"] == 100
        assert result["8"]["rounds"] == 1

    def test_player_not_in_game(self):
        from app.services.metric_aggregator import (
            compute_accuracy_by_cards_metrics as compute_accuracy_by_cards,
        )

        games = _make_two_games()
        result = compute_accuracy_by_cards("Charlie", games)
        assert result == {}

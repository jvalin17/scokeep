"""TDD: Tests for shared metric computation layer.
Written BEFORE metrics.py exists — all must fail initially.
"""


class MockRound:
    def __init__(self, bids, hands_won, scores, cards_dealt=8, trump_suit="spades"):
        self.bids = bids
        self.hands_won = hands_won
        self.scores = scores
        self.cards_dealt = cards_dealt
        self.trump_suit = trump_suit


class TestComputeGameMetrics:
    """metrics.compute_game_metrics must produce unified per-player stats."""

    def test_basic_two_player_one_round(self):
        from app.services.metrics import compute_game_metrics

        rounds = [
            MockRound(
                {"0": 2, "1": 0},
                {"0": 2, "1": 0},
                {"0": 20, "1": 10},
            )
        ]
        gm = compute_game_metrics(["Alice", "Bob"], rounds)

        assert gm.round_count == 1
        assert gm.players == ["Alice", "Bob"]
        alice = gm.player_metrics["Alice"]
        assert alice.total_score == 20
        assert alice.bids_made == 1
        assert alice.bids_total == 1
        assert alice.rounds_played == 1

        bob = gm.player_metrics["Bob"]
        assert bob.total_score == 10
        assert bob.zero_bids_made == 1
        assert bob.zero_bids_attempted == 1

    def test_accuracy_computation(self):
        from app.services.metrics import compute_game_metrics

        rounds = [
            MockRound({"0": 3, "1": 0}, {"0": 3, "1": 0}, {"0": 30, "1": 10}, 8),
            MockRound({"0": 1, "1": 2}, {"0": 0, "1": 2}, {"0": -11, "1": 20}, 7),
        ]
        gm = compute_game_metrics(["Alice", "Bob"], rounds)
        alice = gm.player_metrics["Alice"]
        assert alice.bids_made == 1  # made round 1, missed round 2
        assert alice.bids_total == 2
        assert alice.overbids == 1  # bid 1 got 0
        bob = gm.player_metrics["Bob"]
        assert bob.bids_made == 2  # made both

    def test_streaks_tracked(self):
        from app.services.metrics import compute_game_metrics

        rounds = [
            MockRound({"0": 1}, {"0": 1}, {"0": 11}, 8),
            MockRound({"0": 2}, {"0": 2}, {"0": 20}, 7),
            MockRound({"0": 0}, {"0": 0}, {"0": 10}, 6),
            MockRound({"0": 1}, {"0": 0}, {"0": -11}, 5),  # miss
        ]
        gm = compute_game_metrics(["A"], rounds)
        a = gm.player_metrics["A"]
        assert a.longest_make_streak == 3
        assert a.longest_miss_streak == 1

    def test_cumulative_scores(self):
        from app.services.metrics import compute_game_metrics

        rounds = [
            MockRound({"0": 1}, {"0": 1}, {"0": 11}, 8),
            MockRound({"0": 2}, {"0": 0}, {"0": -20}, 7),
        ]
        gm = compute_game_metrics(["A"], rounds)
        a = gm.player_metrics["A"]
        assert a.score_cumulative == [11, -9]
        assert a.round_scores == [11, -20]

    def test_winner_detection(self):
        from app.services.metrics import compute_game_metrics

        rounds = [
            MockRound(
                {"0": 3, "1": 0},
                {"0": 3, "1": 0},
                {"0": 30, "1": 10},
            )
        ]
        gm = compute_game_metrics(["Alice", "Bob"], rounds)
        assert gm.winner == "Alice"

    def test_empty_rounds(self):
        from app.services.metrics import compute_game_metrics

        gm = compute_game_metrics(["A", "B"], [])
        assert gm.round_count == 0
        assert gm.winner is None

    def test_off_by_one_count(self):
        from app.services.metrics import compute_game_metrics

        rounds = [
            MockRound({"0": 2}, {"0": 3}, {"0": -20}, 8),  # off by 1
            MockRound({"0": 1}, {"0": 0}, {"0": -11}, 7),  # off by 1
            MockRound({"0": 3}, {"0": 1}, {"0": -30}, 6),  # off by 2
        ]
        gm = compute_game_metrics(["A"], rounds)
        assert gm.player_metrics["A"].off_by_one == 2

    def test_best_bid_made(self):
        from app.services.metrics import compute_game_metrics

        rounds = [
            MockRound({"0": 5}, {"0": 5}, {"0": 50}, 8),
            MockRound({"0": 2}, {"0": 2}, {"0": 20}, 7),
        ]
        gm = compute_game_metrics(["A"], rounds)
        assert gm.player_metrics["A"].best_bid_made == 5

    def test_cards_and_trump_per_round(self):
        from app.services.metrics import compute_game_metrics

        rounds = [
            MockRound({"0": 1}, {"0": 1}, {"0": 11}, 8, "spades"),
            MockRound({"0": 0}, {"0": 0}, {"0": 10}, 7, "hearts"),
        ]
        gm = compute_game_metrics(["A"], rounds)
        assert gm.cards_per_round == [8, 7]
        assert gm.trump_per_round == ["spades", "hearts"]


class TestGameMetricsEquivalence:
    """GameMetrics must produce same data as the old build_context."""

    def test_totals_match(self):
        from app.services.metrics import compute_game_metrics

        rounds = [
            MockRound({"0": 2, "1": 0}, {"0": 2, "1": 0}, {"0": 20, "1": 10}, 8),
            MockRound({"0": 0, "1": 3}, {"0": 1, "1": 3}, {"0": -10, "1": 30}, 7),
        ]
        gm = compute_game_metrics(["A", "B"], rounds)
        assert gm.totals == {"A": 10, "B": 40}
